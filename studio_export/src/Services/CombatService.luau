-- Abilities and fish-on-fish contact: dash hits, size-based bumps, stuns and invisibility breaking.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame.Config)
local FishSpecies = require(FishGame.FishSpecies)
local FishStats = require(FishGame.FishStats)
local Remotes = FishGame.Remotes
local FishService = require(script.Parent.FishService)

local CombatService = {}

local pairCooldown: { [string]: number } = {}

local function now()
	return workspace:GetServerTimeNow()
end

local function pairKey(a, b)
	local ka, kb = a.id, b.id
	return ka < kb and (ka .. "|" .. kb) or (kb .. "|" .. ka)
end

local function canFight(info)
	return FishService.alive(info) and not info.model:GetAttribute("Caught") and not info.root.Anchored
		and not info.model:GetAttribute("Spawning")
end

-- starts a dash for any fish (players come through the remote, bots call this directly)
function CombatService.dash(info, direction: Vector3?)
	local species = FishSpecies[info.species]
	local t = now()
	if (info.model:GetAttribute("AbilityReadyAt") or 0) > t + 0.15 or not canFight(info) then
		return false
	end
	info.model:SetAttribute("AbilityReadyAt", t + species.Ability.Cooldown)
	info.model:SetAttribute("DashingUntil", t + Config.DASH_TIME + 0.1)
	info.model:SetAttribute("DashStart", t)
	if info.bot and direction and direction.Magnitude > 0.01 then
		info.dashDirection = direction.Unit
	end
	return true
end

-- splashes when a fish leaps out / dives back in, shown to everyone
local lastSplash: { [Player]: number } = {}
Remotes.Splash.OnServerEvent:Connect(function(player, position)
	local info = FishService.forPlayer(player)
	if not info or typeof(position) ~= "Vector3" or os.clock() - (lastSplash[player] or 0) < 0.3 then
		return
	end
	if (position - info.root.Position).Magnitude > 20 then
		return
	end
	lastSplash[player] = os.clock()
	Remotes.Effect:FireAllClients("Splash", info.model, position, info.model:GetScale())
end)

Remotes.UseAbility.OnServerEvent:Connect(function(player)
	local info = FishService.forPlayer(player)
	if info then
		CombatService.dash(info)
	end
end)

local function stopDash(info)
	info.model:SetAttribute("DashingUntil", 0)
	if info.player then
		Remotes.Knockback:FireClient(info.player, "DashHit", Vector3.zero, 0)
	end
end

-- the lighter fish flies further, like two masses colliding (mass ~ size factor cubed):
-- base speed between equals, up to twice it against a much heavier fish
local function knockbackSpeed(victim, other, base: number): number
	local mv = victim.model:GetScale() ^ 3
	local mo = other.model:GetScale() ^ 3
	return base * 2 * mo / (mv + mo)
end

local BUMP_KNOCKBACK = 28 -- studs/s between two fish of the same size
local BUMP_STUN = 0.4 -- every bump sends both fish tumbling a little

local function dashHit(attacker, victim)
	local size = attacker.model:GetAttribute("Size") or 2
	FishService.damage(victim, FishStats.dashDamage(size), attacker)
	local dir = attacker.root.AssemblyLinearVelocity
	if dir.Magnitude < 1 then
		dir = victim.root.Position - attacker.root.Position
	end
	FishService.stun(victim, dir.Unit * knockbackSpeed(victim, attacker, Config.DASH_HIT_KNOCKBACK), Config.DASH_HIT_STUN)
	stopDash(attacker)
	Remotes.Effect:FireAllClients("Hit", victim.model, (attacker.root.Position + victim.root.Position) / 2)
end

local function bump(a, b)
	local sa, sb = a.model:GetAttribute("Size") or 2, b.model:GetAttribute("Size") or 2
	local big, small = a, b
	if sb > sa then
		big, small = b, a
	end
	local dBig, dSmall, stun, knock = FishStats.collision(sa - sb)
	FishService.damage(big, dBig, small)
	FishService.damage(small, dSmall, big)
	-- both fish bounce off each other; the size table's extra knock applies to the small one
	local away = small.root.Position - big.root.Position
	if away.Magnitude < 0.01 then
		away = Vector3.yAxis
	end
	away = away.Unit
	local smallSpeed = math.max(knock, knockbackSpeed(small, big, BUMP_KNOCKBACK))
	FishService.stun(small, away * smallSpeed, math.max(stun, BUMP_STUN))
	if sa == sb or stun == 0 then
		FishService.stun(big, -away * knockbackSpeed(big, small, BUMP_KNOCKBACK), BUMP_STUN)
	end
	Remotes.Effect:FireAllClients("Bump", small.model, (a.root.Position + b.root.Position) / 2)
end

local function contact(a, b)
	local t = now()
	local key = pairKey(a, b)
	if (pairCooldown[key] or 0) > t then
		return
	end
	-- an invisible player fish shows up again when it touches another player (bots do not reveal it)
	if not a.bot and not b.bot then
		for _, info in { a, b } do
			if info.invisibleUntil > t then
				FishService.setInvisible(info, 0)
			end
		end
	end
	local dashA = (a.model:GetAttribute("DashingUntil") or 0) > t
	local dashB = (b.model:GetAttribute("DashingUntil") or 0) > t
	if dashA or dashB then
		if dashA then
			dashHit(a, b)
		end
		if dashB then
			dashHit(b, a)
		end
		pairCooldown[key] = t + 1
		return
	end
	local relative = (a.root.AssemblyLinearVelocity - b.root.AssemblyLinearVelocity).Magnitude
	if relative >= Config.COLLISION_MIN_SPEED then
		bump(a, b)
		pairCooldown[key] = t + Config.COLLISION_COOLDOWN
	end
end

local acc = 0
RunService.Heartbeat:Connect(function(dt)
	acc += dt
	if acc < 0.05 then
		return
	end
	acc = 0
	local list = {}
	for _, info in FishService.fish do
		if canFight(info) then
			table.insert(list, info)
		end
	end
	for i = 1, #list do
		local a = list[i]
		for j = i + 1, #list do
			local b = list[j]
			if not (a.bot and b.bot) then
				local reach = Config.CONTACT_DISTANCE * (a.model:GetScale() + b.model:GetScale()) / 2
				if (a.root.Position - b.root.Position).Magnitude < reach then
					contact(a, b)
				end
			end
		end
	end
	-- forget old pairs now and then
	if math.random() < 0.01 then
		local t = now()
		for k, v in pairCooldown do
			if v < t then
				pairCooldown[k] = nil
			end
		end
	end
end)

return CombatService

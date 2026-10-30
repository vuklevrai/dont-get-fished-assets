-- Species abilities other than the dash (ModuleScript, ServerScriptService.Services.AbilityService):
--   "TimeStop" (prehistoric fish, Hyneria): the fish flexes and roars; 0.5 s later time stops for 3 s in a
--       sphere of TIME_STOP.radius around it. Every other fish in it freezes (anchored, TimeFrozenUntil set, the
--       animator holds its pose) while the stopper swims in a rage at double speed (RageUntil). Like in JoJo,
--       the hits it lands on frozen fish wait and all go off at once when time resumes.
--   "CrocBite" (crocodile): the jaws hang open for CROC.armed seconds (BiteArmedUntil); fish within CROC.radius
--       are slowed (FishService.slow) and the first one the snout touches is bitten: damage, stun, BiteStart
--       (the "croc" clip: snap and death roll).
-- Remotes.UseAbility is shared with CombatService: CombatService keeps the dash, this module takes the rest
-- (see luau/CHARACTERS_INTEGRATION.md). Effects sent with Remotes.Effect (a table as the third value):
--   "TimeStop", stopper, { center, radius, duration, windup }    "TimeHit", victim, { position }
--   "TimeResume", stopper, { center, radius }                    "BiteArmed", croc, { radius, duration }
--   "Slowed", fish, { duration }                                  "Chomp", croc, { victim, position }
-- Distances in studs. 1 stud = 0.28 m in Roblox, so 10 m = 36 studs and 3 m = 11 studs.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame.Config)
local FishSpecies = require(FishGame.FishSpecies)
local FishStats = require(FishGame.FishStats)
local Remotes = FishGame.Remotes
local FishService = require(script.Parent.FishService)
assert(FishService.slow, "AbilityService needs FishService.slow (luau/CHARACTERS_INTEGRATION.md, step 3)")

local AbilityService = {}

local TIME_STOP = {
	radius = 36, -- 10 m
	duration = 3,
	windup = 0.5, -- the "arret_du_temps" clip releases the stop at 0.5 s
	hitReach = 1.1, -- contact distance factor against frozen fish (x Config.CONTACT_DISTANCE x scales)
}
local CROC = {
	radius = 11, -- 3 m
	armed = 3, -- seconds with the jaws open
	slowFactor = 0.5,
	slowLinger = 0.6, -- the slow fades this long after leaving the zone
	mouth = 3.6, -- studs from the root centre to the tip of the snout at scale 1 (FishData/Crocodile)
	reach = 1.6, -- bite distance from the snout to the prey's hitbox, at scale 1
	damage = 20, -- +5 per size above 2
	stun = 1.5,
	knockback = 30,
}
AbilityService.TIME_STOP = TIME_STOP
AbilityService.CROC = CROC

local function now()
	return workspace:GetServerTimeNow()
end

local function frozen(info): boolean
	return (info.model:GetAttribute("TimeFrozenUntil") or 0) > now()
end

local function canAct(info): boolean
	return FishService.alive(info) and not info.model:GetAttribute("Caught") and not info.root.Anchored
		and not info.model:GetAttribute("Spawning") and not frozen(info)
end

local function ready(info): boolean
	return (info.model:GetAttribute("AbilityReadyAt") or 0) <= now() + 0.15 and canAct(info)
end

local function startCooldown(info)
	local species = FishSpecies[info.species]
	local t = now()
	info.model:SetAttribute("AbilityReadyAt", t + species.Ability.Cooldown)
	info.model:SetAttribute("AbilityStart", t)
end

-- ------------------------------------------------------------------------------------------ time stop
local stops = {} -- stopper info -> { frozen = { info }, hits = { [victim] = hit }, center, ends }

local function owner(info)
	if info.player and info.player.Parent then
		return info.player
	end
	return nil
end

local function freeze(info, untilT: number)
	local model = info.model
	model:SetAttribute("TimeFrozenUntil", math.max(untilT, model:GetAttribute("TimeFrozenUntil") or 0))
	model:SetAttribute("DashingUntil", 0)
	info.root.AssemblyLinearVelocity = Vector3.zero
	info.root.AssemblyAngularVelocity = Vector3.zero
	pcall(info.root.SetNetworkOwner, info.root, nil)
	info.root.Anchored = true
end

local function unfreeze(info)
	local model = info.model
	if not model.Parent or (model:GetAttribute("TimeFrozenUntil") or 0) > now() + 0.05 then
		return -- gone, or frozen again by another stop that ends later
	end
	model:SetAttribute("TimeFrozenUntil", nil)
	if model:GetAttribute("Caught") then
		return -- a fisherman holds it now
	end
	info.root.Anchored = false
	pcall(info.root.SetNetworkOwner, info.root, owner(info))
end

local function resume(stopper)
	local stop = stops[stopper]
	if not stop then
		return
	end
	stops[stopper] = nil
	for _, info in stop.frozen do
		unfreeze(info)
	end
	-- every hit landed during the stop goes off now
	for victim, hit in stop.hits do
		if FishService.alive(victim) then
			FishService.damage(victim, hit.damage, stopper)
			FishService.stun(victim, hit.impulse, Config.DASH_HIT_STUN)
			Remotes.Effect:FireAllClients("Hit", victim.model, hit.position)
		end
	end
	stopper.model:SetAttribute("RageUntil", 0)
	Remotes.Effect:FireAllClients("TimeResume", stopper.model, { center = stop.center, radius = TIME_STOP.radius })
end

function AbilityService.timeStop(info): boolean
	if not ready(info) then
		return false
	end
	startCooldown(info)
	local model = info.model
	Remotes.Effect:FireAllClients("TimeStop", model, {
		center = info.root.Position,
		radius = TIME_STOP.radius,
		duration = TIME_STOP.duration,
		windup = TIME_STOP.windup,
	})
	task.delay(TIME_STOP.windup, function()
		if not FishService.alive(info) or stops[info] then
			return
		end
		local center = info.root.Position
		local ends = now() + TIME_STOP.duration
		local list = {}
		for _, other in FishService.fish do
			if other ~= info and FishService.alive(other) and not other.model:GetAttribute("Caught")
				and (other.root.Position - center).Magnitude <= TIME_STOP.radius then
				freeze(other, ends)
				table.insert(list, other)
			end
		end
		stops[info] = { frozen = list, hits = {}, center = center, ends = ends }
		model:SetAttribute("RageUntil", ends)
		if info.speedBoostUntil < ends then
			FishService.boostSpeed(info, TIME_STOP.duration)
		end
		task.delay(TIME_STOP.duration, function()
			resume(info)
		end)
	end)
	return true
end

-- the stopper touching frozen fish: the hit is stored (and shown frozen in place) until time resumes
local function stepStops()
	for stopper, stop in stops do
		if not FishService.alive(stopper) then
			resume(stopper)
			continue
		end
		local size = stopper.model:GetAttribute("Size") or 2
		for _, victim in stop.frozen do
			if stop.hits[victim] or not FishService.alive(victim) then
				continue
			end
			local reach = Config.CONTACT_DISTANCE * TIME_STOP.hitReach * (stopper.model:GetScale() + victim.model:GetScale()) / 2
			local away = victim.root.Position - stopper.root.Position
			if away.Magnitude < reach then
				local dir = stopper.root.AssemblyLinearVelocity
				if dir.Magnitude < 1 then
					dir = away
				end
				local position = (victim.root.Position + stopper.root.Position) / 2
				stop.hits[victim] = {
					damage = math.max(5, FishStats.dashDamage(size)),
					impulse = dir.Unit * Config.DASH_HIT_KNOCKBACK,
					position = position,
				}
				Remotes.Effect:FireAllClients("TimeHit", victim.model, { position = position })
			end
		end
	end
end

-- ------------------------------------------------------------------------------------------ crocodile
local armed = {} -- croc info -> { ends, slowed = { [info] = true } }

local function disarm(croc)
	armed[croc] = nil
	if croc.model.Parent then
		croc.model:SetAttribute("BiteArmedUntil", 0)
	end
end

function AbilityService.crocBite(info): boolean
	if not ready(info) then
		return false
	end
	startCooldown(info)
	local ends = now() + CROC.armed
	info.model:SetAttribute("BiteArmedUntil", ends)
	armed[info] = { ends = ends, slowed = {} }
	Remotes.Effect:FireAllClients("BiteArmed", info.model, { radius = CROC.radius, duration = CROC.armed })
	return true
end

local function bite(croc, victim, mouth: Vector3)
	local size = croc.model:GetAttribute("Size") or 2
	FishService.damage(victim, CROC.damage + 5 * math.max(0, size - 2), croc)
	local push = croc.root.CFrame.LookVector * CROC.knockback + Vector3.yAxis * 6
	FishService.stun(victim, push, CROC.stun)
	croc.model:SetAttribute("BiteStart", now())
	disarm(croc)
	Remotes.Effect:FireAllClients("Chomp", croc.model, { victim = victim.model, position = mouth })
end

local function stepCrocs()
	local t = now()
	for croc, state in armed do
		if t > state.ends or not FishService.alive(croc) or frozen(croc) or croc.model:GetAttribute("Caught") then
			disarm(croc)
			continue
		end
		local scale = croc.model:GetScale()
		local centre = croc.root.Position
		local mouth = (croc.root.CFrame * CFrame.new(0, 0, -CROC.mouth * scale)).Position
		local victim, best = nil, math.huge
		for _, other in FishService.fish do
			if other == croc or not FishService.alive(other) or other.model:GetAttribute("Caught") then
				continue
			end
			local pos = other.root.Position
			if (pos - centre).Magnitude <= CROC.radius * math.max(1, scale) then
				FishService.slow(other, CROC.slowFactor, CROC.slowLinger)
				if not state.slowed[other] then
					state.slowed[other] = true
					Remotes.Effect:FireAllClients("Slowed", other.model, { duration = state.ends - t + CROC.slowLinger })
				end
			end
			-- distance from the snout to the prey's hitbox (not its centre): a bite on the tail counts
			local inPrey = other.root.CFrame:PointToObjectSpace(mouth)
			local half = other.root.Size / 2
			local closest = Vector3.new(math.clamp(inPrey.X, -half.X, half.X), math.clamp(inPrey.Y, -half.Y, half.Y),
				math.clamp(inPrey.Z, -half.Z, half.Z))
			local d = (inPrey - closest).Magnitude
			if d < CROC.reach * scale and d < best then
				victim, best = other, d
			end
		end
		if victim then
			bite(croc, victim, mouth)
		end
	end
end

-- ------------------------------------------------------------------------------------------ input
function AbilityService.use(info, direction: Vector3?): boolean
	local species = FishSpecies[info.species]
	local id = species and species.Ability.Id
	if id == "TimeStop" then
		return AbilityService.timeStop(info)
	elseif id == "CrocBite" then
		return AbilityService.crocBite(info)
	end
	return false
end

Remotes.UseAbility.OnServerEvent:Connect(function(player, direction)
	local info = FishService.forPlayer(player)
	if info then
		AbilityService.use(info, typeof(direction) == "Vector3" and direction or nil)
	end
end)

local acc = 0
RunService.Heartbeat:Connect(function(dt)
	acc += dt
	if acc < 0.05 then
		return
	end
	acc = 0
	stepStops()
	stepCrocs()
end)

-- a fish that leaves (death, end of round) never stays frozen or armed
FishService.died.Event:Connect(function(info)
	if stops[info] then
		resume(info)
	end
	if armed[info] then
		disarm(info)
	end
end)

return AbilityService

-- Every gameplay fish (player characters and enemy bots): stats, level, size, health, damage, stuns.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame.Config)
local FishBuilder = require(FishGame.FishBuilder)
local FishSpecies = require(FishGame.FishSpecies)
local FishStats = require(FishGame.FishStats)
local Remotes = FishGame.Remotes

local FishService = {}

export type FishInfo = {
	model: Model,
	humanoid: Humanoid,
	root: BasePart,
	species: string,
	player: Player?,
	bot: boolean,
	level: number,
	sizeStat: number,
	speedStat: number,
	speedBoostUntil: number,
	invisibleUntil: number,
	titanUntil: number,
	invulnerableUntil: number,
	lastAttacker: Player?,
	lastAttackTime: number,
}

FishService.fish = {} :: { [Model]: FishInfo }
local nextId = 0
FishService.died = Instance.new("BindableEvent") -- (info, killerPlayer?)

local function now()
	return workspace:GetServerTimeNow()
end

local function levelBadge(info: FishInfo)
	local gui = info.root:FindFirstChild("LevelBadge")
	if not gui then
		gui = Instance.new("BillboardGui")
		gui.Name = "LevelBadge"
		gui.Size = UDim2.fromOffset(34, 34)
		gui.MaxDistance = 140
		gui.LightInfluence = 0
		local circle = Instance.new("Frame")
		circle.Name = "Circle"
		circle.Size = UDim2.fromScale(1, 1)
		circle.Parent = gui
		Instance.new("UICorner", circle).CornerRadius = UDim.new(1, 0)
		local stroke = Instance.new("UIStroke", circle)
		stroke.Thickness = 2.5
		stroke.Color = Color3.fromRGB(30, 30, 36)
		local label = Instance.new("TextLabel")
		label.Name = "Level"
		label.BackgroundTransparency = 1
		label.Size = UDim2.fromScale(1, 1)
		label.Font = Enum.Font.FredokaOne
		label.TextScaled = true
		label.TextColor3 = Color3.new(1, 1, 1)
		label.Parent = circle
		local ls = Instance.new("UIStroke", label)
		ls.Thickness = 1.5
		ls.Color = Color3.fromRGB(30, 30, 36)
		gui.Parent = info.root
	end
	local maxed = info.level >= FishStats.MAX_LEVEL
	gui.Circle.BackgroundColor3 = maxed and Color3.fromRGB(255, 200, 40) or Color3.fromRGB(128, 130, 140)
	gui.Circle.Level.Text = tostring(info.level)
	gui.StudsOffset = Vector3.new(0, 2.6 * info.model:GetScale(), 0)
end

-- size, speed and the level badge follow the level and the active power-ups
function FishService.applyStats(info: FishInfo)
	local titan = info.titanUntil > now()
	local size = info.sizeStat + (info.level - 1) + (titan and Config.TITAN_SIZE or 0)
	local scale = FishStats.factor(size)
	if math.abs(info.model:GetScale() - scale) > 1e-3 then
		info.model:ScaleTo(scale)
	end
	local base = FishStats.factor(info.speedStat + (titan and Config.TITAN_SPEED or 0))
	local speed = base * (1 + FishStats.LEVEL_SPEED * (info.level - 1))
	if info.speedBoostUntil > now() then
		speed += base * Config.SPEED_BOOST
	end
	local m = info.model
	m:SetAttribute("Level", info.level)
	m:SetAttribute("Size", size)
	m:SetAttribute("SpeedFactor", speed)
	m:SetAttribute("Invisible", info.invisibleUntil > now())
	m:SetAttribute("InvisibleUntil", info.invisibleUntil)
	m:SetAttribute("SpeedBoostUntil", info.speedBoostUntil)
	m:SetAttribute("TitanUntil", info.titanUntil)
	if not info.bot then
		levelBadge(info)
	end
end

-- builds a fish ready to be parented; opts: { player, bot, sizeStat, speedStat, maxHealth, name }
function FishService.create(speciesId: string, opts): (Model, FishInfo)
	local species = FishSpecies[speciesId] or FishSpecies[Config.DEFAULT_SPECIES]
	speciesId = FishSpecies[speciesId] and speciesId or Config.DEFAULT_SPECIES
	local model = FishBuilder.build(species.Model, opts.name or (opts.player and opts.player.Name) or "Fish")
	local humanoid = model:FindFirstChildOfClass("Humanoid")
	nextId += 1
	local info: FishInfo = {
		id = nextId,
		model = model,
		humanoid = humanoid,
		root = model.PrimaryPart,
		species = speciesId,
		player = opts.player,
		bot = opts.bot == true,
		level = 1,
		sizeStat = opts.sizeStat or species.Size,
		speedStat = opts.speedStat or species.Speed,
		speedBoostUntil = 0,
		invisibleUntil = 0,
		titanUntil = 0,
		invulnerableUntil = 0,
		lastAttacker = nil,
		lastAttackTime = 0,
	}
	local maxHealth = opts.maxHealth or FishStats.maxHealth(species.Health)
	humanoid.MaxHealth = maxHealth
	humanoid.Health = maxHealth
	model:SetAttribute("Species", speciesId)
	model:SetAttribute("Bot", info.bot)
	model:SetAttribute("AbilityCooldown", species.Ability.Cooldown)
	model:SetAttribute("AbilityReadyAt", 0)
	model:SetAttribute("DashingUntil", 0)
	model:SetAttribute("StunnedUntil", 0)
	model:SetAttribute("Caught", false)
	CollectionService:AddTag(model, Config.FISH_TAG)
	FishService.fish[model] = info
	FishService.applyStats(info)

	humanoid.Died:Connect(function()
		local killer = nil
		if info.lastAttacker and now() - info.lastAttackTime <= Config.KILL_CREDIT_TIME then
			killer = info.lastAttacker
		end
		FishService.fish[model] = nil
		FishService.died:Fire(info, killer)
	end)
	model.Destroying:Connect(function()
		FishService.fish[model] = nil
	end)
	return model, info
end

function FishService.get(model: Instance?): FishInfo?
	return model and FishService.fish[model :: Model] or nil
end

function FishService.forPlayer(player: Player): FishInfo?
	return FishService.get(player.Character)
end

function FishService.alive(info: FishInfo?): boolean
	return info ~= nil and info.model.Parent ~= nil and info.humanoid.Health > 0
end

function FishService.levelUp(info: FishInfo)
	if info.level >= FishStats.MAX_LEVEL or not FishService.alive(info) then
		return false
	end
	info.level += 1
	info.humanoid.MaxHealth += FishStats.LEVEL_HEALTH
	info.humanoid.Health = math.min(info.humanoid.MaxHealth, info.humanoid.Health + FishStats.LEVEL_HEALTH)
	FishService.applyStats(info)
	Remotes.Effect:FireAllClients("LevelUp", info.model)
	return true
end

function FishService.damage(info: FishInfo, amount: number, attacker: FishInfo?)
	if amount <= 0 or not FishService.alive(info) then
		return
	end
	if info.invulnerableUntil > now() or (info.player and info.player:GetAttribute("GodMode")) then
		return
	end
	if attacker and attacker.player then
		info.lastAttacker = attacker.player
		info.lastAttackTime = now()
	end
	info.humanoid.Health = math.max(0, info.humanoid.Health - amount)
end

-- knock a fish away (studs/s) and leave it tumbling for `duration` seconds
function FishService.stun(info: FishInfo, impulse: Vector3, duration: number)
	if duration <= 0 and impulse.Magnitude < 1 then
		return
	end
	info.model:SetAttribute("StunnedUntil", now() + duration)
	if info.player then
		Remotes.Knockback:FireClient(info.player, "Stun", impulse, duration)
	else
		info.root.AssemblyLinearVelocity = impulse
		info.root.AssemblyAngularVelocity = Vector3.new(math.random() - 0.5, math.random() - 0.5, math.random() - 0.5) * 14
	end
end

function FishService.setInvisible(info: FishInfo, seconds: number)
	info.invisibleUntil = seconds > 0 and now() + seconds or 0
	FishService.applyStats(info)
end

function FishService.boostSpeed(info: FishInfo, seconds: number)
	info.speedBoostUntil = now() + seconds
	FishService.applyStats(info)
end

-- Titan power-up: a huge, fast fish for a while
function FishService.titan(info: FishInfo, seconds: number)
	info.titanUntil = now() + seconds
	FishService.applyStats(info)
end

-- health regeneration and power-up timeouts
local acc = 0
RunService.Heartbeat:Connect(function(dt)
	acc += dt
	if acc < 1 then
		return
	end
	acc -= 1
	local t = now()
	for _, info in FishService.fish do
		if FishService.alive(info) then
			if not info.bot and not info.model:GetAttribute("Caught") then
				info.humanoid.Health = math.min(info.humanoid.MaxHealth, info.humanoid.Health + Config.REGEN_PER_SECOND)
			end
			local invisible = info.invisibleUntil > t
			if info.model:GetAttribute("Invisible") ~= invisible
				or (info.speedBoostUntil > 0 and info.speedBoostUntil <= t)
				or (info.titanUntil > 0 and info.titanUntil <= t) then
				if info.speedBoostUntil <= t then
					info.speedBoostUntil = 0
				end
				if info.titanUntil <= t then
					info.titanUntil = 0
				end
				FishService.applyStats(info)
			end
		end
	end
end)

return FishService

-- Enemy fish bots (server-simulated). The first appears 20 s into the round, then one more every 10 s.
-- They hunt the nearest visible player fish and dash at it every 5 s. Same collision rules as players;
-- killing one gives no level.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame.Config)
local Remotes = FishGame.Remotes
local FishService = require(script.Parent.FishService)
local CombatService = require(script.Parent.CombatService)
local RoundService = require(script.Parent.RoundService)
local MapService = require(script.Parent.MapService)

local EnemyFishService = {}

local running = false
local round = nil
local folder: Folder? = nil
local bots = {}

local function now()
	return workspace:GetServerTimeNow()
end

function EnemyFishService.spawnOne(at: CFrame?)
	if not round or not folder then
		return
	end
	local model, info = FishService.create(Config.DEFAULT_SPECIES, {
		bot = true,
		name = "EnemyFish",
		sizeStat = Config.ENEMY_SIZE_STAT,
		speedStat = Config.ENEMY_SPEED_STAT,
		maxHealth = Config.ENEMY_HEALTH,
	})
	model:PivotTo(at or RoundService.waterSpot(round.map, 4))
	model:SetAttribute("Spawning", true)
	-- materialising: frozen and glowing blue for a moment
	local glow = Instance.new("Highlight")
	glow.FillColor = Color3.fromRGB(40, 140, 255)
	glow.OutlineColor = Color3.fromRGB(150, 220, 255)
	glow.FillTransparency = 0.05
	glow.OutlineTransparency = 0
	glow.DepthMode = Enum.HighlightDepthMode.Occluded
	glow.Parent = model
	model.Parent = folder
	pcall(info.root.SetNetworkOwner, info.root, nil)
	local bot = { info = info, readyAt = now() + 2, wander = nil, wanderUntil = 0, target = nil, velocity = Vector3.zero,
		activeAt = now() + Config.ENEMY_SPAWN_FREEZE }
	table.insert(bots, bot)
	Remotes.Effect:FireAllClients("EnemySpawn", model)
	task.delay(Config.ENEMY_SPAWN_FREEZE - 0.6, function()
		if glow.Parent then
			TweenService:Create(glow, TweenInfo.new(0.6), { FillTransparency = 1, OutlineTransparency = 1 }):Play()
		end
	end)
	task.delay(Config.ENEMY_SPAWN_FREEZE, function()
		if model.Parent then
			model:SetAttribute("Spawning", nil)
			glow:Destroy()
		end
	end)
	FishGame:SetAttribute("Enemies", #bots)
end

FishService.died.Event:Connect(function(info)
	if not info.bot then
		return
	end
	Remotes.Effect:FireAllClients("Poof", nil, info.root.Position)
	task.delay(0.15, function()
		info.model:Destroy()
	end)
end)

local rayParams = RaycastParams.new()
rayParams.FilterType = Enum.RaycastFilterType.Exclude
rayParams.IgnoreWater = true

local function nearestTarget(pos: Vector3)
	local best, bestDist = nil, 220
	local t = now()
	for _, info in FishService.fish do
		if info.player and FishService.alive(info) and not info.model:GetAttribute("Caught")
			and info.invisibleUntil <= t and MapService.depth(round.map, info.root.Position) > -0.5 then
			local d = (info.root.Position - pos).Magnitude
			if d < bestDist then
				best, bestDist = info, d
			end
		end
	end
	return best, bestDist
end

local function steer(bot, dt: number)
	local info = bot.info
	local root = info.root
	local model = info.model
	local velocityC = root:FindFirstChild("SwimVelocity")
	local align = root:FindFirstChild("SwimAlign")
	local t = now()
	if t < bot.activeAt then
		velocityC.VectorVelocity = Vector3.zero
		return
	end
	-- stunned: tumble with water drag
	if (model:GetAttribute("StunnedUntil") or 0) > t then
		align.Enabled = false
		velocityC.MaxAxesForce = Vector3.one * Config.SWIM_FORCE * 0.01
		velocityC.VectorVelocity = Vector3.zero
		bot.velocity = root.AssemblyLinearVelocity
		return
	end
	align.Enabled = true
	velocityC.MaxAxesForce = Vector3.one * Config.SWIM_FORCE
	local pos = root.Position
	local speed = Config.SWIM_SPEED * (model:GetAttribute("SpeedFactor") or 1) * 0.9
	local target, dist = nearestTarget(pos)
	local goal: Vector3
	if target then
		goal = target.root.Position
	else
		if not bot.wander or t > bot.wanderUntil or (bot.wander - pos).Magnitude < 6 then
			bot.wander = RoundService.waterSpot(round.map, 4).Position
			bot.wanderUntil = t + 6
		end
		goal = bot.wander
		speed *= 0.6
	end
	-- stay under the surface (flat or curved)
	local goalDepth, goalUp = MapService.depth(round.map, goal)
	if goalDepth < 2.5 then
		goal -= goalUp * (2.5 - goalDepth)
	end
	local dir = goal - pos
	dir = dir.Magnitude > 0.1 and dir.Unit or root.CFrame.LookVector
	-- avoid walls and the bed
	rayParams.FilterDescendantsInstances = { model }
	local ahead = workspace:Raycast(pos, dir * 8, rayParams)
	local blocker = ahead and ahead.Instance:FindFirstAncestorWhichIsA("Model")
	if ahead and not (blocker and blocker:GetAttribute("Species")) then
		dir = (dir + ahead.Normal * 1.5 + Vector3.yAxis * 0.4).Unit
	end
	local dashing = (model:GetAttribute("DashingUntil") or 0) > t
	if not dashing and target and dist < Config.ENEMY_DASH_RANGE and t >= bot.readyAt then
		if CombatService.dash(info, dir) then
			bot.readyAt = t + Config.ENEMY_DASH_COOLDOWN
			bot.dashDir = dir
			dashing = true
		end
	end
	local wanted = dashing and (bot.dashDir or dir) * Config.DASH_SPEED * (model:GetAttribute("SpeedFactor") or 1) or dir * speed
	bot.velocity = bot.velocity:Lerp(wanted, 1 - math.exp(-(dashing and 12 or Config.ACCELERATION) * dt))
	local depth, up = MapService.depth(round.map, pos)
	local rising = bot.velocity:Dot(up)
	if depth < 1.5 and rising > 0 then
		bot.velocity -= up * rising
	end
	velocityC.VectorVelocity = bot.velocity
	if bot.velocity.Magnitude > 1 then
		local look = bot.velocity.Unit
		look = Vector3.new(look.X, math.clamp(look.Y, -Config.MAX_PITCH, Config.MAX_PITCH), look.Z)
		align.CFrame = CFrame.lookAt(Vector3.zero, look)
	end
end

RunService.Heartbeat:Connect(function(dt)
	if not running then
		return
	end
	for i = #bots, 1, -1 do
		local bot = bots[i]
		if FishService.alive(bot.info) then
			steer(bot, dt)
		else
			table.remove(bots, i)
			FishGame:SetAttribute("Enemies", #bots)
		end
	end
end)

function EnemyFishService.start(r)
	round = r
	running = true
	folder = Instance.new("Folder")
	folder.Name = "EnemyFish"
	folder.Parent = workspace
	while running and r.elapsed() < Config.ENEMY_START do
		task.wait(0.25)
	end
	while running do
		if RoundService.settings.Enemies and #bots < Config.ENEMY_MAX then
			EnemyFishService.spawnOne()
		end
		task.wait(Config.ENEMY_INTERVAL)
	end
end

function EnemyFishService.stop()
	running = false
	bots = {}
	if folder then
		folder:Destroy()
		folder = nil
	end
	round = nil
	FishGame:SetAttribute("Enemies", 0)
end

function EnemyFishService.clear()
	for _, bot in bots do
		bot.info.model:Destroy()
	end
	bots = {}
	FishGame:SetAttribute("Enemies", 0)
end

return EnemyFishService

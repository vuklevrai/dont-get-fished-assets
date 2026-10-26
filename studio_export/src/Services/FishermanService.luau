-- Fishermen bots standing around the pond. Each one casts a big hook at a random spot on the water,
-- waits 5-20 s, warns with a red fog ball for 2 s, then strikes: a fish inside the fog is hooked and
-- reeled out of the water while its player plays the escape minigame (losing 1 HP every 0.333 s).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame.Config)
local Remotes = FishGame.Remotes
local FishService = require(script.Parent.FishService)
local MapService = require(script.Parent.MapService)
local RoundService = require(script.Parent.RoundService)

local FishermanService = {}

local WATER = Config.WATER_LEVEL
local HOOK_DEPTH = 3.5
local running = false
local round = nil
local folder: Folder? = nil
local fishermen = {}
local hooks = {}

local function now()
	return workspace:GetServerTimeNow()
end

local function deco(p: BasePart)
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	return p
end

local function part(props)
	local p = Instance.new(props.ClassName or "Part")
	props.ClassName = nil
	p.Material = Enum.Material.SmoothPlastic
	for k, v in props do
		p[k] = v
	end
	return deco(p)
end

-- ------------------------------------------------------------------------------------------ spots
local function spotList(map: Model): { CFrame }
	local list = {}
	local f = map:FindFirstChild("FishermanSpots")
	if f then
		for _, p in f:GetChildren() do
			table.insert(list, p.CFrame)
		end
		return list
	end
	-- fallback for maps without spots: first dry ground on 10 rays out of the pond
	local rx, rz = map:GetAttribute("PondRadiusX") or 100, map:GetAttribute("PondRadiusZ") or 80
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Include
	params.FilterDescendantsInstances = { map:FindFirstChild("Ground") }
	for k = 0, 9 do
		local a = k / 10 * math.pi * 2 + 0.2
		for r = 0.85, 1.8, 0.02 do
			local p = Vector3.new(math.cos(a) * rx * r, 60, math.sin(a) * rz * r)
			local hit = workspace:Raycast(p, Vector3.new(0, -200, 0), params)
			if hit and hit.Position.Y > WATER + 0.4 then
				local ground = hit.Position + Vector3.new(math.cos(a), 0, math.sin(a)) * 2
				table.insert(list, CFrame.lookAt(ground, Vector3.new(0, ground.Y, 0)))
				break
			end
		end
	end
	return list
end

-- ------------------------------------------------------------------------------------------ models
local function buildHat(head: BasePart)
	local olive = Color3.fromRGB(116, 124, 62)
	local brim = part({ Name = "HatBrim", Shape = Enum.PartType.Cylinder, Size = Vector3.new(0.2, 2.1, 2.1),
		CFrame = head.CFrame * CFrame.new(0, 0.55, 0) * CFrame.Angles(0, 0, math.rad(90)), Color = olive })
	local crown = part({ Name = "HatCrown", Shape = Enum.PartType.Cylinder, Size = Vector3.new(0.7, 1.35, 1.35),
		CFrame = head.CFrame * CFrame.new(0, 0.95, 0) * CFrame.Angles(0, 0, math.rad(90)), Color = olive })
	for _, p in { brim, crown } do
		p.Anchored = false
		p.Massless = true
		local w = Instance.new("WeldConstraint")
		w.Part0 = head
		w.Part1 = p
		w.Parent = p
		p.Parent = head.Parent
	end
end

local function buildRod(model: Model)
	local hand = model:FindFirstChild("RightHand")
	local root = model.PrimaryPart
	local dir = (root.CFrame.LookVector * math.cos(math.rad(38)) + Vector3.yAxis * math.sin(math.rad(38))).Unit
	local grip = hand.Position
	local function along(a, b, d, color, name)
		local p0, p1 = grip + dir * a, grip + dir * b
		return part({ Name = name, Shape = Enum.PartType.Cylinder, Size = Vector3.new((p1 - p0).Magnitude, d, d),
			CFrame = CFrame.lookAt((p0 + p1) / 2, p1) * CFrame.Angles(0, math.rad(90), 0), Color = color })
	end
	local pieces = {
		along(-1.0, 1.2, 0.42, Color3.fromRGB(120, 72, 38), "RodHandle"),
		along(1.2, 10.5, 0.2, Color3.fromRGB(46, 46, 52), "Rod"),
		part({ Name = "Reel", Shape = Enum.PartType.Cylinder, Size = Vector3.new(0.35, 0.8, 0.8),
			CFrame = CFrame.new(grip + dir * 0.4 - root.CFrame.RightVector * 0.35) * root.CFrame.Rotation, Color = Color3.fromRGB(200, 60, 50) }),
	}
	for _, p in pieces do
		p.Anchored = false
		p.Massless = true
		local w = Instance.new("WeldConstraint")
		w.Part0 = hand
		w.Part1 = p
		w.Parent = p
		p.Parent = model
	end
	local tip = Instance.new("Attachment")
	tip.Name = "RodTip"
	tip.Parent = pieces[2]
	tip.WorldPosition = grip + dir * 10.5
	return tip
end

local function setArm(model: Model, angle: number, time: number?)
	local arm = model:FindFirstChild("RightUpperArm")
	local joint = arm and arm:FindFirstChild("RightShoulder")
	if not joint then
		return
	end
	-- classic Motor6D: turn C0; new AnimationConstraint joints: turn the torso-side attachment
	local target, prop = joint, "C0"
	if joint:IsA("AnimationConstraint") then
		target, prop = joint.Attachment0, "CFrame"
	end
	if not target then
		return
	end
	local rest = target:GetAttribute("Rest" .. prop)
	if not rest then
		rest = target[prop]
		target:SetAttribute("Rest" .. prop, rest)
	end
	local goal = rest * CFrame.Angles(math.rad(angle), 0, 0)
	if time and time > 0 then
		TweenService:Create(target, TweenInfo.new(time, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { [prop] = goal }):Play()
	else
		target[prop] = goal
	end
end

local function buildFisherman(spot: CFrame)
	local desc = Instance.new("HumanoidDescription")
	desc.HeadColor = Color3.fromRGB(234, 184, 146)
	desc.TorsoColor = Color3.fromRGB(242, 190, 40)
	desc.LeftArmColor = Color3.fromRGB(242, 190, 40)
	desc.RightArmColor = Color3.fromRGB(242, 190, 40)
	desc.LeftLegColor = Color3.fromRGB(52, 76, 120)
	desc.RightLegColor = Color3.fromRGB(52, 76, 120)
	local model = Players:CreateHumanoidModelFromDescription(desc, Enum.HumanoidRigType.R15)
	model.Name = "Fisherman"
	local humanoid = model:FindFirstChildOfClass("Humanoid")
	humanoid.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
	humanoid.HealthDisplayType = Enum.HumanoidHealthDisplayType.AlwaysOff
	local animate = model:FindFirstChild("Animate")
	if animate then
		animate:Destroy()
	end
	local root = model.PrimaryPart
	root.Anchored = true
	local height = humanoid.HipHeight + root.Size.Y / 2
	model:PivotTo(CFrame.new(spot.Position + Vector3.new(0, height, 0)) * spot.Rotation)
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.CanQuery = false
			d.CanTouch = false
		end
	end
	setArm(model, 50)
	buildHat(model:FindFirstChild("Head"))
	local tip = buildRod(model)
	return model, tip
end

local function buildHook(): Model
	local m = Instance.new("Model")
	m.Name = "Hook"
	local white, red, steel = Color3.fromRGB(245, 245, 245), Color3.fromRGB(228, 46, 40), Color3.fromRGB(205, 210, 220)
	local bobber = part({ Name = "Bobber", Shape = Enum.PartType.Ball, Size = Vector3.new(1.8, 1.8, 1.8), CFrame = CFrame.new(), Color = white })
	bobber.Parent = m
	part({ Name = "BobberTop", Shape = Enum.PartType.Ball, Size = Vector3.new(1.84, 1.84, 1.84), CFrame = CFrame.new(0, 0.42, 0), Color = red }).Parent = m
	part({ Name = "Antenna", Size = Vector3.new(0.18, 0.9, 0.18), CFrame = CFrame.new(0, 1.5, 0), Color = red }).Parent = m
	part({ Name = "Line", Size = Vector3.new(0.1, HOOK_DEPTH - 1.6, 0.1), CFrame = CFrame.new(0, -(HOOK_DEPTH - 1.6) / 2 - 0.8, 0), Color = Color3.fromRGB(40, 40, 44) }).Parent = m
	-- big J hook, the bend centred HOOK_DEPTH under the bobber
	local y = -HOOK_DEPTH
	local steelProps = { Color = steel, Material = Enum.Material.Metal, Reflectance = 0.2 }
	local function piece(name, size, cf)
		local p = part({ Name = name, Size = size, CFrame = cf })
		for k, v in steelProps do
			p[k] = v
		end
		p.Parent = m
	end
	piece("Eye", Vector3.new(0.5, 0.5, 0.5), CFrame.new(0, y + 2.6, 0))
	piece("Shank", Vector3.new(0.38, 2.8, 0.38), CFrame.new(0, y + 1.0, 0))
	piece("Bend", Vector3.new(1.5, 0.38, 0.38), CFrame.new(0.55, y - 0.4, 0))
	piece("Tip", Vector3.new(0.38, 1.3, 0.38), CFrame.new(1.12, y + 0.05, 0))
	local barb = part({ ClassName = "WedgePart", Name = "Barb", Size = Vector3.new(0.3, 0.6, 0.5),
		CFrame = CFrame.new(0.9, y + 0.6, 0) * CFrame.Angles(0, math.rad(90), 0) })
	for k, v in steelProps do
		barb[k] = v
	end
	barb.Parent = m
	m.PrimaryPart = bobber
	local top = Instance.new("Attachment")
	top.Name = "LineTop"
	top.Position = Vector3.new(0, 0.9, 0)
	top.Parent = bobber
	return m
end

local function lineBeam(tip: Attachment, hookModel: Model)
	local beam = Instance.new("Beam")
	beam.Attachment0 = tip
	beam.Attachment1 = hookModel.PrimaryPart.LineTop
	beam.Width0 = 0.12
	beam.Width1 = 0.12
	beam.Color = ColorSequence.new(Color3.fromRGB(30, 30, 34))
	beam.LightInfluence = 1
	beam.FaceCamera = true
	beam.Segments = 12
	beam.CurveSize0 = -3
	beam.CurveSize1 = 1
	beam.Parent = hookModel
	return beam
end

-- ------------------------------------------------------------------------------------------ catching
function FishermanService.difficulty(): (number, number)
	local steps = Config.CATCH_DIFFICULTY
	local mode = RoundService.settings.Difficulty
	if mode == "Easy" then
		return steps[1][2], steps[1][3]
	elseif mode == "Medium" then
		return steps[2][2], steps[2][3]
	elseif mode == "Hard" then
		return steps[3][2], steps[3][3]
	end
	local t = round and round.elapsed() or 0
	for i = #steps, 1, -1 do
		if t >= steps[i][1] then
			local nextStep = steps[i + 1]
			if not nextStep then
				return steps[i][2], steps[i][3]
			end
			local f = (t - steps[i][1]) / (nextStep[1] - steps[i][1])
			return steps[i][2] + (nextStep[2] - steps[i][2]) * f, steps[i][3] + (nextStep[3] - steps[i][3]) * f
		end
	end
	return steps[1][2], steps[1][3]
end

-- a CFrame at pos whose Y axis is `up` (on the ball map the water's surface is curved)
local function alignUp(pos: Vector3, up: Vector3): CFrame
	if up.Y > 0.999 then
		return CFrame.new(pos)
	end
	local right = up:Cross(Vector3.zAxis)
	if right.Magnitude < 1e-3 then
		right = Vector3.xAxis
	end
	return CFrame.fromMatrix(pos, right.Unit, up)
end

-- v without its component along up
local function flatten(v: Vector3, up: Vector3): Vector3
	return v - up * v:Dot(up)
end

local function hookOnFish(hook)
	-- the hook sits in the caught fish's mouth
	local info = hook.caught
	if info then
		local nose = info.root.CFrame * CFrame.new(0, 0, -info.root.Size.Z / 2 - 0.4)
		hook.model:PivotTo(alignUp(nose.Position + hook.up * (HOOK_DEPTH - 1.2), hook.up))
	end
end

local function release(hook, escaped: boolean)
	local info = hook.caught
	hook.caught = nil
	if not info then
		return
	end
	info.model:SetAttribute("Caught", false)
	if FishService.alive(info) then
		local away = flatten(hook.pos - hook.fisherman.model.PrimaryPart.Position, hook.up)
		local spot = hook.surface - hook.up * 4
		info.root.Anchored = false
		info.model:PivotTo(CFrame.lookAt(spot, spot + (away.Magnitude > 0.1 and away.Unit or Vector3.xAxis)))
		info.root.AssemblyLinearVelocity = Vector3.zero
		if info.player and info.player.Parent then
			pcall(info.root.SetNetworkOwner, info.root, info.player)
		end
		if escaped then
			info.invulnerableUntil = now() + Config.CATCH_RELEASE_INVULNERABLE
		end
	end
	if info.player then
		Remotes.Released:FireClient(info.player, escaped)
	end
end

local function catch(hook, info)
	hook.caught = info
	local model = info.model
	model:SetAttribute("Caught", true)
	model:SetAttribute("DashingUntil", 0)
	info.root.AssemblyLinearVelocity = Vector3.zero
	pcall(info.root.SetNetworkOwner, info.root, nil)
	info.root.Anchored = true
	local fishermanRoot = hook.fisherman.model.PrimaryPart
	local toFisherman = flatten(fishermanRoot.Position - hook.pos, hook.up)
	toFisherman = toFisherman.Magnitude > 0.1 and toFisherman.Unit or Vector3.xAxis
	local hang = hook.surface + hook.up * 7.4 + toFisherman * 5
	local hangCF = CFrame.lookAt(hang, hang + hook.up, toFisherman)
	local start = info.root.CFrame
	setArm(hook.fisherman.model, 120, 0.3)
	if info.player then
		local speed, green = FishermanService.difficulty()
		Remotes.Caught:FireClient(info.player, { pointerSpeed = speed, greenArc = green, fisherman = hook.fisherman.model, hang = hang })
	end
	-- reel out of the water, then thrash on the line while the health drains
	local t0 = os.clock()
	while hook.caught == info and os.clock() - t0 < 0.7 do
		local f = (os.clock() - t0) / 0.7
		info.model:PivotTo(start:Lerp(hangCF, 1 - (1 - f) ^ 3))
		hookOnFish(hook)
		task.wait()
	end
	setArm(hook.fisherman.model, 95, 0.4)
	local nextDrain = os.clock() + Config.CATCH_DRAIN_INTERVAL
	local seed = math.random() * 100
	while hook.caught == info and FishService.alive(info) and running do
		-- thrash on smooth noise: fast but continuous, never a jump to a random pose
		local t = (os.clock() - t0) * 3.5
		local wiggle = CFrame.Angles(
			math.rad(26 * math.noise(t, seed, 0.31)),
			math.rad(46 * math.noise(seed, t, 1.73)),
			math.rad(18 * math.noise(2.9, seed, t))
		)
		info.model:PivotTo(hangCF * wiggle)
		hookOnFish(hook)
		if os.clock() >= nextDrain then
			nextDrain += Config.CATCH_DRAIN_INTERVAL
			FishService.damage(info, 1)
		end
		task.wait()
	end
	if hook.caught == info then
		-- died on the line (or the round stopped)
		release(hook, false)
	end
end

Remotes.CatchResult.OnServerEvent:Connect(function(player, escaped)
	local info = FishService.forPlayer(player)
	if not info then
		return
	end
	for _, hook in hooks do
		if hook.caught == info then
			if escaped == true then
				release(hook, true)
			else
				FishService.damage(info, Config.CATCH_FAIL_DAMAGE)
			end
			return
		end
	end
end)

-- ------------------------------------------------------------------------------------------ casting
-- the realistic red fog is drawn by every client (Effects "Fog"); the hitbox stays a perfect sphere
local function fog(position: Vector3)
	Remotes.Effect:FireAllClients("Fog", nil, position, Config.HOOK_WARNING)
	local marker = Instance.new("Folder")
	marker.Name = "DangerZone"
	return marker
end

local function waitWhile(seconds: number, hook): boolean
	local t0 = os.clock()
	while os.clock() - t0 < seconds do
		if not running or not hook.model.Parent then
			return false
		end
		if hook.state == "waiting" then
			local bob = math.sin(os.clock() * 2.4 + hook.phase) * 0.18
			hook.model:PivotTo(alignUp(hook.surface + hook.up * bob, hook.up))
		end
		task.wait(0.1)
	end
	return true
end

local function castOnce(rec)
	local root = rec.model.PrimaryPart
	local target, up = MapService.castTarget(round.map, root.Position)
	local hookModel = buildHook()
	local from = rec.tip.WorldPosition
	hookModel:PivotTo(CFrame.new(from))
	hookModel.Parent = folder
	lineBeam(rec.tip, hookModel)
	local hook = { fisherman = rec, model = hookModel, surface = target + up * 0.15, up = up,
		pos = target - up * HOOK_DEPTH, state = "flying", phase = math.random() * 6, caught = nil }
	table.insert(hooks, hook)
	-- swing and throw
	setArm(rec.model, 140, 0.35)
	task.wait(0.35)
	setArm(rec.model, 45, 0.25)
	local t0 = os.clock()
	while running and os.clock() - t0 < 0.9 do
		local f = (os.clock() - t0) / 0.9
		local p = from:Lerp(hook.surface, f) + Vector3.new(0, math.sin(f * math.pi) * 10, 0)
		hookModel:PivotTo(CFrame.new(p))
		task.wait()
	end
	hookModel:PivotTo(alignUp(hook.surface, up))
	Remotes.Effect:FireAllClients("Splash", nil, hook.surface, 0.6)
	hook.state = "waiting"

	if waitWhile(math.random(Config.HOOK_WAIT_MIN * 10, Config.HOOK_WAIT_MAX * 10) / 10, hook) then
		hook.state = "warning"
		local zone = fog(hook.pos)
		zone.Parent = hookModel
		if waitWhile(Config.HOOK_WARNING, hook) then
			-- strike: the closest catchable fish inside the danger zone gets hooked
			zone:Destroy()
			local best, bestDist = nil, math.huge
			local t = now()
			for _, info in FishService.fish do
				if info.player and FishService.alive(info) and not info.model:GetAttribute("Caught")
					and info.invisibleUntil <= t and info.invulnerableUntil <= t then
					local d = (info.root.Position - hook.pos).Magnitude
					if d <= Config.HOOK_RADIUS + 1.2 * info.model:GetScale() and d < bestDist then
						best, bestDist = info, d
					end
				end
			end
			setArm(rec.model, 125, 0.15)
			if best then
				hook.state = "reeling"
				catch(hook, best)
			else
				Remotes.Effect:FireAllClients("Splash", nil, hook.surface, 0.8)
				task.wait(0.3)
			end
		end
	end
	if hook.caught then
		release(hook, false)
	end
	hookModel:Destroy()
	table.remove(hooks, table.find(hooks, hook))
	if rec.model.Parent then
		setArm(rec.model, 50, 0.4)
	end
end

local function fishermanLoop(rec)
	while running and rec.model.Parent do
		castOnce(rec)
		if not running then
			break
		end
		task.wait(Config.HOOK_RECAST)
	end
end

local freeSpots = {}

function FishermanService.spawnOne(): boolean
	if not running or #freeSpots == 0 then
		return false
	end
	local spot = table.remove(freeSpots, math.random(1, #freeSpots))
	local ok, model, tip = pcall(buildFisherman, spot)
	if not ok then
		warn("fisherman failed:", model)
		return false
	end
	model.Parent = folder
	local rec = { model = model, tip = tip }
	table.insert(fishermen, rec)
	task.spawn(fishermanLoop, rec)
	FishGame:SetAttribute("Fishermen", #fishermen)
	return true
end

-- positions of hooks waiting in the water (power-ups like to spawn next to them)
function FishermanService.hookPositions(): { Vector3 }
	local list = {}
	for _, hook in hooks do
		if hook.state == "waiting" or hook.state == "warning" then
			table.insert(list, hook.surface)
		end
	end
	return list
end

function FishermanService.start(r)
	round = r
	running = true
	folder = Instance.new("Folder")
	folder.Name = "Fishermen"
	folder.Parent = workspace
	freeSpots = spotList(r.map)
	local spawned = 0
	while running and spawned < Config.FISHERMAN_MAX do
		if RoundService.settings.Fishermen then
			if FishermanService.spawnOne() then
				spawned += 1
			end
		end
		task.wait(Config.FISHERMAN_INTERVAL)
	end
end

function FishermanService.stop()
	running = false
	for _, hook in hooks do
		if hook.caught then
			release(hook, false)
		end
	end
	hooks = {}
	fishermen = {}
	if folder then
		folder:Destroy()
		folder = nil
	end
	FishGame:SetAttribute("Fishermen", 0)
end

-- admin: remove every fisherman right now
function FishermanService.clear()
	for _, rec in fishermen do
		rec.model:Destroy()
	end
	fishermen = {}
	FishGame:SetAttribute("Fishermen", 0)
end

return FishermanService

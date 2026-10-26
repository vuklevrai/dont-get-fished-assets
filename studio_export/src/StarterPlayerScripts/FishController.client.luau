-- Swims the local player's fish like a fish: momentum, gliding, carved turns, banking and tail strokes.
-- Control schemes, picked by the player attribute MoveMode (admin panel):
--   "Classic"    W/A/S/D relative to the camera, Space = up, Ctrl/C = down
--   "CameraOnly" the camera steers and W swims; A/S/D and up/down do nothing (no reverse)
--   "ShiftLock"  over-the-shoulder camera, the fish always faces the aim, W/A/S/D swim and strafe
-- Q or right click = ability (dash). Leaps (auto camera), stuns (knockback + ragdoll), land flops and the
-- hooked cutscene are handled here too. On the ship the avatar keeps Roblox's own controls and camera.
-- Tuning: Config (see luau/ConfigPatch.md), explained in luau/MOVEMENT_DESIGN.md.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame:WaitForChild("Config"))
local ClientState = require(FishGame:WaitForChild("ClientState"))
local Remotes = FishGame:WaitForChild("Remotes")

local player = Players.LocalPlayer
local camera = workspace.CurrentCamera
local terrain = workspace.Terrain

-- Config wins; the defaults keep the script running before ConfigPatch.md is applied
local function tune(name: string, default: number): number
	local value = Config[name]
	return if type(value) == "number" then value else default
end

local WATER_LEVEL = tune("WATER_LEVEL", -1)
local SWIM_FORCE = tune("SWIM_FORCE", 200000)
local WATER_VOXEL_CHECK = Config.WATER_VOXEL_CHECK ~= false -- also ask the terrain whether there is water

-- swimming
local SWIM_SPEED = tune("SWIM_SPEED", 26)
local SWIM_ACCEL = tune("SWIM_ACCEL", 5) -- 1/s: how quickly the fish reaches its cruise speed
local SWIM_GLIDE_DRAG = tune("SWIM_GLIDE_DRAG", 2.2) -- 1/s: water drag while coasting
local SWIM_GLIDE_BRAKE = tune("SWIM_GLIDE_BRAKE", 6) -- studs/s²: ends the glide (stops ~1 s after cruise)
local SWIM_OVERSPEED_DRAG = tune("SWIM_OVERSPEED_DRAG", 6) -- 1/s: bleeds the extra speed after a dash
local SWIM_LATERAL_DRAG = tune("SWIM_LATERAL_DRAG", 14) -- 1/s: sideways slip lost while turning
local SWIM_STRAFE_DRAG = tune("SWIM_STRAFE_DRAG", 4) -- 1/s: same, when strafing (ShiftLock, swim back)
local SWIM_CARVE = tune("SWIM_CARVE", 0.85) -- share of the lost slip given back as forward speed
local SWIM_TURN_RATE = tune("SWIM_TURN_RATE", 10) -- rad/s when still
local SWIM_TURN_FALLOFF = tune("SWIM_TURN_FALLOFF", 60) -- studs/s at which the turn rate is halved
local SWIM_TURN_SHARPNESS = tune("SWIM_TURN_SHARPNESS", 14) -- 1/s: how fast small corrections close
local SWIM_MAX_CLIMB = tune("SWIM_MAX_CLIMB", 0.97) -- steepest swim direction (sine of the angle)
local SWIM_LEVEL_OUT = tune("SWIM_LEVEL_OUT", 1.2) -- 1/s: an idle fish levels out
local SWIM_PULSE = tune("SWIM_PULSE", 0.05) -- tail strokes: the speed surges by this share
local SWIM_UNDULATION = tune("SWIM_UNDULATION", 0.06) -- rad: body sway at full swim
local SWIM_REVERSE = tune("SWIM_REVERSE", 0.55) -- share of the speed when swimming backwards
local SWIM_ALIGN_RESPONSIVENESS = tune("SWIM_ALIGN_RESPONSIVENESS", 40)
local SURFACE_MARGIN = tune("SURFACE_MARGIN", 1.1) -- the fish cruises this far under the surface
local MAX_PITCH = tune("MAX_PITCH", 0.85)
local BANK = tune("BANK", 0.12)
local MAX_BANK = tune("MAX_BANK", 0.6)
local BANK_SMOOTH = tune("BANK_SMOOTH", 6)
local AIR_STEER = tune("AIR_STEER", 0.04)
local NAGE_LOOP = 0.8 -- s: length of the "nage" clip, FishAnimator plays 0.7 + 1.6 * intensity clip-s per s

-- dash
local DASH_SPEED = tune("DASH_SPEED", 97)
local DASH_TIME = tune("DASH_TIME", 0.45)
local DASH_RAMP = tune("DASH_RAMP", 16) -- 1/s
local DASH_TURN_RATE = tune("DASH_TURN_RATE", 1.2) -- rad/s: a dash can still be nudged
local DASH_HIT_KEEP = tune("DASH_HIT_KEEP", 0.35) -- speed kept when our dash hits a fish
local DASH_WALL_STUN = tune("DASH_WALL_STUN", 1)
local DASH_WALL_BOUNCE = tune("DASH_WALL_BOUNCE", 0.2)

-- leap
local LEAP_MIN_PITCH = tune("LEAP_MIN_PITCH", 0.3)
local LEAP_MIN_SPEED = tune("LEAP_MIN_SPEED", 10)
local LEAP_DISTANCE = tune("LEAP_DISTANCE", 30)
local LEAP_HEIGHT = tune("LEAP_HEIGHT", 10)
local LEAP_TIME = tune("LEAP_TIME", 1.1)
local LEAP_COOLDOWN = tune("LEAP_COOLDOWN", 1.2)
local LEAP_SURFACE_UP = tune("LEAP_SURFACE_UP", 0.85) -- leaps only where the surface faces up this much (ball map: the top cap)
local LEAP_ENTRY_KEEP = tune("LEAP_ENTRY_KEEP", 0.6) -- share of the arc's speed kept when diving back in
local LEAP_CAMERA_FOLLOW = tune("LEAP_CAMERA_FOLLOW", 6) -- 1/s
local LEAP_CAMERA_PITCH = tune("LEAP_CAMERA_PITCH", -0.22) -- rad
local LEAP_CAMERA_TILT = tune("LEAP_CAMERA_TILT", 0.3) -- rad of extra pitch along the arc's slope
local LEAP_CONTROL_RETURN = tune("LEAP_CONTROL_RETURN", 0.35) -- s for the mouse to take over again
local DIVE_BOOST = tune("DIVE_BOOST", 1.7)
local DIVE_BOOST_TIME = tune("DIVE_BOOST_TIME", 1.3)

-- stranded on land: Space hops
local FLOP_UP = tune("FLOP_UP", 38)
local FLOP_FORWARD = tune("FLOP_FORWARD", 16)
local FLOP_COOLDOWN = tune("FLOP_COOLDOWN", 0.5)

-- stun: knockback + ragdoll
local STUN_DRAG = tune("STUN_DRAG", 0.92) -- 1/s: about 60 % of the speed lost per second
local STUN_DRAG_QUAD = tune("STUN_DRAG_QUAD", 0.004) -- per stud/s: violent hits bleed faster at first
local STUN_SPIN = tune("STUN_SPIN", 0.16) -- rad/s of tumble per stud/s of knockback
local STUN_SPIN_MAX = tune("STUN_SPIN_MAX", 14)
local STUN_SPIN_DRAG = tune("STUN_SPIN_DRAG", 1.6) -- 1/s
local STUN_BOUNCE = tune("STUN_BOUNCE", 0.45) -- restitution against walls
local STUN_RECOVER_TIME = tune("STUN_RECOVER_TIME", 0.5) -- s for the controls to come back

-- camera
local CAMERA_HEIGHT = tune("CAMERA_HEIGHT", 1.5)
local CAMERA_MIN_DISTANCE = tune("CAMERA_MIN_DISTANCE", 6)
local CAMERA_MAX_DISTANCE = tune("CAMERA_MAX_DISTANCE", 30)
local CAMERA_FOLLOW = tune("CAMERA_FOLLOW", 10) -- spring frequency (rad/s)
local CAMERA_LEAD = tune("CAMERA_LEAD", 0.08) -- s of velocity the camera looks ahead
local CAMERA_LEAD_MAX = tune("CAMERA_LEAD_MAX", 3) -- studs (at size factor 1)
local CAMERA_FOV = tune("CAMERA_FOV", 70)
local CAMERA_FOV_SPEED = tune("CAMERA_FOV_SPEED", 12) -- extra degrees at dash speed
local SHIFTLOCK_OFFSET = tune("SHIFTLOCK_OFFSET", 2.4) -- studs to the right (at size factor 1)
local SHIFTLOCK_TURN_RATE = tune("SHIFTLOCK_TURN_RATE", 14) -- rad/s
local MOUSE_SENSITIVITY = tune("MOUSE_SENSITIVITY", 0.0035)
local TELEPORT_DISTANCE = 6 -- a bigger jump in one frame is a server teleport: the camera glides after it

-- ------------------------------------------------------------------------------------------ state
local character: Model?, root: BasePart?, humanoid: Humanoid?
local swimVelocity: LinearVelocity?, swimAlign: AlignOrientation?
local driving = false -- true while this script owns the camera and the mouse
local fishParts: { BasePart } = {}
local fade = 0

-- camera
local yaw, pitch = 0, -0.15
local zoom = tune("CAMERA_DISTANCE", 11)
local camOffset, camOffsetVel = Vector3.zero, Vector3.zero -- focus = fish + this offset, sprung towards the lead
local camDist, camDistVel = zoom, 0
local camFov, camFovVel = CAMERA_FOV, 0
local camShoulder, camShoulderVel = 0, 0
local lastRootPos = Vector3.zero
local autoCam = nil -- { yaw, pitch, untilT }: the leap camera, handing control back until untilT
local cutCF: CFrame? = nil -- smoothed camera while hooked
local hookView = nil -- { hang: Vector3, fisherman: Model? } from Remotes.Caught

-- motion
local vel = Vector3.zero -- simulated velocity, what SwimVelocity is told to do
local travel = -Vector3.zAxis -- where the body points (unit)
local heading = CFrame.identity -- final body orientation for SwimAlign
local roll, lastFlatYaw = 0, 0
local intensity, phase = 0, 0 -- tail beat strength (0..1.3) and position in the stroke (0..1)
local wasInWater = true
local wasCaught = false
local lastFlop = 0
local dashUntil = 0
local leap = nil -- { t0, origin, dir, up, distance }
local lastLeap, diveBoostAt = 0, -math.huge
local stunUntil, recoverUntil = 0, 0
local spinAxis, spinRate = Vector3.xAxis, 0

-- world casts ignore every fish (they are handled by the server) and anything without collisions
local worldParams = RaycastParams.new()
worldParams.FilterType = Enum.RaycastFilterType.Exclude
worldParams.IgnoreWater = true
worldParams.RespectCanCollide = true

local function refreshFilter()
	local list: { Instance } = CollectionService:GetTagged(Config.FISH_TAG)
	if character then
		table.insert(list, character)
	end
	worldParams.FilterDescendantsInstances = list
end
CollectionService:GetInstanceAddedSignal(Config.FISH_TAG):Connect(refreshFilter)
CollectionService:GetInstanceRemovedSignal(Config.FISH_TAG):Connect(refreshFilter)

-- ShiftLock aim dot
local crosshairGui = Instance.new("ScreenGui")
crosshairGui.Name = "FishCrosshair"
crosshairGui.ResetOnSpawn = false
crosshairGui.IgnoreGuiInset = true
crosshairGui.Parent = player:WaitForChild("PlayerGui")
local crosshair = Instance.new("Frame")
crosshair.AnchorPoint = Vector2.new(0.5, 0.5)
crosshair.Position = UDim2.fromScale(0.5, 0.5)
crosshair.Size = UDim2.fromOffset(8, 8)
crosshair.BackgroundColor3 = Color3.new(1, 1, 1)
crosshair.Visible = false
crosshair.Parent = crosshairGui
Instance.new("UICorner", crosshair).CornerRadius = UDim.new(1, 0)
local crosshairStroke = Instance.new("UIStroke", crosshair)
crosshairStroke.Thickness = 1.5
crosshairStroke.Color = Color3.fromRGB(20, 30, 50)

-- ------------------------------------------------------------------------------------------ math helpers
local function expK(rate: number, dt: number): number
	return 1 - math.exp(-rate * dt)
end

-- critically damped spring (never overshoots); works on numbers and Vector3s
local function spring(x: any, v: any, target: any, frequency: number, dt: number): (any, any)
	local d = x - target
	local e = math.exp(-frequency * dt)
	local a = v + d * frequency
	return target + (d + a * dt) * e, (v - a * frequency * dt) * e
end

local function wrapAngle(a: number): number
	return (a + math.pi) % (2 * math.pi) - math.pi
end

local function flatYaw(v: Vector3): number
	return math.atan2(-v.X, -v.Z)
end

local function reflect(v: Vector3, normal: Vector3): Vector3
	return v - normal * (2 * v:Dot(normal))
end

-- turns unit vector `from` towards unit vector `to` by at most `maxAngle` radians
local function rotateToward(from: Vector3, to: Vector3, maxAngle: number): Vector3
	local angle = math.acos(math.clamp(from:Dot(to), -1, 1))
	if angle <= maxAngle then
		return to
	end
	local axis = from:Cross(to)
	if axis.Magnitude < 1e-4 then
		-- exactly opposite: swing round through the horizontal
		axis = if math.abs(from.Y) < 0.99 then Vector3.yAxis else Vector3.xAxis
	end
	return (CFrame.fromAxisAngle(axis.Unit, maxAngle) * from).Unit
end

-- smooth for small corrections, capped at `rate` rad/s for big ones (that cap is what makes arcs)
local function steer(from: Vector3, to: Vector3, rate: number, sharpness: number, dt: number): Vector3
	local angle = math.acos(math.clamp(from:Dot(to), -1, 1))
	return rotateToward(from, to, math.min(rate * dt, angle * expK(sharpness, dt)))
end

local function clampClimb(dir: Vector3, limit: number, fallback: Vector3): Vector3
	if math.abs(dir.Y) <= limit then
		return dir
	end
	local flat = Vector3.new(dir.X, 0, dir.Z)
	if flat.Magnitude < 1e-4 then
		flat = Vector3.new(fallback.X, 0, fallback.Z)
	end
	if flat.Magnitude < 1e-4 then
		flat = -Vector3.zAxis
	end
	local y = math.sign(dir.Y) * limit
	return flat.Unit * math.sqrt(1 - y * y) + Vector3.yAxis * y
end

-- turn rate for the current speed: the faster the fish, the wider its tightest turn
local function turnRate(speed: number): number
	return SWIM_TURN_RATE / (1 + speed / SWIM_TURN_FALLOFF)
end

-- ------------------------------------------------------------------------------------------ water
-- The current map's water: a flat pond (default) or a ball floating in the void. Map rotation sets
-- FishGame attributes MapWaterShape ("Plane" | "Sphere"), MapWaterLevel, MapWaterCenter, MapWaterRadius;
-- without them the PondMap's WaterLevel (or Config.WATER_LEVEL) is used.
-- Returns the depth under the surface (negative above it) and the surface normal.
local function surfaceAt(pos: Vector3): (number, Vector3)
	if FishGame:GetAttribute("MapWaterShape") == "Sphere" then
		local centre = FishGame:GetAttribute("MapWaterCenter") or Vector3.zero
		local radius = FishGame:GetAttribute("MapWaterRadius") or 110
		local out = pos - centre
		local d = out.Magnitude
		return radius - d, if d > 1e-3 then out / d else Vector3.yAxis
	end
	local map = workspace:FindFirstChild("PondMap")
	local level = FishGame:GetAttribute("MapWaterLevel") or (map and map:GetAttribute("WaterLevel")) or WATER_LEVEL
	return level - pos.Y, Vector3.yAxis
end

-- is there terrain water just under this point? (keeps fish from "swimming" over land below the water level)
local function waterBelow(pos: Vector3, normal: Vector3): boolean
	if not WATER_VOXEL_CHECK then
		return true
	end
	local probe = pos - normal
	local region = Region3.new(probe - Vector3.one * 0.1, probe + Vector3.one * 0.1):ExpandToGrid(4)
	local materials = terrain:ReadVoxels(region, 4)
	local size = materials.Size
	for x = 1, size.X do
		for y = 1, size.Y do
			for z = 1, size.Z do
				if materials[x][y][z] == Enum.Material.Water then
					return true
				end
			end
		end
	end
	return false
end

-- hysteresis around the surface: control is kept until the fish is clearly out, and only regained once back under
local function waterState(pos: Vector3): (boolean, number, Vector3)
	local depth, normal = surfaceAt(pos)
	local inside = depth > -0.4 and (wasInWater or depth > 0.2)
	if inside and not waterBelow(pos, normal) then
		inside = false
	end
	return inside, depth, normal
end

-- ------------------------------------------------------------------------------------------ character
local function serverNow()
	return workspace:GetServerTimeNow()
end

local function speedFactor(): number
	return character and character:GetAttribute("SpeedFactor") or 1
end

local function scaleOf(): number
	return if character then character:GetScale() else 1
end

-- fish never play the avatar's footstep / swim sounds
local function silence(d: Instance)
	if d:IsA("Sound") then
		d:Destroy()
	end
end

local function releaseControl(subject: Model?)
	character, root, humanoid, swimVelocity, swimAlign = nil, nil, nil, nil, nil
	ClientState.swimModel = nil
	crosshair.Visible = false
	if not driving then
		return
	end
	driving = false
	UserInputService.MouseBehavior = Enum.MouseBehavior.Default
	UserInputService.MouseIconEnabled = true
	camera.CameraType = Enum.CameraType.Custom
	camera.FieldOfView = CAMERA_FOV
	local h = subject and subject:FindFirstChildOfClass("Humanoid")
	if h then
		camera.CameraSubject = h
	end
end

local function onCharacter(newCharacter: Model)
	if not CollectionService:HasTag(newCharacter, Config.FISH_TAG) then
		driving = true
		releaseControl(nil)
		local h = newCharacter:WaitForChild("Humanoid", 10)
		if h and player.Character == newCharacter then
			camera.CameraSubject = h
		end
		return
	end
	character = newCharacter
	root = newCharacter:WaitForChild("HumanoidRootPart") :: BasePart
	humanoid = newCharacter:WaitForChild("Humanoid") :: Humanoid
	swimVelocity = root:WaitForChild("SwimVelocity") :: LinearVelocity
	swimAlign = root:WaitForChild("SwimAlign") :: AlignOrientation
	swimAlign.Responsiveness = SWIM_ALIGN_RESPONSIVENESS
	swimAlign.Enabled = true

	-- the humanoid only exists for camera/health plumbing; keep it from moving the fish
	for _, state in Enum.HumanoidStateType:GetEnumItems() do
		if state ~= Enum.HumanoidStateType.Physics and state ~= Enum.HumanoidStateType.Dead and state ~= Enum.HumanoidStateType.None then
			pcall(humanoid.SetStateEnabled, humanoid, state, false)
		end
	end
	humanoid:ChangeState(Enum.HumanoidStateType.Physics)
	for _, d in root:GetDescendants() do
		silence(d)
	end
	root.DescendantAdded:Connect(silence)

	local look = root.CFrame.LookVector
	yaw = flatYaw(look)
	pitch = -0.15
	heading = root.CFrame.Rotation
	travel = look
	lastFlatYaw = yaw
	vel = Vector3.zero
	roll, intensity, phase = 0, 0, 0
	dashUntil, stunUntil, recoverUntil, spinRate = 0, 0, 0, 0
	leap, autoCam, cutCF, hookView = nil, nil, nil, nil
	wasInWater, wasCaught = true, false
	camOffset, camOffsetVel = Vector3.zero, Vector3.zero
	camDist, camDistVel = zoom * newCharacter:GetScale(), 0
	camShoulder, camShoulderVel = 0, 0
	lastRootPos = root.Position
	refreshFilter()
	fishParts = {}
	fade = 0
	local function addPart(d: Instance)
		if d:IsA("BasePart") and d.Transparency < 1 then
			table.insert(fishParts, d)
		end
	end
	for _, d in newCharacter:GetDescendants() do
		addPart(d)
	end
	newCharacter.DescendantAdded:Connect(addPart)
	ClientState.swimModel = newCharacter
	camera.CameraType = Enum.CameraType.Scriptable
	driving = true
end

player.CharacterAdded:Connect(onCharacter)
if player.Character then
	task.spawn(onCharacter, player.Character)
end

-- ------------------------------------------------------------------------------------------ input
local function moveMode(): string
	local mode = player:GetAttribute("MoveMode")
	if mode == "CameraOnly" or mode == "ShiftLock" then
		return mode
	end
	return "Classic"
end

-- 0 while the leap camera drives, easing back to 1 once the fish is back in the water
local function mouseWeight(): number
	if leap then
		return 0
	end
	if autoCam and autoCam.untilT ~= math.huge then
		local w = 1 - math.clamp((autoCam.untilT - os.clock()) / LEAP_CONTROL_RETURN, 0, 1)
		return w * w * (3 - 2 * w)
	end
	return 1
end

local function rotateCamera(dx: number, dy: number)
	yaw -= dx
	pitch = math.clamp(pitch - dy, -1.35, 1.35)
end

local function aimDirection(): Vector3
	return CFrame.fromEulerAnglesYXZ(pitch, yaw, 0).LookVector
end

local function canAct(): boolean
	return root ~= nil and humanoid ~= nil and humanoid.Health > 0 and not character:GetAttribute("Caught")
		and os.clock() >= stunUntil and leap == nil
end

local function useAbility()
	if not canAct() then
		return
	end
	if (character:GetAttribute("AbilityReadyAt") or 0) > serverNow() then
		return
	end
	-- dash along the camera's aim, started locally so it feels instant; the server checks the cooldown
	local dir = aimDirection()
	travel = dir
	dashUntil = os.clock() + DASH_TIME
	character:SetAttribute("DashStart", serverNow())
	character:SetAttribute("AbilityReadyAt", serverNow() + (character:GetAttribute("AbilityCooldown") or 6))
	Remotes.UseAbility:FireServer(dir)
end

UserInputService.InputBegan:Connect(function(input, processed)
	if not driving or ClientState.uiOpen() then
		return
	end
	if input.UserInputType == Enum.UserInputType.MouseButton2 or (input.KeyCode == Enum.KeyCode.Q and not processed) then
		useAbility()
	end
end)

UserInputService.InputChanged:Connect(function(input)
	if not driving or ClientState.uiOpen() then
		return
	end
	if input.UserInputType == Enum.UserInputType.MouseMovement then
		local k = mouseWeight()
		if k > 0 then
			rotateCamera(input.Delta.X * MOUSE_SENSITIVITY * k, input.Delta.Y * MOUSE_SENSITIVITY * k)
		end
	elseif input.UserInputType == Enum.UserInputType.MouseWheel then
		zoom = math.clamp(zoom - input.Position.Z * 2, CAMERA_MIN_DISTANCE, CAMERA_MAX_DISTANCE)
	end
end)

local function keyAxis(positive: { Enum.KeyCode }, negative: { Enum.KeyCode }): number
	local v = 0
	for _, key in positive do
		if UserInputService:IsKeyDown(key) then
			v += 1
			break
		end
	end
	for _, key in negative do
		if UserInputService:IsKeyDown(key) then
			v -= 1
			break
		end
	end
	return v
end

-- x = right, y = forward, in camera space
local function moveInput(): Vector2
	if UserInputService:GetFocusedTextBox() then
		return Vector2.zero
	end
	return Vector2.new(
		keyAxis({ Enum.KeyCode.D, Enum.KeyCode.Right }, { Enum.KeyCode.A, Enum.KeyCode.Left }),
		keyAxis({ Enum.KeyCode.W, Enum.KeyCode.Up }, { Enum.KeyCode.S, Enum.KeyCode.Down })
	)
end

local function verticalInput(): number
	if UserInputService:GetFocusedTextBox() then
		return 0
	end
	local v = 0
	if UserInputService:IsKeyDown(Enum.KeyCode.Space) then
		v += 1
	end
	if UserInputService:IsKeyDown(Enum.KeyCode.LeftControl) or UserInputService:IsKeyDown(Enum.KeyCode.C) then
		v -= 1
	end
	return v
end

-- what the player asks for this frame:
--   wish     unit direction to swim (nil = no input, the fish coasts)
--   throttle 0..1
--   facing   where the body must point (nil = it follows the swim, like a real fish)
--   strafe   thrust straight along `wish` instead of along the body
local function readIntent(mode: string, camRot: CFrame, move: Vector2, vertical: number)
	local look, right = camRot.LookVector, camRot.RightVector
	if mode == "CameraOnly" then
		if move.Y > 0 then
			return { wish = look, throttle = 1, facing = nil, strafe = false }
		end
		return { wish = nil, throttle = 0, facing = nil, strafe = false }
	end
	local dir = look * move.Y + right * move.X + Vector3.yAxis * vertical
	if mode == "ShiftLock" then
		if dir.Magnitude < 1e-3 then
			return { wish = nil, throttle = 0, facing = look, strafe = true }
		end
		local unit = dir.Unit
		-- strafing is a bit slower than swimming forwards, backing away slower still
		local forwardness = (unit:Dot(look) + 1) / 2
		local throttle = math.min(1, dir.Magnitude) * (SWIM_REVERSE + (1 - SWIM_REVERSE) * forwardness)
		return { wish = unit, throttle = throttle, facing = look, strafe = true }
	end
	if ClientState.backpedal and move.Y < 0 and move.X == 0 and vertical == 0 then
		-- admin option: S swims backwards without turning around
		local flat = Vector3.new(look.X, 0, look.Z)
		flat = if flat.Magnitude > 1e-3 then flat.Unit else travel
		return { wish = -flat, throttle = SWIM_REVERSE, facing = flat, strafe = true }
	end
	if dir.Magnitude < 1e-3 then
		return { wish = nil, throttle = 0, facing = nil, strafe = false }
	end
	return { wish = dir.Unit, throttle = math.min(1, dir.Magnitude), facing = nil, strafe = false }
end

-- ------------------------------------------------------------------------------------------ server pushes
local function handBackCamera()
	if autoCam and autoCam.untilT == math.huge then
		autoCam.untilT = os.clock() + LEAP_CONTROL_RETURN
	end
end

-- knocked away: the body tumbles head over tail while the water slows it down, then control comes back
local function ragdoll(newVel: Vector3, duration: number)
	local clock = os.clock()
	dashUntil, leap = 0, nil
	handBackCamera()
	stunUntil = math.max(stunUntil, clock + duration)
	recoverUntil = stunUntil + STUN_RECOVER_TIME
	vel = newVel
	local axis = Vector3.yAxis:Cross(newVel)
	if axis.Magnitude < 1e-3 then
		axis = heading.RightVector
	end
	-- slightly off-axis so the body looks loose rather than spinning on a pin
	spinAxis = (axis.Unit + heading.LookVector * 0.35).Unit
	spinRate = math.clamp(newVel.Magnitude * STUN_SPIN, 4, STUN_SPIN_MAX)
end

Remotes.Knockback.OnClientEvent:Connect(function(kind: string, impulse: Vector3, duration: number)
	if not root then
		return
	end
	if kind == "DashHit" then
		-- our dash hit a fish: stop, keep a little momentum
		dashUntil = 0
		vel *= DASH_HIT_KEEP
	elseif kind == "Stun" then
		ragdoll(vel * 0.25 + impulse, duration)
		ClientState.shake(math.clamp(impulse.Magnitude / 200, 0.08, 0.45), 0.25)
	end
end)

Remotes.Caught.OnClientEvent:Connect(function(data)
	if type(data) == "table" then
		hookView = { hang = data.hang, fisherman = data.fisherman }
	end
end)

-- ------------------------------------------------------------------------------------------ motion helpers
local function alive(): boolean
	return root ~= nil and root.Parent ~= nil and humanoid ~= nil and humanoid.Health > 0
end

local function obstacleAhead(v: Vector3, dt: number, reach: number): RaycastResult?
	local speed = v.Magnitude
	if speed < 0.5 then
		return nil
	end
	local scale = scaleOf()
	return workspace:Spherecast((root :: BasePart).Position, 0.7 * scale, v * (dt + reach * scale / speed), worldParams)
end

-- swimming into a wall or the bed slides along it, and the body turns to follow the wall
local function slideAlongWalls(dt: number)
	local hit = obstacleAhead(vel, dt, 1.2)
	if not hit then
		return
	end
	local n = hit.Normal
	local into = vel:Dot(n)
	if into < 0 then
		vel -= n * into
	end
	local facingIn = travel:Dot(n)
	if facingIn < 0 then
		local along = travel - n * facingIn
		if along.Magnitude > 1e-3 then
			travel = along.Unit
		end
	end
end

-- tumbling into a wall bounces off it
local function bounce(dt: number)
	local hit = obstacleAhead(vel, dt, 0.6)
	if not hit then
		return
	end
	local into = vel:Dot(hit.Normal)
	if into >= 0 then
		return
	end
	if -into > 15 then
		ClientState.shake(math.clamp(-into / 160, 0.08, 0.3), 0.15)
	end
	spinRate *= -0.7
	vel -= hit.Normal * (into * (1 + STUN_BOUNCE))
end

-- coasting: exponential water drag plus a small brake so the fish comes to rest
local function glide(speed: number, dt: number): number
	local s = math.abs(speed) * math.exp(-SWIM_GLIDE_DRAG * dt) - SWIM_GLIDE_BRAKE * dt
	return math.max(0, s) * math.sign(speed)
end

-- one step of swimming physics: thrust (or glide) along `thrustDir`, sideways slip dies out; when carving,
-- most of that slip is given back as forward speed, so speed is kept through turns (redirected, never created)
local function swimPhysics(dt: number, thrustDir: Vector3, target: number, carve: boolean, cruise: number)
	local before = vel.Magnitude
	local along = vel:Dot(thrustDir)
	local lateral = vel - thrustDir * along
	if target > 0 then
		if along < target then
			along += (target - along) * expK(SWIM_ACCEL, dt)
		else
			along = target + (along - target) * math.exp(-SWIM_OVERSPEED_DRAG * dt)
		end
	else
		-- coasting out of a dash: the extra speed goes quickly, then the normal glide
		if along > cruise then
			along = cruise + (along - cruise) * math.exp(-SWIM_OVERSPEED_DRAG * dt)
		end
		along = glide(along, dt)
	end
	local slip = lateral.Magnitude
	if slip > 1e-4 then
		local kept = slip * math.exp(-(if carve then SWIM_LATERAL_DRAG else SWIM_STRAFE_DRAG) * dt)
		if carve and along > 0 then
			along += (slip - kept) * SWIM_CARVE
		elseif not carve and target <= 0 then
			kept = math.max(0, glide(kept, dt))
		end
		lateral *= kept / slip
	end
	vel = thrustDir * along + lateral
	local limit = math.max(before, target)
	if carve and vel.Magnitude > limit then
		vel = vel.Unit * limit
	end
end

local function diveBoost(clock: number): number
	local since = clock - diveBoostAt
	if since < DIVE_BOOST_TIME then
		return 1 + (DIVE_BOOST - 1) * (1 - since / DIVE_BOOST_TIME)
	end
	return 1
end

-- 0 right after a stun, easing back to 1
local function controlBlend(clock: number): number
	local t = math.clamp((clock - (recoverUntil - STUN_RECOVER_TIME)) / STUN_RECOVER_TIME, 0, 1)
	return t * t * (3 - 2 * t)
end

local function setIntensity(target: number, dt: number)
	intensity += (target - intensity) * expK(5, dt)
end

-- body orientation: faces `forward` (pitch clamped), banks into turns, sways with the tail
local function bodyFrame(forward: Vector3, dt: number, sway: boolean): CFrame
	local flat = Vector3.new(forward.X, 0, forward.Z)
	if flat.Magnitude < 1e-3 then
		flat = Vector3.new(heading.LookVector.X, 0, heading.LookVector.Z)
	end
	flat = if flat.Magnitude > 1e-3 then flat.Unit else -Vector3.zAxis
	local ly = math.clamp(forward.Y, -MAX_PITCH, MAX_PITCH)
	local look = flat * math.sqrt(1 - ly * ly) + Vector3.yAxis * ly
	local y = flatYaw(flat)
	local turn = wrapAngle(y - lastFlatYaw)
	lastFlatYaw = y
	local targetRoll = math.clamp(turn / math.max(dt, 1e-3) * BANK, -MAX_BANK, MAX_BANK)
	roll += (targetRoll - roll) * expK(BANK_SMOOTH, dt)
	local swayAngle = if sway then SWIM_UNDULATION * math.min(intensity, 1) * math.sin(phase * 2 * math.pi) else 0
	return CFrame.lookAt(Vector3.zero, look) * CFrame.Angles(0, swayAngle, roll)
end

local function surfacePoint(pos: Vector3): Vector3
	local depth, normal = surfaceAt(pos)
	return pos + normal * depth
end

-- ------------------------------------------------------------------------------------------ states
local function startLeap(clock: number, aim: Vector3, normal: Vector3, factor: number)
	local flat = aim - normal * aim:Dot(normal)
	if flat.Magnitude < 0.05 then
		flat = travel - normal * travel:Dot(normal)
	end
	if flat.Magnitude < 0.05 then
		flat = Vector3.xAxis
	end
	local rootPart = root :: BasePart
	local dir = flat.Unit
	local distance = LEAP_DISTANCE * factor
	if FishGame:GetAttribute("MapWaterShape") == "Sphere" then
		-- never leap off the ball: the landing point stays within 90 % of its outline, even at high speed
		local centre = FishGame:GetAttribute("MapWaterCenter") or Vector3.zero
		local radius = FishGame:GetAttribute("MapWaterRadius") or 110
		local from = (rootPart.Position - centre) * Vector3.new(1, 0, 1)
		local along = Vector3.new(dir.X, 0, dir.Z)
		if along.Magnitude > 1e-3 then
			along = along.Unit
			local b = from:Dot(along)
			local disc = b * b - (from:Dot(from) - (0.9 * radius) ^ 2)
			if disc > 0 then
				distance = math.clamp(-b + math.sqrt(disc), 0, distance)
			end
		end
	end
	leap = { t0 = clock, origin = rootPart.Position, dir = dir, up = normal, distance = distance }
	lastLeap = clock
	Remotes.Splash:FireServer(surfacePoint(rootPart.Position))
end

local function endLeap(clock: number)
	local exit = leap.dir * (leap.distance / LEAP_TIME) - leap.up * (4 * LEAP_HEIGHT / LEAP_TIME)
	vel = exit * LEAP_ENTRY_KEEP
	travel = clampClimb(vel.Unit, SWIM_MAX_CLIMB, travel)
	leap = nil
	diveBoostAt = clock
	wasInWater = true
	handBackCamera()
	Remotes.Splash:FireServer(surfacePoint((root :: BasePart).Position))
end

-- a predefined arc out of the water and back in; the camera follows it on its own.
-- Returns false once the fish is back in the water (the swim step takes over this frame).
local function stepLeap(dt: number, clock: number): boolean
	local f = (clock - leap.t0) / LEAP_TIME
	local rootPart = root :: BasePart
	-- back under the surface after the top of the arc (a curved surface can come up to meet the fish): dive in
	if f >= 1 or (f > 0.55 and surfaceAt(rootPart.Position) > 0.6) then
		endLeap(clock)
		return false
	end
	local arc = leap.dir * (leap.distance / LEAP_TIME) + leap.up * (4 * LEAP_HEIGHT * (1 - 2 * f) / LEAP_TIME)
	local onArc = leap.origin + leap.dir * (leap.distance * f) + leap.up * (4 * LEAP_HEIGHT * f * (1 - f))
	-- stay on the arc even when something nudges the fish
	vel = arc + (onArc - rootPart.Position) * 8
	local hit = obstacleAhead(vel, dt, 1.2)
	local swimVel = swimVelocity :: LinearVelocity
	if hit then
		-- slammed into a boat, a pod or a wall mid-air: bounce off and let gravity have it
		ClientState.shake(0.3, 0.2)
		ragdoll(reflect(vel, hit.Normal) * 0.3, 0.5)
		swimVel.MaxAxesForce = Vector3.zero
		rootPart.AssemblyLinearVelocity = vel
		return true
	end
	travel = arc.Unit
	swimVel.MaxAxesForce = Vector3.one * SWIM_FORCE
	swimVel.VectorVelocity = vel
	setIntensity(0.5, dt)
	heading = bodyFrame(travel, dt, false)
	autoCam = { yaw = flatYaw(arc), pitch = LEAP_CAMERA_PITCH + LEAP_CAMERA_TILT * arc.Unit.Y, untilT = math.huge }
	return true
end

local function stepDash(dt: number, aim: Vector3, factor: number, depth: number)
	travel = rotateToward(travel, aim, DASH_TURN_RATE * dt)
	vel = vel:Lerp(travel * DASH_SPEED * factor, expK(DASH_RAMP, dt))
	local hit = obstacleAhead(vel, dt, 2.4)
	if hit then
		-- crashing into the map stuns us
		ClientState.shake(0.35, 0.25)
		ragdoll(reflect(vel, hit.Normal) * DASH_WALL_BOUNCE, DASH_WALL_STUN)
		return
	end
	if depth < -0.5 then
		-- burst out of the water: gravity takes over from here
		dashUntil = 0
	end
	local swimVel = swimVelocity :: LinearVelocity
	swimVel.MaxAxesForce = Vector3.one * SWIM_FORCE
	swimVel.VectorVelocity = vel
	setIntensity(1.3, dt)
	heading = bodyFrame(travel, dt, false)
end

local function stepStun(dt: number, inWater: boolean)
	local swimVel = swimVelocity :: LinearVelocity
	if inWater then
		-- water drag: linear (about 60 % of the speed per second) plus a quadratic part for violent hits
		local speed = vel.Magnitude
		vel *= math.exp(-(STUN_DRAG + STUN_DRAG_QUAD * speed) * dt)
		bounce(dt)
		swimVel.MaxAxesForce = Vector3.one * SWIM_FORCE
		swimVel.VectorVelocity = vel
	else
		-- thrown out of the water: gravity takes over (this is how fish leave the ball map)
		vel = (root :: BasePart).AssemblyLinearVelocity
		swimVel.MaxAxesForce = Vector3.zero
	end
	spinRate *= math.exp(-STUN_SPIN_DRAG * dt)
	heading = CFrame.fromAxisAngle(spinAxis, spinRate * dt) * heading
	travel = heading.LookVector
	lastFlatYaw = flatYaw(travel)
	setIntensity(1, dt)
end

local function stepSwim(dt: number, clock: number, intent, depth: number, normal: Vector3, factor: number)
	local control = controlBlend(clock)
	local maxSpeed = SWIM_SPEED * factor * diveBoost(clock)
	local wish = intent.wish
	local throttle = intent.throttle * control
	local speed = vel.Magnitude

	-- steering: the body turns at a limited rate, so changes of direction are arcs
	if intent.facing then
		travel = steer(travel, intent.facing, SHIFTLOCK_TURN_RATE * control, 20, dt)
	elseif wish and throttle > 0 then
		travel = steer(travel, wish, turnRate(speed) * control, SWIM_TURN_SHARPNESS, dt)
	elseif speed < 3 then
		local level = Vector3.new(travel.X, 0, travel.Z)
		if level.Magnitude > 1e-3 then
			travel = steer(travel, level.Unit, 1, SWIM_LEVEL_OUT, dt)
		end
	end
	travel = clampClimb(travel, SWIM_MAX_CLIMB, heading.LookVector)

	-- thrust or glide
	if wish and throttle > 0 then
		if intent.strafe then
			swimPhysics(dt, wish, throttle * maxSpeed, false, maxSpeed)
		else
			swimPhysics(dt, travel, throttle * maxSpeed, true, maxSpeed)
		end
	elseif intent.strafe then
		swimPhysics(dt, if speed > 0.1 then vel / speed else travel, 0, false, maxSpeed)
	else
		swimPhysics(dt, travel, 0, true, maxSpeed)
	end

	-- leap out when swimming up into the surface (top of the water only), otherwise stay under it
	if depth < 1.6 then
		local speedNow = vel.Magnitude
		local aim = if speedNow > 0.1 then vel / speedNow else travel
		local outward = vel:Dot(normal)
		if normal.Y > LEAP_SURFACE_UP and aim:Dot(normal) > LEAP_MIN_PITCH and outward > LEAP_MIN_SPEED * 0.5
			and speedNow > LEAP_MIN_SPEED and clock - lastLeap > LEAP_COOLDOWN and control >= 1 then
			startLeap(clock, aim, normal, factor)
			if stepLeap(dt, clock) then
				return
			end
		end
		local limit = (depth - SURFACE_MARGIN) * 6
		if outward > limit then
			vel -= normal * (outward - limit)
		end
	end
	slideAlongWalls(dt)

	-- tail strokes: the commanded speed surges with the tail beat
	local surge = if throttle > 0 then 1 + SWIM_PULSE * math.sin(phase * 2 * math.pi) else 1
	local swimVel = swimVelocity :: LinearVelocity
	swimVel.MaxAxesForce = Vector3.one * SWIM_FORCE
	swimVel.VectorVelocity = vel * surge

	-- hard strokes while speeding up, a lazy tail while coasting
	local ratio = vel.Magnitude / math.max(maxSpeed, 1)
	setIntensity(if throttle > 0 then math.max(throttle, ratio) else ratio * 0.3, dt)

	local target = bodyFrame(travel, dt, true)
	if control < 1 then
		-- coming out of a tumble: roll back upright smoothly
		heading = heading:Lerp(target, expK(3 + 12 * control, dt))
	else
		heading = target
	end
end

-- stranded on land (or flying through the air): Space makes the fish flop toward where it is steered
local function stepAir(dt: number, clock: number, intent, factor: number)
	local rootPart = root :: BasePart
	local scale = scaleOf()
	local grounded = workspace:Raycast(rootPart.Position, Vector3.new(0, -1.3 * scale, 0), worldParams) ~= nil
	local jump = not ClientState.uiOpen() and UserInputService:IsKeyDown(Enum.KeyCode.Space)
		and not UserInputService:GetFocusedTextBox()
	local wish = intent.wish or Vector3.zero
	if grounded and jump and clock - lastFlop > FLOP_COOLDOWN then
		lastFlop = clock
		local flat = Vector3.new(wish.X, 0, wish.Z)
		flat = if flat.Magnitude > 0.1 then flat.Unit else Vector3.zero
		rootPart.AssemblyLinearVelocity = flat * FLOP_FORWARD + Vector3.yAxis * FLOP_UP
	end
	vel = rootPart.AssemblyLinearVelocity
	local steerForce = SWIM_FORCE * AIR_STEER
	local swimVel = swimVelocity :: LinearVelocity
	swimVel.MaxAxesForce = Vector3.new(steerForce, 0, steerForce)
	local target = wish * (intent.throttle * SWIM_SPEED * factor * 0.5)
	swimVel.VectorVelocity = Vector3.new(target.X, 0, target.Z)
	if vel.Magnitude > 1.5 then
		travel = vel.Unit
	end
	setIntensity(if grounded then 0.6 else 0.3, dt)
	heading = bodyFrame(travel, dt, false)
end

-- ------------------------------------------------------------------------------------------ camera
local function fadeFish(distance: number)
	-- see through the fish when the camera is pushed against it
	local newFade = math.clamp((5 - distance) / 3, 0, 0.9)
	if math.abs(newFade - fade) > 0.01 then
		fade = newFade
		for _, p in fishParts do
			if not (character :: Model):GetAttribute("Invisible") then
				p.LocalTransparencyModifier = fade
			end
		end
	end
end

local function applyAutoCamera(dt: number, clock: number)
	if not autoCam then
		return
	end
	local weight = if autoCam.untilT == math.huge then 1 else math.clamp((autoCam.untilT - clock) / LEAP_CONTROL_RETURN, 0, 1)
	if weight <= 0 then
		autoCam = nil
		return
	end
	local k = expK(LEAP_CAMERA_FOLLOW, dt) * weight
	yaw += wrapAngle(autoCam.yaw - yaw) * k
	pitch = math.clamp(pitch + (autoCam.pitch - pitch) * k, -1.35, 1.35)
end

local function updateCamera(dt: number, mode: string)
	local rootPart = root :: BasePart
	local scale = scaleOf()
	local camRot = CFrame.fromEulerAnglesYXZ(pitch, yaw, 0)

	-- a server teleport (release from a hook, respawn spot...) is absorbed by the offset: the camera glides
	local jump = rootPart.Position - lastRootPos
	lastRootPos = rootPart.Position
	local expected = vel.Magnitude * dt * 2 + 2
	if jump.Magnitude > math.max(TELEPORT_DISTANCE * scale, expected) and jump.Magnitude < 80 then
		camOffset -= jump
	end

	-- focus = fish + sprung offset: smooth, slightly ahead of the swim, never snapping
	local lead = vel * CAMERA_LEAD
	if lead.Magnitude > CAMERA_LEAD_MAX * scale then
		lead = lead.Unit * CAMERA_LEAD_MAX * scale
	end
	camOffset, camOffsetVel = spring(camOffset, camOffsetVel, lead, CAMERA_FOLLOW, dt)
	local focus = rootPart.Position + Vector3.yAxis * (CAMERA_HEIGHT * scale) + camOffset

	camShoulder, camShoulderVel = spring(camShoulder, camShoulderVel, if mode == "ShiftLock" then SHIFTLOCK_OFFSET * scale else 0, 12, dt)
	camDist, camDistVel = spring(camDist, camDistVel, zoom * scale, 10, dt)
	local toEye = camRot.RightVector * camShoulder - camRot.LookVector * camDist
	local eye = focus + toEye
	-- pull in at once when something is in the way, ease back out afterwards
	local hit = workspace:Spherecast(focus, 0.7, toEye, worldParams)
	if hit then
		local d = math.max(hit.Distance, 0.5)
		eye = focus + toEye.Unit * d
		if d < camDist then
			camDist, camDistVel = d, 0
		end
	end

	-- a wider view at high speed
	local over = math.clamp((vel.Magnitude - SWIM_SPEED * 0.9) / (DASH_SPEED - SWIM_SPEED * 0.9), 0, 1)
	camFov, camFovVel = spring(camFov, camFovVel, CAMERA_FOV + CAMERA_FOV_SPEED * over, 6, dt)
	camera.FieldOfView = camFov
	camera.CFrame = CFrame.new(eye + ClientState.shakeOffset()) * camRot
	camera.Focus = CFrame.new(focus)
	fadeFish((eye - focus).Magnitude / scale)
end

-- hooked: a side view of the fish thrashing on the line, framed from where it hangs (the fish itself jerks
-- around, so the camera never looks at it directly) and eased in instead of cut to
local function hookedCamera(dt: number)
	local rootPart = root :: BasePart
	local scale = scaleOf()
	local hang = if hookView and typeof(hookView.hang) == "Vector3" then hookView.hang else rootPart.Position
	local toFisherman = Vector3.xAxis
	local fisherman = hookView and hookView.fisherman
	if typeof(fisherman) == "Instance" and fisherman:IsA("Model") and fisherman.PrimaryPart then
		local d = (fisherman.PrimaryPart.Position - hang) * Vector3.new(1, 0, 1)
		if d.Magnitude > 0.1 then
			toFisherman = d.Unit
		end
	end
	local side = Vector3.yAxis:Cross(toFisherman)
	local eye = hang + side * (11 * scale) + Vector3.yAxis * (2.5 * scale)
	cutCF = (cutCF or camera.CFrame):Lerp(CFrame.lookAt(eye, hang), expK(5, dt))
	camera.CFrame = (cutCF :: CFrame) + ClientState.shakeOffset() * 2
	camera.Focus = CFrame.new(hang)
	lastRootPos = rootPart.Position
end

-- back from the hook: orbit angles from the current view, the focus offset absorbs the jump
local function leaveCutscene()
	local rootPart = root :: BasePart
	local scale = scaleOf()
	local cf = camera.CFrame
	local look = cf.LookVector
	yaw = flatYaw(look)
	pitch = math.clamp(math.asin(math.clamp(look.Y, -1, 1)), -1.35, 1.35)
	camDist, camDistVel = zoom * scale, 0
	camOffset = cf.Position + look * camDist - (rootPart.Position + Vector3.yAxis * (CAMERA_HEIGHT * scale))
	camOffsetVel = Vector3.zero
	lastRootPos = rootPart.Position
	cutCF, hookView = nil, nil
	vel = Vector3.zero
	travel = rootPart.CFrame.LookVector
	heading = rootPart.CFrame.Rotation
	lastFlatYaw = flatYaw(travel)
	dashUntil, stunUntil, recoverUntil, leap, autoCam = 0, 0, 0, nil, nil
	wasInWater = true
end

-- ------------------------------------------------------------------------------------------ per frame
local function publishSwim(dt: number)
	phase = (phase + dt * (0.7 + 1.6 * math.min(intensity, 1.3)) / NAGE_LOOP) % 1
	ClientState.swimIntensity = intensity
	ClientState.swimPhase = phase
end

local function step(dt: number)
	if not alive() then
		if driving then
			releaseControl(player.Character)
		end
		return
	end
	dt = math.min(dt, 0.1) -- a hitch never throws the fish across the map
	local character = character :: Model
	local rootPart = root :: BasePart
	camera.CameraType = Enum.CameraType.Scriptable
	local uiOpen = ClientState.uiOpen()
	UserInputService.MouseBehavior = if uiOpen then Enum.MouseBehavior.Default else Enum.MouseBehavior.LockCenter
	UserInputService.MouseIconEnabled = uiOpen
	local mode = moveMode()
	crosshair.Visible = mode == "ShiftLock" and not uiOpen

	if character:GetAttribute("Caught") then
		wasCaught = true
		setIntensity(1.3, dt)
		publishSwim(dt)
		hookedCamera(dt)
		return
	end
	if wasCaught then
		wasCaught = false
		leaveCutscene()
	end

	local clock = os.clock()
	applyAutoCamera(dt, clock)
	if rootPart.Anchored then
		publishSwim(dt)
		updateCamera(dt, mode)
		return
	end

	local camRot = CFrame.fromEulerAnglesYXZ(pitch, yaw, 0)
	local factor = speedFactor()
	local move = if uiOpen then Vector2.zero else moveInput()
	local vertical = if uiOpen or mode == "CameraOnly" then 0 else verticalInput()
	local intent = readIntent(mode, camRot, move, vertical)
	local inWater, depth, normal = waterState(rootPart.Position)

	if clock < stunUntil then
		stepStun(dt, inWater)
	elseif leap and stepLeap(dt, clock) then
		-- the arc (or the crash that ended it) owns this frame
	elseif clock < dashUntil then
		stepDash(dt, camRot.LookVector, factor, depth)
	elseif inWater then
		if not wasInWater and vel.Y < -12 then
			-- fell back in (not from a leap)
			Remotes.Splash:FireServer(surfacePoint(rootPart.Position))
		end
		stepSwim(dt, clock, intent, depth, normal, factor)
	else
		stepAir(dt, clock, intent, factor)
	end
	if not leap then
		wasInWater = inWater
	end

	local align = swimAlign :: AlignOrientation
	align.CFrame = heading
	publishSwim(dt)
	updateCamera(dt, mode)
end

RunService:BindToRenderStep("FishController", Enum.RenderPriority.Camera.Value + 1, step)

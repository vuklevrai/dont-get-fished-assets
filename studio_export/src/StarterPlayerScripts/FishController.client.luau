-- Swims the local player's fish: camera-relative 3D movement, the ability, leaps and stuns.
-- W/A/S/D move relative to where the camera looks, Space = up, Ctrl/C = down,
-- Q or right click = ability (dash). Only fish characters are driven here; on the ship the avatar
-- keeps Roblox's own controls and camera.
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

local character: Model?, root: BasePart?, humanoid: Humanoid?
local swimVelocity: LinearVelocity?, swimAlign: AlignOrientation?
local driving = false -- true while this script owns the camera and the mouse
local yaw, pitch = 0, -0.15
local zoom = Config.CAMERA_DISTANCE
local velocity = Vector3.zero
local heading = CFrame.identity
local lastYaw, roll = 0, 0
local wasInWater = true
local lastFlop = 0
local fishParts: { BasePart } = {}
local fade = 0

-- action state
local dashUntil, dashDir = 0, Vector3.zero
local stunUntil = 0
local leap = nil -- { t0, origin, dir, distance }
local lastLeap = 0
local diveBoostAt = 0

local rayParams = RaycastParams.new()
rayParams.FilterType = Enum.RaycastFilterType.Exclude
rayParams.IgnoreWater = true

local function serverNow()
	return workspace:GetServerTimeNow()
end

local function speedFactor(): number
	return character and character:GetAttribute("SpeedFactor") or 1
end

-- fish never play the avatar's footstep / swim sounds
local function silence(d: Instance)
	if d:IsA("Sound") then
		d:Destroy()
	end
end

local function releaseControl(subject: Model?)
	character, root, humanoid, swimVelocity, swimAlign = nil, nil, nil, nil, nil
	if not driving then
		return
	end
	driving = false
	UserInputService.MouseBehavior = Enum.MouseBehavior.Default
	UserInputService.MouseIconEnabled = true
	camera.CameraType = Enum.CameraType.Custom
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
	yaw = math.atan2(-look.X, -look.Z)
	pitch = -0.15
	heading = root.CFrame.Rotation
	lastYaw = yaw
	velocity = Vector3.zero
	dashUntil, stunUntil, leap = 0, 0, nil
	rayParams.FilterDescendantsInstances = { newCharacter }
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
	camera.CameraType = Enum.CameraType.Scriptable
	driving = true
end

player.CharacterAdded:Connect(onCharacter)
if player.Character then
	task.spawn(onCharacter, player.Character)
end

-- ------------------------------------------------------------------------------------------ input
local function rotateCamera(dx: number, dy: number)
	yaw -= dx
	pitch = math.clamp(pitch - dy, -1.35, 1.35)
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
	local camRot = CFrame.fromEulerAnglesYXZ(pitch, yaw, 0)
	dashDir = camRot.LookVector
	dashUntil = os.clock() + Config.DASH_TIME
	character:SetAttribute("DashStart", serverNow())
	character:SetAttribute("AbilityReadyAt", serverNow() + (character:GetAttribute("AbilityCooldown") or 6))
	Remotes.UseAbility:FireServer(dashDir)
end

UserInputService.InputBegan:Connect(function(input, processed)
	if not driving or ClientState.uiOpen() then
		return
	end
	if input.UserInputType == Enum.UserInputType.MouseButton2 or (input.KeyCode == Enum.KeyCode.Q and not processed) then
		useAbility()
	end
end)

UserInputService.InputChanged:Connect(function(input, processed)
	if not driving or ClientState.uiOpen() then
		return
	end
	if input.UserInputType == Enum.UserInputType.MouseMovement then
		rotateCamera(input.Delta.X * Config.MOUSE_SENSITIVITY, input.Delta.Y * Config.MOUSE_SENSITIVITY)
	elseif input.UserInputType == Enum.UserInputType.MouseWheel then
		zoom = math.clamp(zoom - input.Position.Z * 2, Config.CAMERA_MIN_DISTANCE, Config.CAMERA_MAX_DISTANCE)
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

-- ------------------------------------------------------------------------------------------ server pushes
Remotes.Knockback.OnClientEvent:Connect(function(kind: string, impulse: Vector3, duration: number)
	if not root then
		return
	end
	if kind == "DashHit" then
		dashUntil = 0
		velocity *= 0.3
	elseif kind == "Stun" then
		dashUntil = 0
		leap = nil
		stunUntil = math.max(stunUntil, os.clock() + duration)
		velocity = impulse
		root.AssemblyLinearVelocity = impulse
		root.AssemblyAngularVelocity = Vector3.new(math.random() - 0.5, math.random() - 0.5, math.random() - 0.5) * 16
	end
end)

-- ------------------------------------------------------------------------------------------ per frame
local function alive(): boolean
	return root ~= nil and root.Parent ~= nil and humanoid ~= nil and humanoid.Health > 0
end

local function orient(look: Vector3, dt: number)
	local flat = Vector2.new(look.X, look.Z)
	if flat.Magnitude < 1e-3 then
		flat = Vector2.new(heading.LookVector.X, heading.LookVector.Z)
	end
	local ly = math.clamp(look.Y, -Config.MAX_PITCH, Config.MAX_PITCH)
	local f = flat.Unit * math.sqrt(1 - ly * ly)
	look = Vector3.new(f.X, ly, f.Y)
	local headingYaw = math.atan2(-look.X, -look.Z)
	local turn = (headingYaw - lastYaw + math.pi) % (2 * math.pi) - math.pi
	lastYaw = headingYaw
	local targetRoll = math.clamp(turn / math.max(dt, 1e-3) * Config.BANK, -Config.MAX_BANK, Config.MAX_BANK)
	roll += (targetRoll - roll) * (1 - math.exp(-6 * dt))
	heading = CFrame.lookAt(Vector3.zero, look) * CFrame.Angles(0, 0, roll)
end

local function updateCamera(camRot: CFrame)
	local focus = root.Position + Vector3.new(0, Config.CAMERA_HEIGHT, 0)
	local offset = -camRot.LookVector * zoom
	local hit = workspace:Spherecast(focus, 0.7, offset, rayParams)
	local distance = hit and math.max(hit.Distance, 0.5) or zoom
	camera.CFrame = CFrame.new(focus - camRot.LookVector * distance + ClientState.shakeOffset()) * camRot
	camera.Focus = CFrame.new(focus)
	local newFade = math.clamp((5 - distance) / 3, 0, 0.9)
	if math.abs(newFade - fade) > 0.01 then
		fade = newFade
		for _, p in fishParts do
			if not character:GetAttribute("Invisible") then
				p.LocalTransparencyModifier = fade
			end
		end
	end
end

-- caught on a hook: a side view of the fish thrashing on the line
local function cutsceneCamera()
	local fisherman = character:GetAttribute("CaughtBy")
	local side = root.CFrame.RightVector
	local focus = root.Position
	local eye = focus + side * 11 + Vector3.new(0, 2.5, 0)
	camera.CFrame = CFrame.lookAt(eye + ClientState.shakeOffset() * 2, focus)
	camera.Focus = CFrame.new(focus)
end

local function step(dt: number)
	if not alive() then
		if driving then
			releaseControl(player.Character)
		end
		return
	end
	local root = root :: BasePart
	camera.CameraType = Enum.CameraType.Scriptable
	local uiOpen = ClientState.uiOpen()
	UserInputService.MouseBehavior = uiOpen and Enum.MouseBehavior.Default or Enum.MouseBehavior.LockCenter
	UserInputService.MouseIconEnabled = uiOpen

	if character:GetAttribute("Caught") then
		cutsceneCamera()
		return
	end

	local camRot = CFrame.fromEulerAnglesYXZ(pitch, yaw, 0)
	local clock = os.clock()
	local factor = speedFactor()
	local force = Config.SWIM_FORCE
	local y = root.Position.Y
	local move = uiOpen and Vector2.zero or moveInput()
	local vertical = uiOpen and 0 or verticalInput()
	local dir = camRot.LookVector * move.Y + camRot.RightVector * move.X + Vector3.yAxis * vertical
	if dir.Magnitude > 1 then
		dir = dir.Unit
	end
	local swimSpeed = Config.SWIM_SPEED * factor
	-- right after diving back in, the fish keeps a fading extra speed
	local boost = 1
	local sinceDive = clock - diveBoostAt
	if sinceDive < Config.DIVE_BOOST_TIME then
		boost = 1 + (Config.DIVE_BOOST - 1) * (1 - sinceDive / Config.DIVE_BOOST_TIME)
	end
	local target = dir * swimSpeed * boost
	local look: Vector3? = nil

	if clock < stunUntil then
		-- tumbling: no control, the water slows the fish down
		swimAlign.Enabled = false
		swimVelocity.MaxAxesForce = Vector3.one * force * 0.012
		swimVelocity.VectorVelocity = Vector3.zero
		velocity = root.AssemblyLinearVelocity
		updateCamera(camRot)
		return
	end
	swimAlign.Enabled = true

	if leap then
		-- fixed arc out of the water and back in
		local f = (clock - leap.t0) / Config.LEAP_TIME
		if f >= 1 then
			leap = nil
			diveBoostAt = clock
			Remotes.Splash:FireServer(Vector3.new(root.Position.X, Config.WATER_LEVEL, root.Position.Z))
			wasInWater = true
		else
			local h = Config.LEAP_HEIGHT
			local v = leap.dir * (leap.distance / Config.LEAP_TIME) + Vector3.yAxis * (4 * h * (1 - 2 * f) / Config.LEAP_TIME)
			swimVelocity.MaxAxesForce = Vector3.one * force
			swimVelocity.VectorVelocity = v
			velocity = v
			orient(v.Unit, dt)
			swimAlign.CFrame = heading
			updateCamera(camRot)
			return
		end
	end

	if clock < dashUntil then
		-- dash: full speed along the aim; slamming into the map stuns us
		local v = dashDir * Config.DASH_SPEED * factor
		local hit = workspace:Spherecast(root.Position, 0.9 * character:GetScale(), dashDir * (v.Magnitude * dt + 2.4 * character:GetScale()), rayParams)
		local blocker = hit and hit.Instance:FindFirstAncestorWhichIsA("Model")
		if hit and not (blocker and CollectionService:HasTag(blocker, Config.FISH_TAG)) then
			dashUntil = 0
			stunUntil = clock + Config.DASH_WALL_STUN
			velocity = -dashDir * 12
			root.AssemblyLinearVelocity = velocity
			root.AssemblyAngularVelocity = Vector3.new(math.random() - 0.5, math.random() - 0.5, math.random() - 0.5) * 12
			ClientState.shake(0.35, 0.25)
			updateCamera(camRot)
			return
		end
		velocity = velocity:Lerp(v, 1 - math.exp(-14 * dt))
		swimVelocity.MaxAxesForce = Vector3.one * force
		swimVelocity.VectorVelocity = velocity
		orient(dashDir, dt)
		swimAlign.CFrame = heading
		updateCamera(camRot)
		return
	end

	-- hysteresis around the surface: control is kept until the fish is clearly out,
	-- and only regained once it is back under
	local inWater = y < Config.WATER_LEVEL + 0.4 and (wasInWater or y < Config.WATER_LEVEL - 0.2)
	if inWater then
		velocity = velocity:Lerp(target, 1 - math.exp(-Config.ACCELERATION * dt))
		local aim = velocity.Magnitude > 0.1 and velocity.Unit or heading.LookVector
		local nearSurface = y > Config.WATER_LEVEL - 1.6
		if nearSurface and aim.Y > Config.LEAP_MIN_PITCH and velocity.Y > Config.LEAP_MIN_SPEED * 0.5
			and velocity.Magnitude > Config.LEAP_MIN_SPEED and clock - lastLeap > Config.LEAP_COOLDOWN then
			-- pointing up into the surface: leap along a fixed arc
			local flat = Vector3.new(aim.X, 0, aim.Z)
			flat = flat.Magnitude > 0.05 and flat.Unit or Vector3.new(heading.LookVector.X, 0, heading.LookVector.Z).Unit
			leap = { t0 = clock, dir = flat, distance = Config.LEAP_DISTANCE * factor }
			lastLeap = clock
			Remotes.Splash:FireServer(Vector3.new(root.Position.X, Config.WATER_LEVEL, root.Position.Z))
		elseif nearSurface and velocity.Y > 0 then
			-- otherwise stay just under the surface
			local ceiling = Config.WATER_LEVEL - 1.1
			velocity = Vector3.new(velocity.X, math.min(velocity.Y, (ceiling - y) * 6), velocity.Z)
		end
		swimVelocity.MaxAxesForce = Vector3.one * force
		swimVelocity.VectorVelocity = velocity
	else
		-- stranded on land: Space makes the fish flop toward where it is steered
		local grounded = workspace:Raycast(root.Position, Vector3.new(0, -1.3 * character:GetScale(), 0), rayParams) ~= nil
		if grounded and vertical > 0 and clock - lastFlop > Config.FLOP_COOLDOWN then
			lastFlop = clock
			local flat = Vector3.new(target.X, 0, target.Z)
			flat = flat.Magnitude > 0.1 and flat.Unit or Vector3.zero
			root.AssemblyLinearVelocity = flat * Config.FLOP_FORWARD + Vector3.yAxis * Config.FLOP_UP
		end
		velocity = root.AssemblyLinearVelocity
		local steer = force * Config.AIR_STEER
		swimVelocity.MaxAxesForce = Vector3.new(steer, 0, steer)
		swimVelocity.VectorVelocity = Vector3.new(target.X * 0.5, 0, target.Z * 0.5)
	end
	wasInWater = inWater

	-- orientation: face the swim direction (or keep facing forward when backpedalling), bank into turns
	if ClientState.backpedal and move.Y < 0 and move.X == 0 then
		look = Vector3.new(camRot.LookVector.X, 0, camRot.LookVector.Z)
	elseif velocity.Magnitude > 1.5 then
		look = velocity.Unit
	end
	if look and look.Magnitude > 1e-3 then
		orient(look.Unit, dt)
	else
		local lv = heading.LookVector
		local flat = Vector3.new(lv.X, 0, lv.Z)
		if flat.Magnitude > 1e-3 then
			roll *= math.exp(-4 * dt)
			heading = heading:Lerp(CFrame.lookAt(Vector3.zero, flat.Unit), 1 - math.exp(-2 * dt))
		end
	end
	swimAlign.CFrame = heading
	updateCamera(camRot)
end

RunService:BindToRenderStep("FishController", Enum.RenderPriority.Camera.Value + 1, step)

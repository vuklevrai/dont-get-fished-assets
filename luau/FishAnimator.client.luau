-- Plays the fish animations exported from Blender (FishAnims): "nage" while swimming (faster with speed),
-- "repos" when idle, "attaque" when the fish dashes, and a frantic swim while caught on a hook.
-- The local player's fish follows FishController's swim intensity and stroke phase (ClientState), so the tail
-- beats with the speed surges; every other fish is driven by its speed.
local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame:WaitForChild("Config"))
local ClientState = require(FishGame:WaitForChild("ClientState"))
local FishSpecies = require(FishGame:WaitForChild("FishSpecies"))
local animFolder = FishGame:WaitForChild("FishAnims")

local ATTACK_SPEED = 1.6 -- the 1.8 s attack plays in about a second
local clips = {}

local function clipsFor(model: Model)
	local species = FishSpecies[model:GetAttribute("Species")]
	local name = species and species.Model or "Bonite"
	if not clips[name] then
		local module = animFolder:FindFirstChild(name)
		clips[name] = module and require(module) or false
	end
	return clips[name] or nil
end

-- pose of one joint at time t (seconds) of a looping or clamped clip
local function sample(anim, joint: string, t: number, loop: boolean): CFrame?
	local rows = anim.joints[joint]
	if not rows then
		return nil
	end
	local n = anim.frames
	local f = t * 30
	if loop then
		f %= (n - 1)
	else
		f = math.clamp(f, 0, n - 1)
	end
	local i = math.floor(f)
	local a, b = rows[i + 1], rows[math.min(i + 2, n)]
	local ca = CFrame.new(a[1], a[2], a[3], a[4], a[5], a[6], a[7])
	local cb = CFrame.new(b[1], b[2], b[3], b[4], b[5], b[6], b[7])
	return ca:Lerp(cb, f - i)
end

local fishes = {}

local function track(model: Instance)
	if not model:IsA("Model") or fishes[model] then
		return
	end
	local motors = {}
	local function add(d: Instance)
		if d:IsA("Motor6D") then
			motors[d.Name] = d
		end
	end
	for _, d in model:GetDescendants() do
		add(d)
	end
	local conn = model.DescendantAdded:Connect(add)
	fishes[model] = { motors = motors, swim = math.random() * 3, idle = math.random() * 3, conn = conn,
		lastDash = model:GetAttribute("DashStart") or 0, attackT = nil }
end

CollectionService:GetInstanceAddedSignal(Config.ANIMATED_TAG):Connect(track)
CollectionService:GetInstanceRemovedSignal(Config.ANIMATED_TAG):Connect(function(model)
	local state = fishes[model]
	if state then
		state.conn:Disconnect()
		fishes[model] = nil
	end
end)
for _, model in CollectionService:GetTagged(Config.ANIMATED_TAG) do
	track(model)
end

RunService.PreSimulation:Connect(function(dt)
	for model, state in fishes do
		local root = model.PrimaryPart
		if not root or not model.Parent then
			continue
		end
		local anims = clipsFor(model)
		if not anims then
			continue
		end
		local speed = root.AssemblyLinearVelocity.Magnitude
		local k = math.clamp(speed / (Config.SWIM_SPEED * 1.4), 0, 1)
		local mine = ClientState.swimModel == model
		if mine then
			k = math.clamp(ClientState.swimIntensity, 0, 1.3)
		elseif model:GetAttribute("PreviewSwim") then
			-- menu preview: anchored, but swims in place
			k = 0.55
		end
		local caught = model:GetAttribute("Caught")
		if mine and not caught then
			state.swim = ClientState.swimPhase * anims.anims.nage.length
		else
			state.swim += dt * (caught and 3.5 or (0.7 + 1.6 * k))
		end
		state.idle += dt
		local dashStart = model:GetAttribute("DashStart") or 0
		if dashStart ~= state.lastDash then
			state.lastDash = dashStart
			state.attackT = 0
		end
		local attack = nil
		if state.attackT then
			state.attackT += dt * ATTACK_SPEED
			if state.attackT >= anims.anims.attaque.length then
				state.attackT = nil
			else
				attack = state.attackT
			end
		end
		local scale = model:GetScale()
		local swimWeight = caught and 1 or math.clamp(k * 2.5, 0, 1)
		for name, motor in state.motors do
			local pose
			if attack then
				pose = sample(anims.anims.attaque, name, attack, false)
			else
				local swim = sample(anims.anims.nage, name, state.swim, true)
				local idle = sample(anims.anims.repos, name, state.idle, true)
				if swim and idle then
					pose = idle:Lerp(swim, swimWeight)
				else
					pose = swim or idle
				end
			end
			if pose then
				motor.Transform = pose.Rotation + pose.Position * scale
			end
		end
	end
end)

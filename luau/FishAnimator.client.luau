-- Plays the fish animations exported from Blender (FishAnims): "nage" while swimming (faster with speed),
-- "repos" when idle, and a frantic swim while caught on a hook. Each FishAnims module can also list:
--   triggers  { [attribute] = clip }  one-shot clip when that timestamp attribute changes
--             (default { DashStart = "attaque" }, the bonite's dash);
--   states    { [attribute] = clip }  loop that replaces the swim while the attribute (a server time) is ahead,
--             e.g. RageUntil = "rage" for the prehistoric fish after its time stop;
--   overlays  { [attribute] = clip }  loop on its own joints only, on top of everything, while the attribute is
--             ahead, e.g. BiteArmedUntil = "gueule_ouverte" (the crocodile's open jaws).
-- A fish whose TimeFrozenUntil is ahead keeps its pose (time stop). Every switch cross-fades over FADE seconds.
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

local ATTACK_SPEED = 1.6 -- clips without their own speed (the bonite's 1.8 s attack plays in about a second)
local FADE = 0.12
local DEFAULT_TRIGGERS = { DashStart = "attaque" }
local NONE = {}
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

local function scaled(cf: CFrame, scale: number): CFrame
	return cf.Rotation + cf.Position * scale
end

local function smooth(x: number): number
	return x * x * (3 - 2 * x)
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
		trig = {}, shot = nil, shotT = 0, loopName = nil, loopT = 0, overlayW = {}, overlayT = 0,
		fadeFrom = nil, fadeT = 1 }
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
	local now = workspace:GetServerTimeNow()
	for model, state in fishes do
		local root = model.PrimaryPart
		if not root or not model.Parent then
			continue
		end
		local anims = clipsFor(model)
		if not anims then
			continue
		end
		-- time stop: the pose holds until time resumes
		if (model:GetAttribute("TimeFrozenUntil") or 0) > now then
			continue
		end
		local set = anims.anims
		local switched = false

		-- one-shot clips on timestamp attributes
		for attr, clipName in anims.triggers or DEFAULT_TRIGGERS do
			local v = model:GetAttribute(attr) or 0
			local last = state.trig[attr]
			if last == nil then
				state.trig[attr] = v
			elseif v ~= last then
				state.trig[attr] = v
				if v > 0 and set[clipName] then
					state.shot, state.shotT = clipName, 0
					switched = true
				end
			end
		end
		local shot = nil
		if state.shot then
			local clip = set[state.shot]
			state.shotT += dt * (clip.speed or ATTACK_SPEED)
			if state.shotT >= clip.length then
				state.shot = nil
				switched = true
			else
				shot = clip
			end
		end

		-- species loop replacing the swim (rage)
		local loopName = nil
		for attr, clipName in anims.states or NONE do
			if (model:GetAttribute(attr) or 0) > now and set[clipName] then
				loopName = clipName
			end
		end
		if loopName ~= state.loopName then
			state.loopName, state.loopT = loopName, 0
			switched = true
		end
		local loopClip = loopName and set[loopName]
		if loopClip then
			state.loopT += dt * (loopClip.speed or 1)
		end

		-- overlays fade in and out on their own
		local overlays = {}
		for attr, clipName in anims.overlays or NONE do
			local on = (model:GetAttribute(attr) or 0) > now and set[clipName] ~= nil
			local w = math.clamp((state.overlayW[clipName] or 0) + (on and dt or -dt) / FADE, 0, 1)
			state.overlayW[clipName] = w
			if w > 0 then
				overlays[clipName] = smooth(w)
			end
		end
		state.overlayT += dt

		-- the swim / idle mix (as before)
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
			state.swim = ClientState.swimPhase * set.nage.length
		else
			state.swim += dt * (caught and 3.5 or (0.7 + 1.6 * k))
		end
		state.idle += dt
		local swimWeight = caught and 1 or math.clamp(k * 2.5, 0, 1)

		if switched then
			-- cross-fade from what is on screen now
			local from = {}
			for name, motor in state.motors do
				from[name] = motor.Transform
			end
			state.fadeFrom, state.fadeT = from, 0
		end
		state.fadeT = math.min(1, state.fadeT + dt / FADE)

		local scale = model:GetScale()
		for name, motor in state.motors do
			local pose = shot and sample(shot, name, state.shotT, false)
			if not pose and loopClip and not caught then
				pose = sample(loopClip, name, state.loopT, true)
			end
			if not pose then
				local swim = sample(set.nage, name, state.swim, true)
				local idle = sample(set.repos, name, state.idle, true)
				if swim and idle then
					pose = idle:Lerp(swim, swimWeight)
				else
					pose = swim or idle
				end
			end
			if not pose then
				continue
			end
			pose = scaled(pose, scale)
			for clipName, w in overlays do
				local o = sample(set[clipName], name, state.overlayT, true)
				if o then
					pose = pose:Lerp(scaled(o, scale), w)
				end
			end
			if state.fadeT < 1 and state.fadeFrom and state.fadeFrom[name] then
				pose = state.fadeFrom[name]:Lerp(pose, smooth(state.fadeT))
			end
			motor.Transform = pose
		end
	end
end)

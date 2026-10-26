-- Combat feedback drawn on this client:
--  * dash: speed lines streaming off every dashing fish; for our own dash, full-screen speed lines and a
--    light blur (the controller already widens the field of view with speed);
--  * hit: a fish that loses health flashes red for an instant (Minecraft style);
--  * low health: the screen edges pulse red while our fish has 10 % of its health or less.
local CollectionService = game:GetService("CollectionService")
local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame:WaitForChild("Config"))
local ClientState = require(FishGame:WaitForChild("ClientState"))
local FxAssets = require(FishGame:WaitForChild("FxAssets"))

local player = Players.LocalPlayer

local LOW_HP = 0.1
local FLASH_TIME = 0.22

local gui = Instance.new("ScreenGui")
gui.Name = "ScreenFx"
gui.IgnoreGuiInset = true
gui.ResetOnSpawn = false
gui.DisplayOrder = 5
gui.Parent = player:WaitForChild("PlayerGui")

local function fullScreen(image: string): ImageLabel
	local l = Instance.new("ImageLabel")
	l.Size = UDim2.fromScale(1, 1)
	l.BackgroundTransparency = 1
	l.Image = image
	l.ImageTransparency = 1
	l.ScaleType = Enum.ScaleType.Stretch
	l.Parent = gui
	return l
end

local speedLines = fullScreen(FxAssets.SpeedLinesScreen)
local vignette = fullScreen(FxAssets.LowHpVignette)
local blur = Instance.new("BlurEffect")
blur.Name = "DashBlur"
blur.Size = 0
blur.Parent = Lighting

-- ------------------------------------------------------------------------------------------ dash
local dashLinesUntil = 0

local function lineEmitter(root: BasePart): ParticleEmitter
	local e = root:FindFirstChild("DashLines") :: ParticleEmitter?
	if e then
		return e
	end
	e = Instance.new("ParticleEmitter")
	e.Name = "DashLines"
	e.Texture = FxAssets.SpeedLine
	e.Shape = Enum.ParticleEmitterShape.Box
	e.ShapeStyle = Enum.ParticleEmitterShapeStyle.Surface
	e.EmissionDirection = Enum.NormalId.Back
	e.Orientation = Enum.ParticleOrientation.VelocityParallel
	e.Rotation = NumberRange.new(90)
	e.Size = NumberSequence.new(1.6)
	e.Squash = NumberSequence.new(-1.2)
	e.Speed = NumberRange.new(30, 45)
	e.Lifetime = NumberRange.new(0.18, 0.3)
	e.LightEmission = 1
	e.LightInfluence = 0
	e.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.15), NumberSequenceKeypoint.new(1, 1) })
	e.Rate = 70
	e.Enabled = false
	e.Parent = root
	return e
end

local function onDash(model: Model)
	local root = model.PrimaryPart
	if not root then
		return
	end
	local mine = model == player.Character
	if not ClientState.performance and not (model:GetAttribute("Invisible") and not mine) then
		local e = lineEmitter(root)
		e.Enabled = true
		task.delay(Config.DASH_TIME, function()
			e.Enabled = false
		end)
	end
	if mine then
		dashLinesUntil = os.clock() + Config.DASH_TIME
		speedLines.ImageTransparency = 0.35
		if not ClientState.performance then
			blur.Size = 0
			TweenService:Create(blur, TweenInfo.new(0.08), { Size = 3 }):Play()
			task.delay(Config.DASH_TIME, function()
				TweenService:Create(blur, TweenInfo.new(0.3), { Size = 0 }):Play()
			end)
		end
	end
end

-- ------------------------------------------------------------------------------------------ hit flash
local function flash(model: Model)
	if model:GetAttribute("Invisible") and model ~= player.Character then
		return -- never give an invisible fish away
	end
	local h = model:FindFirstChild("HitFlash") :: Highlight?
	if not h then
		h = Instance.new("Highlight")
		h.Name = "HitFlash"
		h.FillColor = Color3.fromRGB(255, 30, 30)
		h.OutlineTransparency = 1
		h.DepthMode = Enum.HighlightDepthMode.Occluded
		h.Parent = model
	end
	h.FillTransparency = 0.2
	TweenService:Create(h, TweenInfo.new(FLASH_TIME, Enum.EasingStyle.Quad, Enum.EasingDirection.In), { FillTransparency = 1 }):Play()
end

local function track(model: Instance)
	if not model:IsA("Model") then
		return
	end
	local lastDash = model:GetAttribute("DashStart")
	model:GetAttributeChangedSignal("DashStart"):Connect(function()
		local t = model:GetAttribute("DashStart")
		if t and t ~= lastDash then
			lastDash = t
			onDash(model)
		end
	end)
	local humanoid = model:FindFirstChildOfClass("Humanoid") or model:WaitForChild("Humanoid", 5)
	if humanoid then
		local last = humanoid.Health
		humanoid.HealthChanged:Connect(function(hp)
			if hp < last - 0.5 then
				flash(model)
			end
			last = hp
		end)
	end
end
CollectionService:GetInstanceAddedSignal(Config.FISH_TAG):Connect(track)
for _, m in CollectionService:GetTagged(Config.FISH_TAG) do
	task.spawn(track, m)
end

-- ------------------------------------------------------------------------------------------ per frame
local swap = 0
RunService.RenderStepped:Connect(function(dt)
	local t = os.clock()
	-- dash overlay: two versions swapped every 0.05 s so the lines flicker, then a 0.3 s fade
	if t < dashLinesUntil then
		swap += dt
		if swap > 0.05 then
			swap = 0
			speedLines.Image = speedLines.Image == FxAssets.SpeedLinesScreen and FxAssets.SpeedLinesScreenB or FxAssets.SpeedLinesScreen
		end
		speedLines.ImageTransparency = 0.35
	elseif speedLines.ImageTransparency < 1 then
		speedLines.ImageTransparency = math.min(1, speedLines.ImageTransparency + dt / 0.3 * 0.65)
	end
	-- low health: pulse the red edges at ~1.6 Hz
	local character = player.Character
	local humanoid = character and character:GetAttribute("Species") and character:FindFirstChildOfClass("Humanoid")
	if humanoid and humanoid.Health > 0 and humanoid.Health <= humanoid.MaxHealth * LOW_HP then
		local pulse = 0.5 + 0.5 * math.sin(t * 1.6 * math.pi * 2)
		vignette.ImageTransparency = 0.15 + 0.45 * pulse
	else
		vignette.ImageTransparency = 1
	end
end)

-- Client-side visual effects sent by the server (Remotes.Effect), invisibility rendering and bobbing baits.
local CollectionService = game:GetService("CollectionService")
local Debris = game:GetService("Debris")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame:WaitForChild("Config"))
local FxAssets = require(FishGame:WaitForChild("FxAssets"))
local ClientState = require(FishGame:WaitForChild("ClientState"))
local Remotes = FishGame:WaitForChild("Remotes")

local player = Players.LocalPlayer
local fxFolder = Instance.new("Folder")
fxFolder.Name = "LocalEffects"
fxFolder.Parent = workspace

local SPLASH = {
	crown = FishGame:GetAttribute("SplashCrownTexture"), -- 4x4 flipbook rendered in Blender (splash_flipbook.py)
	ring = FishGame:GetAttribute("SplashRingTexture"),
	crownSize = 10,
	waterRow = 0.22, -- height of the water line in the flipbook frames, from the bottom
}

local function anchorPart(position: Vector3): Part
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.Transparency = 1
	p.Size = Vector3.one * 0.2
	p.Position = position
	p.Parent = fxFolder
	return p
end

local function burst(position: Vector3, props, count: number, life: number)
	local holder = anchorPart(position)
	local e = Instance.new("ParticleEmitter")
	e.Enabled = false
	for k, v in props do
		e[k] = v
	end
	e.Parent = holder
	e:Emit(count)
	Debris:AddItem(holder, life)
	return holder
end

-- splash where a fish breaks the surface: a flipbook crown (Blender), a ring of foam and droplets
local function splash(position: Vector3, scale: number)
	scale = scale or 1
	-- flat maps: on the water line; the ball map: the point sent is already on the bubble
	local level = FishGame:GetAttribute("MapWaterLevel") or Config.WATER_LEVEL
	local surface = if FishGame:GetAttribute("MapWaterShape") == "Sphere" then position
		else Vector3.new(position.X, level + 0.15, position.Z)
	local holder = anchorPart(surface)
	if SPLASH.crown then
		-- the billboard is centred on its emitter: lift it so the frames' water line sits on the surface
		local size = SPLASH.crownSize * scale
		local crownHolder = anchorPart(surface + Vector3.new(0, (0.5 - SPLASH.waterRow) * size, 0))
		Debris:AddItem(crownHolder, 1)
		local crown = Instance.new("ParticleEmitter")
		crown.Texture = SPLASH.crown
		crown.FlipbookLayout = Enum.ParticleFlipbookLayout.Grid4x4
		crown.FlipbookMode = Enum.ParticleFlipbookMode.OneShot
		crown.Lifetime = NumberRange.new(0.55)
		crown.Size = NumberSequence.new(size / 2) -- particle Size is the half-width
		crown.Speed = NumberRange.new(0)
		crown.LightEmission = 0
		crown.LightInfluence = 0.15 -- the colours are already toon-shaded in the texture
		crown.Orientation = Enum.ParticleOrientation.FacingCameraWorldUp
		crown.Enabled = false
		crown.Parent = crownHolder
		crown:Emit(1)
	end
	local ring = Instance.new("Part")
	ring.Anchored = true
	ring.CanCollide = false
	ring.CanQuery = false
	ring.CanTouch = false
	ring.Shape = Enum.PartType.Cylinder
	ring.Material = Enum.Material.SmoothPlastic
	ring.Color = Color3.fromRGB(235, 252, 255)
	ring.Transparency = SPLASH.ring and 1 or 0.25
	ring.Size = Vector3.new(0.12, 2 * scale, 2 * scale)
	ring.CFrame = CFrame.new(surface + Vector3.new(0, 0.05, 0)) * CFrame.Angles(0, 0, math.rad(90))
	ring.Parent = fxFolder
	if SPLASH.ring then
		for _, face in { Enum.NormalId.Right, Enum.NormalId.Left } do
			local d = Instance.new("Decal")
			d.Texture = SPLASH.ring
			d.Face = face
			d.Parent = ring
			TweenService:Create(d, TweenInfo.new(0.9), { Transparency = 1 }):Play()
		end
	end
	TweenService:Create(ring, TweenInfo.new(0.9, Enum.EasingStyle.Quad, Enum.EasingDirection.Out),
		{ Size = Vector3.new(0.12, 11 * scale, 11 * scale), Transparency = 1 }):Play()
	Debris:AddItem(ring, 1)
	local drops = Instance.new("ParticleEmitter")
	drops.Enabled = false
	drops.Color = ColorSequence.new(Color3.fromRGB(225, 248, 255))
	drops.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.7 * scale), NumberSequenceKeypoint.new(1, 0.2) })
	drops.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0), NumberSequenceKeypoint.new(1, 0.4) })
	drops.Lifetime = NumberRange.new(0.5, 0.9)
	drops.Speed = NumberRange.new(14 * scale, 24 * scale)
	drops.SpreadAngle = Vector2.new(40, 40)
	drops.EmissionDirection = Enum.NormalId.Top
	drops.Acceleration = Vector3.new(0, -70, 0)
	drops.LightInfluence = 0.5
	drops.Parent = holder
	drops:Emit(math.floor(18 * scale))
	Debris:AddItem(holder, 1.5)
end

local function aura(model: Model, color: Color3, seconds: number)
	if not model or not model.Parent then
		return
	end
	local h = Instance.new("Highlight")
	h.FillColor = color
	h.OutlineColor = color:Lerp(Color3.new(1, 1, 1), 0.5)
	h.FillTransparency = 0.25
	h.OutlineTransparency = 0
	h.DepthMode = Enum.HighlightDepthMode.Occluded
	h.Parent = model
	TweenService:Create(h, TweenInfo.new(seconds, Enum.EasingStyle.Quad, Enum.EasingDirection.In),
		{ FillTransparency = 1, OutlineTransparency = 1 }):Play()
	Debris:AddItem(h, seconds + 0.05)
	if model.PrimaryPart then
		burst(model.PrimaryPart.Position, {
			Color = ColorSequence.new(color), LightEmission = 1, Size = NumberSequence.new(0.6, 0),
			Lifetime = NumberRange.new(0.5, 0.9), Speed = NumberRange.new(6, 12), SpreadAngle = Vector2.new(180, 180),
		}, 24, 1.2)
	end
end

local function impact(position: Vector3, strong: boolean)
	burst(position, {
		Color = ColorSequence.new(Color3.fromRGB(255, 255, 255)), LightEmission = 0.6,
		Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, strong and 1.6 or 0.9), NumberSequenceKeypoint.new(1, 0) }),
		Lifetime = NumberRange.new(0.25, 0.45), Speed = NumberRange.new(10, 20), SpreadAngle = Vector2.new(180, 180),
	}, strong and 26 or 12, 0.8)
end

local function seq(points)
	local keys = {}
	for _, p in points do
		table.insert(keys, NumberSequenceKeypoint.new(p[1], p[2]))
	end
	return NumberSequence.new(keys)
end

-- the fishermen's danger zone: realistic red smoke (Blender volume flipbook) that blooms in 0.2 s
-- around the hook and stays thick until the strike; the hitbox itself is a perfect sphere (server)
local function fogCloud(position: Vector3, duration: number)
	local radius = Config.HOOK_RADIUS
	local life = duration + 0.35
	local holder = anchorPart(position)
	holder.Size = Vector3.one * radius * 1.2
	local half = radius / 0.852 -- the smoke covers ~85 % of a frame; Size is a half-width
	local grow = math.min(0.2 / life, 0.4)
	local main = Instance.new("ParticleEmitter")
	main.Texture = FxAssets.FogFlipbook
	main.FlipbookLayout = Enum.ParticleFlipbookLayout.Grid4x4
	main.FlipbookMode = Enum.ParticleFlipbookMode.Loop
	main.FlipbookFramerate = NumberRange.new(12)
	main.FlipbookStartRandom = true
	main.Orientation = Enum.ParticleOrientation.FacingCamera
	main.LightInfluence = 0.6
	main.LightEmission = 0.1
	main.Lifetime = NumberRange.new(life)
	main.Speed = NumberRange.new(0)
	main.Rotation = NumberRange.new(-25, 25)
	main.Size = seq({ { 0, half * 0.55 }, { grow, half }, { 1, half * 1.04 } })
	main.Transparency = seq({ { 0, 0.6 }, { grow * 0.75, 0 }, { 1 - 0.3 / life, 0 }, { 1, 1 } })
	main.Enabled = false
	-- on an attachment the cloud is born exactly at the hook (a part would scatter it in its volume)
	local centre = Instance.new("Attachment")
	centre.Parent = holder
	main.Parent = centre
	main:Emit(1)
	if not ClientState.performance then
		-- a second, turned layer and loose puffs give the cloud its depth
		local back = main:Clone()
		back.Parent = centre
		back:Emit(1)
		local puffs = Instance.new("ParticleEmitter")
		puffs.Texture = FxAssets.FogPuff
		puffs.Shape = Enum.ParticleEmitterShape.Sphere
		puffs.ShapeStyle = Enum.ParticleEmitterShapeStyle.Volume
		puffs.Size = seq({ { 0, 3 }, { 0.3, 7 }, { 1, 9 } })
		puffs.Transparency = seq({ { 0, 1 }, { 0.2, 0.35 }, { 0.8, 0.5 }, { 1, 1 } })
		puffs.Lifetime = NumberRange.new(0.8, 1)
		puffs.Rotation = NumberRange.new(0, 360)
		puffs.RotSpeed = NumberRange.new(-25, 25)
		puffs.Speed = NumberRange.new(0.5, 2)
		puffs.SpreadAngle = Vector2.new(180, 180)
		puffs.LightInfluence = 0.6
		puffs.Enabled = false
		puffs.Parent = holder
		puffs:Emit(8)
		task.delay(duration * 0.5, function()
			if puffs.Parent then
				puffs:Emit(5)
			end
		end)
	end
	Debris:AddItem(holder, life + 1.2)
end

-- Titan power-up: a cartoon lightning bolt strikes the fish (Attack on Titan style) with a shock ring
local function titanStrike(model: Model?, position: Vector3)
	local size = 44 -- studs across one frame
	-- the bolt hits at (0.5, 0.86) of the frame: lift the billboard so that point lands on the fish
	local holder = anchorPart(position + Vector3.new(0, 0.36 * size, 0))
	local bolt = Instance.new("ParticleEmitter")
	bolt.Texture = FxAssets.TitanLightning
	bolt.FlipbookLayout = Enum.ParticleFlipbookLayout.Grid4x4
	bolt.FlipbookMode = Enum.ParticleFlipbookMode.OneShot
	bolt.Lifetime = NumberRange.new(0.6)
	bolt.Size = NumberSequence.new(size / 2)
	bolt.Speed = NumberRange.new(0)
	bolt.LightEmission = 1
	bolt.LightInfluence = 0
	bolt.Orientation = Enum.ParticleOrientation.FacingCameraWorldUp
	bolt.Enabled = false
	bolt.Parent = holder
	bolt:Emit(1)
	Debris:AddItem(holder, 1)
	local ring = Instance.new("Part")
	ring.Anchored = true
	ring.CanCollide = false
	ring.CanQuery = false
	ring.CanTouch = false
	ring.Transparency = 1
	ring.Size = Vector3.new(1, 0.1, 1)
	ring.CFrame = CFrame.new(position)
	ring.Parent = fxFolder
	for _, face in { Enum.NormalId.Top, Enum.NormalId.Bottom } do
		local d = Instance.new("Decal")
		d.Texture = FxAssets.TitanFlashRing
		d.Face = face
		d.Parent = ring
		TweenService:Create(d, TweenInfo.new(0.35), { Transparency = 1 }):Play()
	end
	TweenService:Create(ring, TweenInfo.new(0.35, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { Size = Vector3.new(40, 0.1, 40) }):Play()
	Debris:AddItem(ring, 0.5)
	if model then
		aura(model, Color3.fromRGB(255, 150, 30), 1.2)
	end
	if model and model == player.Character then
		ClientState.shake(1.2, 0.5)
	end
end

Remotes.Effect.OnClientEvent:Connect(function(kind, model, a, b)
	if kind == "Fog" then
		fogCloud(a, b)
	elseif kind == "Titan" then
		titanStrike(model, a)
	elseif kind == "Splash" then
		splash(a, b)
	elseif kind == "Hit" then
		impact(a, true)
	elseif kind == "Bump" then
		impact(a, false)
	elseif kind == "Aura" then
		aura(model, a, b)
	elseif kind == "LevelUp" then
		aura(model, Color3.fromRGB(255, 210, 50), 1)
	elseif kind == "EnemySpawn" and model and model.PrimaryPart then
		burst(model.PrimaryPart.Position, {
			Color = ColorSequence.new(Color3.fromRGB(80, 170, 255)), LightEmission = 1, Size = NumberSequence.new(0.5, 0),
			Lifetime = NumberRange.new(1, 1.8), Speed = NumberRange.new(1, 4), SpreadAngle = Vector2.new(180, 180),
			Shape = Enum.ParticleEmitterShape.Sphere,
		}, 40, 2.5)
	elseif kind == "Poof" then
		burst(a, {
			Texture = "rbxasset://textures/particles/smoke_main.dds", Color = ColorSequence.new(Color3.fromRGB(230, 240, 255)),
			Size = NumberSequence.new(2, 5), Transparency = NumberSequence.new(0.3, 1), Lifetime = NumberRange.new(0.6, 1),
			Speed = NumberRange.new(2, 6), SpreadAngle = Vector2.new(180, 180),
		}, 14, 1.5)
	end
end)

-- invisibility: the owner sees a ghost of their fish, everyone else sees nothing
local function applyInvisible(model: Model)
	local invisible = model:GetAttribute("Invisible") == true
	local mine = model == player.Character
	local amount = invisible and (mine and 0.65 or 1) or 0
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.LocalTransparencyModifier = amount
		elseif d:IsA("BillboardGui") then
			d.Enabled = not (invisible and not mine)
		end
	end
end

local function trackFish(model: Instance)
	if model:IsA("Model") then
		model:GetAttributeChangedSignal("Invisible"):Connect(function()
			applyInvisible(model)
		end)
		if model:GetAttribute("Invisible") then
			applyInvisible(model)
		end
	end
end
CollectionService:GetInstanceAddedSignal(Config.FISH_TAG):Connect(trackFish)
for _, m in CollectionService:GetTagged(Config.FISH_TAG) do
	trackFish(m)
end

-- power-up baits bob and spin
local baits = {}
local function trackBait(model: Instance)
	if model:IsA("Model") then
		baits[model] = { base = nil, phase = math.random() * 6 }
	end
end
CollectionService:GetInstanceAddedSignal("PowerUp"):Connect(trackBait)
CollectionService:GetInstanceRemovedSignal("PowerUp"):Connect(function(m)
	baits[m] = nil
end)
for _, m in CollectionService:GetTagged("PowerUp") do
	trackBait(m)
end
RunService.RenderStepped:Connect(function()
	local t = os.clock()
	local serverNow = workspace:GetServerTimeNow()
	for model, state in baits do
		if model.Parent and model.PrimaryPart then
			state.base = state.base or model:GetPivot()
			model:PivotTo(state.base * CFrame.new(0, math.sin(t * 2.2 + state.phase) * 0.6, 0) * CFrame.Angles(0, t * 1.4, 0))
			-- about to vanish: blink, faster and faster
			local left = (model:GetAttribute("ExpiresAt") or math.huge) - serverNow
			local hidden = false
			if left < Config.POWERUP_BLINK then
				local rate = 4 + (Config.POWERUP_BLINK - left) * 3
				hidden = math.sin(t * rate * math.pi * 2) < 0
			end
			if hidden ~= state.hidden then
				state.hidden = hidden
				for _, d in model:GetDescendants() do
					if d:IsA("BasePart") then
						d.LocalTransparencyModifier = hidden and 0.85 or 0
					elseif d:IsA("BillboardGui") then
						d.Enabled = not hidden
					end
				end
			end
		end
	end
end)

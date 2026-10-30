-- Client effects of the species abilities (ModuleScript, ReplicatedStorage.FishGame.AbilityFx).
-- Effects.client calls AbilityFx.handle(kind, model, data) for every kind listed in AbilityFx.kinds:
--   "TimeStop"   stopper, { center, radius, duration, windup }: JoJo style. Purple motes rush into the fish during
--                the windup; then a sphere bursts out to `radius` with a shockwave ring, the screen flashes inverted
--                and the world turns grey-violet for anyone inside (and for the stopper); a clock above the fish
--                ticks every second, "menacing" katakana float around it, frozen fish turn into grey statues and
--                the particles inside the sphere hang in mid-air.
--   "TimeHit"    victim, { position }: a hit landed on a frozen fish; an impact star hangs in place until time
--                resumes (the server applies every stored hit at that moment).
--   "TimeResume" stopper, { center, radius }: the sphere collapses back into the fish, the colours come back.
--   "BiteArmed"  croc, { radius, duration }: swirling slow zone around the crocodile while its jaws are open.
--   "Slowed"     fish, { duration }: a snail over a slowed fish.
--   "Chomp"      croc, { victim, position }: giant jaws slam shut on the prey, impact burst, "CHOMP!", shake.
-- Performance mode (ClientState.performance): fewer particles, no blur.
-- Needs FxAssets keys TimeStopClock, TimeStopHand, MenacingGo, AngerVein, BiteJaw, ImpactStar, SlowRing, SlowIcon
-- (any left at rbxassetid://0 is drawn with plain shapes or text) and uses ShockwaveRing (brief 2) when uploaded.
local CollectionService = game:GetService("CollectionService")
local Debris = game:GetService("Debris")
local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame:WaitForChild("Config"))
local FxAssets = require(FishGame:WaitForChild("FxAssets"))
local ClientState = require(FishGame:WaitForChild("ClientState"))

local player = Players.LocalPlayer

local AbilityFx = {}
AbilityFx.kinds = { TimeStop = true, TimeHit = true, TimeResume = true, BiteArmed = true, Slowed = true, Chomp = true }

local TS = {
	shell = Color3.fromRGB(150, 70, 255),
	core = Color3.fromRGB(40, 0, 90),
	gold = Color3.fromRGB(255, 204, 51),
	-- negative flash, then the stopped world: washed out, violet, a bit harsh
	invert = { Contrast = -2, Saturation = -0.3, Brightness = 0, TintColor = Color3.new(1, 1, 1) },
	grade = { Contrast = 0.22, Saturation = -0.72, Brightness = -0.03, TintColor = Color3.fromRGB(212, 196, 255) },
	invertTime = 0.16,
	expandTime = 0.35,
	collapseTime = 0.3,
	holdTransparency = 0.86, -- the sphere's edge stays faintly visible while time is stopped
	glyphs = 5,
	text = "ZA WARUDO!", -- "" to turn the shout off
	statue = { fill = Color3.fromRGB(176, 170, 204), outline = Color3.fromRGB(240, 236, 255) },
}
local CROC = {
	zone = Color3.fromRGB(70, 200, 140),
	shellTransparency = 0.88,
}
-- optional sound ids (rbxassetid://...), played when set
local SOUNDS = { stop = "", tick = "", resume = "", chomp = "" }

-- --------------------------------------------------------------------------- helpers
local function perf(): boolean
	return ClientState.performance == true
end

local function serverNow(): number
	return workspace:GetServerTimeNow()
end

local function image(key: string): string?
	local id = FxAssets[key]
	if type(id) ~= "string" or id == "" or id == "rbxassetid://0" then
		return nil
	end
	return id
end

local function fxFolder(): Instance
	local folder = workspace:FindFirstChild("LocalEffects")
	if not folder then
		folder = Instance.new("Folder")
		folder.Name = "LocalEffects"
		folder.Parent = workspace
	end
	return folder
end

local function tween(inst: Instance, t: number, props, style: Enum.EasingStyle?, dir: Enum.EasingDirection?)
	local tw = TweenService:Create(inst, TweenInfo.new(t, style or Enum.EasingStyle.Quad, dir or Enum.EasingDirection.Out), props)
	tw:Play()
	return tw
end

local function anchor(position: Vector3): Part
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.Transparency = 1
	p.Size = Vector3.one * 0.2
	p.CFrame = CFrame.new(position)
	p.Parent = fxFolder()
	return p
end

local function ball(position: Vector3, color: Color3, material: Enum.Material, transparency: number): Part
	local p = anchor(position)
	p.Shape = Enum.PartType.Ball
	p.Material = material
	p.Color = color
	p.Transparency = transparency
	p.Size = Vector3.one * 0.4
	return p
end

local function sound(id: string, parent: Instance, volume: number?)
	if id == "" then
		return
	end
	local s = Instance.new("Sound")
	s.SoundId = id
	s.Volume = volume or 0.8
	s.Parent = parent
	s:Play()
	Debris:AddItem(s, 6)
end

local function rootOf(model: Instance?): BasePart?
	if model and model:IsA("Model") and model.Parent then
		return model.PrimaryPart
	end
	return nil
end

local function billboard(adornee: Instance, size: number, offset: Vector3?): BillboardGui
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.fromScale(size, size)
	gui.LightInfluence = 0
	gui.StudsOffset = offset or Vector3.zero
	gui.Adornee = adornee
	gui.ResetOnSpawn = false
	gui.Parent = adornee
	return gui
end

-- a picture (when uploaded) or a fallback label filling a gui
local function picture(parent: Instance, key: string, fallback: string, color: Color3): GuiObject
	local id = image(key)
	if id then
		local l = Instance.new("ImageLabel")
		l.BackgroundTransparency = 1
		l.Size = UDim2.fromScale(1, 1)
		l.Image = id
		l.Parent = parent
		return l
	end
	local t = Instance.new("TextLabel")
	t.BackgroundTransparency = 1
	t.Size = UDim2.fromScale(1, 1)
	t.Text = fallback
	t.TextScaled = true
	t.Font = Enum.Font.FredokaOne
	t.TextColor3 = color
	t.TextStrokeTransparency = 0
	t.TextStrokeColor3 = Color3.fromRGB(20, 8, 30)
	t.Parent = parent
	return t
end

local function fade(gui: GuiObject, t: number)
	if gui:IsA("ImageLabel") then
		tween(gui, t, { ImageTransparency = 1 })
	elseif gui:IsA("TextLabel") then
		tween(gui, t, { TextTransparency = 1, TextStrokeTransparency = 1 })
	end
end

local function pop(gui: GuiObject, peak: number?, t: number?): UIScale
	local s = gui:FindFirstChildOfClass("UIScale") or Instance.new("UIScale")
	s.Scale = 0
	s.Parent = gui
	tween(s, (t or 0.16) * 0.6, { Scale = peak or 1.25 }, Enum.EasingStyle.Back).Completed:Connect(function()
		tween(s, (t or 0.16) * 0.4, { Scale = 1 })
	end)
	return s
end

-- circle outline (shockwave) for when no texture is uploaded
local function ring(parent: Instance, color: Color3, thickness: number): GuiObject
	local id = image("ShockwaveRing")
	if id then
		local l = Instance.new("ImageLabel")
		l.BackgroundTransparency = 1
		l.Size = UDim2.fromScale(1, 1)
		l.Image = id
		l.ImageColor3 = color
		l.Parent = parent
		return l
	end
	local f = Instance.new("Frame")
	f.BackgroundTransparency = 1
	f.Size = UDim2.fromScale(1, 1)
	f.Parent = parent
	Instance.new("UICorner", f).CornerRadius = UDim.new(1, 0)
	local stroke = Instance.new("UIStroke")
	stroke.Color = color
	stroke.Thickness = thickness
	stroke.Parent = f
	return f
end

local function shockwave(position: Vector3, radius: number, color: Color3, t: number)
	local holder = anchor(position)
	local gui = billboard(holder, 0.5)
	local r = ring(gui, color, 6)
	tween(gui, t, { Size = UDim2.fromScale(radius * 2.4, radius * 2.4) }, Enum.EasingStyle.Quart)
	if r:IsA("ImageLabel") then
		tween(r, t, { ImageTransparency = 1 }, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
	else
		tween(r:FindFirstChildOfClass("UIStroke"), t, { Transparency = 1 }, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
	end
	Debris:AddItem(holder, t + 0.1)
end

local function burst(position: Vector3, props, count: number, life: number)
	local holder = anchor(position)
	local e = Instance.new("ParticleEmitter")
	e.Enabled = false
	for k, v in props do
		e[k] = v
	end
	e.Parent = holder
	e:Emit(perf() and math.ceil(count / 2) or count)
	Debris:AddItem(holder, life)
end

-- --------------------------------------------------------------------------- screen grade (shared by stops)
local grade = Instance.new("ColorCorrectionEffect")
grade.Name = "TimeStopGrade"
grade.Enabled = false
grade.Parent = Lighting
local blur = Instance.new("BlurEffect")
blur.Name = "TimeStopBlur"
blur.Size = 0
blur.Parent = Lighting
local graded = 0

local function setGrade(props, t: number): Tween
	grade.Enabled = true
	return tween(grade, t, props)
end

local NEUTRAL = { Contrast = 0, Saturation = 0, Brightness = 0, TintColor = Color3.new(1, 1, 1) }

local function enterStoppedWorld()
	graded += 1
	for k, v in TS.invert do
		grade[k] = v
	end
	grade.Enabled = true
	task.delay(TS.invertTime, function()
		if graded > 0 then
			setGrade(TS.grade, 0.35)
		end
	end)
	if not perf() then
		blur.Size = 0
		tween(blur, 0.12, { Size = 14 }).Completed:Connect(function()
			tween(blur, 0.3, { Size = 0 })
		end)
	end
end

local function leaveStoppedWorld()
	graded = math.max(0, graded - 1)
	if graded > 0 then
		return
	end
	setGrade(NEUTRAL, 0.4).Completed:Connect(function()
		if graded == 0 then
			grade.Enabled = false
		end
	end)
end

-- --------------------------------------------------------------------------- time stop
local stops = {} -- stopper model -> state
local frozenStars = {} -- impact stars waiting for time to resume

local function myFishInside(center: Vector3, radius: number): boolean
	local cam = workspace.CurrentCamera
	if cam and (cam.CFrame.Position - center).Magnitude <= radius then
		return true
	end
	local root = rootOf(player.Character)
	return root ~= nil and (root.Position - center).Magnitude <= radius
end

local function statues(state, on: boolean)
	local t = serverNow()
	for _, model in CollectionService:GetTagged(Config.FISH_TAG) do
		local h = model:FindFirstChild("TimeFrozen")
		local frozen = on and (model:GetAttribute("TimeFrozenUntil") or 0) > t
		if frozen and not h then
			h = Instance.new("Highlight")
			h.Name = "TimeFrozen"
			h.FillColor = TS.statue.fill
			h.FillTransparency = 0.3
			h.OutlineColor = TS.statue.outline
			h.OutlineTransparency = 0.15
			h.DepthMode = Enum.HighlightDepthMode.Occluded
			h.Parent = model
		elseif not frozen and h then
			h:Destroy()
		end
	end
end

local function freezeParticles(state)
	local params = OverlapParams.new()
	params.MaxParts = 400
	local ok, parts = pcall(workspace.GetPartBoundsInRadius, workspace, state.center, state.radius, params)
	if not ok then
		return
	end
	local seen = {}
	for _, part in parts do
		for _, d in part:GetDescendants() do
			if d:IsA("ParticleEmitter") and not seen[d] and d.TimeScale > 0 then
				seen[d] = true
				state.particles[d] = d.TimeScale
				d.TimeScale = 0
			end
		end
	end
end

local function menacingGlyphs(state, root: BasePart, scale: number)
	for n = 1, (perf() and 3 or TS.glyphs) do
		task.delay(0.12 * n, function()
			if not state.alive then
				return
			end
			local a = (n / TS.glyphs) * math.pi * 2 + 0.6
			local offset = Vector3.new(math.cos(a) * 3.2, 1.2 + (n % 2) * 1.6, math.sin(a) * 3.2) * scale
			local gui = billboard(root, 1.6 * scale, offset)
			gui.Name = "Menacing"
			local g = picture(gui, "MenacingGo", "ゴ", Color3.fromRGB(200, 90, 255))
			g.Rotation = (n % 2 == 0) and -12 or 10
			pop(g, 1.35, 0.22)
			table.insert(state.guis, gui)
			table.insert(state.bobbers, { gui = gui, base = offset, phase = n * 1.7, label = g })
		end)
	end
end

local function clock(state, root: BasePart, scale: number)
	local gui = billboard(root, 3.4 * scale, Vector3.new(0, 4.2 * scale, 0))
	gui.Name = "TimeStopClock"
	local face = picture(gui, "TimeStopClock", "", TS.gold)
	if face:IsA("TextLabel") then
		-- no texture: a gold ring
		face.BackgroundTransparency = 0.35
		face.BackgroundColor3 = Color3.fromRGB(42, 18, 80)
		Instance.new("UICorner", face).CornerRadius = UDim.new(1, 0)
		local stroke = Instance.new("UIStroke")
		stroke.Color = TS.gold
		stroke.Thickness = 4
		stroke.Parent = face
	end
	local hand = Instance.new("Frame")
	hand.BackgroundTransparency = 1
	hand.Size = UDim2.fromScale(1, 1)
	hand.Parent = gui
	local handPic = picture(hand, "TimeStopHand", "", TS.gold)
	if handPic:IsA("TextLabel") then
		handPic.Size = UDim2.fromScale(0.08, 0.4)
		handPic.Position = UDim2.fromScale(0.46, 0.1)
		handPic.BackgroundTransparency = 0
		handPic.BackgroundColor3 = TS.gold
	end
	pop(face, 1.2, 0.25)
	state.clock = { gui = gui, face = face, hand = hand }
	table.insert(state.guis, gui)
end

local function shout(text: string)
	if text == "" then
		return
	end
	local screen = Instance.new("ScreenGui")
	screen.Name = "TimeStopShout"
	screen.IgnoreGuiInset = true
	screen.DisplayOrder = 6
	screen.Parent = player:WaitForChild("PlayerGui")
	local label = Instance.new("TextLabel")
	label.AnchorPoint = Vector2.new(0.5, 0.5)
	label.Position = UDim2.fromScale(0.5, 0.3)
	label.Size = UDim2.fromScale(0.7, 0.14)
	label.BackgroundTransparency = 1
	label.Text = text
	label.TextScaled = true
	label.Font = Enum.Font.FredokaOne
	label.TextColor3 = TS.gold
	label.Rotation = -4
	label.Parent = screen
	local stroke = Instance.new("UIStroke")
	stroke.Color = Color3.fromRGB(70, 10, 110)
	stroke.Thickness = 5
	stroke.Parent = label
	pop(label, 1.3, 0.3)
	task.delay(1.1, function()
		tween(label, 0.4, { TextTransparency = 1 })
		tween(stroke, 0.4, { Transparency = 1 })
	end)
	Debris:AddItem(screen, 1.7)
end

local function rage(state, model: Model, root: BasePart, scale: number)
	local h = Instance.new("Highlight")
	h.Name = "Rage"
	h.FillTransparency = 1
	h.OutlineColor = Color3.fromRGB(255, 60, 40)
	h.OutlineTransparency = 0
	h.DepthMode = Enum.HighlightDepthMode.Occluded
	h.Parent = model
	state.rage = h
	local gui = billboard(root, 1.5 * scale, Vector3.new(0, 2.3 * scale, 0))
	gui.Name = "Anger"
	local vein = picture(gui, "AngerVein", "💢", Color3.fromRGB(235, 40, 45))
	pop(vein, 1.4, 0.2)
	table.insert(state.guis, gui)
	state.vein = vein
end

local function startTimeStop(model: Model, data)
	local root = rootOf(model)
	if not root or type(data) ~= "table" then
		return
	end
	local old = stops[model]
	if old then
		old.finish(true)
	end
	local center, radius = data.center or root.Position, data.radius or 36
	local windup, duration = data.windup or 0.5, data.duration or 3
	local scale = model:GetScale()
	local state = { alive = true, guis = {}, bobbers = {}, particles = {}, center = center, radius = radius,
		model = model, inside = false, started = os.clock() }
	stops[model] = state

	-- windup: purple motes rush into the fish from a shell around it (a sphere emitter uses its part's size)
	local shellPart = Instance.new("Part")
	shellPart.Name = "TimeStopCharge"
	shellPart.Transparency = 1
	shellPart.CanCollide = false
	shellPart.CanQuery = false
	shellPart.CanTouch = false
	shellPart.Massless = true
	shellPart.Size = Vector3.one * 9 * scale
	shellPart.CFrame = root.CFrame
	local weld = Instance.new("WeldConstraint")
	weld.Part0 = root
	weld.Part1 = shellPart
	weld.Parent = shellPart
	shellPart.Parent = fxFolder()
	local motes = Instance.new("ParticleEmitter")
	motes.Shape = Enum.ParticleEmitterShape.Sphere
	motes.ShapeStyle = Enum.ParticleEmitterShapeStyle.Surface
	motes.ShapeInOut = Enum.ParticleEmitterShapeInOut.Inward
	motes.Speed = NumberRange.new(10, 14)
	motes.Lifetime = NumberRange.new(0.35, 0.45)
	motes.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.5 * scale), NumberSequenceKeypoint.new(1, 0) })
	motes.Color = ColorSequence.new(Color3.fromRGB(200, 140, 255), TS.shell)
	motes.LightEmission = 1
	motes.Rate = perf() and 40 or 90
	motes.Parent = shellPart
	state.charge = shellPart

	function state.finish(instant: boolean?)
		if not state.alive then
			return
		end
		state.alive = false
		if stops[model] == state then
			stops[model] = nil
		end
		if state.charge then
			state.charge:Destroy()
		end
		if state.shell then
			local shell, core = state.shell, state.core
			if instant then
				shell:Destroy()
				core:Destroy()
			else
				local here = rootOf(model)
				local target = here and here.Position or center
				tween(shell, TS.collapseTime, { Size = Vector3.one * 0.4, CFrame = CFrame.new(target), Transparency = 1 },
					Enum.EasingStyle.Quart, Enum.EasingDirection.In)
				tween(core, TS.collapseTime, { Size = Vector3.one * 0.4, CFrame = CFrame.new(target), Transparency = 1 },
					Enum.EasingStyle.Quart, Enum.EasingDirection.In)
				Debris:AddItem(shell, TS.collapseTime + 0.1)
				Debris:AddItem(core, TS.collapseTime + 0.1)
				task.delay(TS.collapseTime, function()
					shockwave(target, radius * 0.5, Color3.fromRGB(255, 255, 255), 0.4)
				end)
			end
		end
		for _, gui in state.guis do
			for _, d in gui:GetDescendants() do
				if d:IsA("GuiObject") then
					fade(d, 0.25)
				end
			end
			Debris:AddItem(gui, 0.3)
		end
		if state.rage then
			state.rage:Destroy()
		end
		for emitter, ts in state.particles do
			if emitter.Parent then
				emitter.TimeScale = ts
			end
		end
		if state.renderConn then
			state.renderConn:Disconnect()
		end
		statues(state, false)
		if state.inside then
			leaveStoppedWorld()
		end
		for star, _ in frozenStars do
			star.release()
		end
		sound(SOUNDS.resume, workspace.CurrentCamera)
	end

	task.delay(windup, function()
		if not state.alive or not model.Parent then
			return
		end
		local here = rootOf(model)
		if not here then
			state.finish(true)
			return
		end
		center = here.Position
		state.center = center
		if state.charge then
			state.charge:Destroy()
			state.charge = nil
		end
		-- the burst: dark core and violet shell racing out to the radius
		local shell = ball(center, TS.shell, Enum.Material.ForceField, 0)
		local core = ball(center, TS.core, Enum.Material.Neon, 0.55)
		state.shell, state.core = shell, core
		tween(shell, TS.expandTime, { Size = Vector3.one * radius * 2 }, Enum.EasingStyle.Quart)
		tween(core, TS.expandTime, { Size = Vector3.one * radius * 2, Transparency = 0.97 }, Enum.EasingStyle.Quart)
		task.delay(TS.expandTime, function()
			if state.alive then
				tween(shell, 0.5, { Transparency = TS.holdTransparency })
			end
		end)
		shockwave(center, radius, TS.gold, 0.5)
		task.delay(0.08, function()
			shockwave(center, radius * 0.8, TS.shell, 0.45)
		end)
		sound(SOUNDS.stop, here)
		state.inside = myFishInside(center, radius) or model == player.Character
		if state.inside then
			task.delay(TS.expandTime * 0.6, function()
				if state.alive then
					enterStoppedWorld()
				end
			end)
			ClientState.shake(1.4, 0.35)
			if model == player.Character or myFishInside(center, radius) then
				shout(TS.text)
			end
		end
		clock(state, here, scale)
		menacingGlyphs(state, here, scale)
		rage(state, model, here, scale)
		task.delay(TS.expandTime, function()
			if state.alive then
				freezeParticles(state)
			end
		end)

		local lastTick = 0
		local lastScan = 0
		state.renderConn = RunService.RenderStepped:Connect(function()
			if not state.alive then
				return
			end
			local t = os.clock() - state.started - windup
			-- the clock ticks once a second
			local ticks = math.floor(t)
			if state.clock and ticks > lastTick then
				lastTick = ticks
				state.clock.hand.Rotation = ticks * 30
				pop(state.clock.face, 1.12, 0.14)
				sound(SOUNDS.tick, here, 0.5)
			end
			for _, b in state.bobbers do
				b.gui.StudsOffset = b.base + Vector3.new(0, math.sin(t * 2.4 + b.phase) * 0.25 * scale, 0)
				b.label.Rotation = (b.phase % 2 > 1 and -12 or 10) + math.sin(t * 17 + b.phase) * 2.5
			end
			if state.vein then
				local s = state.vein:FindFirstChildOfClass("UIScale")
				if s and t > 0.3 then
					s.Scale = 1 + 0.18 * math.max(0, math.sin(t * 9))
				end
			end
			if os.clock() - lastScan > 0.15 then
				lastScan = os.clock()
				statues(state, true)
			end
		end)
		-- safety net: never stay stopped if the resume never arrives
		task.delay(duration + 1.5, function()
			state.finish(false)
		end)
	end)
end

local function timeHit(data)
	if type(data) ~= "table" or typeof(data.position) ~= "Vector3" then
		return
	end
	local holder = anchor(data.position)
	local gui = billboard(holder, 3)
	gui.AlwaysOnTop = true
	local star = picture(gui, "ImpactStar", "✸", Color3.fromRGB(255, 255, 255))
	star.Rotation = math.random(-20, 20)
	pop(star, 1.3, 0.16)
	local entry = {}
	function entry.release()
		frozenStars[entry] = nil
		if holder.Parent then
			tween(gui, 0.12, { Size = UDim2.fromScale(5, 5) }, Enum.EasingStyle.Back)
			fade(star, 0.25)
			Debris:AddItem(holder, 0.3)
		end
	end
	frozenStars[entry] = true
	task.delay(6, function()
		if frozenStars[entry] then
			entry.release()
		end
	end)
end

-- --------------------------------------------------------------------------- crocodile
local armedFx = {}

local function biteArmed(model: Model, data)
	local root = rootOf(model)
	if not root then
		return
	end
	if armedFx[model] then
		armedFx[model]()
	end
	local radius = (type(data) == "table" and data.radius or 11) * math.max(1, model:GetScale())
	local parts = {}
	local disc
	local id = image("SlowRing")
	disc = anchor(root.Position)
	disc.Size = Vector3.new(radius * 2, 0.05, radius * 2)
	if id then
		local decal = Instance.new("Decal")
		decal.Face = Enum.NormalId.Top
		decal.Texture = id
		decal.Transparency = 0.15
		decal.Parent = disc
		local under = decal:Clone()
		under.Face = Enum.NormalId.Bottom
		under.Parent = disc
	else
		disc.Shape = Enum.PartType.Cylinder
		disc.Size = Vector3.new(0.08, radius * 2, radius * 2)
		disc.Material = Enum.Material.Neon
		disc.Color = CROC.zone
		disc.Transparency = 0.82
	end
	table.insert(parts, disc)
	local shell = ball(root.Position, CROC.zone, Enum.Material.ForceField, 1)
	tween(shell, 0.25, { Size = Vector3.one * radius * 2, Transparency = CROC.shellTransparency }, Enum.EasingStyle.Back)
	table.insert(parts, shell)
	local sucker = Instance.new("ParticleEmitter")
	sucker.Shape = Enum.ParticleEmitterShape.Sphere
	sucker.ShapeStyle = Enum.ParticleEmitterShapeStyle.Surface
	sucker.ShapeInOut = Enum.ParticleEmitterShapeInOut.Inward
	sucker.Speed = NumberRange.new(radius * 0.9, radius * 1.1)
	sucker.Lifetime = NumberRange.new(0.8, 1)
	sucker.Size = NumberSequence.new(0.35, 0.05)
	sucker.Transparency = NumberSequence.new(0.2, 0.8)
	sucker.Color = ColorSequence.new(Color3.fromRGB(190, 255, 220))
	sucker.LightEmission = 0.6
	sucker.Rate = perf() and 20 or 45
	local inner = anchor(root.Position)
	inner.Size = Vector3.one * radius * 1.9
	sucker.Parent = inner
	table.insert(parts, inner)

	local spin = 0
	local conn
	local function stop()
		if not conn then
			return
		end
		conn:Disconnect()
		conn = nil
		armedFx[model] = nil
		sucker.Enabled = false
		for _, p in parts do
			if p:IsA("BasePart") then
				tween(p, 0.3, { Transparency = 1 })
				for _, d in p:GetChildren() do
					if d:IsA("Decal") then
						tween(d, 0.3, { Transparency = 1 })
					end
				end
				Debris:AddItem(p, 1.1)
			end
		end
	end
	armedFx[model] = stop
	conn = RunService.RenderStepped:Connect(function(dt)
		local r = rootOf(model)
		if not r or (model:GetAttribute("BiteArmedUntil") or 0) <= serverNow() then
			stop()
			return
		end
		spin += dt * 2.2
		local pos = r.Position
		if disc.Shape == Enum.PartType.Cylinder then
			disc.CFrame = CFrame.new(pos) * CFrame.Angles(0, spin, math.rad(90))
		else
			disc.CFrame = CFrame.new(pos) * CFrame.Angles(0, spin, 0)
		end
		shell.CFrame = CFrame.new(pos)
		inner.CFrame = CFrame.new(pos)
	end)
end

local function slowed(model: Model, data)
	local root = rootOf(model)
	if not root then
		return
	end
	local old = root:FindFirstChild("SlowedIcon")
	if old then
		old:Destroy()
	end
	local scale = model:GetScale()
	local gui = billboard(root, 1.8 * scale, Vector3.new(0, 3 * scale, 0))
	gui.Name = "SlowedIcon"
	local icon = picture(gui, "SlowIcon", "🐌", Color3.fromRGB(200, 230, 120))
	pop(icon, 1.3, 0.2)
	local duration = type(data) == "table" and data.duration or 3
	local started = os.clock()
	local conn
	conn = RunService.RenderStepped:Connect(function()
		local t = os.clock() - started
		local until_ = model:GetAttribute("SlowedUntil")
		local over = not gui.Parent or (until_ and until_ <= serverNow() and t > 0.5) or t > duration + 2
		if over then
			conn:Disconnect()
			if gui.Parent then
				fade(icon, 0.25)
				Debris:AddItem(gui, 0.3)
			end
			return
		end
		gui.StudsOffset = Vector3.new(0, (3 + 0.2 * math.sin(t * 5)) * scale, 0)
		icon.Rotation = math.sin(t * 3) * 6
	end)
end

local function chomp(model: Model, data)
	if type(data) ~= "table" or typeof(data.position) ~= "Vector3" then
		return
	end
	if armedFx[model] then
		armedFx[model]()
	end
	local scale = model:GetScale()
	local holder = anchor(data.position)
	local gui = billboard(holder, 7 * scale)
	gui.AlwaysOnTop = true
	local function jaw(lower: boolean): GuiObject
		local frame = Instance.new("Frame")
		frame.BackgroundTransparency = 1
		frame.Size = UDim2.fromScale(1, 0.42)
		frame.AnchorPoint = Vector2.new(0.5, lower and 0 or 1)
		frame.Position = UDim2.fromScale(0.5, lower and 1.05 or -0.05)
		frame.Parent = gui
		local pic = picture(frame, "BiteJaw", lower and "▲▲▲▲▲" or "▼▼▼▼▼", Color3.fromRGB(255, 250, 236))
		if lower then
			pic.Rotation = 180
		end
		return frame
	end
	local upper, lower = jaw(false), jaw(true)
	tween(upper, 0.09, { Position = UDim2.fromScale(0.5, 0.52) }, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
	tween(lower, 0.09, { Position = UDim2.fromScale(0.5, 0.48) }, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
	task.delay(0.09, function()
		local star = Instance.new("Frame")
		star.BackgroundTransparency = 1
		star.AnchorPoint = Vector2.new(0.5, 0.5)
		star.Position = UDim2.fromScale(0.5, 0.5)
		star.Size = UDim2.fromScale(0.9, 0.9)
		star.ZIndex = 0
		star.Parent = gui
		local s = picture(star, "ImpactStar", "✸", Color3.fromRGB(255, 255, 255))
		s.ZIndex = 0
		pop(star, 1.35, 0.18)
		local word = Instance.new("TextLabel")
		word.BackgroundTransparency = 1
		word.AnchorPoint = Vector2.new(0.5, 0.5)
		word.Position = UDim2.fromScale(0.5, 0.12)
		word.Size = UDim2.fromScale(0.95, 0.26)
		word.Text = "CHOMP!"
		word.TextScaled = true
		word.Font = Enum.Font.FredokaOne
		word.TextColor3 = Color3.fromRGB(255, 255, 255)
		word.Rotation = -8
		word.ZIndex = 3
		word.Parent = gui
		local stroke = Instance.new("UIStroke")
		stroke.Color = Color3.fromRGB(120, 20, 30)
		stroke.Thickness = 4
		stroke.Parent = word
		pop(word, 1.4, 0.2)
		burst(data.position, {
			Color = ColorSequence.new(Color3.fromRGB(255, 255, 255)), LightEmission = 0.8,
			Size = NumberSequence.new(0.5 * scale, 0), Lifetime = NumberRange.new(0.3, 0.6),
			Speed = NumberRange.new(12, 24), SpreadAngle = Vector2.new(180, 180), Drag = 4,
		}, 26, 1)
		sound(SOUNDS.chomp, holder)
		local victimRoot = rootOf(data.victim)
		if data.victim and data.victim == player.Character then
			ClientState.shake(2.2, 0.45)
		elseif workspace.CurrentCamera and (workspace.CurrentCamera.CFrame.Position - data.position).Magnitude < 45 then
			ClientState.shake(0.9, 0.3)
		end
		if victimRoot then
			shockwave(victimRoot.Position, 4 * scale, Color3.fromRGB(255, 255, 255), 0.3)
		end
		task.delay(0.35, function()
			for _, d in gui:GetDescendants() do
				if d:IsA("GuiObject") then
					fade(d, 0.3)
				end
			end
			fade(word, 0.3)
			tween(stroke, 0.3, { Transparency = 1 })
		end)
	end)
	Debris:AddItem(holder, 1.2)
end

-- --------------------------------------------------------------------------- entry point
function AbilityFx.handle(kind: string, model: Instance?, data)
	if kind == "TimeStop" and model then
		startTimeStop(model :: Model, data)
	elseif kind == "TimeHit" then
		timeHit(data)
	elseif kind == "TimeResume" and model then
		local state = stops[model]
		if state then
			state.finish(false)
		else
			for star, _ in frozenStars do
				star.release()
			end
		end
	elseif kind == "BiteArmed" and model then
		biteArmed(model :: Model, data)
	elseif kind == "Slowed" and model then
		slowed(model :: Model, data)
	elseif kind == "Chomp" and model then
		chomp(model :: Model, data)
	end
end

return AbilityFx

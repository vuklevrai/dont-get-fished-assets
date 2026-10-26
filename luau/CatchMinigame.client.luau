-- Escape minigame while hooked (a "skill check"): a pointer runs around a ring; click (or Space) while it is
-- inside the green zone to break free. A miss costs HP, flashes the ring red, kicks it back, shakes the camera
-- (smooth noise) and makes the pointer tremble, then run the other way round. Speed and zone size come from
-- the server (Remotes.Caught: pointerSpeed, greenArc); the result goes back through Remotes.CatchResult.
-- The lighter "perfect" band in the middle of the zone is cosmetic: a bigger celebration, same result.
-- Everything is drawn with overlapping round dots: smooth bands, round caps, exact angles, no rotated frames.
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

local RADIUS = 118 -- ring centre line, px at UI scale 1
local THICKNESS = 22
local ZONE_SIZE = THICKNESS + 4
local PERFECT_SIZE = 12
local DOT_STEP = 5 -- px between the dots of a band; they overlap into one smooth band
local PERFECT_SHARE = 0.3 -- the perfect band is this share of the green zone
local SPIN_UP = 9 -- 1/s: how fast the pointer reaches its speed (start, and after each reversal)
local TREMBLE_TIME = 0.3
local TREMBLE_AMPLITUDE = 7 -- degrees
local TREMBLE_FREQUENCY = 9 -- Hz
local TREMBLE_DAMPING = 10 -- 1/s
local TRAIL = 12 -- ghost dots behind the pointer
local FAIL_DAMAGE = Config.CATCH_FAIL_DAMAGE or 2
local SCREEN_POSITION = Vector2.new(0.74, 0.55) -- off to the side: the struggling fish stays in view

local RING = Color3.fromRGB(122, 20, 36)
local RING_GROOVE = Color3.fromRGB(150, 34, 52)
local RING_FLASH = Color3.fromRGB(255, 72, 72)
local OUTLINE = Color3.fromRGB(18, 10, 26)
local GREEN = Color3.fromRGB(70, 225, 95)
local PERFECT = Color3.fromRGB(225, 255, 170)
local POINTER = Color3.fromRGB(255, 255, 255)
local TRAIL_COLOR = Color3.fromRGB(255, 236, 140)
local CELEBRATE = { Color3.fromRGB(90, 255, 120), Color3.fromRGB(255, 232, 60), Color3.fromRGB(70, 230, 255) }

-- ------------------------------------------------------------------------------------------ building blocks
local function polar(angle: number, radius: number): UDim2
	local a = math.rad(angle)
	return UDim2.new(0.5, math.sin(a) * radius, 0.5, -math.cos(a) * radius)
end

local function polarVector(angle: number, radius: number): Vector2
	local a = math.rad(angle)
	return Vector2.new(math.sin(a) * radius, -math.cos(a) * radius)
end

local function dot(parent: Instance, size: number, color: Color3): Frame
	local d = Instance.new("Frame")
	d.AnchorPoint = Vector2.new(0.5, 0.5)
	d.Size = UDim2.fromOffset(size, size)
	d.BackgroundColor3 = color
	d.BorderSizePixel = 0
	Instance.new("UICorner", d).CornerRadius = UDim.new(1, 0)
	d.Parent = parent
	return d
end

local function layer(parent: Instance, z: number): Frame
	local f = Instance.new("Frame")
	f.Size = UDim2.fromScale(1, 1)
	f.BackgroundTransparency = 1
	f.ZIndex = z
	f.Parent = parent
	return f
end

local function easeOutBack(t: number): number
	local c = 1.7
	return 1 + (c + 1) * (t - 1) ^ 3 + c * (t - 1) ^ 2
end

-- ------------------------------------------------------------------------------------------ gui
local gui = Instance.new("ScreenGui")
gui.Name = "CatchMinigame"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.Enabled = false
gui.DisplayOrder = 10
gui.Parent = player:WaitForChild("PlayerGui")

local dim = Instance.new("Frame")
dim.Size = UDim2.fromScale(1, 1)
dim.BackgroundColor3 = Color3.fromRGB(10, 14, 30)
dim.BackgroundTransparency = 1
dim.BorderSizePixel = 0
dim.Parent = gui

local flash = Instance.new("Frame")
flash.Size = UDim2.fromScale(1, 1)
flash.BackgroundColor3 = RING_FLASH
flash.BackgroundTransparency = 1
flash.BorderSizePixel = 0
flash.ZIndex = 20
flash.Parent = gui

local BOX = 2 * (RADIUS + THICKNESS) + 40
-- the ring (bounces and recoils) ...
local holder = Instance.new("Frame")
holder.AnchorPoint = Vector2.new(0.5, 0.5)
holder.Position = UDim2.fromScale(SCREEN_POSITION.X, SCREEN_POSITION.Y)
holder.Size = UDim2.fromOffset(BOX, BOX)
holder.BackgroundTransparency = 1
holder.ZIndex = 5
holder.Parent = gui
local holderScale = Instance.new("UIScale")
holderScale.Parent = holder
-- ... and the texts and sparks, which keep their size while the ring moves
local overlay = Instance.new("Frame")
overlay.AnchorPoint = Vector2.new(0.5, 0.5)
overlay.Position = holder.Position
overlay.Size = holder.Size
overlay.BackgroundTransparency = 1
overlay.ZIndex = 6
overlay.Parent = gui
local overlayScale = Instance.new("UIScale")
overlayScale.Parent = overlay

-- one layer per kind of dot: inside a layer the dots overlap freely, the layers fix what is on top
local outlineLayer, ringLayer, grooveLayer = layer(holder, 1), layer(holder, 2), layer(holder, 3)
local zoneLayer, perfectLayer = layer(holder, 4), layer(holder, 5)
local trailLayer, pointerLayer = layer(holder, 6), layer(holder, 7)

local title = Instance.new("TextLabel")
title.AnchorPoint = Vector2.new(0.5, 1)
title.Position = UDim2.new(0.5, 0, 0, 6)
title.Size = UDim2.fromOffset(460, 44)
title.BackgroundTransparency = 1
title.Font = Enum.Font.FredokaOne
title.TextScaled = true
title.TextColor3 = Color3.new(1, 1, 1)
title.Text = "YOU'VE BEEN HOOKED!"
title.Parent = overlay
local titleStroke = Instance.new("UIStroke")
titleStroke.Thickness = 3
titleStroke.Color = Color3.fromRGB(120, 10, 10)
titleStroke.Parent = title
local titleScale = Instance.new("UIScale")
titleScale.Parent = title

local hint = Instance.new("TextLabel")
hint.AnchorPoint = Vector2.new(0.5, 0)
hint.Position = UDim2.new(0.5, 0, 1, -4)
hint.Size = UDim2.fromOffset(460, 26)
hint.BackgroundTransparency = 1
hint.Font = Enum.Font.GothamBlack
hint.TextScaled = true
hint.TextColor3 = Color3.fromRGB(200, 255, 200)
hint.Text = "CLICK or SPACE when the pointer is in the GREEN zone!"
hint.Parent = overlay
local hintStroke = Instance.new("UIStroke")
hintStroke.Thickness = 2
hintStroke.Color = Color3.fromRGB(10, 30, 10)
hintStroke.Parent = hint

-- the ring: a dark outline band, the red band and a lighter groove along its middle
local ringDots: { { frame: Frame, angle: number } } = {}
local RING_COUNT = math.ceil(2 * math.pi * RADIUS / DOT_STEP)
for i = 0, RING_COUNT - 1 do
	local a = i / RING_COUNT * 360
	dot(outlineLayer, THICKNESS + 7, OUTLINE).Position = polar(a, RADIUS)
	local d = dot(ringLayer, THICKNESS, RING)
	d.Position = polar(a, RADIUS)
	table.insert(ringDots, { frame = d, angle = a })
	dot(grooveLayer, math.floor(THICKNESS * 0.3), RING_GROOVE).Position = polar(a, RADIUS)
end

local function pool(parent: Instance, size: number, color: Color3, count: number): { Frame }
	local list = {}
	for i = 1, count do
		local d = dot(parent, size, color)
		d.Visible = false
		list[i] = d
	end
	return list
end
local zoneDots = pool(zoneLayer, ZONE_SIZE, GREEN, RING_COUNT + 2)
local perfectDots = pool(perfectLayer, PERFECT_SIZE, PERFECT, math.ceil(RING_COUNT * 0.5))

-- the pointer: a needle of dots from the hub, a bright tip with a glow, and a fading trail along the ring
local hub = dot(pointerLayer, 30, Color3.fromRGB(245, 245, 250))
hub.Position = UDim2.fromScale(0.5, 0.5)
hub.ZIndex = 3
local hubStroke = Instance.new("UIStroke")
hubStroke.Thickness = 3
hubStroke.Color = OUTLINE
hubStroke.Parent = hub
local NEEDLE = 8
local needle: { Frame } = {}
for i = 1, NEEDLE do
	needle[i] = dot(pointerLayer, 5 + i * 0.7, POINTER)
end
local glow = dot(trailLayer, 46, TRAIL_COLOR)
glow.BackgroundTransparency = 0.6
local trail: { Frame } = {}
for i = 1, TRAIL do
	local d = dot(trailLayer, THICKNESS - i, TRAIL_COLOR)
	d.BackgroundTransparency = 0.25 + 0.7 * i / TRAIL
	d.ZIndex = 2
	trail[i] = d
end
local tip = dot(pointerLayer, 26, POINTER)
tip.ZIndex = 3
local tipStroke = Instance.new("UIStroke")
tipStroke.Thickness = 3
tipStroke.Color = OUTLINE
tipStroke.Parent = tip

-- ------------------------------------------------------------------------------------------ state
local active = false -- the minigame takes input
local resolved = false -- escaped: celebrating, no more input
local angle, angVel, spinDir = 0, 0, 1 -- degrees, degrees/s, +1 = clockwise
local speed, arc = 150, 100
local zoneStart, perfectStart, perfectArc = 0, 0, 30
local zoneShown, zoneTarget = 0, 1 -- the zone pops in and out (0..1)
local trembleStart, trembleUntil, trembleBase = 0, 0, 0
local trembling = false
local ringScale, ringScaleVel = 1, 0 -- bouncy spring
local recoil, recoilVel = Vector2.zero, Vector2.zero -- bouncy spring (px)
local ringFlash = 0 -- 1 = fully red
local celebrateStart, celebrateUntil = 0, 0
local outroStart = math.huge
local colorsDirty = false
local effects = {} -- running one-off animations: { t, duration, step(p, dt), done() }

local function addEffect(duration: number, step: (number, number) -> (), done: (() -> ())?)
	table.insert(effects, { t = 0, duration = duration, step = step, done = done })
end

local function clearEffects()
	for _, e in effects do
		if e.done then
			e.done()
		end
	end
	table.clear(effects)
end

-- ------------------------------------------------------------------------------------------ zone
local function inArc(a: number, from: number, span: number): boolean
	return (a - from) % 360 <= span
end

-- a band from `from` over `span` degrees (clockwise); the round caps end exactly on the angles
local function drawArc(list: { Frame }, from: number, span: number, size: number)
	local cap = math.deg((size / 2) / RADIUS)
	local a0, a1 = from + cap, from + span - cap
	if a1 < a0 then
		a0, a1 = from + span / 2, from + span / 2
	end
	local n = math.min(#list, math.max(1, math.ceil(math.rad(a1 - a0) * RADIUS / DOT_STEP) + 1))
	for i, d in list do
		if i <= n then
			d.Position = polar(if n == 1 then a0 else a0 + (a1 - a0) * (i - 1) / (n - 1), RADIUS)
			d.Visible = true
		else
			d.Visible = false
		end
	end
end

local function sizeZone(k: number)
	local zone = UDim2.fromOffset(ZONE_SIZE * k, ZONE_SIZE * k)
	for _, d in zoneDots do
		d.Size = zone
	end
	local p = UDim2.fromOffset(PERFECT_SIZE * k, PERFECT_SIZE * k)
	for _, d in perfectDots do
		d.Size = p
	end
end

-- a new zone ahead of the pointer in its direction of travel, never right under it
local function placeZone()
	local ahead = 70 + math.random() * math.max(0, 360 - arc - 120)
	if spinDir > 0 then
		zoneStart = (angle + ahead) % 360
	else
		zoneStart = (angle - ahead - arc) % 360
	end
	perfectArc = math.max(6, arc * PERFECT_SHARE)
	perfectStart = (zoneStart + (arc - perfectArc) / 2) % 360
	drawArc(zoneDots, zoneStart, arc, ZONE_SIZE)
	drawArc(perfectDots, perfectStart, perfectArc, PERFECT_SIZE)
	zoneShown, zoneTarget = 0, 1
	sizeZone(0)
end

-- ------------------------------------------------------------------------------------------ effects
local function screenScale(): number
	return math.clamp(camera.ViewportSize.Y / 1000, 0.65, 1.3)
end

local function burst(at: Vector2, count: number)
	for i = 1, count do
		local a = (i / count) * math.pi * 2 + math.random() * 0.5
		local v = Vector2.new(math.cos(a), math.sin(a)) * (240 + math.random() * 280)
		local pos = at
		local size = 7 + math.random() * 7
		local spark = Instance.new("Frame")
		spark.AnchorPoint = Vector2.new(0.5, 0.5)
		spark.BorderSizePixel = 0
		spark.BackgroundColor3 = CELEBRATE[i % #CELEBRATE + 1]
		spark.ZIndex = 30
		spark.Position = UDim2.new(0.5, pos.X, 0.5, pos.Y)
		spark.Size = UDim2.fromOffset(size, size)
		spark.Parent = overlay
		addEffect(0.55 + math.random() * 0.3, function(p, dt)
			v = v * math.exp(-3 * dt) + Vector2.new(0, 560) * dt
			pos += v * dt
			local s = size * (1 - 0.6 * p)
			spark.Position = UDim2.new(0.5, pos.X, 0.5, pos.Y)
			spark.Size = UDim2.fromOffset(s, s)
			spark.Rotation = 45 + 200 * p
			spark.BackgroundTransparency = p * p
		end, function()
			spark:Destroy()
		end)
	end
end

local function shockwave(color: Color3)
	local wave = Instance.new("Frame")
	wave.AnchorPoint = Vector2.new(0.5, 0.5)
	wave.Position = UDim2.fromScale(0.5, 0.5)
	wave.BackgroundTransparency = 1
	wave.Size = UDim2.fromOffset(2 * (RADIUS + THICKNESS), 2 * (RADIUS + THICKNESS))
	wave.ZIndex = 25
	Instance.new("UICorner", wave).CornerRadius = UDim.new(1, 0)
	local stroke = Instance.new("UIStroke")
	stroke.Color = color
	stroke.Parent = wave
	wave.Parent = overlay
	addEffect(0.45, function(p)
		local d = 2 * (RADIUS + THICKNESS) * (1 + 0.65 * (1 - (1 - p) ^ 3))
		wave.Size = UDim2.fromOffset(d, d)
		stroke.Thickness = 1 + 9 * (1 - p)
		stroke.Transparency = p
	end, function()
		wave:Destroy()
	end)
end

-- a text that pops in (bouncy scale), drifts up and fades; `rainbow` sweeps the celebration colours over it
local function popText(text: string, at: Vector2, size: Vector2, duration: number, color: Color3, rainbow: boolean)
	local label = Instance.new("TextLabel")
	label.AnchorPoint = Vector2.new(0.5, 0.5)
	label.Position = UDim2.new(0.5, at.X, 0.5, at.Y)
	label.Size = UDim2.fromOffset(size.X, size.Y)
	label.BackgroundTransparency = 1
	label.Font = Enum.Font.FredokaOne
	label.TextScaled = true
	label.Text = text
	label.TextColor3 = if rainbow then Color3.new(1, 1, 1) else color
	label.ZIndex = 40
	local stroke = Instance.new("UIStroke")
	stroke.Thickness = 4
	stroke.Color = OUTLINE
	stroke.Parent = label
	local scale = Instance.new("UIScale")
	scale.Scale = 0.2
	scale.Parent = label
	local gradient: UIGradient? = nil
	if rainbow then
		local g = Instance.new("UIGradient")
		g.Color = ColorSequence.new({
			ColorSequenceKeypoint.new(0, CELEBRATE[1]),
			ColorSequenceKeypoint.new(0.5, CELEBRATE[2]),
			ColorSequenceKeypoint.new(1, CELEBRATE[3]),
		})
		g.Parent = label
		gradient = g
	end
	label.Parent = overlay
	local s, sv = 0.2, 0
	addEffect(duration, function(p, dt)
		sv += (-300 * (s - 1) - 15 * sv) * dt
		s += sv * dt
		scale.Scale = s
		label.Position = UDim2.new(0.5, at.X, 0.5, at.Y - 36 * p)
		label.Rotation = math.sin(p * math.pi * 4) * 5 * (1 - p)
		if gradient then
			gradient.Rotation = 200 * p
			gradient.Offset = Vector2.new(0.35 * math.sin(p * 9), 0)
		end
		local fade = math.clamp((p - 0.65) / 0.35, 0, 1)
		label.TextTransparency = fade
		stroke.Transparency = fade
	end, function()
		label:Destroy()
	end)
end

local function screenFlash(duration: number, from: number, colorAt: (number) -> Color3)
	addEffect(duration, function(p)
		flash.BackgroundColor3 = colorAt(p)
		flash.BackgroundTransparency = from + (1 - from) * p
	end, function()
		flash.BackgroundTransparency = 1
	end)
end

local function celebrateColor(k: number): Color3
	k %= #CELEBRATE
	local i = math.floor(k)
	return CELEBRATE[i + 1]:Lerp(CELEBRATE[(i + 1) % #CELEBRATE + 1], k - i)
end

-- ------------------------------------------------------------------------------------------ outcomes
local function escaped(perfect: boolean)
	resolved = true
	local clock = os.clock()
	celebrateStart, celebrateUntil = clock, clock + 0.7
	ringScaleVel += if perfect then 7 else 5.5
	local tipAt = polarVector(angle, RADIUS)
	burst(tipAt, if perfect then 28 else 18)
	shockwave(CELEBRATE[2])
	if perfect then
		shockwave(CELEBRATE[3])
	end
	popText(if perfect then "PERFECT ESCAPE!" else "ESCAPED!", Vector2.new(0, -8), Vector2.new(380, 70), 1.25, Color3.new(1, 1, 1), true)
	screenFlash(0.4, 0.55, function(p)
		return celebrateColor(p * 3)
	end)
	hint.Text = ""
end

local function missed()
	local clock = os.clock()
	-- tremble on a damped oscillation, then run the other way round
	trembleStart, trembleUntil, trembleBase = clock, clock + TREMBLE_TIME, angle
	trembling = true
	spinDir = -spinDir
	angVel = 0
	zoneTarget = 0
	ringFlash = 1
	ringScaleVel -= 2
	recoilVel -= polarVector(angle, 1) * 520
	ClientState.shake(0.6, 0.3)
	screenFlash(0.3, 0.6, function(_)
		return RING_FLASH
	end)
	popText("-" .. tostring(FAIL_DAMAGE), polarVector(angle, RADIUS + 34), Vector2.new(90, 46), 0.8, RING_FLASH, false)
end

local function attempt()
	if not active or resolved or os.clock() < trembleUntil then
		return
	end
	if inArc(angle, zoneStart, arc) then
		Remotes.CatchResult:FireServer(true)
		escaped(inArc(angle, perfectStart, perfectArc))
	else
		Remotes.CatchResult:FireServer(false)
		missed()
	end
end

-- leaves the screen: right away, or after the celebration when the fish escaped
local function close()
	if not active then
		return
	end
	active = false
	ClientState.setUiOpen("Catch", false)
	outroStart = os.clock() + (if resolved then 0.55 else 0)
end

-- respawned or reset: gone at once
local function hardClose()
	active, resolved = false, false
	ClientState.setUiOpen("Catch", false)
	clearEffects()
	outroStart = math.huge
	gui.Enabled = false
end

Remotes.Caught.OnClientEvent:Connect(function(data)
	clearEffects()
	speed = type(data) == "table" and tonumber(data.pointerSpeed) or 150
	arc = math.clamp(type(data) == "table" and tonumber(data.greenArc) or 100, 10, 300)
	angle = math.random() * 360
	angVel, spinDir = 0, 1
	trembleUntil, trembling = 0, false
	resolved = false
	outroStart = math.huge
	placeZone()
	ringScale, ringScaleVel = 0.55, 0 -- pops in
	recoil, recoilVel = Vector2.zero, Vector2.zero
	ringFlash, celebrateUntil = 0, 0
	colorsDirty = true
	hint.Text = "CLICK or SPACE when the pointer is in the GREEN zone!"
	holder.Visible, overlay.Visible = true, true
	active = true
	gui.Enabled = true
	ClientState.setUiOpen("Catch", true)
end)

Remotes.Released.OnClientEvent:Connect(close)
player.CharacterAdded:Connect(hardClose)

UserInputService.InputBegan:Connect(function(input)
	if input.UserInputType == Enum.UserInputType.MouseButton1
		or (input.KeyCode == Enum.KeyCode.Space and not UserInputService:GetFocusedTextBox()) then
		attempt()
	end
end)

-- ------------------------------------------------------------------------------------------ per frame
local function paintRing(clock: number)
	if clock < celebrateUntil then
		-- celebration: the colours sweep around the ring
		local t = (clock - celebrateStart) * 5
		for _, entry in ringDots do
			entry.frame.BackgroundColor3 = celebrateColor(entry.angle / 360 * 3 + t)
		end
		colorsDirty = true
	elseif ringFlash > 0 then
		local c = RING:Lerp(RING_FLASH, ringFlash)
		for _, entry in ringDots do
			entry.frame.BackgroundColor3 = c
		end
		colorsDirty = true
	elseif colorsDirty then
		for _, entry in ringDots do
			entry.frame.BackgroundColor3 = RING
		end
		colorsDirty = false
	end
end

local function drawPointer()
	tip.Position = polar(angle, RADIUS)
	glow.Position = tip.Position
	for i, d in needle do
		d.Position = polar(angle, 18 + (RADIUS - 30) * i / NEEDLE)
	end
	local dir = if math.abs(angVel) > 1 then math.sign(angVel) else spinDir
	local spacing = math.clamp(math.abs(angVel) * 0.012, 1.2, 7) -- degrees between ghosts
	for i, d in trail do
		d.Position = polar(angle - dir * spacing * i, RADIUS)
	end
	local inside = active and not resolved and inArc(angle, zoneStart, arc)
	tip.BackgroundColor3 = if inside then GREEN:Lerp(POINTER, 0.4) else POINTER
end

RunService.RenderStepped:Connect(function(dt)
	if not gui.Enabled then
		return
	end
	dt = math.min(dt, 0.1)
	local clock = os.clock()

	if active and not resolved then
		local character = player.Character
		if not character or not character:GetAttribute("Caught") then
			close()
		end
	end

	-- pointer: smooth spin-up, damped tremble after a miss, then the other way round
	if active and not resolved then
		if clock < trembleUntil then
			local tau = clock - trembleStart
			angle = trembleBase + TREMBLE_AMPLITUDE * math.sin(2 * math.pi * TREMBLE_FREQUENCY * tau) * math.exp(-TREMBLE_DAMPING * tau)
		else
			if trembling then
				trembling = false
				placeZone()
			end
			angVel += (spinDir * speed - angVel) * (1 - math.exp(-SPIN_UP * dt))
			angle = (angle + angVel * dt) % 360
		end
	end

	-- springs: the ring's bounce and recoil
	ringScaleVel += (-260 * (ringScale - 1) - 12 * ringScaleVel) * dt
	ringScale += ringScaleVel * dt
	recoilVel += (-recoil * 420 - recoilVel * 22) * dt
	recoil += recoilVel * dt
	ringFlash = math.max(0, ringFlash - dt / 0.35)

	-- the zone pops in and shrinks away smoothly
	if zoneShown ~= zoneTarget then
		zoneShown = if zoneTarget > zoneShown then math.min(1, zoneShown + dt / 0.18) else math.max(0, zoneShown - dt / 0.12)
		sizeZone(if zoneTarget > 0 then easeOutBack(zoneShown) else zoneShown)
	end

	-- leaving
	local outro = 1
	if not active and clock >= outroStart then
		local p = math.clamp((clock - outroStart) / 0.25, 0, 1)
		outro = 1 - p * p
		if p >= 1 then
			holder.Visible = false
			overlay.Visible = #effects > 0
		end
	end

	local base = screenScale()
	holderScale.Scale = base * math.max(0, ringScale) * outro
	overlayScale.Scale = base
	holder.Position = UDim2.new(SCREEN_POSITION.X, recoil.X * base, SCREEN_POSITION.Y, recoil.Y * base)
	titleScale.Scale = 1 + 0.035 * math.sin(clock * 6)
	title.Visible = active and not resolved
	hint.Visible = active and not resolved
	local dimTarget = if active then 0.78 else 1
	dim.BackgroundTransparency += (dimTarget - dim.BackgroundTransparency) * (1 - math.exp(-10 * dt))

	paintRing(clock)
	drawPointer()

	for i = #effects, 1, -1 do
		local e = effects[i]
		e.t += dt
		local p = math.min(e.t / e.duration, 1)
		e.step(p, dt)
		if p >= 1 then
			table.remove(effects, i)
			if e.done then
				e.done()
			end
		end
	end

	if not active and not holder.Visible and #effects == 0 then
		gui.Enabled = false
	end
end)

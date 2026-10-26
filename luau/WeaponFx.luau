-- Client effects of the harpoon and bazooka fishermen (ModuleScript, ReplicatedStorage.FishGame.WeaponFx).
-- Call WeaponFx.handle(kind, ...) from the Remotes.Effect handler. Both (kind, a, b, ...) and the existing
-- (kind, model, a, b, ...) shapes work: when the first value is not a Vector3 but the second is, the first is skipped.
--   "HarpoonAim", origin: Vector3, bottom: Vector3, radius: number, duration: number
--       red fog column from origin (the fisherman) to bottom (the sea bed): appears in 0.15 s, stays `duration`
--       seconds, fades in 0.25 s. Sharp hitbox edge (a ForceField tube), misty fog inside, red rings where it meets
--       the water surface and the bed. Returns { destroy() }.
--   "HarpoonFire", from: Vector3, to: Vector3, travelTime: number [, key: any]
--       the harpoon flies from `from` (the gun) to `to` in travelTime, pulling a rope (Beam). Returns
--       { rope: Beam, harpoon: Model, setTip(pos: Vector3), destroy() } for the retraction during the catch.
--       setTip moves the harpoon point to pos (it hangs along the rope); destroy removes harpoon and rope.
--       Optional `key`: the handle is also kept under it, so remotes alone can drive it:
--       "HarpoonTip", key, pos  and  "HarpoonEnd", key.
--   "MissileAim", center: Vector3, radius: number, duration: number
--       red circle on the bed under the zone and a sight on the zone that blinks faster and faster.
--       (the fog itself is Effects' "Fog"). Returns { destroy() }.
--   "MissileFire", from: Vector3, target: Vector3, flightTime: number
--       the missile climbs and dives on the target along a Bezier arc, smoke trail (bubbles under water), flame
--       at the nozzle; its nose reaches `target` exactly after flightTime. Returns { missile: Model, destroy() }.
--   "Explosion", center: Vector3, radius: number
--       cartoon flipbook, shockwave growing to `radius`, sparks, smoke (bubbles under water), flash of light and a
--       soft camera shake (smooth noise offset, never a jump) when the camera is closer than radius * 3.
-- Performance mode (ClientState.performance): half the particles, no second layer.
-- Needs, in ReplicatedStorage.FishGame: FxAssets (keys AimBeamFlipbook, AimRing, MissileReticle, ExplosionFlipbook,
-- ShockwaveRing, SmokePuff, MissileFlame, Bubble, ShardSpark: any left at rbxassetid://0 falls back to plain shapes),
-- ClientState, Config. Uses when present: WeaponModels (real harpoon and missile, else simple stand-ins), Bubbles.
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

local WeaponFx = {}

local FRAME_PX = 256 -- one frame of a 4x4 flipbook sheet (1024 px)
local RED = Color3.fromRGB(255, 46, 36)

local AIM = {
	fps = 10, -- the fog flows down one tile (the column's width) per 1.6 s
	appear = 0.15,
	vanish = 0.25,
	fogTransparency = 0.1,
	shellTransparency = 0.45, -- ForceField tube: the sharp edge of the hitbox
	ringTransparency = 0.05,
}

-- --------------------------------------------------------------------------- shared helpers
local function perf(): boolean
	return ClientState.performance == true
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

local loaded = {}
local function optional(name: string): any
	if loaded[name] ~= nil then
		return loaded[name] or nil
	end
	local module = FishGame:FindFirstChild(name)
	if not (module and module:IsA("ModuleScript")) then
		return nil -- not there (yet): try again next time
	end
	local ok, result = pcall(require, module)
	if not ok then
		warn("WeaponFx: could not load " .. name .. ": " .. tostring(result))
	end
	loaded[name] = ok and result or false
	return ok and result or nil
end

local function waterLevel(): number
	return FishGame:GetAttribute("MapWaterLevel") or Config.WATER_LEVEL or -1
end

local function underwater(p: Vector3): boolean
	if FishGame:GetAttribute("MapWaterShape") == "Sphere" then
		local c = FishGame:GetAttribute("MapWaterCenter")
		local r = FishGame:GetAttribute("MapWaterRadius")
		if typeof(c) == "Vector3" and type(r) == "number" then
			return (p - c).Magnitude < r
		end
	end
	return p.Y < waterLevel()
end

local function fxPart(size: Vector3, cf: CFrame): Part
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.Transparency = 1
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.Size = size
	p.CFrame = cf
	p.Parent = fxFolder()
	return p
end

local function seq(points: { { number } }): NumberSequence
	local keys = {}
	for _, p in points do
		table.insert(keys, NumberSequenceKeypoint.new(p[1], p[2]))
	end
	return NumberSequence.new(keys)
end

-- looks along `dir` without ever being degenerate (straight up or down)
local function lookAlong(pos: Vector3, dir: Vector3): CFrame
	if dir.Magnitude < 1e-4 then
		return CFrame.new(pos)
	end
	local d = dir.Unit
	local up = if math.abs(d.Y) > 0.98 then Vector3.zAxis else Vector3.yAxis
	return CFrame.lookAt(pos, pos + d, up)
end

-- a frame whose Y axis runs along `axis`
local function alongAxis(pos: Vector3, axis: Vector3): CFrame
	local up = axis.Unit
	local side = up:Cross(if math.abs(up.Y) < 0.95 then Vector3.yAxis else Vector3.xAxis).Unit
	return CFrame.fromMatrix(pos, side, up)
end

-- lying flat on a surface: Y along its normal
local function flatOn(pos: Vector3, normal: Vector3): CFrame
	local x = normal:Cross(Vector3.zAxis)
	x = if x.Magnitude > 0.1 then x.Unit else Vector3.xAxis
	return CFrame.fromMatrix(pos, x, normal)
end

local function floorBelow(from: Vector3, depth: number?): RaycastResult?
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	local ignore = { fxFolder() }
	for _, fish in CollectionService:GetTagged(Config.FISH_TAG or "Fish") do
		table.insert(ignore, fish)
	end
	for _, plr in Players:GetPlayers() do
		if plr.Character then
			table.insert(ignore, plr.Character)
		end
	end
	params.FilterDescendantsInstances = ignore
	params.IgnoreWater = true
	return workspace:Raycast(from, Vector3.new(0, -(depth or 300), 0), params)
end

-- one RenderStepped connection drives every running effect; a job returns false when it is finished
local jobs: { [(number, number) -> boolean]: boolean } = {}
local stepping: RBXScriptConnection? = nil

local function schedule(job: (number, number) -> boolean)
	jobs[job] = true
	if stepping then
		return
	end
	stepping = RunService.RenderStepped:Connect(function(dt)
		local now = os.clock()
		local list = {} -- a job may start another one: walk a copy
		for fn in jobs do
			table.insert(list, fn)
		end
		for _, fn in list do
			local ok, alive = pcall(fn, dt, now)
			if not ok then
				warn("WeaponFx: " .. tostring(alive))
			end
			if not ok or alive == false then
				jobs[fn] = nil
			end
		end
		if next(jobs) == nil and stepping then
			stepping:Disconnect()
			stepping = nil
		end
	end)
end

local function frameOffset(frame: number): Vector2
	return Vector2.new(frame % 4, math.floor(frame / 4)) * FRAME_PX
end

-- a flat, unlit picture on faces of a thin part (rings): a fixed 512 px canvas stretched over the face, so the
-- part can grow without touching the GUI. Returns the ImageLabels.
local function decalPair(part: BasePart, faces: { Enum.NormalId }, texture: string): { ImageLabel }
	local out = {}
	for _, face in faces do
		local sg = Instance.new("SurfaceGui")
		sg.Face = face
		sg.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
		sg.CanvasSize = Vector2.new(512, 512)
		sg.LightInfluence = 0
		sg.Brightness = 1.2
		sg.Parent = part
		local img = Instance.new("ImageLabel")
		img.BackgroundTransparency = 1
		img.Size = UDim2.fromScale(1, 1)
		img.Image = texture
		img.ImageTransparency = 1
		img.Parent = sg
		table.insert(out, img)
	end
	return out
end

-- a red ring lying flat at `cf` (texture, or a plain neon ring of parts when the texture is not uploaded yet)
local function flatRing(cf: CFrame, radius: number): (BasePart, { ImageLabel }, { BasePart })
	local size = radius * 2
	local part = fxPart(Vector3.new(size, 0.05, size), cf)
	local texture = image("AimRing")
	if texture then
		return part, decalPair(part, { Enum.NormalId.Top, Enum.NormalId.Bottom }, texture), {}
	end
	local pieces = {}
	local n = 32
	for i = 0, n - 1 do
		local a = i / n * math.pi * 2
		local seg = fxPart(Vector3.new(0.35, 0.12, 2 * math.pi * radius / n + 0.1),
			cf * CFrame.Angles(0, -a, 0) * CFrame.new(radius, 0, 0))
		seg.Material = Enum.Material.Neon
		seg.Color = RED
		seg.Parent = part
		table.insert(pieces, seg)
	end
	return part, {}, pieces
end

local function setRing(images: { ImageLabel }, pieces: { BasePart }, transparency: number)
	for _, img in images do
		img.ImageTransparency = transparency
	end
	for _, p in pieces do
		p.Transparency = transparency
	end
end

-- camera shake: ClientState's smooth noise. The fish camera (FishController, Scriptable) applies it itself;
-- for any other camera (avatar, spectating) the offset is added right after the camera scripts.
local shakeBound = false
local function shake(strength: number, duration: number)
	ClientState.shake(strength, duration)
	if shakeBound then
		return
	end
	shakeBound = true
	RunService:BindToRenderStep("WeaponFxShake", Enum.RenderPriority.Camera.Value + 2, function()
		local cam = workspace.CurrentCamera
		if cam and cam.CameraType ~= Enum.CameraType.Scriptable and os.clock() < (ClientState.shakeUntil or 0) + 0.4 then
			cam.CFrame += ClientState.shakeOffset()
		end
	end)
end

local function bubbles(pos: Vector3, n: number)
	local B = optional("Bubbles")
	if B and B.burst then
		B.burst(pos, n)
	end
end

-- weapon models: WeaponModels when it is installed, else a simple stand-in with the same anchors
local function standIn(name: string): Model
	local model = Instance.new("Model")
	model.Name = name
	local root = Instance.new("Part")
	root.Name = "Root"
	root.Size = Vector3.one * 0.2
	root.Transparency = 1
	root.Anchored = true
	root.CanCollide = false
	root.CanQuery = false
	root.CanTouch = false
	root.Parent = model
	model.PrimaryPart = root
	local function piece(shape: Enum.PartType, size: Vector3, cf: CFrame, color: Color3, material: Enum.Material?)
		local p = Instance.new("Part")
		p.Shape = shape
		p.Size = size
		p.CFrame = cf
		p.Color = color
		p.Material = material or Enum.Material.SmoothPlastic
		p.Anchored = true
		p.CanCollide = false
		p.CanQuery = false
		p.CanTouch = false
		p.Parent = model
	end
	local function anchor(key: string, cf: CFrame)
		local att = Instance.new("Attachment")
		att.Name = key
		att.CFrame = cf
		att.Parent = root
	end
	if name == "Harpoon" then
		piece(Enum.PartType.Cylinder, Vector3.new(6.6, 0.22, 0.22), CFrame.new(0, 0, 3.9) * CFrame.Angles(0, math.pi / 2, 0),
			Color3.fromRGB(196, 202, 212), Enum.Material.Metal)
		piece(Enum.PartType.Ball, Vector3.one * 0.5, CFrame.new(0, 0, 0.45), Color3.fromRGB(232, 236, 242), Enum.Material.Metal)
		anchor("Tip", CFrame.identity)
		anchor("RopeAttach", CFrame.new(0, 0, 7.38))
	else
		piece(Enum.PartType.Cylinder, Vector3.new(3, 0.74, 0.74), CFrame.new(0, 0, 2.3) * CFrame.Angles(0, math.pi / 2, 0),
			Color3.fromRGB(242, 242, 236))
		piece(Enum.PartType.Ball, Vector3.one * 0.74, CFrame.new(0, 0, 0.6), Color3.fromRGB(226, 44, 40))
		anchor("Nose", CFrame.identity)
		anchor("Exhaust", CFrame.new(0, 0, 3.82) * CFrame.Angles(0, math.pi, 0))
	end
	return model
end

local function buildModel(name: string): Model
	local lib = optional("WeaponModels")
	if lib and lib.build then
		local ok, model = pcall(lib.build, name, true)
		if ok and model then
			return model
		end
	end
	return standIn(name)
end

local function hideModel(model: Model)
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.LocalTransparencyModifier = 1
		elseif d:IsA("Beam") or d:IsA("Trail") or d:IsA("Light") then
			d.Enabled = false
		end
	end
end

-- --------------------------------------------------------------------------- harpoon: aim column
function WeaponFx.harpoonAim(origin: Vector3, bottom: Vector3, radius: number?, duration: number?)
	local r = radius or 7
	local hold = math.max(duration or 1, 0)
	local axis = origin - bottom
	local length = axis.Magnitude
	if length < 0.5 then
		return nil
	end
	local low = perf()
	local base = alongAxis((origin + bottom) / 2, axis) -- Y runs from the bed up to the fisherman
	local parts: { Instance } = {}
	local fogLabels: { ImageLabel } = {}
	local fogShift: { number } = {} -- each quad plays the loop from another frame, so the planes never match

	-- 1) the fog: the flipbook on crossed vertical quads (3, or 2 in performance mode); the frames tile down the
	--    column, one tile is as tall as the column is wide
	local fog = image("AimBeamFlipbook")
	if fog then
		local quads = if low then 2 else 3
		local pps = FRAME_PX / (2 * r)
		for i = 0, quads - 1 do
			local quad = fxPart(Vector3.new(2 * r, length, 0.05), base * CFrame.Angles(0, i * math.pi / quads, 0))
			table.insert(parts, quad)
			for _, face in { Enum.NormalId.Front, Enum.NormalId.Back } do
				local sg = Instance.new("SurfaceGui")
				sg.Face = face
				sg.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
				sg.PixelsPerStud = pps
				sg.LightInfluence = 0
				sg.Brightness = 1
				sg.ClipsDescendants = true
				sg.Parent = quad
				local tiles = math.ceil(length / (2 * r))
				for k = 0, tiles - 1 do
					local img = Instance.new("ImageLabel")
					img.BackgroundTransparency = 1
					img.Size = UDim2.new(1, 0, 0, FRAME_PX)
					img.Position = UDim2.fromOffset(0, k * FRAME_PX) -- from the fisherman's end down
					img.Image = fog
					img.ImageRectSize = Vector2.new(FRAME_PX, FRAME_PX)
					img.ImageTransparency = 1
					img.Parent = sg
					table.insert(fogLabels, img)
					table.insert(fogShift, (i * 5 + (if face == Enum.NormalId.Back then 8 else 0)) % 16)
				end
			end
		end
	end

	-- 2) the hitbox edge: a ForceField tube, sharp silhouette, see-through middle
	local shell = fxPart(Vector3.new(length, 2 * r, 2 * r), base * CFrame.Angles(0, 0, math.pi / 2))
	shell.Shape = Enum.PartType.Cylinder
	shell.Material = Enum.Material.ForceField
	shell.Color = RED
	table.insert(parts, shell)
	local shellTarget = if fog then AIM.shellTransparency else 0.15

	-- 3) rings where the column meets the bed and the water surface
	local rings: { { any } } = {}
	local function addRing(pos: Vector3)
		local part, images, pieces = flatRing(CFrame.new(pos), r * 1.08)
		table.insert(parts, part)
		table.insert(rings, { images, pieces })
	end
	addRing(bottom + Vector3.new(0, 0.12, 0))
	if FishGame:GetAttribute("MapWaterShape") ~= "Sphere" then
		local level = waterLevel()
		if (origin.Y - level) * (bottom.Y - level) < 0 then
			local t = (level - bottom.Y) / (origin.Y - bottom.Y)
			addRing(bottom:Lerp(origin, t) + Vector3.new(0, 0.08, 0))
		end
	end

	local start = os.clock()
	local finish = AIM.appear + hold + AIM.vanish
	local dead = false
	local shown = -1
	local function cleanup()
		dead = true
		for _, p in parts do
			p:Destroy()
		end
	end
	schedule(function(_, now)
		if dead then
			return false
		end
		local t = now - start
		if t >= finish then
			cleanup()
			return false
		end
		-- 0 -> 1 in `appear`, 1 while it holds, 1 -> 0 in `vanish`
		local a = if t < AIM.appear then t / AIM.appear elseif t > AIM.appear + hold then (finish - t) / AIM.vanish else 1
		local frame = math.floor(t * (if low then 8 else AIM.fps)) % 16
		local turn = frame ~= shown
		shown = frame
		for k, img in fogLabels do
			img.ImageTransparency = 1 - a * (1 - AIM.fogTransparency)
			if turn then
				img.ImageRectOffset = frameOffset((frame + fogShift[k]) % 16)
			end
		end
		shell.Transparency = 1 - a * (1 - shellTarget)
		local pulse = 0.5 + 0.5 * math.sin(t * math.pi * 2 * 2.2)
		for _, ring in rings do
			setRing(ring[1], ring[2], 1 - a * (1 - AIM.ringTransparency - 0.3 * pulse))
		end
		return true
	end)
	return { destroy = cleanup }
end

-- --------------------------------------------------------------------------- harpoon: shot and rope
local harpoons: { [any]: any } = {}

function WeaponFx.harpoonFire(from: Vector3, to: Vector3, travelTime: number?, key: any?)
	local flight = math.max(travelTime or 0.35, 0.05)
	local low = perf()
	local harpoon = buildModel("Harpoon")
	harpoon.Parent = fxFolder()
	local root = harpoon.PrimaryPart :: BasePart
	local dir = to - from
	local look = if dir.Magnitude > 1e-3 then dir.Unit else Vector3.new(0, -1, 0)
	harpoon:PivotTo(lookAlong(from, look))

	-- the rope, from the gun to the ring at the back of the harpoon
	local holder = fxPart(Vector3.one * 0.2, CFrame.new(from))
	local a0 = Instance.new("Attachment")
	a0.Parent = holder
	local a1 = root:FindFirstChild("RopeAttach") :: Attachment?
	if not a1 then
		local att = Instance.new("Attachment")
		att.Name = "RopeAttach"
		att.Position = Vector3.new(0, 0, 7.38)
		att.Parent = root
		a1 = att
	end
	local rope = Instance.new("Beam")
	rope.Attachment0 = a0
	rope.Attachment1 = a1
	rope.Width0 = 0.16
	rope.Width1 = 0.16
	rope.FaceCamera = true
	rope.Segments = 12
	rope.Color = ColorSequence.new(Color3.fromRGB(236, 226, 196))
	rope.Transparency = NumberSequence.new(0)
	rope.LightInfluence = 0.6
	rope.Parent = holder

	-- a short white streak behind it while it flies
	local trail: Trail? = nil
	if not low then
		local t0 = Instance.new("Attachment")
		t0.Position = Vector3.new(0, 0.25, 7)
		t0.Parent = root
		local t1 = Instance.new("Attachment")
		t1.Position = Vector3.new(0, -0.25, 7)
		t1.Parent = root
		local tr = Instance.new("Trail")
		tr.Attachment0 = t0
		tr.Attachment1 = t1
		tr.FaceCamera = true
		tr.Lifetime = 0.18
		tr.Color = ColorSequence.new(Color3.fromRGB(235, 250, 255))
		tr.Transparency = seq({ { 0, 0.35 }, { 1, 1 } })
		tr.LightEmission = 0.5
		tr.Parent = root
		trail = tr
	end

	local handle = { rope = rope, harpoon = harpoon }
	local dead = false
	local manual = false
	local wasWet = underwater(from)

	function handle.setTip(a: any, b: any?)
		local pos = if typeof(a) == "Vector3" then a else b
		if dead or typeof(pos) ~= "Vector3" then
			return
		end
		manual = true
		if trail then
			trail.Enabled = false
		end
		-- the harpoon hangs along the rope, pointing away from the gun
		local away = pos - a0.WorldPosition
		harpoon:PivotTo(lookAlong(pos, if away.Magnitude > 0.1 then away else look))
	end

	function handle.destroy()
		if dead then
			return
		end
		dead = true
		harpoon:Destroy()
		holder:Destroy()
		if key ~= nil and harpoons[key] == handle then
			harpoons[key] = nil
		end
	end

	if key ~= nil then
		if harpoons[key] then
			harpoons[key].destroy()
		end
		harpoons[key] = handle
	end

	local start = os.clock()
	schedule(function(_, now)
		if dead or manual then
			return false
		end
		local t = math.clamp((now - start) / flight, 0, 1)
		local tip = from:Lerp(to, t)
		harpoon:PivotTo(lookAlong(tip, look))
		local wet = underwater(tip)
		if wet and not wasWet then
			bubbles(tip, if low then 4 else 8) -- breaking into the water
		elseif wet and not low and math.random() < 0.35 then
			bubbles(tip - look * 2, 1)
		end
		wasWet = wet
		if t >= 1 then
			if trail then
				trail.Enabled = false
			end
			if wet then
				bubbles(to, if low then 3 else 6)
			end
			return false
		end
		return true
	end)
	-- never leave a rope behind if the catch logic forgets it
	task.delay(math.max(60, flight + 5), handle.destroy)
	return handle
end

-- --------------------------------------------------------------------------- bazooka: aim
function WeaponFx.missileAim(center: Vector3, radius: number?, duration: number?)
	local r = radius or (Config.HOOK_RADIUS or 17.5)
	local hold = math.max(duration or 1, 0)
	local parts: { Instance } = {}

	-- the circle on the bed straight under the zone (or under the centre when there is no bed in reach)
	local hit = floorBelow(center + Vector3.new(0, 1, 0))
	local ringCF = if hit then flatOn(hit.Position + hit.Normal * 0.12, hit.Normal) else CFrame.new(center - Vector3.new(0, r, 0))
	local ringPart, ringImages, ringPieces = flatRing(ringCF, r)
	table.insert(parts, ringPart)

	-- the sight: a camera-facing reticle on the zone itself
	local holder = fxPart(Vector3.one * 0.2, CFrame.new(center))
	table.insert(parts, holder)
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.new(2.2 * r, 0, 2.2 * r, 0) -- BillboardGui scale = studs
	gui.LightInfluence = 0
	gui.AlwaysOnTop = false
	gui.MaxDistance = 600
	gui.Adornee = holder
	gui.Parent = holder
	local sight = Instance.new("Frame")
	sight.BackgroundTransparency = 1
	sight.AnchorPoint = Vector2.new(0.5, 0.5)
	sight.Position = UDim2.fromScale(0.5, 0.5)
	sight.Size = UDim2.fromScale(1, 1)
	sight.Parent = gui
	local reticle = image("MissileReticle")
	local sightImages: { ImageLabel } = {}
	local sightStrokes: { UIStroke } = {}
	local sightFrames: { Frame } = {}
	if reticle then
		local img = Instance.new("ImageLabel")
		img.BackgroundTransparency = 1
		img.Size = UDim2.fromScale(1, 1)
		img.Image = reticle
		img.Parent = sight
		table.insert(sightImages, img)
	else
		-- plain shapes: a circle, four ticks and a dot
		local circle = Instance.new("Frame")
		circle.AnchorPoint = Vector2.new(0.5, 0.5)
		circle.Position = UDim2.fromScale(0.5, 0.5)
		circle.Size = UDim2.fromScale(0.6, 0.6)
		circle.BackgroundTransparency = 1
		circle.Parent = sight
		local corner = Instance.new("UICorner")
		corner.CornerRadius = UDim.new(0.5, 0)
		corner.Parent = circle
		local stroke = Instance.new("UIStroke")
		stroke.Thickness = 5
		stroke.Color = RED
		stroke.Parent = circle
		table.insert(sightStrokes, stroke)
		for _, d in { Vector2.new(1, 0), Vector2.new(-1, 0), Vector2.new(0, 1), Vector2.new(0, -1) } do
			local bar = Instance.new("Frame")
			bar.AnchorPoint = Vector2.new(0.5, 0.5)
			bar.Position = UDim2.fromScale(0.5 + d.X * 0.3, 0.5 + d.Y * 0.3)
			bar.Size = if d.X ~= 0 then UDim2.fromScale(0.22, 0.035) else UDim2.fromScale(0.035, 0.22)
			bar.BackgroundColor3 = RED
			bar.BorderSizePixel = 0
			bar.Parent = sight
			table.insert(sightFrames, bar)
		end
		local dot = Instance.new("Frame")
		dot.AnchorPoint = Vector2.new(0.5, 0.5)
		dot.Position = UDim2.fromScale(0.5, 0.5)
		dot.Size = UDim2.fromScale(0.05, 0.05)
		dot.BackgroundColor3 = RED
		dot.BorderSizePixel = 0
		dot.Parent = sight
		local dotCorner = Instance.new("UICorner")
		dotCorner.CornerRadius = UDim.new(0.5, 0)
		dotCorner.Parent = dot
		table.insert(sightFrames, dot)
	end
	local function setSight(transparency: number)
		for _, img in sightImages do
			img.ImageTransparency = transparency
		end
		for _, s in sightStrokes do
			s.Transparency = transparency
		end
		for _, f in sightFrames do
			f.BackgroundTransparency = transparency
		end
	end
	setSight(1)
	setRing(ringImages, ringPieces, 1)

	local start = os.clock()
	local appear, vanish = 0.2, 0.15
	local finish = appear + hold + vanish
	local dead = false
	local function cleanup()
		dead = true
		for _, p in parts do
			p:Destroy()
		end
	end
	local blinkPhase = 0
	schedule(function(dt, now)
		if dead then
			return false
		end
		local t = now - start
		if t >= finish then
			cleanup()
			return false
		end
		local a = if t < appear then t / appear elseif t > appear + hold then (finish - t) / vanish else 1
		-- lock-on: the sight shrinks onto the zone and turns while it appears
		local lock = math.clamp(t / 0.3, 0, 1)
		local grow = 1 + 0.5 * (1 - lock) ^ 2
		gui.Size = UDim2.new(2.2 * r * grow, 0, 2.2 * r * grow, 0)
		sight.Rotation = (1 - lock) ^ 2 * 90 + t * 12
		-- blinking, faster and faster: 0.45 s per blink at the start, 0.06 s at the end; solid at the very end
		local progress = math.clamp((t - appear) / math.max(hold, 0.01), 0, 1)
		local interval = 0.45 + (0.06 - 0.45) * progress ^ 1.3
		blinkPhase += dt / interval
		local on = (blinkPhase % 1) < 0.6 or t > appear + hold - 0.2
		setSight(if on then 1 - a else 1)
		setRing(ringImages, ringPieces, 1 - a * (1 - AIM.ringTransparency))
		return true
	end)
	return { destroy = cleanup }
end

-- --------------------------------------------------------------------------- bazooka: shot
function WeaponFx.missileFire(from: Vector3, target: Vector3, flightTime: number?)
	local flight = math.max(flightTime or 1.2, 0.1)
	local low = perf()
	local missile = buildModel("Missile")
	missile.Parent = fxFolder()
	local root = missile.PrimaryPart :: BasePart

	-- the arc: up out of the launcher, over the top, then a dive onto the target (cubic Bezier)
	local delta = target - from
	local flat = Vector3.new(delta.X, 0, delta.Z)
	local h = math.clamp(delta.Magnitude * 0.45, 16, 70)
	local p0, p3 = from, target
	local p1 = from + Vector3.new(0, h, 0) + flat * 0.2
	local p2 = target + Vector3.new(0, h * 0.85, 0) - flat * 0.05
	local function at(t: number): Vector3
		local u = 1 - t
		return p0 * (u * u * u) + p1 * (3 * u * u * t) + p2 * (3 * u * t * t) + p3 * (t * t * t)
	end
	local function heading(t: number): Vector3
		local u = 1 - t
		return (p1 - p0) * (3 * u * u) + (p2 - p1) * (6 * u * t) + (p3 - p2) * (3 * t * t)
	end
	missile:PivotTo(lookAlong(p0, heading(0)))

	local exhaust = root:FindFirstChild("Exhaust") :: Attachment?
	if not exhaust then
		local att = Instance.new("Attachment")
		att.Name = "Exhaust"
		att.CFrame = CFrame.new(0, 0, 3.82) * CFrame.Angles(0, math.pi, 0)
		att.Parent = root
		exhaust = att
	end
	local nozzle = exhaust :: Attachment

	-- smoke trail (puffs stay in the world where they were left)
	local smoke = Instance.new("ParticleEmitter")
	smoke.Texture = image("SmokePuff") or "rbxasset://textures/particles/smoke_main.dds"
	smoke.Rate = if low then 22 else 45
	smoke.Lifetime = NumberRange.new(0.7, 1.1)
	smoke.Speed = NumberRange.new(2, 4)
	smoke.EmissionDirection = Enum.NormalId.Front -- the Exhaust attachment looks out of the nozzle
	smoke.SpreadAngle = Vector2.new(12, 12)
	smoke.Size = seq({ { 0, 0.7 }, { 1, 3.2 } })
	smoke.Transparency = seq({ { 0, 0.15 }, { 0.7, 0.5 }, { 1, 1 } })
	smoke.Rotation = NumberRange.new(0, 360)
	smoke.RotSpeed = NumberRange.new(-60, 60)
	smoke.Acceleration = Vector3.new(0, 2, 0)
	smoke.Drag = 1.5
	smoke.LightInfluence = 0.5
	smoke.Parent = nozzle

	-- nozzle flame: a camera-facing beam behind the nozzle (texture X runs from the nozzle backwards)
	local flameEnd = Instance.new("Attachment")
	flameEnd.CFrame = nozzle.CFrame * CFrame.new(0, 0, -2.2)
	flameEnd.Parent = root
	local flame = Instance.new("Beam")
	flame.Attachment0 = nozzle
	flame.Attachment1 = flameEnd
	flame.FaceCamera = true
	flame.Width0 = 0.75
	flame.Width1 = 0.25
	flame.LightEmission = 1
	flame.LightInfluence = 0
	local flameTexture = image("MissileFlame")
	if flameTexture then
		flame.Texture = flameTexture
		flame.TextureMode = Enum.TextureMode.Stretch
		flame.Color = ColorSequence.new(Color3.new(1, 1, 1))
	else
		flame.Color = ColorSequence.new({
			ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 250, 210)),
			ColorSequenceKeypoint.new(0.35, Color3.fromRGB(255, 200, 50)),
			ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 90, 20)),
		})
		flame.Transparency = seq({ { 0, 0 }, { 1, 1 } })
	end
	flame.Parent = root
	if not low then
		local light = Instance.new("PointLight")
		light.Color = Color3.fromRGB(255, 160, 60)
		light.Range = 10
		light.Brightness = 2
		light.Parent = nozzle
	end

	local handle = { missile = missile }
	local dead = false
	function handle.destroy()
		if dead then
			return
		end
		dead = true
		missile:Destroy()
	end

	local start = os.clock()
	local nextBubble = 0
	schedule(function(_, now)
		if dead then
			return false
		end
		local t = math.clamp((now - start) / flight, 0, 1)
		missile:PivotTo(lookAlong(at(t), heading(math.max(t, 0.001))))
		flame.Width0 = 0.75 * (0.85 + 0.3 * math.random())
		-- under water the smoke turns into a stream of bubbles
		local tail = nozzle.WorldPosition
		local wet = underwater(tail)
		smoke.Enabled = not wet
		if wet and now >= nextBubble then
			nextBubble = now + (if low then 0.08 else 0.04)
			bubbles(tail, 1)
		end
		if t >= 1 then
			-- hide it, let the trail fade where it was, then clean up
			smoke.Enabled = false
			hideModel(missile)
			task.delay(1.4, handle.destroy)
			return false
		end
		return true
	end)
	return handle
end

-- --------------------------------------------------------------------------- explosion
function WeaponFx.explosion(center: Vector3, radius: number?)
	local r = radius or (Config.HOOK_RADIUS or 17.5)
	local low = perf()
	local wet = underwater(center)
	local life = 2.2
	local holder = fxPart(Vector3.one * 0.2, CFrame.new(center))
	Debris:AddItem(holder, life)
	local att = Instance.new("Attachment")
	att.Parent = holder

	-- 1) the cartoon flipbook: its fireball covers ~71 % of a frame at its biggest, so a frame 2.83 r wide
	--    makes the fire fill the blast circle (ParticleEmitter Size is a half-width)
	local half = r * 1.41
	local book = image("ExplosionFlipbook")
	if book then
		local e = Instance.new("ParticleEmitter")
		e.Texture = book
		e.FlipbookLayout = Enum.ParticleFlipbookLayout.Grid4x4
		e.FlipbookMode = Enum.ParticleFlipbookMode.OneShot
		e.Lifetime = NumberRange.new(0.75) -- 16 frames at ~21 fps
		e.Size = NumberSequence.new(half)
		e.Speed = NumberRange.new(0)
		e.Rotation = NumberRange.new(-12, 12)
		e.LightEmission = 0.15
		e.LightInfluence = 0
		e.Orientation = Enum.ParticleOrientation.FacingCamera
		e.ZOffset = 1
		e.Enabled = false
		e.Parent = att
		e:Emit(1)
		if not low then
			-- second layer: turned round, a touch bigger and fainter, a beat later
			local back = e:Clone()
			back.Size = NumberSequence.new(half * 1.12)
			back.Rotation = NumberRange.new(165, 195)
			back.Transparency = NumberSequence.new(0.35)
			back.ZOffset = 0
			back.Parent = att
			task.delay(0.05, function()
				if back.Parent then
					back:Emit(1)
				end
			end)
		end
	else
		local ball = fxPart(Vector3.one * r * 0.4, CFrame.new(center))
		ball.Shape = Enum.PartType.Ball
		ball.Material = Enum.Material.Neon
		ball.Color = Color3.fromRGB(255, 150, 40)
		ball.Transparency = 0
		TweenService:Create(ball, TweenInfo.new(0.45, Enum.EasingStyle.Quad, Enum.EasingDirection.Out),
			{ Size = Vector3.one * r * 1.6, Transparency = 1 }):Play()
		Debris:AddItem(ball, 0.5)
	end

	-- 2) shockwave: a flat ring growing to the blast radius, and (full mode) a bubble of force around it
	local wave = fxPart(Vector3.new(r * 0.3, 0.05, r * 0.3), CFrame.new(center))
	Debris:AddItem(wave, 0.5)
	local waveTexture = image("ShockwaveRing")
	if waveTexture then
		for _, img in decalPair(wave, { Enum.NormalId.Top, Enum.NormalId.Bottom }, waveTexture) do
			img.ImageTransparency = 0.05
			TweenService:Create(img, TweenInfo.new(0.4, Enum.EasingStyle.Quad, Enum.EasingDirection.In), { ImageTransparency = 1 }):Play()
		end
		-- the ring's outer edge reaches the blast radius (diameter 2 r)
		TweenService:Create(wave, TweenInfo.new(0.35, Enum.EasingStyle.Quad, Enum.EasingDirection.Out),
			{ Size = Vector3.new(r * 2, 0.05, r * 2) }):Play()
	else
		wave.Shape = Enum.PartType.Cylinder
		wave.Size = Vector3.new(0.2, r * 0.3, r * 0.3)
		wave.CFrame = CFrame.new(center) * CFrame.Angles(0, 0, math.pi / 2)
		wave.Material = Enum.Material.Neon
		wave.Color = Color3.fromRGB(230, 250, 255)
		wave.Transparency = 0.2
		TweenService:Create(wave, TweenInfo.new(0.35, Enum.EasingStyle.Quad, Enum.EasingDirection.Out),
			{ Size = Vector3.new(0.2, r * 2, r * 2), Transparency = 1 }):Play()
	end
	if not low then
		local bubble = fxPart(Vector3.one, CFrame.new(center))
		bubble.Shape = Enum.PartType.Ball
		bubble.Material = Enum.Material.ForceField
		bubble.Color = Color3.fromRGB(220, 245, 255)
		bubble.Transparency = 0.2
		TweenService:Create(bubble, TweenInfo.new(0.32, Enum.EasingStyle.Quad, Enum.EasingDirection.Out),
			{ Size = Vector3.one * r * 2, Transparency = 1 }):Play()
		Debris:AddItem(bubble, 0.4)
	end

	-- 3) sparks flying out (slowed hard by the water when wet)
	local sparks = Instance.new("ParticleEmitter")
	local spark = image("ShardSpark")
	if spark then
		sparks.Texture = spark
	end
	sparks.Color = ColorSequence.new(Color3.fromRGB(255, 230, 120), Color3.fromRGB(255, 120, 30))
	sparks.LightEmission = 1
	sparks.LightInfluence = 0
	sparks.Size = seq({ { 0, 0.9 }, { 1, 0 } })
	sparks.Lifetime = NumberRange.new(0.4, 0.8)
	sparks.Speed = NumberRange.new(r * 1.6, r * 3.2)
	sparks.SpreadAngle = Vector2.new(180, 180)
	sparks.Drag = if wet then 4 else 1
	sparks.Acceleration = if wet then Vector3.new(0, 4, 0) else Vector3.new(0, -40, 0)
	sparks.Enabled = false
	sparks.Parent = att
	sparks:Emit(if low then 14 else 28)

	-- 4) what lingers: smoke in the air, a rush of bubbles under water
	if wet then
		bubbles(center, if low then 9 else 18)
		task.delay(0.25, function()
			bubbles(center + Vector3.new(0, r * 0.2, 0), if low then 4 else 8)
		end)
	else
		local puffs = Instance.new("ParticleEmitter")
		puffs.Texture = image("SmokePuff") or "rbxasset://textures/particles/smoke_main.dds"
		puffs.Size = seq({ { 0, r * 0.18 }, { 1, r * 0.45 } })
		puffs.Transparency = seq({ { 0, 0.1 }, { 0.6, 0.4 }, { 1, 1 } })
		puffs.Lifetime = NumberRange.new(1.2, 1.8)
		puffs.Speed = NumberRange.new(r * 0.35, r * 0.7)
		puffs.SpreadAngle = Vector2.new(180, 180)
		puffs.Drag = 2
		puffs.Acceleration = Vector3.new(0, 6, 0)
		puffs.Rotation = NumberRange.new(0, 360)
		puffs.RotSpeed = NumberRange.new(-40, 40)
		puffs.LightInfluence = 0.5
		puffs.Enabled = false
		puffs.Parent = att
		puffs:Emit(if low then 4 else 8)
	end

	-- 5) a flash of light
	local light = Instance.new("PointLight")
	light.Color = Color3.fromRGB(255, 170, 70)
	light.Range = math.min(60, r * 2.5)
	light.Brightness = 8
	light.Shadows = false
	light.Parent = holder
	TweenService:Create(light, TweenInfo.new(0.35, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { Brightness = 0 }):Play()

	-- 6) a soft shake when the camera is close
	local cam = workspace.CurrentCamera
	if cam then
		local d = (cam.CFrame.Position - center).Magnitude
		if d < r * 3 then
			local k = 1 - d / (r * 3)
			shake(0.35 + 1.25 * k, 0.35 + 0.3 * k)
		end
	end
end

-- --------------------------------------------------------------------------- entry point
function WeaponFx.handle(kind: string, ...: any): any
	local args = table.pack(...)
	local first = 1
	if kind == "HarpoonTip" or kind == "HarpoonEnd" then
		if args[1] == nil and args.n > 1 then
			first = 2 -- (kind, nil, key, ...)
		end
	elseif args.n > 1 and typeof(args[1]) ~= "Vector3" and typeof(args[2]) == "Vector3" then
		first = 2 -- the Effect remote's usual (kind, model, ...) shape: no model is needed here
	end
	local a, b, c, d = args[first], args[first + 1], args[first + 2], args[first + 3]
	if kind == "HarpoonAim" then
		return WeaponFx.harpoonAim(a, b, c, d)
	elseif kind == "HarpoonFire" then
		return WeaponFx.harpoonFire(a, b, c, d)
	elseif kind == "HarpoonTip" then
		local h = harpoons[a]
		if h then
			h.setTip(b)
		end
		return h
	elseif kind == "HarpoonEnd" then
		local h = harpoons[a]
		if h then
			h.destroy()
		end
		return nil
	elseif kind == "MissileAim" then
		return WeaponFx.missileAim(a, b, c)
	elseif kind == "MissileFire" then
		return WeaponFx.missileFire(a, b, c)
	elseif kind == "Explosion" then
		return WeaponFx.explosion(a, b)
	end
	return nil
end

return WeaponFx

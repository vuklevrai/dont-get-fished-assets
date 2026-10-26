-- Ambient bubbles rising to the surface (ModuleScript, ReplicatedStorage.FishGame.Bubbles).
--   Bubbles.start() -> stop(): every 1.5-4 s (3-6 s in performance mode) a cluster of 3-12 bubbles (2-6) is born on
--     the bed at a random spot within 120 studs of the camera, under the water. They wobble up, speed up a little,
--     swell as they rise and pop at the surface. start() can be called by several scripts: the ambience runs until
--     every stop() it returned has been called.
--   Bubbles.burst(pos: Vector3, n: number): a one-off cluster at pos (explosions, splashes); nothing above water.
-- Water, from the FishGame attributes: MapWaterShape "Plane" -> the surface is at MapWaterLevel (and the cluster
--   must be inside the current map's arena: ArenaMin/ArenaMax or PondRadiusX/Z, like MapService.inArena);
--   "Sphere" -> the ball MapWaterCenter / MapWaterRadius: bubbles start at the inside bottom of the ball, rise
--   straight up and pop where they leave it. The bed is found with a downward raycast that ignores fish (tag
--   "Fish"), characters and local effects.
-- Budget: at most 60 live bubbles (20 in performance mode, ClientState.performance). A bubble is a BillboardGui
--   (FxAssets.Bubble, or a drawn circle while that image is not uploaded) on an Attachment of one anchored part.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame:WaitForChild("Config"))
local FxAssets = require(FishGame:WaitForChild("FxAssets"))
local ClientState = require(FishGame:WaitForChild("ClientState"))

local Bubbles = {}

local MAX_LIVE, MAX_LIVE_LOW = 60, 20
local RANGE = 120 -- studs around the camera where clusters are born
local POP_TIME = 0.12
local MAX_LIFE = 25 -- seconds: a bubble that never meets the surface is dropped
local MAP_MODELS = { Pond = "PondMap", Aquarium = "AquariumMap", Ballon = "BallonMap", Ocean = "OceanMap" } -- as MapService

type Bubble = {
	att: Attachment,
	gui: BillboardGui,
	fade: (number) -> (),
	start: number,
	x: number,
	z: number,
	y: number,
	y0: number,
	speed: number,
	accel: number,
	maxSpeed: number,
	amp: number,
	freq: number,
	phase: number,
	dx: number,
	dz: number,
	size: number,
	popAt: number?,
}

local live: { Bubble } = {}
local pool: { Bubble } = {}
local users = 0 -- start() calls still running
local nextCluster = 0
local stepping: RBXScriptConnection? = nil
local anchor: Part? = nil
local rng = Random.new()

local function low(): boolean
	return ClientState.performance == true
end

local function image(): string?
	local id = FxAssets.Bubble
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

local function anchorPart(): Part
	if anchor and anchor.Parent then
		return anchor
	end
	local p = Instance.new("Part")
	p.Name = "BubbleAnchor"
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.Transparency = 1
	p.Size = Vector3.one * 0.2
	p.CFrame = CFrame.identity -- attachments on it are placed in world coordinates
	p.Parent = fxFolder()
	anchor = p
	return p
end

-- --------------------------------------------------------------------------- water
local function sphere(): (Vector3?, number?)
	if FishGame:GetAttribute("MapWaterShape") ~= "Sphere" then
		return nil, nil
	end
	local c = FishGame:GetAttribute("MapWaterCenter")
	local r = FishGame:GetAttribute("MapWaterRadius")
	if typeof(c) == "Vector3" and type(r) == "number" and r > 0 then
		return c, r
	end
	return nil, nil
end

local function level(): number
	return FishGame:GetAttribute("MapWaterLevel") or Config.WATER_LEVEL or -1
end

local function inWater(p: Vector3): boolean
	local c, r = sphere()
	if c and r then
		return (p - c).Magnitude < r
	end
	return p.Y < level()
end

-- same test as MapService.inArena for the flat maps
local function inArena(p: Vector3): boolean
	local name = FishGame:GetAttribute("MapName")
	local map = if type(name) == "string" and MAP_MODELS[name] then workspace:FindFirstChild(MAP_MODELS[name]) else nil
	if not map then
		return true
	end
	local lo, hi = map:GetAttribute("ArenaMin"), map:GetAttribute("ArenaMax")
	if typeof(lo) == "Vector3" and typeof(hi) == "Vector3" then
		return p.X > lo.X and p.X < hi.X and p.Z > lo.Z and p.Z < hi.Z
	end
	local rx, rz = map:GetAttribute("PondRadiusX"), map:GetAttribute("PondRadiusZ")
	if type(rx) == "number" and type(rz) == "number" then
		return (p.X / rx) ^ 2 + (p.Z / rz) ^ 2 < 0.95
	end
	return true
end

local function bedBelow(x: number, top: number, z: number): Vector3?
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
	local hit = workspace:Raycast(Vector3.new(x, top, z), Vector3.new(0, -400, 0), params)
	return hit and hit.Position or nil
end

-- --------------------------------------------------------------------------- one bubble
local function newBubble(): Bubble
	local att = Instance.new("Attachment")
	att.Name = "Bubble"
	local gui = Instance.new("BillboardGui")
	gui.LightInfluence = 0
	gui.AlwaysOnTop = false
	gui.MaxDistance = RANGE + 60
	gui.Size = UDim2.new(1, 0, 1, 0) -- BillboardGui scale = studs
	gui.Adornee = att
	gui.Enabled = false
	gui.Parent = att
	local fade: (number) -> ()
	local texture = image()
	if texture then
		local img = Instance.new("ImageLabel")
		img.BackgroundTransparency = 1
		img.Size = UDim2.fromScale(1, 1)
		img.Image = texture
		img.Parent = gui
		fade = function(t: number)
			img.ImageTransparency = t
		end
	else
		-- a drawn bubble: clear body, light rim, a white glint
		local body = Instance.new("Frame")
		body.Size = UDim2.fromScale(1, 1)
		body.BackgroundColor3 = Color3.fromRGB(200, 244, 255)
		body.BorderSizePixel = 0
		body.Parent = gui
		local corner = Instance.new("UICorner")
		corner.CornerRadius = UDim.new(0.5, 0)
		corner.Parent = body
		local rim = Instance.new("UIStroke")
		rim.Color = Color3.fromRGB(235, 252, 255)
		rim.Thickness = 1.5
		rim.Parent = body
		local glint = Instance.new("Frame")
		glint.Size = UDim2.fromScale(0.28, 0.2)
		glint.Position = UDim2.fromScale(0.2, 0.18)
		glint.Rotation = -35
		glint.BackgroundColor3 = Color3.new(1, 1, 1)
		glint.BorderSizePixel = 0
		glint.Parent = body
		local glintCorner = Instance.new("UICorner")
		glintCorner.CornerRadius = UDim.new(0.5, 0)
		glintCorner.Parent = glint
		fade = function(t: number)
			body.BackgroundTransparency = 0.78 + 0.22 * t
			rim.Transparency = t
			glint.BackgroundTransparency = t
		end
	end
	att.Parent = anchorPart()
	return {
		att = att, gui = gui, fade = fade, start = 0, x = 0, z = 0, y = 0, y0 = 0, speed = 0, accel = 0, maxSpeed = 0,
		amp = 0, freq = 0, phase = 0, dx = 1, dz = 0, size = 0.5, popAt = nil,
	}
end

local function recycle(b: Bubble)
	b.gui.Enabled = false
	if #pool < MAX_LIVE then
		table.insert(pool, b)
	else
		b.att:Destroy()
	end
end

local function step(dt: number)
	local now = os.clock()
	-- the ambience: a new cluster now and then
	if users > 0 and now >= nextCluster then
		nextCluster = now + (if low() then rng:NextNumber(3, 6) else rng:NextNumber(1.5, 4))
		Bubbles.cluster()
	end
	local c, r = sphere()
	local surface = level()
	for i = #live, 1, -1 do
		local b = live[i]
		if now < b.start then
			continue
		end
		local gui = b.gui
		if b.popAt then
			-- pop: a quick swell while it vanishes
			local k = (now - b.popAt) / POP_TIME
			if k >= 1 then
				table.remove(live, i)
				recycle(b)
			else
				local d = b.size * (1 + 0.6 * k)
				gui.Size = UDim2.new(d, 0, d, 0)
				b.fade(k)
			end
			continue
		end
		if not gui.Enabled then
			gui.Enabled = true
			b.fade(0)
		end
		b.speed = math.min(b.speed + b.accel * dt, b.maxSpeed)
		b.y += b.speed * dt
		local wobble = math.sin((now - b.start) * b.freq + b.phase) * b.amp
		local pos = Vector3.new(b.x + b.dx * wobble, b.y, b.z + b.dz * wobble)
		-- bubbles swell as they rise (less pressure)
		local d = b.size * math.min(1.8, 1 + (b.y - b.y0) / 55)
		gui.Size = UDim2.new(d, 0, d, 0)
		b.att.Position = pos
		local out = if c and r then (pos - c).Magnitude + d * 0.5 >= r else pos.Y + d * 0.5 >= surface
		if out or now - b.start > MAX_LIFE then
			b.popAt = now
		end
	end
	if #live == 0 and users == 0 and stepping then
		stepping:Disconnect()
		stepping = nil
	end
end

local function ensureRunning()
	if not stepping then
		stepping = RunService.RenderStepped:Connect(step)
	end
end

local function spawnBubble(pos: Vector3, delay: number)
	if #live >= (if low() then MAX_LIVE_LOW else MAX_LIVE) then
		return
	end
	local b = table.remove(pool) or newBubble()
	if not b.att.Parent then
		b.att.Parent = anchorPart()
	end
	local a = rng:NextNumber(0, math.pi * 2)
	b.start = os.clock() + delay
	b.x, b.y, b.z, b.y0 = pos.X, pos.Y, pos.Z, pos.Y
	b.speed = rng:NextNumber(2.5, 4.5)
	b.accel = rng:NextNumber(1.5, 3)
	b.maxSpeed = rng:NextNumber(10, 15)
	b.amp = rng:NextNumber(0.25, 0.75)
	b.freq = rng:NextNumber(4, 7)
	b.phase = rng:NextNumber(0, math.pi * 2)
	b.dx, b.dz = math.cos(a), math.sin(a)
	b.size = rng:NextNumber(0.35, 0.9)
	b.popAt = nil
	b.gui.Enabled = false
	b.att.Position = pos
	table.insert(live, b)
	ensureRunning()
end

-- --------------------------------------------------------------------------- public
function Bubbles.burst(pos: Vector3, n: number?)
	if typeof(pos) ~= "Vector3" or not inWater(pos) then
		return
	end
	local count = math.clamp(math.floor(n or 6), 1, 30)
	if low() then
		count = math.max(1, math.floor(count / 2))
	end
	for k = 1, count do
		local off = Vector3.new(rng:NextNumber(-1, 1), rng:NextNumber(-0.5, 0.5), rng:NextNumber(-1, 1)) * (0.4 + 0.15 * count)
		spawnBubble(pos + off, (k - 1) * 0.025)
	end
end

-- one ambient cluster near the camera (start() calls it on its own; public for tests)
function Bubbles.cluster()
	local cam = workspace.CurrentCamera
	if not cam then
		return
	end
	local eye = cam.CFrame.Position
	local base: Vector3? = nil
	local c, r = sphere()
	if c and r then
		-- the inside bottom of the ball
		local a = rng:NextNumber(0, math.pi * 2)
		local rr = math.sqrt(rng:NextNumber()) * r * 0.85
		local x, z = c.X + math.cos(a) * rr, c.Z + math.sin(a) * rr
		if Vector2.new(x - eye.X, z - eye.Z).Magnitude <= RANGE then
			base = Vector3.new(x, c.Y - math.sqrt(math.max(r * r - rr * rr, 0)) + 1.5, z)
		end
	else
		local top = level()
		local a = rng:NextNumber(0, math.pi * 2)
		local dist = 12 + (RANGE - 12) * rng:NextNumber() ^ 1.5
		local x, z = eye.X + math.cos(a) * dist, eye.Z + math.sin(a) * dist
		if inArena(Vector3.new(x, top, z)) then
			local hit = bedBelow(x, top - 0.5, z)
			if hit and hit.Y < top - 3 then -- deep enough to be worth it
				base = hit + Vector3.new(0, 0.4, 0)
			end
		end
	end
	if not base then
		return
	end
	local n = if low() then rng:NextInteger(2, 6) else rng:NextInteger(3, 12)
	for k = 1, n do
		local off = Vector3.new(rng:NextNumber(-1.5, 1.5), 0, rng:NextNumber(-1.5, 1.5))
		spawnBubble(base + off, (k - 1) * rng:NextNumber(0.05, 0.14))
	end
end

function Bubbles.start(): () -> ()
	users += 1
	nextCluster = math.min(nextCluster, os.clock() + 0.5)
	ensureRunning()
	local stopped = false
	return function()
		if not stopped then
			stopped = true
			users -= 1
		end
	end
end

return Bubbles

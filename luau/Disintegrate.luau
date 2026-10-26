-- Block-by-block elimination of a fish (ModuleScript, ReplicatedStorage.FishGame.Disintegrate).
--   Disintegrate.play(model: Model, impulseDir: Vector3?)
--   Clones every visible BasePart of the fish locally (never the invisible root), hides the original (the server
--   destroys it) and strips joints, constraints and scripts off the clones. Then the blocks let go in a cascade
--   over ~0.35 s: from the tail to the head, or from the impact side when impulseDir is given (the direction the
--   blow pushes the fish). Each block leaves with a random speed and spin and a short white flash. Under water it
--   is braked hard and drifts up a little; above the water (MapWaterLevel, or outside the ball map's sphere)
--   normal gravity applies and it comes to rest on the ground under it. The blocks stay scattered 2 s, then
--   shrink and fade out in 0.3 s.
--   At most 80 moving pieces (40 in performance mode): a bigger fish is cut into that many slices, each moving
--   as one. Pure CFrame animation on RenderStepped: anchored, no collision, no touch, invisible to raycasts.
-- Needs, in ReplicatedStorage.FishGame: Config, FxAssets (ShardSpark, optional sparkle at each release),
-- ClientState (.performance).
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame:WaitForChild("Config"))
local FxAssets = require(FishGame:WaitForChild("FxAssets"))
local ClientState = require(FishGame:WaitForChild("ClientState"))

local Disintegrate = {}

local MAX_PIECES, MAX_PIECES_LOW = 80, 40
local CASCADE = 0.35 -- seconds from the first block to the last
local SCATTERED = 2 -- seconds a block stays scattered once it has left
local VANISH = 0.3
local WATER_DRAG = 4.5 -- 1/s: how fast the water kills the speed
local WATER_SPIN_DRAG = 2.5
local BUOYANCY = 2.5 -- studs/s2 upwards in the water
local AIR_DRAG = 0.3
local FLASH = Color3.new(1, 1, 1)
local KEEP = { Decal = true, Texture = true, SpecialMesh = true, SurfaceAppearance = true }

type Piece = {
	parts: { BasePart },
	offsets: { CFrame },
	sizes: { Vector3 },
	colors: { Color3 },
	alphas: { number },
	cf: CFrame,
	vel: Vector3,
	axis: Vector3,
	spin: number,
	radius: number,
	leaveAt: number,
	left: boolean,
	flashing: boolean,
	ground: number?,
	done: boolean,
}

local rng = Random.new()

local function fxFolder(): Instance
	local folder = workspace:FindFirstChild("LocalEffects")
	if not folder then
		folder = Instance.new("Folder")
		folder.Name = "LocalEffects"
		folder.Parent = workspace
	end
	return folder
end

local function inWater(p: Vector3): boolean
	if FishGame:GetAttribute("MapWaterShape") == "Sphere" then
		local c = FishGame:GetAttribute("MapWaterCenter")
		local r = FishGame:GetAttribute("MapWaterRadius")
		if typeof(c) == "Vector3" and type(r) == "number" then
			return (p - c).Magnitude < r
		end
	end
	return p.Y < (FishGame:GetAttribute("MapWaterLevel") or Config.WATER_LEVEL or -1)
end

local function randomUnit(): Vector3
	local z = rng:NextNumber(-1, 1)
	local a = rng:NextNumber(0, math.pi * 2)
	local r = math.sqrt(1 - z * z)
	return Vector3.new(r * math.cos(a), z, r * math.sin(a))
end

local function groundBelow(from: Vector3, ignore: { Instance }): number?
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = ignore
	params.IgnoreWater = true
	local hit = workspace:Raycast(from, Vector3.new(0, -200, 0), params)
	return hit and hit.Position.Y or nil
end

local function spark(): string?
	local id = FxAssets.ShardSpark
	if type(id) ~= "string" or id == "" or id == "rbxassetid://0" then
		return nil
	end
	return id
end

function Disintegrate.play(model: Model, impulseDir: Vector3?)
	if typeof(model) ~= "Instance" or not model:IsA("Model") or model:GetAttribute("Disintegrated") then
		return
	end
	model:SetAttribute("Disintegrated", true) -- local only: never play twice for the same fish
	local low = ClientState.performance == true
	local root = model.PrimaryPart
	local sources: { BasePart } = {}
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") and d ~= root and d.Transparency < 0.99 and d.LocalTransparencyModifier < 0.99 then
			table.insert(sources, d)
		end
	end
	-- hide the original right away (the server removes it): parts, badges, health bars, highlights, particles
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.LocalTransparencyModifier = 1
		elseif d:IsA("BillboardGui") or d:IsA("SurfaceGui") or d:IsA("Highlight") then
			d.Enabled = false
		elseif d:IsA("ParticleEmitter") or d:IsA("Trail") or d:IsA("Beam") then
			d.Enabled = false
		end
	end
	if #sources == 0 then
		return -- nothing visible for this player (an invisible fish): nothing to break
	end

	-- the cascade order: along the impact direction, or from the tail (behind the fish) to the head
	local centre = Vector3.zero
	for _, p in sources do
		centre += p.Position
	end
	centre /= #sources
	local look = if root then root.CFrame.LookVector else model:GetPivot().LookVector
	local axis = if impulseDir and impulseDir.Magnitude > 1e-3 then impulseDir.Unit else look
	table.sort(sources, function(a, b)
		return (a.Position - centre):Dot(axis) < (b.Position - centre):Dot(axis)
	end)

	-- the local copies
	local holder = Instance.new("Model")
	holder.Name = "Disintegrating"
	holder.Parent = fxFolder()
	local clones: { BasePart } = {}
	for _, src in sources do
		local c = src:Clone()
		if not c then
			local p = Instance.new("Part")
			p.Size = src.Size
			p.Color = src.Color
			p.Material = src.Material
			c = p
		end
		local clone = c :: BasePart
		for _, d in clone:GetDescendants() do
			if not KEEP[d.ClassName] then
				d:Destroy()
			end
		end
		clone.Anchored = true
		clone.CanCollide = false
		clone.CanQuery = false
		clone.CanTouch = false
		clone.Massless = true
		clone.CastShadow = false
		clone.LocalTransparencyModifier = 0
		clone.CFrame = src.CFrame
		clone.Parent = holder
		table.insert(clones, clone)
	end

	-- pieces: one per block, or slices of neighbouring blocks for big fish
	local limit = if low then MAX_PIECES_LOW else MAX_PIECES
	local count = math.min(#clones, limit)
	local pieces: { Piece } = {}
	local now = os.clock()
	local ignore = { holder, fxFolder() }
	for _, fish in CollectionService:GetTagged(Config.FISH_TAG or "Fish") do
		table.insert(ignore, fish)
	end
	for _, plr in Players:GetPlayers() do
		if plr.Character then
			table.insert(ignore, plr.Character)
		end
	end
	for k = 1, count do
		local first = math.floor((k - 1) * #clones / count) + 1
		local last = math.floor(k * #clones / count)
		local members: { BasePart } = {}
		local mid = Vector3.zero
		for i = first, last do
			table.insert(members, clones[i])
			mid += clones[i].Position
		end
		mid /= #members
		local base = if #members == 1 then members[1].CFrame else CFrame.new(mid)
		local piece: Piece = {
			parts = members, offsets = {}, sizes = {}, colors = {}, alphas = {}, cf = base, vel = Vector3.zero,
			axis = randomUnit(), spin = rng:NextNumber(3, 9), radius = 0.5, leaveAt = 0, left = false,
			flashing = false, ground = nil, done = false,
		}
		local reach = 0
		for _, part in members do
			table.insert(piece.offsets, base:ToObjectSpace(part.CFrame))
			table.insert(piece.sizes, part.Size)
			table.insert(piece.colors, part.Color)
			table.insert(piece.alphas, part.Transparency)
			reach = math.max(reach, (part.Position - mid).Magnitude + part.Size.Magnitude * 0.25)
		end
		piece.radius = math.max(0.3, reach)
		-- out from the body, a random kick, and the blow's push when there is one
		local out = mid - centre
		local dir = if out.Magnitude > 1e-3 then out.Unit else randomUnit()
		local vel = dir * rng:NextNumber(6, 14) + randomUnit() * rng:NextNumber(2, 6)
		if impulseDir and impulseDir.Magnitude > 1e-3 then
			vel += impulseDir.Unit * rng:NextNumber(6, 12)
		end
		piece.vel = vel
		piece.leaveAt = now + CASCADE * (if count > 1 then (k - 1) / (count - 1) else 0)
		table.insert(pieces, piece)
	end

	-- one sparkle emitter, moved to each block as it leaves
	local sparkle: ParticleEmitter? = nil
	local sparkleAt: Attachment? = nil
	local sparkTexture = spark()
	if sparkTexture and not low then
		local anchor = Instance.new("Part")
		anchor.Anchored = true
		anchor.CanCollide = false
		anchor.CanQuery = false
		anchor.CanTouch = false
		anchor.Transparency = 1
		anchor.Size = Vector3.one * 0.2
		anchor.CFrame = CFrame.identity
		anchor.Parent = holder
		local att = Instance.new("Attachment")
		att.Parent = anchor
		local e = Instance.new("ParticleEmitter")
		e.Texture = sparkTexture
		e.LightEmission = 1
		e.LightInfluence = 0
		e.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.9), NumberSequenceKeypoint.new(1, 0) })
		e.Lifetime = NumberRange.new(0.25, 0.4)
		e.Speed = NumberRange.new(2, 5)
		e.SpreadAngle = Vector2.new(180, 180)
		e.Rotation = NumberRange.new(0, 360)
		e.Enabled = false
		e.Parent = att
		sparkle = e
		sparkleAt = att
	end

	local connection: RBXScriptConnection? = nil
	connection = RunService.RenderStepped:Connect(function(dt)
		local t = os.clock()
		local alive = false
		for _, piece in pieces do
			if piece.done then
				continue
			end
			alive = true
			if t < piece.leaveAt then
				continue -- still part of the fish
			end
			if not piece.left then
				piece.left = true
				piece.flashing = true
				local here = piece.cf.Position
				if not inWater(here) then
					piece.ground = groundBelow(here + Vector3.new(0, 1, 0), ignore)
				end
				if sparkle and sparkleAt then
					sparkleAt.Position = here
					sparkle:Emit(1)
				end
			end
			-- motion: water brakes hard and lifts a little, air lets gravity pull
			local pos = piece.cf.Position
			if inWater(pos) then
				piece.vel = piece.vel * math.exp(-WATER_DRAG * dt) + Vector3.new(0, BUOYANCY * dt, 0)
				piece.spin *= math.exp(-WATER_SPIN_DRAG * dt)
				piece.ground = nil
			else
				piece.vel = piece.vel * math.exp(-AIR_DRAG * dt) - Vector3.new(0, workspace.Gravity * dt, 0)
			end
			pos += piece.vel * dt
			if piece.ground and pos.Y < piece.ground + piece.radius then
				pos = Vector3.new(pos.X, piece.ground + piece.radius, pos.Z)
				piece.vel = Vector3.zero
				piece.spin *= 0.5
			end
			piece.cf = CFrame.new(pos) * CFrame.fromAxisAngle(piece.axis, piece.spin * dt) * piece.cf.Rotation
			-- 2 s after leaving: shrink and fade
			local fade = (t - piece.leaveAt - SCATTERED) / VANISH
			if fade >= 1 then
				piece.done = true
				for _, part in piece.parts do
					part:Destroy()
				end
				continue
			end
			local scale = if fade > 0 then 1 - 0.85 * fade else 1
			local flash = math.exp(-(t - piece.leaveAt) * 16)
			for i, part in piece.parts do
				local offset = piece.offsets[i]
				part.CFrame = piece.cf * (if scale < 1 then CFrame.new(offset.Position * scale) * offset.Rotation else offset)
				if fade > 0 then
					part.Size = piece.sizes[i] * scale
					part.Transparency = math.max(piece.alphas[i], fade)
				end
				if piece.flashing then
					part.Color = if flash > 0.03 then piece.colors[i]:Lerp(FLASH, flash) else piece.colors[i]
				end
			end
			if flash <= 0.03 then
				piece.flashing = false
			end
		end
		if not alive then
			if connection then
				connection:Disconnect()
			end
			holder:Destroy()
		end
	end)
end

return Disintegrate

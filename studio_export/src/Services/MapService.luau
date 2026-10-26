-- Map rotation and the geometry of each map's water: where fish spawn, where hooks land, where baits
-- appear, and who has left the arena. Every map stays in the world (PondMapBuilder, MapInstaller); a
-- round only picks one. The active map's water is published on FishGame for the clients:
-- MapName, MapWaterShape ("Plane" | "Sphere"), MapWaterLevel, MapWaterCenter, MapWaterRadius.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame.Config)
local FishService = require(script.Parent.FishService)

local MapService = {}

MapService.ORDER = { "Pond", "Aquarium", "Ballon", "Ocean" }
local MODELS = { Pond = "PondMap", Aquarium = "AquariumMap", Ballon = "BallonMap", Ocean = "OceanMap" }
local VOID_MARGIN = 14 -- studs outside the bubble before a fish counts as thrown out (a leap goes ~10)
local VOID_TIME = 0.8 -- seconds outside before it is gone
local FALL_LIMIT = -160 -- anything below this fell out of the world

local rotation = 0
local outside: { [any]: number } = {} -- fish outside the ball map's bubble -> since when
MapService.current = nil :: Model?

function MapService.get(name: string): Model?
	return MODELS[name] and workspace:FindFirstChild(MODELS[name]) or nil
end

-- picks the round's map: the admin's choice, or the next one in the rotation
function MapService.choose(name: string?): Model
	if not name or not MapService.get(name) then
		for _ = 1, #MapService.ORDER do
			rotation = rotation % #MapService.ORDER + 1
			local candidate = MapService.ORDER[rotation]
			if MapService.get(candidate) then
				name = candidate
				break
			end
		end
	end
	local map = MapService.get(name :: string) :: Model
	MapService.current = map
	table.clear(outside)
	FishGame:SetAttribute("MapName", name)
	FishGame:SetAttribute("MapWaterShape", map:GetAttribute("WaterShape") or "Plane")
	FishGame:SetAttribute("MapWaterLevel", map:GetAttribute("WaterLevel") or Config.WATER_LEVEL)
	FishGame:SetAttribute("MapWaterCenter", map:GetAttribute("WaterCenter") or Vector3.zero)
	FishGame:SetAttribute("MapWaterRadius", map:GetAttribute("WaterRadius") or 0)
	return map
end

local function isSphere(map: Model): boolean
	return map:GetAttribute("WaterShape") == "Sphere"
end

local function level(map: Model): number
	return map:GetAttribute("WaterLevel") or Config.WATER_LEVEL
end

local function sphere(map: Model): (Vector3, number)
	return map:GetAttribute("WaterCenter") or Vector3.zero, map:GetAttribute("WaterRadius") or 100
end

local function randomDirection(): Vector3
	local z = math.random() * 2 - 1
	local a = math.random() * math.pi * 2
	local r = math.sqrt(1 - z * z)
	return Vector3.new(r * math.cos(a), z, r * math.sin(a))
end

-- depth under the surface (negative above it) and the surface's outward normal there
function MapService.depth(map: Model, pos: Vector3): (number, Vector3)
	if isSphere(map) then
		local centre, radius = sphere(map)
		local out = pos - centre
		local d = out.Magnitude
		return radius - d, if d > 1e-3 then out / d else Vector3.yAxis
	end
	return level(map) - pos.Y, Vector3.yAxis
end

-- is this surface point inside the playable part of the map? (sphere maps: everywhere)
function MapService.inArena(map: Model, p: Vector3): boolean
	if isSphere(map) then
		return true
	end
	local lo, hi = map:GetAttribute("ArenaMin"), map:GetAttribute("ArenaMax")
	if lo and hi then
		return p.X > lo.X and p.X < hi.X and p.Z > lo.Z and p.Z < hi.Z
	end
	local rx, rz = map:GetAttribute("PondRadiusX") or 100, map:GetAttribute("PondRadiusZ") or 80
	return (p.X / rx) ^ 2 + (p.Z / rz) ^ 2 < 0.8
end

-- a random point of the water surface inside the arena, with the surface's up there
function MapService.surfacePoint(map: Model): (Vector3, Vector3)
	if isSphere(map) then
		local centre, radius = sphere(map)
		local dir = randomDirection()
		return centre + dir * radius, dir
	end
	local lo, hi = map:GetAttribute("ArenaMin"), map:GetAttribute("ArenaMax")
	if lo and hi then
		return Vector3.new(lo.X + math.random() * (hi.X - lo.X), level(map), lo.Z + math.random() * (hi.Z - lo.Z)), Vector3.yAxis
	end
	local rx, rz = map:GetAttribute("PondRadiusX") or 100, map:GetAttribute("PondRadiusZ") or 80
	local a, r = math.random() * math.pi * 2, math.sqrt(math.random()) * 0.85
	return Vector3.new(math.cos(a) * rx * r, level(map), math.sin(a) * rz * r), Vector3.yAxis
end

-- where a fisherman's hook lands: on the water, in reach of the rod
function MapService.castTarget(map: Model, from: Vector3): (Vector3, Vector3)
	if isSphere(map) then
		-- on the part of the bubble that faces the fisherman
		local centre, radius = sphere(map)
		local toward = (from - centre).Unit
		for _ = 1, 30 do
			local dir = (toward + randomDirection() * 0.75).Unit
			local p = centre + dir * radius
			local d = (p - from).Magnitude
			if d > 14 and d < 90 then
				return p, dir
			end
		end
		return centre + toward * radius, toward
	end
	local best, bestUp = nil, Vector3.yAxis
	for _ = 1, 40 do
		local p, up = MapService.surfacePoint(map)
		local d = ((p - from) * Vector3.new(1, 0, 1)).Magnitude
		if d > 18 and d < 100 then
			return p, up
		end
		if not best or d < ((best - from) * Vector3.new(1, 0, 1)).Magnitude then
			best, bestUp = p, up
		end
	end
	return best, bestUp
end

-- a random point under the surface (baits, wandering bots)
function MapService.waterPoint(map: Model, depth: number): Vector3
	local p, up = MapService.surfacePoint(map)
	return p - up * depth
end

-- a spawn spot for a fish: the map's spawn markers, or (pond) a random spot between bed and surface
local rayParams = RaycastParams.new()
rayParams.FilterType = Enum.RaycastFilterType.Include

function MapService.spawnCFrame(map: Model, depthMargin: number?): CFrame
	local yaw = CFrame.Angles(0, math.random() * math.pi * 2, 0)
	local markers = map:FindFirstChild("PlayerSpawnPoints")
	if markers and #markers:GetChildren() > 0 then
		local list = markers:GetChildren()
		local p = list[math.random(1, #list)].Position
		local jitter = Vector3.new(math.random() - 0.5, math.random() - 0.5, math.random() - 0.5) * 6
		return CFrame.new(p + jitter) * yaw
	end
	local top = level(map) - (depthMargin or 3)
	rayParams.FilterDescendantsInstances = { map:FindFirstChild("Ground") }
	for _ = 1, 40 do
		local p = MapService.surfacePoint(map)
		local hit = workspace:Raycast(Vector3.new(p.X, 80, p.Z), Vector3.new(0, -300, 0), rayParams)
		local bed = hit and hit.Position.Y or level(map) - 20
		if bed < level(map) - 9 then
			local y = bed + 4 + math.random() * math.max(0, top - (bed + 4))
			return CFrame.new(p.X, y, p.Z) * yaw
		end
	end
	return CFrame.new(0, level(map) - 10, 0) * yaw
end

-- ------------------------------------------------------------------------------------------ the void
-- On the ball map, a fish thrown out of the bubble falls into the void and is eliminated; on any map,
-- a fish that fell out of the world is too.
local acc = 0
RunService.Heartbeat:Connect(function(dt)
	acc += dt
	if acc < 0.2 then
		return
	end
	acc = 0
	local map = MapService.current
	local t = os.clock()
	for _, info in FishService.fish do
		if not FishService.alive(info) or info.model:GetAttribute("Caught") then
			outside[info] = nil
			continue
		end
		local pos = info.root.Position
		local gone = pos.Y < FALL_LIMIT
		if not gone and map and isSphere(map) then
			local depth = MapService.depth(map, pos)
			if depth < -VOID_MARGIN * math.max(1, info.model:GetScale()) then
				outside[info] = outside[info] or t
				gone = t - outside[info] > VOID_TIME or depth < -60
			else
				outside[info] = nil
			end
		end
		if gone then
			outside[info] = nil
			info.humanoid.Health = 0
		end
	end
end)

return MapService

-- Plays the rendered water loop on every water surface (parts tagged "WaterSurface", one per map) and
-- lets the pattern drift slowly. Surfaces stream in and out with the maps.
local CollectionService = game:GetService("CollectionService")
local ContentProvider = game:GetService("ContentProvider")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local ClientState = require(FishGame:WaitForChild("ClientState"))
local FRAMES = require(FishGame:WaitForChild("WaterFrames"))
local FPS = 12
local DRIFT = Vector2.new(0.4, 0.25) -- studs per second

local textures: { [Texture]: boolean } = {}
local function track(surface: Instance)
	for _, child in surface:GetChildren() do
		if child:IsA("Texture") then
			textures[child] = true
		end
	end
end
CollectionService:GetInstanceAddedSignal("WaterSurface"):Connect(track)
CollectionService:GetInstanceRemovedSignal("WaterSurface"):Connect(function(surface)
	for _, child in surface:GetChildren() do
		textures[child] = nil
	end
end)
for _, surface in CollectionService:GetTagged("WaterSurface") do
	track(surface)
end

-- load every frame before animating so a swap never shows an empty surface
ContentProvider:PreloadAsync(FRAMES)

local clock = 0
local current = 0
RunService.RenderStepped:Connect(function(dt)
	if ClientState.performance then
		return -- performance mode: the water keeps a still frame
	end
	clock += dt
	local frame = math.floor(clock * FPS) % #FRAMES + 1
	local swap = frame ~= current
	current = frame
	for texture in textures do
		if not texture.Parent then
			textures[texture] = nil
			continue
		end
		if swap then
			texture.Texture = FRAMES[frame]
		end
		texture.OffsetStudsU = (clock * DRIFT.X) % texture.StudsPerTileU
		texture.OffsetStudsV = (clock * DRIFT.Y) % texture.StudsPerTileV
	end
end)

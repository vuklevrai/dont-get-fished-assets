-- Plays the rendered water loop on the pond surface (flipbook) and lets the pattern drift slowly.
local ContentProvider = game:GetService("ContentProvider")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FRAMES = require(ReplicatedStorage:WaitForChild("FishGame"):WaitForChild("WaterFrames"))
local FPS = 12
local DRIFT = Vector2.new(0.4, 0.25) -- studs per second

local surface = workspace:WaitForChild("PondMap"):WaitForChild("Water"):WaitForChild("WaterSurface")
local textures: { Texture } = {}
for _, child in surface:GetChildren() do
	if child:IsA("Texture") then
		table.insert(textures, child)
	end
end

-- load every frame before animating so a swap never shows an empty surface
ContentProvider:PreloadAsync(FRAMES)

local clock = 0
local current = 0
RunService.RenderStepped:Connect(function(dt)
	clock += dt
	local frame = math.floor(clock * FPS) % #FRAMES + 1
	local swap = frame ~= current
	current = frame
	for _, texture in textures do
		if swap then
			texture.Texture = FRAMES[frame]
		end
		texture.OffsetStudsU = (clock * DRIFT.X) % texture.StudsPerTileU
		texture.OffsetStudsV = (clock * DRIFT.Y) % texture.StudsPerTileV
	end
end)

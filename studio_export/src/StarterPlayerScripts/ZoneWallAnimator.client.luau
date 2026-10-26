-- The ocean map's storm wall (parts tagged "ZoneWall"): the Blender flipbook (fx/zone_wall_flipbook.png,
-- 4x4 frames that each tile horizontally) is played on both big faces through a SurfaceGui, since a
-- Texture cannot pick one frame of a sheet. Performance mode shows the still version instead.
local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local ClientState = require(FishGame:WaitForChild("ClientState"))
local FxAssets = require(FishGame:WaitForChild("FxAssets"))

local FPS = 12
local FRAME = 256 -- pixels of one frame in the sheet
local PIXELS_PER_STUD = 4

local labels: { [ImageLabel]: boolean } = {}

local function dress(wall: Instance)
	if not wall:IsA("BasePart") or wall:FindFirstChild("ZoneGui") then
		return
	end
	local size = wall.Size
	-- the two big faces: the wall is thin along its smallest axis
	local faces, height = {}, size.Y
	if size.X <= size.Z then
		faces = { Enum.NormalId.Left, Enum.NormalId.Right }
	else
		faces = { Enum.NormalId.Front, Enum.NormalId.Back }
	end
	wall.LocalTransparencyModifier = 1 -- the texture is the look
	for _, face in faces do
		local sg = Instance.new("SurfaceGui")
		sg.Name = "ZoneGui"
		sg.Face = face
		sg.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
		sg.PixelsPerStud = PIXELS_PER_STUD
		sg.LightInfluence = 0
		sg.Brightness = 1.4
		sg.Parent = wall
		local img = Instance.new("ImageLabel")
		img.Size = UDim2.fromScale(1, 1)
		img.BackgroundTransparency = 1
		img.ScaleType = Enum.ScaleType.Tile
		-- one tile is as tall as the wall, so the glowing water line sits at its foot
		img.TileSize = UDim2.fromOffset(height * PIXELS_PER_STUD, height * PIXELS_PER_STUD)
		img.Image = FxAssets.ZoneWallFlipbook
		img.ImageRectSize = Vector2.new(FRAME, FRAME)
		img.Parent = sg
		labels[img] = true
	end
end

CollectionService:GetInstanceAddedSignal("ZoneWall"):Connect(dress)
for _, wall in CollectionService:GetTagged("ZoneWall") do
	dress(wall)
end

local clock = 0
local shown = -1
RunService.RenderStepped:Connect(function(dt)
	clock += dt
	local frame = ClientState.performance and -1 or math.floor(clock * FPS) % 16
	if frame == shown then
		return
	end
	shown = frame
	for img in labels do
		if not img.Parent then
			labels[img] = nil
		elseif frame < 0 then
			img.Image = FxAssets.ZoneWallStatic
			img.ImageRectSize = Vector2.zero
			img.ImageRectOffset = Vector2.zero
		else
			img.Image = FxAssets.ZoneWallFlipbook
			img.ImageRectSize = Vector2.new(FRAME, FRAME)
			img.ImageRectOffset = Vector2.new(frame % 4, math.floor(frame / 4)) * FRAME
		end
	end
end)

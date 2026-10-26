-- Escape minigame while hooked: a pointer spins around a red ring; click (or Space) while it is over the
-- green arc to break free. A miss costs 2 HP, shakes the screen, flashes it red and makes the pointer
-- tremble before it starts again. Speed and arc size come from the server (harder as the round goes on).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local ClientState = require(FishGame:WaitForChild("ClientState"))
local Remotes = FishGame:WaitForChild("Remotes")

local player = Players.LocalPlayer
local RADIUS = 120
local SEGMENTS = 72

local gui = Instance.new("ScreenGui")
gui.Name = "CatchMinigame"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.Enabled = false
gui.DisplayOrder = 10
gui.Parent = player:WaitForChild("PlayerGui")

local vignette = Instance.new("Frame")
vignette.Size = UDim2.fromScale(1, 1)
vignette.BackgroundColor3 = Color3.fromRGB(10, 14, 30)
vignette.BackgroundTransparency = 0.7
vignette.Parent = gui

local flash = Instance.new("Frame")
flash.Size = UDim2.fromScale(1, 1)
flash.BackgroundColor3 = Color3.fromRGB(255, 20, 20)
flash.BackgroundTransparency = 1
flash.ZIndex = 20
flash.Parent = gui

local holder = Instance.new("Frame")
holder.AnchorPoint = Vector2.new(0.5, 0.5)
-- off to the side so the struggling fish stays visible in the middle of the screen
holder.Position = UDim2.fromScale(0.74, 0.55)
holder.Size = UDim2.fromOffset(RADIUS * 2 + 40, RADIUS * 2 + 40)
holder.BackgroundTransparency = 1
holder.Parent = gui

local title = Instance.new("TextLabel")
title.AnchorPoint = Vector2.new(0.5, 1)
title.Position = UDim2.new(0.5, 0, 0, -14)
title.Size = UDim2.fromOffset(520, 46)
title.BackgroundTransparency = 1
title.Font = Enum.Font.FredokaOne
title.TextScaled = true
title.TextColor3 = Color3.new(1, 1, 1)
title.Text = "YOU'VE BEEN HOOKED!"
title.Parent = holder
local ts = Instance.new("UIStroke", title)
ts.Thickness = 3
ts.Color = Color3.fromRGB(120, 10, 10)

local hint = Instance.new("TextLabel")
hint.AnchorPoint = Vector2.new(0.5, 0)
hint.Position = UDim2.new(0.5, 0, 1, 10)
hint.Size = UDim2.fromOffset(520, 28)
hint.BackgroundTransparency = 1
hint.Font = Enum.Font.GothamBlack
hint.TextScaled = true
hint.TextColor3 = Color3.fromRGB(200, 255, 200)
hint.Text = "Click when the pointer is on GREEN to escape!"
hint.Parent = holder
local hs = Instance.new("UIStroke", hint)
hs.Thickness = 2
hs.Color = Color3.fromRGB(10, 30, 10)

-- the ring, made of small blocks
local ringSegments = {}
for i = 0, SEGMENTS - 1 do
	local a = math.rad(i / SEGMENTS * 360)
	local seg = Instance.new("Frame")
	seg.AnchorPoint = Vector2.new(0.5, 0.5)
	seg.Size = UDim2.fromOffset(13, 22)
	seg.Position = UDim2.new(0.5, math.sin(a) * RADIUS, 0.5, -math.cos(a) * RADIUS)
	seg.Rotation = math.deg(a)
	seg.BorderSizePixel = 0
	seg.Parent = holder
	ringSegments[i] = seg
end
local center = Instance.new("Frame")
center.AnchorPoint = Vector2.new(0.5, 0.5)
center.Position = UDim2.fromScale(0.5, 0.5)
center.Size = UDim2.fromOffset(36, 36)
center.BackgroundColor3 = Color3.fromRGB(240, 240, 240)
center.Parent = holder
Instance.new("UICorner", center).CornerRadius = UDim.new(1, 0)

-- the pointer spins with its container
local spinner = Instance.new("Frame")
spinner.AnchorPoint = Vector2.new(0.5, 0.5)
spinner.Position = UDim2.fromScale(0.5, 0.5)
spinner.Size = UDim2.fromOffset(RADIUS * 2, RADIUS * 2)
spinner.BackgroundTransparency = 1
spinner.Parent = holder
local pointer = Instance.new("Frame")
pointer.AnchorPoint = Vector2.new(0.5, 0)
pointer.Position = UDim2.new(0.5, 0, 0, -18)
pointer.Size = UDim2.fromOffset(8, RADIUS + 18)
pointer.BackgroundColor3 = Color3.new(1, 1, 1)
pointer.Parent = spinner
Instance.new("UICorner", pointer).CornerRadius = UDim.new(1, 0)
local ps = Instance.new("UIStroke", pointer)
ps.Thickness = 2
ps.Color = Color3.fromRGB(20, 20, 20)

local active = false
local angle = 0
local speed, arc = 150, 100
local greenStart = 0
local trembleUntil = 0

local RED, GREEN = Color3.fromRGB(220, 40, 40), Color3.fromRGB(60, 220, 80)

local function inGreen(a: number): boolean
	local d = (a - greenStart) % 360
	return d <= arc
end

local function paintRing()
	for i, seg in ringSegments do
		local a = (i + 0.5) / SEGMENTS * 360
		seg.BackgroundColor3 = inGreen(a) and GREEN or RED
	end
end

local function newGreen()
	-- never right under the pointer
	greenStart = (angle + 90 + math.random() * (360 - arc - 120)) % 360
	paintRing()
end

local function close()
	active = false
	gui.Enabled = false
	ClientState.setUiOpen("Catch", false)
end

local function attempt()
	if not active or os.clock() < trembleUntil then
		return
	end
	if inGreen(angle) then
		hint.Text = "ESCAPED!"
		Remotes.CatchResult:FireServer(true)
	else
		Remotes.CatchResult:FireServer(false)
		ClientState.shake(0.9, 0.25)
		flash.BackgroundTransparency = 0.45
		TweenService:Create(flash, TweenInfo.new(0.3), { BackgroundTransparency = 1 }):Play()
		trembleUntil = os.clock() + 0.45
	end
end

Remotes.Caught.OnClientEvent:Connect(function(data)
	speed = data.pointerSpeed or 150
	arc = math.clamp(data.greenArc or 100, 10, 300)
	angle = math.random() * 360
	newGreen()
	hint.Text = "Click when the pointer is on GREEN to escape!"
	trembleUntil = 0
	active = true
	gui.Enabled = true
	ClientState.setUiOpen("Catch", true)
end)

Remotes.Released.OnClientEvent:Connect(close)
player.CharacterAdded:Connect(close)

UserInputService.InputBegan:Connect(function(input)
	if input.UserInputType == Enum.UserInputType.MouseButton1 or input.KeyCode == Enum.KeyCode.Space then
		attempt()
	end
end)

local wasTrembling = false
RunService.RenderStepped:Connect(function(dt)
	if not active then
		return
	end
	local character = player.Character
	if not character or not character:GetAttribute("Caught") then
		close()
		return
	end
	if os.clock() < trembleUntil then
		spinner.Rotation = angle + math.random(-6, 6)
		wasTrembling = true
		return
	end
	if wasTrembling then
		wasTrembling = false
		newGreen()
	end
	angle = (angle + speed * dt) % 360
	spinner.Rotation = angle
end)

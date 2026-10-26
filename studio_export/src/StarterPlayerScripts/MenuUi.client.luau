-- Main menu (M, or the button on the left): fish inventory (3D preview, skins, stats, ability, show off)
-- and the shop (empty for now).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame:WaitForChild("Config"))
local ClientState = require(FishGame:WaitForChild("ClientState"))
local FishBuilder = require(FishGame:WaitForChild("FishBuilder"))
local FishSpecies = require(FishGame:WaitForChild("FishSpecies"))
local FishStats = require(FishGame:WaitForChild("FishStats"))
local Remotes = FishGame:WaitForChild("Remotes")

local player = Players.LocalPlayer

local NAVY = Color3.fromRGB(26, 46, 82)
local NAVY_DARK = Color3.fromRGB(16, 30, 56)
local GOLD = Color3.fromRGB(255, 205, 70)
local TEAL = Color3.fromRGB(60, 190, 230)
local FONT = Enum.Font.FredokaOne

local function corner(o, r)
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, r or 12)
	c.Parent = o
end
local function stroke(o, color, t)
	local s = Instance.new("UIStroke")
	s.Color = color
	s.Thickness = t or 2
	s.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	s.Parent = o
	return s
end
local function textStroke(o, color, t)
	local s = Instance.new("UIStroke")
	s.Color = color
	s.Thickness = t or 2
	s.Parent = o
end
local function make(class, parent, props)
	local o = Instance.new(class)
	if o:IsA("GuiObject") then
		o.BorderSizePixel = 0
	end
	if o:IsA("TextLabel") or o:IsA("TextButton") then
		o.Font = FONT
		o.TextScaled = true
		o.TextColor3 = Color3.new(1, 1, 1)
	end
	for k, v in props do
		o[k] = v
	end
	o.Parent = parent
	return o
end
local function button(parent, text, color, props)
	local b = make("TextButton", parent, { Text = text, BackgroundColor3 = color, AutoButtonColor = true })
	for k, v in props or {} do
		b[k] = v
	end
	corner(b, 10)
	stroke(b, Color3.fromRGB(12, 20, 36), 2)
	textStroke(b, Color3.fromRGB(12, 20, 36), 1.5)
	return b
end

local gui = make("ScreenGui", player:WaitForChild("PlayerGui"), { Name = "MenuUi", ResetOnSpawn = false })

-- ------------------------------------------------------------------------------------------ menu button
local menuButton = make("TextButton", gui, { Name = "MenuButton", AnchorPoint = Vector2.new(0, 0.5), Position = UDim2.new(0, 14, 0.5, 0),
	Size = UDim2.fromOffset(58, 58), BackgroundColor3 = NAVY, Text = "", AutoButtonColor = true })
corner(menuButton, 16)
stroke(menuButton, GOLD, 3)
for i = 0, 2 do
	local bar = make("Frame", menuButton, { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.new(0.5, 0, 0, 18 + i * 10),
		Size = UDim2.fromOffset(28, 5), BackgroundColor3 = Color3.new(1, 1, 1) })
	corner(bar, 3)
end
local keyHint = make("TextLabel", menuButton, { AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 1, 4), Size = UDim2.fromOffset(40, 16),
	BackgroundTransparency = 1, Text = "M", Font = Enum.Font.GothamBlack })
textStroke(keyHint, Color3.fromRGB(10, 20, 40), 2)

-- ------------------------------------------------------------------------------------------ panel
local panel = make("Frame", gui, { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.5), Size = UDim2.fromOffset(760, 470),
	BackgroundColor3 = NAVY, Visible = false })
corner(panel, 20)
stroke(panel, GOLD, 4)
local header = make("TextLabel", panel, { Position = UDim2.fromOffset(24, 12), Size = UDim2.fromOffset(200, 40), BackgroundTransparency = 1,
	Text = "MENU", TextXAlignment = Enum.TextXAlignment.Left })
textStroke(header, NAVY_DARK, 3)
local closeButton = button(panel, "X", Color3.fromRGB(225, 70, 60), { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -14, 0, 14),
	Size = UDim2.fromOffset(40, 40) })

local tabs = {}
local pages = {}
local function addTab(name, text, x)
	local b = button(panel, text, NAVY_DARK, { Position = UDim2.fromOffset(x, 16), Size = UDim2.fromOffset(150, 36) })
	tabs[name] = b
	local page = make("Frame", panel, { Position = UDim2.fromOffset(18, 66), Size = UDim2.new(1, -36, 1, -84), BackgroundTransparency = 1, Visible = false })
	pages[name] = page
	return b, page
end
local fishTab, fishPage = addTab("Fish", "\u{1F41F} FISH", 210)
local shopTab, shopPage = addTab("Shop", "\u{1F6D2} SHOP", 372)

-- ------------------------------------------------------------------------------------------ fish page
local list = make("ScrollingFrame", fishPage, { Size = UDim2.new(0, 190, 1, 0), BackgroundColor3 = NAVY_DARK, ScrollBarThickness = 6,
	CanvasSize = UDim2.new(), AutomaticCanvasSize = Enum.AutomaticSize.Y })
corner(list, 14)
make("UIPadding", list, { PaddingTop = UDim.new(0, 10), PaddingLeft = UDim.new(0, 10), PaddingRight = UDim.new(0, 10) })
make("UIListLayout", list, { Padding = UDim.new(0, 8), SortOrder = Enum.SortOrder.LayoutOrder })


local detail = make("Frame", fishPage, { Position = UDim2.fromOffset(206, 0), Size = UDim2.new(1, -206, 1, 0), BackgroundTransparency = 1 })
local viewport = make("ViewportFrame", detail, { Size = UDim2.fromOffset(250, 230), BackgroundColor3 = Color3.fromRGB(70, 170, 225),
	Ambient = Color3.fromRGB(170, 180, 200), LightColor = Color3.fromRGB(255, 250, 240), LightDirection = Vector3.new(-1, -2, -1) })
corner(viewport, 16)
stroke(viewport, Color3.fromRGB(12, 20, 36), 3)
local world = make("WorldModel", viewport, {})
local vpCamera = make("Camera", viewport, { FieldOfView = 40 })
viewport.CurrentCamera = vpCamera
local vpGradient = make("UIGradient", viewport, { Rotation = 90,
	Color = ColorSequence.new(Color3.fromRGB(140, 220, 255), Color3.fromRGB(30, 120, 200)) })

local nameLabel = make("TextLabel", detail, { Position = UDim2.fromOffset(264, 0), Size = UDim2.new(1, -264, 0, 40), BackgroundTransparency = 1,
	Text = "", TextXAlignment = Enum.TextXAlignment.Left })
textStroke(nameLabel, NAVY_DARK, 3)

local skinRow = make("Frame", detail, { Position = UDim2.fromOffset(264, 46), Size = UDim2.new(1, -264, 0, 30), BackgroundTransparency = 1 })
make("UIListLayout", skinRow, { FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 6), VerticalAlignment = Enum.VerticalAlignment.Center,
	SortOrder = Enum.SortOrder.LayoutOrder })
make("TextLabel", skinRow, { Size = UDim2.fromOffset(54, 22), BackgroundTransparency = 1, Text = "Skin", Font = Enum.Font.GothamBlack,
	TextColor3 = Color3.fromRGB(190, 215, 255), LayoutOrder = -1 })

local statsBox = make("Frame", detail, { Position = UDim2.fromOffset(264, 84), Size = UDim2.new(1, -264, 0, 108), BackgroundTransparency = 1 })
make("UIListLayout", statsBox, { Padding = UDim.new(0, 8), SortOrder = Enum.SortOrder.LayoutOrder })
local statBars = {}
for statIndex, stat in { { "Speed", Color3.fromRGB(80, 210, 255) }, { "Health", Color3.fromRGB(110, 225, 100) }, { "Size", Color3.fromRGB(255, 180, 60) } } do
	local row = make("Frame", statsBox, { Size = UDim2.new(1, 0, 0, 28), BackgroundTransparency = 1, LayoutOrder = statIndex })
	make("TextLabel", row, { Size = UDim2.fromOffset(80, 24), Position = UDim2.fromOffset(0, 2), BackgroundTransparency = 1, Text = stat[1],
		Font = Enum.Font.GothamBlack, TextXAlignment = Enum.TextXAlignment.Left })
	local cells = {}
	for i = 1, 5 do
		local cell = make("Frame", row, { Position = UDim2.fromOffset(86 + (i - 1) * 42, 3), Size = UDim2.fromOffset(38, 22),
			BackgroundColor3 = Color3.fromRGB(40, 56, 88) })
		corner(cell, 6)
		stroke(cell, NAVY_DARK, 2)
		cells[i] = cell
	end
	statBars[stat[1]] = { cells = cells, color = stat[2] }
end

local abilityBox = make("Frame", detail, { Position = UDim2.fromOffset(0, 244), Size = UDim2.new(1, 0, 0, 92), BackgroundColor3 = NAVY_DARK })
corner(abilityBox, 14)
local abilityTitle = make("TextLabel", abilityBox, { Position = UDim2.fromOffset(14, 8), Size = UDim2.new(1, -28, 0, 26), BackgroundTransparency = 1,
	TextXAlignment = Enum.TextXAlignment.Left, TextColor3 = GOLD })
local abilityText = make("TextLabel", abilityBox, { Position = UDim2.fromOffset(14, 36), Size = UDim2.new(1, -28, 0, 48), BackgroundTransparency = 1,
	TextScaled = false, TextSize = 15, TextWrapped = true, Font = Enum.Font.GothamMedium, TextXAlignment = Enum.TextXAlignment.Left,
	TextYAlignment = Enum.TextYAlignment.Top, TextColor3 = Color3.fromRGB(220, 232, 255) })

local selectButton = button(detail, "SELECTED", Color3.fromRGB(70, 190, 90), { Position = UDim2.fromOffset(0, 344), Size = UDim2.fromOffset(250, 44) })
local showOffButton = button(detail, "SHOW OFF: OFF", Color3.fromRGB(150, 110, 230), { Position = UDim2.fromOffset(264, 344), Size = UDim2.new(1, -264, 0, 44) })

-- ------------------------------------------------------------------------------------------ shop page
make("TextLabel", shopPage, { Size = UDim2.new(1, 0, 0, 44), BackgroundTransparency = 1, Text = "SHOP - COMING SOON!", TextColor3 = GOLD })
local shopGrid = make("Frame", shopPage, { Position = UDim2.fromOffset(0, 60), Size = UDim2.new(1, 0, 1, -60), BackgroundTransparency = 1 })
make("UIGridLayout", shopGrid, { CellSize = UDim2.fromOffset(160, 200), CellPadding = UDim2.fromOffset(16, 16),
	HorizontalAlignment = Enum.HorizontalAlignment.Center })
for _ = 1, 4 do
	local card = make("Frame", shopGrid, { BackgroundColor3 = NAVY_DARK })
	corner(card, 14)
	stroke(card, Color3.fromRGB(60, 80, 120), 2)
	make("TextLabel", card, { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.42), Size = UDim2.fromOffset(80, 80),
		BackgroundTransparency = 1, Text = "?", TextColor3 = Color3.fromRGB(90, 110, 150) })
	make("TextLabel", card, { AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(0.5, 0, 1, -12), Size = UDim2.new(1, -20, 0, 22),
		BackgroundTransparency = 1, Text = "Soon", Font = Enum.Font.GothamBlack, TextColor3 = Color3.fromRGB(120, 140, 180) })
end

-- ------------------------------------------------------------------------------------------ preview
local viewed = player:GetAttribute("SelectedFish") or Config.DEFAULT_SPECIES
local previewModel: Model? = nil
local previewBase = 1

local function buildPreview(speciesId)
	if previewModel then
		previewModel:Destroy()
		previewModel = nil
	end
	local species = FishSpecies[speciesId]
	if not species then
		return
	end
	local fish = FishBuilder.build(species.Model, "Preview")
	for _, d in fish:GetDescendants() do
		if d:IsA("Humanoid") or d:IsA("LinearVelocity") or d:IsA("AlignOrientation") then
			d:Destroy()
		elseif d:IsA("BasePart") then
			d.Anchored = false
		end
	end
	fish.PrimaryPart.Anchored = true
	fish:SetAttribute("Species", speciesId)
	fish:SetAttribute("PreviewSwim", true)
	-- the preview's size follows the size stat, against a fixed camera
	previewBase = FishStats.factor(species.Size)
	fish:ScaleTo(previewBase)
	fish.Parent = world
	previewModel = fish
	vpCamera.CFrame = CFrame.lookAt(Vector3.new(0, 2, 9.5), Vector3.new(0, 0, 0))
end

local function paintStats(species)
	for stat, bar in statBars do
		local value = species[stat]
		for i, cell in bar.cells do
			cell.BackgroundColor3 = i <= value and bar.color or Color3.fromRGB(40, 56, 88)
		end
	end
end

local function refreshFish()
	for _, c in list:GetChildren() do
		if c:IsA("TextButton") then
			c:Destroy()
		end
	end
	local ids = {}
	for id in FishSpecies do
		table.insert(ids, id)
	end
	table.sort(ids, function(a, b)
		return (FishSpecies[a].Order or 0) < (FishSpecies[b].Order or 0)
	end)
	local selected = player:GetAttribute("SelectedFish") or Config.DEFAULT_SPECIES
	for i, id in ids do
		local species = FishSpecies[id]
		local card = button(list, species.DisplayName, id == viewed and TEAL or Color3.fromRGB(46, 70, 112),
			{ Size = UDim2.new(1, 0, 0, 52), LayoutOrder = i })
		if id == selected then
			local tick = make("TextLabel", card, { AnchorPoint = Vector2.new(1, 0.5), Position = UDim2.new(1, -6, 0.5, 0), Size = UDim2.fromOffset(22, 22),
				BackgroundTransparency = 1, Text = "\u{2714}", TextColor3 = Color3.fromRGB(140, 255, 140) })
			textStroke(tick, NAVY_DARK, 2)
		end
		card.Activated:Connect(function()
			viewed = id
			Remotes.SelectFish:FireServer(id)
			refreshFish()
		end)
	end
	local species = FishSpecies[viewed]
	if not species then
		return
	end
	nameLabel.Text = species.DisplayName
	for _, c in skinRow:GetChildren() do
		if c:IsA("TextButton") then
			c:Destroy()
		end
	end
	for i, skin in species.Skins do
		button(skinRow, skin.Name, i == 1 and GOLD or Color3.fromRGB(46, 70, 112), { Size = UDim2.fromOffset(96, 26), LayoutOrder = i,
			TextColor3 = i == 1 and NAVY_DARK or Color3.new(1, 1, 1) })
	end
	paintStats(species)
	abilityTitle.Text = string.format("%s  \u{2022}  %ds cooldown", string.upper(species.Ability.Name), species.Ability.Cooldown)
	abilityText.Text = species.Ability.Description
	selectButton.Text = viewed == selected and "SELECTED" or "SELECT"
	selectButton.BackgroundColor3 = viewed == selected and Color3.fromRGB(70, 190, 90) or Color3.fromRGB(240, 160, 40)
	if not previewModel or previewModel:GetAttribute("Species") ~= viewed then
		buildPreview(viewed)
	end
end

local function refreshShowOff()
	local on = player:GetAttribute("ShowOff") == true
	showOffButton.Text = on and "SHOW OFF: ON" or "SHOW OFF: OFF"
	showOffButton.BackgroundColor3 = on and Color3.fromRGB(200, 120, 255) or Color3.fromRGB(110, 90, 160)
end

-- ------------------------------------------------------------------------------------------ open / close
local open = false
local current = "Fish"

local function showPage(name)
	current = name
	for n, page in pages do
		page.Visible = n == name
		tabs[n].BackgroundColor3 = n == name and TEAL or NAVY_DARK
	end
	Remotes.SetHolding:FireServer(open and name == "Fish")
end

local function setOpen(value: boolean)
	open = value
	panel.Visible = value
	ClientState.setUiOpen("Menu", value)
	if value then
		viewed = player:GetAttribute("SelectedFish") or Config.DEFAULT_SPECIES
		refreshFish()
		refreshShowOff()
		panel.Size = UDim2.fromOffset(700, 430)
		TweenService:Create(panel, TweenInfo.new(0.18, Enum.EasingStyle.Back), { Size = UDim2.fromOffset(760, 470) }):Play()
		showPage(current)
	else
		Remotes.SetHolding:FireServer(false)
	end
end

menuButton.Activated:Connect(function()
	setOpen(not open)
end)
closeButton.Activated:Connect(function()
	setOpen(false)
end)
fishTab.Activated:Connect(function()
	showPage("Fish")
end)
shopTab.Activated:Connect(function()
	showPage("Shop")
end)
selectButton.Activated:Connect(function()
	Remotes.SelectFish:FireServer(viewed)
end)
showOffButton.Activated:Connect(function()
	Remotes.ShowOff:FireServer(not player:GetAttribute("ShowOff"))
end)
player:GetAttributeChangedSignal("SelectedFish"):Connect(function()
	if open then
		refreshFish()
	end
end)
player:GetAttributeChangedSignal("ShowOff"):Connect(refreshShowOff)
-- the menu closes when the round turns you into a fish
player.CharacterAdded:Connect(function(character)
	if open and character:GetAttribute("Species") then
		setOpen(false)
	end
end)

UserInputService.InputBegan:Connect(function(input, processed)
	if processed or UserInputService:GetFocusedTextBox() then
		return
	end
	if input.KeyCode == Enum.KeyCode.M then
		setOpen(not open)
	end
end)

-- the preview turns slowly
RunService.RenderStepped:Connect(function()
	if open and previewModel and previewModel.PrimaryPart then
		previewModel:PivotTo(CFrame.Angles(0, os.clock() * 0.9, 0) * CFrame.Angles(0, 0, math.rad(8)))
	end
end)

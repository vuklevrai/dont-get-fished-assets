-- Test-phase admin panel (K, or the ADMIN button top-right). Shown only to admins (owner / Studio);
-- every action is checked again by AdminService on the server.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local Workspace = game:GetService("Workspace")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame:WaitForChild("Config"))
local ClientState = require(FishGame:WaitForChild("ClientState"))
local FishSpecies = require(FishGame:WaitForChild("FishSpecies"))
local Remotes = FishGame:WaitForChild("Remotes")

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 32, 44)
local DARK = Color3.fromRGB(18, 20, 28)
local RED = Color3.fromRGB(230, 70, 70)
local GREEN = Color3.fromRGB(70, 190, 100)
local BLUE = Color3.fromRGB(60, 130, 230)
local GREY = Color3.fromRGB(70, 76, 92)
local FONT = Enum.Font.GothamBlack

local function corner(o, r)
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, r or 8)
	c.Parent = o
end
local function make(class, parent, props)
	local o = Instance.new(class)
	if o:IsA("GuiObject") then
		o.BorderSizePixel = 0
	end
	if o:IsA("TextLabel") or o:IsA("TextButton") then
		o.Font = FONT
		o.TextColor3 = Color3.new(1, 1, 1)
		o.TextSize = 14
	end
	for k, v in props do
		o[k] = v
	end
	o.Parent = parent
	return o
end

local gui = make("ScreenGui", player:WaitForChild("PlayerGui"), { Name = "AdminUi", ResetOnSpawn = false, DisplayOrder = 20, Enabled = false })

local toggle = make("TextButton", gui, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -12, 0, 10), Size = UDim2.fromOffset(108, 34),
	BackgroundColor3 = RED, Text = "\u{1F6E0} ADMIN [K]" })
corner(toggle, 10)
make("UIStroke", toggle, { Color = DARK, Thickness = 2, ApplyStrokeMode = Enum.ApplyStrokeMode.Border })

local panel = make("Frame", gui, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -12, 0, 52), Size = UDim2.new(0, 330, 1, -170),
	BackgroundColor3 = PANEL, Visible = false })
corner(panel, 12)
make("UIStroke", panel, { Color = RED, Thickness = 2 })
make("TextLabel", panel, { Position = UDim2.fromOffset(12, 8), Size = UDim2.new(1, -24, 0, 22), BackgroundTransparency = 1,
	Text = "ADMIN  \u{2022}  TEST TOOLS", TextSize = 16, TextXAlignment = Enum.TextXAlignment.Left, TextColor3 = Color3.fromRGB(255, 120, 120) })
local status = make("TextLabel", panel, { Position = UDim2.fromOffset(12, 34), Size = UDim2.new(1, -24, 0, 62), BackgroundColor3 = DARK,
	Font = Enum.Font.RobotoMono, TextSize = 12, TextXAlignment = Enum.TextXAlignment.Left, TextYAlignment = Enum.TextYAlignment.Top,
	TextColor3 = Color3.fromRGB(170, 230, 170), Text = "" })
corner(status, 6)
make("UIPadding", status, { PaddingLeft = UDim.new(0, 6), PaddingTop = UDim.new(0, 4) })

local body = make("ScrollingFrame", panel, { Position = UDim2.fromOffset(8, 102), Size = UDim2.new(1, -16, 1, -110), BackgroundTransparency = 1,
	ScrollBarThickness = 5, CanvasSize = UDim2.new(), AutomaticCanvasSize = Enum.AutomaticSize.Y })
make("UIListLayout", body, { Padding = UDim.new(0, 6), SortOrder = Enum.SortOrder.LayoutOrder })
make("UIPadding", body, { PaddingLeft = UDim.new(0, 4), PaddingRight = UDim.new(0, 8) })

local order = 0
local function section(title)
	order += 1
	make("TextLabel", body, { Size = UDim2.new(1, 0, 0, 20), BackgroundTransparency = 1, Text = string.upper(title), TextSize = 13,
		TextXAlignment = Enum.TextXAlignment.Left, TextColor3 = Color3.fromRGB(150, 160, 190), LayoutOrder = order })
	order += 1
	local grid = make("Frame", body, { Size = UDim2.new(1, 0, 0, 0), AutomaticSize = Enum.AutomaticSize.Y, BackgroundTransparency = 1, LayoutOrder = order })
	make("UIGridLayout", grid, { CellSize = UDim2.new(0.5, -4, 0, 32), CellPadding = UDim2.fromOffset(6, 6), SortOrder = Enum.SortOrder.LayoutOrder })
	return grid
end

local refreshers = {}
local function act(grid, text, color, onClick)
	local b = make("TextButton", grid, { BackgroundColor3 = color, Text = text, AutoButtonColor = true, TextWrapped = true })
	corner(b, 8)
	b.Activated:Connect(onClick)
	return b
end
local function send(action, ...)
	local args = table.pack(...)
	return function()
		Remotes.Admin:FireServer(action, table.unpack(args, 1, args.n))
	end
end
-- a two-state button whose look follows get()
local function switch(grid, text, get, set)
	local b = act(grid, text, GREY, function() end)
	local function paint()
		local on = get()
		b.Text = text .. (on and ": ON" or ": OFF")
		b.BackgroundColor3 = on and GREEN or GREY
	end
	b.Activated:Connect(function()
		set(not get())
		task.delay(0.15, paint)
	end)
	table.insert(refreshers, paint)
	paint()
	return b
end

-- ------------------------------------------------------------------------------------------ game
local gameGrid = section("Game")
act(gameGrid, "\u{25B6} Start endless test", GREEN, send("StartTest"))
act(gameGrid, "\u{2693} Back to lobby", BLUE, send("StopTest"))
switch(gameGrid, "Hold lobby", function()
	return FishGame:GetAttribute("SettingHoldLobby") == true
end, function(on)
	Remotes.Admin:FireServer("Setting", "HoldLobby", on)
end)

-- ------------------------------------------------------------------------------------------ fish
local fishGrid = section("Play as")
local speciesButtons = {}
for id, species in FishSpecies do
	speciesButtons[id] = act(fishGrid, species.DisplayName, GREY, send("SetSpecies", id))
	speciesButtons[id].LayoutOrder = species.Order or 0
end
table.insert(refreshers, function()
	local selected = player:GetAttribute("SelectedFish") or Config.DEFAULT_SPECIES
	for id, b in speciesButtons do
		b.BackgroundColor3 = id == selected and BLUE or GREY
	end
end)

local meGrid = section("My fish")
act(meGrid, "\u{2764} Full heal", GREEN, send("Heal"))
act(meGrid, "\u{2B06} +1 level", Color3.fromRGB(220, 170, 40), send("LevelUp"))
act(meGrid, "\u{1F480} Kill me", RED, send("KillMe"))
switch(meGrid, "God mode", function()
	return player:GetAttribute("GodMode") == true
end, function(on)
	Remotes.Admin:FireServer("GodMode", on)
end)
switch(meGrid, "S = swim back", function()
	return ClientState.backpedal
end, function(on)
	ClientState.backpedal = on
	ClientState.changed:Fire()
end)

-- ------------------------------------------------------------------------------------------ spawning
local spawnGrid = section("Spawn")
act(spawnGrid, "\u{1F41F} Enemy fish", Color3.fromRGB(60, 120, 200), send("SpawnEnemy"))
act(spawnGrid, "\u{1F3A3} Fisherman", Color3.fromRGB(200, 150, 40), send("SpawnFisherman"))
act(spawnGrid, "\u{2B50} Bait: Level", Color3.fromRGB(210, 170, 30), send("SpawnPowerUp", "Level"))
act(spawnGrid, "\u{26A1} Bait: Speed", Color3.fromRGB(40, 170, 210), send("SpawnPowerUp", "Speed"))
act(spawnGrid, "\u{1F47B} Bait: Invisible", Color3.fromRGB(150, 100, 220), send("SpawnPowerUp", "Invisible"))
act(spawnGrid, "Clear enemies", Color3.fromRGB(120, 60, 60), send("ClearEnemies"))
act(spawnGrid, "Clear fishermen", Color3.fromRGB(120, 60, 60), send("ClearFishermen"))

-- ------------------------------------------------------------------------------------------ round settings
local settingsGrid = section("Automatic spawns")
for _, name in { "Fishermen", "Enemies", "PowerUps" } do
	switch(settingsGrid, name, function()
		return FishGame:GetAttribute("Setting" .. name) ~= false
	end, function(on)
		Remotes.Admin:FireServer("Setting", name, on)
	end)
end
local DIFFICULTIES = { "Auto", "Easy", "Medium", "Hard" }
local difficultyButton = act(settingsGrid, "", Color3.fromRGB(160, 80, 160), function() end)
local function paintDifficulty()
	difficultyButton.Text = "Hook minigame: " .. (FishGame:GetAttribute("SettingDifficulty") or "Auto")
end
difficultyButton.Activated:Connect(function()
	local currentIndex = table.find(DIFFICULTIES, FishGame:GetAttribute("SettingDifficulty") or "Auto") or 1
	Remotes.Admin:FireServer("Setting", "Difficulty", DIFFICULTIES[currentIndex % #DIFFICULTIES + 1])
end)
table.insert(refreshers, paintDifficulty)

-- ------------------------------------------------------------------------------------------ status
local function clock(seconds)
	seconds = math.max(0, math.floor(seconds))
	return string.format("%d:%02d", seconds // 60, seconds % 60)
end

local function refreshStatus()
	local now = Workspace:GetServerTimeNow()
	local phase = FishGame:GetAttribute("Phase") or "?"
	local timeText
	if phase == "Round" then
		timeText = clock(now - (FishGame:GetAttribute("RoundStart") or now))
	else
		timeText = clock((FishGame:GetAttribute("PhaseEnd") or now) - now) .. " left"
	end
	local lines = {
		string.format("%s%s  %s   alive %d", phase, FishGame:GetAttribute("TestMode") and " (test)" or "", timeText, FishGame:GetAttribute("Alive") or 0),
		string.format("fishermen %d   enemies %d", FishGame:GetAttribute("Fishermen") or 0, FishGame:GetAttribute("Enemies") or 0),
	}
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if character and character:GetAttribute("Species") and humanoid then
		table.insert(lines, string.format("me: %d/%d HP  lvl %d  size %s  speed x%.2f", math.ceil(humanoid.Health), humanoid.MaxHealth,
			character:GetAttribute("Level") or 1, tostring(character:GetAttribute("Size") or "?"), character:GetAttribute("SpeedFactor") or 1))
	else
		table.insert(lines, "me: on the ship")
	end
	status.Text = table.concat(lines, "\n")
end

-- ------------------------------------------------------------------------------------------ open / close
local open = false
local function setOpen(value)
	open = value and gui.Enabled
	panel.Visible = open
	toggle.BackgroundColor3 = open and Color3.fromRGB(150, 40, 40) or RED
	ClientState.setUiOpen("Admin", open)
	if open then
		for _, f in refreshers do
			f()
		end
		refreshStatus()
	end
end

toggle.Activated:Connect(function()
	setOpen(not open)
end)
UserInputService.InputBegan:Connect(function(input, processed)
	if processed or UserInputService:GetFocusedTextBox() then
		return
	end
	if input.KeyCode == Enum.KeyCode.K then
		setOpen(not open)
	end
end)

local function refreshAdmin()
	gui.Enabled = player:GetAttribute("IsAdmin") == true
	if not gui.Enabled then
		setOpen(false)
	end
end
player:GetAttributeChangedSignal("IsAdmin"):Connect(refreshAdmin)
refreshAdmin()

FishGame.AttributeChanged:Connect(function()
	if open then
		for _, f in refreshers do
			f()
		end
	end
end)
player.AttributeChanged:Connect(function()
	if open then
		for _, f in refreshers do
			f()
		end
	end
end)

task.spawn(function()
	while true do
		if open then
			refreshStatus()
		end
		task.wait(0.25)
	end
end)

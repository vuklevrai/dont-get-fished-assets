-- In-game HUD: round banner (top), health bar + level + ability cooldown (bottom), active effects,
-- power-up toasts, and a camera shake whenever the fish takes damage.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame:WaitForChild("Config"))
local ClientState = require(FishGame:WaitForChild("ClientState"))
local FishSpecies = require(FishGame:WaitForChild("FishSpecies"))
local Remotes = FishGame:WaitForChild("Remotes")

local player = Players.LocalPlayer

local NAVY = Color3.fromRGB(24, 44, 78)
local GOLD = Color3.fromRGB(255, 210, 80)
local FONT = Enum.Font.FredokaOne

local gui = Instance.new("ScreenGui")
gui.Name = "Hud"
gui.ResetOnSpawn = false
gui.Parent = player:WaitForChild("PlayerGui")

local function corner(o, r)
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, r or 12)
	c.Parent = o
end

local function stroke(o, color, t)
	local s = Instance.new("UIStroke")
	s.Color = color
	s.Thickness = t or 2
	s.Parent = o
	return s
end

local function label(parent, props)
	local l = Instance.new("TextLabel")
	l.BackgroundTransparency = 1
	l.Font = FONT
	l.TextColor3 = Color3.new(1, 1, 1)
	l.TextScaled = true
	for k, v in props do
		l[k] = v
	end
	l.Parent = parent
	return l
end

-- ------------------------------------------------------------------------------------------ top banner
local banner = Instance.new("Frame")
banner.AnchorPoint = Vector2.new(0.5, 0)
banner.Position = UDim2.new(0.5, 0, 0, 8)
banner.Size = UDim2.fromOffset(300, 54)
banner.BackgroundColor3 = NAVY
banner.BackgroundTransparency = 0.12
banner.Parent = gui
corner(banner, 14)
stroke(banner, GOLD, 3)
local title = label(banner, { Size = UDim2.new(1, -20, 0, 28), Position = UDim2.fromOffset(10, 4) })
stroke(title, Color3.fromRGB(12, 22, 40), 2)
local detail = label(banner, { Size = UDim2.new(1, -20, 0, 16), Position = UDim2.fromOffset(10, 33), Font = Enum.Font.GothamBold,
	TextColor3 = Color3.fromRGB(190, 225, 255) })
local testBadge = label(banner, { Size = UDim2.fromOffset(84, 20), AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 1, 4),
	Text = "TEST MODE", BackgroundTransparency = 0, BackgroundColor3 = Color3.fromRGB(220, 60, 60), Visible = false })
corner(testBadge, 8)

local function clock(seconds: number): string
	seconds = math.max(0, math.floor(seconds))
	return string.format("%d:%02d", seconds // 60, seconds % 60)
end

-- ------------------------------------------------------------------------------------------ bottom panel
local bottom = Instance.new("Frame")
bottom.AnchorPoint = Vector2.new(0.5, 1)
bottom.Position = UDim2.new(0.5, 0, 1, -18)
bottom.Size = UDim2.fromOffset(470, 78)
bottom.BackgroundTransparency = 1
bottom.Visible = false
bottom.Parent = gui

local levelBadge = Instance.new("Frame")
levelBadge.Size = UDim2.fromOffset(52, 52)
levelBadge.Position = UDim2.fromOffset(0, 18)
levelBadge.Parent = bottom
corner(levelBadge, 26)
stroke(levelBadge, Color3.fromRGB(30, 30, 36), 3)
local levelText = label(levelBadge, { Size = UDim2.fromScale(1, 1) })
stroke(levelText, Color3.fromRGB(30, 30, 36), 2)
label(levelBadge, { Size = UDim2.fromOffset(52, 14), Position = UDim2.fromOffset(0, -16), Text = "LEVEL", Font = Enum.Font.GothamBlack,
	TextColor3 = Color3.fromRGB(230, 240, 255) })

local barBack = Instance.new("Frame")
barBack.Position = UDim2.fromOffset(62, 30)
barBack.Size = UDim2.fromOffset(320, 28)
barBack.BackgroundColor3 = Color3.fromRGB(30, 34, 44)
barBack.Parent = bottom
corner(barBack, 10)
stroke(barBack, Color3.fromRGB(12, 14, 20), 3)
local barFill = Instance.new("Frame")
barFill.Size = UDim2.fromScale(1, 1)
barFill.BackgroundColor3 = Color3.fromRGB(90, 220, 90)
barFill.Parent = barBack
corner(barFill, 10)
local barShine = Instance.new("Frame")
barShine.Size = UDim2.new(1, -8, 0.35, 0)
barShine.Position = UDim2.fromOffset(4, 3)
barShine.BackgroundColor3 = Color3.new(1, 1, 1)
barShine.BackgroundTransparency = 0.7
barShine.Parent = barFill
corner(barShine, 6)
local hpText = label(barBack, { Size = UDim2.new(1, 0, 1, -6), Position = UDim2.fromOffset(0, 3), ZIndex = 3 })
stroke(hpText, Color3.fromRGB(12, 14, 20), 2)
local effects = Instance.new("Frame")
effects.Position = UDim2.fromOffset(62, 0)
effects.Size = UDim2.fromOffset(320, 24)
effects.BackgroundTransparency = 1
effects.Parent = bottom
local effectsLayout = Instance.new("UIListLayout")
effectsLayout.FillDirection = Enum.FillDirection.Horizontal
effectsLayout.Padding = UDim.new(0, 6)
effectsLayout.Parent = effects

local ability = Instance.new("Frame")
ability.Position = UDim2.fromOffset(394, 4)
ability.Size = UDim2.fromOffset(64, 64)
ability.BackgroundColor3 = Color3.fromRGB(255, 150, 40)
ability.ClipsDescendants = true
ability.Parent = bottom
corner(ability, 14)
stroke(ability, Color3.fromRGB(30, 20, 10), 3)
local abilityName = label(ability, { Size = UDim2.new(1, -8, 0, 22), Position = UDim2.fromOffset(4, 12), Text = "DASH" })
stroke(abilityName, Color3.fromRGB(60, 30, 0), 2)
label(ability, { Size = UDim2.new(1, -8, 0, 14), Position = UDim2.fromOffset(4, 40), Text = "Q / RMB", Font = Enum.Font.GothamBlack,
	TextColor3 = Color3.fromRGB(70, 34, 0) })
local cooldownShade = Instance.new("Frame")
cooldownShade.BackgroundColor3 = Color3.fromRGB(10, 14, 24)
cooldownShade.BackgroundTransparency = 0.25
cooldownShade.Size = UDim2.fromScale(1, 0)
cooldownShade.ZIndex = 4
cooldownShade.Parent = ability
local cooldownText = label(ability, { Size = UDim2.fromScale(1, 1), ZIndex = 5, Text = "" })
stroke(cooldownText, Color3.fromRGB(0, 0, 0), 2)

local function effectChip(text: string, color: Color3)
	local chip = label(effects, { Size = UDim2.fromOffset(96, 22), Text = text, BackgroundTransparency = 0.1, BackgroundColor3 = color,
		Font = Enum.Font.GothamBlack })
	corner(chip, 8)
	return chip
end
local chips = {
	speed = effectChip("", Color3.fromRGB(40, 170, 230)),
	invisible = effectChip("", Color3.fromRGB(150, 90, 230)),
	stunned = effectChip("STUNNED", Color3.fromRGB(230, 80, 60)),
}

-- ------------------------------------------------------------------------------------------ toasts
local toast = label(gui, { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.32), Size = UDim2.fromOffset(420, 54),
	Text = "", TextTransparency = 1 })
local toastStroke = stroke(toast, Color3.fromRGB(20, 20, 30), 3)
toastStroke.Transparency = 1

local function showToast(text: string, color: Color3)
	toast.Text = text
	toast.TextColor3 = color
	toast.TextTransparency = 0
	toastStroke.Transparency = 0
	toast.Size = UDim2.fromOffset(300, 40)
	TweenService:Create(toast, TweenInfo.new(0.25, Enum.EasingStyle.Back), { Size = UDim2.fromOffset(420, 54) }):Play()
	task.delay(1.4, function()
		if toast.Text == text then
			TweenService:Create(toast, TweenInfo.new(0.4), { TextTransparency = 1 }):Play()
			TweenService:Create(toastStroke, TweenInfo.new(0.4), { Transparency = 1 }):Play()
		end
	end)
end

Remotes.Effect.OnClientEvent:Connect(function(kind, model, a)
	if model ~= player.Character then
		return
	end
	if kind == "PowerUp" then
		local colors = { Level = Color3.fromRGB(255, 215, 60), Speed = Color3.fromRGB(80, 225, 255), Invisible = Color3.fromRGB(200, 140, 255) }
		local texts = { Level = "LEVEL UP!", Speed = "SPEED BOOST! (20s)", Invisible = "INVISIBLE! (10s)" }
		if a ~= "Level" then
			showToast(texts[a] or "", colors[a] or Color3.new(1, 1, 1))
		end
	elseif kind == "LevelUp" then
		showToast("LEVEL " .. tostring(model:GetAttribute("Level")) .. "!", Color3.fromRGB(255, 215, 60))
	end
end)

-- ------------------------------------------------------------------------------------------ damage shake
local watched: Humanoid? = nil
local lastHealth = 0
local function watch(character: Model)
	local humanoid = character:WaitForChild("Humanoid", 10)
	if not humanoid then
		return
	end
	watched = humanoid
	lastHealth = humanoid.Health
	humanoid.HealthChanged:Connect(function(h)
		if humanoid ~= watched then
			return
		end
		local lost = lastHealth - h
		lastHealth = h
		if lost > 0 and CollectionService:HasTag(character, Config.FISH_TAG) then
			if lost < 10 then
				ClientState.shake(0.22, 0.18)
			else
				ClientState.shake(0.8, 0.35)
			end
		end
	end)
end
player.CharacterAdded:Connect(watch)
if player.Character then
	task.spawn(watch, player.Character)
end

-- ------------------------------------------------------------------------------------------ update
RunService.Heartbeat:Connect(function()
	local now = workspace:GetServerTimeNow()
	local phase = FishGame:GetAttribute("Phase")
	local test = FishGame:GetAttribute("TestMode")
	testBadge.Visible = test == true
	if phase == "Intermission" then
		if FishGame:GetAttribute("SettingHoldLobby") then
			title.Text = "Lobby on hold (admin)"
		else
			title.Text = "Next round in " .. math.max(0, math.ceil((FishGame:GetAttribute("PhaseEnd") or now) - now)) .. "s"
		end
		detail.Text = "Get ready to swim for your life!"
	elseif phase == "Round" then
		title.Text = "\u{23F1} " .. clock(now - (FishGame:GetAttribute("RoundStart") or now))
		local alive = FishGame:GetAttribute("Alive") or 0
		detail.Text = test and "Endless test game" or (alive .. " fish still swimming")
	elseif phase == "Results" then
		local survivors = FishGame:GetAttribute("Survivors") or ""
		title.Text = "Round over!"
		detail.Text = survivors ~= "" and ("Winner: " .. survivors) or "Nobody survived..."
	else
		title.Text = "Don't Get Fished"
		detail.Text = ""
	end

	local character = player.Character
	local isFish = character and CollectionService:HasTag(character, Config.FISH_TAG)
	bottom.Visible = isFish == true
	if not isFish then
		return
	end
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	if not humanoid then
		return
	end
	local ratio = humanoid.MaxHealth > 0 and math.clamp(humanoid.Health / humanoid.MaxHealth, 0, 1) or 0
	barFill.Size = UDim2.fromScale(ratio, 1)
	barFill.BackgroundColor3 = Color3.fromRGB(235, 70, 60):Lerp(Color3.fromRGB(90, 220, 90), math.clamp((ratio - 0.15) / 0.5, 0, 1))
	hpText.Text = string.format("%d / %d HP", math.ceil(humanoid.Health), humanoid.MaxHealth)
	local level = character:GetAttribute("Level") or 1
	levelText.Text = tostring(level)
	levelBadge.BackgroundColor3 = level >= 5 and Color3.fromRGB(255, 200, 40) or Color3.fromRGB(128, 130, 140)

	local species = FishSpecies[character:GetAttribute("Species")]
	abilityName.Text = species and string.upper(species.Ability.Name) or "DASH"
	local cd = character:GetAttribute("AbilityCooldown") or 6
	local left = (character:GetAttribute("AbilityReadyAt") or 0) - now
	if left > 0 then
		cooldownShade.Size = UDim2.fromScale(1, math.clamp(left / cd, 0, 1))
		cooldownText.Text = string.format("%.1f", left)
	else
		cooldownShade.Size = UDim2.fromScale(1, 0)
		cooldownText.Text = ""
	end
	local speedLeft = (character:GetAttribute("SpeedBoostUntil") or 0) - now
	chips.speed.Visible = speedLeft > 0
	chips.speed.Text = "\u{26A1} SPEED " .. math.ceil(speedLeft) .. "s"
	local invLeft = (character:GetAttribute("InvisibleUntil") or 0) - now
	chips.invisible.Visible = character:GetAttribute("Invisible") == true and invLeft > 0
	chips.invisible.Text = "INVISIBLE " .. math.ceil(invLeft) .. "s"
	chips.stunned.Visible = (character:GetAttribute("StunnedUntil") or 0) > now
end)

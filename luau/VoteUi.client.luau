-- Game mode vote during the intermission (LocalScript, StarterPlayer.StarterPlayerScripts.VoteUi).
-- Contract with the server (ReplicatedStorage.FishGame):
--   attributes VoteOpen (bool), VoteEndsAt (number, workspace:GetServerTimeNow()), VotesBattleRoyale and
--   VotesSurvival (numbers), BattleRoyaleLocked (bool: fewer than 3 players), NextMode ("BattleRoyale" |
--   "Survival", the result); remote Remotes.Vote (RemoteEvent): Vote:FireServer("BattleRoyale" | "Survival"),
--   a player may change their vote.
-- Two big cards side by side at the bottom centre of the screen, each with its vote bar and count; the card voted
-- for glows; a countdown on top ("VOTE ENDS IN 7"); a locked Battle Royale card is greyed out with a padlock and
-- "3 players minimum". When the vote closes, the result is announced in big letters for 2 s.
-- Keys 1 / 2 vote too. Cartoon style: rounded corners, thick strokes, FredokaOne. A UIScale fits phones.
-- Texts are in English (international audience). Uses ClientState.setUiOpen while open (frees the mouse).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local ClientState = require(FishGame:WaitForChild("ClientState"))
local Remotes = FishGame:WaitForChild("Remotes")

local player = Players.LocalPlayer
local FONT = Enum.Font.FredokaOne
local OUTLINE = Color3.fromRGB(28, 30, 48)
local WHITE = Color3.new(1, 1, 1)
local MODES = {
	{
		id = "BattleRoyale",
		title = "BATTLE ROYALE",
		text = "Last fish alive wins",
		icon = "🐟",
		badge = "👑",
		color = Color3.fromRGB(40, 146, 226),
		key = Enum.KeyCode.One,
	},
	{
		id = "Survival",
		title = "SURVIVAL",
		text = "Survive waves of fishermen and zombie fish",
		icon = "💀",
		badge = nil,
		color = Color3.fromRGB(190, 40, 90),
		key = Enum.KeyCode.Two,
	},
}
local CARD_W, CARD_H, GAP = 300, 196, 26

local myVote: string? = nil
local cards = {}

local function corner(parent: Instance, radius: number)
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, radius)
	c.Parent = parent
	return c
end

local function stroke(parent: Instance, thickness: number, color: Color3?, contextual: boolean?)
	local s = Instance.new("UIStroke")
	s.Thickness = thickness
	s.Color = color or OUTLINE
	s.LineJoinMode = Enum.LineJoinMode.Round
	if contextual then
		s.ApplyStrokeMode = Enum.ApplyStrokeMode.Contextual
	else
		s.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	end
	s.Parent = parent
	return s
end

local function label(parent: Instance, text: string, size: number, color: Color3?): TextLabel
	local t = Instance.new("TextLabel")
	t.BackgroundTransparency = 1
	t.Font = FONT
	t.Text = text
	t.TextSize = size
	t.TextColor3 = color or WHITE
	t.TextWrapped = true
	t.Parent = parent
	stroke(t, math.max(1.5, size / 12), OUTLINE, true)
	return t
end

-- --------------------------------------------------------------------------- the screen
local gui = Instance.new("ScreenGui")
gui.Name = "VoteUi"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.DisplayOrder = 8
gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
gui.Enabled = false
gui.Parent = player:WaitForChild("PlayerGui")

local panel = Instance.new("Frame")
panel.Name = "Panel"
panel.AnchorPoint = Vector2.new(0.5, 1)
panel.Position = UDim2.new(0.5, 0, 1, -28)
panel.Size = UDim2.fromOffset(2 * CARD_W + GAP, CARD_H + 64)
panel.BackgroundTransparency = 1
panel.Parent = gui
local panelFit = Instance.new("UIScale") -- phones: the whole panel shrinks around its bottom-centre anchor
panelFit.Parent = panel

local countdown = label(panel, "VOTE ENDS IN 10", 30)
countdown.Name = "Countdown"
countdown.AnchorPoint = Vector2.new(0.5, 0)
countdown.Position = UDim2.fromScale(0.5, 0)
countdown.Size = UDim2.new(1, 0, 0, 40)
local countdownScale = Instance.new("UIScale")
countdownScale.Parent = countdown

-- the result, centre screen (a holder that fits the screen, the label inside pops)
local resultHolder = Instance.new("Frame")
resultHolder.AnchorPoint = Vector2.new(0.5, 0.5)
resultHolder.Position = UDim2.fromScale(0.5, 0.42)
resultHolder.Size = UDim2.fromOffset(900, 160)
resultHolder.BackgroundTransparency = 1
resultHolder.Parent = gui
local resultFit = Instance.new("UIScale")
resultFit.Parent = resultHolder
local result = label(resultHolder, "", 84)
result.Name = "Result"
result.AnchorPoint = Vector2.new(0.5, 0.5)
result.Position = UDim2.fromScale(0.5, 0.6)
result.Size = UDim2.fromOffset(900, 110)
result.Visible = false
local resultScale = Instance.new("UIScale")
resultScale.Parent = result
local resultSub = label(result, "NEXT ROUND", 30)
resultSub.AnchorPoint = Vector2.new(0.5, 1)
resultSub.Position = UDim2.fromScale(0.5, 0)
resultSub.Size = UDim2.new(1, 0, 0, 36)

local function buildCard(mode, index: number)
	local card = Instance.new("TextButton")
	card.Name = mode.id
	card.AutoButtonColor = false
	card.Text = ""
	card.Size = UDim2.fromOffset(CARD_W, CARD_H)
	card.Position = UDim2.fromOffset((index - 1) * (CARD_W + GAP), 52)
	card.BackgroundColor3 = mode.color
	card.Parent = panel
	corner(card, 22)
	local border = stroke(card, 5)
	local gradient = Instance.new("UIGradient")
	gradient.Rotation = 90
	gradient.Color = ColorSequence.new(Color3.new(1, 1, 1), Color3.fromRGB(170, 170, 185))
	gradient.Parent = card
	local hover = Instance.new("UIScale")
	hover.Parent = card

	-- icon: a big emoji in a round badge, a crown on the fish for the battle royale
	local medal = Instance.new("Frame")
	medal.AnchorPoint = Vector2.new(0, 0.5)
	medal.Position = UDim2.new(0, 16, 0, 62)
	medal.Size = UDim2.fromOffset(84, 84)
	medal.BackgroundColor3 = mode.color:Lerp(Color3.new(0, 0, 0), 0.25)
	medal.Parent = card
	corner(medal, 42)
	stroke(medal, 4)
	local icon = label(medal, mode.icon, 50)
	icon.Size = UDim2.fromScale(1, 1)
	if mode.badge then
		local crown = label(medal, mode.badge, 34)
		crown.AnchorPoint = Vector2.new(0.5, 0.5)
		crown.Position = UDim2.fromScale(0.62, 0.12)
		crown.Size = UDim2.fromOffset(44, 44)
		crown.Rotation = 18
	end

	local title = label(card, mode.title, 30)
	title.TextXAlignment = Enum.TextXAlignment.Left
	title.Position = UDim2.fromOffset(112, 18)
	title.Size = UDim2.new(1, -124, 0, 38)
	title.TextScaled = true
	local text = label(card, mode.text, 18)
	text.TextXAlignment = Enum.TextXAlignment.Left
	text.TextYAlignment = Enum.TextYAlignment.Top
	text.Position = UDim2.fromOffset(112, 60)
	text.Size = UDim2.new(1, -124, 0, 50)

	-- the vote bar and its count
	local track = Instance.new("Frame")
	track.AnchorPoint = Vector2.new(0, 1)
	track.Position = UDim2.new(0, 16, 1, -16)
	track.Size = UDim2.new(1, -86, 0, 24)
	track.BackgroundColor3 = Color3.fromRGB(24, 26, 40)
	track.BackgroundTransparency = 0.35
	track.Parent = card
	corner(track, 12)
	stroke(track, 3)
	local fill = Instance.new("Frame")
	fill.Size = UDim2.fromScale(0, 1)
	fill.BackgroundColor3 = Color3.fromRGB(255, 226, 92)
	fill.Parent = track
	corner(fill, 12)
	local count = label(card, "0", 34)
	count.AnchorPoint = Vector2.new(1, 1)
	count.Position = UDim2.new(1, -14, 1, -8)
	count.Size = UDim2.fromOffset(60, 40)
	count.TextXAlignment = Enum.TextXAlignment.Right

	-- "your vote" tag on the chosen card
	local tag = label(card, "YOUR VOTE", 18, Color3.fromRGB(255, 236, 120))
	tag.AnchorPoint = Vector2.new(0.5, 0.5)
	tag.Position = UDim2.new(0.5, 0, 0, 0)
	tag.Size = UDim2.fromOffset(150, 26)
	tag.BackgroundTransparency = 0
	tag.BackgroundColor3 = OUTLINE
	tag.Visible = false
	corner(tag, 13)

	-- the padlock veil (battle royale with fewer than 3 players)
	local veil = Instance.new("Frame")
	veil.Size = UDim2.fromScale(1, 1)
	veil.BackgroundColor3 = Color3.fromRGB(70, 72, 84)
	veil.BackgroundTransparency = 0.2
	veil.Visible = false
	veil.ZIndex = 5
	veil.Parent = card
	corner(veil, 22)
	local lock = label(veil, "🔒", 54)
	lock.AnchorPoint = Vector2.new(0.5, 0.5)
	lock.Position = UDim2.fromScale(0.5, 0.36)
	lock.Size = UDim2.fromOffset(80, 70)
	lock.ZIndex = 6
	local lockText = label(veil, "3 players minimum", 24)
	lockText.AnchorPoint = Vector2.new(0.5, 0.5)
	lockText.Position = UDim2.fromScale(0.5, 0.72)
	lockText.Size = UDim2.new(1, -20, 0, 34)
	lockText.ZIndex = 6

	local entry = {
		mode = mode, card = card, border = border, hover = hover, fill = fill, count = count, tag = tag, veil = veil,
		locked = false, votes = 0,
	}
	card.MouseEnter:Connect(function()
		if not entry.locked then
			TweenService:Create(hover, TweenInfo.new(0.12), { Scale = 1.04 }):Play()
		end
	end)
	card.MouseLeave:Connect(function()
		TweenService:Create(hover, TweenInfo.new(0.12), { Scale = 1 }):Play()
	end)
	card.Activated:Connect(function()
		entry.vote()
	end)
	return entry
end

local function refresh()
	local total = 0
	for _, entry in cards do
		total += entry.votes
	end
	for _, entry in cards do
		local share = if total > 0 then entry.votes / total else 0
		TweenService:Create(entry.fill, TweenInfo.new(0.25, Enum.EasingStyle.Quad), { Size = UDim2.fromScale(share, 1) }):Play()
		entry.count.Text = tostring(entry.votes)
		local chosen = myVote == entry.mode.id and not entry.locked
		entry.tag.Visible = chosen
		entry.border.Color = if chosen then Color3.fromRGB(255, 240, 140) else OUTLINE
		entry.border.Thickness = if chosen then 7 else 5
		entry.veil.Visible = entry.locked
		entry.card.Active = not entry.locked
	end
end

local function sendVote(id: string)
	local remote = Remotes:FindFirstChild("Vote")
	if remote and remote:IsA("RemoteEvent") then
		remote:FireServer(id)
	end
end

for i, mode in MODES do
	local entry = buildCard(mode, i)
	entry.vote = function()
		if entry.locked or not FishGame:GetAttribute("VoteOpen") then
			return
		end
		myVote = mode.id -- shown at once, the server's counts follow
		sendVote(mode.id)
		TweenService:Create(entry.hover, TweenInfo.new(0.08), { Scale = 0.96 }):Play()
		task.delay(0.08, function()
			TweenService:Create(entry.hover, TweenInfo.new(0.15, Enum.EasingStyle.Back), { Scale = 1.04 }):Play()
		end)
		refresh()
	end
	cards[mode.id] = entry
end

-- --------------------------------------------------------------------------- state from the server
local function readState()
	cards.BattleRoyale.votes = FishGame:GetAttribute("VotesBattleRoyale") or 0
	cards.Survival.votes = FishGame:GetAttribute("VotesSurvival") or 0
	cards.BattleRoyale.locked = FishGame:GetAttribute("BattleRoyaleLocked") == true
	if cards.BattleRoyale.locked and myVote == "BattleRoyale" then
		myVote = nil
	end
	refresh()
end

local function announce(mode: string?)
	local entry = mode and cards[mode]
	if not entry then
		return
	end
	result.Text = entry.mode.title .. "!"
	result.TextColor3 = entry.mode.color:Lerp(WHITE, 0.25)
	result.TextTransparency = 0
	resultSub.TextTransparency = 0
	result.Visible = true
	resultScale.Scale = 0.5
	TweenService:Create(resultScale, TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	task.delay(1.7, function()
		TweenService:Create(result, TweenInfo.new(0.3), { TextTransparency = 1 }):Play()
		TweenService:Create(resultSub, TweenInfo.new(0.3), { TextTransparency = 1 }):Play()
		task.wait(0.3)
		result.Visible = false
	end)
end

local open = false
local function setOpen(value: boolean)
	if value == open then
		return
	end
	open = value
	ClientState.setUiOpen("Vote", value)
	if value then
		myVote = nil
		readState()
		gui.Enabled = true
		panel.Position = UDim2.new(0.5, 0, 1, CARD_H + 80)
		TweenService:Create(panel, TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out),
			{ Position = UDim2.new(0.5, 0, 1, -28) }):Play()
	else
		TweenService:Create(panel, TweenInfo.new(0.25, Enum.EasingStyle.Quad, Enum.EasingDirection.In),
			{ Position = UDim2.new(0.5, 0, 1, CARD_H + 80) }):Play()
		-- the result: NextMode may be published a moment after VoteOpen goes false
		task.delay(0.1, function()
			announce(FishGame:GetAttribute("NextMode"))
		end)
	end
end

for _, name in { "VotesBattleRoyale", "VotesSurvival", "BattleRoyaleLocked" } do
	FishGame:GetAttributeChangedSignal(name):Connect(readState)
end
FishGame:GetAttributeChangedSignal("VoteOpen"):Connect(function()
	setOpen(FishGame:GetAttribute("VoteOpen") == true)
end)

-- keys 1 and 2
UserInputService.InputBegan:Connect(function(input, processed)
	if processed or not open then
		return
	end
	for _, mode in MODES do
		if input.KeyCode == mode.key then
			cards[mode.id].vote()
		end
	end
end)

-- countdown, phone fit, the glow on the chosen card
local lastSecond = -1
RunService.RenderStepped:Connect(function()
	local view = workspace.CurrentCamera and workspace.CurrentCamera.ViewportSize or Vector2.new(1280, 720)
	local fit = math.clamp(math.min(view.X / 1100, view.Y / 640), 0.45, 1.2)
	panelFit.Scale = fit
	resultFit.Scale = fit
	if not open then
		if gui.Enabled and not result.Visible and panel.Position.Y.Offset > CARD_H then
			gui.Enabled = false
		end
		return
	end
	local endsAt = FishGame:GetAttribute("VoteEndsAt")
	local left = if type(endsAt) == "number" then math.max(0, math.ceil(endsAt - workspace:GetServerTimeNow())) else 0
	countdown.Text = "VOTE ENDS IN " .. tostring(left)
	countdown.TextColor3 = if left <= 3 then Color3.fromRGB(255, 96, 96) else WHITE
	if left ~= lastSecond then
		lastSecond = left
		if left <= 3 then
			countdownScale.Scale = 1.25
			TweenService:Create(countdownScale, TweenInfo.new(0.3, Enum.EasingStyle.Back), { Scale = 1 }):Play()
		end
	end
	local glow = 0.5 + 0.5 * math.sin(os.clock() * 6)
	for _, entry in cards do
		if myVote == entry.mode.id and not entry.locked then
			entry.border.Color = Color3.fromRGB(255, 240, 140):Lerp(WHITE, glow * 0.6)
		end
	end
end)

if FishGame:GetAttribute("VoteOpen") == true then
	setOpen(true)
end

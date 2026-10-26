-- Lobby: fish selection, and the selected fish carried in the avatar's arms
-- (while the inventory is open, or permanently with "Show off"). The arms are posed on every client
-- by HeldFishPose, on top of the avatar's animations.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame.Config)
local FishBuilder = require(FishGame.FishBuilder)
local FishSpecies = require(FishGame.FishSpecies)
local FishStats = require(FishGame.FishStats)
local Remotes = FishGame.Remotes
local FishService = require(script.Parent.FishService)

local LobbyService = {}

local HELD_SCALE = 0.45 -- the carried fish is a plush-sized version
local previewing: { [Player]: boolean } = {}

local function removeHeld(character: Model)
	local held = character:FindFirstChild("HeldFish")
	if held then
		held:Destroy()
	end
end

local function holdFish(player: Player, character: Model)
	local species = FishSpecies[player:GetAttribute("SelectedFish")] or FishSpecies[Config.DEFAULT_SPECIES]
	local torso = character:FindFirstChild("UpperTorso")
	if not torso then
		return
	end
	local held = character:FindFirstChild("HeldFish")
	if held and held:GetAttribute("Species") == player:GetAttribute("SelectedFish") then
		return
	end
	if held then
		held:Destroy()
	end
	local fish = FishBuilder.build(species.Model, "HeldFish")
	fish:SetAttribute("Species", player:GetAttribute("SelectedFish"))
	for _, d in fish:GetDescendants() do
		if d:IsA("Humanoid") or d:IsA("LinearVelocity") or d:IsA("AlignOrientation") then
			d:Destroy()
		elseif d:IsA("BasePart") then
			d.CanCollide = false
			d.CanQuery = false
			d.CanTouch = false
			d.Massless = true
		end
	end
	fish:ScaleTo(HELD_SCALE * FishStats.factor(species.Size))
	-- lying across the forearms, head to the avatar's right
	fish:PivotTo(torso.CFrame * CFrame.new(0, -0.55, -1.25) * CFrame.Angles(0, math.rad(90), 0))
	local weld = Instance.new("WeldConstraint")
	weld.Part0 = torso
	weld.Part1 = fish.PrimaryPart
	weld.Parent = fish.PrimaryPart
	fish.Parent = character
end

function LobbyService.refresh(player: Player)
	local character = player.Character
	if not character or FishService.get(character) or not character:FindFirstChild("Humanoid") then
		return
	end
	if player:GetAttribute("ShowOff") or previewing[player] then
		holdFish(player, character)
	else
		removeHeld(character)
	end
end

function LobbyService.start()
	Remotes.SelectFish.OnServerEvent:Connect(function(player, speciesId)
		if type(speciesId) == "string" and FishSpecies[speciesId] then
			player:SetAttribute("SelectedFish", speciesId)
			LobbyService.refresh(player)
		end
	end)
	Remotes.ShowOff.OnServerEvent:Connect(function(player, on)
		player:SetAttribute("ShowOff", on == true)
		LobbyService.refresh(player)
	end)
	Remotes.SetHolding.OnServerEvent:Connect(function(player, on)
		previewing[player] = on == true or nil
		LobbyService.refresh(player)
	end)
	local function watch(player: Player)
		player.CharacterAdded:Connect(function(character)
			character:WaitForChild("UpperTorso", 10)
			task.wait(0.5) -- let the avatar appearance load before posing the arms
			LobbyService.refresh(player)
		end)
	end
	Players.PlayerAdded:Connect(watch)
	for _, player in Players:GetPlayers() do
		watch(player)
	end
	Players.PlayerRemoving:Connect(function(player)
		previewing[player] = nil
	end)
end

return LobbyService

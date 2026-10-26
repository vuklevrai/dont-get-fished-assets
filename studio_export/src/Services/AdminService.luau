-- Test-phase admin tools (K panel). Only the game's owner, or anyone in Studio, may use them.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local FishSpecies = require(FishGame.FishSpecies)
local Remotes = FishGame.Remotes
local Services = script.Parent
local FishService = require(Services.FishService)
local RoundService = require(Services.RoundService)
local FishermanService = require(Services.FishermanService)
local PowerUpService = require(Services.PowerUpService)
local EnemyFishService = require(Services.EnemyFishService)

local AdminService = {}

function AdminService.isAdmin(player: Player): boolean
	if RunService:IsStudio() then
		return true
	end
	return game.CreatorType == Enum.CreatorType.User and player.UserId == game.CreatorId
end

local SETTINGS = { Fishermen = "boolean", Enemies = "boolean", PowerUps = "boolean", Difficulty = "string", HoldLobby = "boolean",
	Map = "string" }
local DIFFICULTIES = { Auto = true, Easy = true, Medium = true, Hard = true }
local MAPS = { Auto = true, Pond = true, Aquarium = true, Ballon = true, Ocean = true }

local actions = {}

function actions.StartTest()
	RoundService.startTest()
end

function actions.StopTest()
	RoundService.stopTest()
end

function actions.SetSpecies(player, id)
	if FishSpecies[id] then
		player:SetAttribute("SelectedFish", id)
	end
end

function actions.Heal(player)
	local info = FishService.forPlayer(player)
	if info then
		info.humanoid.Health = info.humanoid.MaxHealth
	end
end

function actions.LevelUp(player)
	local info = FishService.forPlayer(player)
	if info then
		FishService.levelUp(info)
	end
end

function actions.KillMe(player)
	local humanoid = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
	if humanoid then
		humanoid.Health = 0
	end
end

function actions.GodMode(player, on)
	player:SetAttribute("GodMode", on == true)
end

function actions.SpawnEnemy(player)
	local info = FishService.forPlayer(player)
	local at = info and info.root.CFrame * CFrame.new(0, 0, -22) or nil
	EnemyFishService.spawnOne(at)
end

function actions.ClearEnemies()
	EnemyFishService.clear()
end

function actions.SpawnFisherman()
	FishermanService.spawnOne()
end

function actions.ClearFishermen()
	FishermanService.clear()
end

function actions.SpawnPowerUp(player, kind)
	local info = FishService.forPlayer(player)
	if info and PowerUpService.TYPES[kind] then
		local p = (info.root.CFrame * CFrame.new(0, 0, -10)).Position
		PowerUpService.spawn(kind, p)
	end
end

function actions.Setting(_, name, value)
	if SETTINGS[name] ~= type(value) then
		return
	end
	if name == "Difficulty" and not DIFFICULTIES[value] then
		return
	end
	if name == "Map" and not MAPS[value] then
		return
	end
	RoundService.settings[name] = value
	RoundService.publishSettings()
end

function AdminService.start()
	local function mark(player: Player)
		player:SetAttribute("IsAdmin", AdminService.isAdmin(player))
	end
	Players.PlayerAdded:Connect(mark)
	for _, player in Players:GetPlayers() do
		mark(player)
	end
	Remotes.Admin.OnServerEvent:Connect(function(player, action, ...)
		if not AdminService.isAdmin(player) or type(action) ~= "string" or not actions[action] then
			return
		end
		local ok, err = pcall(actions[action], player, ...)
		if not ok then
			warn("admin action", action, "failed:", err)
		end
	end)
end

return AdminService

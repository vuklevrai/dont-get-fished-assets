-- Boots the game: lobby, combat, round systems (fishermen, power-ups, enemy fish), admin tools,
-- then runs the round loop forever. See ServerScriptService.Services.
local Services = script.Parent:WaitForChild("Services")

local RoundService = require(Services.RoundService)
require(Services.CombatService)
local LobbyService = require(Services.LobbyService)
local AdminService = require(Services.AdminService)

RoundService.systems = {
	require(Services.FishermanService),
	require(Services.PowerUpService),
	require(Services.EnemyFishService),
}

LobbyService.start()
AdminService.start()
RoundService.run()

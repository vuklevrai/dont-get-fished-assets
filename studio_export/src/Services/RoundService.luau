-- Round flow. Players wait on the pirate ship as avatars, then everyone becomes a fish in the map.
-- A round lasts until one fish is left (or none in a solo game). An admin test game never ends:
-- fish that die come back as fish. Round state lives in attributes on ReplicatedStorage.FishGame:
-- Phase (Intermission | Round | Results), PhaseEnd, RoundStart, TestMode, Alive, Survivors.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame.Config)
local FishSpecies = require(FishGame.FishSpecies)
local FishService = require(script.Parent.FishService)
local MapService = require(script.Parent.MapService)

local RoundService = {}

RoundService.settings = { Fishermen = true, Enemies = true, PowerUps = true, Difficulty = "Auto", HoldLobby = false, Map = "Auto" }
RoundService.systems = {} -- services with start(round) / stop()
RoundService.round = nil -- { map, startTime, testMode, elapsed() }

local swimmers: { [Player]: boolean } = {} -- players taking part in the current round, still alive
local startedWith = 0
local lastTwoDone = false
local request: string? = nil -- "Test" | "Stop"

local function now()
	return workspace:GetServerTimeNow()
end

local function setPhase(name: string, duration: number?)
	FishGame:SetAttribute("Phase", name)
	FishGame:SetAttribute("PhaseEnd", duration and now() + duration or 0)
end

-- the round's map: the admin's pick, or the next one in the rotation (MapService)
function RoundService.currentMap(): Model
	local pick = RoundService.settings.Map
	return MapService.choose(pick ~= "Auto" and pick or nil)
end

function RoundService.publishSettings()
	for k, v in RoundService.settings do
		FishGame:SetAttribute("Setting" .. k, v)
	end
end

function RoundService.spawnAvatar(player: Player)
	if player.Parent then
		swimmers[player] = nil
		player:LoadCharacter()
	end
end

-- a random underwater spot of the map where a fish can appear
function RoundService.waterSpot(map: Model, depthMargin: number?): CFrame
	return MapService.spawnCFrame(map, depthMargin)
end

function RoundService.makeFish(player: Player)
	local round = RoundService.round
	if not round or not player.Parent then
		return
	end
	local species = player:GetAttribute("SelectedFish")
	if not FishSpecies[species] then
		species = Config.DEFAULT_SPECIES
	end
	local fish = FishService.create(species, { player = player })
	fish:PivotTo(RoundService.waterSpot(round.map))
	fish.Parent = workspace
	local avatar = player.Character
	swimmers[player] = true
	player.Character = fish
	if avatar and avatar ~= fish then
		avatar:Destroy()
	end
	fish.PrimaryPart:SetNetworkOwner(player)
end

local function aliveCount(): number
	local n = 0
	for player in swimmers do
		local info = FishService.forPlayer(player)
		if player.Parent and FishService.alive(info) then
			n += 1
		else
			swimmers[player] = nil
		end
	end
	return n
end

-- elimination: the killer levels up; when only two players remain, both level up once
FishService.died.Event:Connect(function(info, killer: Player?)
	local player = info.player
	if not player then
		return
	end
	if killer and killer ~= player then
		local killerFish = FishService.forPlayer(killer)
		if killerFish then
			FishService.levelUp(killerFish)
		end
	end
	swimmers[player] = nil
	local round = RoundService.round
	if round and not round.testMode and not lastTwoDone and startedWith > 2 and aliveCount() == 2 then
		lastTwoDone = true
		for p in swimmers do
			local f = FishService.forPlayer(p)
			if f then
				FishService.levelUp(f)
			end
		end
	end
	local character = info.model
	task.delay(round and round.testMode and Config.TEST_RESPAWN_DELAY or Config.RESPAWN_DELAY, function()
		if player.Parent and player.Character == character then
			if RoundService.round and RoundService.round.testMode then
				RoundService.makeFish(player)
			else
				RoundService.spawnAvatar(player)
			end
		end
	end)
end)

-- avatars that die on the ship (reset) come back on the ship
local function onCharacterAdded(player: Player, character: Model)
	if FishService.get(character) then
		return
	end
	local humanoid = character:WaitForChild("Humanoid", 10)
	if humanoid then
		humanoid.Died:Connect(function()
			task.wait(Config.RESPAWN_DELAY)
			if player.Parent and player.Character == character then
				RoundService.spawnAvatar(player)
			end
		end)
	end
end

local function onPlayerAdded(player: Player)
	player:SetAttribute("SelectedFish", player:GetAttribute("SelectedFish") or Config.DEFAULT_SPECIES)
	player.CharacterAdded:Connect(function(character)
		onCharacterAdded(player, character)
	end)
	if RoundService.round and RoundService.round.testMode then
		RoundService.makeFish(player)
	else
		RoundService.spawnAvatar(player)
	end
end

-- admin controls
function RoundService.startTest()
	request = "Test"
end

function RoundService.stopTest()
	request = "Stop"
end

local function startRound(testMode: boolean)
	local map = RoundService.currentMap()
	local t0 = now()
	RoundService.round = {
		map = map,
		startTime = t0,
		testMode = testMode,
		elapsed = function()
			return now() - t0
		end,
	}
	FishGame:SetAttribute("RoundStart", t0)
	FishGame:SetAttribute("TestMode", testMode)
	FishGame:SetAttribute("Survivors", "")
	lastTwoDone = false
	startedWith = 0
	for _, player in Players:GetPlayers() do
		local ok, err = pcall(RoundService.makeFish, player)
		if ok then
			startedWith += 1
		else
			warn("could not turn", player.Name, "into a fish:", err)
		end
	end
	setPhase("Round")
	for _, system in RoundService.systems do
		task.spawn(system.start, RoundService.round)
	end
end

local function endRound(showResults: boolean)
	local survivors = {}
	for player in swimmers do
		table.insert(survivors, player.DisplayName)
	end
	FishGame:SetAttribute("Survivors", table.concat(survivors, ", "))
	if showResults then
		setPhase("Results", Config.RESULTS_TIME)
		task.wait(Config.RESULTS_TIME)
	end
	for _, system in RoundService.systems do
		pcall(system.stop)
	end
	RoundService.round = nil
	FishGame:SetAttribute("TestMode", false)
	for _, player in Players:GetPlayers() do
		if FishService.get(player.Character) or swimmers[player] then
			RoundService.spawnAvatar(player)
		end
	end
	swimmers = {}
end

function RoundService.run()
	RoundService.publishSettings()
	Players.CharacterAutoLoads = false
	Players.PlayerAdded:Connect(onPlayerAdded)
	Players.PlayerRemoving:Connect(function(player)
		swimmers[player] = nil
	end)
	for _, player in Players:GetPlayers() do
		task.spawn(onPlayerAdded, player)
	end

	while true do
		-- intermission on the ship
		setPhase("Intermission", Config.INTERMISSION_TIME)
		FishGame:SetAttribute("Alive", 0)
		request = nil
		repeat
			task.wait(0.25)
			if #Players:GetPlayers() < Config.MIN_PLAYERS or RoundService.settings.HoldLobby then
				FishGame:SetAttribute("PhaseEnd", now() + Config.INTERMISSION_TIME)
			end
		until now() >= FishGame:GetAttribute("PhaseEnd") or request == "Test"
		local testMode = request == "Test"
		request = nil
		startRound(testMode)

		-- the round
		local stopped = false
		while true do
			task.wait(0.25)
			local alive = aliveCount()
			FishGame:SetAttribute("Alive", alive)
			if request == "Test" then
				RoundService.round.testMode = true
				FishGame:SetAttribute("TestMode", true)
				request = nil
			elseif request == "Stop" then
				stopped = true
				break
			end
			if not RoundService.round.testMode then
				if alive == 0 or (startedWith >= 2 and alive <= 1) then
					break
				end
			end
		end
		endRound(not stopped)
	end
end

return RoundService

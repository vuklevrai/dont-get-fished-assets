-- Arms wrapped around the carried fish (LobbyService welds a "HeldFish" in front of the avatar).
-- Runs on every client for every avatar: after the animations have posed the joints, the shoulders
-- and elbows get an extra rotation, so walking and emotes keep playing underneath. Works with both
-- Motor6D and AnimationConstraint avatar joints (both expose Transform).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local POSE = {
	-- joint name, part holding it, extra rotation
	{ "RightShoulder", "RightUpperArm", CFrame.Angles(math.rad(62), 0, math.rad(-24)) },
	{ "LeftShoulder", "LeftUpperArm", CFrame.Angles(math.rad(62), 0, math.rad(24)) },
	{ "RightElbow", "RightLowerArm", CFrame.Angles(math.rad(38), 0, 0) },
	{ "LeftElbow", "LeftLowerArm", CFrame.Angles(math.rad(38), 0, 0) },
}

local holders = {} -- avatar -> { {joint, offset}, ... }

local function jointsOf(character: Model)
	local list = {}
	for _, entry in POSE do
		local part = character:FindFirstChild(entry[2])
		local joint = part and part:FindFirstChild(entry[1])
		if joint and (joint:IsA("Motor6D") or joint:IsA("AnimationConstraint")) then
			table.insert(list, { joint, entry[3] })
		end
	end
	return list
end

local function watch(character: Model)
	local function update()
		if character:FindFirstChild("HeldFish") then
			holders[character] = holders[character] or jointsOf(character)
		else
			holders[character] = nil
		end
	end
	character.ChildAdded:Connect(update)
	character.ChildRemoved:Connect(update)
	character.Destroying:Connect(function()
		holders[character] = nil
	end)
	update()
end

local function watchPlayer(player: Player)
	player.CharacterAdded:Connect(watch)
	if player.Character then
		watch(player.Character)
	end
end
Players.PlayerAdded:Connect(watchPlayer)
for _, player in Players:GetPlayers() do
	watchPlayer(player)
end

-- after the Animator has written this frame's pose
RunService.PreSimulation:Connect(function()
	for character, joints in holders do
		if not character.Parent then
			holders[character] = nil
			continue
		end
		for _, j in joints do
			j[1].Transform = j[2] * j[1].Transform
		end
	end
end)

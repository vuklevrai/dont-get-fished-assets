-- Power-ups: big glowing baits floating just under the surface. Every 5 s there is a 50% chance one
-- appears next to a random hook (or anywhere in the arena). A player fish swimming into it picks it up.
-- Untouched, a bait vanishes after 12 s, blinking during its last 3 s (the client draws the blink from
-- its ExpiresAt attribute).
local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FishGame = ReplicatedStorage:WaitForChild("FishGame")
local Config = require(FishGame.Config)
local Remotes = FishGame.Remotes
local FishService = require(script.Parent.FishService)
local RoundService = require(script.Parent.RoundService)
local FishermanService = require(script.Parent.FishermanService)
local MapService = require(script.Parent.MapService)

local PowerUpService = {}

PowerUpService.TYPES = {
	Level = { Color = Color3.fromRGB(255, 205, 40), Icon = "⭐", Label = "LEVEL UP" },
	Speed = { Color = Color3.fromRGB(60, 220, 255), Icon = "⚡", Label = "SPEED" },
	Invisible = { Color = Color3.fromRGB(190, 110, 255), Icon = "👻", Label = "INVISIBLE" },
	Titan = { Color = Color3.fromRGB(255, 120, 30), Icon = "💪", Label = "TITAN!" },
}
local BAIT_SCALE = 3

-- a random kind, following Config.POWERUP_WEIGHTS (Titan is rare)
local function randomKind(): string
	local total = 0
	for _, w in Config.POWERUP_WEIGHTS do
		total += w
	end
	local roll = math.random() * total
	for kind, w in Config.POWERUP_WEIGHTS do
		roll -= w
		if roll <= 0 then
			return kind
		end
	end
	return "Speed"
end

local running = false
local round = nil
local folder: Folder? = nil
local items = {}

local function now()
	return workspace:GetServerTimeNow()
end

local function deco(p: BasePart)
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.Material = Enum.Material.SmoothPlastic
	return p
end

local function buildBait(kind: string): Model
	local def = PowerUpService.TYPES[kind]
	local m = Instance.new("Model")
	m.Name = "PowerUp_" .. kind
	local orb = deco(Instance.new("Part"))
	orb.Name = "Orb"
	orb.Shape = Enum.PartType.Ball
	orb.Size = Vector3.one * 3.2 * BAIT_SCALE
	orb.Color = def.Color
	orb.Material = Enum.Material.Neon
	orb.Transparency = 0.55
	orb.CFrame = CFrame.new()
	orb.Parent = m
	m.PrimaryPart = orb
	-- a fat pink worm curled inside the glow
	local pink = Color3.fromRGB(255, 120, 150)
	for i = 0, 4 do
		local a = i / 4 * math.pi * 1.3 - 0.6
		local seg = deco(Instance.new("Part"))
		seg.Name = "Worm"
		seg.Size = Vector3.new(0.7, 0.7, 0.9) * BAIT_SCALE
		seg.Color = i % 2 == 0 and pink or Color3.fromRGB(240, 96, 130)
		seg.CFrame = CFrame.new(math.cos(a) * 0.8 * BAIT_SCALE, math.sin(i * 1.3) * 0.3 * BAIT_SCALE, math.sin(a) * 0.8 * BAIT_SCALE)
			* CFrame.Angles(0, -a, 0)
		seg.Parent = m
	end
	local light = Instance.new("PointLight")
	light.Color = def.Color
	light.Range = 26
	light.Brightness = 2.5
	light.Parent = orb
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.fromOffset(64, 64)
	gui.StudsOffset = Vector3.new(0, 3.2 * BAIT_SCALE * 0.75, 0)
	gui.MaxDistance = 160
	gui.LightInfluence = 0
	local icon = Instance.new("TextLabel")
	icon.BackgroundTransparency = 1
	icon.Size = UDim2.fromScale(1, 1)
	icon.TextScaled = true
	icon.Text = def.Icon
	icon.Parent = gui
	gui.Parent = orb
	m:SetAttribute("Kind", kind)
	CollectionService:AddTag(m, "PowerUp")
	return m
end

-- where a new bait goes: near a hook in the water (they are a lure), else anywhere in the arena
local function baitPosition(): Vector3
	local map = round.map
	local hooksOut = FishermanService.hookPositions()
	if #hooksOut > 0 and map:GetAttribute("WaterShape") ~= "Sphere" then
		for _ = 1, 10 do
			local h = hooksOut[math.random(1, #hooksOut)]
			local a, d = math.random() * math.pi * 2, 22 + math.random() * 14
			local p = h + Vector3.new(math.cos(a) * d, 0, math.sin(a) * d)
			if MapService.inArena(map, p) then
				local depth = MapService.depth(map, p)
				return p - Vector3.yAxis * (Config.POWERUP_DEPTH - depth)
			end
		end
	end
	return MapService.waterPoint(map, Config.POWERUP_DEPTH)
end

function PowerUpService.spawn(kind: string?, at: Vector3?)
	if not round or not folder then
		return
	end
	kind = kind or randomKind()
	local pos = at or baitPosition()
	local bait = buildBait(kind)
	bait:PivotTo(CFrame.new(pos))
	local expires = now() + Config.POWERUP_LIFETIME
	bait:SetAttribute("ExpiresAt", expires)
	bait.Parent = folder
	table.insert(items, { model = bait, kind = kind, expires = expires })
end

local function apply(info, kind: string)
	local def = PowerUpService.TYPES[kind]
	if kind == "Level" then
		FishService.levelUp(info)
		Remotes.Effect:FireAllClients("Aura", info.model, def.Color, 1)
	elseif kind == "Speed" then
		FishService.boostSpeed(info, Config.SPEED_BOOST_TIME)
		Remotes.Effect:FireAllClients("Aura", info.model, def.Color, 0.6)
	elseif kind == "Invisible" then
		FishService.setInvisible(info, Config.INVISIBLE_TIME)
	elseif kind == "Titan" then
		FishService.titan(info, Config.TITAN_TIME)
		Remotes.Effect:FireAllClients("Titan", info.model, info.root.Position)
	end
	if info.player then
		Remotes.Effect:FireClient(info.player, "PowerUp", info.model, kind, def.Label)
	end
end

local acc = 0
RunService.Heartbeat:Connect(function(dt)
	acc += dt
	if not running or acc < 0.1 then
		return
	end
	acc = 0
	local t = now()
	for i = #items, 1, -1 do
		local item = items[i]
		local pos = item.model.PrimaryPart and item.model.PrimaryPart.Position
		local taken = false
		if pos then
			for _, info in FishService.fish do
				if info.player and FishService.alive(info) and not info.model:GetAttribute("Caught") then
					if (info.root.Position - pos).Magnitude < 1.6 * BAIT_SCALE + 1.6 * info.model:GetScale() then
						apply(info, item.kind)
						taken = true
						break
					end
				end
			end
		end
		if taken or t > item.expires or not pos then
			item.model:Destroy()
			table.remove(items, i)
		end
	end
end)

function PowerUpService.start(r)
	round = r
	running = true
	folder = Instance.new("Folder")
	folder.Name = "PowerUps"
	folder.Parent = workspace
	while running do
		task.wait(Config.POWERUP_INTERVAL)
		if running and RoundService.settings.PowerUps and #items < Config.POWERUP_MAX
			and math.random() < Config.POWERUP_CHANCE then
			PowerUpService.spawn()
		end
	end
end

function PowerUpService.stop()
	running = false
	items = {}
	if folder then
		folder:Destroy()
		folder = nil
	end
	round = nil
end

return PowerUpService

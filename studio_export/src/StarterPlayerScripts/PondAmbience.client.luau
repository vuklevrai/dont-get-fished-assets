-- Seaweed sway, block style: each leaf snaps between half-stud offsets a few times per second
-- (higher leaves move further), like stop-motion. Client-only; the leaves never collide.
local CollectionService = game:GetService("CollectionService")
local Workspace = game:GetService("Workspace")

local STEP = 0.5 -- studs: offsets snap to this grid
local FRAME = 0.2 -- seconds between poses
local RANGE = 260 -- only seaweed this close to the camera moves

local weeds = {}

local function snap(v: number): number
	return math.floor(v / STEP + 0.5) * STEP
end

local function track(model: Instance)
	if weeds[model] then
		return
	end
	local leaves, rest = {}, {}
	for _, p in model:GetChildren() do
		if p:IsA("BasePart") then
			p.CanCollide = false
			table.insert(leaves, p)
		end
	end
	if #leaves == 0 then
		return
	end
	for i, p in leaves do
		rest[i] = p.CFrame
	end
	weeds[model] = { leaves = leaves, rest = rest, phase = math.random() * 6.28, centre = leaves[1].Position, lastPose = nil }
end

CollectionService:GetInstanceAddedSignal("Seaweed"):Connect(function(model)
	task.defer(track, model)
end)
CollectionService:GetInstanceRemovedSignal("Seaweed"):Connect(function(model)
	weeds[model] = nil
end)
for _, model in CollectionService:GetTagged("Seaweed") do
	track(model)
end

while true do
	task.wait(FRAME)
	local camera = Workspace.CurrentCamera
	local eye = camera and camera.CFrame.Position or Vector3.zero
	local t = os.clock()
	local parts, cframes = {}, {}
	for model, w in weeds do
		if not model.Parent then
			weeds[model] = nil
			continue
		end
		if (w.centre - eye).Magnitude > RANGE then
			continue
		end
		for i, leaf in w.leaves do
			local s = leaf:GetAttribute("Segment") or (i - 1)
			local reach = s * 0.22
			local dx = snap(math.sin(t * 1.1 + w.phase + s * 0.45) * reach)
			local dz = snap(math.cos(t * 0.8 + w.phase * 1.3 + s * 0.4) * reach * 0.7)
			table.insert(parts, leaf)
			table.insert(cframes, w.rest[i] + Vector3.new(dx, 0, dz))
		end
	end
	if #parts > 0 then
		Workspace:BulkMoveTo(parts, cframes, Enum.BulkMoveMode.FireCFrameChanged)
	end
end

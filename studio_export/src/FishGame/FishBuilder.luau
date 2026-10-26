-- Builds a playable fish character from generated box data (see FishData).
local CollectionService = game:GetService("CollectionService")
local Config = require(script.Parent.Config)

local FishBuilder = {}

local SCALE = Config.FISH_SCALE
-- model data faces +X; Roblox characters face -Z
local TO_ROBLOX = CFrame.Angles(0, math.rad(90), 0)
-- model-space point that becomes the HumanoidRootPart centre
local PIVOT = Vector3.new(0.2, 0, 0)

local function toFish(cf: CFrame): CFrame
	local c = TO_ROBLOX * (cf - PIVOT)
	return c.Rotation + c.Position * SCALE
end

local function quatCFrame(pos: Vector3, q): CFrame
	return CFrame.new(pos.X, pos.Y, pos.Z, q[1], q[2], q[3], q[4])
end

local function hiddenPart(name: string, size: Vector3, cf: CFrame): Part
	local p = Instance.new("Part")
	p.Name = name
	p.Size = size
	p.CFrame = cf
	p.Transparency = 1
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.Massless = true
	return p
end

function FishBuilder.build(species: string, name: string, palette: { [string]: Color3 }?): Model
	local data = require(script.Parent.FishData[species])
	local colors = palette or data.colors
	local model = Instance.new("Model")
	model.Name = name
	model.ModelStreamingMode = Enum.ModelStreamingMode.Atomic

	local root = hiddenPart("HumanoidRootPart", Vector3.new(1.2, 1.4, 4.6), CFrame.identity)
	root.CanCollide = true
	root.CanQuery = true
	root.CanTouch = true
	root.Massless = false
	-- frictionless so the fish slides along walls instead of sticking to them
	root.CustomPhysicalProperties = PhysicalProperties.new(1, 0, 0, 100, 1)
	root.Parent = model
	model.PrimaryPart = root

	-- one invisible joint part per rig segment, chained with Motor6Ds for the swim animation
	local joints = { centre = root }
	local pending = {}
	for segName, seg in data.segments do
		joints[segName] = hiddenPart("Seg_" .. segName, Vector3.new(0.2, 0.2, 0.2), toFish(quatCFrame(seg.pos, seg.rot)))
		joints[segName].Parent = model
		table.insert(pending, segName)
	end
	for _, segName in pending do
		local parentName = data.segments[segName].parent
		-- the head hangs off the front body so it follows the body's sway
		if parentName == "centre" and segName ~= "corps_avant" and joints.corps_avant then
			parentName = "corps_avant"
		end
		local part0, part1 = joints[parentName], joints[segName]
		local motor = Instance.new("Motor6D")
		motor.Name = segName
		motor.Part0 = part0
		motor.Part1 = part1
		motor.C0 = part0.CFrame:ToObjectSpace(part1.CFrame)
		motor.C1 = CFrame.identity
		motor.Parent = part0
	end

	for _, piece in data.pieces do
		local base = quatCFrame(piece.pos, piece.rot)
		local joint = joints[piece.seg] or root
		for i, b in piece.boxes do
			local size = Vector3.new(b[4] - b[1], b[5] - b[2], b[6] - b[3])
			local centre = Vector3.new(b[1] + b[4], b[2] + b[5], b[3] + b[6]) / 2
			local p = Instance.new("Part")
			p.Name = piece.name
			p.Size = size * SCALE
			p.CFrame = toFish(base * CFrame.new(centre))
			p.Color = colors[piece.mat] or Color3.new(1, 0, 1)
			p.Material = Enum.Material.SmoothPlastic
			p.MaterialVariant = "FishBlock"
			p.TopSurface = Enum.SurfaceType.Smooth
			p.BottomSurface = Enum.SurfaceType.Smooth
			p.CanCollide = false
			p.CanQuery = false
			p.CanTouch = false
			p.Massless = true
			local weld = Instance.new("WeldConstraint")
			weld.Part0 = joint
			weld.Part1 = p
			weld.Parent = p
			p.Parent = joint
		end
	end

	local humanoid = Instance.new("Humanoid")
	humanoid.RequiresNeck = false
	humanoid.BreakJointsOnDeath = false
	humanoid.HipHeight = 0
	humanoid.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
	humanoid.HealthDisplayType = Enum.HumanoidHealthDisplayType.AlwaysOff
	humanoid.Parent = model

	-- swim physics: the owning client drives these two constraints
	local att = Instance.new("Attachment")
	att.Name = "RootAttachment"
	att.Parent = root
	local velocity = Instance.new("LinearVelocity")
	velocity.Name = "SwimVelocity"
	velocity.Attachment0 = att
	velocity.RelativeTo = Enum.ActuatorRelativeTo.World
	velocity.VelocityConstraintMode = Enum.VelocityConstraintMode.Vector
	velocity.ForceLimitMode = Enum.ForceLimitMode.PerAxis
	velocity.MaxAxesForce = Vector3.one * Config.SWIM_FORCE
	velocity.VectorVelocity = Vector3.zero
	velocity.Parent = root
	local align = Instance.new("AlignOrientation")
	align.Name = "SwimAlign"
	align.Mode = Enum.OrientationAlignmentMode.OneAttachment
	align.Attachment0 = att
	align.Responsiveness = Config.TURN_RESPONSIVENESS
	align.MaxTorque = math.huge
	align.CFrame = CFrame.identity
	align.Parent = root

	model:SetAttribute("Species", species)
	CollectionService:AddTag(model, Config.ANIMATED_TAG)
	return model
end

return FishBuilder

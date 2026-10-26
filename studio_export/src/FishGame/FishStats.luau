-- Stat formulas shared by server and client.
local FishStats = {}

-- size and speed use the same curve: stat 2 is the reference (x1)
local CURVE = { 0.8, 1.0, 1.15, 1.3, 1.5 }
local HEALTH = { 30, 50, 70, 90, 120 }

function FishStats.factor(stat: number): number
	if stat <= 1 then
		return CURVE[1]
	elseif stat <= 5 then
		return CURVE[math.floor(stat)]
	end
	return CURVE[5] + (stat - 5) * 0.2 -- sizes keep growing with levels past 5
end

function FishStats.maxHealth(stat: number): number
	return HEALTH[math.clamp(math.floor(stat), 1, 5)]
end

-- Base fish dash: 5 damage at size 2, +5 per size above
function FishStats.dashDamage(size: number): number
	return math.max(0, 5 + 5 * (size - 2))
end

-- bump between two fish swimming normally: returns damage to the bigger one, damage to the smaller one,
-- stun of the smaller one (s) and how hard it is thrown back (studs/s)
function FishStats.collision(sizeDifference: number)
	local d = math.abs(sizeDifference)
	if d < 1 then
		return 2, 2, 0, 0
	elseif d < 2 then
		return 1, 2, 0, 0
	elseif d < 3 then
		return 1, 3, 0.5, 12
	elseif d < 4 then
		return 0, 3, 1, 35
	end
	return 0, 4, 1, 80
end

FishStats.MAX_LEVEL = 5
FishStats.LEVEL_HEALTH = 10
FishStats.LEVEL_SPEED = 0.05

return FishStats

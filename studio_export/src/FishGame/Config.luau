-- Shared tuning values for the fish game.
return {
	WATER_LEVEL = -1, -- Y of the pond surface (terrain water)

	FISH_SCALE = 2, -- studs per model unit for the fish models
	FISH_TAG = "Fish", -- gameplay fish: player characters and enemy bots
	ANIMATED_TAG = "AnimatedFish", -- every fish model the animator moves (held and preview fish too)

	-- round flow (seconds)
	INTERMISSION_TIME = 20,
	RESULTS_TIME = 6,
	MIN_PLAYERS = 1,
	RESPAWN_DELAY = 2,
	TEST_RESPAWN_DELAY = 3,
	DEFAULT_SPECIES = "BaseFish",

	-- swimming (base values, multiplied by the fish's SpeedFactor attribute)
	SWIM_SPEED = 26,
	ACCELERATION = 6.25, -- how fast velocity reaches its target (1/s)
	TURN_RESPONSIVENESS = 15,
	SWIM_FORCE = 200000,
	AIR_STEER = 0.04,
	MAX_PITCH = 0.85,
	BANK = 0.12,
	MAX_BANK = 0.6,

	-- swimming feel (FishController, see luau/MOVEMENT_DESIGN.md)
	SWIM_ACCEL = 5,
	SWIM_GLIDE_DRAG = 2.2,
	SWIM_GLIDE_BRAKE = 6,
	SWIM_OVERSPEED_DRAG = 6,
	SWIM_LATERAL_DRAG = 14,
	SWIM_STRAFE_DRAG = 4,
	SWIM_CARVE = 0.85,
	SWIM_TURN_RATE = 10,
	SWIM_TURN_FALLOFF = 60,
	SWIM_TURN_SHARPNESS = 14,
	SWIM_MAX_CLIMB = 0.97,
	SWIM_LEVEL_OUT = 1.2,
	SWIM_PULSE = 0.05,
	SWIM_UNDULATION = 0.06,
	SWIM_REVERSE = 0.55,
	SWIM_ALIGN_RESPONSIVENESS = 40,
	SURFACE_MARGIN = 1.1,
	BANK_SMOOTH = 6,
	WATER_VOXEL_CHECK = true,

	-- dash feel
	DASH_RAMP = 16,
	DASH_TURN_RATE = 1.2,
	DASH_HIT_KEEP = 0.35,
	DASH_WALL_BOUNCE = 0.2,

	-- leap camera
	LEAP_ENTRY_KEEP = 0.6,
	LEAP_CAMERA_FOLLOW = 6,
	LEAP_CAMERA_PITCH = -0.22,
	LEAP_CAMERA_TILT = 0.3,
	LEAP_CONTROL_RETURN = 0.35,
	LEAP_SURFACE_UP = 0.85,

	-- stun: knockback + ragdoll
	STUN_DRAG = 0.92,
	STUN_DRAG_QUAD = 0.004,
	STUN_SPIN = 0.16,
	STUN_SPIN_MAX = 14,
	STUN_SPIN_DRAG = 1.6,
	STUN_BOUNCE = 0.45,
	STUN_RECOVER_TIME = 0.5,

	-- camera feel
	CAMERA_FOLLOW = 10,
	CAMERA_LEAD = 0.08,
	CAMERA_LEAD_MAX = 3,
	CAMERA_FOV = 70,
	CAMERA_FOV_SPEED = 12,
	SHIFTLOCK_OFFSET = 2.4,
	SHIFTLOCK_TURN_RATE = 14,

	-- leap: swimming up into the surface throws the fish along a fixed arc
	LEAP_MIN_PITCH = 0.3, -- look direction Y needed to leap
	LEAP_MIN_SPEED = 10,
	LEAP_DISTANCE = 30,
	LEAP_HEIGHT = 10,
	LEAP_TIME = 1.1,
	LEAP_COOLDOWN = 1.2,
	DIVE_BOOST = 1.7, -- speed multiplier right after diving back in, fading out
	DIVE_BOOST_TIME = 1.3,

	-- stranded on land: Space hops
	FLOP_UP = 38,
	FLOP_FORWARD = 16,
	FLOP_COOLDOWN = 0.5,

	-- dash ability
	DASH_SPEED = 97,
	DASH_TIME = 0.45,
	DASH_HIT_STUN = 1,
	DASH_HIT_KNOCKBACK = 45,
	DASH_WALL_STUN = 1,

	-- collisions between fish
	COLLISION_MIN_SPEED = 10, -- relative speed for a bump to count
	COLLISION_COOLDOWN = 0.6, -- per pair of fish
	CONTACT_DISTANCE = 3.4, -- centre distance at size factor 1

	REGEN_PER_SECOND = 1,
	KILL_CREDIT_TIME = 8, -- a hit within this many seconds before death earns the level

	-- camera
	CAMERA_DISTANCE = 11,
	CAMERA_MIN_DISTANCE = 6,
	CAMERA_MAX_DISTANCE = 30,
	CAMERA_HEIGHT = 1.5,
	MOUSE_SENSITIVITY = 0.0035,
	TOUCH_SENSITIVITY = 0.008,
	GAMEPAD_SENSITIVITY = 3,

	-- fishermen
	FISHERMAN_INTERVAL = 7,
	FISHERMAN_MAX = 10,
	HOOK_WAIT_MIN = 5,
	HOOK_WAIT_MAX = 20,
	HOOK_WARNING = 1, -- the fog strikes exactly this long after it appears
	HOOK_RADIUS = 17.5, -- perfect sphere around the hook (the fog drawn around it is irregular)
	HOOK_RECAST = 2,
	CATCH_DRAIN_INTERVAL = 0.333,
	CATCH_FAIL_DAMAGE = 2,
	CATCH_RELEASE_INVULNERABLE = 1,
	-- catch minigame: { from elapsed seconds, pointer degrees/s, green arc degrees }
	CATCH_DIFFICULTY = { { 0, 150, 110 }, { 90, 260, 65 }, { 150, 380, 38 } },

	-- power-ups
	POWERUP_INTERVAL = 5,
	POWERUP_CHANCE = 0.5,
	POWERUP_LIFETIME = 12,
	POWERUP_BLINK = 3, -- blinks during its last seconds
	POWERUP_DEPTH = 6, -- baits float this far under the surface
	POWERUP_MAX = 8,
	POWERUP_WEIGHTS = { Level = 30, Speed = 30, Invisible = 30, Titan = 8 }, -- Titan is the rare one
	SPEED_BOOST = 1.0, -- +100 % of the base speed
	SPEED_BOOST_TIME = 20,
	INVISIBLE_TIME = 10,
	TITAN_TIME = 15,
	TITAN_SIZE = 5, -- extra size stat
	TITAN_SPEED = 5, -- extra speed stat

	-- enemy fish
	ENEMY_START = 20,
	ENEMY_INTERVAL = 10,
	ENEMY_MAX = 10,
	ENEMY_SPAWN_FREEZE = 2,
	ENEMY_DASH_COOLDOWN = 5,
	ENEMY_DASH_RANGE = 25,
	ENEMY_HEALTH = 10,
	ENEMY_SPEED_STAT = 3,
	ENEMY_SIZE_STAT = 3,
}

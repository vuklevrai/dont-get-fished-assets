-- Texture ids of the effects rendered in Blender (cloud-assets branches, fx/README.md explains each one).
-- Brief 2 keys are at rbxassetid://0 until uploaded: WeaponFx, Bubbles and Disintegrate then draw plain shapes.
return {
	FogFlipbook = "rbxassetid://81509858468482", -- 4x4 loop, fog spans ~85 % of the frame width
	FogPuff = "rbxassetid://97845245254710",
	TitanLightning = "rbxassetid://112173117745283", -- 4x4 one-shot, impact at (0.5, 0.86) of the frame
	TitanFlashRing = "rbxassetid://88050158473067",
	SpeedLine = "rbxassetid://103233755273956", -- 256x32, bright head on the right
	SpeedLinesScreen = "rbxassetid://82086263097519",
	SpeedLinesScreenB = "rbxassetid://124809726568185",
	LowHpVignette = "rbxassetid://124504819039558",
	ZoneWallFlipbook = "rbxassetid://89013307367369", -- 4x4 loop, each frame tiles horizontally
	ZoneWallStatic = "rbxassetid://112854019042597",

	-- brief 2 (fx/aim_beam.py, fx/weapon_fx.py)
	AimBeamFlipbook = "rbxassetid://0", -- aim_beam_flipbook.png: 4x4 loop, each frame tiles vertically
	AimRing = "rbxassetid://0", -- aim_ring.png: red danger circle
	MissileReticle = "rbxassetid://0", -- missile_reticle.png: the bazooka's sight
	ExplosionFlipbook = "rbxassetid://0", -- explosion_flipbook.png: 4x4 one-shot, blast at (0.5, 0.53)
	ShockwaveRing = "rbxassetid://0", -- shockwave_ring.png
	SmokePuff = "rbxassetid://0", -- smoke_puff.png: missile trail, smoke after a blast
	MissileFlame = "rbxassetid://0", -- missile_flame.png: Beam texture, nozzle on the left
	Bubble = "rbxassetid://0", -- bubble.png
	ShardSpark = "rbxassetid://0", -- shard_spark.png: sparkle when a block leaves a fish
}

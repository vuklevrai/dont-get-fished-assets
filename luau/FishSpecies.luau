-- Playable fish. Stats go from 1 (weakest) to 5 (strongest). Hidden = true keeps a species out of the menu
-- (the enemy bots' fish); Model = the FishData / FishAnims entry.
return {
	BaseFish = {
		Order = 1,
		DisplayName = "Base fish",
		Model = "Bonite", -- FishData / FishAnims entry
		Speed = 2,
		Health = 2,
		Size = 2,
		Ability = {
			Id = "Dash",
			Name = "Dash",
			Cooldown = 6,
			Description = "Charge forward. A fish you hit takes 5 damage (+5 for each size above 2) and is stunned for 1 second. Crashing into a wall stuns you.",
		},
		Skins = {
			{ Id = "Classic", Name = "Classic" },
		},
	},
	Hyneria = {
		Order = 2,
		DisplayName = "Prehistoric fish",
		Model = "Hyneria",
		Speed = 2,
		Health = 3,
		Size = 3,
		Ability = {
			Id = "TimeStop",
			Name = "Time Stop",
			Cooldown = 25,
			Description = "Stop time for 3 seconds around you (36 studs): every other fish freezes while you swim twice as fast. The hits you land all go off when time resumes.",
		},
		Skins = {
			{ Id = "Classic", Name = "Classic" },
		},
	},
	Crocodile = {
		Order = 3,
		DisplayName = "Crocodile",
		Model = "Crocodile",
		Speed = 2,
		Health = 4,
		Size = 3,
		Ability = {
			Id = "CrocBite",
			Name = "Croc",
			Cooldown = 12,
			Description = "Open your jaws for 3 seconds: fish within 11 studs are slowed by half, and the first one you touch is bitten (20 damage, +5 for each size above 2) and stunned.",
		},
		Skins = {
			{ Id = "Classic", Name = "Classic" },
		},
	},
	EnemyFish = {
		Order = 99,
		Hidden = true, -- the enemy bots only
		DisplayName = "Enemy fish",
		Model = "Piranha",
		Speed = 3,
		Health = 1,
		Size = 3,
		Ability = {
			Id = "Dash",
			Name = "Dash",
			Cooldown = 5,
			Description = "Charges the nearest fish.",
		},
		Skins = {
			{ Id = "Classic", Name = "Classic" },
		},
	},
}

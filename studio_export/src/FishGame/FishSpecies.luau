-- Playable fish. Stats go from 1 (weakest) to 5 (strongest).
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
}

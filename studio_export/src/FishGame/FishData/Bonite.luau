-- Generated from bonite_brainrot.glb: boxes per rig segment, in model units (fish faces +X).
return {
	colors = {
		joue = Color3.fromRGB(226, 203, 133),
		flanc = Color3.fromRGB(88, 120, 187),
		dos = Color3.fromRGB(34, 53, 111),
		ventre = Color3.fromRGB(241, 223, 216),
		argent = Color3.fromRGB(195, 208, 228),
		encre = Color3.fromRGB(20, 26, 54),
		blanc = Color3.fromRGB(246, 246, 241),
		nageoire = Color3.fromRGB(90, 135, 150),
		jaune = Color3.fromRGB(168, 180, 67),
	},
	segments = {
		tete = { parent = "centre", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 } },
		corps_avant = { parent = "centre", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 } },
		corps_arriere = { parent = "corps_avant", pos = Vector3.new(0.2, 0, 0), rot = { 0, 0, 0, 1 } },
		queue_1 = { parent = "corps_arriere", pos = Vector3.new(-0.4, 0, 0), rot = { 0, 0, 0, 1 } },
		queue_2 = { parent = "queue_1", pos = Vector3.new(-0.8, 0, 0), rot = { 0, 0, 0, 1 } },
		nageoire_caudale = { parent = "queue_2", pos = Vector3.new(-1.1, 0, 0), rot = { 0, 0, 0, 1 } },
		nageoire_dorsale = { parent = "corps_avant", pos = Vector3.new(0.5, 0.4, 0), rot = { 0, 0, 0, 1 } },
		nageoire_pectorale_g = { parent = "corps_avant", pos = Vector3.new(0.72, -0.08, 0.305), rot = { 0.0223, 0.222, 0.0973, 0.9699 } },
		nageoire_pectorale_d = { parent = "corps_avant", pos = Vector3.new(0.72, -0.08, -0.305), rot = { -0.0223, -0.222, 0.0973, 0.9699 } },
	},
	pieces = {
		{ name = "tete_joue", seg = "tete", mat = "joue", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ 0, -0.3, -0.3, 0.2, 0, 0.3 },
		} },
		{ name = "tete_flanc", seg = "tete", mat = "flanc", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ 0, 0, -0.3, 0.2, 0.3, 0.3 },
			{ 0.2, 0, -0.3, 0.3, 0.2, 0.3 },
			{ 0.3, 0, -0.2, 0.5, 0.2, 0.2 },
			{ 0.5, 0, -0.2, 0.6, 0.1, 0.2 },
		} },
		{ name = "tete_dos", seg = "tete", mat = "dos", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ 0, 0.3, -0.3, 0.2, 0.4, 0.3 },
			{ 0.2, 0.2, -0.3, 0.3, 0.3, 0.3 },
			{ 0.3, 0.2, -0.2, 0.5, 0.3, 0.2 },
			{ 0.5, 0.1, -0.2, 0.6, 0.2, 0.2 },
			{ 0.6, 0, -0.1, 0.7, 0.1, 0.1 },
		} },
		{ name = "tete_ventre", seg = "tete", mat = "ventre", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ 0.2, -0.3, -0.3, 0.3, -0.1, 0.3 },
			{ 0.3, -0.3, -0.2, 0.4, -0.1, 0.2 },
			{ 0.4, -0.2, -0.2, 0.6, -0.1, 0.2 },
		} },
		{ name = "tete_argent", seg = "tete", mat = "argent", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ 0.2, -0.1, -0.3, 0.3, 0, 0.3 },
		} },
		{ name = "tete_encre", seg = "tete", mat = "encre", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ 0.3, -0.1, -0.2, 0.6, 0, 0.2 },
			{ 0.6, -0.1, -0.1, 0.7, 0, 0.1 },
		} },
		{ name = "oeil_g_blanc", seg = "tete", mat = "blanc", pos = Vector3.new(1, 0.11, 0.3), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.11, -0.11, -0.008, 0.11, 0.11, 0.032 },
		} },
		{ name = "oeil_g_pupille", seg = "tete", mat = "encre", pos = Vector3.new(1, 0.11, 0.3), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.015, -0.06, 0.023, 0.085, 0.06, 0.047 },
		} },
		{ name = "sourcil_g_mesh", seg = "tete", mat = "encre", pos = Vector3.new(0.99, 0.255, 0.3), rot = { 0, 0, 0.04, 0.9992 }, boxes = {
			{ -0.125, -0.036, -0.004, 0.125, 0.036, 0.044 },
		} },
		{ name = "oeil_d_blanc", seg = "tete", mat = "blanc", pos = Vector3.new(1, 0.11, -0.3), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.11, -0.11, -0.032, 0.11, 0.11, 0.008 },
		} },
		{ name = "oeil_d_pupille", seg = "tete", mat = "encre", pos = Vector3.new(1, 0.11, -0.3), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.015, -0.06, -0.047, 0.085, 0.06, -0.023 },
		} },
		{ name = "sourcil_d_mesh", seg = "tete", mat = "encre", pos = Vector3.new(0.99, 0.255, -0.3), rot = { 0, 0, 0.04, 0.9992 }, boxes = {
			{ -0.125, -0.036, -0.044, 0.125, 0.036, 0.004 },
		} },
		{ name = "caudale_nageoire", seg = "nageoire_caudale", mat = "nageoire", pos = Vector3.new(-1.1, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.6, -0.5, -0.03, -0.3, -0.4, 0.03 },
			{ -0.6, 0.4, -0.03, -0.3, 0.5, 0.03 },
			{ -0.5, -0.4, -0.03, -0.2, -0.3, 0.03 },
			{ -0.5, 0.3, -0.03, -0.2, 0.4, 0.03 },
			{ -0.4, -0.3, -0.03, -0.1, -0.2, 0.03 },
			{ -0.4, 0.2, -0.03, -0.1, 0.3, 0.03 },
			{ -0.3, -0.2, -0.03, 0, -0.1, 0.03 },
			{ -0.3, 0.1, -0.03, 0, 0.2, 0.03 },
			{ -0.2, -0.1, -0.03, 0, 0.1, 0.03 },
		} },
		{ name = "queue_2_argent", seg = "queue_2", mat = "argent", pos = Vector3.new(-0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.3, -0.1, -0.1, 0, 0, 0.1 },
		} },
		{ name = "queue_2_dos", seg = "queue_2", mat = "dos", pos = Vector3.new(-0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.3, 0, -0.1, 0, 0.1, 0.1 },
		} },
		{ name = "queue_2_jaune", seg = "queue_2", mat = "jaune", pos = Vector3.new(-0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.185, 0.1, -0.025, -0.115, 0.16, 0.025 },
			{ -0.185, -0.16, -0.025, -0.115, -0.1, 0.025 },
		} },
		{ name = "queue_1_argent", seg = "queue_1", mat = "argent", pos = Vector3.new(-0.4, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.4, -0.1, -0.1, -0.1, 0, 0.1 },
			{ -0.1, -0.1, -0.2, 0, 0, 0.2 },
		} },
		{ name = "queue_1_dos", seg = "queue_1", mat = "dos", pos = Vector3.new(-0.4, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.4, 0, -0.1, -0.3, 0.1, 0.1 },
			{ -0.3, 0.1, -0.1, -0.1, 0.2, 0.1 },
			{ -0.1, 0.1, -0.2, 0, 0.2, 0.2 },
		} },
		{ name = "queue_1_ventre", seg = "queue_1", mat = "ventre", pos = Vector3.new(-0.4, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.3, -0.2, -0.1, -0.1, -0.1, 0.1 },
			{ -0.1, -0.2, -0.2, 0, -0.1, 0.2 },
		} },
		{ name = "queue_1_encre", seg = "queue_1", mat = "encre", pos = Vector3.new(-0.4, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.3, 0, -0.1, -0.1, 0.1, 0.1 },
		} },
		{ name = "queue_1_flanc", seg = "queue_1", mat = "flanc", pos = Vector3.new(-0.4, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.1, 0, -0.2, 0, 0.1, 0.2 },
		} },
		{ name = "queue_1_jaune", seg = "queue_1", mat = "jaune", pos = Vector3.new(-0.4, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.385, 0.1, -0.025, -0.315, 0.16, 0.025 },
			{ -0.185, 0.2, -0.025, -0.115, 0.26, 0.025 },
			{ -0.385, -0.16, -0.025, -0.315, -0.1, 0.025 },
			{ -0.185, -0.26, -0.025, -0.115, -0.2, 0.025 },
		} },
		{ name = "corps_arriere_ventre", seg = "corps_arriere", mat = "ventre", pos = Vector3.new(0.2, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.6, -0.2, -0.2, -0.3, -0.1, 0.2 },
			{ -0.5, -0.3, -0.2, -0.2, -0.2, 0.2 },
			{ -0.2, -0.4, -0.2, 0, -0.3, 0.2 },
			{ -0.3, -0.2, -0.3, -0.2, -0.1, 0.3 },
			{ -0.2, -0.3, -0.3, 0, -0.2, 0.3 },
		} },
		{ name = "corps_arriere_argent", seg = "corps_arriere", mat = "argent", pos = Vector3.new(0.2, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.6, -0.1, -0.2, -0.3, 0, 0.2 },
			{ -0.3, -0.1, -0.3, 0, 0, 0.3 },
			{ -0.2, -0.2, -0.3, 0, -0.1, 0.3 },
		} },
		{ name = "corps_arriere_flanc", seg = "corps_arriere", mat = "flanc", pos = Vector3.new(0.2, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.6, 0, -0.2, -0.3, 0.1, 0.2 },
			{ -0.3, 0.1, -0.3, 0, 0.2, 0.3 },
		} },
		{ name = "corps_arriere_encre", seg = "corps_arriere", mat = "encre", pos = Vector3.new(0.2, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.6, 0.1, -0.2, -0.3, 0.2, 0.2 },
			{ -0.3, 0, -0.3, 0, 0.1, 0.3 },
			{ -0.3, 0.2, -0.3, 0, 0.3, 0.3 },
		} },
		{ name = "corps_arriere_dos", seg = "corps_arriere", mat = "dos", pos = Vector3.new(0.2, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.6, 0.2, -0.2, -0.3, 0.3, 0.2 },
			{ -0.3, 0.3, -0.2, 0, 0.4, 0.2 },
		} },
		{ name = "corps_arriere_jaune", seg = "corps_arriere", mat = "jaune", pos = Vector3.new(0.2, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.585, 0.3, -0.025, -0.515, 0.36, 0.025 },
		} },
		{ name = "corps_arriere_nageoire", seg = "corps_arriere", mat = "nageoire", pos = Vector3.new(0.2, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.5, -0.5, -0.025, -0.3, -0.3, 0.025 },
			{ -0.5, 0.3, -0.025, -0.4, 0.6, 0.025 },
			{ -0.4, 0.3, -0.025, -0.3, 0.5, 0.025 },
			{ -0.3, -0.4, -0.025, -0.2, -0.3, 0.025 },
			{ -0.3, 0.4, -0.025, -0.2, 0.5, 0.025 },
		} },
		{ name = "corps_avant_ventre", seg = "corps_avant", mat = "ventre", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.6, -0.4, -0.2, -0.1, -0.3, 0.2 },
			{ -0.6, -0.3, -0.3, -0.1, -0.2, 0.3 },
		} },
		{ name = "corps_avant_argent", seg = "corps_avant", mat = "argent", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.6, -0.2, -0.3, -0.1, 0, 0.3 },
		} },
		{ name = "corps_avant_encre", seg = "corps_avant", mat = "encre", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.6, 0, -0.3, -0.5, 0.1, 0.3 },
			{ -0.6, 0.2, -0.3, -0.5, 0.3, 0.3 },
			{ -0.5, 0.1, -0.3, -0.1, 0.2, 0.3 },
		} },
		{ name = "corps_avant_flanc", seg = "corps_avant", mat = "flanc", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.6, 0.1, -0.3, -0.5, 0.2, 0.3 },
			{ -0.5, 0, -0.3, 0, 0.1, 0.3 },
			{ -0.5, 0.2, -0.3, 0, 0.3, 0.3 },
			{ -0.1, 0.1, -0.3, 0, 0.2, 0.3 },
		} },
		{ name = "corps_avant_dos", seg = "corps_avant", mat = "dos", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.6, 0.3, -0.2, 0, 0.4, 0.2 },
		} },
		{ name = "corps_avant_joue", seg = "corps_avant", mat = "joue", pos = Vector3.new(0.8, 0, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.1, -0.3, -0.2, 0, -0.2, 0.2 },
			{ -0.1, -0.2, -0.3, 0, 0, 0.3 },
		} },
		{ name = "dorsale_jaune", seg = "nageoire_dorsale", mat = "jaune", pos = Vector3.new(0.5, 0.4, 0), rot = { 0, 0, 0, 1 }, boxes = {
			{ -0.3, 0, -0.025, 0.3, 0.1, 0.025 },
			{ -0.2, 0.1, -0.025, 0.3, 0.2, 0.025 },
			{ -0.1, 0.2, -0.025, 0.3, 0.3, 0.025 },
			{ 0.1, 0.3, -0.025, 0.3, 0.4, 0.025 },
		} },
		{ name = "nageoire_pectorale_g_nageoire", seg = "nageoire_pectorale_g", mat = "nageoire", pos = Vector3.new(0.72, -0.08, 0.305), rot = { 0.0223, 0.222, 0.0973, 0.9699 }, boxes = {
			{ -0.2, -0.135, -0.02, 0, 0.045, 0.02 },
			{ -0.3, -0.045, -0.02, -0.2, 0.045, 0.02 },
		} },
		{ name = "nageoire_pectorale_d_nageoire", seg = "nageoire_pectorale_d", mat = "nageoire", pos = Vector3.new(0.72, -0.08, -0.305), rot = { -0.0223, -0.222, 0.0973, 0.9699 }, boxes = {
			{ -0.2, -0.135, -0.02, 0, 0.045, 0.02 },
			{ -0.3, -0.045, -0.02, -0.2, 0.045, 0.02 },
		} },
	},
}

# ConfigPatch — nouveau système de nage (C5)

À appliquer dans `ReplicatedStorage.FishGame.Config`. Toutes les constantes ont aussi une valeur par défaut dans `FishController` : le script tourne même si une ligne manque, mais c'est `Config` qui fait foi.

## 1. Fichiers à remplacer

| Fichier livré | Emplacement dans Studio | Pourquoi |
|---|---|---|
| `luau/FishController.client.luau` | `StarterPlayer.StarterPlayerScripts.FishController` (LocalScript) | Le nouveau système de nage (remplacement complet). |
| `luau/ClientState.luau` | `ReplicatedStorage.FishGame.ClientState` (ModuleScript) | Les secousses passent par un **bruit lissé** au lieu de positions aléatoires image par image : c'est ce qui « téléportait » la caméra. L'API ne change pas (`shake`, `shakeOffset`). |
| `luau/FishAnimator.client.luau` | `StarterPlayer.StarterPlayerScripts.FishAnimator` (LocalScript) | 6 lignes changées : la queue du poisson local suit l'intensité et le rythme de nage du contrôleur (`ClientState.swimIntensity` / `swimPhase`). |

## 2. Valeurs modifiées

| Constante | Avant | Après | Raison |
|---|---|---|---|
| `SWIM_SPEED` | 20 | **26** | +30 % demandé. Les bots ennemis l'utilisent aussi : ils suivent. |
| `DASH_SPEED` | 75 | **97** | +30 %, pour garder le même rapport dash / nage. |
| `LEAP_HEIGHT` | 7 | **10** | Bond plus haut (demande). |
| `LEAP_DISTANCE` | 24 | **30** | La vitesse horizontale du bond (30 / 1,1 = 27 studs/s) colle à la nouvelle nage. |
| `LEAP_TIME` | 1.0 | **1.1** | Un peu plus de temps en l'air pour la hauteur de 10. |
| `LEAP_MIN_SPEED` | 8 | **10** | +30 %, comme la nage. |
| `COLLISION_MIN_SPEED` | 8 | **10** (recommandé) | Même seuil relatif qu'avant (0,4 × la vitesse de nage). Côté serveur. |

`ACCELERATION` (6.25) n'est plus utilisé par le joueur, seulement par `EnemyFishService` : ne pas y toucher.
`TURN_RESPONSIVENESS` (15) reste pour les bots ; le joueur utilise `SWIM_ALIGN_RESPONSIVENESS` (réglé localement par le client).

## 3. Nouvelles constantes (bloc à coller dans `Config`)

```lua
	-- swimming feel (FishController, see luau/MOVEMENT_DESIGN.md)
	SWIM_ACCEL = 5, -- 1/s: how quickly the fish reaches its cruise speed (90 % in ~0.47 s)
	SWIM_GLIDE_DRAG = 2.2, -- 1/s: water drag while coasting
	SWIM_GLIDE_BRAKE = 6, -- studs/s²: ends the glide (stops ~1 s after cruise)
	SWIM_OVERSPEED_DRAG = 6, -- 1/s: bleeds the extra speed after a dash or a dive
	SWIM_LATERAL_DRAG = 14, -- 1/s: sideways slip lost while turning
	SWIM_STRAFE_DRAG = 4, -- 1/s: same, when strafing (ShiftLock, swim back)
	SWIM_CARVE = 0.85, -- share of the lost slip given back as forward speed
	SWIM_TURN_RATE = 10, -- rad/s when still
	SWIM_TURN_FALLOFF = 60, -- studs/s at which the turn rate is halved
	SWIM_TURN_SHARPNESS = 14, -- 1/s: how fast small corrections close
	SWIM_MAX_CLIMB = 0.97, -- steepest swim direction (sine of the angle)
	SWIM_LEVEL_OUT = 1.2, -- 1/s: an idle fish levels out
	SWIM_PULSE = 0.05, -- tail strokes: the speed surges by +/- this share
	SWIM_UNDULATION = 0.06, -- rad: body sway at full swim
	SWIM_REVERSE = 0.55, -- share of the speed when swimming backwards
	SWIM_ALIGN_RESPONSIVENESS = 40, -- SwimAlign on the player's fish (set by the client)
	SURFACE_MARGIN = 1.1, -- the fish cruises this far under the surface
	BANK_SMOOTH = 6, -- 1/s
	WATER_VOXEL_CHECK = true, -- also ask the terrain whether there is water (no swimming over land)

	-- dash feel
	DASH_RAMP = 16, -- 1/s
	DASH_TURN_RATE = 1.2, -- rad/s: a dash can still be nudged
	DASH_HIT_KEEP = 0.35, -- speed kept when our dash hits a fish
	DASH_WALL_BOUNCE = 0.2, -- share of the speed bounced back when crashing into a wall

	-- leap camera
	LEAP_ENTRY_KEEP = 0.6, -- share of the arc's speed kept when diving back in
	LEAP_CAMERA_FOLLOW = 6, -- 1/s
	LEAP_CAMERA_PITCH = -0.22, -- rad
	LEAP_CAMERA_TILT = 0.3, -- rad of extra pitch along the arc's slope
	LEAP_CONTROL_RETURN = 0.35, -- s for the mouse to take over again
	LEAP_SURFACE_UP = 0.85, -- leaps only where the surface faces up this much (ball map: the top cap)

	-- stun: knockback + ragdoll
	STUN_DRAG = 0.92, -- 1/s: about 60 % of the speed lost per second
	STUN_DRAG_QUAD = 0.004, -- per stud/s: violent hits bleed faster at first
	STUN_SPIN = 0.16, -- rad/s of tumble per stud/s of knockback
	STUN_SPIN_MAX = 14,
	STUN_SPIN_DRAG = 1.6, -- 1/s
	STUN_BOUNCE = 0.45, -- restitution against walls
	STUN_RECOVER_TIME = 0.5, -- s for the controls to come back

	-- camera
	CAMERA_FOLLOW = 10, -- spring frequency (rad/s)
	CAMERA_LEAD = 0.08, -- s of velocity the camera looks ahead
	CAMERA_LEAD_MAX = 3, -- studs (at size factor 1)
	CAMERA_FOV = 70,
	CAMERA_FOV_SPEED = 12, -- extra degrees at dash speed
	SHIFTLOCK_OFFSET = 2.4, -- studs to the right (at size factor 1)
	SHIFTLOCK_TURN_RATE = 14, -- rad/s
```

## 4. Attributs utilisés

| Attribut | Sur | Valeurs | Qui le règle |
|---|---|---|---|
| `MoveMode` | le `Player` | `"Classic"` (défaut), `"CameraOnly"`, `"ShiftLock"` | Le panneau admin (session locale). Le contrôleur le relit à chaque image : on peut changer de mode en pleine nage. Un `SetAttribute` fait côté client suffit (seul le client le lit). |
| `MapWaterShape` | `ReplicatedStorage.FishGame` | `"Plane"` (défaut) ou `"Sphere"` | La rotation des cartes. **Obligatoire pour la carte Ballon**, sinon le jeu croit que l'eau est un plan à y = −1. |
| `MapWaterLevel` | `FishGame` | nombre (y de la surface) | Rotation des cartes. Sans lui : `PondMap:GetAttribute("WaterLevel")`, puis `Config.WATER_LEVEL`. |
| `MapWaterCenter`, `MapWaterRadius` | `FishGame` | `Vector3`, nombre | Carte Ballon : `(0, 0, 0)` et `110`. |

Le contrôleur vérifie aussi qu'il y a vraiment de l'**eau de terrain** sous le poisson (`WATER_VOXEL_CHECK`). Si une carte utilisait de l'eau en parts, mettre `WATER_VOXEL_CHECK = false`.

### Bouton du panneau admin (suggestion)

À coller dans `AdminUi`, juste après le bouton « S = swim back ». Il utilise les fonctions du script existant (`act`, `meGrid`, `refreshers`). L'attribut n'est lu que par le client, donc un `SetAttribute` local suffit.

```lua
local MOVE_MODES = { "Classic", "CameraOnly", "ShiftLock" }
local moveButton = act(meGrid, "", Color3.fromRGB(60, 150, 200), function() end)
local function paintMoveMode()
	moveButton.Text = "Move: " .. (player:GetAttribute("MoveMode") or "Classic")
end
moveButton.Activated:Connect(function()
	local current = table.find(MOVE_MODES, player:GetAttribute("MoveMode") or "Classic") or 1
	player:SetAttribute("MoveMode", MOVE_MODES[current % #MOVE_MODES + 1])
	paintMoveMode()
end)
table.insert(refreshers, paintMoveMode)
```

## 5. Ce que le client expose

- `ClientState.swimModel`, `ClientState.swimIntensity` (0 → 1,3), `ClientState.swimPhase` (0 → 1) : écrits à chaque image par le contrôleur, lus par `FishAnimator`. Utilisables aussi pour les effets de vitesse (lignes, distorsion) : `swimIntensity > 1` = dash.
- Un `ScreenGui` `FishCrosshair` (point blanc au centre), visible seulement en mode ShiftLock.

## 6. Patchs serveur recommandés (session locale)

**a) Poisson pris à l'hameçon : remplacer le tremblement aléatoire par un bruit lissé.**
Dans `FishermanService`, fonction `catch`, la boucle de la prise tire des angles aléatoires toutes les 0,06 s : le poisson saute d'une pose à l'autre. La caméra ne le suit plus (elle cadre le point d'accroche), mais le poisson lui-même reste saccadé. Remplacer la boucle par :

```lua
	setArm(hook.fisherman.model, 95, 0.4)
	local nextDrain = os.clock() + Config.CATCH_DRAIN_INTERVAL
	local seed = math.random() * 100
	while hook.caught == info and FishService.alive(info) and running do
		-- thrash on smooth noise: fast but continuous, never a jump to a random pose
		local t = (os.clock() - t0) * 3.5
		local wiggle = CFrame.Angles(
			math.rad(26 * math.noise(t, seed, 0.31)),
			math.rad(46 * math.noise(seed, t, 1.73)),
			math.rad(18 * math.noise(2.9, seed, t))
		)
		info.model:PivotTo(hangCF * wiggle)
		hookOnFish(hook)
		if os.clock() >= nextDrain then
			nextDrain += Config.CATCH_DRAIN_INTERVAL
			FishService.damage(info, 1)
		end
		task.wait()
	end
```

(`math.noise` reste en général entre −0,5 et 0,5 : les amplitudes ×2 donnent à peu près les ±14° / ±25° / ±10° d'avant.)

**b) Recul « comme une masse ».** Le client applique l'impulsion reçue par `Knockback("Stun", impulse, duration)`, puis la fait décroître (≈ 60 %/s). Suggestion pour le serveur :

```lua
-- the lighter fish flies further, like two masses colliding (mass ~ size factor cubed)
local function knockbackSpeed(victim, other, base: number): number
	local mv = victim.model:GetScale() ^ 3
	local mo = other.model:GetScale() ^ 3
	return base * 2 * mo / (mv + mo) -- = base between equals, up to 2 x base against a much heavier fish
end
```

Distances parcourues selon l'impulsion (voir `MOVEMENT_DESIGN.md`) : 12 → 12 studs, 35 → 34, 45 → 43, 80 → 73, 120 → 103.

**c) Power-up Speed à +100 %** : `SPEED_BOOST = 1.0`. Le contrôleur n'a rien à faire, il lit `SpeedFactor`. Le rayon de virage s'élargit tout seul à grande vitesse.

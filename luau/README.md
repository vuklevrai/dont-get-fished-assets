# Modules Luau

## Brief 2

Tous ces modules sont des **ModuleScripts client**, à placer dans `ReplicatedStorage.FishGame`. Seul `VoteUi` est un LocalScript.

Ils ne dépendent que de modules qui existent déjà : `FxAssets`, `ClientState` et `Config`. `WeaponFx` utilise aussi `WeaponModels` et `Bubbles` s'ils sont là. Sinon, il dessine des formes simples à leur place.

Une clé `FxAssets` restée à `rbxassetid://0` n'empêche rien de marcher : le module la remplace par une forme dessinée (anneaux en parts Neon, viseur en `Frame`, bulles en cercles, boule orange pour l'explosion). Tout peut donc se tester avant le téléversement des textures.

| Fichier | Type | Où |
|---|---|---|
| `WeaponFx.luau` | ModuleScript | `ReplicatedStorage.FishGame.WeaponFx` |
| `Disintegrate.luau` | ModuleScript | `ReplicatedStorage.FishGame.Disintegrate` |
| `Bubbles.luau` | ModuleScript | `ReplicatedStorage.FishGame.Bubbles` |
| `WeaponModels.luau` | ModuleScript (généré) | `ReplicatedStorage.FishGame.WeaponModels` |
| `FxAssets.luau` | ModuleScript | **remplace** `ReplicatedStorage.FishGame.FxAssets` : mêmes ids qu'aujourd'hui, plus les 9 nouvelles clés |
| `VoteUi.client.luau` | LocalScript | `StarterPlayer.StarterPlayerScripts.VoteUi` |

### WeaponFx

Pour l'appeler, ajouter une ligne en tête du gestionnaire de `Remotes.Effect` dans `Effects.client.luau` :

```lua
local WeaponFx = require(FishGame:WaitForChild("WeaponFx"))
local WEAPON_KINDS = { HarpoonAim = true, HarpoonFire = true, HarpoonTip = true, HarpoonEnd = true,
	MissileAim = true, MissileFire = true, Explosion = true }

Remotes.Effect.OnClientEvent:Connect(function(kind, ...)
	if WEAPON_KINDS[kind] then
		WeaponFx.handle(kind, ...)
		return
	end
	local model, a, b = ...
	-- ... existing kinds (Fog, Titan, Splash...)
end)
```

`handle` accepte deux formes :
- **sans modèle** : `("HarpoonAim", origin, bottom, …)` ;
- **avec modèle** : `("HarpoonAim", model, origin, bottom, …)`, la forme habituelle du remote.

La règle : quand la première valeur n'est pas un `Vector3` et que la deuxième en est un, la première est ignorée.

Côté serveur (exemples) :

```lua
-- harpoon: aim for 1 s, then fire; the catch reels the harpoon up to the surface
Remotes.Effect:FireAllClients("HarpoonAim", gunPos, bedPos, 7, 1.0)
Remotes.Effect:FireAllClients("HarpoonFire", gunPos, hitPos, 0.35, fishermanId) -- key = fishermanId
Remotes.Effect:FireAllClients("HarpoonTip", fishermanId, tipPos) -- each reel step (10 Hz is plenty)
Remotes.Effect:FireAllClients("HarpoonEnd", fishermanId) -- release, death or end of the catch

-- bazooka: the fog stays Effects' "Fog"; the circle on the bed and the sight come from MissileAim
Remotes.Effect:FireAllClients("MissileAim", zoneCentre, 17.5, 1.0)
Remotes.Effect:FireAllClients("MissileFire", muzzlePos, zoneCentre, 1.2)
task.delay(1.2, function()
	Remotes.Effect:FireAllClients("Explosion", zoneCentre, 17.5)
end)
```

| Type d'effet | Arguments | Ce qu'il fait | Retour |
|---|---|---|---|
| `HarpoonAim` | `origin`, `bottom`, `radius` (environ 7), `duration` | Colonne de brouillard rouge du pêcheur jusqu'au fond, en planche d'images sur 3 quads croisés.<br>Bord net : un tube en matériau `ForceField`.<br>Anneaux rouges sur le fond et à la traversée de la surface.<br>Apparaît en 0,15 s, reste `duration`, s'efface en 0,25 s.<br>Un axe oblique fonctionne aussi. | `{ destroy() }` |
| `HarpoonFire` | `from`, `to`, `travelTime`, `key?` | Le harpon (`WeaponModels`) file en ligne droite, tire une corde (`Beam`) depuis `from` et laisse une traînée blanche.<br>Bulles à l'entrée dans l'eau. | `{ rope, harpoon, setTip(pos), destroy() }` |
| `HarpoonTip` | `key`, `pos` | Appelle `setTip(pos)` sur le harpon gardé sous `key`.<br>`setTip` place la pointe en `pos`, le harpon pendu dans l'axe de la corde. Il prend la main sur le vol s'il arrive avant la fin. | le handle |
| `HarpoonEnd` | `key` | Appelle `destroy()` : retire le harpon et la corde.<br>Sécurité : un harpon oublié disparaît seul au bout de 60 s. | — |
| `MissileAim` | `center`, `radius`, `duration` | Cercle rouge sur le fond, sous la zone (raycast qui ignore les poissons).<br>Viseur face caméra sur la zone : il se verrouille en tournant, puis clignote de plus en plus vite (une fois par 0,45 s au début, une fois par 0,06 s à la fin) et reste fixe pendant les 0,2 dernières secondes. | `{ destroy() }` |
| `MissileFire` | `from`, `target`, `flightTime` | Arc de Bézier : le missile monte puis plonge ; son nez atteint `target` exactement à `flightTime`.<br>Traînée `SmokePuff`, remplacée par des bulles sous l'eau. Flamme en `Beam` qui scintille, lumière à la tuyère.<br>À l'arrivée, le missile disparaît et la fumée retombe sur place. | `{ missile, destroy() }` |
| `Explosion` | `center`, `radius` | Planche d'images (deux couches), anneau d'onde de choc qui grandit jusqu'à `radius`, bulle `ForceField`, étincelles, fumée hors de l'eau ou bulles dessous, éclair de lumière.<br>**Secousse** si la caméra est à moins de `radius × 3` (voir ci-dessous). | — |

**Mode performance.** On passe à 2 quads au lieu de 3 pour la colonne, avec 2 fois moins de particules : fumée, étincelles et bulles. On supprime aussi la deuxième couche d'explosion, la bulle `ForceField`, la traînée du harpon et la lumière de tuyère.

**Secousse de caméra.** Elle passe par `ClientState.shake`, le bruit lisse qui s'amortit. La caméra ne fait donc jamais de saut.
- **Caméra poisson** (`Scriptable`) : `FishController` l'applique déjà.
- **Autre caméra** (avatar, spectateur) : `WeaponFx` ajoute le décalage juste après les scripts caméra, avec `BindToRenderStep` à `Camera + 2`.

### Disintegrate

```lua
local Disintegrate = require(FishGame:WaitForChild("Disintegrate"))
-- client, when the server announces a death (BEFORE it destroys the fish):
Disintegrate.play(fishModel, hitDirection) -- hitDirection optional (the way the blow pushes the fish)
```

**Important.** Le client doit encore avoir le modèle pour le cloner. Côté serveur, il faut donc envoyer l'effet, par exemple `Effect:FireAllClients("Disintegrate", model, dir)`, **avant** de détruire le poisson. Prévoir environ 0,2 s de délai, ou bien cacher le poisson et le détruire ensuite.

Déroulé :
1. **Préparation** : le module clone chaque bloc visible (pas le `Root` ni les parts invisibles) et cache l'original avec `LocalTransparencyModifier`. Il coupe aussi les billboards, les highlights et les particules.
2. **Cascade** sur 0,35 s, de la queue vers la tête, ou depuis le côté de l'impact.
   - Chaque bloc part avec une vitesse aléatoire et une rotation, et un flash blanc.
   - **Sous l'eau** : forte décélération et légère remontée.
   - **Hors de l'eau** : `workspace.Gravity`, puis le bloc s'arrête sur le sol trouvé sous lui.
3. **Fin** : 2 s éparpillés, puis rétrécissement et fondu en 0,3 s.

Limite : 80 morceaux au maximum (40 en mode performance). Au-delà, les blocs voisins sont regroupés en tranches. Tout est ancré, sans collision, invisible aux raycasts, et animé par CFrame.

Le module refuse de jouer deux fois pour le même modèle (attribut local `Disintegrated`).

### Bubbles

```lua
local Bubbles = require(FishGame:WaitForChild("Bubbles"))
local stopBubbles = Bubbles.start() -- e.g. in PondAmbience, once
-- ...
stopBubbles()
Bubbles.burst(position, 12) -- one-off cluster (WeaponFx uses it for explosions, the harpoon, the missile)
```

**Grappes.** Une grappe naît toutes les 1,5 à 4 s (3 à 6 s en mode performance). Elle compte 3 à 12 bulles (2 à 6), sur le fond, à moins de 120 studs de la caméra.

**Forme de l'eau**, d'après les attributs `MapWaterShape`, `MapWaterLevel`, `MapWaterCenter` et `MapWaterRadius` :
- **`Plane`** : le point doit être dans l'arène de la carte courante, avec le même test que `MapService.inArena` (`ArenaMin`/`ArenaMax`, ou `PondRadiusX`/`PondRadiusZ`). Le fond est trouvé par un raycast qui ignore les poissons (tag `Fish`), les personnages et `LocalEffects`.
- **`Sphere`** : les bulles naissent au fond intérieur de la boule, montent tout droit et éclatent à sa sortie.

**Mouvement.** Chaque bulle oscille, accélère un peu et grossit (jusqu'à 1,8 fois). Elle éclate à la surface en gonflant et en s'effaçant en 0,12 s.

**Budget.** 60 bulles vivantes au maximum (20 en mode performance), recyclées dans un pool. Si `MapService` déplace les cartes (tout au même endroit), il faut garder la table `MAP_MODELS` et le test d'arène alignés sur le serveur.

### VoteUi

C'est un LocalScript. Le contrat avec le serveur est celui du brief :
- **Attributs** : `VoteOpen`, `VoteEndsAt`, `VotesBattleRoyale`, `VotesSurvival`, `BattleRoyaleLocked`, `NextMode` ;
- **Remote** : `Remotes.Vote:FireServer(mode)`, avec `mode` valant `"BattleRoyale"` ou `"Survival"`.

```lua
-- server sketch
FishGame:SetAttribute("BattleRoyaleLocked", #Players:GetPlayers() < 3)
FishGame:SetAttribute("VoteEndsAt", workspace:GetServerTimeNow() + 10)
FishGame:SetAttribute("VoteOpen", true)
-- Remotes.Vote.OnServerEvent: store votes[player] = mode (refuse "BattleRoyale" while locked), then publish the counts
FishGame:SetAttribute("NextMode", winner) -- before VoteOpen goes false
FishGame:SetAttribute("VoteOpen", false)
```

**Mise en page.** Deux cartes en bas au centre, chacune avec une barre et un compteur. La carte votée est encadrée d'un contour qui brille, avec l'étiquette « YOUR VOTE ».
- **Compte à rebours** : « VOTE ENDS IN 7 », qui devient rouge et pulse sous 3 s.
- **Battle Royale verrouillée** : la carte est grisée, avec un cadenas et « 3 players minimum ».
- **Fermeture** : à la fermeture du vote, le résultat s'affiche en grand pendant 2 s, par exemple « SURVIVAL! ».
- **Clavier** : les touches 1 et 2 votent aussi.

**Style.** `UIScale` pour les téléphones. Police `FredokaOne`, bleu (40, 146, 226) et rouge-violet (190, 40, 90). Les icônes sont des emoji, comme les appâts. Aperçu : `vote_ui_preview.html` / `.png`.

### WeaponModels (généré)

`maps/build_maps.py` (cible `weapons`) le génère à partir des mêmes tables que `models/*.json`. **Ne pas le modifier à la main.**

```lua
local WeaponModels = require(FishGame:WaitForChild("WeaponModels"))
local gun = WeaponModels.build("HarpoonGun", false) -- false: welded to its Root, ready to weld to a hand
gun.Parent = fishermanModel
local hand = fishermanModel:FindFirstChild("RightHand")
local weld = Instance.new("Weld")
weld.Part0 = hand
weld.Part1 = gun.Root
weld.C0 = hand.RightGripAttachment.CFrame -- the grip; turn with weld.C1 if the barrel is not along the arm
weld.Parent = gun.Root
-- when it fires: gun.Harpoon is the loaded harpoon (hide it, show it again on reload)
local muzzle = gun.Root.Muzzle.WorldPosition
```

- **Noms** : `HarpoonGun`, `Harpoon`, `Bazooka`, `Missile`.
- **Origine** : la poignée pour les armes, la pointe (ou le nez) pour les projectiles. Le canon et le vol vont vers −Z.
- **Points d'ancrage** : en `Attachment` sur `Root`, voir `models/weapons_spots.json`.
- **Groupes** : chaque groupe est un `Model` enfant, par exemple `HarpoonGun.Harpoon` ou `Bazooka.Missile`.

## Brief 1 (pour mémoire)

`FishController`, `FishAnimator`, `ClientState` et `CatchMinigame` : voir `MOVEMENT_DESIGN.md` et `ConfigPatch.md`. Ils sont déjà intégrés.

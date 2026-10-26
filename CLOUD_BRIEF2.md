# Brief cloud n° 2 — « Don't Get Fished » (ajouts de fin de développement)

> **Comment l'utiliser.** Colle ce fichier entier comme premier message d'une session cloud (Opus, effort max) ouverte sur le dépôt `vuklevrai/dont-get-fished-assets`.
>
> La session cloud **n'a accès ni à Roblox Studio ni au PC**. Elle produit seulement des fichiers : scripts Blender, tables de primitives, textures PNG et modules Luau autonomes. La session locale les intègre ensuite dans Studio.
>
> Travaille sur une **nouvelle branche `cloud-assets-2`**, partie de `cloud-assets`. Termine par un `REPORT.md` à la racine (voir § 4).

---

## 0. Préparation (à faire par toi, l'utilisateur, avant de lancer la session)

1. Mets dans le dépôt, branche `cloud-assets`, les fichiers du dossier `pour_github2/` :
   - ce `CLOUD_BRIEF2.md` ;
   - `NOTES_PROJET.md` (version à jour, avec sa section 13).
2. Re-exporte depuis Studio les scripts, qui ont beaucoup changé depuis le premier brief. Fais un clic droit, puis **Save to File…** au format `.rbxmx`, et remplace les fichiers du dossier `studio_export/` :
   - `StarterPlayer.StarterPlayerScripts` → `StarterPlayerScripts.rbxmx`
   - `ReplicatedStorage.FishGame` → `FishGame.rbxmx`
   - `ServerScriptService` → `ServerScriptService.rbxmx`

   Si l'export te pose problème, saute cette étape : les contrats ci-dessous suffisent.
3. Ouvre la session cloud sur la branche `cloud-assets` et colle ce fichier.

---

## 1. Contexte technique

Les conventions du **premier brief** (`CLOUD_BRIEF.md`, § 1) restent valables :
- tables de primitives au format `export_table` ;
- matériaux `Stud`, `Smooth`, `Glass`, `Neon`, `Wood`, `Metal`, `ForceField` ;
- un JSON plus un PNG de données (largeur 512) par asset ;
- aperçus `*_preview.png` ;
- graines aléatoires fixes ;
- PNG RGBA à alpha droit, en puissances de 2, planches 4×4 ;
- Luau dans le style de `studio_export/`.

Les outils de la branche `cloud-assets` sont à réutiliser tels quels : `maps/dgf_maps.py`, `maps/build_maps.py`, `spawn/dgf_assets.py`, et les générateurs de `fx/`.

**Ce qui existe déjà dans le jeu** (d'après `NOTES_PROJET.md` § 13) :
- **Cartes** : Pond, Aquarium, Ballon (qui sera retiré de la rotation) et Océan.
- **Placement de l'Océan** : la carte est importée avec son repère local, celui de `maps/ocean/spots.json`. Son fond plat est **une dalle dont le dessus est à y = −46** (locale), l'eau monte jusqu'à y = −1, et l'arène fait 300 × 240, centrée en (0, 0).
- **Mur de zone** : il sera remplacé localement par un simple panneau bleuté semi-transparent, sans animation. Il n'y a **rien à faire** dessus.
- **Poissons** : un poisson est un `Model` fait de **Parts** (blocs), avec un `PrimaryPart` invisible nommé `Root`. Un poisson de taille 5 mesure environ 9 × 3,5 studs.
- **Pêcheurs** : ce sont des personnages R15 debout, sur un pod ou un bateau. Ils regardent l'eau.
- **Effets** : le client reçoit les effets par `Remotes.Effect.OnClientEvent(kind, ...)`. Les modules `FxAssets` (ids d'images) et `ClientState` existent :
  - `ClientState.performance` vaut `true` en mode performance ;
  - `ClientState.changed` est un `BindableEvent`.
- **Attributs de `ReplicatedStorage.FishGame`** :
  - `MapWaterShape` : `"Plane"` ou `"Sphere"` ;
  - `MapWaterLevel` : nombre (y monde de la surface) ;
  - `MapWaterCenter` : `Vector3` ;
  - `MapWaterRadius` : nombre ;
  - `Phase` : `"Intermission"`, `"Round"`…

---

## 2. Tâches confiées au cloud

### C1 — Décor de l'Océan (Blender, tables de primitives)

Dossier `maps/ocean_decor/`.

1. **Squelette fossile de requin préhistorique (mégalodon)**, posé sur le fond comme décor central. Il doit être bien lisible de loin.
   - **Taille et pose** : environ **90 studs de long**, couché sur le côté ou en léger arc.
   - **Os** :
     - crâne massif avec mâchoire ouverte et rangées de dents triangulaires (`Wedge`) ;
     - colonne vertébrale en vertèbres séparées ;
     - côtes courbes ;
     - nageoires pectorales et caudale osseuses.
   - **Couleurs** : os ivoire ou beige, de (231, 220, 190) à (196, 180, 146), avec des fissures plus sombres et un peu de mousse verte.
   - **Budget** : **≤ 1 200 primitives**.
   - **Collision** : seulement le crâne et la colonne. Les poissons doivent pouvoir **nager entre les côtes** : laisse au moins **11 studs d'espace libre** entre les côtes ou dans la cage thoracique, et vérifie-le comme pour les tunnels de l'Aquarium.
   - **Origine** : le centre du dessous, posé sur y = 0 (le local placera le modèle à y = −46).
2. **Coraux** : 6 variantes de 40 à 120 primitives chacune, toutes avec l'origine à la base et sans collision.
   - Couleurs flashy cartoon : rose, orange, violet, jaune, turquoise.
   - Formes : coraux branchus, en éventail, cerveau (boules), tubes, champignon plat, anémone.
3. **`spots.json`** dans le repère de l'Océan, tous posés sur le fond (y = −46) :
   - `FossilSpot` : un seul point. Place le fossile dans l'arène, mais **décalé du centre** (par exemple à (60, −46, −40)) pour garder de la place de jeu.
   - `CoralSpots` : environ **60** points.
     - Les 2/3 sont dans l'arène, en bosquets, jamais à moins de 25 studs d'un `PlayerSpawnPoint` de `maps/ocean/spots.json`.
     - Le tiers restant est hors de l'arène, jusqu'à ±500, pour l'effet « océan sans fin ».
     - Chaque point porte un `variant` (de 1 à 6) et un `scale` (de 0,8 à 1,6).
   - `SeaweedSpots` : environ **40** points avec un champ `height` de 18 à 40, même logique de répartition. Le local générera les algues animées à ces endroits.
4. **Aperçus** : le fossile seul en deux vues, et une vue sous-marine de l'arène avec tout le décor.

### C2 — Armes des nouveaux pêcheurs (Blender, modèles)

Dossier `models/`. Pour chaque modèle : origine à la **poignée** (là où se trouve la main droite), canon orienté vers **−Z** (`LookVector`), aucune collision, **≤ 250 primitives**.

1. **`HarpoonGun`** : fusil-harpon de pêche de **6 à 7 studs de long**.
   - Crosse en bois, tube métal, élastiques orange.
   - Le **harpon chargé** forme un **groupe séparé `Harpoon`** dans la table, pour que le local puisse le détacher et le tirer.
2. **`Harpoon`** (projectile seul) : tige métal d'environ 7 studs, pointe à **barbillons**, anneau arrière où s'attache la corde. Origine à la pointe, orienté vers −Z.
3. **`Bazooka`** : lance-roquettes cartoon d'épaule, de 6 à 7 studs.
   - Tube vert militaire ou jaune avec bandes de danger, viseur, poignée.
   - Le **missile chargé** forme un groupe séparé `Missile`.
4. **`Missile`** (projectile seul) : corps blanc ou rouge, ogive, 4 ailerons, tuyère. Il fait environ 4 studs de long. Origine au nez, orienté vers −Z.
5. **Points d'ancrage** dans `models/weapons_spots.json`, en coordonnées locales :
   - `Muzzle` pour chaque arme (la bouche du canon) ;
   - `RopeAttach` pour le harpon ;
   - `Exhaust` pour le missile (la tuyère, pour la fumée).
6. **Aperçus** : les 4 modèles.

### C3 — Textures d'effets (dossier `fx/`)

Même style que la branche `cloud-assets` : toon avec contours, sauf le rouge de visée, qui reste « brouillard réaliste » comme `fog_flipbook`.

1. **`aim_beam_flipbook.png`** : 1024 × 1024, 4×4. C'est une bande verticale de brouillard rouge, en boucle, destinée à la **colonne de visée du harpon**. Elle sera plaquée sur des quads verticaux disposés en croix autour d'un cylindre épais (rayon d'environ 7 studs) qui va du pêcheur au fond.
   - Le haut et le bas de chaque image doivent se raccorder (**tuilable verticalement**).
   - Les bords gauche et droit doivent s'estomper en douceur.
   - La teinte doit rester proche de `fog_flipbook`.
2. **`explosion_flipbook.png`** : 1024 × 1024, 4×4, en une seule passe (sans boucle). C'est une explosion cartoon :
   - flash blanc-jaune, boule orange, puis fumée grise ;
   - contours foncés, à la façon d'un jeu Roblox populaire.
3. **`smoke_puff.png`** : 256 × 256. Une bouffée de fumée cartoon grise, pour la traînée du missile.
4. **`bubble.png`** : 128 × 128. Une bulle d'eau : cercle clair transparent, contour cyan léger et reflet blanc en haut à gauche. Elle doit être lisible sur le bleu de l'eau.
5. **`shard_spark.png`** : 128 × 128, optionnel. Une petite étincelle blanche pour la désintégration.

Ajoute un `fx/README.md` avec les réglages conseillés pour chaque texture : `ParticleEmitter` (taille, durée de vie, fps du flipbook) ou `ImageLabel`.

### C4 — Modules Luau autonomes (dossier `luau/`)

Chaque fichier est un **ModuleScript client**, testable seul et sans dépendance cachée. Il peut utiliser `FxAssets`, en y ajoutant les nouvelles clés, et `ClientState`, pour respecter `ClientState.performance`. Les ids d'images restent à `"rbxassetid://0"` : le local les remplira.

1. **`WeaponFx.luau`** : les effets des nouveaux pêcheurs. Le local appellera `WeaponFx.handle(kind, ...)` depuis le gestionnaire de `Remotes.Effect`. Contrat :
   - **`"HarpoonAim", origin: Vector3, bottom: Vector3, radius: number, duration: number`** : colonne de brouillard rouge, de `origin` (le pêcheur) jusqu'à `bottom` (le fond), d'un rayon de `radius`, environ 7. Elle apparaît en 0,15 s, reste en place `duration` secondes, puis s'estompe. Elle doit être bien visible d'en haut comme sous l'eau. C'est la zone de danger, donc la forme doit être nette ; seul le bord est brumeux.
   - **`"HarpoonFire", from: Vector3, to: Vector3, travelTime: number`** : le harpon (modèle construit à partir de C2 avec un petit constructeur Luau, ou un simple placeholder) file de `from` à `to`, en tirant une corde (`Beam`).
     - Renvoie un handle `{ rope: Beam, harpoon: Model, setTip(pos: Vector3), destroy() }`. Le local s'en servira pour la rétraction pendant la capture.
   - **`"MissileAim", center: Vector3, radius: number, duration: number`** : un cercle rouge au sol en plus du brouillard existant (le local s'occupe déjà du brouillard). Prévois un **viseur** clignotant de plus en plus vite.
   - **`"MissileFire", from: Vector3, target: Vector3, flightTime: number`** : le missile vole en **arc** (une courbe de Bézier qui monte, puis plonge sur la cible), avec une traînée `smoke_puff` et une flamme à la tuyère. Il arrive exactement après `flightTime`.
   - **`"Explosion", center: Vector3, radius: number`** : flipbook d'explosion, onde de choc (anneau qui grandit jusqu'à `radius`), bulles si c'est sous l'eau, et **secousse de caméra douce** si la caméra est à moins de `radius × 3`. Pas de téléportation de la caméra : utiliser un offset bruité qui s'amortit.

   En mode performance : moitié moins de particules et pas de deuxième couche.
2. **`Disintegrate.luau`** : `Disintegrate.play(model: Model, impulseDir: Vector3?)`. C'est l'élimination d'un poisson, désintégré bloc par bloc :
   - **Nettoyage** : le module clone en local chaque `BasePart` visible du modèle (sauf le `Root` invisible), cache l'original (le local le détruira côté serveur) et retire des clones tout joint ou script.
   - **Désintégration** : les blocs se détachent **en cascade**, de la queue vers la tête, ou depuis le point d'impact, sur environ 0,35 s.
     - Chacun part avec une vitesse aléatoire et une rotation.
     - Il est **freiné comme dans l'eau** : décélération forte, légère remontée.
     - Il reçoit un petit flash blanc au détachement.
   - **Disparition** : les blocs restent **éparpillés 2 secondes**, puis rapetissent et deviennent transparents en 0,3 s avant d'être détruits.
   - **Hors de l'eau** (au-dessus de `MapWaterLevel`), la gravité normale s'applique.
   - **Performance** : ≤ 80 blocs animés (au-delà, regrouper) ; mise à jour en `RenderStepped` sans physique Roblox (`Anchored = true`, CFrame calculé), `CanCollide`, `CanQuery` et `CanTouch` à false.
3. **`Bubbles.luau`** : `Bubbles.start()` lance l'ambiance de bulles et renvoie une fonction d'arrêt.
   - **Grappes** : toutes les 1,5 à 4 s, une grappe de 3 à 12 bulles naît à un endroit aléatoire du fond, dans un rayon de 120 studs autour de la caméra et sous la surface.
   - **Mouvement** : les bulles **remontent** en oscillant légèrement, accélèrent un peu, grossissent en montant, puis éclatent à la surface (petit pop).
   - **Forme de l'eau** :
     - `"Plane"` : la surface est à `MapWaterLevel` ;
     - `"Sphere"` : la surface est la sphère `MapWaterCenter`/`MapWaterRadius`. Les bulles montent vers le haut et éclatent à la sortie de la sphère.
   - Le fond est trouvé par un raycast vers le bas qui ignore les poissons (tag `Fish`).
   - Utilise des `BillboardGui` ou des `ParticleEmitter` avec `bubble.png`.
   - **Budget** : ≤ 60 bulles vivantes ; ≤ 20 et moins souvent en mode performance.
   - Ajoute aussi `Bubbles.burst(pos: Vector3, n: number)` : une grappe ponctuelle, utilisée pour les explosions et les splashs.
4. **`VoteUi.luau`** : un `LocalScript`, le vote du mode de jeu pendant l'intermission. Contrat avec le serveur (le local fait le serveur) :
   - **Attributs de `ReplicatedStorage.FishGame`** :
     - `VoteOpen` (bool) ;
     - `VoteEndsAt` (nombre, `workspace:GetServerTimeNow()`) ;
     - `VotesBattleRoyale` et `VotesSurvival` (nombres) ;
     - `BattleRoyaleLocked` (bool : true quand il y a moins de 3 joueurs) ;
     - `NextMode` (`"BattleRoyale"` ou `"Survival"`, le résultat).
   - **Remote** : `ReplicatedStorage.FishGame.Remotes.Vote` (`RemoteEvent`), avec `:FireServer("BattleRoyale" | "Survival")`. On peut changer son vote.
   - **UI** : deux grandes cartes côte à côte, en bas au centre de l'écran.
     - Carte « BATTLE ROYALE » : « Le dernier poisson en vie gagne » et une icône poisson et couronne.
     - Carte « SURVIE » : « Survivez aux vagues de pêcheurs et de poissons zombies » et une icône tête de mort.
     - Chaque carte affiche une barre de votes et son nombre. La carte votée a un contour brillant.
     - Un compte à rebours est affiché.
     - Si `BattleRoyaleLocked`, la carte BR est grisée avec un cadenas et « 3 joueurs minimum ».
     - Le résultat (`NextMode`) est annoncé en grand pendant 2 s à la fermeture du vote.
   - **Style** : cartoon, coins arrondis, contours épais (`UIStroke`), police `FredokaOne` ou `GothamBlack`. Couleurs : BR en bleu (40, 146, 226), Survie en rouge-violet (190, 40, 90). L'UI s'adapte aux téléphones (`UIScale`).
   - **Textes en anglais** dans le jeu (la cible est internationale) : « BATTLE ROYALE », « SURVIVAL », « Last fish alive wins », « Survive waves of fishermen and zombie fish », « 3 players minimum », « VOTE ENDS IN 7 ».

Chaque module commence par un commentaire de quelques lignes qui rappelle son contrat. Écris aussi `luau/README.md` avec un exemple d'appel par module.

---

## 3. Ce que la session locale fait de son côté (pour information, ne pas le faire)

- **Rééquilibrage** :
  - vitesse ±6 % par niveau ;
  - power-up Speed à +30 % ;
  - hameçon : −1 PV toutes les 0,25 s ;
  - Titan : PV ×2, puis remis à 100 % à la fin ;
  - rotation +50 % ;
  - dash de 4 s.
- **Barres de vie** au-dessus des poissons et suppression du sautillement à la nage.
- **Collisions** façon auto-tamponneuses, avec un éjection qui dépend de la masse.
- **Pêcheurs** :
  - hameçons qui suivent les poissons proches (3 m) après 30 s ;
  - logique serveur des pêcheurs harpon (tir toutes les 15 s, capture avec rétraction jusqu'à la surface) et bazooka (toutes les 20 s, −20 PV, ragdoll de 2 s, éjection de 5 m) ;
  - planning d'apparition : un pêcheur toutes les 10 s (5 classiques, 4 harpons, puis le bazooka à la fin).
- **Mode survie** : 3 manches (45 s, 45 s, puis l'infinie « Survive.. If you can »), poissons zombies, et le serveur du vote.
- **Power-ups** : −25 % de taille, chute lente jusqu'au fond, nouveau power-up Force (+25 % de dégâts), nouveaux taux d'apparition.
- **Cartes** : toutes jouées au même emplacement (une seule visible à la fois), Ballon retiré de la rotation, nouveau mur bleuté sur l'Océan.
- **Lobby** : les poissons « show off » portés en sac à dos.
- **Intégration** de tout ce que produit le cloud.

---

## 4. Rapport final attendu (`REPORT.md` à la racine de `cloud-assets-2`)

1. La liste des fichiers produits, chacun avec son rôle.
2. Pour chaque modèle : le nombre de primitives, l'origine et l'orientation.
3. Pour chaque texture : la taille, la disposition et les réglages conseillés.
4. Pour chaque module Luau : le contrat exact et les dépendances (clés `FxAssets` ajoutées).
5. **L'ordre d'intégration** conseillé pour la session locale.
6. Ce qui n'a pas pu être fait ou vérifié.

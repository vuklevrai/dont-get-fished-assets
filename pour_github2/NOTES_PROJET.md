# Don't Get Fished — notes du projet

> À coller au début d'une nouvelle session Claude. Résume le jeu, les règles, l'architecture et l'état actuel.

## 1. Le concept
Battle royale de pêche inversée sur Roblox. Les joueurs sont des **poissons** dans un étang-arène. Ils doivent survivre aux **pêcheurs bots** (hameçons), aux **poissons ennemis bots** et aux autres joueurs. Le dernier poisson en vie gagne.
- Lobby : un **bateau pirate** flottant au-dessus de la carte, où les joueurs ont leur avatar R15 (animations et emotes).
- Style visuel : blocs avec des studs, cartoon, dégradés de couleurs.
- Pour l'instant **PC uniquement** (mobile et console plus tard).
- À corriger plus tard : des matériaux qui se chevauchent (z-fighting).

## 2. Contrôles (poisson)
- Souris verrouillée au centre et invisible. La caméra dirige la nage en 3D.
- W/A/S/D : nager par rapport à la caméra. Espace : monter. Ctrl ou C : descendre. Pas d'accélération avec Maj.
- **Q ou clic droit** : capacité.
- Poisson orienté vers le haut qui touche la surface → **bond** sur un arc prédéfini (24 studs de distance, 7 de hauteur, 1 s), splash à la sortie et à l'entrée dans l'eau, puis bonus de vitesse dégressif (×1,7 pendant 1,3 s).
- Option admin « S = nager à reculons » (sans faire demi-tour).
- Hors de l'eau : Espace fait sauter le poisson par à-coups.
- **M** = menu. **K** = panneau admin.

## 3. Stats et règles
Courbe commune à la **Vitesse** et à la **Taille** : stat 1 = 80 %, 2 = 100 %, 3 = 115 %, 4 = 130 %, 5 = 150 %, puis +20 % par point au-delà de 5. La taille n'a **pas de plafond**.
**PV** selon la stat Santé : 1 = 30, 2 = 50, 3 = 70, 4 = 90, 5 = 120. Régénération de 1 PV/s (pas quand le poisson est pris à l'hameçon).

| Élément | Valeur |
|---|---|
| Base fish | Vitesse 2, Santé 2, Taille 2 |
| Rotation | +25 % (TURN_RESPONSIVENESS = 15) |
| Dash (capacité de base) | charge vers l'avant, recharge 6 s, animation GLB « attaque » |
| Dégâts du dash | 5 + 5 par point de taille au-dessus de 2 (taille 1 = 0, étourdit seulement) |
| Dash qui touche un poisson | la cible est étourdie 1 s (ragdoll) |
| Dash qui touche un mur | c'est soi-même qui est étourdi 1 s |

**Collisions en nage normale** (vitesse relative ≥ 8). Les dégâts se lisent « gros / petit » :
| Écart de taille | Dégâts gros / petit | Effet sur le petit |
|---|---|---|
| 0 | 2 / 2 | — |
| 1 | 1 / 2 | — |
| 2 | 1 / 3 | étourdi 0,5 s |
| 3 | 0 / 3 | étourdi 1 s et repoussé |
| 4 et plus | 0 / 4 | étourdi 1 s et repoussé loin |

**Niveaux 1 à 5** : badge rond au-dessus du poisson, gris (jaune au niveau 5).
- Chaque niveau donne +10 PV max (et +10 PV soignés), +1 taille et +5 % de la vitesse de base.
- Tuer un **joueur** = +1 niveau (les bots ne rapportent rien).
- Quand il ne reste que 2 joueurs (sur une manche qui en comptait plus de 2), les deux gagnent un niveau.

**Secousse d'écran** : légère si moins de 10 dégâts, normale si 10 ou plus.

## 4. Pêcheurs (bots)
- 10 postes autour de l'étang (dossier `PondMap.FishermanSpots`, dont un au bout du ponton).
- 1 pêcheur au début de la manche, puis +1 toutes les 7 s.
- Chaque pêcheur lance un gros hameçon à un endroit aléatoire de la surface (entre 18 et 100 studs de lui), attend 5 à 20 s, puis affiche une boule de brouillard rouge pendant 2 s (zone de 7 studs), puis ferre.
- Un poisson attrapé : vue de côté, il se débat, perd 1 PV toutes les 0,333 s.
- **Mini-jeu pour s'échapper** : cliquer (ou Espace) quand l'aiguille passe sur l'arc vert du cercle rouge. Réussite = libération avec 1 s d'invulnérabilité. Échec = −2 PV, secousse, flash rouge, et l'aiguille tremble avant de repartir.
- Difficulté : facile au début, moyenne à 1:30, difficile à 2:30 (aiguille plus rapide, arc vert plus petit).
- 0 PV pendant la prise = éliminé. Le pêcheur relance au bout de 2 s.

## 5. Power-ups (appâts à la surface)
Toutes les 5 s, 50 % de chance d'en faire apparaître un, près d'un hameçon ou au hasard (8 au maximum, durée de vie 30 s).
- **Level** : +1 niveau et aura jaune pendant 1 s.
- **Speed** : +25 % de la vitesse de base pendant 20 s.
- **Invisible** : 10 s. Immunisé contre les hameçons, invisible pour les autres, semi-transparent pour soi. Toucher un autre joueur annule l'effet, toucher un bot non.

## 6. Poissons ennemis (bots)
- Le premier apparaît à 20 s, puis +1 toutes les 10 s (10 au maximum).
- Stats : 3 partout, sauf 10 PV. Skin de test : Base fish.
- Ils foncent vers le joueur le plus proche (sauf s'il est invisible) et dashent toutes les 5 s s'ils sont à moins de 25 studs.
- Apparition : figés 2 s avec une aura bleue.
- Les règles de collision s'appliquent. Les tuer ne rapporte pas de niveau.

## 7. Manches
- Intermission de 20 s sur le bateau, puis tout le monde devient poisson.
- La manche dure jusqu'à ce qu'il ne reste qu'un poisson (ou plus aucun en solo). Chrono en haut de l'écran, puis 6 s de résultats.
- **Partie test admin** : infinie, on réapparaît en poisson au bout de 3 s.

## 8. Interface (LocalScripts dans StarterPlayerScripts)
- **Hud** :
  - en haut : intermission, chrono de manche, nombre de poissons en vie, badge TEST MODE ;
  - en bas : niveau, barre de PV, tuile de la capacité avec la recharge, chips d'effets actifs, messages courts, secousses.
- **MenuUi** :
  - bouton à gauche au milieu de l'écran ou touche M ;
  - onglet Fish : liste des poissons, aperçu 3D animé (ViewportFrame avec WorldModel), skin, barres de stats sur 5 cases, capacité et description, boutons Select et Show off ;
  - onglet Shop vide.
- **AdminUi** (K, en haut à droite, visible seulement si l'attribut `IsAdmin` est vrai) :
  - lancer la partie test, revenir au lobby, Hold lobby ;
  - choisir son poisson, soin, +1 niveau, se tuer, mode invincible, option « S = nager à reculons » ;
  - faire apparaître un ennemi, un pêcheur ou un appât ; vider les ennemis ou les pêcheurs ;
  - activer ou couper les apparitions automatiques ; difficulté du mini-jeu (Auto, Easy, Medium, Hard) ; état en direct.
- **CatchMinigame** : l'anneau d'échappement (à droite de l'écran).
- Autres scripts :
  - **FishController** : nage, caméra, dash, bond, étourdissement ;
  - **FishAnimator** : animations du poisson ;
  - **Effects** : splash, impacts, auras, invisibilité, appâts ;
  - **HeldFishPose** : bras de l'avatar autour du poisson, côté client ;
  - **PondAmbience** : algues animées ;
  - **WaterAnimator** : eau animée.

## 9. Architecture
**ReplicatedStorage.FishGame**
- `Config` : toutes les constantes (vitesses, temps, pêcheurs, ennemis, power-ups…).
- `FishSpecies` : les espèces, par exemple `BaseFish = {Order, DisplayName, Model="Bonite", Speed, Health, Size, Ability={Id,Name,Cooldown,Description}, Skins}`.
- `FishStats` : les courbes de stats, les dégâts de dash, la table des collisions, les constantes de niveau.
- `FishBuilder` : construit le modèle de poisson.
  - pièces à partir de `FishData.<Model>` ;
  - HumanoidRootPart et pièces `Seg_*` reliées par des Motor6D ;
  - contrôle de la nage : `SwimVelocity` (LinearVelocity) et `SwimAlign` (AlignOrientation) ;
  - tag `AnimatedFish`.
- `FishAnims.Bonite` : les animations du GLB (`repos`, `nage`, `attaque`) converties en keyframes pour Motor6D.Transform.
- `ClientState` : les interfaces ouvertes (souris libérée), l'option nage à reculons, la secousse d'écran.
- `Remotes` : UseAbility, Knockback, Splash, Caught, CatchResult, Released, Admin, SelectFish, SetHolding, ShowOff, Effect.
- **Attributs sur FishGame** :
  - `Phase`, `PhaseEnd`, `RoundStart`, `TestMode`, `Alive`, `Survivors`, `Fishermen`, `Enemies` ;
  - les réglages `Setting*` (Fishermen, Enemies, PowerUps, Difficulty, HoldLobby) ;
  - les textures du splash `SplashCrownTexture` et `SplashRingTexture`.

**ServerScriptService** : `GameServer` démarre les services suivants, rangés dans `Services/`.
- `FishService` :
  - registre des poissons (joueurs et bots) ;
  - fonctions `create`, `applyStats` (ScaleTo, badge de niveau), `levelUp`, `damage`, `stun`, `setInvisible`, `boostSpeed`, et l'événement `died` ;
  - régénération à 1 Hz.
- `CombatService` : dash (avec la recharge), détection des contacts à 20 Hz, coups de dash, collisions selon la taille, relais des splash.
- `RoundService` : boucle des manches, `settings`, `waterSpot`, `makeFish`, `startTest`, `stopTest`.
- `LobbyService` : sélection du poisson, Show off, poisson tenu (« HeldFish » soudé devant le torse).
- `FishermanService`, `PowerUpService`, `EnemyFishService` : chacun avec `start(round)`, `stop()` et `clear()`.
- `AdminService` : actions réservées aux admins (dans Studio, ou au propriétaire du jeu).

**Attributs sur les modèles de poisson**
- Identité et stats : `Species`, `Bot`, `Level`, `Size`, `SpeedFactor`.
- Effets : `Invisible`, `InvisibleUntil`, `SpeedBoostUntil`.
- Capacité : `AbilityCooldown`, `AbilityReadyAt`, `DashingUntil`, `DashStart`.
- États : `StunnedUntil`, `Caught`, `Spawning`.
- Tags : `Fish` (gameplay) et `AnimatedFish`. Les appâts ont le tag `PowerUp`, les algues le tag `Seaweed`.

**Attributs sur le joueur** : `SelectedFish`, `ShowOff`, `GodMode`, `IsAdmin`.

**ServerStorage.DGFTools**
- `PondMapBuilder.build()` : régénère `workspace.PondMap`.
  - rayons de l'étang : 40,5 × 31,5 cellules de 4 studs ;
  - fond autour de −46 ;
  - surface de l'eau à y = −1 ;
  - graine aléatoire fixe : 2026.
- `ShipInstaller` : installe le bateau.
- `AssetPackImporter` : importe les pièces venues de Blender.
- `ServerStorage.MapAssets.Trees` : les modèles d'arbres.

## 10. Pièges techniques déjà rencontrés
- Les épaules de l'avatar R15 sont des `AnimationConstraint` : `C0` est en lecture seule et tourner les attachments côté serveur ne fonctionne pas. Il faut modifier `.Transform` côté client, en PreSimulation (voir HeldFishPose).
- Un `require` lancé depuis execute_luau (MCP) obtient une **instance séparée** du module. Pour déclencher la logique du jeu, passer par les RemoteEvents (par exemple `Remotes.Admin:FireServer("StartTest")` côté Client).
- La taille (`Size`) d'un ParticleEmitter correspond à la **demi-largeur** de la particule.
- `GetDebugId` demande des droits de plugin : on utilise des identifiants numériques (`info.id`).
- Pas d'import de mesh possible par l'API : les modèles Blender sont transférés sous forme de parts, via des données JSON encodées dans une image PNG puis téléversées.
- Pendant une partie, les scripts ne se lisent ni ne se modifient : il faut arrêter le Play d'abord.

## 11. Fichiers hors Studio (dossier de la session)
- `tools/` : `serve.ps1` (serveur HTTP local pour téléverser les images), `export_fish_anims.py`, `Voxelize.cs`, `MakeGif.cs`…
- `fish/bonite_brainrot.glb` : le modèle du poisson et ses animations.
- `spawn/` : le générateur du bateau et des arbres (Blender) et les textures de studs.
- `water/` : la texture d'eau cartoon animée (Blender + OSL).
- `splash/splash_flipbook.py` : le splash (planche de 4 × 4 images, couronne d'eau et anneau d'écume).
- Blender : `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`, lancé en mode `-b --factory-startup --python <script> -- <args>`.

## 12. État actuel et pistes
**Fait** : les 25 points de la grosse demande (interface, capacité, pêcheurs, power-ups, ennemis, niveaux, arène profonde, algues, splash Blender, admin).
**Non vérifié** :
- le clic réussi sur la zone verte du mini-jeu ;
- la nage à reculons avec S, l'étourdissement contre un mur, l'aspect visuel des algues ;
- les règles à plusieurs joueurs (niveau en tuant un joueur, niveau bonus pour les deux derniers, invisibilité face aux joueurs).

**À faire ensuite** :
- monnaie et Shop (achat de poissons et de capacités) ;
- autres espèces et autres skins ;
- sauvegarde des joueurs (DataStore) ;
- version mobile et console ;
- corrections des matériaux qui se chevauchent ;
- plusieurs cartes en rotation.

**Penser à sauvegarder dans Studio (Ctrl+S ou Publier).**

## 13. Phase d'amélioration (26/10) — intégrée
- **Nage** : nouveau `FishController` de la session cloud (inertie, virages en arc, caméra à ressort, bond suivi par la caméra, recul en ragdoll). Vitesse 26 (+30 %), dash 97. Modes de nage pour l'admin via l'attribut joueur `MoveMode` (Classic / CameraOnly / ShiftLock). Les anciens scripts sont dans `ServerStorage.Backup_v1`.
- **Mini-jeu** : version « skill check » (`CatchMinigame`). Le pointeur change de sens à chaque raté. Le poisson pris à l'hameçon se débat sur un bruit lissé.
- **Recul** : chaque collision fait rebondir les deux poissons, et le plus léger part plus loin (masse ∝ échelle³, dans `CombatService`).
- **Pêcheurs** : zone de 17,5 studs (×2,5), capture 1 s après l'apparition du brouillard. Le brouillard rouge réaliste est dessiné côté client (Effects « Fog »).
- **Power-ups** : 3× plus gros, 6 studs sous la surface, disparition après 12 s avec clignotement les 3 dernières secondes. Speed = +100 %. **Titan**, rare (poids 8 contre 30) : +5 taille et +5 vitesse pendant 15 s, avec éclair et onde de choc.
- **Effets** (`ScreenFx`) : lignes de vitesse et léger flou au dash, flash rouge du poisson touché, vignette rouge à 10 % de PV ou moins.
- **Menu** : panneau élargi à 900 px, onglet Options avec mode performance (`ClientState.performance` : eau et algues figées, pas d'ombres, moins de particules, fleurs masquées). Le choix n'est pas encore sauvegardé.
- **Cartes** : toutes présentes dans le monde, et `MapService` choisit celle de la manche (rotation, ou choix admin « Map: »).
  - Pond : à l'origine. Aquarium : (1600, 0, 0). Ballon : sphère d'eau en (−1600, 0, 0), rayon 110. Océan : centre (0, 0, 2400).
  - Attributs publiés sur FishGame : `MapName`, `MapWaterShape`, `MapWaterLevel`, `MapWaterCenter`, `MapWaterRadius`.
  - Chaque carte contient les dossiers `FishermanSpots`, `PlayerSpawnPoints` et `Barriers`.
  - Construites par `ServerStorage.DGFTools.MapInstaller` (tables de la session cloud) ; les barrières de l'étang par `PondMapBuilder.buildBarriers`.
- **Barrières invisibles** : groupe de collision `FishBarrier`, qui ne bloque que les poissons (groupe `Fish`). Elles longent le rivage de l'étang, couvrent le ponton, prolongent les vitres de l'aquarium et forment le mur de zone de l'Océan. Sur le Ballon, les pods sont en `NoFish` : un poisson éjecté de la bulle tombe dans le vide et meurt.
- **Textures** : identifiants dans `ReplicatedStorage.FishGame.FxAssets`.
- **Transfert de code ou de données vers Studio sans tout recopier** : `tools/pack_png.ps1` (fichiers → PNG), téléversement avec `upload_image`, puis décodage par EditableImage dans Studio.

# Rapport de la session cloud — Don't Get Fished, phase d'amélioration

Branche `cloud-assets`. Les six tâches du brief (C1 à C6) sont livrées. **Rien n'a pu être testé dans Roblox Studio** : le code Luau a été relu ligne par ligne et passé dans un vérificateur de structure maison, la physique de nage a été simulée en Python, et tous les visuels ont été rendus et regardés. Les réglages finaux se feront en jouant.

## 1. Fichiers produits

### Code Luau (`luau/`)
| Fichier | Rôle |
|---|---|
| `FishController.client.luau` | **C5**, remplacement complet du contrôleur de nage : inertie et glisse, virages en arc (rayon qui grandit avec la vitesse), roulis, tangage, ondulation, coups de queue à ±5 %, vitesse +30 %, bond suivi par la caméra (souris ignorée puis rendue en douceur), caméra à ressort avec avance et FOV qui suit la vitesse, 3 modes (`Classic`, `CameraOnly`, `ShiftLock`), recul et ragdoll avec traînée exponentielle et rebonds, vue de l'hameçon lissée, eau en plan ou en **sphère** (carte Ballon) |
| `ClientState.luau` | Les secousses passent par du **bruit lissé** (`math.noise`) au lieu de positions aléatoires image par image, ce qui supprime les « téléportations » de caméra. Il porte aussi l'intensité et la phase de nage. L'API ne change pas. |
| `FishAnimator.client.luau` | 6 lignes changées : la queue du poisson local suit le rythme du contrôleur. |
| `CatchMinigame.client.luau` | **C6**, le mini-jeu « skill check » (détails en § 3) |
| `ConfigPatch.md` | Les constantes à modifier ou ajouter dans `Config`, les attributs utilisés, et des patchs serveur conseillés : tremblement lissé du poisson pris à l'hameçon, recul selon la masse. |
| `MOVEMENT_DESIGN.md` | Le modèle de nage expliqué, les mesures, un tableau « ressenti → paramètre » pour régler, et une liste de tests à faire dans Studio. |
| `catch_minigame_preview.html` / `.png` | Aperçu **jouable** du mini-jeu dans un navigateur, et une planche de 3 états. |

### Effets (`fx/`) — détails et réglages Roblox dans `fx/README.md`
| Fichier | Rôle |
|---|---|
| `fog_flipbook.png` (4×4 de 256²), `fog_flipbook_8x8.png` (8×8 de 128²), `fog_puff.png` (512²) | **C4.1**, brouillard de capture rouge et réaliste : volume Cycles, boucle parfaite, plongée de trois quarts |
| `titan_lightning_flipbook.png` (4×4 de 256²), `titan_flash_ring.png` (512²) | **C4.2**, éclair Titan cartoon (amorce, impact, flash, ramifications, fumée noire) et onde de choc |
| `speed_line.png` (256×32), `speed_lines_screen.png` et `_b.png` (1024²) | **C4.3**, lignes de vitesse du dash |
| `low_hp_vignette.png` (1024²) | **C4.4**, vignette rouge de quasi-mort |
| `zone_wall_flipbook.png` (4×4, se répète à l'horizontale), `zone_wall_static.png` (512²) | **C3**, mur de zone style tempête Fortnite |
| `*_preview_water.png`, `*_preview_sky.png`, `zone_wall_tiling_check.png` | Aperçus sur l'eau (78, 214, 251) et sur le ciel |
| `fog_flipbook.py`, `titan_lightning.py`, `screen_fx.py`, `zone_wall.py`, `fxlib.py` | Générateurs Blender déterministes |

### Cartes et modèles (`maps/`, `models/`) — détails dans `maps/README.md`
| Fichier | Rôle |
|---|---|
| `maps/aquarium/aquarium.json`, `aquarium_data.png`, `spots.json`, `previews/` | **C1**, carte Aquarium |
| `models/futuristic_pod.json`, `futuristic_pod_data.png` | **C1**, modèle `FuturisticPod` réutilisable |
| `maps/ballon/ballon_platforms.json`, `_data.png`, `spots.json`, `previews/` | **C2**, carte Ballon : plateformes flottantes et placement des pods |
| `models/fishing_boat.json`, `_data.png`, `fishing_boat_spots.json` | **C3**, bateau de pêche et son point `FishermanStand` |
| `models/island.json`, `_data.png` | **C3**, île et palmier |
| `maps/ocean/ocean_markers.json`, `_data.png`, `spots.json`, `previews/` | **C3**, disposition de l'océan : panneaux du mur de zone, 10 bateaux, île, arène |
| `models/previews/` | Aperçus du pod, du bateau et de l'île |
| `maps/dgf_maps.py`, `maps/build_maps.py` | Générateurs (géométrie, puis export et rendus Blender) |

### Entrées rangées dans le dépôt
- `studio_export/` : les 3 exports `.rbxm` (binaires) et les **26 scripts extraits en clair** dans `src/`, plus `GameServer`.
- `references/` : les 5 images de référence.
- `pour_github/` : ce que tu as déposé (notes, brief, scripts de référence).

## 2. Les cartes

| Carte / modèle | Dimensions réelles | Primitives | Points d'ancrage |
|---|---|---|---|
| **Aquarium** | eau de 324 × 252, surface à y = −1, sable vers −86 (environ 85 à 90 de profondeur), verre de 2 d'épaisseur jusqu'à y = +8, rebord jusqu'à +11, meuble dessous | **1 410** / 4 000 | 10 `FishermanSpots` (sol des pods à y = 11, regard vers le centre), 22 `SeaweedSpots`, `PlayerSpawnVolume` (300 × 60 × 228), axes des 4 tunnels du rocher, château, arche |
| └ gros rocher | environ 91 × 45 × 70, creux, avec 4 passages de 13 à 14 studs (environ 11 libres) | 823 avec les petits rochers | — |
| └ mini château | 46 × 32 × 46, portes de 14 × 17, fenêtres de 10 × 10, 4 tours | 116 | — |
| **FuturisticPod** | disque de 16 + rampe de 6, hauteur environ 13 avec l'arche | **78** / 300 | origine = sol du pod, regard vers −Z |
| **Ballon** | sphère de rayon 110 en (0, 0, 0) (eau faite en local), 10 pods de y ≈ −6 à y ≈ 60 | **190** (plateformes) | 10 `FishermanSpots`, bout de rampe à exactement 8 de la bulle, `PlayerSpawnVolume` (cube de 111), `PlayerSpawnSphere` (r = 88), attributs à poser |
| **Océan** | boîte de 1 200 × 1 200, arène de 300 × 240, mur de y = −60 à +40 | **4** (mur de zone) | 10 `BoatSpots` (proue vers le centre, au moins 3 studs hors du mur), 10 `FishermanSpots` en coordonnées monde, `IslandSpot` (200, −1, −470), `PlayerSpawnVolume` |
| **FishingBoat** | 26 × 10, hauteur environ 14 avec le mât | **232** / 600 | `FishermanStand` en (0 ; 4,6 ; 10,6), regard vers la proue |
| **Island** | environ 34 de large, palmier d'environ 20 de haut | **96** | origine sur la ligne d'eau |

Tous les matériaux sont dans la liste autorisée. Toutes les rotations ont été vérifiées : orthonormées, déterminant +1. Chaque image de données est relue pour vérifier qu'elle redonne exactement son JSON.

## 3. Réglages clés

### Nage (`Config`, voir `luau/ConfigPatch.md`)
| Réglage | Valeur | Effet mesuré (simulation à 60 images/s) |
|---|---|---|
| `SWIM_SPEED` | 20 → **26** | +30 % |
| `SWIM_ACCEL` | 5 | 0 → 90 % de la croisière en 0,47 s |
| `SWIM_GLIDE_DRAG`, `SWIM_GLIDE_BRAKE` | 2,2 / 6 | glisse sous 3 studs/s en 0,73 s, arrêt en 1,07 s (environ 9 studs) |
| `SWIM_TURN_RATE`, `SWIM_TURN_FALLOFF`, `SWIM_TURN_SHARPNESS` | 10 / 60 / 14 | 90° en 0,30 s. Demi-tour en arc : environ 8 studs à 26 studs/s, 14 à 39, 20 à 52. |
| `SWIM_LATERAL_DRAG`, `SWIM_CARVE` | 14 / 0,85 | vitesse conservée dans les virages, dérapage maximal d'environ 20° |
| `SWIM_PULSE`, `SWIM_UNDULATION` | 0,05 / 0,06 rad | coups de queue de ±5 %, en phase avec l'animation |
| `DASH_SPEED` | 75 → **97** | dash d'environ 41 studs, retour à la croisière en environ 0,7 s |
| `LEAP_HEIGHT`, `LEAP_DISTANCE`, `LEAP_TIME` | 7 → **10**, 24 → 30, 1,0 → 1,1 | bond plus haut, caméra automatique, souris rendue en 0,35 s |
| `STUN_DRAG` (+ `STUN_DRAG_QUAD`) | 0,92/s | environ 60 % de vitesse perdue par seconde. Impulsion 45 → 43 studs parcourus, 80 → 73. |
| `CAMERA_FOLLOW`, `CAMERA_LEAD`, `CAMERA_FOV_SPEED` | 10 / 0,08 s / +12° | caméra à ressort sans dépassement, avance dans la direction de nage, FOV qui monte avec la vitesse |

### Mini-jeu (C6)
- **Look** : anneau épais et net dessiné en pastilles rondes qui se chevauchent (bords lisses, angles exacts, pas de cadres tournés), zone verte avec bande « parfaite », pointeur avec halo et traînée.
- **Raté** : tremblement en **oscillation amortie** (7°, 9 Hz, 0,3 s), puis **changement de sens**, flash rouge de l'anneau, petit recul (ressort), « −2 », secousse lissée, nouvelle zone devant le pointeur.
- **Réussite** : couleurs vert-jaune-cyan qui tournent sur l'anneau, rebond (ressort sous-amorti), onde de choc, étincelles, « ESCAPED! » animé.
- **La bande « parfaite »** est uniquement visuelle : le protocole réseau ne change pas.

## 4. Ce qui n'a pas pu être fait ou vérifié

1. **Aucun test dans Roblox Studio.** Il n'y a pas d'accès à Studio, et je n'ai pas eu le droit d'exécuter un analyseur Luau téléchargé. À vérifier en jouant : tout ce qui est listé à la fin de `luau/MOVEMENT_DESIGN.md`.
2. **Les valeurs de nage** sont des valeurs de départ, calibrées par simulation mais pas en jouant.
3. **Importeur** : les tables suivent le format de `spawn/assets.json`, mais l'importeur de la session locale (`AssetPackImporter`) n'a pas été lancé dessus. Si les matériaux `Wood`, `Metal` ou `ForceField` n'y étaient pas encore gérés, il faut les ajouter.
4. **Mantaflow non utilisé** pour le brouillard : une simulation ne boucle pas proprement. J'ai pris des volumes Cycles en bruit 4D, la solution de repli prévue par le brief.
5. **Le mur de zone animé** demande un `SurfaceGui` qui avance `ImageRectOffset`, parce qu'un objet `Texture` ne sait pas afficher une case de planche (voir `fx/README.md`).
6. **Hors de mon périmètre (session locale)** : les barrières invisibles, le recul côté serveur (une suggestion est dans `ConfigPatch.md`), les power-ups, l'onglet Options, le flash rouge du poisson touché, l'intégration de la vignette et de la distorsion, le choix du mode de déplacement dans le panneau admin, l'intégration et la rotation des cartes, l'eau en terrain.

**Écarts assumés par rapport au brief :**
- **Bateaux** : leur cap pointe vers le centre, donc le pêcheur, à l'arrière, regarde vers la proue par-dessus la cabine. C'est pour ça que sa plateforme est surélevée.
- **Pods de l'aquarium** : ils regardent le centre exact du bac, donc en biais sur les côtés.
- **`ClientState` et `FishAnimator`** sont aussi modifiés, alors que le brief ne demandait que `FishController` : c'était nécessaire pour la secousse lissée et la synchronisation de la queue.

## 5. Ordre d'intégration conseillé (session locale)
1. Mettre à jour `Config` (`luau/ConfigPatch.md`), puis remplacer `ClientState`, `FishAnimator`, `FishController` et `CatchMinigame`.
2. Tester la nage dans l'étang actuel, régler avec `MOVEMENT_DESIGN.md`, puis appliquer les patchs serveur conseillés (§ 6 de `ConfigPatch.md`).
3. Ajouter au panneau admin le choix du mode de déplacement (attribut joueur `MoveMode`).
4. Téléverser les textures `fx/` et brancher les effets.
5. Importer les tables `maps/` et `models/`, cloner les pods et les bateaux aux spots, remplir l'eau en terrain, poser les attributs `MapWater*` à chaque rotation de carte (obligatoire pour la carte Ballon).

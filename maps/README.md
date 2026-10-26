# Nouvelles cartes et modèles (C1, C2, C3)

Géométrie : `maps/dgf_maps.py`, en Python pur. Mêmes conventions que `spawn/dgf_assets.py` : studs, Y vers le haut, coordonnées Roblox, même `export_table`.
Export et aperçus : `maps/build_maps.py`, avec Blender.

```
blender -b --factory-startup --python maps/build_maps.py -- <racine_du_dépôt> [models,aquarium,ballon,ocean] [export|render|all]
```

Pour un rendu d'essai rapide : variable d'environnement `PREVIEW_SCALE=0.5`. Tout est déterministe (graines fixes). Les aperçus utilisent `spawn/tex/stud_color.png`, cherché dans `pour_github/spawn/tex` puis dans `spawn/tex`.

## Format des fichiers

- **`<nom>.json`** : la table de primitives, exactement le format de `spawn/assets.json` :
  `{"v":1,"assets":[...],"groups":[...],"shapes":["Block","Wedge","Cylinder","Ball"],"mats":[...],"prims":[[asset,group,shape,mat,collide,transparency,r,g,b,sx,sy,sz,px,py,pz,qx,qy,qz,qw],...]}`
- **`<nom>_data.png`** : la même table encodée pour l'import : 4 octets de longueur en big-endian, puis le JSON UTF-8 rangé dans les pixels RGB, largeur 512. Le script relit chaque image et vérifie qu'elle redonne exactement le JSON. Au-delà de 512×1024, la table serait coupée en `_part1`, `_part2`… Aucune n'en a eu besoin.
- **Matériaux utilisés** : seulement `Stud`, `Smooth`, `Glass`, `Neon`, `Wood`, `Metal` et `ForceField`.
- **`spots.json`** : les points d'ancrage. Chaque point contient :
  - `pos` [x, y, z] ;
  - `quat` [qx, qy, qz, qw] ;
  - `cframe` : 12 nombres, à utiliser directement avec `CFrame.new(table.unpack(spot.cframe))` ;
  - parfois des champs en plus (`height` pour les algues, `lat` pour les pods du Ballon).

  Le `LookVector` (−Z) de chaque CFrame indique la direction regardée.

## C1 — Aquarium (`maps/aquarium/`)

| | |
|---|---|
| Eau (intérieur du verre) | **324 × 252** studs (x ±162, z ±126), surface à **y = −1**, sable vers y = −86 (entre −92 et −82), donc **environ 85 à 90 studs de profondeur** |
| Verre | 4 parois et un fond en `Glass` (transparence 0,6), **2 studs d'épaisseur** (collision), de y = −96 à +8 |
| Rebord | plastique sarcelle de 6 × 3 studs, de y = +8 à **+11**, bande `Neon` cyan dessus. Montants d'angle et cadre du bas assortis. |
| Meuble | meuble en bois sous le bac : plateau, portes, poignées, plinthe. Fond en lattes de bois clair derrière la vitre arrière, comme sur la photo de référence. |
| Sable | 252 dalles de 18 × 18 en blocs à studs, légères dunes (plus haut au fond), dégradé doux en 3 nuances, 114 graviers |
| **Gros rocher au centre** | rocher blanc poreux en voxels de 3,5 studs, environ 91 × 45 × 70 (environ 40 studs au-dessus du sable). **Creux**, avec une chambre centrale et **4 passages** : un tunnel est-ouest et un nord-sud qui traversent la chambre, un tunnel en diagonale et une cheminée vers le haut. Alésages de 13 à 14 studs, environ 11 studs de passage libre après voxelisation, pour un poisson de taille 5 qui mesure 9 × 3,5. Axes des tunnels dans `spots.json`, clé `Tunnels`. |
| **Mini château** | centre (−100, z = 50), donjon creux de 46 × 32 × 46 : **portes de 14 × 17** sur deux côtés (coins arrondis), **fenêtres de 10 × 10** sur les deux autres, 4 tours rondes à créneaux et toits en cône à paliers (rouge et bleu), drapeaux |
| Autres obstacles | une arche rocheuse sous laquelle on nage (104, z = −54), 5 petits rochers, 3 bois flottés, un coffre au trésor ouvert, une amphore, un diffuseur avec sa colonne de bulles |
| **Primitives** | **1 410** (budget 4 000), pods non compris |
| `spots.json` | `FishermanSpots` (10), `SeaweedSpots` (22, avec une hauteur conseillée de 24 à 52 studs), `PlayerSpawnVolume` (centre (0, −40, 0), taille 300 × 60 × 228), `PlayerSpawnPoints` (24 points vérifiés à plus de 6 studs de toute pièce solide), `water`, `Tunnels`, `Castle`, `Arch` |

- **Pods** : 10 `FuturisticPod` hors du verre, à hauteur du rebord : 3 sur chaque grand côté, 2 sur chaque petit côté. Leur sol est à **y = 11**.
- **Orientation des pods** : chacun regarde le centre du bac. Le bout de sa rampe s'arrête au-dessus du rebord, à au moins 2 studs du verre (vérifié par le calcul).
- **Algues** : la session locale les génère et les anime aux `SeaweedSpots`. Les aperçus montrent de simples bâtonnets verts à leur place.
- **Aperçus** (`previews/`) :
  - `aquarium_top_preview.png` : vue de dessus ;
  - `aquarium_overview_preview.png` : vue d'ensemble ;
  - `aquarium_cut_side_preview.png` : coupe de côté au milieu du rocher, qui montre la chambre et les tunnels ;
  - `aquarium_underwater_rock_preview.png` : sous l'eau, vers le rocher ;
  - `aquarium_underwater_castle_preview.png` : sous l'eau, vers le château.

## Modèle FuturisticPod (`models/futuristic_pod*`)

| | |
|---|---|
| Primitives | **78** (budget 300) |
| Origine | **le centre du sol du pod**, là où se tient le pêcheur. Regarde vers **−Z** : c'est le côté de la rampe. |
| Forme | disque métallique de 16 studs, gros anneau `Neon` cyan, rayons lumineux au sol, rampe de 6 studs vers l'eau, poteaux et rambarde lumineuse sur la moitié arrière, arche lumineuse, console, base en cône avec 3 réacteurs (il « flotte ») |
| Pose | cloner le modèle et le placer avec `PivotTo(CFrame du spot)`, en mettant l'origine du modèle au sol du pod |

## C2 — Ballon (`maps/ballon/`)

- **Eau** : faite en local, avec `Terrain:FillBall` en (0, 0, 0) et un rayon de **110**.
- **Placement** : 10 pods tout autour, à des hauteurs variées (latitudes de −4° à 32°), chacun sur une **petite plateforme flottante** hexagonale. Ces plateformes sont la table `ballon_platforms`, 190 primitives : 19 par plateforme.
- **Distance** : le bout de chaque rampe est à exactement **8 studs** de la bulle (dans la fourchette de 6 à 10 demandée).
- **Orientation** : chaque pod regarde le centre (horizontalement).
- **`spots.json`** : `FishermanSpots` (10), `SeaweedSpots` (vide), `PlayerSpawnVolume` (cube de 111 de côté inscrit dans la sphère), `PlayerSpawnSphere` (rayon 88), `PlayerSpawnPoints` (24 points dans la sphère), `water`, plus `ClientAttributes` : les attributs à poser sur `ReplicatedStorage.FishGame` pour que le nouveau contrôleur traite l'eau comme une **sphère** (`MapWaterShape = "Sphere"`, `MapWaterCenter`, `MapWaterRadius`).
- **Aperçus** : `ballon_overview_preview.png` (sphère bleue translucide avec les pods) et `ballon_side_preview.png`.

## C3 — Océan (`maps/ocean/`, `models/`)

| | |
|---|---|
| Disposition | boîte d'eau de **1 200 × 1 200** (faite en local, fond conseillé à y = −46), **arène de 300 × 240** au centre, délimitée par le mur de zone |
| Mur de zone | 4 panneaux `ForceField` translucides (table `ocean_markers`, groupe `ZoneWall`), de y = −60 à +40, à recouvrir avec `fx/zone_wall_*.png` (voir `fx/README.md`) |
| Bateaux | 10 `BoatSpots` : 3 sur chaque grand côté, 2 sur chaque petit. Chaque **proue pointe vers le centre de l'arène** et reste à **3 studs ou plus hors du mur** (vérifié). Ces CFrames placent l'origine du bateau, sur la ligne d'eau. |
| Pêcheurs | 10 `FishermanSpots`, déjà convertis en coordonnées monde : le point `FishermanStand` de chaque bateau |
| Île | `IslandSpot` en (200, −1, −470), loin derrière un grand côté, hors d'atteinte |
| `PlayerSpawnVolume` | centre (0, −23,5, 0), taille 280 × 34 × 220. Plus 24 `PlayerSpawnPoints`. |

**Bateau de pêche `FishingBoat`** (`models/fishing_boat*`) :
- **Taille** : **232 primitives** (budget 600), 26 × 10 studs, origine sur la ligne d'eau au centre de la coque, proue vers −Z.
- **Coque** : rouge sous l'eau, blanche avec une bande bleue, avec bastingages ; pont en lattes.
- **Cabine** : timonerie vitrée tout autour, avec porte, radar, antenne, projecteur, feux de navigation (rouge à bâbord, vert à tribord) et bouée de sauvetage.
- **Équipement** : mât et bras de pêche jaune avec poulie, cordage et filet suspendu ; tas de filets, caisses, bacs à poissons, bouées orange, **3 pneus de chaque côté**.
- **Plateforme de pêche** : surélevée à l'arrière, avec marches et rambarde. Le pêcheur y voit par-dessus la cabine.
- **Collision** : coque, pont, cabine et plateforme. Le petit matériel ne collisionne pas.
- **`FishermanStand`** : dans `models/fishing_boat_spots.json`, en (0 ; 4,6 ; 10,6) en local, regard vers la proue.

**Île `Island`** (`models/island*`) :
- **Taille** : **96 primitives**, îlot de sable d'environ 34 studs de large.
- **Sable** : blocs à studs en 3 nuances (mouillé, humide, sec), qui descendent sous l'eau.
- **Décor** : rochers et touffes d'herbe, et un **palmier** au tronc courbé à anneaux, avec 3 noix de coco et 8 palmes tombantes.
- **Origine** : sur la ligne d'eau.

**Aperçus** :
- `maps/ocean/previews/` : `ocean_top_preview.png`, `ocean_overview_preview.png`, `ocean_boats_close_preview.png` ;
- `models/previews/` : le pod, le bateau (deux vues) et l'île.

---

# Brief 2 : décor de l'Océan (C1) et armes (C2)

- **Géométrie** : `maps/dgf_props.py`, qui reprend les outils et les conventions de `dgf_maps.py`.
- **Export et aperçus** : `maps/build_maps.py`, avec deux nouvelles cibles :

```
blender -b --factory-startup --python maps/build_maps.py -- <racine_du_dépôt> ocean_decor,weapons [export|render|all]
```

## C1 — Décor de l'Océan (`maps/ocean_decor/`)

### Squelette de mégalodon (`megalodon_fossil.json` / `_data.png`)

| | |
|---|---|
| Taille | **90 × 33 × 46,5 studs** (long × haut × large, nageoires pectorales comprises) |
| Primitives | **459** (budget 1 200) |
| Origine | **le centre du dessous, posé sur y = 0**. La tête regarde vers **−Z**. |
| Pose | sur le ventre, en léger arc : la queue se courbe d'environ 7 studs sur le côté, gueule grande ouverte (30°) |
| Crâne | crâne bas et large, à section en « maison » : arête et bords biseautés, rostre pointu au-dessus des mâchoires, orbites sombres, arcades, narines |
| Mâchoires | en U ; la mâchoire inférieure repose sur le sable, la supérieure est relevée de 30° ; articulation sur les côtés |
| Dents | **2 rangées par mâchoire** (15 grandes dents, puis 12 petites en quinconce), chaque dent faite de 2 `Wedge` |
| Colonne | 24 vertèbres **séparées** (disques), plus 4 qui montent dans le lobe haut de la queue. Épines neurales sur toute la colonne, épines hémales sous la queue, apophyses transverses dans le tronc. |
| Côtes | **4 paires**, courbes, en tonneau : elles s'écartent puis se referment vers le bas, inclinées vers l'arrière, la pointe à moitié enfouie dans un monticule de sable |
| Nageoires | pectorales (rayons couchés sur le sable), dorsale (7 rayons), caudale hétérocerque (7 rayons en haut, 5 en bas) |
| Couleurs | os de (231, 220, 190) à (196, 180, 146) ; mâchoires (184, 166, 128) ; dents (250, 246, 234) ; fissures sombres (bandes sur le crâne, anneaux sur les côtes et les vertèbres) ; mousse verte |
| Collision | **seulement le crâne, les mâchoires et les vertèbres** (groupes `Skull`, `Jaw`, `Spine` : 73 primitives). Tout le reste a `collide = 0`. |
| Groupes | `Skull`, `Jaw`, `Teeth`, `Spine`, `SpineDetail`, `Ribs`, `Fins`, `Detail` (fissures, mousse), `Sand` (monticules qui s'enfoncent sous y = 0 : on peut les supprimer ou les recolorer) |

**Vérification « on nage entre les côtes »**, avec la même méthode que pour les tunnels de l'Aquarium : la distance exacte à chaque primitive, mesurée à hauteur de poisson (y = 8).
- **Passages latéraux** : une ligne entre deux paires de côtes, qui traverse la cage d'un flanc à l'autre. Diamètre libre : **11,45 / 11,45 / 11,52 studs** pour les 3 passages (≥ 11 demandés).
- **Dans la cage, dans la longueur** : au moins **11 studs libres de z = −12,3 à z = +25,7** (38 studs), et jusqu'à 16,5 studs au plus large.
- Les résultats sont recopiés dans `spots.json`, clé `fossil_checks`.

### Coraux (`corals.json` / `_data.png`)

Une seule table contient 6 assets, **`Coral1` à `Coral6`**. Tous ont l'origine **au centre de la base, sur y = 0**, et **aucune collision**. Les dômes peuvent descendre un peu sous y = 0 : ils s'enfoncent dans le fond.

| Variante | Asset | Primitives | Largeur × hauteur × profondeur (×1) | Description |
|---|---|---|---|---|
| 1 | `Coral1` | 58 | 9 × 11 × 5,5 | corail branchu, rose vif, bouts plus clairs |
| 2 | `Coral2` | 107 | 12 × 11,5 × 2,6 | gorgone en éventail, violette, dentelle dans un seul plan vertical |
| 3 | `Coral3` | 98 | 12,5 × 6,7 × 10 | corail cerveau, jaune, dômes cerclés de sillons ondulés |
| 4 | `Coral4` | 43 | 8,6 × 7,5 × 9,3 | corail tuyau d'orgue, orange : tubes à bord clair et bouche sombre |
| 5 | `Coral5` | 42 | 14,7 × 8 × 14,7 | corail table, turquoise : pied et deux plateaux à bord festonné |
| 6 | `Coral6` | 91 | 15 × 8 × 14 | anémone : colonne violette, tentacules roses à bout orange |

### `spots.json` (repère de l'Océan, posé sur le fond : y = −46)

- **`FossilSpot`** : (60, −46, −40), dans l'arène mais décalé du centre. Il est tourné pour que la tête regarde vers le côté de l'arène. Le point d'apparition le plus proche est à 17 studs de l'os le plus proche : personne n'apparaît dans le squelette.
- **`CoralSpots`** : **60 points** (40 dans l'arène, en 11 bosquets ; 20 dehors, jusqu'à ±500), chacun avec `variant` (1 à 6, environ 10 de chaque) et `scale` (de 0,8 à 1,6).
- **`SeaweedSpots`** : **43 points** (30 dedans, dont 3 autour du fossile ; 13 dehors), chacun avec `height` (de 18 à 40).
- **Règle commune** : aucun corail ni aucune algue ne s'approche **à moins de 25 studs d'un `PlayerSpawnPoint`**, sur toute sa hauteur (segment de la base au sommet) : minimum mesuré 25,1. Rien non plus sur l'emprise du fossile.
- **Clés en plus** : `CoralVariants`, `stats`, `fossil_checks`, `primitives`.
- **Pose** : `CFrame.new(table.unpack(spot.cframe))`, puis pour les coraux `model:ScaleTo(spot.scale)` avec l'origine au pied.

**Aperçus** (`previews/`) :
- `megalodon_fossil_preview.png` et `_side.png` : le fossile seul, deux vues ;
- `corals_preview.png` : les variantes 1 à 6, de gauche à droite ;
- `ocean_decor_underwater_preview.png` et `_wide_preview.png` : l'arène sous l'eau ; les algues y sont des tiges provisoires ;
- `ocean_decor_top_preview.png` : vue de dessus, avec le cadre de l'arène en bleu et les points d'apparition en rouge.

## C2 — Armes (`models/`)

Pour tous les modèles : **aucune collision**, canon (ou sens de vol) vers **−Z**.

| Modèle | Fichiers | Primitives | Origine | Taille |
|---|---|---|---|---|
| `HarpoonGun` | `harpoon_gun.json` / `_data.png` | **58** (dont les 26 du groupe `Harpoon`) | la poignée pistolet (main droite) | 6,5 studs de la crosse à la bouche ; le harpon chargé dépasse de 1,6 |
| `Harpoon` | `harpoon.json` / `_data.png` | **26** | la pointe | 7,75 studs de la pointe à l'anneau |
| `Bazooka` | `bazooka.json` / `_data.png` | **40** (dont les 13 du groupe `Missile`) | la poignée pistolet | 6,6 studs de la bouche à la tuyère arrière |
| `Missile` | `missile.json` / `_data.png` | **13** | le nez | 3,8 studs |

**Description des modèles :**
- **HarpoonGun** : fût en bois, poignée à cannelures, crosse en caoutchouc, rail et tête métalliques, deux élastiques orange tendus jusqu'aux crans du harpon, moulinet jaune sous le fût. Le **groupe `Harpoon`** est le harpon chargé : il suffit de le détacher ou de le cacher au tir.
- **Harpoon** : tige en acier, pointe en croix avec **4 barbillons** repliés vers l'arrière, crans, bande orange, butée, **anneau en laiton** à l'arrière pour la corde.
- **Bazooka** : tube vert militaire avec **bandes de danger jaunes et noires**, bouche et tuyère évasées, poignée pistolet, détente rouge, poignée avant, appui d'épaule, poignée de transport, viseur latéral (lentille bleue à l'avant, rouge à l'arrière). Le **groupe `Missile`** est le missile chargé, nez visible dans la bouche.
- **Missile** : ogive rouge, corps blanc avec bande rouge, 4 ailerons rouges en flèche, tuyère sombre et petit disque `Neon` orange.

**`models/weapons_spots.json`** (coordonnées locales, avec `pos`, `quat` et `cframe`) :
- `HarpoonGun` : `Muzzle`, `HarpoonTip`, `RopeAttach` (l'anneau du harpon chargé) ;
- `Harpoon` : `Tip`, `RopeAttach` ;
- `Bazooka` : `Muzzle`, `MissileNose`, `Backblast` (regarde vers l'arrière) ;
- `Missile` : `Nose`, `Exhaust` (tuyère, regarde vers l'arrière, pour la fumée).

**`luau/WeaponModels.luau`** contient les mêmes 4 tables, prêtes à construire : `WeaponModels.build(name, anchored?)`. Avec lui, aucun import n'est nécessaire (voir `luau/README.md`).

**Aperçus** (`models/previews/`) : `harpoon_gun_preview.png`, `harpoon_preview.png`, `bazooka_preview.png`, `missile_preview.png`, et `weapons_lineup_preview.png` (les 4 modèles à côté d'une silhouette R15 de 5,2 studs, pour l'échelle).

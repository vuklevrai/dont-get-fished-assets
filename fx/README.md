# Effets (C4) et texture du mur de zone (C3)

Tout est en PNG RGBA à **alpha droit** (non prémultiplié), en puissances de 2. Les planches d'images se lisent de gauche à droite, puis de haut en bas. Chaque générateur est un script Blender déterministe (graines fixes) :

```
blender -b --factory-startup --python fx/<script>.py -- <dossier_de_sortie>
```

Ils tournent aussi sous Windows avec Blender 5.2. `fog_flipbook.py` utilise Cycles (volume), les autres dessinent en 2D avec numpy (`fxlib.py`) et enregistrent via Blender.
Les aperçus animés (`*_water.gif`, `*_sky.gif`) sont faits par `make_gifs.py`, qui demande Python et Pillow, sans Blender.

## 1. Brouillard de capture, rouge et réaliste (`fog_flipbook.py`)

| Fichier | Format | Usage |
|---|---|---|
| `fog_flipbook.png` | 1024², **4×4** images de 256², boucle sans raccord | brouillard principal |
| `fog_flipbook_8x8.png` | 1024², **8×8** images de 128², même boucle en 64 images | mouvement plus fluide, image plus douce (au choix) |
| `fog_puff.png` | 512², une bouffée isolée | particules en plus, pour l'épaisseur |
| `fog_preview_water.png`, `fog_preview_sky.png` | aperçus sur l'eau (78, 214, 251) et sur le ciel | contrôle |

- **Rendu** : volume Cycles, fumée en bruit 4D déformé (volutes), cœur (170, 20, 20), bord (255, 60, 40), vue en plongée de trois quarts (58°). La boucle est parfaite, parce que le bruit est échantillonné sur un cercle dans l'espace (z, w).
- **Taille** : le brouillard visible (alpha > 0,2) occupe environ **85 % de la largeur** de l'image (mesuré sur les 16 images : 0,852). Pour une zone de capture de rayon **17,5 studs**, la demi-largeur de la particule doit être 17,5 / 0,852 ≈ **20,5 studs** (`ParticleEmitter.Size` est une demi-largeur).
- **ParticleEmitter conseillé** :
  - `FlipbookLayout = Grid4x4`, `FlipbookMode = Loop`, `FlipbookFramerate = 12` (boucle de 1,33 s) ;
  - `FlipbookStartRandom = true`, `Orientation = FacingCamera`, `LightInfluence = 0.6`, `LightEmission = 0.1` ;
  - **apparition en 0,2 s** : `Size` = {0 : 0,55 × 20,5 ; 0,2 : 20,5 ; 1 : 20,5}, et `Transparency` = {0 : 0,6 ; 0,15 : 0 ; 0,9 : 0 ; 1 : 1}.
- **Épaisseur** : ajouter 6 à 10 `fog_puff.png` (taille 6 à 10, rotation lente aléatoire, vie 0,8 à 1 s) autour du centre.

## 2. Éclair « Titan » (`titan_lightning.py`)

| Fichier | Format | Usage |
|---|---|---|
| `titan_lightning_flipbook.png` | 1024², 4×4 images de 256², environ 0,6 s | l'éclair quand on prend le power-up Titan |
| `titan_flash_ring.png` | 512² | onde de choc vue de dessus, posée sur l'eau |
| `titan_preview_*.png`, `titan_flash_ring_preview.png` | aperçus | contrôle |

- **Déroulé** :
  - images 0-1 : une amorce fine descend ;
  - images 2-3 : l'éclair épais frappe et l'image flashe en blanc-jaune ;
  - images 4-11 : les ramifications crépitent (redessinées toutes les 2 images) et de la **fumée noire** monte autour de l'impact, le contraste jaune et noir de la référence ;
  - images 12-15 : tout s'éteint.
- **Style** : cartoon, cohérent avec le splash. Contour brun foncé, bandes orange, jaune et blanc, halo.
- **Point d'impact** : (0,5 ; 0,86) de l'image. L'éclair entre par le haut. Avec un `ParticleEmitter` centré sur l'image, décaler l'émetteur vers le haut de 0,36 × la taille de l'image, pour que l'impact tombe sur le poisson.
- **Réglages** : `FlipbookMode = OneShot`, `FlipbookFramerate = 27`, `Lifetime = 0.6`, `Orientation = FacingCameraWorldUp`, `LightEmission = 1`.
- **Anneau** : une part plate (ou une Decal sur un disque) à la surface de l'eau. Faire passer la taille de 0 à 40 studs et `Transparency` de 0 à 1 en 0,3 s.

## 3. Lignes de vitesse du dash (`screen_fx.py`)

| Fichier | Format | Usage |
|---|---|---|
| `speed_line.png` | 256×32 | trait blanc fin aux bouts dégradés, plus brillant à droite (la tête). Pour des particules étirées (`Orientation = VelocityParallel`, `Squash` négatif pour allonger) ou un `Beam`. |
| `speed_lines_screen.png` | 1024² | overlay plein écran : traits radiaux vers le centre, **centre transparent** |
| `speed_lines_screen_b.png` | 1024² | une autre version : alterner les deux toutes les 0,05 s pour que les lignes scintillent |
| `speed_line_preview.png`, `speed_lines_screen_preview_*.png` | aperçus | contrôle |

Overlay : `ImageLabel` plein écran, `ImageTransparency` qui passe de 1 à environ 0,35 au début du dash, puis revient à 1 en 0,3 s.

## 4. Vignette rouge de quasi-mort (`screen_fx.py`)

- `low_hp_vignette.png` (1024²) : bords rouges, centre transparent, dégradé doux. La forme est un carré arrondi qui épouse les bords de l'écran, avec un bord légèrement irrégulier.
- Usage : `ImageLabel` plein écran, `ScaleType = Stretch`, visible quand les PV sont ≤ 10 %. Faire pulser `ImageTransparency` entre 0,15 et 0,6 à environ 1,6 Hz (`math.sin`, sans aléatoire).

## 5. Mur de zone, style tempête Fortnite (`zone_wall.py`, carte Océan)

| Fichier | Format | Usage |
|---|---|---|
| `zone_wall_flipbook.png` | 1024², 4×4 images de 256², boucle de 16 images, **chaque image se répète à l'horizontale** | mur animé |
| `zone_wall_static.png` | 512², se répète à l'horizontale | mode performance |
| `zone_wall_preview_*.png` | aperçus | contrôle |
| `zone_wall_tiling_check.png` | 3 copies côte à côte, pour voir qu'il n'y a pas de couture | contrôle |

- **Rendu** : voile bleu-violet de (120, 70, 255) à (80, 170, 255), bandes qui ondulent, stries qui montent, éclairs, **bord lumineux en bas** (la ligne d'eau, comme sur la référence).
- **Opacité** : plus opaque en bas, elle s'estompe vers le haut. Le bas de l'image correspond à la ligne d'eau.
- **Animation dans Roblox** : un objet `Texture` affiche toute l'image, il ne peut pas choisir une case de la planche. Il faut donc, par face du mur :
  1. créer un `SurfaceGui` avec un `ImageLabel` (Size 1,1, `ScaleType = Tile`, `ImageRectSize = (256, 256)`) ;
  2. régler `TileSize` pour qu'une tuile fasse environ la hauteur du mur ;
  3. avancer `ImageRectOffset` d'une case toutes les 1/12 s.
- **Mode performance** : `zone_wall_static.png` dans un objet `Texture`, avec `StudsPerTileU` et `StudsPerTileV` égaux à la hauteur du mur, et un léger défilement de `OffsetStudsU`.

---

# Brief 2 : textures des pêcheurs à harpon et à bazooka

Tout reste en PNG RGBA à **alpha droit**, en puissances de 2. Deux générateurs :
- **`aim_beam.py`** : volume Cycles, environ 25 min sur 4 CPU à 64 échantillons ;
- **`weapon_fx.py`** : dessin 2D numpy, quelques secondes.

```
blender -b --factory-startup --python fx/aim_beam.py -- <dossier> [échantillons=64]
blender -b --factory-startup --python fx/weapon_fx.py -- <dossier>
```

`make_gifs.py` produit aussi les aperçus animés `aim_beam_flipbook_*.gif` et `explosion_flipbook_*.gif`.

`luau/WeaponFx.luau` applique déjà les réglages ci-dessous. Clés `FxAssets` à remplir après téléversement :
- `AimBeamFlipbook`, `AimRing`, `MissileReticle` ;
- `ExplosionFlipbook`, `ShockwaveRing`, `SmokePuff` ;
- `MissileFlame`, `Bubble`, `ShardSpark`.

## 6. Colonne de visée du harpon (`aim_beam.py`)

| Fichier | Format | Usage |
|---|---|---|
| `aim_beam_flipbook.png` | 1024², **4×4** images de 256², boucle | bande verticale de brouillard rouge réaliste, même teinte que `fog_flipbook` |
| `aim_beam_preview_*.png`, `aim_beam_tiling_check.png`, `aim_beam_flipbook_*.gif` | aperçus | `tiling_check` empile trois fois la même image : aucune couture |

- **Tuilable verticalement**. Le haut de chaque image se raccorde à son bas : le bruit est périodique le long de la colonne, et la colonne est rendue sur trois hauteurs de tuile, puis recadrée.
  - **Mesure** : l'écart à la couture vaut 0,0184, contre 0,0181 entre deux lignes ordinaires.
- **Boucle sans raccord**. Le brouillard descend d'une tuile par boucle, tout en se transformant (mélange cos/sin de deux bruits).
  - **Mesure** : l'écart de l'image 15 à l'image 0 vaut 0,025, comme d'une image à la suivante (0,024).
- **Bords gauche et droit fondus** : alpha 0 au bord, 0,89 au centre. Le corps dense (alpha au moins égal à la moitié du maximum) couvre **83 % de la largeur**, ce qui rend la forme nette avec un bord seul brumeux.
- **Montage conseillé** (celui de `WeaponFx`) : 3 quads verticaux fins en étoile autour de l'axe, 2 en mode performance. Sur chaque face :
  - un `SurfaceGui` en `PixelsPerStud = 256 / diamètre` ;
  - des `ImageLabel` empilés, d'une tuile chacun (autant de studs de haut que la colonne a de diamètre), avec `ImageRectSize = (256, 256)`.
  - On avance `ImageRectOffset` d'une case **toutes les 1/10 s**, soit une tuile qui descend en 1,6 s.
  - Réglages : `LightInfluence = 0`, `ImageTransparency = 0,1`.
  - Chaque quad démarre la boucle sur une autre image, pour que les plans ne se répètent pas.
  - On évite `ScaleType.Tile` combiné à `ImageRectOffset` : rien ne garantit que la case de la planche soit répétée.

## 7. Explosion cartoon (`weapon_fx.py`)

| Fichier | Format | Usage |
|---|---|---|
| `explosion_flipbook.png` | 1024², 4×4 images de 256², **une seule passe** | flash blanc-jaune en étoile, boule de feu orange en bandes avec contour brun, fumée grise qui prend le dessus, monte et se défait en bouffées |
| `explosion_preview_*.png`, `explosion_flipbook_*.gif` | aperçus | |

- **Centre de l'explosion** : (0,5 ; 0,53) de l'image. Rien ne touche les bords (vérifié image par image).
- **Taille** : la boule de feu couvre **71 % de la largeur** d'une image à son maximum (image 4), et le dessin le plus large de la planche en couvre 83 %. Pour remplir un cercle de rayon `r`, `ParticleEmitter.Size` (une demi-largeur) vaut **1,41 × r**.
- **Réglages** :
  - `FlipbookLayout = Grid4x4`, `FlipbookMode = OneShot`, `Lifetime = 0.75` (environ 21 images/s) ;
  - `Orientation = FacingCamera`, `LightInfluence = 0`, `LightEmission = 0.15`, `Rotation` de ±12°.
- **Deuxième couche** (sauf en mode performance) : la même particule tournée de 180°, 12 % plus grande, transparence 0,35, émise 0,05 s plus tard.

## 8. Textures simples

| Fichier | Taille | Usage et réglages conseillés |
|---|---|---|
| `smoke_puff.png` | 256² | **Traînée du missile**, `ParticleEmitter` :<br>- `Rate` 45 (22 en mode performance), `Lifetime` de 0,7 à 1,1 ;<br>- `Size` de 0,7 à 3,2, `Transparency` 0,15 puis 0,5 puis 1 ;<br>- `RotSpeed` ±60, `Drag` 1,5, `Acceleration` (0, 2, 0), `LightInfluence` 0,5.<br>**Fumée après l'explosion**, hors de l'eau : 8 particules, taille de 0,18 r à 0,45 r. |
| `bubble.png` | 128² | Bulle claire à contour cyan, avec reflets.<br>**`BillboardGui`** (`Bubbles`) : 0,35 à 0,9 stud, jusqu'à 1,8 fois plus grosse en montant, `LightInfluence` 0.<br>**Ou `ParticleEmitter`** : `Size` de 0,2 à 0,45. |
| `shard_spark.png` | 128² | Étincelle blanche à 4 branches (désintégration, explosion). `LightEmission` 1, `Size` de 0,9 à 0, `Lifetime` de 0,25 à 0,4. |
| `aim_ring.png` | 512² | Cercle rouge net avec une lueur intérieure (zone du missile, bouts de la colonne du harpon).<br>Une part de 0,05 d'épaisseur, de 2 r × 2 r, avec sur ses faces Top et Bottom un `SurfaceGui` en **`FixedSize` 512 × 512**, `LightInfluence` 0.<br>`ImageTransparency` pulse entre 0,05 et 0,35. |
| `missile_reticle.png` | 512² | Viseur du bazooka. `BillboardGui` de 2,2 r studs, `LightInfluence` 0, qui clignote de plus en plus vite. |
| `shockwave_ring.png` | 512² | Onde de choc blanche et cyan. Part plate en `FixedSize` 512, qui grandit de 0,3 r à 2 r en 0,35 s, avec `ImageTransparency` de 0,05 à 1 en 0,4 s. |
| `missile_flame.png` | 256 × 64 | Flamme de tuyère pour un **`Beam`**. Le X de la texture suit le faisceau, la tuyère est à gauche, la queue est déjà fondue.<br>`TextureMode = Stretch`, `Attachment0` = tuyère, `Attachment1` 2,2 studs derrière.<br>`Width0` 0,75, `Width1` 0,25, `FaceCamera`, `LightEmission` 1, `LightInfluence` 0. `Width0` scintille de ±15 % à chaque image. |
| `weapon_fx_preview_water.png`, `weapon_fx_preview_sky.png` | 1792 × 256 | Les 7 textures simples sur l'eau et sur le ciel. |

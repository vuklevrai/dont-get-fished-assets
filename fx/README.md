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

# Brief pour la session cloud — « Don't Get Fished » (phase d'amélioration)

> **Comment l'utiliser.** Colle ce fichier entier comme premier message d'une session cloud (Opus, effort max) ouverte sur ton dépôt GitHub de travail. Joins aussi `NOTES_PROJET.md`. La session cloud **n'a pas accès à Roblox Studio** ni au PC : elle produit uniquement des **fichiers** (scripts Blender, données, textures PNG, scripts Luau). La session locale les intègre ensuite dans Studio.

---

## 0. Préparation (à faire par toi avant de lancer la session cloud)

1. Crée un dépôt GitHub privé, par exemple `dont-get-fished-assets`.
2. Mets-y ces fichiers, en les copiant depuis le dossier de la session locale :
   - `NOTES_PROJET.md` et ce fichier `CLOUD_BRIEF.md`
   - le dossier `spawn/`, au minimum `dgf_assets.py`, `build_blender.py` et `textures.py` : c'est le **format de référence** des assets
   - `splash/splash_flipbook.py` : la référence pour les planches d'images d'effets (style toon, contours)
   - `water/water_texture.py` et `water/cartoon_cells.osl` : la palette et le style de l'eau
   - `tools/export_fish_anims.py` : la méthode JSON → PNG
3. Exporte depuis Studio, avec un clic droit puis **Save to File…** au format `.rbxmx`, dans un dossier `studio_export/` du dépôt :
   - `StarterPlayer.StarterPlayerScripts` → `StarterPlayerScripts.rbxmx`
   - `ReplicatedStorage.FishGame` → `FishGame.rbxmx`
   - `ServerScriptService` → `ServerScriptService.rbxmx`
4. Tes images de référence ne sont pas arrivées jusqu'à moi : les liens `![[...]]` d'Obsidian ne transportent pas les fichiers. Si tu les as, mets-les dans `references/` :
   - `zone_fortnite.png` (la zone)
   - `fog.png` (le brouillard)
   - `titan_lightning.png` (l'éclair)
   - `aquarium.png`
   - `minecraft_hit.png`

   Sinon, la session cloud travaille d'après les descriptions ci-dessous.

---

## 1. Contexte technique (à lire par la session cloud)

- Jeu Roblox de pêche inversée : les joueurs sont des poissons. Tout est expliqué dans `NOTES_PROJET.md`.
- Style visuel : blocs avec studs, cartoon, couleurs vives et légers dégradés. **Seule exception : le brouillard de capture doit être réaliste.**
- **Pas d'import de mesh.** Toute géométrie doit être décrite comme une **liste de primitives Roblox** (Block, Wedge, Cylinder, Ball), au même format que `spawn/dgf_assets.py` (fonction `export_table`) :
  - `{"v":1,"assets":[...],"groups":[...],"shapes":["Block","Wedge","Cylinder","Ball"],"mats":[...],"prims":[[asset,group,shape,mat,collide,transparency,r,g,b,sx,sy,sz,px,py,pz,qx,qy,qz,qw],...]}`
  - unités en studs, Y vers le haut, coordonnées Roblox ;
  - matériaux autorisés : `Stud` (MaterialVariant studs), `Smooth`, `Glass`, `Neon`, `Wood`, `Metal`, `ForceField`.
- Livrer chaque table en **JSON** et aussi en **PNG de données** : 4 octets de longueur en big-endian, puis le JSON UTF-8 rangé dans les pixels RGB, largeur 512 (voir `tools/export_fish_anims.py`). Une seule image par asset, de 1024×1024 au maximum. Au-delà, découper en `_part1`, `_part2`…
- **Budget** : au maximum ~4 000 primitives par carte (décor compris) et ~600 par modèle. Fusionner les blocs voisins identiques.
- Blender peut s'installer dans le conteneur Linux : `pip install bpy` ou l'archive officielle Blender 4.x/5.x, lancée en mode `blender -b --factory-startup --python script.py -- args`. Les scripts doivent pouvoir aussi tourner sous Windows avec Blender 5.2, de façon déterministe (graine aléatoire fixe).
- Pour **chaque asset**, rendre une ou deux images d'aperçu (`*_preview.png`) qui permettent de valider le look sans Studio.
- Textures et planches d'images : PNG RGBA à alpha droit, en puissances de 2. Planches de 4×4 ou 8×8 images, ordonnées de gauche à droite puis de haut en bas.
- Palette de l'eau (sRGB) : cellules (78, 214, 251), lignes (135, 241, 255), ombre (70, 186, 246), écume (245, 253, 255), contour (40, 146, 226).
- Le code Luau doit suivre le style des scripts existants (`studio_export/`) : Luau strict-friendly, commentaires courts en anglais, `Config` pour toutes les constantes.

---

## 2. Tâches confiées au cloud

### C1 — Carte « Aquarium » (Blender → primitives)
- Même emprise au sol que la carte actuelle : environ 324 × 252 studs d'eau. Profondeur **~90 studs**, surface de l'eau à y = −1.
- Un grand bac en verre : 4 parois en `Glass` (transparence 0,6), un rebord épais en métal ou plastique coloré, et un socle ou meuble sous l'aquarium.
- Au fond :
  - du sable en blocs avec un léger dégradé ;
  - une vingtaine de touffes d'algues, livrées comme **points d'apparition** (groupe `SeaweedSpots`) : la session locale les génère et les anime ;
  - **un gros rocher au centre**, creux, avec au moins 3 tunnels et trous traversants où un poisson de taille 5 (environ 9 studs de long et 3,5 de haut) peut passer ;
  - **un mini château** ailleurs dans le bac : tours, porte et fenêtres traversables, intérieur creux.
- **Pods d'apparition futuristes pour les pêcheurs** : 10 plateformes en dehors du verre, à hauteur du rebord.
  - Style : disque métallique, anneau `Neon` cyan, petite rampe vers le bord, colonnes ou arceaux lumineux.
  - Fournir un modèle `FuturisticPod` réutilisable, livré à part (≤ 300 primitives), et 10 CFrames `FishermanSpots` qui regardent vers le centre (position = sol du pod).
- Les parois doivent avoir une épaisseur réelle (≥ 2 studs) pour servir aussi de collision.
- Livrables :
  - `maps/aquarium/aquarium.json` et `aquarium_data.png` ;
  - `maps/aquarium/spots.json` contenant `FishermanSpots`, `SeaweedSpots` et `PlayerSpawnVolume` (une boîte) ;
  - des aperçus en vue de dessus, de côté en coupe, et sous l'eau vers le rocher.

### C2 — Carte « Ballon » (bulle d'eau dans le vide)
- La boule d'eau elle-même est faite en local (Terrain:FillBall). Le cloud fournit seulement :
  - le placement de 10 `FuturisticPod` (le modèle de C1) autour d'une sphère de **rayon 110**, centrée en (0, 0, 0), sur des petites plateformes flottantes à 6–10 studs de la surface de la bulle ;
  - une liste `spots.json` au même format que C1.
- Pas d'autre décor. Aperçu : la sphère en bleu translucide avec les pods.

### C3 — Carte « Océan » + bateau de pêche + île
- **Bateau de pêche** (`FishingBoat`, ≤ 600 primitives), petit, environ 26 × 10 studs :
  - coque en bois ou peinte (blanc, bleu ou rouge), cabine avec vitres ;
  - mât et bras de pêche, bouée, filets, caisses, pneus sur les flancs ;
  - un point `FishermanStand` (CFrame) à l'arrière, là où le pêcheur se tient ;
  - collision sur la coque et le pont.
- **Mini île inaccessible** : un îlot de sable en blocs (~30 studs de diamètre) avec **un palmier tropical** en blocs (tronc courbé, palmes), placé loin derrière la zone de jeu.
- **Disposition** : la carte est une grande boîte d'eau de 1 200 × 1 200 studs au maximum, dont l'eau sera faite en local. Au centre, l'arène jouable est un **rectangle de 300 × 240 studs**, délimité par un mur de « zone ».
- Fournir 10 positions de bateaux juste à l'extérieur du rectangle (au maximum 15 studs du bord, cap tourné vers le centre), et la position de l'île.
- **Texture du mur de zone, style tempête de Fortnite** : un mur translucide bleu-violet (vers (120, 70, 255) → (80, 170, 255)) avec des bandes qui ondulent et un motif d'éclairs ou de distorsion.
  - Livrer une **planche de 4×4 images en boucle**, `zone_wall_flipbook.png` (1024², tileable horizontalement), plus `zone_wall_static.png`.
  - Ajouter un dégradé d'opacité vertical : plus opaque en bas, il s'estompe en haut.
- Livrables : `models/fishing_boat.json/.png`, `models/island.json/.png`, `maps/ocean/spots.json`, `fx/zone_wall_*.png`, et des aperçus.

### C4 — Effets en planches d'images (Blender)
1. **Brouillard de capture réaliste, rouge** (`fx/fog_flipbook.png`, 8×8 images à 128² ou 4×4 à 256²).
   - Fumée volumétrique : Mantaflow si c'est possible, sinon des volumes de bruit Cycles. Bord irrégulier et à peu près circulaire, vu en plongée de trois quarts.
   - Rouge sang à orange sombre : cœur (170, 20, 20), bords (255, 60, 40).
   - La boucle peut tourner en continu.
   - Ajouter `fog_puff.png` : une bouffée isolée, utilisée comme texture de particule pour l'épaisseur.
   - Ce sera rendu au-dessus de l'eau, sur environ 2,5 × 7 studs de rayon soit ~17,5 studs, et sur seulement 1 s de vie : le brouillard doit apparaître vite (grossir en 0,2 s) puis rester épais.
2. **Éclair « Titan »** (`fx/titan_lightning_flipbook.png`, 4×4 à 256², ~0,6 s).
   - Inspiré de la transformation dans L'Attaque des Titans : un éclair jaune-orangé épais qui tombe du ciel, un flash, puis des ramifications.
   - Style cartoon cohérent avec le jeu : contours, pas de photoréalisme.
   - Ajouter `titan_flash_ring.png` : un anneau d'onde de choc vu de dessus.
3. **Lignes de vitesse du dash** :
   - `fx/speed_line.png` : un trait blanc fin à bouts dégradés (256 × 32), pour des particules étirées ou un Beam ;
   - `fx/speed_lines_screen.png` : une overlay 1024² de traits radiaux vers le centre, centre transparent.
4. **Vignette rouge de quasi-mort** (`fx/low_hp_vignette.png`, 1024²) : bords rouges et centre transparent, avec un dégradé doux.

Pour chaque effet : un GIF ou une planche d'aperçu sur fond d'eau ((78, 214, 251)) et sur fond de ciel.

### C5 — Code Luau : nouveau système de nage (le plus important)
Partir de `studio_export/StarterPlayerScripts.rbxmx` (script `FishController`) et de `FishGame.rbxmx` (`Config`).

**Objectif** : que le poisson nage vraiment comme un poisson et non comme un avatar qui marche. C'est pour un jeu compétitif : la nage doit être fluide, précise et satisfaisante.

**Exigences :**
- **Inertie et glisse** : accélération progressive, vitesse qui se conserve dans les virages (pas d'arrêt net), traînée de l'eau. À l'arrêt, le poisson glisse encore 0,5 à 1 s.
- **Le corps suit la trajectoire** : virages en arc (rayon minimal qui dépend de la vitesse), roulis dans les virages, tangage qui suit la pente, petite ondulation latérale du corps à la nage. L'animation de queue est déjà gérée par `FishAnimator` ; tu peux exposer un attribut « intensité de nage » pour la piloter.
- **Poussées de nage** : impulsions de queue légères et rythmées, la vitesse oscille de ±5 %.
- **Vitesse de base +30 %** : `SWIM_SPEED` passe de 20 à 26. Ajuster de façon cohérente l'accélération, le dash (`DASH_SPEED`) et la vitesse de sortie du bond.
- **Bond** (`LEAP_HEIGHT` de 7 à ~10) : pendant le bond, **la caméra suit le poisson automatiquement** (suivi lissé de sa trajectoire). La souris n'a **aucun effet** pendant le bond, puis le contrôle revient en douceur au retour dans l'eau.
- **Caméra** : suivi doux (spring), légère avance dans la direction de la nage, FOV qui monte un peu avec la vitesse. Pas de saccade : **jamais de téléportation de caméra**. Toute secousse doit passer par un bruit lissé (Perlin ou ressort), jamais par des positions aléatoires image par image.
- **Trois modes de contrôle**, choisis par un attribut joueur `MoveMode` (réglé par le panneau admin) :
  - `"Classic"` : le nouveau système, ZQSD et WASD relatifs à la caméra ;
  - `"CameraOnly"` : le poisson s'oriente uniquement avec la caméra et **seule la touche W avance**. A, D et S n'ont aucun effet, pas de recul ;
  - `"ShiftLock"` : comme Classic, mais en vue « shift lock » (caméra décalée sur l'épaule, le poisson toujours orienté vers la visée).
- Garder **toute** l'interface existante : la capacité (Q ou clic droit), les remotes, `ClientState`, la sortie de l'eau et le flop sur la terre, le stun, la caméra de capture et l'option nage à reculons. La nouvelle façon de gérer le stun est décrite ci-dessous.
- **Ragdoll et recul** : à réception de `Knockback("Stun", impulse, duration)`, le poisson est projeté avec l'impulsion, **puis ralentit de façon exponentielle** (traînée de l'eau, environ 60 % de vitesse perdue par seconde) et tourne sur lui-même en ragdoll. Le contrôle revient progressivement à la fin. Le serveur, de son côté, calculera l'impulsion d'après le rapport des tailles, comme une masse.
- Livrables :
  - `luau/FishController.client.luau` : le remplacement complet ;
  - `luau/ConfigPatch.md` : les constantes à ajouter ou modifier, avec les valeurs ;
  - `luau/MOVEMENT_DESIGN.md` : l'explication des réglages et de comment les ajuster.

### C6 — Code Luau : mini-jeu d'échappement façon « skill check »
Partir de `CatchMinigame` (dans `StarterPlayerScripts.rbxmx`).
- **Look** :
  - un anneau circulaire épais et net, avec des segments plus fluides (ou un anneau en image) ;
  - une zone verte (et une petite zone « parfaite » plus claire, en option) ;
  - un pointeur stylé avec une traînée.
- **Mouvement** : le pointeur tourne avec une vitesse fluide.
- **Raté** : le pointeur **change de sens** à chaque erreur (horaire → antihoraire → horaire…), avec un petit tremblement fluide de 0,3 s. Le tremblement est une oscillation amortie, pas du hasard.
- **Réussite** : flash de couleurs vives (vert-jaune-cyan), l'anneau grossit puis rebondit (scale bounce), étincelles et texte « ESCAPED! » animé.
- **Raté (visuel)** : flash rouge sur l'anneau, petit recul de l'anneau, texte « -2 », **secousse caméra lissée**.
- Garder le protocole réseau existant : `Remotes.Caught` (données `pointerSpeed` et `greenArc`), `CatchResult:FireServer(bool)`, `Released`, ainsi que `ClientState.setUiOpen("Catch", …)`.
- Livrable : `luau/CatchMinigame.client.luau`, avec si possible un aperçu (une maquette PNG ou HTML de l'animation).

---

## 3. Rapport final attendu

`REPORT.md` à la racine du dépôt, qui contient :
- la liste de tous les fichiers produits, avec leur rôle ;
- pour chaque carte : les dimensions réelles, le nombre de primitives et les points d'ancrage ;
- les réglages clés du nouveau mouvement ;
- ce qui n'a pas pu être fait ou vérifié.

Tout doit être **commité sur une branche** `cloud-assets`, et une archive `deliverables.zip` doit être placée à la racine.

---

## 4. Ce que fait la session locale pendant ce temps (pour information)
Ces points ont besoin de Studio :
- barrières invisibles autour de l'eau et des bateaux ;
- calcul du recul côté serveur (impulsion selon la masse) ;
- hitbox des zones de capture ×2,5 et capture **1 s** après l'apparition du brouillard ;
- power-ups : sous la surface, ×3 plus gros, durée de vie 12 s, clignotement les 3 dernières secondes ; Speed à +100 % ; nouveau power-up rare **Titan** (+5 taille, +5 vitesse) ;
- barres de stats plus larges dans le menu ;
- onglet **Options** avec un mode performance ;
- **flash rouge** façon Minecraft sur le poisson touché ;
- **vignette** rouge quand il reste ≤ 10 % des PV ;
- distorsion d'écran pendant le dash ;
- options de mode de déplacement dans le panneau admin ;
- intégration des cartes (eau en terrain, bulle, océan, mur de zone) et rotation des cartes.

# Personnages voxel (Blender)

Trois personnages dans le style du poisson de base (`bonite_brainrot.glb`) :
- voxels de 0,1 ;
- tenons en damier sur le dessus et les flancs ;
- couleurs unies par zone, sans texture ;
- rig fait de nœuds nommés, sans squelette.

Tout est généré par du code Python qui pilote Blender 5.2 (`bpy`). Les mêmes fonctions d'animation produisent à la fois le `.blend`, le `.glb` et les données du jeu. Les trois ne peuvent donc pas diverger.

| | Poisson ennemi | Poisson préhistorique | Crocodile |
|---|---|---|---|
| Fichier | `piranha.py` | `hyneria.py` | `crocodile.py` |
| Modèle dans le jeu | `Piranha` (espèce `EnemyFish`, bots) | `Hyneria` (espèce `Hyneria`) | `Crocodile` (espèce `Crocodile`) |
| Longueur | 3,3 (6,6 studs) | 4,5 (9 studs) | 4,6 (9,3 studs) |
| Triangles (Blender, GLB) | 6 130 | 7 030 | 6 824 |
| Parts dans le jeu | 187 | 234 | 221 |
| Articulations (Motor6D) | 15 | 19 | 16 |
| Animations | `repos` 2,4 s, `nage` 0,8 s, `dash` 1 s | `repos` 3 s, `nage` 1 s, `arret_du_temps` 1,6 s, `rage` 0,5 s | `repos` 3 s, `nage` 1,2 s, `gueule_ouverte` 1 s, `croc` 1,5 s |

Pour comparer, la Bonite fait 5 836 triangles et 90 parts.

## Les personnages

**Poisson ennemi.** C'est un poisson classique au profil de piranha, entièrement en rouges : dos bordeaux, flancs rouges, ventre orangé. Tout est fait pour qu'il paraisse menaçant :
- mâchoire inférieure en avant, avec des crocs blancs visibles même bouche fermée sur une lèvre noire ;
- yeux jaunes à petite pupille dans une orbite noire ;
- gros sourcils froncés et cicatrice recousue sur l'œil droit ;
- dorsale de requin à bord noir et queue fourchue.

Ses animations :
- `repos` : il claque lentement des mâchoires et ses yeux scrutent autour de lui ;
- `nage` : ondulation, nageoires repliées ;
- `dash` : il se tord en C, gueule grande ouverte, se détend en fouet, claque des mâchoires et finit par deux claquements de dents.

**Poisson préhistorique.** C'est un sarcoptérygien du Dévonien, d'après ta peinture (un Hyneria) :
- tête large et plate couverte de plaques osseuses (sutures pâles, taches sombres) ;
- gueule large, à petites dents et lèvre inférieure pâle ;
- écailles bleu-vert en rangées décalées ;
- nageoires paires lobées (base charnue écaillée, éventail bordé de rouge et orange) ;
- deux dorsales à l'arrière et longue queue en fer de lance.

Ses animations :
- `repos` : la queue bouge à peine et les nageoires lobées pagaient en alternance, comme une marche ;
- `nage` : grande ondulation de la longue queue ;
- `arret_du_temps` : il se cambre et tremble (0 à 0,45 s), rugit, puis l'arrêt part à 0,5 s, il se détend vers l'avant et garde un sourire menaçant ;
- `rage` : nage rapide et nerveuse, sourcils froncés, gueule qui claque. Elle tourne en boucle tant que dure l'arrêt du temps.

**Crocodile.**
- Dos olive à rangées d'écailles en relief, queue à crête et bandes sombres, ventre crème.
- Long museau dont les dents du haut dépassent même gueule fermée. Une **dent en or** fait la touche brainrot.
- Yeux jaunes à pupille en fente sur le dessus du crâne, quatre pattes griffues.

Ses animations :
- `repos` : il flotte, ouvre lentement la gueule et pagaie des pattes ;
- `nage` : pattes repliées contre le corps, la queue fait tout le travail ;
- `gueule_ouverte` : se superpose à la nage pendant la capacité ;
- `croc` : la gueule s'ouvre en grand, il se jette en avant et claque des mâchoires, puis secoue la tête et fait une roulade de la mort complète.

## Ouvrir dans Blender

Chaque `<nom>/<nom>.blend` s'ouvre dans Blender 5.2. Il suffit d'appuyer sur Lecture : la timeline enchaîne toutes les animations, et des marqueurs les nomment.

Il y a une piste NLA par animation sur chaque nœud. Pour en isoler une, couper les autres pistes dans l'éditeur NLA. Une caméra et trois lumières sont en place : F12 rend directement.

Le `<nom>.glb` contient le même modèle et une animation glTF par clip, avec la même structure que la Bonite :
- nœuds `rig > centre > segments` ;
- un mesh par couleur et par segment ;
- matériaux PBR unis.

## Régénérer

```
python3 characters/build_characters.py [piranha] [hyneria] [crocodile]
```

Il faut le module Python `bpy` 5.2, ou bien Blender lui-même : `blender -b --factory-startup --python characters/build_characters.py -- piranha`.

Le script écrit :
- `characters/<nom>/<nom>.blend`, `<nom>.glb` et `build_report.json` ;
- `luau/FishData/<Modèle>.luau` et `luau/FishAnims/<Modèle>.luau`.

Il vérifie aussi chaque construction :
- que les boucles se referment ;
- que Blender rejoue exactement les fonctions d'animation ;
- que le GLB relu sans Blender redonne les mêmes poses, à 0,000001 près ;
- que les `Motor6D.Transform` rejoués comme dans le jeu (`Part1 = Part0 * C0 * Transform`) retombent sur le modèle à moins de 0,002 stud près.

Les aperçus se font en deux temps :
- `python3 characters/render_all.py` : vues fixes, silhouette, un GIF par animation ;
- `python3 characters/ability_previews.py` : les deux capacités avec leurs effets.

## Fichiers

- `voxlib.py` : le cœur.
  - Grille de voxels par segment et fusion des voxels en boîtes (pour le jeu).
  - Évaluation des poses, avec des quaternions écrits à la main.
  - Export de `FishData` et `FishAnims`.
  - Contrôle de cinématique directe façon Roblox.
- `blendlib.py` : le côté Blender.
  - Faces exposées fusionnées et tenons.
  - Nœuds, actions à slots et pistes NLA (API de Blender 5).
  - Export GLB et timeline.
- `parts.py` : yeux, sourcils, crocs, plaques de nageoires, profils.
- `glbcheck.py` : relit un GLB sans Blender et rejoue ses animations.
- `render.py`, `render_all.py`, `ability_previews.py` : les rendus Cycles.

## Importer le GLB directement dans Roblox (autre voie)

Le jeu n'en a pas besoin : `FishBuilder` construit les poissons en parts à partir de `FishData`. Si tu veux quand même un MeshPart :
- passer par **Avatar > Importer 3D**, ou par le Gestionnaire d'assets ;
- vérifier que les couleurs unies ressortent bien ;
- savoir que Roblox n'importe pas les animations de nœuds d'un glTF sans squelette.

Pour le jeu, la bonne voie reste donc `FishData` + `FishAnims`. L'import n'a pas été testé dans Studio.

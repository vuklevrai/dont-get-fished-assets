# Rapport : trois personnages (branche `characters`)

## Ce qui est livré

Trois personnages modélisés et animés dans Blender, dans le style du poisson de base : voxels, tenons en damier, couleurs unies, yeux cubiques et sourcils.

| | Poisson ennemi | Poisson préhistorique | Crocodile |
|---|---|---|---|
| Idée | Un poisson classique tout en rouges, taillé comme un piranha pour faire peur | Un prédateur du Dévonien d'après ta peinture (un Hyneria) | Le crocodile de ta photo, version brainrot avec une dent en or |
| Immobile | `repos` : claque lentement des mâchoires, regarde autour | `repos` : la queue bouge à peine, nageoires lobées qui pagaient | `repos` : flotte, ouvre lentement la gueule |
| Déplacement | `nage` | `nage` : la longue queue ondule | `nage` : pattes repliées, la queue fait tout |
| Capacité | `dash` : se tord en C, gueule ouverte, claque en fouettant | `arret_du_temps` (rugissement, l'arrêt part à 0,5 s), puis `rage` (nage rapide et énervée) | `gueule_ouverte` (pendant 3 s), puis `croc` (claquement, tête secouée, roulade de la mort) |

Pour chacun, il y a :
- un **`.blend`** : on appuie sur Lecture et toutes les animations défilent, avec des marqueurs ;
- un **`.glb`** avec les animations ;
- les **données du jeu** au format exact que `FishBuilder` et `FishAnimator` utilisent déjà.

Pour les capacités :
- **Effets spéciaux** :
  - module client `AbilityFx`, avec l'arrêt du temps inspiré de JoJo, la zone de ralentissement et le « CHOMP! » ;
  - 8 textures dans `fx/`.
- **Logique serveur** : module `AbilityService`.
  - Gel de 3 s dans un rayon de 36 studs. Les coups portés pendant l'arrêt sont mis en attente et partent tous à la reprise, comme dans JoJo.
  - Ralentissement de moitié dans 11 studs, puis morsure du premier poisson touché.
- **Animateur** : nouvel animateur, qui reste compatible avec la Bonite.

Aperçus :
- `characters/<nom>/previews/` : vues fixes, silhouette, un GIF par animation ;
- `characters/previews/timestop.gif` et `croc.gif` : les deux capacités avec leurs effets ;
- une visionneuse 3D en ligne : lien dans le message de livraison.

## Chiffres

| | Ennemi | Préhistorique | Crocodile | Bonite (référence) |
|---|---|---|---|---|
| Triangles (Blender/GLB) | 6 130 | 7 030 | 6 824 | 5 836 |
| Parts dans le jeu | 187 | 234 | 221 | 90 |
| Articulations | 15 | 19 | 16 | 9 |

Le plus lourd, ce sont **187 parts par bot ennemi**, soit environ 1 900 pour 10 bots. C'est jouable. Si ça rame, je peux en faire une version allégée sans crocs du haut ni taches.

## Vérifications faites

- **Boucles** : chaque animation en boucle revient exactement à sa première pose.
- **Blender** : il rejoue les animations sans aucun écart avec les fonctions qui les définissent.
- **GLB** : relu sans Blender, il redonne les mêmes poses (écart de 0,0000003).
- **Données du jeu** : rejouées comme le fait Roblox (`Part0 * C0 * Transform`), elles retombent sur le modèle Blender à moins de 0,002 stud près.
- **Luau** : le code passe mon vérificateur structurel (blocs, parenthèses, variables non déclarées).
- **Visionneuse** : testée dans Chromium.

## Choix que j'ai faits à ta place (à contester si besoin)

- **Mètres** : 10 m = 36 studs et 3 m = 11 studs, avec l'échelle officielle de Roblox (1 stud = 0,28 m). Si tu pensais « 1 mètre = 1 stud », ce sont deux constantes à changer.
- **« ZA WARUDO! »** s'affiche à l'écran au moment de l'arrêt du temps. C'est une seule ligne à vider si tu n'en veux pas.
- **Équilibrage** : ce sont des propositions de départ, à régler en jouant.
  - Recharges : 25 s pour l'arrêt du temps, 12 s pour le croc.
  - Morsure : 20 dégâts.
  - Stats : préhistorique 2/3/3, crocodile 2/4/3 (vitesse, santé, taille).
- **Bots** : les ennemis prennent le piranha rouge au lieu de la Bonite.

## Ce qui n'a pas pu être vérifié

Rien n'a tourné dans Roblox Studio : je n'y ai pas accès. Points à regarder en jeu :
- **Flash négatif** : il utilise `ColorCorrectionEffect.Contrast = -2`. Si Roblox borne cette valeur, il devient un voile gris. La solution est notée dans le guide.
- **Effets** : le rendu du matériau ForceField de la sphère et la lisibilité des statues grises.
- **Réglages de gameplay** : la portée de la morsure et la taille des hitbox.

## La suite, le plus simplement possible

1. Ouvre Claude Code sur ton ordinateur, là où tu as Roblox Studio.
2. Colle-lui ce message :
   > Récupère la branche `characters` du dépôt (`git fetch origin` puis `git checkout characters`). Lis `luau/CHARACTERS_INTEGRATION.md` et applique-le étape par étape, en me disant quoi tester dans Studio après chaque étape.
3. Teste ce qu'il te dit et reviens ici avec des captures d'écran ou les erreurs en rouge si quelque chose cloche.

## Fichiers

- `characters/` :
  - les générateurs (`piranha.py`, `hyneria.py`, `crocodile.py`) et leur bibliothèque (`voxlib.py`, `blendlib.py`, `parts.py`) ;
  - les rendus (`render.py`, `render_all.py`, `ability_previews.py`) et `glbcheck.py` ;
  - un dossier par personnage (`.blend`, `.glb`, `build_report.json`, `previews/`) ;
  - `README.md`.
- `luau/` :
  - `FishData/*.luau` et `FishAnims/*.luau` (générés) ;
  - `FishBuilder.luau`, `FishAnimator.client.luau`, `FishSpecies.luau`, `AbilityService.luau`, `AbilityFx.luau`, `FxAssets.luau` ;
  - **`CHARACTERS_INTEGRATION.md`** : le guide pour Studio.
- `fx/ability_fx.py` et les 8 textures : `timestop_clock`, `timestop_hand`, `menacing_go`, `anger_vein`, `bite_jaw`, `impact_star`, `slow_ring`, `slow_icon`.
- `deliverables_personnages.zip` : tout ça en une seule archive.

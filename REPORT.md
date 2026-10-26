# Rapport — brief cloud n° 2 (branche `cloud-assets-2`)

Les quatre tâches du brief sont faites et vérifiées hors de Studio :
- **C1** : décor de l'Océan ;
- **C2** : armes ;
- **C3** : textures ;
- **C4** : modules Luau.

Le travail part de `cloud-assets` et reprend ses outils sans les casser : `dgf_maps.py`, `build_maps.py`, `fxlib.py`, `make_gifs.py`. Le rapport du premier brief s'appelle maintenant `REPORT_BRIEF1.md`.

Les exports Studio du 26/10 sont dans `studio_export/` (fichiers `.rbxm` et scripts extraits dans `src/`). Ils ont servi à caler les modules sur le code actuel : `FxAssets`, `ClientState`, `MapService`, `Effects` et `ZoneWallAnimator`.

Le README de chaque dossier détaille tout :
- `maps/README.md` (section « Brief 2 ») ;
- `fx/README.md` (sections 6 à 8) ;
- `luau/README.md`.

---

## 1. Fichiers produits

### C1 — Décor de l'Océan (`maps/ocean_decor/`)

| Fichier | Rôle |
|---|---|
| `megalodon_fossil.json` / `_data.png` | Squelette de mégalodon, 459 primitives |
| `corals.json` / `_data.png` | Les 6 coraux en une seule table, assets `Coral1` à `Coral6` |
| `spots.json` | `FossilSpot`, 60 `CoralSpots` (`variant`, `scale`), 43 `SeaweedSpots` (`height`), plus `fossil_checks`, `stats` et `primitives` |
| `previews/*.png` | Fossile (2 vues), coraux, arène sous l'eau (2 vues), vue de dessus |

### C2 — Armes (`models/`)

| Fichier | Rôle |
|---|---|
| `harpoon_gun.json`, `harpoon.json`, `bazooka.json`, `missile.json` (et leurs `_data.png`) | Les 4 tables d'armes |
| `weapons_spots.json` | `Muzzle`, `RopeAttach`, `Exhaust`, etc., en coordonnées locales |
| `previews/harpoon_gun_preview.png`, `harpoon_preview.png`, `bazooka_preview.png`, `missile_preview.png`, `weapons_lineup_preview.png` | Aperçus ; la dernière vue montre les 4 armes à côté d'une silhouette R15 pour l'échelle |

### C3 — Textures (`fx/`)

| Fichier | Rôle |
|---|---|
| `aim_beam_flipbook.png` | Colonne de visée du harpon : planche 4×4, boucle, tuilable verticalement |
| `explosion_flipbook.png` | Explosion cartoon : planche 4×4, une seule passe |
| `smoke_puff.png`, `bubble.png`, `shard_spark.png` | Fumée, bulle, étincelle |
| `aim_ring.png`, `missile_reticle.png`, `shockwave_ring.png`, `missile_flame.png` | Cercle de danger, viseur, onde de choc, flamme de tuyère (textures en plus du brief, utilisées par `WeaponFx`) |
| `aim_beam.py`, `weapon_fx.py` | Générateurs. `make_gifs.py` gère aussi les deux nouvelles planches. |
| `*_preview_*.png`, `*_flipbook_*.gif`, `aim_beam_tiling_check.png`, `weapon_fx_preview_*.png` | Aperçus |

### C4 — Luau (`luau/`)

| Fichier | Rôle |
|---|---|
| `WeaponFx.luau` | Effets des pêcheurs à harpon et à bazooka |
| `Disintegrate.luau` | Élimination d'un poisson bloc par bloc |
| `Bubbles.luau` | Bulles d'ambiance et `burst` |
| `VoteUi.client.luau` | Vote du mode de jeu (LocalScript) |
| `WeaponModels.luau` | **Généré** : construit les 4 armes en Luau à partir des tables, sans import |
| `FxAssets.luau` | Remplace l'actuel : mêmes ids, plus 9 nouvelles clés |
| `README.md` | Contrats et exemples d'appel |
| `vote_ui_preview.html` et `vote_ui_preview*.png` | Maquette fidèle du vote, en 3 captures : vote en cours, Battle Royale verrouillée, résultat |

### Outils et autres fichiers

| Fichier | Rôle |
|---|---|
| `maps/dgf_props.py` | Géométrie du fossile, des coraux, des points d'ancrage, des armes, et contrôles de passage |
| `maps/build_maps.py` | Nouvelles cibles `ocean_decor` et `weapons` (export, aperçus, génération de `WeaponModels.luau`) |
| `CLOUD_BRIEF2.md`, `pour_github2/` | Le brief, `NOTES_PROJET.md` à jour et le prompt d'origine |
| `deliverables2.zip` | Tout ce qui est utile à la session locale (voir la fin du rapport) |

---

## 2. Modèles

| Modèle | Primitives (budget) | Origine | Orientation | Collision |
|---|---|---|---|---|
| `MegalodonFossil` | **459** (≤ 1 200) | centre du dessous, posé sur y = 0 | tête vers −Z ; à placer en `FossilSpot` (60, −46, −40) avec sa rotation | crâne, mâchoires et vertèbres uniquement (73 primitives) |
| `Coral1` à `Coral6` | 58 / 107 / 98 / 43 / 42 / 91 (de 40 à 120) | centre de la base, y = 0 | lacet aléatoire dans les points d'ancrage ; échelle de 0,8 à 1,6 avec `ScaleTo` | aucune |
| `HarpoonGun` | **58** (≤ 250), dont 26 pour le groupe `Harpoon` | la poignée (main droite) | canon vers −Z | aucune |
| `Harpoon` | **26** | la pointe | vol vers −Z ; `RopeAttach` en (0, 0, 7,38) | aucune |
| `Bazooka` | **40**, dont 13 pour le groupe `Missile` | la poignée | canon vers −Z | aucune |
| `Missile` | **13** | le nez | vol vers −Z ; `Exhaust` en (0, 0, 3,82), regard vers +Z | aucune |

**Fossile (vérification).** On peut **nager entre les côtes** : 3 passages latéraux de 11,45, 11,45 et 11,52 studs de diamètre libre (11 demandés).
- **Méthode** : la distance exacte, primitive par primitive, comme pour les tunnels de l'Aquarium.
- **Cage, dans la longueur** : au moins 11 studs sur 38 studs.
- **Dimensions** : 90 studs de long, 33 de haut. Gueule ouverte, double rangée de dents en `Wedge`, vertèbres séparées, côtes courbes, nageoires pectorales, dorsale et caudale osseuses, fissures et mousse.

**Points d'ancrage du décor.**
- **Coraux** : 60 points, dont 40 dans l'arène en 11 bosquets et 20 dehors jusqu'à ±500.
- **Algues** : 43 points (30 dedans, 13 dehors), `height` de 18 à 40.
- **Distance aux points d'apparition** : tout reste à **25 studs ou plus** de chaque `PlayerSpawnPoint`, sur toute sa hauteur (minimum mesuré 25,1).
- **Fossile** : le point d'apparition le plus proche est à 17 studs de l'os le plus proche.

---

## 3. Textures

| Texture | Taille et disposition | Réglages conseillés (ceux de `WeaponFx`) |
|---|---|---|
| `aim_beam_flipbook.png` | 1024², 4×4 de 256², boucle de 16 images ; **chaque image se raccorde en haut et en bas** ; bords gauche et droit fondus (alpha 0), alpha 0,89 au centre, corps dense sur 83 % de la largeur | 3 quads verticaux croisés (2 en mode performance), avec un `SurfaceGui` (`PixelsPerStud = 256 / diamètre`) sur chaque face.<br>Des `ImageLabel` empilés, une tuile par diamètre de hauteur, `ImageRectSize` 256.<br>Une case de plus **toutes les 1/10 s**, `LightInfluence` 0, `ImageTransparency` 0,1.<br>Mesures : écart à la couture 0,0184, contre 0,0181 entre deux lignes voisines ; image 15 → image 0 : 0,025, contre 0,024 entre deux images. |
| `explosion_flipbook.png` | 1024², 4×4, une seule passe ; centre en (0,5 ; 0,53) ; la boule de feu couvre 71 % de l'image ; rien ne touche les bords | `ParticleEmitter` en `Grid4x4` et `OneShot`, `Lifetime` 0,75.<br>**`Size` = 1,41 × rayon**, `FacingCamera`, `LightInfluence` 0, `LightEmission` 0,15.<br>Deuxième couche tournée de 180° (sauf en mode performance). |
| `smoke_puff.png` | 256² | Traînée : `Rate` 45 (22), `Lifetime` de 0,7 à 1,1, `Size` de 0,7 à 3,2, `Transparency` 0,15 puis 0,5 puis 1, `RotSpeed` ±60, `Drag` 1,5 |
| `bubble.png` | 128² | `BillboardGui` de 0,35 à 0,9 stud (jusqu'à 1,8 fois en montant), `LightInfluence` 0 |
| `shard_spark.png` | 128² | `LightEmission` 1, `Size` de 0,9 à 0, `Lifetime` de 0,25 à 0,4 |
| `aim_ring.png` | 512² | Part plate de 2 r × 2 r ; `SurfaceGui` en `FixedSize` 512 sur Top et Bottom ; `LightInfluence` 0 ; pulsation entre 0,05 et 0,35 |
| `missile_reticle.png` | 512² | `BillboardGui` de 2,2 r studs, `LightInfluence` 0 ; clignote d'une fois par 0,45 s à une fois par 0,06 s |
| `shockwave_ring.png` | 512² | Part plate en `FixedSize` 512, de 0,3 r à 2 r en 0,35 s, `ImageTransparency` de 0,05 à 1 |
| `missile_flame.png` | 256 × 64 | `Beam` en `Stretch` de la tuyère vers l'arrière (2,2 studs), `Width0` 0,75 → `Width1` 0,25, `FaceCamera`, `LightEmission` 1 |

Toutes les textures sont en RGBA à alpha droit, en puissances de 2, à graines fixes. Rouge de visée en brouillard réaliste ; tout le reste en style toon avec contours.

---

## 4. Modules Luau : contrats et dépendances

**Clés `FxAssets` ajoutées** (à remplir après téléversement) :
- `AimBeamFlipbook`, `AimRing`, `MissileReticle` ;
- `ExplosionFlipbook`, `ShockwaveRing`, `SmokePuff` ;
- `MissileFlame`, `Bubble`, `ShardSpark`.

Tant qu'une clé vaut `rbxassetid://0`, le module dessine une forme simple à la place. Tout se teste donc avant le téléversement.

### `WeaponFx.handle(kind, ...)`

Dépendances : `FxAssets`, `ClientState`, `Config` ; facultatives : `WeaponModels`, `Bubbles`.

| Type d'effet | Arguments | Retour |
|---|---|---|
| `HarpoonAim` | `origin`, `bottom`, `radius`, `duration` | `{ destroy() }` |
| `HarpoonFire` | `from`, `to`, `travelTime`, `key?` | **`{ rope: Beam, harpoon: Model, setTip(pos), destroy() }`** |
| `HarpoonTip` | `key`, `pos` | le handle. **En plus du contrat** : pilotage par remote, sans garder le handle. |
| `HarpoonEnd` | `key` | — (en plus du contrat) |
| `MissileAim` | `center`, `radius`, `duration` | `{ destroy() }` |
| `MissileFire` | `from`, `target`, `flightTime` | `{ missile, destroy() }` |
| `Explosion` | `center`, `radius` | — |

Détails :
- **Formes acceptées** : `handle` accepte aussi la forme habituelle du remote, `(kind, model, a, b, …)`.
- **`HarpoonAim`** : l'apparition prend 0,15 s.
- **`MissileFire`** : le nez arrive exactement à `flightTime`.
- **`Explosion`** : secousse de caméra par le bruit lisse de `ClientState`, sans saut ; voir `luau/README.md` pour la caméra non poisson.
- **Mode performance** : 2 fois moins de particules, sans deuxième couche.

### `Disintegrate.play(model, impulseDir?)`

Dépendances : `Config`, `FxAssets` (`ShardSpark`), `ClientState`.

- **Préparation** : clone local des blocs visibles (sauf le `Root`), original caché, joints et scripts retirés.
- **Cascade** sur 0,35 s, de la queue vers la tête ou depuis l'impact. Flash blanc, freinage dans l'eau et légère remontée, gravité hors de l'eau.
- **Fin** : 2 s éparpillés, puis rétrécissement et fondu en 0,3 s.
- **Limites** : 80 morceaux au maximum, regroupés au-delà. Ancré, mis à jour à chaque `RenderStepped`, sans collision, `CanQuery` et `CanTouch` désactivés.

### `Bubbles.start() -> stop`, `Bubbles.burst(pos, n)`

Dépendances : `Config`, `FxAssets` (`Bubble`), `ClientState`, et les attributs `Map*` de `FishGame`.

- **Grappes** de 3 à 12 bulles toutes les 1,5 à 4 s, à moins de 120 studs de la caméra.
- **Forme de l'eau** : `Plane` (avec le test d'arène de `MapService`) ou `Sphere` (de la sortie de la boule jusqu'en haut).
- **Fond** : raycast qui ignore le tag `Fish`.
- **Budget** : 60 bulles au maximum, 20 en mode performance.

### `VoteUi.client.luau`

Contrat du brief :
- **Attributs** : `VoteOpen`, `VoteEndsAt`, `VotesBattleRoyale`, `VotesSurvival`, `BattleRoyaleLocked`, `NextMode` ;
- **Remote** : `Remotes.Vote:FireServer("BattleRoyale" | "Survival")`.

Textes en anglais exactement comme demandé. Dépendance : `ClientState.setUiOpen`. Le remote est attendu avec `FindFirstChild` au moment du vote : il peut être créé plus tard.

### `WeaponModels.build(name, anchored?)`

Construit `HarpoonGun`, `Harpoon`, `Bazooka` ou `Missile`.
- **Racine** : une part `Root` invisible, à l'origine du modèle.
- **Points d'ancrage** : en `Attachment` sur `Root`.
- **Groupes** : chaque groupe est un `Model` enfant (`gun.Harpoon`, `bazooka.Missile`).
- **`anchored == false`** : les parts sont soudées à `Root`, prêtes à être soudées à une main.

Aucune dépendance.

---

## 5. Ordre d'intégration conseillé (session locale)

1. **Textures.** Téléverser les 9 PNG de `fx/` listés plus haut, puis remplacer `FishGame.FxAssets` par `luau/FxAssets.luau` en y mettant les ids. Facultatif : on peut aussi commencer sans, les formes de secours s'affichent.
2. **Modules.** Copier `WeaponModels`, `WeaponFx`, `Bubbles` et `Disintegrate` dans `ReplicatedStorage.FishGame`. Brancher les types d'effet d'armes dans le gestionnaire de `Remotes.Effect` (`Effects.client.luau`, extrait dans `luau/README.md`). **Test** : depuis le client, appeler `WeaponFx.handle` avec des positions de l'Océan.
3. **Pêcheurs à harpon et à bazooka**, côté serveur (logique du brief § 3).
   - Armes : `WeaponModels.build("HarpoonGun", false)` soudée à `RightHand`, au niveau de `RightGripAttachment`. Ajuster `C1` si le canon ne suit pas le bras.
   - Effets : `HarpoonAim` → `HarpoonFire` (avec `key` = id du pêcheur) → `HarpoonTip` à chaque cran de rétraction → `HarpoonEnd`. Puis `MissileAim` → `MissileFire` → `Explosion` à l'arrivée.
4. **Élimination.** Le serveur envoie l'effet de mort **avant** de détruire le poisson (environ 0,2 s, ou poisson caché puis détruit). Le client appelle `Disintegrate.play(model, direction)`.
5. **Bulles.** `Bubbles.start()` une fois, par exemple dans `PondAmbience`.
6. **Vote.** Mettre `VoteUi.client.luau` dans `StarterPlayerScripts`, puis écrire le serveur du vote : attributs et `Remotes.Vote`. Publier `NextMode` **avant** de passer `VoteOpen` à `false`.
7. **Décor de l'Océan.**
   - Importer `megalodon_fossil` et `corals` avec `AssetPackImporter`, comme les cartes du premier brief.
   - Placer le fossile en `FossilSpot` (repère de l'Océan : ajouter le décalage de la carte, y = −46 = le fond).
   - Cloner `Coral<variant>` à chaque `CoralSpot` avec `ScaleTo(scale)`.
   - Faire pousser les algues animées aux `SeaweedSpots` (`height`).
8. **Tests en jeu** : voir la section 6.

---

## 6. Ce qui n'a pas pu être fait ou vérifié

**Rien n'a tourné dans Roblox Studio** : cette session n'y a pas accès. Les modules sont relus à la main et passent un vérificateur Luau maison (blocs, parenthèses, variables non déclarées), qui n'est pas un vrai analyseur de types. Points à regarder en jeu :

- **Rendu.** Plusieurs choix ne se jugent qu'en jeu :
  - **Tube de la colonne** en matériau `ForceField` : rendu à juger dans Studio. Si besoin, passer à `Neon` avec transparence 0,8 (constante `AIM.shellTransparency` et matériau dans `harpoonAim`).
  - **Flamme du missile** : on suppose que l'axe X de la texture suit le `Beam` (de l'attachment 0 vers le 1). Si la flamme apparaît tournée de 90°, faire pivoter `missile_flame.png`.
  - **Bulles** : `BillboardGui` attachés à des `Attachment`, la méthode documentée.
  - **Colonne de visée** : la planche est vérifiée numériquement (couture et boucle), mais pas l'empilement dans le `SurfaceGui`.
- **Code.**
  - **Soudure des armes** à la main : `C0` et `C1` sont à ajuster à l'œil.
  - **`MapService`** : si les cartes sont toutes rapprochées au même endroit, il faut garder alignés le test d'arène de `Bubbles` (`MAP_MODELS`, `ArenaMin`/`ArenaMax`, `PondRadius`) et celui du serveur.
  - **Emoji de `VoteUi`** (🐟👑💀🔒) : ils dépendent de la police emoji de la plateforme, comme ceux des appâts déjà en jeu.
- **Décor.**
  - **Couleur du fond de l'Océan** : elle est inconnue d'ici. Les monticules de sable du fossile (groupe `Sand`) seront peut-être à recolorer ou à supprimer.
  - **Collisions du fossile** : tester qu'un poisson ne reste pas coincé dans la gueule ouverte. Les côtes et les dents ne collisionnent pas.
  - **Algues** : elles restent à générer en local. Les aperçus n'en montrent que des tiges provisoires.
- **Équilibrage** : la durée de vol du missile et la vitesse du harpon sont des paramètres d'appel, laissés au serveur local.

**`deliverables2.zip`** (à la racine) : `REPORT.md`, `luau/` (brief 2), `fx/` (textures, générateurs, aperçus), `maps/ocean_decor/`, les 4 armes de `models/` avec leurs aperçus, `maps/dgf_props.py` et `maps/build_maps.py`.

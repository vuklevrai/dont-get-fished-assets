# Nouveau système de nage — principes et réglages

Fichier : `luau/FishController.client.luau`. Les constantes sont dans `Config` (voir `ConfigPatch.md`). Les chiffres ci-dessous viennent d'une simulation du modèle à 60 images/s (le même calcul que le script). **Rien n'a pu être testé dans Studio** : ce sont des valeurs de départ à ajuster manette en main.

## 1. Pourquoi l'ancien poisson « marchait »

L'ancien contrôleur faisait `velocity:Lerp(cible, …)` sur le vecteur entier : la vitesse passait directement d'une direction à l'autre, en passant par zéro, comme un avatar. Le corps se tournait ensuite vers la vitesse. Résultat : demi-tours sur place, arrêts nets, aucune glisse.

## 2. Le modèle : un corps qui pousse vers l'avant

Le poisson a deux choses distinctes :
- **`travel`** : la direction de son corps ;
- **`vel`** : sa vitesse réelle.

À chaque image :
1. **Le corps tourne vers l'envie du joueur à vitesse limitée.** C'est ce plafond qui crée les **arcs**. Plus le poisson va vite, plus le plafond baisse (`SWIM_TURN_RATE / (1 + vitesse / SWIM_TURN_FALLOFF)`), donc **plus le virage est large**.
2. **La poussée se fait le long du corps** (`SWIM_ACCEL`). Sans touche, le poisson **glisse** : traînée exponentielle (`SWIM_GLIDE_DRAG`) plus un petit frein (`SWIM_GLIDE_BRAKE`) pour qu'il finisse par s'arrêter.
3. **La glissade de côté disparaît vite** (`SWIM_LATERAL_DRAG`), mais 85 % est **rendue en vitesse vers l'avant** (`SWIM_CARVE`) : la vitesse se conserve dans les virages, sans jamais pouvoir dépasser la vitesse d'avant ou la vitesse visée (un virage réoriente la vitesse, il n'en crée pas).
4. **Coups de queue** : la vitesse envoyée à la physique ondule de ±5 % (`SWIM_PULSE`) au rythme de la queue. La queue (`FishAnimator`) et l'ondulation du corps (`SWIM_UNDULATION`) suivent la même phase.
5. **Le corps** suit la pente (tangage limité à `MAX_PITCH`), s'incline dans les virages (`BANK`, `MAX_BANK`) et ondule légèrement.

| Mesure (Base fish, vitesse 26) | Valeur |
|---|---|
| 0 → 90 % de la vitesse de croisière | 0,47 s |
| Glisse après relâchement | sous 3 studs/s en 0,73 s, arrêt complet en 1,07 s, environ 9 studs parcourus |
| Virage de 90° | 0,30 s, vitesse conservée (26) |
| Demi-tour à 26 studs/s | environ 0,5 s, arc d'environ 8 studs de large |
| Demi-tour à 39 studs/s (stat Vitesse 5) | environ 0,58 s, arc d'environ 14 studs |
| Demi-tour à 52 studs/s (power-up Speed +100 %) | arc d'environ 20 studs |
| Dash (97 studs/s pendant 0,45 s) | environ 41 studs, puis retour à la croisière en environ 0,7 s |

## 3. Les trois modes (`Player:SetAttribute("MoveMode", …)`)

| Mode | Contrôles | Corps |
|---|---|---|
| `Classic` (défaut) | W/A/S/D relatifs à la caméra, Espace monte, Ctrl/C descend | Suit la nage : un S tout seul fait un demi-tour en arc. Option admin « S = nager à reculons » conservée. |
| `CameraOnly` | La caméra oriente, **seul W avance**. A, D, S, Espace et Ctrl n'ont aucun effet dans l'eau (Espace sert encore à sauter sur la terre). | W tenu : le poisson tourne vers la visée. W relâché : il glisse tout droit et la caméra est libre. |
| `ShiftLock` | Caméra décalée sur l'épaule droite (`SHIFTLOCK_OFFSET`), point de visée au centre. W/A/S/D nagent et font des pas de côté. Reculer va à 55 % de la vitesse, le pas de côté à environ 78 %. | Toujours tourné vers la visée (`SHIFTLOCK_TURN_RATE`) : pratique pour viser un dash. |

On peut changer de mode en pleine nage, sans à-coup : le décalage d'épaule est lissé.

## 4. Caméra

- **Suivi par ressort** (amorti critique, aucun dépassement) : la caméra vise le poisson plus un décalage qui tend vers une **légère avance** dans la direction de la nage (`CAMERA_LEAD`, plafonnée à `CAMERA_LEAD_MAX`).
- **Champ de vision** : il monte avec la vitesse, jusqu'à +12° au dash (`CAMERA_FOV_SPEED`).
- **Taille du poisson** : distance, hauteur, avance et décalage d'épaule sont multipliés par la taille du poisson. Un poisson de niveau 5 ou un Titan n'a plus la caméra dans le corps.
- **Obstacles** : la caméra se rapproche **immédiatement** si quelque chose bloque, puis repart en douceur.
- **Jamais de saut de caméra** :
  - les secousses passent par `math.noise` (bruit continu) dans `ClientState`, et leur force monte et descend en douceur ;
  - si le serveur téléporte le poisson (libération de l'hameçon, réapparition proche), le décalage absorbe le saut et la caméra **glisse** vers la nouvelle place ;
  - la vue de l'hameçon cadre le **point d'accroche** (fourni par `Remotes.Caught`) et pas le poisson qui se débat. La caméra y entre et en sort en fondu, au lieu d'une coupure.
- Les objets **sans collision** (algues, brouillard, appâts) et **les autres poissons** n'arrêtent plus la caméra (`RespectCanCollide` et un filtre sur le tag `Fish`).

## 5. Bond hors de l'eau

- Il se déclenche comme avant : nager vers le haut dans la surface, assez vite. Seulement sur le **dessus** de l'eau : sur la carte Ballon, uniquement sur la calotte supérieure de la sphère, là où la normale de la surface pointe vers le haut à plus de 0,85 (`LEAP_SURFACE_UP`). Sur cette calotte, un bond de 30 studs retombe toujours sur la bulle : on ne peut pas s'éjecter soi-même en sautant.
- Si la surface remonte à la rencontre du poisson après le sommet de l'arc (surface courbe), il replonge tout de suite au lieu de finir l'arc sous l'eau.
- Arc prédéfini : 10 de haut, 30 de long, 1,1 s. Le poisson est **recalé sur l'arc** à chaque image, donc une petite poussée ne le dévie pas.
- **Pendant le bond, la souris est ignorée** : la caméra suit seule la trajectoire, en lacet comme en tangage (`LEAP_CAMERA_*`). Au retour dans l'eau, la souris reprend la main progressivement en 0,35 s (`LEAP_CONTROL_RETURN`) pendant que le suivi automatique s'efface.
- Si l'arc touche un obstacle (bateau, pod, rebord), le poisson rebondit, tourne sur lui-même 0,5 s et retombe.
- En rentrant dans l'eau : il plonge avec 60 % de la vitesse de l'arc, puis il a le bonus de plongée (×1,7 sur 1,3 s, comme avant).

## 6. Recul et ragdoll

À réception de `Knockback("Stun", impulse, duration)` :
1. `vel = 25 % de la vitesse actuelle + impulse` ;
2. **traînée de l'eau** : linéaire (`STUN_DRAG` 0,92/s, soit environ 60 % perdus par seconde) plus une part quadratique (`STUN_DRAG_QUAD`) qui freine davantage les chocs violents au début ;
3. **culbute** autour d'un axe perpendiculaire à la poussée, légèrement de biais pour que le corps paraisse lâche. La vitesse de rotation est proportionnelle au choc et décroît (`STUN_SPIN*`) ;
4. contre un mur, le poisson **rebondit** (restitution 0,45), son sens de rotation s'inverse et l'écran tremble un peu ;
5. à la fin, **le contrôle revient en 0,5 s** (`STUN_RECOVER_TIME`) : poussée et rotation passent progressivement de 0 à 100 %, et le corps se redresse en douceur.

Si le choc sort le poisson de l'eau, la gravité prend le relais. C'est ce qui permet d'**éjecter un poisson de la carte Ballon** : en nage normale, on ne peut pas sortir de la bulle soi-même (la surface retient), mais un dash ou un recul peuvent en sortir.

| Impulsion envoyée (studs/s) | Vitesse après 1 s | Distance en 1 s | Distance totale |
|---|---|---|---|
| 12 | 4,6 | 8 | 12 |
| 35 | 12,8 | 22 | 34 |
| 45 (dash actuel) | 16,0 | 28 | 43 |
| 80 | 26,3 | 47 | 73 |
| 120 | 36,3 | 67 | 103 |

C'est le serveur qui choisit l'impulsion (rapport des masses : voir `ConfigPatch.md`, § 6b). Ce tableau sert à choisir les valeurs : l'arène fait environ 324 × 252 studs.

## 7. Comment régler (symptôme → paramètre)

| Ressenti | Paramètre | Sens |
|---|---|---|
| « Le poisson est lourd au démarrage » | `SWIM_ACCEL` | ↑ (6–7) |
| « Il glisse trop / pas assez » | `SWIM_GLIDE_DRAG`, `SWIM_GLIDE_BRAKE` | ↑ glisse moins / ↓ glisse plus |
| « Les virages sont trop larges » | `SWIM_TURN_RATE` ↑, ou `SWIM_TURN_FALLOFF` ↑ (le rayon grandit moins avec la vitesse) | |
| « Ça dérape dans les virages » | `SWIM_LATERAL_DRAG` | ↑ (18–20) |
| « Ça perd de la vitesse en tournant » | `SWIM_CARVE` | ↑ (max 1) |
| « On ne sent pas les coups de queue » | `SWIM_PULSE` (0,05 → 0,08), `SWIM_UNDULATION` | ↑ |
| « Le dash s'étire trop » | `SWIM_OVERSPEED_DRAG` | ↑ |
| « La caméra est molle / nerveuse » | `CAMERA_FOLLOW` | ↑ plus serrée / ↓ plus souple |
| « Pas assez d'effet de vitesse » | `CAMERA_FOV_SPEED`, `CAMERA_LEAD` | ↑ |
| « Le ragdoll dure / tourne trop » | `STUN_DRAG` ↑, `STUN_SPIN` ↓ | |
| « Le contrôle revient trop brutalement » | `STUN_RECOVER_TIME` | ↑ |

Règle simple : **changer un seul paramètre à la fois**, de 20 à 30 %, puis rejouer.

## 8. À vérifier dans Studio (personne ne l'a encore fait)

1. Nage normale : démarrage, glisse, demi-tour en arc, inclinaison dans les virages, ondulation de la queue en phase avec les poussées.
2. Les trois modes, et le passage de l'un à l'autre en pleine nage.
3. Bond : la caméra suit seule, la souris est ignorée puis revient en douceur, les deux splashs se déclenchent.
4. Dash : légère correction possible pendant le dash, étourdissement contre un mur avec rebond, vitesse qui retombe ensuite.
5. Recul : choc d'un gros poisson, culbute, rebond sur un mur, contrôle qui revient progressivement.
6. Hameçon : la caméra entre et sort en fondu, plus aucun saut, puis le mini-jeu C6.
7. Mur ou fond : le poisson glisse le long, sans coller.
8. Terre : sauts avec Espace (dans tous les modes).
9. Carte Ballon : régler `MapWaterShape = "Sphere"`, vérifier qu'on ne sort pas en nageant mais qu'un recul peut éjecter.

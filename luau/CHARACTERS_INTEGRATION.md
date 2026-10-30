# Personnages : poisson ennemi, poisson préhistorique, crocodile — intégration dans Studio

Ce guide est écrit pour la session Claude locale (celle qui a accès à Studio). On fait une étape à la fois et on teste avant de passer à la suivante.

## 0. Fichiers

| Fichier (dépôt) | Type | Où dans Studio |
|---|---|---|
| `luau/FishData/Piranha.luau`, `Hyneria.luau`, `Crocodile.luau` | ModuleScript (généré) | `ReplicatedStorage.FishGame.FishData.<nom>` |
| `luau/FishAnims/Piranha.luau`, `Hyneria.luau`, `Crocodile.luau` | ModuleScript (généré) | `ReplicatedStorage.FishGame.FishAnims.<nom>` |
| `luau/FishBuilder.luau` | ModuleScript | **remplace** `ReplicatedStorage.FishGame.FishBuilder` |
| `luau/FishAnimator.client.luau` | LocalScript | **remplace** `StarterPlayerScripts.FishAnimator` |
| `luau/FishSpecies.luau` | ModuleScript | **remplace** `ReplicatedStorage.FishGame.FishSpecies` |
| `luau/AbilityFx.luau` | ModuleScript | `ReplicatedStorage.FishGame.AbilityFx` |
| `luau/AbilityService.luau` | ModuleScript | `ServerScriptService.Services.AbilityService` |
| `luau/FxAssets.luau` | ModuleScript | **remplace** `ReplicatedStorage.FishGame.FxAssets` : 8 nouvelles clés à la fin |

Les fichiers à **remplacer** viennent de l'export du 26/10 (`studio_export/src`). Si la version dans Studio a changé depuis, il faut fusionner les deux au lieu d'écraser. `git diff` sur `studio_export/src/FishGame/FishBuilder.luau` montre exactement ce qui change.

Les `FishData` et `FishAnims` sont générés par `characters/build_characters.py` (Blender 5.2 en module Python). Il ne faut pas les retoucher à la main : on corrige le modèle dans `characters/<nom>.py`, puis on régénère.

## 1. Les modèles seuls (aucun changement de règles)

1. Copier les 6 modules `FishData` / `FishAnims`, puis `FishBuilder` et `FishAnimator`.
2. **Test** : dans la barre de commandes (mode Edit), construire chaque modèle et le poser devant la caméra.
   ```lua
   local FB = require(game.ReplicatedStorage.FishGame.FishBuilder)
   for i, m in {"Piranha", "Hyneria", "Crocodile"} do
       local f = FB.build(m, "Test" .. m)
       f:PivotTo(workspace.CurrentCamera.CFrame * CFrame.new((i - 2) * 14, 0, -25))
       f.PrimaryPart.Anchored = true
       f.Parent = workspace
   end
   ```
   Vérifier les couleurs, que les pièces sont bien jointives et que les crocs sont à leur place. La Bonite doit être inchangée : le nouveau `FishBuilder` garde ses valeurs par défaut quand `FishData` n'a pas d'entrée `root`.
3. Lancer **Play** et vérifier que la Bonite s'anime comme avant. Le nouvel animateur garde le comportement « attaque » sur `DashStart`.

## 2. Le poisson ennemi des bots

- `Config.luau`, dans le bloc des ennemis, ajouter :
  ```lua
  ENEMY_SPECIES = "EnemyFish", -- the bots' fish: the red piranha (FishSpecies.EnemyFish)
  ```
- `EnemyFishService.luau`, dans `spawnOne` :
  - chercher `FishService.create(Config.DEFAULT_SPECIES, {` ;
  - remplacer par `FishService.create(Config.ENEMY_SPECIES or Config.DEFAULT_SPECIES, {`.
- `FishSpecies` (nouvelle version) contient `EnemyFish` avec `Hidden = true`. Dans `MenuUi.client.luau`, il faut le cacher de la liste :
  - chercher
    ```lua
    for id in FishSpecies do
        table.insert(ids, id)
    end
    ```
  - remplacer par
    ```lua
    for id, species in FishSpecies do
        if not species.Hidden then
            table.insert(ids, id)
        end
    end
    ```
- (Facultatif) `LobbyService` : refuser `SelectFish` pour une espèce `Hidden`, pour qu'un client ne puisse pas la choisir par le remote.
- **Test** : partie test, puis « faire apparaître un ennemi » (panneau admin). Le piranha rouge doit apparaître, nager, puis dasher : il se courbe en C, ouvre grand la gueule, claque des mâchoires et revient.

## 3. Le ralentissement (pour le crocodile)

Dans `FishService.luau` :

1. Dans `create`, ajouter deux champs à la table `info`, juste après `speedBoostUntil = 0,` :
   ```lua
   slowUntil = 0,
   slowFactor = 1,
   ```
2. Dans `applyStats`, juste après le bloc `if info.speedBoostUntil > now() then ... end`, ajouter :
   ```lua
   if (info.slowUntil or 0) > now() then
       speed *= info.slowFactor or 1
   end
   ```
   Puis, avec les autres `SetAttribute`, ajouter :
   ```lua
   m:SetAttribute("SlowedUntil", info.slowUntil or 0)
   ```
3. Ajouter cette fonction, par exemple après `boostSpeed` :
   ```lua
   -- slowed down (crocodile): speed x factor until `seconds` from now; calling again refreshes it
   function FishService.slow(info: FishInfo, factor: number, seconds: number)
       local t = now()
       local was = (info.slowUntil or 0) > t
       info.slowUntil = math.max(info.slowUntil or 0, t + seconds)
       info.slowFactor = if was then math.min(info.slowFactor or 1, factor) else factor
       if was then
           return
       end
       FishService.applyStats(info)
       task.spawn(function()
           while FishService.fish[info.model] and info.slowUntil > now() do
               task.wait(info.slowUntil - now() + 0.03)
           end
           info.slowFactor = 1
           if FishService.fish[info.model] then
               FishService.applyStats(info)
           end
       end)
   end
   ```

## 4. Les capacités (serveur)

1. Copier `AbilityService` dans `ServerScriptService.Services`.
2. Dans `GameServer.server.luau`, juste après `require(Services.CombatService)`, ajouter :
   ```lua
   require(Services.AbilityService)
   ```
3. `CombatService.luau` : le dash reste à lui, le reste va à `AbilityService`, qui écoute aussi `Remotes.UseAbility`.
   - Chercher
     ```lua
     Remotes.UseAbility.OnServerEvent:Connect(function(player)
         local info = FishService.forPlayer(player)
         if info then
             CombatService.dash(info)
         end
     end)
     ```
   - Remplacer par
     ```lua
     Remotes.UseAbility.OnServerEvent:Connect(function(player)
         local info = FishService.forPlayer(player)
         local species = info and FishSpecies[info.species]
         -- the other abilities (time stop, croc) are AbilityService's
         if info and (not species or species.Ability.Id == "Dash") then
             CombatService.dash(info)
         end
     end)
     ```

## 5. Les capacités (client)

1. `FishController.client.luau`.
   - En haut, ajouter :
     ```lua
     local FishSpecies = require(FishGame:WaitForChild("FishSpecies"))
     ```
   - Dans `canAct()`, empêcher d'agir pendant que le temps est arrêté :
     - chercher `return root ~= nil and humanoid ~= nil and humanoid.Health > 0` ;
     - remplacer par `return root ~= nil and not root.Anchored and humanoid ~= nil and humanoid.Health > 0`.
   - Dans `useAbility()`, juste après le test `AbilityReadyAt`, ajouter :
     ```lua
     local species = FishSpecies[character:GetAttribute("Species")]
     if species and species.Ability.Id ~= "Dash" then
         -- time stop, croc: the server runs them, no local dash
         character:SetAttribute("AbilityReadyAt", serverNow() + (character:GetAttribute("AbilityCooldown") or 6))
         Remotes.UseAbility:FireServer(aimDirection())
         return
     end
     ```
2. `Effects.client.luau`.
   - En haut, ajouter :
     ```lua
     local AbilityFx = require(FishGame:WaitForChild("AbilityFx"))
     ```
   - Au tout début de `Remotes.Effect.OnClientEvent:Connect(function(kind, model, a, b)`, ajouter :
     ```lua
     if AbilityFx.kinds[kind] then
         AbilityFx.handle(kind, model, a)
         return
     end
     ```
3. Copier `AbilityFx` dans `ReplicatedStorage.FishGame`.
4. **Test du poisson préhistorique** : partie test, choisir « Prehistoric fish » dans le menu, faire apparaître 2 ou 3 ennemis à côté, puis appuyer sur Q.
   - **0 à 0,5 s** : des particules violettes convergent vers le poisson, qui se cambre et rugit.
   - **à 0,5 s** : une sphère violette s'étend à 36 studs avec un anneau doré, l'écran clignote en négatif, puis devient gris-violet. « ZA WARUDO! » s'affiche en haut de l'écran.
   - **pendant 3 s** :
     - les ennemis dans la sphère se figent et deviennent des statues grises ;
     - une horloge tourne d'un cran par seconde au-dessus du poisson ;
     - des « ゴ » flottent autour de lui, un symbole de colère 💢 bat au-dessus de sa tête, et il nage deux fois plus vite avec l'animation « rage ».
   - **Coups pendant l'arrêt** : toucher un ennemi figé fait apparaître une étoile d'impact figée. Toutes partent au moment où le temps reprend : dégâts et recul en même temps.
   - **À la fin** : la sphère se rétracte dans le poisson et les couleurs reviennent.
5. **Test du crocodile** : choisir « Crocodile », appuyer sur Q près d'un ennemi.
   - Pendant 3 s, la gueule reste grande ouverte. Un anneau vert tourne autour du crocodile, et les poissons à moins de 11 studs portent un escargot au-dessus d'eux et nagent à moitié vitesse.
   - Le premier poisson touché par le museau déclenche la morsure :
     - les mâchoires géantes se referment, avec « CHOMP! » et une étoile d'impact ;
     - le crocodile fait une roulade de la mort complète ;
     - la victime prend 20 dégâts (+5 par point de taille au-dessus de 2) et est étourdie 1,5 s.

## 6. Textures (facultatif au début)

Téléverser les 8 PNG de `fx/` listés dans `FxAssets` (`timestop_clock.png`, `timestop_hand.png`, `menacing_go.png`, `anger_vein.png`, `bite_jaw.png`, `impact_star.png`, `slow_ring.png`, `slow_icon.png`), puis remplacer les `rbxassetid://0`.

Sans elles, `AbilityFx` dessine des formes simples ou du texte : cercle doré pour l'horloge, « ゴ », « 💢 », « ▼▼▼ » pour les mâchoires, « 🐌 ». Tout est donc testable avant.

## Réglages

- **Distances** : `AbilityService.TIME_STOP.radius = 36` et `CROC.radius = 11`. Roblox compte 1 stud = 0,28 m, donc 10 m font 36 studs et 3 m font 11 studs. Si « mètre » voulait dire « stud » dans la demande, mettre 10 et 3.
- **Équilibrage** : `FishSpecies` (stats, recharges de 25 s et 12 s), `AbilityService.CROC` (dégâts, étourdissement, ralentissement) et `TIME_STOP.duration`. Ce sont des propositions de départ.
- **Aperçu du menu** : le crocodile et le poisson préhistorique sont plus longs que la Bonite (9 studs contre 6,4). S'ils débordent de l'aperçu de `MenuUi`, reculer `vpCamera` (aujourd'hui à 9,5 studs) ou diviser `previewBase` par la longueur du modèle.
- **Effets** : `AbilityFx.TS`.
  - `text = ""` coupe le « ZA WARUDO! ».
  - `invert` : le flash négatif utilise `ColorCorrectionEffect.Contrast = -2`. Si Studio borne ce réglage, le flash devient un simple voile gris. Dans ce cas, mettre `Contrast = -1` ou supprimer le flash.
  - `SOUNDS` : identifiants de sons facultatifs (arrêt, tic-tac, reprise, croc).

## Ce qui n'a pas pu être vérifié ici

Rien n'a tourné dans Roblox Studio. Le code passe un vérificateur structurel maison (blocs, parenthèses, variables non déclarées), qui n'est pas un vrai analyseur de types.

Les données, elles, sont vérifiées numériquement. Les animations rejouées comme le fait le jeu (`Part0 * C0 * Transform`) retombent sur le modèle Blender à moins de 0,002 stud près.

À juger en jeu :
- le rendu du matériau `ForceField` de la sphère ;
- la lisibilité des « statues » (`Highlight`) ;
- le flash négatif (voir ci-dessus) ;
- la portée de la morsure (`CROC.reach`) ;
- la taille des hitbox (`root.size` dans chaque `FishData`).


On est à un stade avancé du jeu maintenant, il reste à faire des ajouts de fonctionnalités et quelques changements. Tu vas pareil externaliser sur session cloud tout ce que tu peux et tu vas faire le reste après.

Voici un réequilibrage d'abord:

-La vitesse du poisson de base lorsqu'il évolue en stats évolue trop vite. Arrangeons ça : On garde la vitesse de base du poisson à 2, il est à base 100, maintenant à chaque niveau en plus ou en moins (niveau du poisson) il gagne ou perd 6% de vitesse. 
-Maintenant un power up de vitesse fait gagner -30% de vitesse de ce qu'il avait, c'est trop rapide pour que les joueurs suivent
-Quand je me fait hook par un pêcheur augmente les dégâts à -1 PV toutes les 0,25 secondes
-Le power up titan donne désormais 2x PV et quand ça s'enlève les PV reviennent tous à 100%
-Augmente un peu plus la vitesse d'orientation du poisson quand je tourne ma caméra d'environ 50%
-Le cooldown de dash du base fish est de 4 secondes désormais

Un nouvel ajout, une barre de vie apparente au dessus de chaque poissons et également des poissons bots

-Cette barre de vie est une barre très fine en largeur et petite qui apparait au dessous de l'indicateur de niveau
-Elle est rouge

Rework de la physique du jeu

-J'aimerais quand il y a une collision entre poissons qu'il y ait une collision style auto-tamponeuses
-Fais en sorte que quand il y a une collision si la différence de taille est grande (et donc par conséquent de poids) le poisson le plus petit sois éjecté plus loin

Rework des pêcheurs

-Fais en sorte que au bout de 30 secondes de jeu les hameçons suivent les joueurs qui sont à 3 mètres à la ronde, toujours seulement à la surface de l'eau
-Ils se déplacent à une vitesse modérée

Rework poisson dans le lobby

-Comme tu sais il y a une option dans l'inventaire qui permet de "show off" ses poissons, mais maintenant je souhaite qu'ils soient affichés en sac à dos à la place.

Rework apparition des maps

-Fais en sorte que à l'endroit ou il y a la map de base, lorsqu'on passe d'une manche à l'autre elle disparaisse pour laisser place à une autre map tirée au hasard au même endroit ou elle se trouvait

Rework déplacement du poisson

-Lorsqu'il se déplace dans l'eau il y a un mini déplacement qui va du haut vers le bas, comme si il sautillait, ce qui rend le mouvement pas très naturel, j'aimerais l'enlever complètement

Nouveau pêcheurs à harpon

-On va ajouter un nouveau type de pêcheurs, les pêcheurs à harpon
-Leur harpon vise les joueurs au hasard
-Quand ils visent, le petit brouillard rouge apparait mais cette fois sous forme de ligne de mire, en cylindre, et traverse du pêcheur jusqu'au sol. C'est une ligne qui indique la zone de danger et la hitbox. C'est le même fonctionnement que pour les pêcheurs classiques mais cette fois avec un cylindre. Le poisson qui se trouve dedans se fait attraper. Le cylindre doit être plutôt épais pour pas que ce soit trop facile de l'esquiver
-On va reprendre la même mécanique de capture que pour les pêcheurs classiques sauf que le harpon se retracte au fur et à mesure (sans sortir le poisson de l'eau, il se bloque à la surface)
-Il tire toutes les 15 secondes
-La hitbox est statique elle ne bouge pas

Nouveau pêcheur à missile

-On va ajouter un nouveau type de pêcheurs, les pêcheurs à lance missile bazooka
-Leur missile vise les joueurs au hasard
-Quand ils visent, le petit brouillard rouge apparait de nouveau en forme de cercle, comme les pêcheurs classiques. Le poisson qui se trouve dedans se fait attraper.
-Sauf que cette fois la mécanique c'est que le missile se dirige vers la hitbox et touche toute la zone en infligeant de lourds dégâts, -20PV et un gros ragdoll de 2 seconde ou le joueur est propulsé à 5 mètres de l'endroit ou il était
-Il tire toutes les 20 secondes
-La hitbox est statique elle ne bouge pas

Réequilibrage pêcheurs et poissons bots 

-Il y a 5 pêcheurs classiques qui apparaissent durant la partie, 4 pêcheurs à harpon et 1 pêcheur à bazooka à la fin.
-Toutes les 10 secondes un pêcheur apparait, au hasard avec seulement celui à bazooka à la fin

Nouveau mode de jeu

-Grosse addition, comme tu le sais on a déjà un mode de jeu c'est le mode battle royale, maintenant j'ai envie d'ajouter un mode survie
-En gros, les joueurs apparaissent et doivent survivre à une horde de pêcheurs et de poissons zombie qui apparaissent au fur et à mesure
-Ce mode de jeu sera le seul disponible dans le cas ou dans le serveur il y a moins de 3 joueurs, autrement dit il en faut au moins 3 pour lancer le battle royale
-Les pêcheurs apparaitront toujours au nombre de dix mais pour pimenter le jeu le taux d'attaques sera beaucoup plus élevé
-Il y a 3 manches, laisse moi les expliquer : la première manche est une manche simple avec 5 pêcheurs basiques et un poisson zombie qui apparait toutes les 5 secondes, la deuxième est une manche difficile avec tous les pêcheurs disponibles (les 10) et un poisson zombie toutes les 5 secondes toujours. Les deux premières manches durent 45 secondes chacunes. La dernière est une manche infinie, mais toutes les 5 secondes la vitesse augmente, toutes les 5 secondes le temps de recharge des pêcheurs diminue de 1 seconde, toutes les 5 secondes le taux d'apparition de poissons zombie augmente de +1, et toutes les 5 secondes le temps qu'il y a entre l'apparition d'une hitbox (quelconque, ça peut être n'importe quel pêcheur) et le moment ou le poisson se fait attraper diminue de 5%. Signifiant que ça devient vite le chaos
-Les poissons zombie n'ont pas la capacité de dash ils n'ont aucune abilité, ils ont tous les stats à 1 à part la taille qui est à 3 et la vitesse à 2. J'ajouterai le skin plus tard du poisson zombie donc pour l'instant utilise le skin de base
-La dernière manche est juste nommée "Survive.. If you can" 

Mécanique de vote

-Avant de commencer une manche les joueurs peuvent voter pour le mode de jeu qu'ils veulent, pas pour la map par contre.

Elimination

-Quand un poisson se fait éliminer (joueur ou bot) il y a une animation qui se joue ou il se fait désintégrer bloc par bloc (vu que le poisson est fait de blocs). Les blocs restent éparpillés pendant 2 secondes avant de disparaitre.

Power ups

-Les power ups doivent être réduits de 25% de leur taille car ils sont trop gros
-Désormais les power ups dès qu'ils apparaissent tombent jusqu'au fond de l'eau lentement, inspire toi de la physique d'un objet qui tombe dans l'eau dans la vraie vie
-On va ajouter un nouveau power up de force, quand un poisson le prend il gagne +25% de dégâts totaux (tout ce qu'il inflige comme dégâts)
-Voici les taux d'apparition de power ups désormais : Vitesse 25%, Force 25%, Niveau 20%, Invisible 20%, Titan 10%

Maps

-Il y a des maps qui ne vont pas, enlève déjà la map ballon et garde la dans la réserve du jeu mais je veux plus qu'elle apparaisse d'elle même.
-La map océan a besoin d'un rework. Quand je te parlais d'une zone fortnite je te parlais pas de ça, on va juste le remplacer par une zone bleuâtre simple et à demi transparente pour signifier la limite, je veux pas d'animation dessus.
-Sur la map océan rajoute des algues et des coraux avec en décor un squelette fossile grand d'un requin préhistorique.

Bulles

-Ajoute des bulles qui spawnent à des endroits random à certains moments et qui remontent à la surface. C'est un effet spéciaux pour rajouter du réalisme.







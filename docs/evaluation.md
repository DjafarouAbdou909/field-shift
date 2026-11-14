# Évaluation

## Évaluation de la sortie de recommander, phase 5

Établie le 14 novembre 2026. Il n'existe pas de vérité terrain sur la meilleure rotation, si bien que l'évaluation ne mesure pas une précision. Elle vérifie la conformité de chaque recommandation, confronte ses résultats aux connaissances agronomiques établies, mesure la dépendance de son classement aux choix incertains et écrit ses limites. Chaque nombre de ce document est affiché par `venv/bin/python -m moteur.evaluation`, qui évalue les recommandations que retourne `recommander()` pour Korhogo et Bouaké et pour les trois priorités, la rotation actuelle étant coton puis maïs.

### Conformité

Les six recommandations, deux villes et trois priorités, passent les huit contrôles. Leurs données sont réelles, `donnees_fictives` à faux. Elles comparent trois stratégies dont une seule rotation actuelle. Chaque élément de niveau `mesure` ou `calcule` cite sa source. Chaque indicateur porte une plage. Chaque stratégie a ses raisons et ses preuves. Un classement instable nomme le scénario qui le change. Enfin, le message du gabarit du bot passe le garde-fou.

### Vérifications de bon sens

| Vérification | Korhogo | Bouaké | Portée |
|---|---|---|---|
| Une rotation avec légumineuse a un meilleur score d'apport d'azote qu'une rotation sans | vrai, 1,67 et 2,5 contre 0 | vrai, mêmes valeurs | Vrai par construction du critère, ce n'est pas une vérification indépendante |
| Sorgho puis niébé a un score d'eau au moins égal à coton puis maïs | vrai, 4,65 contre 4,05 | vrai, 4,35 contre 2,97 | Les deux rotations diffèrent par le coton autant que par le maïs |
| Le sorgho demande moins d'eau que le maïs sur son cycle | vrai, 453 contre 482 mm | vrai, 390 contre 415 mm | Besoin FAO-56 en conditions standard |
| La pluie couvre le besoin du sorgho au moins aussi souvent que celui du maïs | vrai, 1,00 contre 0,96 | vrai, 0,96 contre 0,88 | Dépend de la durée du cycle et de la date de semis |
| Le mil demande moins d'eau que le maïs sur son cycle | vrai, 378 contre 482 mm | vrai, 323 contre 415 mm | Besoin FAO-56 en conditions standard |
| La pluie couvre le besoin du mil au moins aussi souvent que celui du maïs | **faux**, 0,92 contre 0,96 | vrai, 0,92 contre 0,88 | Dépend de la durée du cycle et de la date de semis |
| FAO-56 attribue au maïs une plus forte sensibilité du rendement au manque d'eau qu'au sorgho | vrai, facteur Ky 1,25 contre 0,9 | vrai | Connaissance sourcée, tableau 24, qui n'entre pas dans les scores |

L'échec du mil à Korhogo n'est pas une erreur de calcul. Son cycle de 105 jours, semé au début des pluies, couvre surtout le début de saison, moins arrosé que celui du maïs de 125 jours. Il montre que le critère eau mesure la couverture du besoin par la pluie et les séquences sèches de mi-saison, et non la tolérance d'une culture au manque d'eau, que FAO-56 exprime par le facteur Ky. La meilleure tolérance du sorgho et du mil, que CLAUDE.md demande de vérifier, n'est donc pas représentée dans les scores, ce que les limites écrivent.

### Korhogo et Bouaké

Avec la référence, les deux villes reçoivent le même classement pour les trois priorités, sorgho puis niébé premier pour l'eau et l'azote, coton puis maïs premier pour le débouché. Les scores d'eau diffèrent pourtant nettement, de 4,05 à 4,65 à Korhogo et de 2,97 à 4,35 à Bouaké, Bouaké étant plus exposée au manque d'eau. L'écart suit donc les données en valeur mais non en classement. Pour le débouché et l'azote, l'identité est attendue, ces critères ne dépendant pas du lieu. Pour l'eau, l'ordre des stratégies est le même dans les deux villes, mais celui de Korhogo est fragile, comme le montre la section suivante.

### Sensibilité du classement publié

Les classements sont recalculés par la fonction qui construit chaque recommandation.

- **Pluie réduite de 20 % et début des pluies retardé de 14 jours.** Le classement ne change dans aucune ville ni pour aucune priorité.
- **Date de semis du coton.** À Bouaké, le classement ne change pour aucune date. À Korhogo, pour l'eau, coton, niébé puis maïs passe premier si le coton est semé au début des pluies ou au début de la fenêtre du CNRA, le 1er juin. Au début de fenêtre, coton puis maïs et sorgho puis niébé sont à égalité de note, et le classement publié les ordonne dans l'ordre de déclaration des stratégies.
- **Durée du cycle du coton.** À Korhogo, pour l'eau, coton, niébé puis maïs passe premier avec 180 jours et avec l'hypothèse de 150 jours. À Bouaké, il ne passe premier qu'avec 150 jours.
- **Débouché et azote.** Ces classements ne changent dans aucune variante, puisque leurs critères ne dépendent pas des données.

### Critères de réussite du cadrage

| Critère | État |
|---|---|
| 1. Au moins trois stratégies par ville, dont la rotation actuelle, éléments classés et sourcés | Atteint, contrôlé pour les six recommandations |
| 2. Chaque chiffre reproductible par une commande, avec sa plage et sa source | Atteint pour IMERG et POWER, reproductions vérifiées par réexécution. Les données de surface attendent AppEEARS |
| 3. Bon sens, dont un écart entre villes qui suit les données ou dont l'absence est expliquée | Partiellement atteint. Le mil échoue sur la couverture à Korhogo, la tolérance à la sécheresse n'est pas représentée, l'absence d'écart de classement entre villes est expliquée |
| 4. Le scénario qui change le classement est nommé | Atteint, dans l'avertissement et les lacunes de chaque recommandation |
| 5. Parcours WhatsApp complet sur données réelles, sous le garde-fou | Non atteint. Le dialogue du bot n'est pas écrit. Les messages de chaque étape et le garde-fou étendu à l'alerte et au diagnostic sont écrits sur la branche bot-langage, où le gabarit ne prête plus de cause au classement instable |
| 6. Relecture par un agronome ou un conseiller ANADER | Non atteint, aucune relecture à ce jour |
| 7. Chaque règle de calcul explicable par chaque membre | À vérifier par l'équipe, les règles étant écrites en tête de chaque module |

### Ce que la comparaison permet d'affirmer

- Dans la référence, Bouaké est plus exposée que Korhogo au manque d'eau, selon la pluie IMERG et le besoin FAO-56, chacune des trois stratégies y ayant un score d'eau plus bas.
- À Bouaké, coton puis maïs reste dernière pour la priorité eau dans tous les scénarios, à toutes les dates de semis du coton et pour toutes les durées de cycle testées.
- Le sorgho et le mil demandent moins d'eau que le maïs sur leur cycle dans les deux villes.

### Ce qu'elle ne permet pas d'affirmer

- Qu'une stratégie donnera un meilleur rendement ou un meilleur revenu. Aucun rendement n'est prédit et aucun prix n'est sourcé.
- Quelle stratégie économise le mieux l'eau à Korhogo, le classement y dépendant de la date de semis et de la durée du cycle du coton.
- Que les bénéfices d'azote et de débouché valent dans le Poro, leurs sources étant tirées du Nigeria et du Burkina Faso.

### Limites

- **Pas de vérité terrain** sur la meilleure rotation, ni de relecture par un agronome.
- **Critères d'azote et de débouché.** Ils ne dépendent pas du lieu. Le débouché pénalise mécaniquement toute rotation qui réduit le coton, et ne mesure pas un revenu.
- **Tolérance à la sécheresse non représentée.** Le facteur Ky de FAO-56 n'entre pas dans les scores.
- **Conditions standard de FAO-56.** Durées et coefficients culturaux généraux, sans stress, sans variété locale ni ajustement climatique. Le riz pluvial n'est pas distingué du riz irrigué.
- **Durée du cycle du coton** non propre aux variétés ivoiriennes, dont dépend le classement pour l'eau.
- **Date de semis.** Le coton suit la fenêtre observée par le CNRA, les autres cultures sont semées au début des pluies par hypothèse, et le classement de Korhogo pour l'eau dépend de la date de semis du coton.
- **Pluie totale et non pluie utile**, sans ruissellement ni bilan hydrique du sol.
- **Début de saison.** Règle attribuée à Sivakumar par des sources secondaires, recherche à partir du 1er mars qui tronque Bouaké près d'une année sur deux, seule la première saison de Bouaké étant traitée.
- **Pluie IMERG.** Case de chaque ville anormalement humide depuis 2013, d'où la moyenne de neuf cases, et désaccord avec PRECTOTCORR. Les pluviomètres GHCN sont trop lacunaires pour trancher le cumul annuel.
- **Données de surface absentes.** SMAP, MODIS et SRTM attendent les extractions AppEEARS.
- **Égalités de note.** Le classement publié ordonne deux stratégies à égalité dans l'ordre de leur déclaration.
- **Igname, mucuna et arachide** hors de la comparaison, faute de durée, de coefficient ou de bénéfice sourcés.

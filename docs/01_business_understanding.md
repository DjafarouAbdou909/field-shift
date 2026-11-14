# Compréhension du métier

## Problème

Dans le nord et le centre de la Côte d'Ivoire, l'agriculteur choisit chaque saison ce qu'il sème, sans lecture simple de ce que sa zone a connu en pluie et en début de saison, ni comparaison argumentée entre sa rotation et d'autres. Que la rotation coton puis maïs soit la plus courante autour de Korhogo est une hypothèse à faire confirmer par un conseiller de l'ANADER.

## Utilisateurs

- **L'agriculteur**, souvent dans une zone sans connexion, qui utilise un smartphone.
- **Son conseiller de l'ANADER**, qui discute avec lui des options.
- **Le jury du défi**, qui juge l'usage des données de la NASA.

## Réponse proposée

Une application de conversation qui fonctionne entièrement hors connexion. Le moteur calcule à l'avance, avec une connexion, toutes les recommandations pour chaque lieu et chaque priorité, à partir des données NASA POWER et GPM IMERG et des valeurs de FAO 56. Sur le téléphone, le GPS situe le champ sans réseau, et la conversation se déroule localement, sans modèle de langage ni appel réseau.

## Décisions éclairées

1. Garder la rotation actuelle ou en discuter une autre.
2. Introduire une légumineuse ou remplacer le maïs par le sorgho.
3. Voir comment le classement change selon la priorité, l'eau, le sol ou le débouché, et s'il résiste à une saison plus sèche ou plus tardive.

L'outil ne tranche aucune de ces décisions.

## Critères de réussite

- Au moins trois rotations comparées pour chaque lieu, dont la rotation actuelle.
- Chaque chiffre affiché provient du moteur, avec son niveau mesuré, calculé ou hypothèse, et sa source.
- L'application fonctionne en mode avion après une première ouverture avec connexion.
- Le classement indique s'il change avec une pluie réduite de 20 % ou un début des pluies retardé de 14 jours.
- Chaque membre de l'équipe sait expliquer chaque règle de calcul.

## Ce que l'outil ne fait pas

- Il ne prédit pas de rendement et ne désigne pas une meilleure rotation prouvée.
- Il ne donne ni dose d'engrais, ni date de semis, ni traitement.
- Il ne fournit pas de météo en direct, seulement le climat de 2001 à 2024.
- Il ne couvre que Korhogo et Bouaké, dans un rayon de 60 km.

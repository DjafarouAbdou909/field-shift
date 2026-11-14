# Journal des décisions

Une entrée par étape, la plus récente en bas. Chaque entrée indique la date et l'heure, le rôle, la décision et sa raison.

## Heure 0, toute l'équipe

- **Un moteur et deux interfaces.** Le moteur est appelé dans le même processus par le bot et par l'application, ce qui laisse un seul service à déployer.
- **Contrat version 1.** Défini dans moteur/contrat.py, avec un exemple fictif pour développer les interfaces en parallèle.
- **Pluie IMERG.** La pluie PRECTOTCORR de NASA POWER présente une rupture en 2020, constatée dans le projet African Crop Yield Intelligence, et n'est pas utilisée.
- **Gabarits par défaut.** Le bot envoie des messages déterministes. Un modèle de langage n'intervient que pour les questions libres, sous le contrôle du garde-fou.
- **Limite connue du garde-fou.** Il vérifie qu'un nombre figure dans la recommandation, pas qu'il est attaché à la bonne grandeur. Le renforcement par couples nombre et unité est à faire.

## 14 novembre 2026, 00 h 40, responsable de l'équipe, relecture avant le premier commit

- **Comparaisons de secrets en octets.** `hmac.compare_digest` lève une erreur sur une chaîne non ASCII, si bien qu'un en-tête de signature ou un jeton de vérification contenant un « é » provoquait une erreur 500 au lieu d'un refus 403. La comparaison se fait désormais en octets, et deux tests couvrent ce cas.
- **Dossier data à créer.** Il n'est pas versionné, et le bot ne peut pas ouvrir sa base SQLite s'il manque. La création est ajoutée aux instructions d'installation.
- **Documents alignés sur le code.** Le README ne prétend plus que tous les modules lèvent `NotImplementedError`, l'application ne prétend plus lire les paramètres d'URL, `bot/config.py` est attribué au membre A et les livrables CRISP-DM au rôle données et moteur.
- **Sources des leçons antérieures.** La rupture de `PRECTOTCORR` et la part du climat de 0,9 % à 6,3 % renvoient désormais au fichier précis de African Crop Yield Intelligence qui les établit.
- **Points ouverts soumis au responsable.** Le projet antérieur a aussi écarté `GWETROOT` pour la même rupture de 2020, alors que ce dépôt le retient. Le contrat ne porte ni la tendance des indicateurs, ni la plage des scores, ni les scénarios qui changent le classement, que la section 5 de CLAUDE.md et la règle 4 demandent.

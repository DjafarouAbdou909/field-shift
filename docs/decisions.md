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

## 14 novembre 2026, rôle données et moteur, phase 1 de CRISP-DM

- **Cadrage rédigé dans docs/cadrage.md, en attente de validation.** Problème, utilisateurs, quatre décisions éclairées, sept critères de réussite proposés, données envisagées et six exclusions.
- **Une seule source agronomique lue en entier.** Zagbaï, Berti et Lebailly, 2006, sur la région de Korhogo, relue page par page. Les autres articles repérés n'ont pas pu être ouverts, leurs serveurs refusant la lecture automatique, et rien n'en est tiré.
- **Hypothèses déclarées.** La rotation coton puis maïs comme rotation la plus courante, le retard du début des pluies, l'usage de WhatsApp et la lecture du français restent à confirmer. Le retard des pluies sera testé sur les données en phase 2.
- **Anomalie dans la source.** L'article situe la région de Korhogo entre 4 et 7 degrés de longitude Est, alors qu'elle est à l'ouest du méridien de Greenwich. Cette donnée n'est pas reprise.
- **Revenu sans source de prix.** Faute de prix aux producteurs sourcés, le critère revenu resterait qualitatif.

## 14 novembre 2026, responsable de l'équipe, validation du cadrage

- **Cadrage validé.** Le critère 3 ne fixe plus le résultat d'avance. L'écart entre Korhogo et Bouaké doit suivre ce que montrent les données, ou son absence doit être expliquée.
- **Exclusions validées.** L'outil montre la date habituelle de début des pluies mais ne conseille aucune date de semis, ne donne ni dose d'engrais ni traitement phytosanitaire, et cite les langues locales comme perspective.
- **GWETROOT écarté.** Il présente la même rupture de 2020 que `PRECTOTCORR`, constatée dans le projet antérieur. L'humidité du sol vient de SMAP seul.
- **Revenu qualitatif.** Il ne sera chiffré que si chaque culture comparée a une source de prix vérifiable, un prix pour le coton seul faussant la comparaison.
- **Énoncé du défi non lu.** Son site présente un certificat TLS que ni curl ni l'outil de lecture ne valident. La vérification n'a pas été contournée, le lien est cité comme non lu.
- **Travail antérieur en suspens.** L'heure officielle du début du hackathon n'a pas été communiquée. Tant qu'elle manque, on ne peut pas dire si le squelette créé le 14 novembre 2026 lui est antérieur, et `docs/travail_anterieur.md` reste inchangé.

## 14 novembre 2026, rôle données et moteur, phase 2 de CRISP-DM

- **Compréhension des données rédigée dans docs/donnees.md.** Chaque nombre est affiché par `venv/bin/python -m moteur.controles`, et deux exécutions ont donné des sorties identiques.
- **Séries téléchargées et consignées.** POWER et IMERG de 2001 à 2025 pour Korhogo et Bouaké, avec les huit cases IMERG voisines de chaque ville, et les pluviomètres GHCN-Daily des deux villes. Toutes les séries satellitaires sont complètes et respectent les bornes physiques.
- **IMERG confirmé à 0,1 degré**, par des points appariés. L'en-tête CSV de POWER l'étiquette à tort comme MERRA-2, ses métadonnées officielles le définissent comme IMERG.
- **Pluie comparée entre trois sources.** IMERG et `PRECTOTCORR` divergent au point de désigner une ville différente comme la plus arrosée. Le pluviomètre suit mieux IMERG au jour le jour à Korhogo et à Bouaké, ce qui conforte le choix d'IMERG.
- **Anomalie signalée.** Depuis 2013, la case IMERG de chaque ville est presque toujours la plus arrosée de son voisinage, sans cause établie. Il est proposé de prendre la moyenne des neuf cases en phase 3.
- **Rupture de 2020 non visible localement.** Le rapport de `PRECTOTCORR` à IMERG ne change pas en 2020 aux deux villes. L'abandon de `PRECTOTCORR` repose désormais sur son désaccord avec IMERG et le pluviomètre, plus que sur la rupture.
- **Sources non obtenues.** SMAP et SRTM exigent un compte Earthdata. MODIS et SoilGrids sont accessibles, mais un point au centre-ville ne décrit pas les champs.
- **Registre corrigé.** Le rayonnement de POWER vient de CERES SYN1deg et non de MERRA-2, comme l'indique l'en-tête des fichiers.
- **Travail antérieur déclaré.** Les fonctions reprises de African Crop Yield Intelligence sont listées dans docs/travail_anterieur.md.

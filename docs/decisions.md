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

## 14 novembre 2026, responsable de l'équipe, décisions sur la phase 2

- **Branches à jour de main.** bot-canal, bot-langage et presentation ont avancé jusqu'à main sans être extraites, moteur la contenait déjà. Elles suivent encore CLAUDE.md, que seule la branche moteur a retiré, alors que le responsable veut qu'il reste hors du dépôt, exclu par `.git/info/exclude`.
- **Pluie d'un lieu.** C'est la moyenne des neuf cases IMERG centrées sur la ville. Depuis 2013, la seule case de la ville dépasse cette moyenne de 7,6 % à Korhogo et de 4,3 % à Bouaké, contre moins de 1 % avant, selon `venv/bin/python -m moteur.controles`.
- **Points cultivés.** Ce sont les pixels MCD12Q1 de classes 12 et 14 de la couche `LC_Type1` IGBP. La couche UMD n'a plus de classe 14 dans la collection 6.1, selon le guide d'utilisation du produit.
- **Compte Earthdata.** Ouvert par le responsable, identifiants dans `~/.netrc`, jamais dans le dépôt. AppEEARS propose MCD12Q1, MOD13Q1, SMAP SPL3SMP_E et SRTMGL1 selon l'API de son catalogue, l'extraction reste à essayer.
- **Début du hackathon.** Le 14 novembre 2026, heure non précisée. Les fichiers du squelette ont été modifiés pour la dernière fois entre 00 h 18 et 00 h 23 GMT ce jour et le premier commit date de 00 h 38. `docs/travail_anterieur.md` reste inchangé tant que l'heure manque.

## 14 novembre 2026, responsable de l'équipe, CLAUDE.md, travail antérieur et références

- **CLAUDE.md retiré du suivi partout.** Le retrait n'existait que sur la branche moteur. Il a été reporté sur main par le commit `cf0b8e7`, sans toucher au fichier du disque, puis bot-canal, bot-langage et presentation ont avancé jusqu'à main. Le fichier reste dans l'historique et dans la copie distante de main.
- **Squelette déclaré comme travail antérieur.** L'heure exacte du début du hackathon n'étant pas connue, le contenu entier du premier commit `f3646cd` est déclaré par prudence dans docs/travail_anterieur.md.
- **Cadrage sur une seule source.** Les trois articles repérés ne sont pas téléchargés. Le cadrage reste fondé sur la seule source lue, Zagbaï, Berti et Lebailly, 2006.

## 14 novembre 2026, rôle données et moteur, phase 3 de CRISP-DM, partie sans Earthdata

- **.gitignore rétabli.** La ligne CLAUDE.md non commitée est retirée, seul `.git/info/exclude` exclut ce fichier, et git status ne le montre plus.
- **Indicateurs calculés pour Korhogo et Bouaké**, de 2001 à 2025, par `venv/bin/python -m moteur.indicateurs`, avec leur médiane, leurs quantiles 10 et 90 %, leur pente de Theil-Sen et un test de Mann-Kendall. Les résultats sont dans la section phase 3 de docs/donnees.md.
- **Règles de saison paramétrées.** Leurs seuils sont attribués à Sivakumar, 1988, par des sources secondaires seulement, l'article n'ayant pas pu être lu.
- **Trois défauts signalés au lieu d'être corrigés en silence.** La règle de fin de saison place la fin en novembre et n'est pas retenue. La recherche du début à partir du 1er mai coupe la saison 21 années sur 25 à Korhogo. MERRA-2 surestime d'environ un tiers la part des jours au-dessus de 35 °C par rapport au thermomètre de Korhogo.
- **Décisions soumises au responsable.** Date de recherche du début, remplacement de la fin de saison, traitement des jours chauds.

## 14 novembre 2026, responsable de l'équipe, règles des indicateurs

- **Début de saison cherché à partir du 1er mars pour les deux villes**, afin qu'elles restent comparables. Seule la première saison des pluies de Bouaké est traitée, ce qu'indiquent les limites de docs/donnees.md et le cadrage. Une recherche témoin à partir du 1er janvier montre que Korhogo n'est pas tronqué, une seule année sur 25 commençant avant le 1er mars, mais que Bouaké l'est. La saison y commence avant le 1er mars 11 années sur 25, et 6 débuts sur 25 tombent dans la première semaine de mars.
- **Plus de fin de saison.** La pluie et la chaleur se mesurent sur la durée du cycle de chaque culture à partir du début des pluies, avec des durées sourcées en phase 4. La règle de fin abandonnée plaçait la fin en novembre.
- **Température maximale moyenne sur le cycle au lieu des jours au-dessus de 35 °C.** Comparé au thermomètre de Korhogo, MERRA-2 n'a qu'un biais moyen de 0,46 °C, mais il compte 36,6 % de jours au-dessus de 35 °C contre 27,5 % à la station. Un faible biais déplace une moyenne de sa seule valeur, alors qu'il gonfle fortement un décompte au-dessus d'un seuil proche des valeurs courantes. La moyenne est donc plus robuste avec MERRA-2.
- **README mis à jour.** Il décrit les nouveaux modules, les dossiers de données et les deux commandes de reproduction, ne présente plus CLAUDE.md comme un fichier du dépôt, et perd la ligne isolée `# field-shift` ajoutée à sa fin par le commit `260cb06`.

## 14 novembre 2026, rôle données et moteur, durées des cycles et recherche du 1er février

- **Troncature de Bouaké acceptée comme limite écrite.** Une recherche du début à partir du 1er février change 10 années sur 25 à Bouaké, avance la médiane du 17 au 11 mars et le début de 8,6 jours en moyenne, jusqu'à 83 jours en 2003. À Korhogo, elle ne change que 2018. Le 1er mars reste la règle, la question pourra être posée à un agronome.
- **Durées de cycle tirées du tableau 11 de FAO-56**, version HTML lue sur fao.org, chaque ligne recopiée dans `moteur/cultures.py` et citée dans docs/donnees.md. La ligne de référence suit une règle visible, Afrique de l'Ouest, puis tropiques, puis reste de l'Afrique, puis toutes les lignes, et la plage de toutes les lignes sert de variabilité. Ces durées sont générales, non propres aux variétés ivoiriennes, et portent le niveau `hypothese`. L'igname et le mucuna, absents du tableau, n'ont pas de durée.
- **Anomalies du tableau signalées.** Pour les deux lignes du sorgho et pour le niébé, les stades imprimés ne somment pas au total imprimé, qui fait foi. La date de semis de la ligne West Africa de l'arachide est mal alignée dans la version HTML.
- **Indicateurs de cycle calculés** pour huit cultures et les deux villes. Le bilan retranche l'évapotranspiration de référence et non le besoin propre de chaque culture, ce qui est écrit dans les limites.
- **Registre des sources.** FAO-56 est ajouté aux connaissances agronomiques de docs/sources.md, partie que CLAUDE.md attribue au rôle présentation, qui en est informé par cette entrée.

## 14 novembre 2026, responsable de l'équipe, besoin en eau et cultures comparées

- **Besoin en eau de chaque culture.** C'est le coefficient cultural du tableau 12 de FAO-56 multiplié par l'évapotranspiration de référence, sur les stades du tableau 11, selon les équations 56 et 66 du bulletin, comparé à la pluie du cycle. L'équation 66 est vérifiée sur l'exemple 28 du bulletin. Les limites écrivent que ces coefficients supposent des conditions standard, sans stress ni variété locale, et sans ajustement climatique.
- **Ligne de référence réelle.** Pour disposer de stades, la durée de référence est désormais une ligne réelle du tableau 11, la médiane, ou la plus courte des deux médianes. Le sorgho passe de 135 à 130 jours, le mil de 123 à 105 et le riz de 165 à 150. Quand les stades imprimés ne somment pas au total, le stade de fin absorbe l'écart.
- **Igname et mucuna retirés de la comparaison chiffrée**, faute de durée et de coefficient sourcés, et cités dans les limites et les perspectives. Huit cultures restent, dont toutes celles des trois stratégies de l'exemple, ce que vérifie un test.
- **Membre chargé de la présentation prévenu** par le responsable de l'ajout de FAO-56 au registre des sources.

## 14 novembre 2026, responsable de l'équipe, durées de cycle sur une ligne réelle

- **Règle validée.** La durée de référence d'une culture est une ligne réelle du tableau 11 de FAO-56, la ligne médiane des lignes retenues, ou la plus courte des deux lignes médianes quand leur nombre est pair.
- **Sorgho, 130 jours au lieu de 135.** Ligne Sorghum, stades 20, 35, 40 et 30, total 130, semis May/June, région USA, Pakis., Med. Ses stades somment à 125, et le stade de fin passe à 35 jours pour atteindre le total imprimé.
- **Mil, 105 jours au lieu de 123.** Ligne Millet, stades 15, 25, 40 et 25, total 105, semis June, région Pakistan.
- **Riz pluvial, 150 jours au lieu de 165.** Ligne Rice, stades 30, 30, 60 et 30, total 150, semis Dec; May, région Tropics; Mediterranean.
- **Recalcul vérifié.** Les 57 tests passent, les fichiers `data/processed/cycles_<lieu>.csv` portent ces trois durées, et une nouvelle exécution de `venv/bin/python -m moteur.indicateurs` avec le code commité redonne exactement la sortie citée dans docs/donnees.md.

## 14 novembre 2026, rôle données et moteur, sources agronomiques des bénéfices

- **Six sources lues et consignées** dans docs/sources.md avec leur page. Yusuf et collègues 2009, avec l'IITA, au Nigeria, pour le précédent soja ou niébé du maïs. Guenot et Huchet-Bourdon 2014 au Burkina Faso pour la rotation coton puis maïs. Gouro et Vall 2010, projet du CIRAD au Mali et au Burkina Faso, et Cattan et collègues 2001 au Burkina Faso, pour la dégradation du sol en culture continue. La FAO 1995 pour la tolérance du sorgho et des mils à la sécheresse. Zagbaï et collègues 2006, déjà lu, pour Korhogo.
- **Aucune étude ivoirienne lue.** Les notes du CNRA d'Akanza et collègues sur l'arachide et le niébé comme précédents du maïs, et la thèse de Bado au Burkina Faso, n'ont pas pu être téléchargées, les serveurs répondant 403 ou 404. Elles restent des pistes, non citées.
- **Trois bénéfices restent des hypothèses sans source lue.** L'arachide comme précédent du maïs, l'arrière-effet des engrais du coton sur le maïs, et la meilleure tolérance du sorgho et du mil par rapport au maïs, que la FAO n'affirme que qualitativement et sans comparaison au maïs.
- **Bloc-notes vidé pendant une reprise de session.** La copie de secours de CLAUDE.md et les PDF déjà lus ont disparu du dossier temporaire. La copie a été refaite. Les empreintes notées dans les documents restent celles des fichiers lus.

## 14 novembre 2026, responsable de l'équipe, trois stratégies retenues

- **Stratégies inscrites dans `moteur/rotations.py`.** Coton puis maïs, la rotation actuelle. Coton, niébé puis maïs. Sorgho puis niébé. Chaque bénéfice, lacune et risque porte son niveau et le code de sa source au registre, ce que vérifie un test.
- **Niébé à la place de l'arachide.** Les trois conditions sont remplies. Sa durée, 110 jours, vient de la ligne Green gram, cowpeas du tableau 11 de FAO-56, son coefficient de la ligne Green Gram and Cowpeas du tableau 12, et son bénéfice de Yusuf et collègues 2009, où le maïs continu est inférieur au maïs après chacun des deux niébés, page 915. L'effet dépend de la variété et reste inférieur à celui du soja, page 920, ce qui figure dans les lacunes.
- **Arachide dans les perspectives**, faute de source lue sur son effet sur le maïs suivant. Elle garde sa durée et son coefficient sourcés.
- **Exemple fictif inchangé.** `moteur/exemple.json` garde sa stratégie avec arachide, car il ne sert qu'au développement des interfaces et le modifier relève d'une décision d'équipe sur le contrat.

## 14 novembre 2026, rôle données et moteur, notebooks par phase

- **Dossier `notebooks/`**, un notebook par phase de CRISP-DM sur le modèle de structure de African Crop Yield Intelligence, sans code repris. Les notebooks 01 et 02 sont écrits et exécutés, les suivants viendront avec leur phase.
- **Aucune logique dans les notebooks.** Ils appellent les fonctions de `moteur/` et affichent leurs résultats et leurs graphiques. Quatre calculs jusqu'ici écrits dans la commande de contrôle sont devenus des fonctions testées, `rupture_rapport`, `case_la_plus_arrosee`, `jours_par_annee` et `charger_lieu`, ainsi que `parametres_entete` et `essai_resolution_imerg`, qui rend reproductible l'essai de résolution d'IMERG fait à la main en phase 2. La commande `venv/bin/python -m moteur.controles` donne une sortie identique à celle du code précédent.
- **Exécution reproductible.** `venv/bin/python notebooks/executer.py` exécute les notebooks en place, par un noyau en transport IPC dans un dossier temporaire, sans horodatage des cellules, si bien que deux exécutions donnent des fichiers identiques. Chaque nombre cité dans les cellules de texte a été retrouvé dans les sorties, sauf les chiffres du projet antérieur, cités avec leur référence, et la taille de la maille MERRA-2.
- **Dépendances ajoutées et figées** aux versions du projet antérieur, ipykernel 7.4.0, matplotlib 3.11.2, nbclient 0.11.0 et nbformat 5.11.1. Les versions déjà figées n'ont pas changé.

## 14 novembre 2026, rôle données et moteur, pluie IMERG en temps universel et notebook 03

- **IMERG bien demandé en temps universel.** POWER ne sert `IMERG_PRECTOT` qu'en temps universel et renvoie -999 en temps solaire local, avec le message « The IMERG Source Data is not available at the Local Solar Time (LST) standard. », vérifié par une requête de trois jours. Les 21 requêtes IMERG du registre passent `time-standard=UTC`, leurs en-têtes l'indiquent, et les 18 séries complètes ont leurs 9 131 jours sans valeur manquante. Aucun retéléchargement n'a été nécessaire.
- **Protection ajoutée.** Une réponse entièrement à -999 est désormais refusée au téléchargement, un test fige le temps universel pour IMERG, et la lecture de l'en-tête s'arrête au bloc des messages, qu'elle aurait pris pour des paramètres.
- **Notebook 03 écrit et exécuté**, pour IMERG et POWER. Il appelle les fonctions de `moteur/`, dont trois nouvelles, `courbes_kc_comparees`, `tableau_cultures` et `tendance_theil_sen`, testées. SMAP, MODIS et SRTM y seront ajoutés quand les extractions AppEEARS seront disponibles.
- **Observation en passant.** La case IMERG de chaque ville compte nettement plus de jours de pluie non nulle que ses voisines, 5 507 contre 4 299 à 4 721 à Korhogo, ce qui va dans le sens de l'anomalie déjà signalée sur ces cases.

## 14 novembre 2026, rôle données et moteur, phase 4 de CRISP-DM et extractions AppEEARS

- **Notation extensible.** Dans `moteur/criteres.py`, chaque critère est une liste d'indicateurs, fonctions qui retournent une valeur, un score de 0 à 5, un niveau et une source, ou rien si leurs données manquent. Le score d'un critère est la moyenne de ses indicateurs disponibles. Un indicateur tiré de SMAP ou de MODIS s'ajoutera par une fonction inscrite dans `INDICATEURS`, ses données passant par le champ `surfaces` du contexte, ce qu'un test vérifie.
- **Règles de départ, à valider.** Eau, couverture du besoin, part des années où la pluie du cycle couvre le besoin de la culture, et besoin en eau, placé entre la culture comparée la plus économe et la plus exigeante, tous deux `calcule`. Sol, part des années en légumineuse, `hypothese` appuyée sur YUSUF2009 et CATTAN2001. Revenu qualitatif, part des années en coton, culture à débouché organisé selon GUENOT2014, `hypothese`, sans prix. Les poids et le passage d'une valeur à un score sont des choix de l'équipe.
- **Résultats.** Sorgho puis niébé arrive premier pour les priorités eau et sol, coton puis maïs pour la priorité revenu, coton, niébé puis maïs deuxième partout, à Korhogo comme à Bouaké. Le classement ne change ni avec une pluie réduite de 20 %, ni avec un début de saison retardé de 14 jours, alors que la couverture du besoin tombe par exemple de 0,98 à 0,74 pour coton puis maïs à Korhogo sous la pluie réduite.
- **Même classement dans les deux villes, absence expliquée.** Le sol et le revenu ne dépendent que de la composition des rotations, et l'écart de couverture entre les villes ne suffit pas à changer l'ordre. Les données NASA pèsent donc peu dans le classement actuel, ce qui est signalé. Les deux villes répondent en revanche en sens contraire à un début retardé, la couverture montant à Korhogo et baissant à Bouaké.
- **Extractions AppEEARS lancées** avec le compte Earthdata, identifiants lus dans `~/.netrc` sans être affichés ni écrits. Deux tâches MCD12Q1 `LC_Type1` de 961 points chacune, sur une grille de 0,01 degré qui recouvre les neuf cases IMERG de chaque ville, sont en attente chez AppEEARS. Les tâches sont consignées dans `data/raw/appeears/taches.json`, et chaque fichier sera vérifié contre l'empreinte SHA-256 publiée par AppEEARS.

## 14 novembre 2026, responsable de l'équipe, critère eau propre au lieu et à l'année

- **Critères renommés par ce qu'ils mesurent.** La clé `revenu` porte le libellé accès à un débouché organisé, fondé sur la place du coton dans l'économie des savanes, référence 1 du cadrage, page 325. La clé `sol` porte le libellé apport d'azote par les légumineuses. Les clés du contrat sont inchangées. Le premier critère pénalise mécaniquement toute rotation qui réduit le coton, ce qu'écrivent les limites.
- **Critère eau refondu, sans indicateur ajouté pour gonfler son poids.** L'indicateur de besoin relatif aux autres cultures est retiré. Restent, année par année et pour chaque culture, la couverture du besoin en eau du cycle, coefficient cultural FAO-56 fois évapotranspiration de référence depuis le début des pluies, par la pluie IMERG du même cycle, et la part des années sans séquence sèche de plus de 7 jours au stade de mi-saison. Le chapitre 8 de FAO-56 place la plus forte sensibilité au manque d'eau à la floraison et à la formation du rendement, que son chapitre 5 situe à la mi-saison. Chaque score d'eau porte son intervalle à 90 % par rééchantillonnage des années, graine fixée.
- **Korhogo et Bouaké se distinguent désormais sur la priorité eau.** Bouaké classe sorgho puis niébé premier, de façon stable, parce que la mi-saison du coton y tombe sur le creux de juillet, sans séquence sèche de plus de 7 jours seulement 0,2 des années. Korhogo classe coton, niébé puis maïs premier, mais l'eau n'y départage pas les stratégies, et un début retardé de 14 jours intervertit les deux suivantes. Ce résultat dépend de l'hypothèse de semis au début des pluies.
- **Source quantitative pour la phase 5.** Le tableau 24 de FAO-56 donne le facteur de réponse du rendement au manque d'eau, 1,25 pour le maïs et 0,9 pour le sorgho, utile à la vérification de bon sens.

## 14 novembre 2026, rôle données et moteur, date de semis du coton

- **Source lue sur le calendrier de semis.** Gnapi et collègues, 2025, CNRA, station de recherche sur le coton de Bouaké, page 1575. 70 % des producteurs enquêtés sèment le coton du 1er au 30 juin au nord du 9e parallèle, où est Korhogo, et 80 % du 11 juin au 10 juillet au sud, où est Bouaké. Aucun document de la CIDT ni de l'Intercoton n'a été trouvé.
- **Deux scénarios calculés.** Semis du coton au début des pluies, puis au début, au milieu et à la fin de la fenêtre observée, ou au début des pluies s'il survient plus tard, les autres cultures restant semées au début des pluies.
- **Bouaké, classement inchangé** pour les trois priorités et les trois dates de la fenêtre. La pluie y couvre le besoin du coton 0,96 des années semé au début des pluies, mais 0,375 semé le 25 juin, le cycle de 195 jours débordant sur la saison sèche, si bien que coton puis maïs reste dernier pour la priorité eau dans tous les cas.
- **Korhogo, classement de la priorité eau changé.** Sorgho puis niébé passe premier avec un semis du coton le 15 ou le 30 juin, au lieu de coton, niébé puis maïs. C'est écrit dans les limites.
- **Réserve.** La durée de 195 jours du coton, ligne Égypte, Pakistan et Californie de FAO-56, est probablement plus longue que celle des variétés ivoiriennes, ce qui exagère sans doute le manque d'eau du coton semé tard.
- **Décision à prendre.** Retenir ou non le semis observé par le CNRA comme référence pour le coton.

## 14 novembre 2026, responsable de l'équipe, semis de référence du coton, durée de son cycle et session AppEEARS

- **Semis observé par le CNRA retenu comme référence pour le coton**, au milieu de la fenêtre de Gnapi et collègues, 2025, le 15 juin à Korhogo et le 25 juin à Bouaké, parce qu'il est mieux sourcé que le début des pluies. Le semis au début des pluies devient un scénario de sensibilité.
- **Le classement de Korhogo pour la priorité eau dépend de la date de semis retenue pour le coton.** Avec le semis de référence, sorgho puis niébé est premier, devant coton, niébé puis maïs, à 0,063 point près. Avec un semis au début des pluies, l'ordre de ces deux stratégies s'inverse. C'est le résultat honnête et non une raison d'écarter la référence. Le classement de Bouaké ne change dans aucun scénario.
- **Korhogo et Bouaké reçoivent le même classement avec la référence**, mais des scores d'eau nettement différents, de 4,05 à 4,65 à Korhogo et de 2,969 à 4,35 à Bouaké.
- **Durée du cycle du coton non sourcée pour la Côte d'Ivoire.** Ni l'article du CNRA, ni deux affiches du CNRA à l'ICCB 2024, ni une recherche dans la littérature n'ont donné de durée lisible. La durée de FAO-56, 195 jours, est gardée et marquée comme non propre aux variétés ivoiriennes. Testée avec 180 et 225 jours, lignes du même tableau, et avec 150 jours, hypothèse aux stades proportionnels, elle change le classement pour l'eau à Korhogo dès 180 jours, et à Bouaké seulement avec 150 jours.
- **Session AppEEARS corrigée.** La surveillance précédente se connectait et se déconnectait à chaque passage, ouvrant au moins huit sessions sur le compte Earthdata partagé avec nasa-space-app-challenge, ce qui a pu invalider le jeton de ce projet. Elle a été arrêtée. Le client se connecte désormais une seule fois par processus, réutilise son jeton, se reconnecte une seule fois sur un refus 401 ou 403 avant de lever l'erreur, et ne se déconnecte plus. Des tests sans réseau le vérifient. La nouvelle surveillance est un seul processus qui interroge AppEEARS toutes les 15 minutes.

## 14 novembre 2026, responsable de l'équipe, durée du coton dans les résultats et compte Earthdata partagé

- **Durée du coton dans les résultats de l'outil.** Les 195 jours de FAO-56 restent la référence, marqués comme non propres aux variétés ivoiriennes. Cette incertitude figure désormais dans les lacunes des deux stratégies avec coton de `moteur/rotations.py`, qui seront montrées à l'agriculteur et au conseiller, et le notebook 04 montre le classement pour l'eau avec 150, 180, 195 et 225 jours. Le responsable écrit au CNRA pour obtenir la durée d'une variété ivoirienne.
- **Trois projets partagent le compte Earthdata**, field-shift et deux autres. Des jetons ont été refusés par erreur 403 cet après-midi dans le projet de l'équipe, en partie par des connexions simultanées. La reconnexion unique sur un refus 401 ou 403 est gardée. La surveillance ne s'arrête plus sur un refus qui persiste après la reconnexion : elle le signale et réessaie au passage suivant, ce qu'un test vérifie. Elle a été relancée avec ce code, une connexion de plus.

## 14 novembre 2026, rôle données et moteur, recommander et interfaces sur les vrais résultats

- **`recommander()` écrite.** Elle retourne pour Korhogo et Bouaké une Recommandation conforme au contrat, `donnees_fictives` à faux, avec cinq indicateurs, médiane de 2001 à 2025 et plage des quantiles 10 à 90 %, les trois stratégies retenues, leurs scores, preuves, bénéfices, lacunes et risques sourcés, le classement, sa stabilité et un avertissement qui nomme les scénarios qui le changent. Elle refuse un lieu hors zone ou une rotation inconnue. Les valeurs publiées sont arrondies, sinon le gabarit du bot écrivait par exemple 1221,81 mm, que le garde-fou ne retrouvait pas.
- **Confiance.** Faible pour une stratégie avec coton, dont la durée de cycle n'est pas propre aux variétés ivoiriennes, ou dont le rang change dans un scénario. Moyenne sinon. Jamais élevée, aucun bénéfice n'étant validé localement.
- **Application sur les vrais résultats.** `app/app.py` appelle `recommander()`, lit les paramètres d'URL envoyés par le bot et n'utilise plus l'exemple fictif. Un test exécute l'application sans navigateur, et un autre vérifie qu'aucun fichier de `app/` ni de `bot/` ne charge l'exemple fictif, réservé aux tests.
- **Bot.** Son dialogue n'est pas encore écrit, il n'affiche donc rien. Son gabarit `resume` produit sur les vraies recommandations un message qui passe le garde-fou pour les deux villes et les trois priorités. Il écrit cependant « Attention, ce classement change si la saison est plus sèche. » dès que le classement n'est pas stable, ce qui est faux pour Korhogo, dont le classement change avec la date de semis du coton. Le membre B est prévenu, l'avertissement du moteur nommant déjà le bon scénario.
- **Registre.** La source FAO56_ET0, équation 6 du chapitre 2 de FAO-56, est ajoutée, et `moteur/sources.py` convertit chaque code du registre en Source du contrat.

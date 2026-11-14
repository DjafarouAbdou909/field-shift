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

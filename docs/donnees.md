# Données

## Compréhension des données, phase 2

Établie le 14 novembre 2026. Chaque nombre des constats et du tableau des écarts est affiché par la commande `venv/bin/python -m moteur.controles`, ceux d'AppEEARS viennent de l'API de son catalogue, qui télécharge les séries absentes dans `data/raw` puis les contrôle sans les modifier. Chaque fichier téléchargé est consigné avec son empreinte SHA-256 dans `data/raw/power/registre.csv` et `data/raw/ghcn/registre.csv`. Deux exécutions successives ont donné des sorties identiques.

### Sources examinées

| Source | Variables | Résolution constatée | Période et pas | Accès | État |
|---|---|---|---|---|---|
| GPM IMERG par NASA POWER | Pluie `IMERG_PRECTOT`, mm par jour | 0,1 degré, vérifié | 2001 à 2025, jour en temps universel | API POWER sans compte | Téléchargée, case de chaque ville et ses huit voisines |
| NASA POWER, MERRA-2 | `T2M_MAX`, `T2M_MIN`, `T2MDEW`, `WS2M`, `PRECTOTCORR` | 0,5 par 0,625 degré | 2001 à 2025, jour en temps solaire local | API POWER sans compte | Téléchargée, `PRECTOTCORR` pour comparaison seulement |
| NASA POWER, CERES SYN1deg | Rayonnement `ALLSKY_SFC_SW_DWN`, MJ par m² et par jour | 1 degré d'après le nom du produit, non vérifié | 2001 à 2025, jour | API POWER sans compte | Téléchargé |
| NOAA GHCN-Daily | Pluie de pluviomètre, dixièmes de mm | Station | Lacunaire, voir plus bas | Fichiers publics NCEI | Téléchargée pour Korhogo `IVM00065536` et Bouaké `IV000005555` |
| MODIS MOD13Q1 par ORNL DAAC ou AppEEARS | NDVI et réflectances | 231,7 m | 16 jours | Service public sans compte, ou AppEEARS avec compte | Accès vérifié, rien téléchargé |
| MODIS MCD12Q1 par AppEEARS | Occupation du sol, classification IGBP | 500 m | Annuelle | Compte NASA Earthdata requis | Présence au catalogue vérifiée, rien téléchargé |
| ISRIC SoilGrids 2.0 | Argile, carbone organique, pH | 250 m | Sans objet | API REST sans compte | Accès vérifié, valeur vide au centre de Korhogo |
| NASA SMAP par AppEEARS | Humidité du sol en surface | 9 km selon le catalogue | Depuis le 31 mars 2015 | Compte NASA Earthdata requis | Présence au catalogue vérifiée, rien téléchargé |
| NASA SRTM par AppEEARS | Altitude et pente | 30 m selon le catalogue | Février 2000 | Compte NASA Earthdata requis | Présence au catalogue vérifiée, rien téléchargé |

La résolution d'IMERG a été établie par l'essai suivant. Deux points d'une même case de 0,1 degré, 9,42 et -5,68 puis 9,48 et -5,62, donnent la même pluie du 1er au 10 août 2025, alors que la case voisine au nord, 9,52 et -5,62, en diffère. Quatre points d'une même maille de 0,5 par 0,625 degré ont la même température et des pluies différentes.

### Constats

1. **Séries complètes et physiquement possibles.** Les 9 131 jours de 2001 à 2025 sont présents pour chaque variable aux deux lieux, sans date en double ni valeur manquante. Aucune pluie, aucun vent ni aucun rayonnement n'est négatif. Aucun minimum de température ne dépasse le maximum, aucun point de rosée ne dépasse la température maximale, et aucun rayonnement au sol ne dépasse le rayonnement extraterrestre de FAO-56. Aucune pluie journalière ne dépasse 200 mm, le maximum étant de 101,55 mm à Korhogo et 113,34 mm à Bouaké pour IMERG.
2. **Étiquette erronée dans les fichiers POWER.** L'en-tête CSV décrit `IMERG_PRECTOT` comme « MERRA-2 Total Precipitation ». Les métadonnées officielles de l'API, `api/system/manager/parameters`, le définissent comme la pluie totale d'IMERG, et le comportement à 0,1 degré le confirme. L'en-tête est donc faux, pas la donnée.
3. **IMERG et PRECTOTCORR divergent fortement.** Le cumul annuel moyen de 2001 à 2025 vaut 1 248 mm selon IMERG et 986 mm selon `PRECTOTCORR` à Korhogo, 1 133 mm et 1 347 mm à Bouaké. Les deux sources ne s'accordent donc pas sur la ville la plus arrosée. Leur corrélation journalière varie de 0,191 à 0,550 selon l'année à Korhogo et de 0,135 à 0,545 à Bouaké.
4. **Le pluviomètre favorise IMERG au jour le jour.** Sur les jours où la station a une valeur, la corrélation avec IMERG atteint 0,327 à Korhogo et 0,457 à Bouaké, contre 0,256 et 0,217 avec `PRECTOTCORR`. Elle baisse avec la pluie IMERG de la veille, à 0,286 et 0,331, ce qui confirme l'alignement des dates. Ces stations ne déclarent que 1 224 jours sur 13 années à Korhogo et 1 383 jours sur 12 années à Bouaké, sans aucune donnée de 2003 à 2014. Leurs jours ne forment pas un échantillon tiré au hasard, et elles ne permettent pas de dire quelle source donne le bon cumul annuel.
5. **La rupture de 2020 de `PRECTOTCORR` n'est pas visible à ces deux points.** Le rapport de son cumul annuel à celui d'IMERG vaut en moyenne 0,791 de 2001 à 2019 et 0,785 de 2020 à 2025 à Korhogo, 1,196 et 1,236 à Bouaké. La rupture établie par le projet antérieur sur l'ensemble de l'Afrique ne se lit donc pas localement, mais le constat 3 suffit à écarter `PRECTOTCORR`.
6. **La case de chaque ville est devenue anormalement humide.** Parmi les neuf cases de 0,1 degré centrées sur la ville, celle de la ville est la plus arrosée 1 année sur 12 de 2001 à 2012 et 11 années sur 13 de 2013 à 2025 à Korhogo, 0 sur 12 puis 9 sur 13 à Bouaké. Le hasard en donnerait une sur neuf. Les cases restent très liées au jour le jour, avec une corrélation médiane de 0,855 à 0,971 selon l'année et le lieu. La cause est inconnue. Un effet urbain réel ou un artefact du produit sont deux hypothèses, et la reprise des déclarations des stations en 2015 coïncide avec le changement sans le démontrer.
7. **Le calendrier des pluies concorde avec la littérature, pas les cumuls.** À Korhogo, la pluie mensuelle moyenne dépasse 50 mm d'avril, 88,1 mm, à octobre, 120,7 mm, avec un maximum en septembre de 239,0 mm. C'est la saison d'avril ou mai à octobre décrite par la référence 1 du cadrage avec ce même seuil. Les cumuls annuels d'IMERG, de 1 009,96 à 1 462,73 mm, dépassent en revanche souvent la plage de 800 à 1 200 mm qu'elle tire d'études de 1965 à 2000. Bouaké dépasse 50 mm de février à octobre, avec un creux en juillet, 92,6 mm, entre juin, 137,5 mm, et août, 125,3 mm.
8. **Un point au centre-ville ne décrit pas les champs.** SoilGrids renvoie une argile vide au centre de Korhogo, et le pixel MODIS de 231,7 m y couvre la ville. Les sols et la végétation doivent être lus sur des points cultivés autour de chaque ville.

### Décisions du responsable pour la phase 3

- **Pluie d'un lieu.** C'est la moyenne des neuf cases IMERG de 0,1 degré centrées sur la ville, à cause du constat 6. La dispersion entre cases sert de mesure d'incertitude spatiale. Le tableau suivant chiffre ce que ce choix change par rapport à la seule case de la ville.

| Lieu | Période | Écart moyen de la case de la ville à la moyenne des neuf cases | Écart annuel le plus bas et le plus haut |
|---|---|---|---|
| Korhogo | 2001 à 2012 | 9,0 mm, soit 0,7 % | -2,5 % et 3,9 % |
| Korhogo | 2013 à 2025 | 89,2 mm, soit 7,6 % | -1,7 % et 12,6 % |
| Korhogo | 2001 à 2025 | 50,7 mm, soit 4,3 % | -2,5 % et 12,6 % |
| Bouaké | 2001 à 2012 | -5,9 mm, soit -0,6 % | -2,7 % et 1,6 % |
| Bouaké | 2013 à 2025 | 50,5 mm, soit 4,3 % | 0,7 % et 7,4 % |
| Bouaké | 2001 à 2025 | 23,4 mm, soit 2,0 % | -2,7 % et 7,4 % |

La seule case de la ville aurait donc ajouté à Korhogo, depuis 2013, une hausse apparente de la pluie d'environ 7 %, que les cases voisines ne confirment pas.

- **Points cultivés.** Ce sont les pixels de MODIS MCD12Q1 version 6.1 de classe 12, terres cultivées à au moins 60 %, et 14, mosaïques de petites cultures couvrant 40 à 60 % avec de la végétation naturelle, dans la couche `LC_Type1` de la classification IGBP, tableau 3 du guide d'utilisation [G]. Ces deux classes ne coexistent que dans cette couche. La couche `LC_Type2` de l'Université du Maryland a perdu sa classe 14 dans la collection 6.1, selon la section 2.3 et le tableau 4 du même guide.
- **SMAP et SRTM.** Le responsable ouvre un compte NASA Earthdata. Ses identifiants restent dans `~/.netrc`, jamais dans le dépôt.

### AppEEARS pour les données de surface

L'API publique du catalogue d'AppEEARS, https://appeears.earthdatacloud.nasa.gov/api/product, interrogée le 14 novembre 2026 sans compte, liste 193 produits. Elle marque disponibles les quatre produits utiles, et décrit leurs couches avec leurs bornes et leurs codes de valeur manquante. La page du catalogue destinée aux lecteurs est https://appeears.earthdatacloud.nasa.gov/products. Elle répond, mais son contenu, construit dans le navigateur, n'a pas été lu.

| Besoin | Produit AppEEARS | Résolution | Période | Couche utile |
|---|---|---|---|---|
| Points cultivés | MCD12Q1.061, LP DAAC | 500 m | Annuelle depuis 2001, fin annoncée Present | `LC_Type1`, classes 1 à 17, valeur manquante 255 |
| NDVI et sol nu | MOD13Q1.061, LP DAAC | 250 m | 16 jours depuis le 18 février 2000 | `_250m_16_days_NDVI`, avec `_250m_16_days_pixel_reliability` |
| Humidité du sol | SPL3SMP_E.006, NSIDC DAAC | 9 km | Journalière depuis le 31 mars 2015 | `soil_moisture` du matin et `soil_moisture_pm` du soir, 0,02 à 0,5, valeur manquante -9999 |
| Pente | SRTMGL1_NC.003, LP DAAC | 30 m | Février 2000 | `SRTMGL1_DEM`, en mètres |

Trois remarques en découlent. Le produit SMAP retenu, SPL3SMP_E, provient du radiomètre, alors que SPL4SMGP, également proposé, sort d'un modèle d'assimilation et ne serait pas une mesure. Une case SMAP de 9 km couvre de nombreux pixels cultivés de 500 m, si bien que tous les points cultivés voisins partageront la même humidité. L'année la plus récente de MCD12Q1 n'est pas indiquée par l'API et reste à constater à l'extraction. L'extraction elle-même demande le compte Earthdata et n'a pas encore été essayée.

[G] Sulla-Menashe D. et Friedl M. A., User Guide to Collection 6 MODIS Land Cover, MCD12Q1 and MCD12C1, Product, avec l'avant-propos de la collection 6.1, https://lpdaac.usgs.gov/documents/1409/MCD12_User_Guide_V61.pdf, tableau 3 en page 9 du PDF et tableau 4 en page 10, empreinte SHA-256 du PDF lu cf3902bd4bb323e34c67c7c2f159631b2caf767b43e423805ede7768b3e95164.

### Ce qui n'est pas vérifié

La version et la chaîne de traitement d'IMERG servies par POWER, que l'API n'indique pas. La résolution effective du rayonnement CERES. La cause du constat 6. Le cumul annuel réel aux deux villes, aucune des trois sources ne permettant de trancher. La dernière année disponible de MCD12Q1, et l'extraction par AppEEARS, qui attend le compte Earthdata.

## Préparation des données, phase 3

Établie le 14 novembre 2026, sans les données qui attendent le compte Earthdata. Sauf mention contraire, chaque nombre de cette section est affiché par `venv/bin/python -m moteur.indicateurs` ou par `venv/bin/python -m moteur.controles`. Les indicateurs annuels de 2001 à 2025 sont écrits dans `data/processed/indicateurs_<lieu>.csv`. La pluie d'un lieu est la moyenne des neuf cases IMERG, la météo est celle de la maille POWER, et l'évapotranspiration suit FAO-56, vérifiée sur ses exemples 8 et 18.

### Règles retenues

- **Début de saison.** C'est le premier jour, à partir du 1er mars, qui ouvre trois jours cumulant au moins 20 mm sans séquence sèche de plus de 7 jours dans les 30 jours suivants. Ces seuils sont attribués à Sivakumar, 1988, par des sources secondaires. L'article n'a pas pu être lu, son dépôt à l'ICRISAT exigeant une authentification, et l'attribution reste à vérifier. Le 1er mars vaut pour les deux villes afin qu'elles restent comparables.
- **Cycle de culture au lieu d'une fin de saison.** La pluie, l'évapotranspiration, leur bilan, la température maximale moyenne et la plus longue séquence sèche se mesurent sur la durée du cycle de chaque culture à partir du début de saison, par `indicateurs_cycle`. Les durées viennent du tableau 11 de FAO-56 et le besoin en eau du tableau 12, comme décrit plus bas.
- **Température maximale moyenne au lieu des jours chauds.** Le nombre de jours au-dessus de 35 °C n'est plus calculé, pour la raison donnée plus bas.

### Résultats

| Indicateur, médiane et plage des quantiles 10 à 90 % | Korhogo | Bouaké |
|---|---|---|
| Pluie annuelle, mm | 1 222, de 1 033 à 1 318 | 1 120, de 901 à 1 279 |
| Évapotranspiration annuelle, mm | 1 930, de 1 772 à 2 014 | 1 529, de 1 436 à 1 633 |
| Indice d'aridité, pluie sur évapotranspiration | 0,63, de 0,52 à 0,73 | 0,72, de 0,57 à 0,85 |
| Début de saison | 13 avril, du 26 mars au 3 mai | 17 mars, du 2 mars au 29 avril, tronqué |
| Plus longue séquence sèche des 60 jours suivant le début, jours | 6, de 4 à 9 | 6, de 4,4 à 9 |

Aucune tendance de la pluie annuelle n'est significative au seuil de 5 %, avec +13,6 mm par décennie à Korhogo, p = 0,797, et +60,1 mm à Bouaké, p = 0,072. Le début de saison recule de 9,1 jours par décennie à Korhogo, p = 0,037. Ce recul reste fragile. Avec une recherche à partir du 1er mai, il tombait à +1,9 jour par décennie, p = 0,373, au commit `17cae3b`, et avec cinq indicateurs testés par lieu, la probabilité qu'au moins un soit significatif par hasard vaut environ 23 %, soit 1 moins 0,95 à la puissance 5 si les tests étaient indépendants. À Bouaké, la séquence sèche de début de saison s'allonge de 1,1 jour par décennie, p = 0,015, et l'indice d'aridité augmente de 0,070 par décennie, p = 0,034, sous les mêmes réserves.

### Troncature du début de saison par le 1er mars

Une recherche témoin à partir du 1er janvier montre ce que le 1er mars ne voit pas.

- **Korhogo n'est pas tronqué.** Aucun début ne tombe dans les 14 jours suivant le 1er mars, le plus précoce étant le jour 83, soit le 24 mars. La recherche témoin ne trouve qu'une année sur 25 où la saison commence avant le 1er mars, au jour 52, soit le 21 février.
- **Bouaké est tronqué.** 6 débuts sur 25 tombent dans les 7 jours suivant le 1er mars, dont 2 le 1er mars même, et 5 entre le 7e et le 13e jour. La recherche témoin trouve 11 années sur 25 où la saison commence avant le 1er mars, la plus précoce au jour 17, soit le 17 janvier. Le début de saison de Bouaké est donc retardé artificiellement près d'une année sur deux, et sa date médiane du 17 mars est trop tardive d'une quantité que la recherche témoin ne permet pas de fixer, puisque ses débuts de janvier et de février peuvent être de simples orages de saison sèche.

### Recherche du 1er février à Bouaké

À la demande du responsable, le début est aussi cherché à partir du 1er février. À Bouaké, 10 années sur 25 changent, la médiane passe du jour 76 au jour 70, soit du 17 au 11 mars, et l'écart moyen est de 8,6 jours. L'écart le plus grand, 83 jours, touche 2003, où la recherche du 1er mars ne trouve un début que le 9 mai, au jour 129, contre le 15 février, au jour 46, pour celle du 1er février. À Korhogo, seule l'année 2018 change, du jour 108 au jour 52. Le 1er mars reste la règle retenue, et cet écart mesure ce qu'elle retire à Bouaké.

### Durée du cycle des cultures

Elle vient du tableau 11 du chapitre 6 du bulletin FAO-56, Allen, Pereira, Raes et Smith, 1998, lu le 14 novembre 2026 dans sa version HTML, https://www.fao.org/4/x0490e/x0490e0b.htm. Chaque ligne est recopiée dans `moteur/cultures.py`. La ligne de référence est choisie dans l'ordre parmi les lignes d'Afrique de l'Ouest, des tropiques, puis du reste de l'Afrique, et sinon parmi toutes. Si plusieurs restent, c'est la ligne du total médian, la plus courte des deux lignes médianes quand leur nombre est pair. La référence est ainsi toujours une ligne réelle, dont les stades servent au coefficient cultural. La plage couvre toutes les lignes de la culture.

| Culture | Durée de référence, jours | Plage du tableau | Ligne du tableau 11, stades initial, développement, mi-saison et fin, total, semis, région |
|---|---|---|---|
| Coton | 195 | 180 à 225 | Cotton, 30, 50, 60, 55, total 195, Mar-May, Egypt; Pakistan; Calif. |
| Maïs | 125 | 125 à 180 | Maize grain, 20, 35, 40, 30, total 125, June, Nigeria humid |
| Sorgho | 130 | 130 à 140 | Sorghum, 20, 35, 40, 30, total 130, May/June, USA, Pakis., Med. |
| Mil | 105 | 105 à 140 | Millet, 15, 25, 40, 25, total 105, June, Pakistan |
| Arachide | 130 | 130 à 140 | Groundnut, 25, 35, 45, 25, total 130, Dry, West Africa |
| Niébé | 110 | 110 | Green gram, cowpeas, 20, 30, 30, 20, total 110, March, Mediterranean |
| Soja | 85 | 85 à 150 | Soybeans, 15, 15, 40, 15, total 85, Dec, Tropics |
| Riz pluvial | 150 | 150 à 180 | Rice, 30, 30, 60, 30, total 150, Dec; May, Tropics; Mediterranean |

Trois anomalies du tableau sont signalées. Les stades imprimés somment à 125 et 130 jours pour les deux lignes du sorgho, dont les totaux imprimés sont 130 et 140, et à 100 jours pour le niébé, au total imprimé de 110. Le total imprimé fait foi et le stade de fin absorbe l'écart, 35 jours au lieu de 30 pour le sorgho et 30 au lieu de 20 pour le niébé. La ligne Soybeans Central USA imprime 30/35 au développement, et seule la valeur 35 fait somme avec son total. Dans la version HTML, la date de semis de la ligne West Africa de l'arachide est imprimée Dry, le mot season passant à la ligne suivante, si bien que la période de semis de cette ligne reste incertaine.

### Coefficient cultural et besoin en eau

Le besoin en eau d'une culture est la somme, sur chaque jour du cycle, de son coefficient cultural multiplié par l'évapotranspiration de référence, équation 56 du chapitre 5 de FAO-56. Le coefficient vient du tableau 12 du même chapitre et sa courbe suit l'équation 66, constante aux stades initial et de mi-saison, linéaire au développement et en fin de cycle, ce que vérifie l'exemple 28 du bulletin, reproduit à 0,01 près. Une culture sans Kc ini propre prend celui de son groupe, et une valeur imprimée en plage prend le milieu de sa plage.

| Culture | Ligne du tableau 12 | Kc ini | Kc mid | Kc end |
|---|---|---|---|---|
| Coton | Cotton, Kc ini du groupe g. Fibre Crops | 0,35 | 1,15 à 1,20 | 0,70 à 0,50 |
| Maïs | Maize, Field grain, Kc ini du groupe i. Cereals | 0,3 | 1,20 | 0,60 à 0,35, note 11 |
| Sorgho | Sorghum, grain, Kc ini du groupe i. Cereals | 0,3 | 1,00 à 1,10 | 0,55 |
| Mil | Millet, Kc ini du groupe i. Cereals | 0,3 | 1,00 | 0,30 |
| Arachide | Groundnut, Kc ini du groupe e. Legumes | 0,4 | 1,15 | 0,60 |
| Niébé | Green Gram and Cowpeas, Kc ini du groupe e. Legumes | 0,4 | 1,05 | 0,60 à 0,35, note 6 |
| Soja | Soybeans, Kc ini du groupe e. Legumes | 0,4 | 1,15 | 0,50 |
| Riz pluvial | Rice | 1,05 | 1,20 | 0,90 à 0,60 |

La note 11 attribue 0,60 à une récolte de maïs humide et 0,35 à une récolte après séchage au champ, la note 6 attribue 0,60 au niébé récolté en frais et 0,35 en sec.

### Indicateurs sur le cycle des cultures

Pour chaque année, chaque culture commence au début de saison de l'année et dure sa durée de référence. Les médianes entre années sont les suivantes, les quantiles 10 et 90 % figurant dans la sortie de la commande et dans `data/processed/cycles_<lieu>.csv`. La pluie moins le besoin est donnée avec sa plage des quantiles 10 à 90 %.

| Culture | Pluie du cycle, mm, Korhogo puis Bouaké | Besoin en eau, mm | Pluie moins besoin, mm, médiane et plage | Années où la pluie reste sous le besoin, sur 25 | Température maximale moyenne, °C |
|---|---|---|---|---|---|
| Coton | 1 074 et 802 | 719 et 608 | 360, de 179 à 522, et 192, de 52 à 397 | 0 et 1 | 31,7 et 30,1 |
| Maïs | 637 et 525 | 482 et 415 | 113, de 24 à 298, et 95, de -8 à 215 | 1 et 3 | 32,6 et 30,7 |
| Sorgho | 671 et 562 | 453 et 390 | 193, de 89 à 358, et 128, de 29 à 293 | 0 et 1 | 32,5 et 30,6 |
| Mil | 479 et 438 | 378 et 323 | 78, de 16 à 218, et 115, de 18 à 230 | 2 et 2 | 33,1 et 31,1 |
| Arachide | 671 et 562 | 502 et 432 | 145, de 40 à 314, et 88, de -15 à 249 | 0 et 3 | 32,5 et 30,6 |
| Niébé | 518 et 468 | 405 et 347 | 83, de 26 à 215, et 108, de -2 à 234 | 2 et 3 | 32,9 et 31,0 |
| Soja | 360 et 366 | 399 et 334 | -40, de -115 à 73, et 36, de -51 à 129 | 15 et 8 | 33,9 et 31,5 |
| Riz pluvial | 806 et 606 | 760 et 659 | 15, de -74 à 229, et -60, de -159 à 65 | 11 et 18 | 32,0 et 30,3 |

Ces indicateurs décrivent le climat que traverse chaque cycle et le besoin d'une culture en conditions standard, pas la réponse d'une culture au manque d'eau. Le besoin du sorgho et du mil est plus faible que celui du maïs, mais que ces céréales tolèrent mieux la sécheresse reste à tirer d'une source agronomique en phase 4. L'écart entre cultures dépend aussi beaucoup de leur durée, le mil de 105 jours recevant moins de pluie que le sorgho de 130 jours.

### Limites

- **Une seule saison à Bouaké.** Bouaké a deux saisons des pluies, ce que montre le creux de juillet de la phase 2, et seule la première est traitée.
- **Début de Bouaké tronqué** près d'une année sur deux, comme décrit ci-dessus.
- **Durées générales.** Les durées du tableau 11 de FAO-56 sont générales et ne sont pas propres aux variétés ivoiriennes. Aucune ligne ne décrit la Côte d'Ivoire, une seule l'Afrique de l'Ouest pour l'arachide, une le Nigeria pour le maïs, et le tableau ne distingue pas le riz pluvial du riz irrigué. Elles portent donc le niveau `hypothese`, même avec leur source.
- **Igname et mucuna hors comparaison chiffrée.** Absents des tableaux 11 et 12 de FAO-56, ils n'ont ni durée ni coefficient cultural sourcés et ne figurent dans aucun chiffre. Huit cultures restent comparées, dont toutes celles des trois stratégies de l'exemple.
- **Conditions standard.** Les coefficients du tableau 12 supposent des cultures sans stress, bien conduites, à rendement maximal, sans variété locale. Kc mid et Kc end valent pour une humidité relative minimale d'environ 45 % et un vent d'environ 2 m/s, et FAO-56 demande de les ajuster sinon, ce qui n'est pas fait. Kc ini n'est qu'une approximation pour les études préliminaires selon le bulletin, et celui du riz, 1,05, suppose un sol très souvent humide qui ne convient pas forcément au riz pluvial.
- **Accès à un débouché organisé.** Ce critère, part des années en coton, pénalise mécaniquement toute rotation qui réduit le coton. Il mesure la place du coton dans l'économie des savanes selon Zagbaï et collègues, page 325, et non un revenu.
- **Apport d'azote par les légumineuses.** Ce critère, part des années en légumineuse, s'appuie sur une étude au Nigeria et ne mesure pas l'azote du sol.
- **Date de semis.** Le coton est semé au milieu de la fenêtre observée par le CNRA, le 15 juin à Korhogo et le 25 juin à Bouaké, GNAPI2025, page 1575, ou au début des pluies s'il survient plus tard. Les autres cultures sont supposées semées au début des pluies, ce qui reste une hypothèse. Le classement de Korhogo pour la priorité eau dépend de la date de semis retenue pour le coton. Semé au début des pluies ou le 1er juin, coton, niébé puis maïs y est premier, semé le 15 ou le 30 juin, sorgho puis niébé l'est. Le classement de Bouaké ne dépend pas de cette date.
- **Durée du cycle du coton.** Les 195 jours de la ligne Égypte, Pakistan et Californie de FAO-56 ne sont pas propres aux variétés ivoiriennes, et aucune durée ivoirienne n'a été trouvée dans un document lu. Ils mènent un coton semé fin juin jusqu'en janvier. Le classement pour l'eau en dépend. À Korhogo, il change entre 180 et 195 jours. À Bouaké, il reste le même entre 180 et 225 jours, mais change avec une durée hypothétique de 150 jours, où coton, niébé puis maïs passe premier.
- **Seuil des séquences sèches de mi-saison.** Le seuil de 7 jours est repris de la règle de début de saison, elle-même attribuée à Sivakumar par des sources secondaires.
- **Pluie totale et non pluie utile.** Le besoin est comparé à toute la pluie du cycle, sans retirer le ruissellement ni l'infiltration profonde, et sans tenir compte de la répartition des pluies dans le cycle. L'écart surestime donc l'eau dont la culture dispose.

### Perspectives

- **Igname et mucuna.** Les réintégrer dès qu'une durée de cycle et un coefficient cultural sourcés seront disponibles, par exemple auprès du CNRA ou de l'ANADER.
- **Arachide.** Elle a une durée et un coefficient sourcés, mais aucune source lue n'appuie encore son effet sur le maïs suivant, si bien qu'elle a été retirée de la stratégie coton, maïs et légumineuse au profit du niébé. Elle y reviendra si les notes du CNRA d'Akanza et collègues, ou la thèse de Bado, peuvent être lues et le confirment.
- **Ajustement climatique de Kc mid et Kc end**, selon les équations du chapitre 6 de FAO-56, avec l'humidité et le vent de POWER.
- **Pluie utile**, par un bilan hydrique du sol fondé sur la texture de SoilGrids.

### Choix écartés et leur raison

1. **Règle de fin de saison.** Elle exigeait 20 jours entièrement secs après le dernier jour de pluie d'au moins 1 mm, à partir du 1er septembre. Au commit `17cae3b`, elle plaçait la fin au 17 novembre en médiane à Korhogo, alors que la pluie mensuelle y tombe à 25,6 mm en novembre, où 11,2 % des jours reçoivent encore au moins 1 mm. La moyenne des neuf cases n'en était pas la cause, la case seule de la ville donnant une fin au jour 315 en médiane avec 12 années sans fin trouvée.
2. **Recherche du début à partir du 1er mai.** Au même commit, la recherche du 1er mars plaçait le début avant le 1er mai 21 années sur 25 à Korhogo et 22 sur 25 à Bouaké, ce que la recherche du 1er mai ne pouvait pas voir.
3. **Jours au-dessus de 35 °C.** Sur 2 258 jours communs avec le thermomètre de Korhogo, la température maximale de MERRA-2 dépasse celle de la station de 0,46 °C en moyenne, avec une corrélation de 0,818, mais elle dépasse 35 °C sur 36,6 % des jours contre 27,5 % à la station. À Bouaké, sur 2 075 jours, l'écart moyen est de 0,10 °C et la part des jours au-delà de 35 °C de 15,8 % contre 10,6 %. Un léger biais suffit à gonfler un décompte au-dessus d'un seuil, alors qu'il ne déplace une moyenne que de ce biais.

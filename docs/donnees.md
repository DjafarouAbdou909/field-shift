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

# Données

## Compréhension des données, phase 2

Établie le 14 novembre 2026. Chaque nombre de cette section est affiché par la commande `venv/bin/python -m moteur.controles`, qui télécharge les séries absentes dans `data/raw` puis les contrôle sans les modifier. Chaque fichier téléchargé est consigné avec son empreinte SHA-256 dans `data/raw/power/registre.csv` et `data/raw/ghcn/registre.csv`. Deux exécutions successives ont donné des sorties identiques.

### Sources examinées

| Source | Variables | Résolution constatée | Période et pas | Accès | État |
|---|---|---|---|---|---|
| GPM IMERG par NASA POWER | Pluie `IMERG_PRECTOT`, mm par jour | 0,1 degré, vérifié | 2001 à 2025, jour en temps universel | API POWER sans compte | Téléchargée, case de chaque ville et ses huit voisines |
| NASA POWER, MERRA-2 | `T2M_MAX`, `T2M_MIN`, `T2MDEW`, `WS2M`, `PRECTOTCORR` | 0,5 par 0,625 degré | 2001 à 2025, jour en temps solaire local | API POWER sans compte | Téléchargée, `PRECTOTCORR` pour comparaison seulement |
| NASA POWER, CERES SYN1deg | Rayonnement `ALLSKY_SFC_SW_DWN`, MJ par m² et par jour | 1 degré d'après le nom du produit, non vérifié | 2001 à 2025, jour | API POWER sans compte | Téléchargé |
| NOAA GHCN-Daily | Pluie de pluviomètre, dixièmes de mm | Station | Lacunaire, voir plus bas | Fichiers publics NCEI | Téléchargée pour Korhogo `IVM00065536` et Bouaké `IV000005555` |
| MODIS MOD13Q1 par ORNL DAAC | NDVI et réflectances | 231,7 m | 16 jours | Service public sans compte | Accès vérifié, rien téléchargé |
| ISRIC SoilGrids 2.0 | Argile, carbone organique, pH | 250 m | Sans objet | API REST sans compte | Accès vérifié, valeur vide au centre de Korhogo |
| NASA SMAP | Humidité du sol en surface | Non vérifiée | Depuis 2015 | Compte NASA Earthdata requis | Non obtenu |
| NASA SRTM | Altitude et pente | Non vérifiée | 2000 | Compte Earthdata ou clé OpenTopography requis | Non obtenu |

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

### Décisions proposées pour la phase 3

- **Pluie d'un lieu.** Prendre la moyenne des neuf cases IMERG plutôt que la seule case de la ville, à cause du constat 6, et garder la dispersion entre cases comme mesure d'incertitude spatiale.
- **Points cultivés.** Choisir autour de chaque ville des points de culture à partir d'une carte d'occupation du sol, dont la source reste à choisir et à vérifier.
- **SMAP et SRTM.** Ouvrir un compte NASA Earthdata, dont les identifiants iraient dans `.env`, ou renoncer à ces deux sources et le dire.

### Ce qui n'est pas vérifié

La version et la chaîne de traitement d'IMERG servies par POWER, que l'API n'indique pas. La résolution effective du rayonnement CERES. La cause du constat 6. Le cumul annuel réel aux deux villes, aucune des trois sources ne permettant de trancher.

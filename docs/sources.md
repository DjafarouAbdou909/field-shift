# Registre des sources

Toute valeur affichée par l'outil renvoie à une ligne de ce registre. Une ligne dont la version ou la date de consultation manque n'est pas encore vérifiée.

## Données d'observation

| Code | Jeu de données | Variable | Résolution | Période | Accès | Version et date de consultation |
|---|---|---|---|---|---|---|
| IMERG | NASA GPM IMERG, par l'API NASA POWER, version non indiquée par l'API | Pluie journalière, paramètre IMERG_PRECTOT, temps universel | 0,1 degré, vérifiée par points appariés | 2001 à 2025 | https://power.larc.nasa.gov/api/temporal/daily/point | Consulté le 14 novembre 2026, empreintes dans data/raw/power/registre.csv |
| POWER | NASA POWER, réanalyse MERRA-2 | Températures maximale et minimale, point de rosée, vent à 2 m, temps solaire local | 0,5 par 0,625 degré | 2001 à 2025 | https://power.larc.nasa.gov/api/temporal/daily/point | Consulté le 14 novembre 2026, empreintes dans data/raw/power/registre.csv |
| CERES | CERES SYN1deg, par l'API NASA POWER | Rayonnement solaire au sol ALLSKY_SFC_SW_DWN | 1 degré d'après le nom du produit, non vérifiée | 2001 à 2025 | https://power.larc.nasa.gov/api/temporal/daily/point | Consulté le 14 novembre 2026, empreintes dans data/raw/power/registre.csv |
| PRECTOTCORR | NASA POWER, réanalyse MERRA-2 | Pluie corrigée, servant à la seule comparaison avec IMERG | 0,5 par 0,625 degré | 2001 à 2025 | https://power.larc.nasa.gov/api/temporal/daily/point | Consulté le 14 novembre 2026, empreintes dans data/raw/power/registre.csv |
| GHCN | NOAA NCEI GHCN-Daily, stations IVM00065536 Korhogo et IV000005555 Bouaké, données GSOD | Pluie de pluviomètre en dixièmes de mm, selon readme.txt de GHCN-Daily | Station | Lacunaire, aucune donnée de 2003 à 2014 | https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/ | Consulté le 14 novembre 2026, empreintes dans data/raw/ghcn/registre.csv |
| SMAP | NASA SMAP | Humidité du sol en surface | À vérifier | Depuis 2015 | Compte NASA Earthdata requis | Non obtenu |
| MODIS | NASA MODIS MOD13Q1, par le service ORNL DAAC | NDVI | 231,7 m, 16 jours | À fixer | https://modis.ornl.gov/rst/api/v1/ | Accès vérifié le 14 novembre 2026, rien téléchargé |
| SRTM | NASA SRTM | Altitude et pente | 30 ou 90 mètres, à vérifier | 2000 | Compte Earthdata ou clé OpenTopography requis | Non obtenu |
| SOILGRIDS | ISRIC SoilGrids 2.0, non produit par la NASA | Texture, carbone organique, pH | 250 mètres | Sans objet | https://rest.isric.org/soilgrids/v2.0/ | Accès vérifié le 14 novembre 2026, valeur vide au centre de Korhogo |
| ECARTES | GWETROOT de NASA POWER | Humidité de la zone racinaire | Sans objet | Sans objet | Sans objet | Écarté le 14 novembre 2026, voir docs/decisions.md |

## Connaissances agronomiques

| Code | Affirmation | Référence complète | Page ou tableau |
|---|---|---|---|

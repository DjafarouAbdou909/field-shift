# Registre des sources

| Source | Contenu utilisé | Accès | Consultation |
|---|---|---|---|
| NASA POWER, API journalière par point, communauté AG | Températures, point de rosée, rayonnement, vent | https://power.larc.nasa.gov/ | 14 novembre 2026 |
| NASA GPM IMERG, par l'API NASA POWER | Pluie journalière, paramètre IMERG_PRECTOT | https://power.larc.nasa.gov/ | 14 novembre 2026 |
| Allen, Pereira, Raes et Smith, 1998, Crop evapotranspiration, FAO Irrigation and Drainage Paper 56 | Équations 6 à 40, exemple 18, tableau 11 des durées de stades, tableau 12 des coefficients culturaux | https://www.fao.org/4/x0490e/x0490e00.htm | 14 novembre 2026 |

Les lignes exactes des tableaux 11 et 12 sont citées pour chaque culture dans `config/projet.toml`.

## Hypothèses sans source lue

- La rotation actuelle coton puis maïs autour de Korhogo.
- L'apport d'azote des légumineuses au sol.
- Le débouché organisé du coton.
- Le critère de début des pluies, 20 mm en 3 jours sans plus de 7 jours secs dans les 30 jours suivants, à partir du 1er mars.

## Noms de lieux

| Source | Contenu utilisé | Accès | Licence |
|---|---|---|---|
| GeoNames, export CI.zip et admin1CodesASCII.txt | Lieux habités et subdivisions de quatrième niveau de Côte d'Ivoire, avec leur région | https://download.geonames.org/export/dump/ | Creative Commons Attribution 4.0 |

Les 52 localités sans région dans GeoNames reçoivent la région de la localité la plus proche qui en a une. GeoNames n'est pas une donnée NASA.

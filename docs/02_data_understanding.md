# Compréhension des données

Les chiffres de ce document sont produits par `python -m moteur.exporter` et figurent dans `app/donnees/recommandations.json`.

## 1. Inventaire

| Variable | Paramètre NASA POWER | Unité lue dans les fichiers | Usage |
|---|---|---|---|
| Pluie GPM IMERG | IMERG_PRECTOT | mm/day | Début des pluies, pluie de mi-saison |
| Température maximale et minimale | T2M_MAX, T2M_MIN | C | Évapotranspiration |
| Point de rosée | T2MDEW | C | Pression de vapeur réelle, FAO 56 équation 14 |
| Rayonnement solaire | ALLSKY_SFC_SW_DWN | MJ/m^2/day | Évapotranspiration |
| Vent à 2 mètres | WS2M | m/s | Évapotranspiration |

**Constat**

- Dix-huit points, neuf par lieu, sur une grille de 0,1 degré centrée sur la case qui contient chaque ville, de 2001 à 2024, soit 8 766 jours par point.
- Aucune valeur manquante pour aucun paramètre ni aucun point.
- L'altitude de chaque point est lue dans la géométrie de la réponse POWER, par exemple 352 m au point central de Korhogo.

**Analyse**

- L'API POWER ne sert IMERG qu'en temps universel. En heure solaire locale, réglage par défaut, toutes les valeurs valent moins 999. Les requêtes imposent donc le temps universel.
- Les unités correspondent exactement à celles qu'attend FAO 56, et aucune conversion n'est nécessaire.

## 2. Climat des deux lieux

| Indicateur | Korhogo | Bouaké |
|---|---|---|
| Pluie annuelle moyenne | 1 202 mm | 1 101 mm |
| Écart type interannuel | 115 mm | 172 mm |
| Début des pluies médian | 14 avril | 18 mars |
| Début des pluies, une année sur deux entre | 3 et 27 avril | 11 mars et 7 avril |

**Constat**

- D'après IMERG, Bouaké reçoit en moyenne moins de pluie que Korhogo, avec une variabilité plus forte.
- Le début des pluies est trouvé les 24 années dans les deux lieux.

**Analyse**

Bouaké ne peut donc pas être présentée comme la zone plus humide. Elle sert de zone de contraste du centre, avec une saison qui démarre plus tôt.

## 3. Tendance du début des pluies

| Durée maximale de séquence sèche | Korhogo, jours par décennie | Bouaké, jours par décennie |
|---|---|---|
| 7 jours, critère retenu | 14,4, intervalle de 8,6 à 23,0 | 2,9, intervalle de moins 12,1 à 19,8 |
| 10 jours | 6,5, intervalle de moins 1,8 à 15,3 | moins 3,0, intervalle de moins 9,6 à 4,8 |
| 14 jours | 0,7, intervalle de moins 8,8 à 11,7 | moins 5,3, intervalle de moins 10,2 à 0,3 |

**Constat**

- Avec le critère retenu, le début des pluies recule nettement à Korhogo. Ce recul disparaît dès que la séquence sèche tolérée passe à 10 jours.
- Les premières pluies de 20 mm en trois jours arrivent souvent tôt, puis sont suivies de plus de 7 jours secs. En 2017 par exemple, la première arrive le 18 mars et le début retenu le 28 mai.

**Analyse**

Le recul mesuré tient aux faux départs suivis d'une séquence sèche, et non à un retard général des premières pluies. Il dépend du critère choisi.

**Décision**

L'application n'annonce une tendance que si elle tient avec les trois critères. Elle affiche donc qu'aucune tendance robuste n'est établie.

## 4. Couverture du besoin en eau

Le besoin en eau de mi-saison est le coefficient cultural de FAO 56 multiplié par l'évapotranspiration de référence, sur le stade de pleine croissance, pour un semis au début des pluies. Il est comparé à la pluie IMERG du même stade.

| Culture | Korhogo, années couvertes sur 24 | Bouaké, années couvertes sur 24 |
|---|---|---|
| Coton | 23 | 10 |
| Maïs | 12 | 8 |
| Sorgho | 16 | 11 |
| Arachide | 17 | 8 |
| Niébé | 13 | 9 |

**Analyse**

- À Korhogo, le critère eau ne départage presque pas les rotations, avec 0,72 pour les deux rotations à légumineuse et 0,73 pour coton puis maïs, un écart bien inférieur à l'incertitude. Le classement y dépend surtout des critères sol et débouché, qui reposent sur des hypothèses.
- À Bouaké, la rotation avec sorgho et niébé couvre le mieux le besoin en eau, et le classement résiste aux deux scénarios.

## 5. Limites

- Le semis est supposé au début des pluies. Une date de semis observée, notamment pour le coton, peut changer les résultats.
- Seule la première saison des pluies de Bouaké est traitée.
- Les durées de stades et les coefficients de FAO 56 ne sont pas propres aux variétés ivoiriennes, et les coefficients ne sont pas ajustés au climat local.
- La pluie est comparée au besoin sans bilan hydrique du sol ni pluie efficace.
- Une case de 0,1 degré couvre environ 11 km et ne décrit pas une parcelle.

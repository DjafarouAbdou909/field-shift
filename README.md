# Nasa-space-abidjan

NASA Space Apps Challenge 2026, défi « Field Shift: Adapting Farms with NASA Data ».

Une application de conversation qui aide un agriculteur de Korhogo ou de Bouaké, en Côte d'Ivoire, à comparer sa rotation des cultures à d'autres, à partir des données de la NASA. Elle fonctionne **entièrement sans connexion** après une première ouverture.

## Principe

```
NASA POWER et GPM IMERG  --->  donnees/   téléchargement vérifié par empreinte
FAO 56, tableaux 11 et 12 --->  moteur/    début des pluies, besoin en eau, critères, sensibilité
                                   |
                                   v
                    app/donnees/recommandations.json   toutes les recommandations, calculées à l'avance
                                   |
                                   v
                    app/       application de conversation, hors connexion
```

L'application est pensée pour les personnes qui ne lisent pas. Chaque bouton porte un pictogramme, un mode voix lit chaque message et le nom de chaque bouton, et l'agriculteur peut enregistrer une note vocale dans sa langue pour son conseiller. La note reste sur le téléphone sans réseau et se partage dès que le réseau revient. L'application ne prétend pas la comprendre.

Le téléphone ne calcule rien et n'utilise ni réseau ni modèle de langage. Chaque phrase chiffrée vient du moteur, avec son niveau, mesuré, calculé ou hypothèse, et sa source. Le GPS situe le champ sans réseau.

## Architecture

```
config/projet.toml   lieux, période, paramètres, valeurs FAO 56 citées ligne par ligne, rotations, priorités
donnees/             python -m donnees, téléchargement et vérification des données NASA POWER
moteur/
  fao56.py           évapotranspiration de référence et coefficient cultural
  saison.py          début des pluies et séquences sèches
  series.py          séries journalières de chaque lieu
  criteres.py        critères eau, sol et débouché, classement, sensibilité
  statistiques.py    quartiles, intervalles de Wilson, tendances par bootstrap
  exporter.py        python -m moteur.exporter, recommandations pour l'application
app/                 application web installable et hors connexion
docs/                compréhension du métier, compréhension des données, sources, décisions
tests/               tests du moteur, dont l'exemple 18 de FAO 56
```

## Reproduire

```bash
python3.12 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python -m unittest discover -s tests -t .
venv/bin/python -m donnees            # 18 fichiers, 17 Mo mesurés le 14 novembre 2026
venv/bin/python -m moteur.exporter    # 5 secondes mesurées
```

## Essayer l'application

```bash
cd app && ../venv/bin/python -m http.server 8000
```

Ouvrez http://localhost:8000, et non l'adresse 0.0.0.0 affichée par le serveur, sur laquelle le navigateur bloque le GPS, le micro et le mode hors connexion. Ouvrez-la une première fois, puis coupez le serveur ou la connexion. L'application continue de fonctionner. Ce comportement a été vérifié dans Chrome, serveur arrêté, sur la conversation complète.

Pour les agriculteurs, l'application doit être publiée sur un hébergement HTTPS, puis ouverte une fois avec une connexion, par exemple au bureau de l'ANADER.

## Résultats et limites

Voir `docs/02_data_understanding.md`. En résumé, le critère eau départage les rotations à Bouaké mais presque pas à Korhogo, où le classement dépend surtout d'hypothèses sur le sol et le débouché, et aucune tendance robuste du début des pluies n'est établie. Le semis est supposé au début des pluies, et les valeurs de FAO 56 ne sont pas propres aux variétés ivoiriennes.

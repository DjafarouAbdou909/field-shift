# Field Shift CI

Équipe CodeX Africa, NASA Space Apps Challenge 2026, défi « Field Shift: Adapting Farms with NASA Data ».

Un outil d'aide à la décision qui compare au moins trois rotations des cultures, dont la rotation actuelle, pour les agriculteurs du nord de la Côte d'Ivoire, à partir des données de la NASA. Il est accessible par une application web pour le conseiller agricole et par WhatsApp, en texte et en voix, pour l'agriculteur.

## Arborescence

```
field-shift/
├── README.md
├── requirements.txt          versions figées
├── .env.example              paramètres à copier en .env, jamais versionné
├── moteur/                   rôle données et moteur
│   ├── contrat.py            Recommandation, seule frontière entre les rôles
│   ├── exemple.json          recommandation FICTIVE pour développer les interfaces
│   ├── recommander.py        point d'entrée, recommander() et charger_exemple()
│   ├── lieux.py              Korhogo, Bouaké
│   ├── donnees.py            téléchargement vérifié POWER, IMERG et GHCN, pluie des neuf cases
│   ├── controles.py          contrôles des séries, comparaison des sources de pluie
│   ├── indicateurs.py        indicateurs annuels et par cycle, tendance et variabilité
│   ├── cultures.py           cultures candidates et leurs caractéristiques sourcées
│   ├── rotations.py          trois stratégies retenues, appuis sourcés
│   ├── criteres.py           indicateurs par critère, scores, poids, sensibilité
│   ├── appeears.py           extractions NASA AppEEARS par points, compte Earthdata
│   ├── alerte.py             alerte de végétation NASA HLS, sans cause déduite
│   ├── maladies.py           liste fermée du diagnostic par photo, maladies sourcées
│   ├── sources.py            sources citées par le moteur, sous la forme du contrat
│   └── evaluation.py         conformité, bon sens et sensibilité des recommandations
├── bot/                      bot WhatsApp
│   ├── main.py               FastAPI, webhook vérifié          membre A
│   ├── config.py             paramètres lus dans l'environnement membre A
│   ├── securite.py           signature, idempotence, empreinte membre A
│   ├── sessions.py           conversations dans SQLite         membre A
│   ├── dialogue.py           machine à états du parcours       membre A
│   ├── whatsapp.py           envoi, boutons, listes, médias    membre A
│   └── langage/                                                membre B
│       ├── gabarits.py       messages déterministes
│       ├── garde_fou.py      aucun chiffre ni culture hors du moteur
│       ├── reformulation.py  réponses libres, sous garde-fou
│       └── voix.py           transcription et synthèse vocale
├── app/app.py                application Streamlit
├── tests/                    unittest, avec des webhooks Meta enregistrés
├── notebooks/                un notebook par phase de CRISP-DM, exécuté avant chaque commit
│   └── executer.py           exécute les notebooks en place
├── docs/
│   ├── cadrage.md            le problème en une page
│   ├── donnees.md            compréhension et préparation des données
│   ├── evaluation.md         évaluation des recommandations et limites
│   ├── sources.md            registre de chaque source
│   ├── travail_anterieur.md  ce qui existait avant le hackathon
│   └── decisions.md          journal des décisions
├── presentation/pitch.md
└── data/                     données, non versionnées
    ├── raw/power/            séries POWER et IMERG, avec registre des empreintes
    ├── raw/ghcn/             pluviomètres et thermomètres GHCN-Daily, avec registre
    └── processed/            indicateurs annuels par lieu
```

État au départ. Le contrat, l'exemple, la sécurité du webhook, le garde-fou, un premier gabarit et une application de démonstration sont écrits et testés. Les autres modules ne contiennent que leur cahier des charges, et leurs fonctions déjà déclarées lèvent `NotImplementedError`.

## Installation

```bash
python3.12 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
mkdir -p data                   # non versionné, le bot y crée sa base SQLite
venv/bin/python -m unittest discover -s tests -t .
```

La conversion audio demande aussi `ffmpeg`, par exemple `sudo apt install ffmpeg`.

## Reproduire les données et les indicateurs

```bash
venv/bin/python -m moteur.controles     # télécharge les séries absentes et les contrôle
venv/bin/python -m moteur.indicateurs   # calcule les indicateurs de Korhogo et Bouaké
venv/bin/python -m moteur.criteres      # note les stratégies et teste la sensibilité
venv/bin/python -m moteur.evaluation    # évalue les recommandations de recommander()
venv/bin/python -m moteur.appeears suivre   # état et téléchargement des extractions AppEEARS
```

Les chiffres cités dans `docs/donnees.md` sont ceux qu'affichent ces deux commandes.

Les notebooks de `notebooks/` appellent les fonctions de `moteur/` sans calcul propre, et se réexécutent avant chaque commit pour que leurs sorties soient visibles sur GitHub.

```bash
venv/bin/python notebooks/executer.py
```

## Lancement

```bash
venv/bin/streamlit run app/app.py                   # application, http://localhost:8501
venv/bin/uvicorn bot.main:app --port 8000           # bot, webhook sur /webhook
```

Meta exige une URL HTTPS publique pour le webhook, fournie par l'hébergeur ou par un tunnel.

## Démarrer une session Claude

Ouvrir Claude Code à la racine du dépôt, sur sa branche, puis coller le message de son rôle. `CLAUDE.md` n'est pas versionné. Chaque membre en garde une copie à la racine, exclue par `.git/info/exclude`, et Claude la charge automatiquement.

**Données et moteur, branche `moteur`**

```
Je tiens le rôle données et moteur. Lis CLAUDE.md, docs/decisions.md et git log, puis
résume en trois lignes où en est le moteur. Ensuite, écris moteur/donnees.py et
moteur/indicateurs.py pour Korhogo, en reprenant avec mention d'origine le code de
~/African-Crop-Yield-Intelligence, et consigne chaque source dans docs/sources.md.
Objectif de l'heure 16, les indicateurs de Korhogo calculés et contrôlés.
```

**Membre A, canal WhatsApp, branche `bot-canal`**

```
Je suis le membre A, responsable du canal WhatsApp. Lis CLAUDE.md, docs/decisions.md
et git log, puis résume en trois lignes où en est le bot. Je ne modifie que bot/main.py,
bot/config.py, bot/securite.py, bot/sessions.py, bot/dialogue.py et bot/whatsapp.py.
Objectif de l'heure 8, un bot écho joignable par WhatsApp. Écris d'abord les fonctions
d'envoi de bot/whatsapp.py, puis sessions.py et dialogue.py sur moteur.charger_exemple().
Chaque fonction a ses tests, sans appel réseau, avec des réponses de Meta enregistrées
dans tests/webhooks. Explique-moi chaque étape de configuration côté Meta.
```

**Membre B, langage et voix, branche `bot-langage`**

```
Je suis le membre B, responsable du langage et de la voix. Lis CLAUDE.md,
docs/decisions.md et git log, puis résume en trois lignes où en est le langage du bot.
Je ne modifie que bot/langage/. Commence par enrichir gabarits.py pour chaque étape du
parcours, chaque gabarit testé contre le garde-fou. Puis renforce garde_fou.py en
contrôlant les couples nombre et unité, ce qui lève la limite figée dans
test_limite_connue_petits_entiers. Ensuite voix.py, puis reformulation.py. Vérifie dans
la documentation officielle du fournisseur choisi le nom exact du modèle et les formats
audio, sans les supposer, et consigne le choix dans docs/decisions.md.
```

## Licence et attribution

À définir par l'équipe avant la soumission.

# Field Shift CI

Équipe CodeX Africa, NASA Space Apps Challenge 2026, défi « Field Shift: Adapting Farms with NASA Data ».

Un outil d'aide à la décision qui compare au moins trois rotations des cultures, dont la rotation actuelle, pour les agriculteurs du nord de la Côte d'Ivoire, à partir des données de la NASA. Il est accessible par une application web pour le conseiller agricole et par WhatsApp, en texte et en voix, pour l'agriculteur.

## Arborescence

```
field-shift/
├── CLAUDE.md                 consignes chargées par toute session Claude
├── README.md
├── requirements.txt          versions figées
├── .env.example              paramètres à copier en .env, jamais versionné
├── moteur/                   rôle données et moteur
│   ├── contrat.py            Recommandation, seule frontière entre les rôles
│   ├── exemple.json          recommandation FICTIVE pour développer les interfaces
│   ├── recommander.py        point d'entrée, recommander() et charger_exemple()
│   ├── lieux.py              Korhogo, Bouaké
│   ├── donnees.py            téléchargement vérifié NASA POWER et IMERG
│   ├── indicateurs.py        indicateurs, tendance et variabilité
│   ├── cultures.py           cultures candidates et leurs caractéristiques sourcées
│   ├── rotations.py          stratégies comparées
│   └── criteres.py           scores, poids par priorité, sensibilité
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
├── docs/
│   ├── cadrage.md            le problème en une page
│   ├── sources.md            registre de chaque source
│   ├── travail_anterieur.md  ce qui existait avant le hackathon
│   └── decisions.md          journal des décisions
├── presentation/pitch.md
└── data/                     données, non versionnées
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

## Lancement

```bash
venv/bin/streamlit run app/app.py                   # application, http://localhost:8501
venv/bin/uvicorn bot.main:app --port 8000           # bot, webhook sur /webhook
```

Meta exige une URL HTTPS publique pour le webhook, fournie par l'hébergeur ou par un tunnel.

## Démarrer une session Claude

Ouvrir Claude Code à la racine du dépôt, sur sa branche, puis coller le message de son rôle. `CLAUDE.md` est chargé automatiquement.

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
# field-shift

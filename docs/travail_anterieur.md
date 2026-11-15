# Travail antérieur au hackathon

Ce document déclare tout ce qui existait avant le début du hackathon, pour que le jury distingue clairement ce qui a été construit pendant l'événement.

## AGRI-BOT

AGRI-BOT est un assistant WhatsApp pour les agriculteurs, développé avant le hackathon par un membre de l'équipe et classé deuxième au Gnambélé BootCamp du PNUD en Côte d'Ivoire en septembre 2026. Il a inspiré la conception du bot de ce dépôt, notamment la vérification des signatures, l'idempotence et le profil de l'agriculteur. Aucun fichier d'AGRI-BOT n'a été copié tel quel. La consigne du diagnostic par photo de `moteur/diagnostic.py` a d'abord repris celle de `backend/nlp/prompts.py` d'AGRI-BOT, adaptée au vouvoiement et au conseiller ANADER et complétée par l'interdiction de nommer un produit, puis elle a été réécrite le 15 novembre 2026. Les trois messages d'échec du même module restent adaptés de `backend/vision/disease_client.py`. Ces deux emprunts sont mentionnés en tête du module. Le squelette du bot déclaré plus bas est antérieur au début par prudence, le reste du bot est écrit pendant le hackathon.

## African Crop Yield Intelligence

Ce projet de recherche sur les rendements agricoles africains, du même membre de l'équipe, fournit une chaîne testée de téléchargement et de traitement des données NASA POWER, IMERG, SoilGrids et relief. Les fonctions reprises sont listées ci-dessous, et chacune mentionne son origine en tête du fichier.

| Fichier de ce dépôt | Origine | Commit d'origine | Modifications |
|---|---|---|---|
| `moteur/donnees.py` | `empreinte_sha256` de `src/data/load.py`, `consigner` de `src/features/acquisition.py`, `telecharger_maille` et `lire_power` de `src/features/climat.py` | `2b4c18c` | Une requête par point au lieu d'une grille de mailles, période 2001 à 2025, GWETROOT retiré, contrôle de complétude isolé dans `reponse_complete` |
| `moteur/indicateurs.py` | `pression_saturante`, `rayonnement_extraterrestre`, `evapotranspiration_reference`, leurs constantes et le seuil de 1 mm d'un jour de pluie, de `src/features/indicateurs.py` | `2b4c18c` | Aucune. Le test de l'exemple 18 de FAO-56 de `tests/test_indicateurs.py` reprend celui de `tests/test_indicateurs.py` du même projet |
| `moteur/controles.py` | Seuil de 200 mm par jour de `src/features/controles.py` | `2b4c18c` | Utilisé comme repère, le reste du module est écrit pendant le hackathon |

## Squelette du dépôt

Le squelette a été préparé le 14 novembre 2026, jour du début du hackathon. Il forme en entier le premier commit `f3646cd`, daté de 00 h 38 GMT, qui inclut les corrections de la relecture notées ce jour dans `docs/decisions.md`. L'heure exacte du début n'étant pas connue, il est déclaré par prudence comme travail antérieur, en entier.

- **Structure.** Arborescence, README, `requirements.txt`, `.env.example`, `.gitignore`, et les cahiers des charges des modules encore vides.
- **Contrat.** `moteur/contrat.py`, l'exemple fictif `moteur/exemple.json`, `moteur/recommander.py` avec `charger_exemple`, les lieux de `moteur/lieux.py`, la liste des cultures de `moteur/cultures.py` et les poids par priorité de `moteur/criteres.py`.
- **Sécurité du webhook.** `bot/main.py`, `bot/securite.py`, `bot/config.py` et la lecture des messages entrants de `bot/whatsapp.py`, c'est-à-dire la vérification de signature, l'idempotence et l'empreinte salée des numéros.
- **Garde-fou et premier gabarit.** `bot/langage/garde_fou.py` et `bot/langage/gabarits.py`.
- **Application de démonstration.** `app/app.py`, qui affiche l'exemple fictif.
- **Tests.** Les 21 tests de `tests/test_contrat.py`, `tests/test_garde_fou.py` et `tests/test_webhook.py`, avec les webhooks enregistrés de `tests/webhooks`.

## Construit pendant le hackathon

Tout ce qui suit le commit `f3646cd`, à savoir le cadrage et les cinq notebooks CRISP-DM, le téléchargement et les contrôles des séries NASA POWER, IMERG et GHCN, les indicateurs agroclimatiques, le moteur de comparaison des rotations avec ses critères, sa sensibilité et son évaluation, la comparaison des périodes 2001-2012 et 2013-2025, les extractions AppEEARS de MODIS et HLS, l'application Streamlit branchée sur le moteur, le bot AgriBot sur WhatsApp avec son dialogue, sa voix, sa discussion agricole et son diagnostic par photo, leurs tests, le registre des sources, le journal des décisions et la présentation.

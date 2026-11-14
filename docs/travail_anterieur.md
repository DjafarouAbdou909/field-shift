# Travail antérieur au hackathon

Ce document déclare tout ce qui existait avant le début du hackathon, pour que le jury distingue clairement ce qui a été construit pendant l'événement.

## AGRI-BOT

AGRI-BOT est un assistant WhatsApp pour les agriculteurs, développé avant le hackathon par un membre de l'équipe et classé deuxième au Gnambélé BootCamp du PNUD en Côte d'Ivoire en septembre 2026. Il a inspiré la conception du bot de ce dépôt, notamment la vérification des signatures, l'idempotence et le profil de l'agriculteur. Aucun fichier d'AGRI-BOT n'a été copié, et le bot de ce dépôt est entièrement écrit pendant le hackathon.

## African Crop Yield Intelligence

Ce projet de recherche sur les rendements agricoles africains, du même membre de l'équipe, fournit une chaîne testée de téléchargement et de traitement des données NASA POWER, IMERG, SoilGrids et relief. Les fonctions reprises sont listées ci-dessous, et chacune mentionne son origine en tête du fichier.

| Fichier de ce dépôt | Origine | Commit d'origine | Modifications |
|---|---|---|---|
| `moteur/donnees.py` | `empreinte_sha256` de `src/data/load.py`, `consigner` de `src/features/acquisition.py`, `telecharger_maille` et `lire_power` de `src/features/climat.py` | `2b4c18c` | Une requête par point au lieu d'une grille de mailles, période 2001 à 2025, GWETROOT retiré, contrôle de complétude isolé dans `reponse_complete` |
| `moteur/indicateurs.py` | `rayonnement_extraterrestre` et `CONSTANTE_SOLAIRE` de `src/features/indicateurs.py` | `2b4c18c` | Aucune |
| `moteur/controles.py` | Seuil de 200 mm par jour de `src/features/controles.py` | `2b4c18c` | Utilisé comme repère, le reste du module est écrit pendant le hackathon |

## Construit pendant le hackathon

Le moteur de comparaison des rotations, le contrat, le bot WhatsApp, le garde-fou de fidélité, l'application Streamlit et la présentation.

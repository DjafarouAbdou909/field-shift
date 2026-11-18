#!/usr/bin/env bash
# Déploie AgriBot sur un serveur Ubuntu 24.04, à lancer depuis la racine du dépôt sur le PC.
#
#   bash deploy/deployer.sh utilisateur@adresse-ip mondomaine.com
#
# Envoie par SSH le fichier .env, les données NASA de data/ et ce dossier deploy/, puis lance
# l'installation sur le serveur avec sudo. Le code lui-même est cloné depuis GitHub, il faut donc
# avoir poussé la branche main avant. Rien n'est envoyé ailleurs que sur votre serveur.
set -euo pipefail

SERVEUR="${1:?usage, bash deploy/deployer.sh utilisateur@adresse-ip mondomaine.com}"
DOMAINE="${2:?usage, bash deploy/deployer.sh utilisateur@adresse-ip mondomaine.com}"

cd "$(dirname "$0")/.."
[ -f .env ] || { echo "Le fichier .env manque à la racine du dépôt." >&2; exit 1; }
[ -d data/raw/power ] || { echo "Les données NASA manquent dans data/raw, lancez d'abord python -m moteur.controles." >&2; exit 1; }
command -v rsync >/dev/null || { echo "Installez rsync sur le PC, sudo apt install rsync." >&2; exit 1; }

echo "1/3 Préparation du dossier d'envoi sur $SERVEUR"
ssh -t "$SERVEUR" 'mkdir -p ~/agribot-envoi && chmod 700 ~/agribot-envoi && (command -v rsync >/dev/null || sudo apt-get install -y rsync)'

echo "2/3 Envoi de .env, des données et des fichiers de déploiement"
rsync -az --chmod=F600 .env "$SERVEUR":agribot-envoi/.env
# Le modèle Whisper, environ 600 Mo, se retélécharge tout seul sur le serveur.
rsync -az --delete --exclude modeles/ --exclude 'simulateur_*' data/ "$SERVEUR":agribot-envoi/data/
rsync -az --delete deploy/ "$SERVEUR":agribot-envoi/deploy/

echo "3/3 Installation sur le serveur, le mot de passe sudo peut être demandé"
ssh -t "$SERVEUR" "sudo bash \$HOME/agribot-envoi/deploy/installer.sh '$DOMAINE' \$HOME/agribot-envoi"

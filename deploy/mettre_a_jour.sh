#!/usr/bin/env bash
# Met à jour AgriBot sur le serveur après un git push, à lancer sur le serveur.
#
#   sudo bash /opt/agribot/deploy/mettre_a_jour.sh
#
# ou depuis le PC, ssh -t utilisateur@adresse-ip sudo bash /opt/agribot/deploy/mettre_a_jour.sh
set -euo pipefail

RACINE=/opt/agribot
[ "$(id -u)" -eq 0 ] || { echo "À lancer avec sudo." >&2; exit 1; }

sudo -u agribot git -C "$RACINE" pull --ff-only
sudo -u agribot "$RACINE/venv/bin/pip" install -q -r "$RACINE/requirements.txt"
install -m 644 "$RACINE/deploy/agribot.service" /etc/systemd/system/agribot.service
install -m 644 "$RACINE/deploy/agribot-app.service" /etc/systemd/system/agribot-app.service
systemctl daemon-reload
systemctl restart agribot agribot-app
sleep 3
curl -fsS http://127.0.0.1:8000/sante && echo
echo "AgriBot est à jour, commit $(git -C "$RACINE" log --oneline -1)"

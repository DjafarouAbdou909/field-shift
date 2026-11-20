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
for unite in agribot-app.service agribot-sauvegarde.service agribot-sauvegarde.timer agribot-surveillance.service agribot-surveillance.timer; do
    install -m 644 "$RACINE/deploy/$unite" "/etc/systemd/system/$unite"
done
systemctl daemon-reload
# Configuration HTTPS régénérée avec le domaine noté à l'installation, ou lu dans l'ancienne configuration.
DOMAINE="$(cat /etc/agribot/domaine 2>/dev/null || sed -n 's/^bot\.\(.*\) {$/\1/p' /etc/caddy/Caddyfile | head -1)"
if [ -n "$DOMAINE" ]; then
    install -d -m 755 /etc/agribot && echo "$DOMAINE" > /etc/agribot/domaine
    sed "s/__DOMAINE__/$DOMAINE/g" "$RACINE/deploy/Caddyfile" > /etc/caddy/Caddyfile
    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null && systemctl reload caddy
fi
systemctl restart agribot agribot-app
sleep 3
curl -fsS http://127.0.0.1:8000/sante && echo
echo "AgriBot est à jour, commit $(sudo -u agribot git -C "$RACINE" log --oneline -1)"

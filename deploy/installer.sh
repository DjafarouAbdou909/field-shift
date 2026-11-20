#!/usr/bin/env bash
# Installe ou met à jour AgriBot sur un serveur Ubuntu 24.04, lancé par deploy/deployer.sh.
#
#   sudo bash installer.sh mondomaine.com /home/utilisateur/agribot-envoi
#
# Le bot répond sur https://bot.mondomaine.com/webhook et l'application des conseillers sur
# https://app.mondomaine.com. Caddy obtient et renouvelle seul les certificats HTTPS. Le script
# peut être relancé sans risque, il ne refait que ce qui manque.
set -euo pipefail

DOMAINE="${1:?usage, sudo bash installer.sh mondomaine.com dossier-envoi}"
ENVOI="${2:?usage, sudo bash installer.sh mondomaine.com dossier-envoi}"
DEPOT="${DEPOT:-https://github.com/DjafarouAbdou909/field-shift.git}"
RACINE=/opt/agribot
UTILISATEUR=agribot

[ "$(id -u)" -eq 0 ] || { echo "À lancer avec sudo." >&2; exit 1; }

echo "Paquets système"
apt-get update -q
DEBIAN_FRONTEND=noninteractive apt-get install -y -q python3.12 python3.12-venv ffmpeg git caddy ufw rsync curl \
    sqlite3 fail2ban unattended-upgrades
timedatectl set-timezone Africa/Abidjan || true

echo "Mémoire d'appoint"
# Avec 2 Go, le bot, Whisper et l'application tiennent juste. 2 Go de swap évitent qu'un pic de
# mémoire n'arrête un service. Rien n'est fait si le serveur a déjà du swap ou plus de 3 Go.
MEMOIRE_MO=$(awk '/MemTotal/ {print int($2 / 1024)}' /proc/meminfo)
if [ "$MEMOIRE_MO" -lt 3072 ] && [ -z "$(swapon --show --noheadings)" ]; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    sysctl -q vm.swappiness=10
    echo 'vm.swappiness=10' > /etc/sysctl.d/99-agribot.conf
fi

echo "Utilisateur de service $UTILISATEUR"
id "$UTILISATEUR" >/dev/null 2>&1 || useradd --system --create-home --home-dir /home/$UTILISATEUR \
    --shell /usr/sbin/nologin "$UTILISATEUR"

echo "Code depuis $DEPOT"
if [ -d "$RACINE/.git" ]; then
    sudo -u "$UTILISATEUR" git -C "$RACINE" pull --ff-only
else
    mkdir -p "$RACINE" && chown "$UTILISATEUR:$UTILISATEUR" "$RACINE"
    sudo -u "$UTILISATEUR" git clone --depth 1 "$DEPOT" "$RACINE"
fi

echo "Environnement Python"
[ -x "$RACINE/venv/bin/python" ] || sudo -u "$UTILISATEUR" python3.12 -m venv "$RACINE/venv"
sudo -u "$UTILISATEUR" "$RACINE/venv/bin/pip" install -q --upgrade pip
sudo -u "$UTILISATEUR" "$RACINE/venv/bin/pip" install -q -r "$RACINE/requirements.txt"

echo "Données NASA et réglages"
sudo -u "$UTILISATEUR" mkdir -p "$RACINE/data"
if [ -d "$ENVOI/data" ]; then
    rsync -a "$ENVOI/data/" "$RACINE/data/"
    chown -R "$UTILISATEUR:$UTILISATEUR" "$RACINE/data"
fi
if [ -f "$ENVOI/.env" ]; then
    install -o "$UTILISATEUR" -g "$UTILISATEUR" -m 600 "$ENVOI/.env" "$RACINE/.env"
    shred -u "$ENVOI/.env" 2>/dev/null || rm -f "$ENVOI/.env"
fi
[ -f "$RACINE/.env" ] || { echo "Le fichier $RACINE/.env manque, relancez deploy/deployer.sh depuis le PC." >&2; exit 1; }
# Le lien Détail envoyé aux agriculteurs doit pointer vers l'application publique, pas vers localhost.
[ -n "$(tail -c1 "$RACINE/.env")" ] && echo >> "$RACINE/.env"
if grep -q '^URL_APPLICATION=' "$RACINE/.env"; then
    sed -i "s|^URL_APPLICATION=.*|URL_APPLICATION=https://app.$DOMAINE|" "$RACINE/.env"
else
    echo "URL_APPLICATION=https://app.$DOMAINE" >> "$RACINE/.env"
fi

echo "Services AgriBot"
install -m 644 "$RACINE/deploy/agribot.service" /etc/systemd/system/agribot.service
install -m 644 "$RACINE/deploy/agribot-app.service" /etc/systemd/system/agribot-app.service
systemctl daemon-reload
systemctl enable --quiet agribot agribot-app
systemctl restart agribot agribot-app

echo "HTTPS par Caddy pour bot.$DOMAINE et app.$DOMAINE"
sed "s/__DOMAINE__/$DOMAINE/g" "$RACINE/deploy/Caddyfile" > /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null
systemctl enable --quiet caddy
systemctl reload caddy || systemctl restart caddy

echo "Pare-feu, SSH, HTTP et HTTPS seulement"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

echo "Sécurité et entretien du serveur"
# Mises à jour de sécurité d'Ubuntu installées chaque jour, sans intervention.
echo 'APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";' > /etc/apt/apt.conf.d/20auto-upgrades
# fail2ban bloque les adresses qui multiplient les échecs de connexion SSH, réglage par défaut d'Ubuntu.
systemctl enable --quiet --now fail2ban
# Journal système limité à 200 Mo, pour ne jamais remplir le disque.
mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nSystemMaxUse=200M\n' > /etc/systemd/journald.conf.d/agribot.conf
systemctl restart systemd-journald
# Connexion SSH par mot de passe coupée seulement si une clé SSH est déjà installée pour ce compte.
COMPTE="${SUDO_USER:-root}"
DOSSIER_COMPTE="$(getent passwd "$COMPTE" | cut -d: -f6)"
if [ -s "$DOSSIER_COMPTE/.ssh/authorized_keys" ]; then
    printf 'PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin prohibit-password\n' \
        > /etc/ssh/sshd_config.d/00-agribot.conf
    sshd -t && { systemctl reload ssh 2>/dev/null || systemctl restart ssh; }
    echo "Connexion SSH par clé uniquement, le mot de passe ne suffit plus."
else
    echo "Aucune clé SSH installée pour $COMPTE, la connexion par mot de passe reste ouverte. Lancez ssh-copy-id puis relancez le déploiement."
fi
# Sauvegarde quotidienne des sessions et surveillance du bot toutes les 5 minutes.
for unite in agribot-sauvegarde.service agribot-sauvegarde.timer agribot-surveillance.service agribot-surveillance.timer; do
    install -m 644 "$RACINE/deploy/$unite" "/etc/systemd/system/$unite"
done
systemctl daemon-reload
systemctl enable --quiet --now agribot-sauvegarde.timer agribot-surveillance.timer

echo "Vérification locale"
for essai in $(seq 1 30); do
    curl -fsS http://127.0.0.1:8000/sante >/dev/null 2>&1 && break
    sleep 2
done
curl -fsS http://127.0.0.1:8000/sante && echo
echo
echo "AgriBot est installé. Webhook à saisir chez Meta, https://bot.$DOMAINE/webhook"
echo "Journal du bot, sudo journalctl -u agribot -f"

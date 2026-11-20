#!/usr/bin/env bash
# Sauvegarde les sessions SQLite et les voix déjà synthétisées, et garde les 14 dernières copies.
# Lancé chaque nuit par agribot-sauvegarde.timer. Les sessions ne contiennent que des empreintes
# salées des numéros, jamais un numéro en clair.
set -euo pipefail

RACINE=/opt/agribot
CIBLE=/var/backups/agribot
JOUR="$(date +%Y-%m-%d)"
install -d -m 700 "$CIBLE"
if [ -f "$RACINE/data/bot.sqlite3" ]; then
    sqlite3 "$RACINE/data/bot.sqlite3" ".backup '$CIBLE/bot-$JOUR.sqlite3'"
    chmod 600 "$CIBLE/bot-$JOUR.sqlite3"
fi
[ -d "$RACINE/data/voix" ] && tar -czf "$CIBLE/voix-$JOUR.tar.gz" -C "$RACINE/data" voix
ls -1t "$CIBLE"/bot-*.sqlite3 2>/dev/null | tail -n +15 | xargs -r rm -f
ls -1t "$CIBLE"/voix-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm -f

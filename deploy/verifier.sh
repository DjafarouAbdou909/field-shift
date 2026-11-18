#!/usr/bin/env bash
# Vérifie depuis le PC que le bot déployé répond en HTTPS et accepte la vérification de Meta.
#
#   bash deploy/verifier.sh mondomaine.com
#
# Le jeton de vérification est lu dans .env et n'est jamais affiché.
set -euo pipefail

DOMAINE="${1:?usage, bash deploy/verifier.sh mondomaine.com}"
cd "$(dirname "$0")/.."
JETON="$(grep '^WHATSAPP_VERIFY_TOKEN=' .env | cut -d= -f2-)"

echo -n "Santé du bot, "
curl -fsS --max-time 15 "https://bot.$DOMAINE/sante" && echo

echo -n "Vérification Meta du webhook, "
REPONSE="$(curl -fsS --max-time 15 -G "https://bot.$DOMAINE/webhook" \
    --data-urlencode "hub.mode=subscribe" --data-urlencode "hub.verify_token=$JETON" \
    --data-urlencode "hub.challenge=agribot-ok")"
[ "$REPONSE" = "agribot-ok" ] && echo "acceptée" || { echo "refusée" >&2; exit 1; }

echo -n "Application des conseillers, code HTTP "
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 15 "https://app.$DOMAINE/"

# Déployer AgriBot sur un serveur

Ce guide met AgriBot sur un serveur allumé jour et nuit, pour que le bot ne dépende plus d'un PC ni de ngrok. Il marche avec n'importe quel hébergeur qui loue une machine Ubuntu 24.04, Google Cloud, Hetzner, Contabo, OVH ou un autre.

À la fin, vous aurez deux adresses en HTTPS.

| Adresse | Rôle |
|---|---|
| `https://bot.mondomaine.com/webhook` | Le webhook que Meta appelle à chaque message WhatsApp |
| `https://app.mondomaine.com` | L'application des conseillers, ouverte par le bouton Détail du bot |

## Ce qu'il faut avant de commencer

1. **Le domaine gratuit Space Apps**, réclamé chez Porkbun, par exemple `agribot-ci.com`.
2. **Un serveur Ubuntu 24.04** avec au moins **2 Go de mémoire**, 4 Go étant plus confortable pour Whisper, et 20 Go de disque. Notez son **adresse IP** et le nom d'utilisateur de connexion, souvent `root` ou `ubuntu`.
3. **Un accès SSH par clé** depuis votre PC. Testez `ssh utilisateur@adresse-ip`, la connexion doit s'ouvrir.
4. **Le dépôt à jour sur GitHub**, car le serveur télécharge le code depuis GitHub. Faites `git push origin main` avant.

## Étape 1, faire pointer le domaine vers le serveur

Dans Porkbun, ouvrez votre domaine, puis **DNS**, et ajoutez deux enregistrements.

| Type | Hôte | Réponse | TTL |
|---|---|---|---|
| A | `bot` | adresse IP du serveur | 600 |
| A | `app` | adresse IP du serveur | 600 |

Attendez quelques minutes, puis vérifiez depuis votre PC.

```bash
getent hosts bot.mondomaine.com app.mondomaine.com
```

Les deux lignes doivent afficher l'adresse IP du serveur. Sinon, attendez encore, le certificat HTTPS ne peut pas être obtenu avant.

## Étape 2, tout installer en une commande

Depuis la racine du dépôt sur votre PC.

```bash
bash deploy/deployer.sh utilisateur@adresse-ip mondomaine.com
```

La commande envoie au serveur, par SSH et nulle part ailleurs, votre fichier `.env`, les données NASA de `data/` et les fichiers de `deploy/`. Puis elle installe sur le serveur Python, ffmpeg, le code, le bot, l'application des conseillers, le HTTPS par Caddy et un pare-feu. Elle peut être relancée sans risque.

Sur le serveur, le fichier `.env` n'est lisible que par l'utilisateur `agribot`, et la copie envoyée est effacée après l'installation. Le lien Détail du bot est réglé sur `https://app.mondomaine.com`.

## Étape 3, vérifier

```bash
bash deploy/verifier.sh mondomaine.com
```

Les trois lignes doivent indiquer `{"statut":"ok"}`, `acceptée` et `200`. Le premier démarrage peut prendre une minute, le temps de charger les données NASA et de télécharger le modèle Whisper.

## Étape 4, brancher WhatsApp sur le serveur

Dans le tableau de bord Meta, ouvrez votre application, puis **WhatsApp**, puis **Configuration**.

1. Dans **Callback URL**, mettez `https://bot.mondomaine.com/webhook`.
2. Dans **Verify token**, gardez la même valeur que `WHATSAPP_VERIFY_TOKEN` dans `.env`.
3. Cliquez sur **Verify and save**.
4. Vérifiez que le champ **messages** est toujours abonné.

Envoyez « bonjour » au bot sur WhatsApp. S'il répond, vous pouvez arrêter le bot et ngrok sur votre PC.

**Jeton d'accès.** Un jeton temporaire de Meta expire en environ 24 heures. Pour un bot permanent, `WHATSAPP_ACCESS_TOKEN` doit être le jeton permanent d'un utilisateur système, créé dans Meta Business Suite. Après l'avoir mis dans `.env` sur le PC, relancez l'étape 2.

## Au quotidien

| Besoin | Commande depuis le PC |
|---|---|
| Mettre à jour le bot après un `git push` | `ssh -t utilisateur@adresse-ip sudo bash /opt/agribot/deploy/mettre_a_jour.sh` |
| Lire le journal du bot en direct | `ssh -t utilisateur@adresse-ip sudo journalctl -u agribot -f` |
| Redémarrer le bot | `ssh -t utilisateur@adresse-ip sudo systemctl restart agribot` |
| Changer une clé de `.env` | Modifier `.env` sur le PC, puis relancer l'étape 2 |

Le bot et l'application redémarrent seuls après une panne ou un redémarrage du serveur.

## En cas de problème

| Symptôme | Piste |
|---|---|
| `apt` ne trouve pas le paquet `caddy` | Installer Caddy depuis son dépôt officiel, guide sur https://caddyserver.com/docs/install, puis relancer l'étape 2 |
| `verifier.sh` échoue en HTTPS | Le domaine ne pointe pas encore vers le serveur, ou les ports 80 et 443 sont fermés chez l'hébergeur |
| Vérification Meta refusée | `WHATSAPP_VERIFY_TOKEN` diffère entre Meta et `.env` |
| Le bot ne répond plus après un jour | Jeton d'accès temporaire expiré, voir l'étape 4 |
| Les photos ne sont plus analysées | Quota gratuit de Gemini atteint, environ 20 photos par jour |

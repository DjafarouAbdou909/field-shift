"""Cohérence des fichiers de déploiement de deploy/, sans serveur ni réseau."""

import re
import subprocess
import unittest
from pathlib import Path

DEPLOY = Path(__file__).resolve().parent.parent / "deploy"
RACINE = DEPLOY.parent


class TestDeploiement(unittest.TestCase):
    def test_scripts_bash_valides(self):
        for script in sorted(DEPLOY.glob("*.sh")):
            resultat = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
            self.assertEqual(resultat.returncode, 0, f"{script.name} {resultat.stderr}")

    def test_services_lancent_le_bot_et_l_application(self):
        bot = (DEPLOY / "agribot.service").read_text()
        app = (DEPLOY / "agribot-app.service").read_text()
        self.assertIn("uvicorn bot.main:app --host 127.0.0.1 --port 8000", bot)
        self.assertIn("streamlit run app/app.py --server.port 8501 --server.address 127.0.0.1", app)
        self.assertTrue((RACINE / "bot" / "main.py").exists() and (RACINE / "app" / "app.py").exists())
        for service in (bot, app):
            self.assertIn("User=agribot", service, "jamais en root")
            self.assertIn("EnvironmentFile=/opt/agribot/.env", service)
            self.assertIn("Restart=always", service)

    def test_caddy_n_expose_que_le_webhook_et_la_sante(self):
        caddy = (DEPLOY / "Caddyfile").read_text()
        self.assertIn("bot.__DOMAINE__", caddy)
        self.assertIn("app.__DOMAINE__", caddy)
        bloc_bot = caddy.split("app.__DOMAINE__")[0]
        self.assertEqual(sorted(re.findall(r"handle (/\S+)", bloc_bot)), ["/sante", "/webhook*"])
        self.assertIn("reverse_proxy 127.0.0.1:8000", bloc_bot)
        self.assertIn("reverse_proxy 127.0.0.1:8501", caddy.split("app.__DOMAINE__")[1])

    def test_les_cles_ne_sont_jamais_affichees(self):
        """Aucun script n'affiche .env, et le jeton de vérification n'est jamais écrit à l'écran."""
        for script in DEPLOY.glob("*.sh"):
            texte = script.read_text()
            self.assertNotRegex(texte, r"cat [^\n]*\.env", script.name)
            self.assertNotRegex(texte, r"echo[^\n]*\$JETON", script.name)
        installer = (DEPLOY / "installer.sh").read_text()
        self.assertIn("-m 600", installer, ".env du serveur lisible par le seul utilisateur du service")

    def test_memoire_d_appoint_sur_petit_serveur(self):
        """Sous 3 Go, 2 Go de swap sont créés une seule fois, et gardés au redémarrage."""
        installer = (DEPLOY / "installer.sh").read_text()
        self.assertIn('[ "$MEMOIRE_MO" -lt 3072 ]', installer)
        self.assertIn("swapon --show", installer)
        self.assertIn("grep -q '^/swapfile ' /etc/fstab", installer)

    def test_securite_et_entretien_du_serveur(self):
        """Mises à jour de sécurité, fail2ban, SSH par clé lu en premier, journal limité, sauvegarde et surveillance."""
        installer = (DEPLOY / "installer.sh").read_text()
        for attendu in ("unattended-upgrades", "fail2ban", "SystemMaxUse=200M", "agribot-sauvegarde.timer",
                        "agribot-surveillance.timer", "PasswordAuthentication no"):
            self.assertIn(attendu, installer)
        self.assertIn("/etc/ssh/sshd_config.d/00-agribot.conf", installer,
                      "la première valeur lue gagne, le fichier doit passer avant 50-cloud-init.conf")
        self.assertIn('if [ -s "$DOSSIER_COMPTE/.ssh/authorized_keys" ]', installer,
                      "le mot de passe n'est coupé que si une clé est installée")
        for unite in ("agribot-sauvegarde.service", "agribot-sauvegarde.timer", "agribot-surveillance.service",
                      "agribot-surveillance.timer"):
            self.assertTrue((DEPLOY / unite).exists(), unite)
        self.assertIn("http://127.0.0.1:8000/sante", (DEPLOY / "agribot-surveillance.service").read_text())
        self.assertIn("tail -n +15", (DEPLOY / "sauvegarder.sh").read_text(), "14 copies gardées")

    def test_entetes_https(self):
        caddy = (DEPLOY / "Caddyfile").read_text()
        self.assertEqual(caddy.count("Strict-Transport-Security"), 3)

    def test_plateforme_hors_connexion_servie(self):
        """La plateforme hors connexion est servie par le VPS, son service de cache revérifié à chaque visite."""
        caddy = (DEPLOY / "Caddyfile").read_text()
        bloc = caddy.split("hors-ligne.__DOMAINE__")[1]
        self.assertIn("root * /opt/agribot/offline/app", bloc)
        self.assertIn('header /sw.js Cache-Control "no-cache"', bloc)
        self.assertTrue((RACINE / "offline" / "app" / "sw.js").exists())

    def test_redeploiement_garde_les_sessions_du_serveur(self):
        """Un nouveau déploiement depuis le PC n'écrase ni les sessions ni les voix du serveur."""
        installer = (DEPLOY / "installer.sh").read_text()
        self.assertIn("--exclude bot.sqlite3 --exclude voix/", installer)
        self.assertIn('[ -f "$RACINE/data/bot.sqlite3" ] ||', installer)
        self.assertIn("--ignore-existing", installer)

    def test_mise_a_jour_regenere_caddy(self):
        miseajour = (DEPLOY / "mettre_a_jour.sh").read_text()
        self.assertIn("/etc/agribot/domaine", miseajour)
        self.assertIn("caddy validate", miseajour)

    def test_lien_detail_public(self):
        """Le lien Détail des agriculteurs pointe vers l'application publique, pas vers localhost."""
        self.assertIn("URL_APPLICATION=https://app.$DOMAINE", (DEPLOY / "installer.sh").read_text())


if __name__ == "__main__":
    unittest.main()

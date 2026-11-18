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

    def test_lien_detail_public(self):
        """Le lien Détail des agriculteurs pointe vers l'application publique, pas vers localhost."""
        self.assertIn("URL_APPLICATION=https://app.$DOMAINE", (DEPLOY / "installer.sh").read_text())


if __name__ == "__main__":
    unittest.main()

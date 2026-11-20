import hashlib
import hmac
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from bot import main
from bot.securite import RegistreMessages, empreinte_numero, signature_valide
from bot.whatsapp import messages_entrants

WEBHOOKS = Path(__file__).with_name("webhooks")
SECRET = "secret-de-test"


def signer(corps: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), corps, hashlib.sha256).hexdigest()


class TestSecurite(unittest.TestCase):
    def test_signature(self):
        corps = b'{"a": 1}'
        self.assertTrue(signature_valide(corps, signer(corps), SECRET))
        self.assertFalse(signature_valide(corps + b" ", signer(corps), SECRET))
        self.assertFalse(signature_valide(corps, None, SECRET))
        self.assertFalse(signature_valide(corps, signer(corps), ""))
        self.assertFalse(signature_valide(corps, "sha256=é", SECRET))

    def test_empreinte_stable_et_salee(self):
        self.assertEqual(empreinte_numero("225", "sel"), empreinte_numero("225", "sel"))
        self.assertNotEqual(empreinte_numero("225", "sel"), empreinte_numero("225", "autre"))
        self.assertNotIn("225", empreinte_numero("225", "sel"))
        with self.assertRaises(ValueError):
            empreinte_numero("225", "")

    def test_registre(self):
        registre = RegistreMessages(":memory:")
        self.assertFalse(registre.deja_vu("wamid.A"))
        self.assertTrue(registre.deja_vu("wamid.A"))
        self.assertFalse(registre.deja_vu("wamid.B"))

    def test_statut_de_livraison_ignore(self):
        import json
        self.assertEqual(list(messages_entrants(json.loads((WEBHOOKS / "statut.json").read_text()))), [])


class TestWebhook(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {
            "WHATSAPP_VERIFY_TOKEN": "jeton", "WHATSAPP_APP_SECRET": SECRET,
            "BASE_DE_DONNEES": str(Path(self.dossier.name) / "bot.sqlite3"),
        })
        self.env.start()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.env.stop()
        main.registre.cache_clear()
        self.dossier.cleanup()

    def test_verification_meta(self):
        parametres = {"hub.mode": "subscribe", "hub.verify_token": "jeton", "hub.challenge": "42"}
        self.assertEqual(self.client.get("/webhook", params=parametres).text, "42")
        parametres["hub.verify_token"] = "faux"
        self.assertEqual(self.client.get("/webhook", params=parametres).status_code, 403)
        parametres["hub.verify_token"] = "é"
        self.assertEqual(self.client.get("/webhook", params=parametres).status_code, 403)

    def test_signature_invalide_refusee(self):
        corps = (WEBHOOKS / "texte.json").read_bytes()
        reponse = self.client.post("/webhook", content=corps, headers={"X-Hub-Signature-256": "sha256=0"})
        self.assertEqual(reponse.status_code, 403)
        reponse = self.client.post("/webhook", content=corps, headers={"X-Hub-Signature-256": "sha256=é".encode("latin-1")})
        self.assertEqual(reponse.status_code, 403)

    def test_message_traite_une_seule_fois(self):
        corps = (WEBHOOKS / "texte.json").read_bytes()
        entetes = {"X-Hub-Signature-256": signer(corps), "Content-Type": "application/json"}
        with mock.patch("bot.dialogue.traiter") as traiter:
            self.assertEqual(self.client.post("/webhook", content=corps, headers=entetes).status_code, 200)
            self.assertEqual(self.client.post("/webhook", content=corps, headers=entetes).status_code, 200)
        traiter.assert_called_once()
        self.assertEqual(traiter.call_args.args[0]["text"]["body"], "rotation")

    def test_age_et_longueur_journalises_sans_le_contenu(self):
        """Un message livré en retard se voit dans le journal, qui ne contient jamais le texte de l'agriculteur."""
        import json
        message = json.loads((WEBHOOKS / "texte.json").read_text())
        envoi = message["entry"][0]["changes"][0]["value"]["messages"][0]
        envoi["timestamp"] = str(int(main.time.time()) - 3600)
        corps = json.dumps(message).encode()
        entetes = {"X-Hub-Signature-256": signer(corps), "Content-Type": "application/json"}
        with mock.patch("bot.dialogue.traiter"), self.assertLogs("bot", "INFO") as journal:
            self.client.post("/webhook", content=corps, headers=entetes)
        ligne = next(l for l in journal.output if "reçu" in l)
        self.assertRegex(ligne, r"message text reçu, envoyé il y a 36\d\d s, 8 caractères")
        self.assertNotIn("rotation", ligne)


if __name__ == "__main__":
    unittest.main()

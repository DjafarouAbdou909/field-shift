import os
import unittest
from unittest import mock

from bot import whatsapp

ENV = {"WHATSAPP_ACCESS_TOKEN": "jeton-de-test", "WHATSAPP_PHONE_NUMBER_ID": "123"}


def reponse(contenu=None, octets=b""):
    r = mock.Mock()
    r.json.return_value = contenu or {}
    r.content = octets
    r.raise_for_status.return_value = None
    return r


class TestEnvois(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, ENV)
        self.env.start()
        self.client = mock.Mock()
        self.client.post.return_value = reponse({"id": "media-1"})
        self.post = mock.patch.object(whatsapp, "_http", return_value=self.client)
        self.post.start()
        self.appel = self.client.post
        whatsapp._medias.clear()

    def tearDown(self):
        self.post.stop()
        self.env.stop()

    def corps(self, rang=-1):
        return self.appel.call_args_list[rang].kwargs["json"]

    def test_texte(self):
        whatsapp.envoyer_texte("225", "Bonjour")
        self.assertEqual(self.appel.call_args.args[0], "https://graph.facebook.com/v27.0/123/messages")
        self.assertEqual(self.appel.call_args.kwargs["headers"], {"Authorization": "Bearer jeton-de-test"})
        self.assertEqual(self.corps(), {"messaging_product": "whatsapp", "recipient_type": "individual",
                                        "to": "225", "type": "text", "text": {"body": "Bonjour"}})

    def test_texte_long_decoupe(self):
        whatsapp.envoyer_texte("225", "\n".join(["a" * 3000] * 3))
        self.assertEqual(self.appel.call_count, 3)
        self.assertTrue(all(len(c.kwargs["json"]["text"]["body"]) <= 4096 for c in self.appel.call_args_list))

    def test_boutons(self):
        whatsapp.envoyer_boutons("225", "Choisissez", {"eau": "Eau", "sol": "Sol"})
        interactif = self.corps()["interactive"]
        self.assertEqual(interactif["type"], "button")
        self.assertEqual(interactif["action"]["buttons"][1], {"type": "reply", "reply": {"id": "sol", "title": "Sol"}})

    def test_limites_des_boutons(self):
        for boutons in ({}, {"a": "1", "b": "2", "c": "3", "d": "4"}, {"a": "x" * 21}, {"a": "Même", "b": "Même"}):
            with self.assertRaises(ValueError):
                whatsapp.envoyer_boutons("225", "Choisissez", boutons)
        self.appel.assert_not_called()

    def test_liste(self):
        whatsapp.envoyer_liste("225", "Votre zone", {"korhogo": "Korhogo"})
        action = self.corps()["interactive"]["action"]
        self.assertEqual(action["button"], "Choisir")
        self.assertEqual(action["sections"][0]["rows"], [{"id": "korhogo", "title": "Korhogo"}])
        with self.assertRaises(ValueError):
            whatsapp.envoyer_liste("225", "Trop", {str(i): str(i) for i in range(11)})

    def test_note_vocale(self):
        whatsapp.envoyer_audio("225", b"OggS")
        televersement = self.appel.call_args_list[0]
        self.assertEqual(televersement.args[0], "https://graph.facebook.com/v27.0/123/media")
        self.assertEqual(televersement.kwargs["data"]["messaging_product"], "whatsapp")
        self.assertEqual(televersement.kwargs["files"]["file"][2], "audio/ogg")
        self.assertEqual(self.corps()["audio"], {"id": "media-1", "voice": True})

    def test_note_identique_televersee_une_seule_fois(self):
        whatsapp.envoyer_audio("225", b"OggS-meme-note")
        whatsapp.envoyer_audio("226", b"OggS-meme-note")
        televersements = [c for c in self.appel.call_args_list if c.args[0].endswith("/media")]
        self.assertEqual(len(televersements), 1)
        self.assertEqual(self.corps()["audio"]["id"], "media-1")

    def test_indicateur_de_saisie(self):
        whatsapp.indiquer_saisie("wamid.1")
        self.assertEqual(self.appel.call_args.kwargs["json"], {
            "messaging_product": "whatsapp", "status": "read", "message_id": "wamid.1",
            "typing_indicator": {"type": "text"}})

    def test_sans_jeton(self):
        with mock.patch.dict(os.environ, {"WHATSAPP_ACCESS_TOKEN": ""}), self.assertRaises(RuntimeError):
            whatsapp.envoyer_texte("225", "Bonjour")


class TestMedia(unittest.TestCase):
    def test_telechargement_en_deux_temps_avec_le_jeton(self):
        client = mock.Mock()
        client.get.side_effect = [reponse({"url": "https://lookaside.example/media"}), reponse(octets=b"\xff\xd8image")]
        get = client.get
        with mock.patch.dict(os.environ, ENV), mock.patch.object(whatsapp, "_http", return_value=client):
            self.assertEqual(whatsapp.telecharger_media("m1"), b"\xff\xd8image")
        self.assertEqual(get.call_args_list[0].args[0], "https://graph.facebook.com/v27.0/m1")
        self.assertEqual(get.call_args_list[1].args[0], "https://lookaside.example/media")
        self.assertEqual(get.call_args_list[1].kwargs["headers"], {"Authorization": "Bearer jeton-de-test"})


class TestReformulation(unittest.TestCase):
    def setUp(self):
        from moteur import charger_exemple
        self.reco = charger_exemple()
        self.env = mock.patch.dict(os.environ, {"GROQ_API_KEY": "g"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_reponse_fidele_gardee(self):
        from bot.langage import reformulation
        generation = mock.Mock(return_value={"reponse": "Le sorgho demande moins d'eau."})
        self.assertEqual(reformulation.repondre("Pourquoi le sorgho ?", self.reco, "secours", generation),
                         "Le sorgho demande moins d'eau.")
        self.assertIn("Pourquoi le sorgho ?", generation.call_args.args[1])

    def test_reponse_infidele_remplacee(self):
        from bot.langage import reformulation
        generation = mock.Mock(return_value={"reponse": "Pulvérisez un fongicide, vous gagnerez 7 tonnes."})
        self.assertEqual(reformulation.repondre("Que faire ?", self.reco, "secours", generation), "secours")

    def test_panne_remplacee(self):
        from bot.langage import reformulation
        generation = mock.Mock(side_effect=RuntimeError("sans réseau"))
        self.assertEqual(reformulation.repondre("Que faire ?", self.reco, "secours", generation), "secours")


if __name__ == "__main__":
    unittest.main()

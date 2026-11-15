import json
import os
import unittest
from unittest import mock

from bot.langage import conversation, gabarits, groq


def session(contenu=None, json_brut=None):
    s = mock.Mock()
    s.post.return_value.status_code = 200
    s.post.return_value.json.return_value = json_brut or {"choices": [{"message": {"content": json.dumps(contenu)}}]}
    return s


class TestGroq(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"GROQ_API_KEY": "cle-de-test"})
        self.env.start()
        conversation.oublier("cle")

    def tearDown(self):
        self.env.stop()

    def test_generation_json_stricte(self):
        s = session({"option": "eau"})
        self.assertEqual(groq.generer("système", "message", groq.schema("choix", {"option": {"type": "string"}}), s),
                         {"option": "eau"})
        appel = s.post.call_args
        self.assertEqual(appel.args[0], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(appel.kwargs["headers"], {"Authorization": "Bearer cle-de-test"})
        corps = appel.kwargs["json"]
        self.assertEqual(corps["model"], "openai/gpt-oss-120b")
        self.assertEqual(corps["reasoning_effort"], "low")
        self.assertTrue(corps["response_format"]["json_schema"]["strict"])
        self.assertFalse(corps["response_format"]["json_schema"]["schema"]["additionalProperties"])

    def test_transcription(self):
        s = session(json_brut={"text": " Mon champ est à Korhogo. "})
        self.assertEqual(groq.transcrire(b"OggS", "audio/ogg; codecs=opus", s), "Mon champ est à Korhogo.")
        appel = s.post.call_args
        self.assertEqual(appel.args[0], "https://api.groq.com/openai/v1/audio/transcriptions")
        self.assertEqual(appel.kwargs["files"]["file"], ("note.ogg", b"OggS", "audio/ogg"))
        self.assertEqual(appel.kwargs["data"]["model"], "whisper-large-v3-turbo")
        self.assertEqual(appel.kwargs["data"]["language"], "fr")
        self.assertIn("Korhogo", appel.kwargs["data"]["prompt"])

    def test_reponse_filtree_et_retenue(self):
        generation = mock.Mock(return_value={"intention": "question",
                                             "reponse": "Semez après les pluies. Mettez de l'engrais NPK."})
        self.assertEqual(groq.repondre("cle", "Quand semer ?", generation),
                         ("question", f"Semez après les pluies. {conversation.RENVOI}"))
        self.assertEqual(conversation.historique("cle")[-1][0], "AgriBot")
        self.assertEqual(generation.call_args.args[0], conversation.CONSIGNE)

    def test_demande_de_rotation(self):
        self.assertEqual(groq.repondre("cle", "Je veux une rotation", mock.Mock(return_value={"intention": "rotation",
                                                                                              "reponse": ""})),
                         ("rotation", ""))

    def test_panne(self):
        self.assertEqual(groq.repondre("cle", "Q", mock.Mock(side_effect=RuntimeError()))[0], "indisponible")
        self.assertIsNone(groq.choisir("x", gabarits.BOUTONS_MENU, mock.Mock(side_effect=RuntimeError())))
        self.assertIsNone(groq.reformuler("s", "m", mock.Mock(side_effect=RuntimeError())))

    def test_choix_dans_l_enumeration(self):
        generation = mock.Mock(return_value={"option": "photo"})
        self.assertEqual(groq.choisir("mes plants ont des taches", gabarits.BOUTONS_MENU, generation), "photo")
        enum = generation.call_args.args[2]["json_schema"]["schema"]["properties"]["option"]["enum"]
        self.assertEqual(enum, ["rotation", "photo", "vegetation", "aucun"])
        self.assertIsNone(groq.choisir("rien", gabarits.BOUTONS_MENU, mock.Mock(return_value={"option": "aucun"})))

    def test_sans_cle(self):
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            self.assertFalse(groq.configure())
            with self.assertRaises(RuntimeError):
                groq.transcrire(b"x", "audio/ogg", session())


if __name__ == "__main__":
    unittest.main()

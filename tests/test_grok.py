import json
import os
import unittest
from unittest import mock

from bot.langage import conversation, grok


def reponse_grok(**sortie):
    return {"choices": [{"message": {"role": "assistant", "content": json.dumps(sortie)}}]}


class TestGrok(unittest.TestCase):
    def setUp(self):
        conversation.oublier("cle")

    def test_requete_figee(self):
        corps = grok.requete("Quand semer le maïs ?", [("agriculteur", "Bonjour"), ("Field Shift", "Bonjour.")])
        self.assertEqual(corps["model"], "grok-4.20-0309-non-reasoning")
        self.assertEqual(corps["messages"][0]["content"], conversation.CONSIGNE)
        self.assertIn("Quand semer le maïs ?", corps["messages"][1]["content"])
        self.assertIn("Field Shift : Bonjour.", corps["messages"][1]["content"])
        self.assertEqual(corps["response_format"]["json_schema"]["schema"]["properties"]["intention"]["enum"],
                         ["rotation", "question"])

    def test_reponse_filtree_et_retenue(self):
        appel = mock.Mock(return_value=reponse_grok(intention="question",
                                                    reponse="Semez après les premières pluies. Mettez de l'engrais NPK."))
        intention, reponse = grok.repondre("cle", "Quand semer ?", appel=appel)
        self.assertEqual((intention, reponse), ("question", f"Semez après les premières pluies. {conversation.RENVOI}"))
        self.assertEqual(conversation.historique("cle")[-1], ("Field Shift", reponse))

    def test_demande_de_rotation(self):
        appel = mock.Mock(return_value=reponse_grok(intention="rotation", reponse=""))
        self.assertEqual(grok.repondre("cle", "Je veux une rotation", appel=appel), ("rotation", ""))

    def test_panne(self):
        self.assertEqual(grok.repondre("cle", "Q", appel=mock.Mock(side_effect=RuntimeError()))[0], "indisponible")

    def test_cle_en_entete(self):
        session = mock.Mock()
        session.post.return_value.status_code = 200
        session.post.return_value.json.return_value = reponse_grok(intention="question", reponse="R.")
        with mock.patch.dict(os.environ, {"XAI_API_KEY": "cle-de-test"}):
            self.assertTrue(grok.configure())
            grok.appeler({"model": "x"}, session=session)
        self.assertEqual(session.post.call_args.args[0], "https://api.x.ai/v1/chat/completions")
        self.assertEqual(session.post.call_args.kwargs["headers"], {"Authorization": "Bearer cle-de-test"})

    def test_sans_cle(self):
        with mock.patch.dict(os.environ, {"XAI_API_KEY": ""}):
            self.assertFalse(grok.configure())
            with self.assertRaises(RuntimeError):
                grok.appeler({})


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from unittest import mock

from bot.langage import conversation


def interaction(**sortie):
    return {"status": "completed", "steps": [{"type": "model_output", "content": [
        {"type": "text", "text": json.dumps(sortie)}]}]}


class TestFiltre(unittest.TestCase):
    def test_produits_retires(self):
        for phrase in ("Pulvérisez un fongicide.", "Mettez 200 kg par hectare d'engrais NPK.",
                       "Achetez de l'huile de neem au marché.", "Utilisez du savon noir dilué.",
                       "Le glyphosate détruit les herbes."):
            sortie = conversation.filtrer(f"Observez vos plants. {phrase}")
            self.assertEqual(sortie, f"Observez vos plants. {conversation.RENVOI}", phrase)

    def test_anader_jamais_en_son_nom(self):
        sortie = conversation.filtrer("En tant qu'agent de l'ANADER, je vous conseille ceci. Le sorgho résiste bien.")
        self.assertNotIn("En tant qu", sortie)
        self.assertIn("Le sorgho résiste bien.", sortie)
        self.assertEqual(conversation.filtrer("Allez voir votre conseiller ANADER."), "Allez voir votre conseiller ANADER.")

    def test_mots_proches_gardes(self):
        texte = "L'huile de palme vient du palmier. Une remarque utile sur la dose de pluie n'existe pas."
        self.assertIn("L'huile de palme vient du palmier.", conversation.filtrer(texte))

    def test_lignes_gardees(self):
        self.assertEqual(conversation.filtrer("Ligne un.\nLigne deux."), "Ligne un.\nLigne deux.")


class TestRepondre(unittest.TestCase):
    def setUp(self):
        conversation.oublier("cle")

    def test_question_et_memoire(self):
        appel = mock.Mock(side_effect=[
            interaction(transcription="", intention="question", reponse="Le niébé enrichit le sol."),
            interaction(transcription="", intention="question", reponse="Oui, après le maïs.")])
        self.assertEqual(conversation.repondre("cle", "À quoi sert le niébé ?", appel=appel)[:2],
                         ("question", "Le niébé enrichit le sol."))
        conversation.repondre("cle", "Et après quoi ?", appel=appel)
        deuxieme = appel.call_args_list[1].args[0]
        self.assertIn("Le niébé enrichit le sol.", deuxieme["input"][0]["content"][0]["text"])
        self.assertIs(deuxieme["store"], False)
        self.assertIn("Ne nomme jamais de produit", deuxieme["system_instruction"])

    def test_memoire_oubliee(self):
        appel = mock.Mock(return_value=interaction(transcription="", intention="question", reponse="R."))
        conversation.repondre("cle", "Q", appel=appel)
        conversation.oublier("cle")
        self.assertEqual(conversation.historique("cle"), [])

    def test_memoire_expiree(self):
        appel = mock.Mock(return_value=interaction(transcription="", intention="question", reponse="R."))
        conversation.repondre("cle", "Q", appel=appel)
        with mock.patch.object(conversation.time, "monotonic", return_value=10 ** 9):
            self.assertEqual(conversation.historique("cle"), [])

    def test_demande_de_rotation(self):
        appel = mock.Mock(return_value=interaction(transcription="je veux une rotation", intention="rotation", reponse="x"))
        self.assertEqual(conversation.repondre("cle", audio=(b"OggS", "audio/ogg; codecs=opus"), appel=appel),
                         ("rotation", "", "je veux une rotation"))
        audio = appel.call_args.args[0]["input"][0]["content"][1]
        self.assertEqual((audio["type"], audio["mime_type"]), ("audio", "audio/ogg"))

    def test_reponse_filtree(self):
        appel = mock.Mock(return_value=interaction(transcription="", intention="question",
                                                   reponse="Arrachez les plants. Pulvérisez un insecticide."))
        self.assertEqual(conversation.repondre("cle", "Que faire ?", appel=appel)[1],
                         f"Arrachez les plants. {conversation.RENVOI}")

    def test_panne(self):
        self.assertEqual(conversation.repondre("cle", "Q", appel=mock.Mock(side_effect=RuntimeError()))[:2],
                         ("question", conversation.SECOURS))


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from unittest import mock

from bot.langage import gabarits
from bot.langage.comprehension import comprendre, par_le_modele, par_les_mots


class TestParLesMots(unittest.TestCase):
    def test_phrases_dites(self):
        cas = [("Oui d'accord", gabarits.BOUTONS_CONSENTEMENT, "accepte"),
               ("Non merci", gabarits.BOUTONS_CONSENTEMENT, "refuse"),
               ("je veux un conseil pour semer", gabarits.BOUTONS_MENU, "rotation"),
               ("ma plante est malade", gabarits.BOUTONS_MENU, "photo"),
               ("Bouaké", gabarits.LIGNES_LIEUX, "bouake"),
               ("je suis vers Korhogo", gabarits.LIGNES_LIEUX, "korhogo"),
               ("je fais du coton et du maïs", gabarits.LIGNES_ROTATIONS, "coton_mais"),
               ("coton et maïs", gabarits.LIGNES_ROTATIONS, "coton_mais"),
               ("je plante sorgho et niébé", gabarits.LIGNES_ROTATIONS, "sorgho_niebe"),
               ("coton niébé maïs", gabarits.LIGNES_ROTATIONS, "coton_niebe_mais"),
               ("la pluie, l'eau", gabarits.BOUTONS_PRIORITE, "eau"),
               ("le deuxième", gabarits.BOUTONS_PRIORITE, "revenu"),
               ("3", gabarits.BOUTONS_PRIORITE, "sol"),
               ("bonjour comment ça va", gabarits.BOUTONS_MENU, None)]
        for phrase, options, attendu in cas:
            self.assertEqual(par_les_mots(phrase, options), attendu, phrase)

    def test_egalite_ne_tranche_rien(self):
        self.assertIsNone(par_les_mots("eau et sol", gabarits.BOUTONS_PRIORITE))


class TestParLeModele(unittest.TestCase):
    def interaction(self, option):
        return {"status": "completed", "steps": [{"type": "model_output", "content": [
            {"type": "text", "text": json.dumps({"option": option})}]}]}

    def test_option_choisie_dans_l_enumeration(self):
        appel = mock.Mock(return_value=self.interaction("photo"))
        self.assertEqual(par_le_modele("mes plants ont des taches", gabarits.BOUTONS_MENU, appel), "photo")
        corps = appel.call_args.args[0]
        self.assertIs(corps["store"], False)
        self.assertEqual(corps["response_format"]["schema"]["properties"]["option"]["enum"],
                         ["rotation", "photo", "aucun"])

    def test_aucun_ou_panne(self):
        self.assertIsNone(par_le_modele("rien", gabarits.BOUTONS_MENU, mock.Mock(return_value=self.interaction("aucun"))))
        self.assertIsNone(par_le_modele("rien", gabarits.BOUTONS_MENU, mock.Mock(side_effect=RuntimeError())))

    def test_mots_avant_modele(self):
        appel = mock.Mock()
        self.assertEqual(comprendre("photo", gabarits.BOUTONS_MENU, appel), "photo")
        appel.assert_not_called()


class TestEcoute(unittest.TestCase):
    def test_transcription_et_option(self):
        from bot.langage.comprehension import ecouter
        reponse = {"status": "completed", "steps": [{"type": "model_output", "content": [
            {"type": "text", "text": json.dumps({"transcription": "Mon champ est à Korhogo", "option": "korhogo"})}]}]}
        appel = mock.Mock(return_value=reponse)
        self.assertEqual(ecouter(b"OggS", "audio/ogg; codecs=opus", gabarits.LIGNES_LIEUX, appel),
                         ("Mon champ est à Korhogo", "korhogo"))
        contenu = appel.call_args.args[0]["input"][0]["content"]
        self.assertEqual((contenu[1]["type"], contenu[1]["mime_type"]), ("audio", "audio/ogg"))
        self.assertIs(appel.call_args.args[0]["store"], False)

    def test_panne(self):
        from bot.langage.comprehension import ecouter
        self.assertIsNone(ecouter(b"OggS", "audio/ogg", {}, mock.Mock(side_effect=RuntimeError())))


class TestChoixADire(unittest.TestCase):
    def test_choix_lus(self):
        self.assertEqual(gabarits.choix_a_dire(gabarits.BOUTONS_PRIORITE),
                         "Vous pouvez répondre en disant, Eau, Débouché, ou Sol.")


if __name__ == "__main__":
    unittest.main()

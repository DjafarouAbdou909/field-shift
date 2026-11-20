import unittest
from unittest import mock

from bot.langage import gabarits
from bot.langage.comprehension import comprendre, par_les_mots


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


class TestComprendre(unittest.TestCase):
    def test_mots_avant_groq(self):
        generation = mock.Mock()
        with mock.patch.dict("os.environ", {"GROQ_API_KEY": "g"}):
            self.assertEqual(comprendre("photo", gabarits.BOUTONS_MENU, generation), "photo")
        generation.assert_not_called()

    def test_groq_en_dernier_recours(self):
        generation = mock.Mock(return_value={"option": "korhogo"})
        with mock.patch.dict("os.environ", {"GROQ_API_KEY": "g"}):
            self.assertEqual(comprendre("mon chat est à côté du robot", gabarits.LIGNES_LIEUX, generation), "korhogo")

    def test_sans_groq(self):
        with mock.patch.dict("os.environ", {"GROQ_API_KEY": ""}):
            self.assertIsNone(comprendre("mon chat est à côté du robot", gabarits.LIGNES_LIEUX))


class TestChoixADire(unittest.TestCase):
    def test_choix_lus(self):
        self.assertEqual(gabarits.choix_a_dire(gabarits.BOUTONS_PRIORITE),
                         "Dites simplement Assez d'eau, Bien vendre ou Enrichir la terre.")


if __name__ == "__main__":
    unittest.main()

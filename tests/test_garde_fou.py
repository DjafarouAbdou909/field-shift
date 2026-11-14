import unittest

from bot.langage.gabarits import resume
from bot.langage.garde_fou import ecarts, message_fidele, texte_sur
from moteur import charger_exemple


class TestGardeFou(unittest.TestCase):
    def setUp(self):
        self.reco = charger_exemple()

    def test_gabarit_toujours_fidele(self):
        texte = resume(self.reco)
        self.assertEqual(ecarts(texte, self.reco), [])

    def test_chiffres_du_moteur_acceptes(self):
        self.assertTrue(message_fidele("La saison démarre 11 jours plus tard, entre 4 et 18 jours.", self.reco))
        self.assertTrue(message_fidele("La pluie est de 980 mm.", self.reco))

    def test_chiffre_invente_refuse(self):
        self.assertFalse(message_fidele("Votre rendement augmentera de 35 %.", self.reco))
        self.assertFalse(message_fidele("La pluie est de 980,5 mm.", self.reco))

    def test_culture_inventee_refusee(self):
        self.assertFalse(message_fidele("Essayez plutôt le manioc.", self.reco))
        self.assertTrue(message_fidele("Le niebe enrichit le sol.", self.reco))

    def test_secours_si_texte_infidele(self):
        self.assertEqual(texte_sur("Gagnez 7 tonnes de plus.", self.reco, "secours"), "secours")
        self.assertEqual(texte_sur(None, self.reco, "secours"), "secours")
        self.assertEqual(texte_sur("Le sorgho résiste mieux.", self.reco, "secours"), "Le sorgho résiste mieux.")

    def test_limite_connue_petits_entiers(self):
        """Limite documentée, le contrôle vérifie la présence d'un nombre, pas son sens.

        2 figure parmi les scores, donc une phrase fausse qui l'utilise passe. À renforcer
        en contrôlant les couples nombre et unité.
        """
        self.assertTrue(message_fidele("Gagnez 2 tonnes de plus.", self.reco))


if __name__ == "__main__":
    unittest.main()

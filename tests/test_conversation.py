import unittest
from unittest import mock

from bot.langage import conversation


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


class TestMemoire(unittest.TestCase):
    def setUp(self):
        conversation.oublier("cle")

    def test_six_echanges_au_plus(self):
        for i in range(10):
            conversation.retenir("cle", f"Q{i}", f"R{i}")
        historique = conversation.historique("cle")
        self.assertEqual(len(historique), 12)
        self.assertEqual(historique[-1], ("AgriBot", "R9"))

    def test_oubli_sur_stop(self):
        conversation.retenir("cle", "Q", "R")
        conversation.oublier("cle")
        self.assertEqual(conversation.historique("cle"), [])

    def test_memoire_expiree(self):
        conversation.retenir("cle", "Q", "R")
        with mock.patch.object(conversation.time, "monotonic", return_value=10 ** 9):
            self.assertEqual(conversation.historique("cle"), [])

    def test_consigne(self):
        for regle in ("vouvoyant", "Ne nomme jamais de produit", "jamais en son nom", "Ne prédis aucun rendement"):
            self.assertIn(regle, conversation.CONSIGNE)


if __name__ == "__main__":
    unittest.main()

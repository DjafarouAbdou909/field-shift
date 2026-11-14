import unittest

from moteur.contrat import MESSAGES_DIAGNOSTIC, Diagnostic
from moteur.maladies import HORS_MODELE, MALADIES, liste, source_maladie


class TestMaladies(unittest.TestCase):
    def test_quatre_maladies_sourcees(self):
        """Chaque maladie de la liste fermée cite au moins une source du registre."""
        self.assertEqual(len(MALADIES), 4)
        for nom in MALADIES:
            self.assertTrue(source_maladie(nom).reference)

    def test_listes_par_culture(self):
        self.assertEqual(len(liste("maïs")), 3)
        self.assertEqual(len(liste("coton")), 1)
        self.assertFalse(set(HORS_MODELE) & set(MALADIES))

    def test_un_diagnostic_peut_citer_chaque_maladie(self):
        for nom, maladie in MALADIES.items():
            Diagnostic(donnees_fictives=False, culture=maladie["culture"], statut="maladie_possible", maladie=nom,
                       confiance=0.9, liste=liste(maladie["culture"]), source_maladie=source_maladie(nom),
                       origine_images="essai", avertissement=MESSAGES_DIAGNOSTIC["maladie_possible"])


if __name__ == "__main__":
    unittest.main()

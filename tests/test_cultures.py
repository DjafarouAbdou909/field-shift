import unittest

from moteur.cultures import CULTURES, LIGNES_FAO56, duree_cycle


class TestDureesFAO56(unittest.TestCase):
    def test_stades_et_totaux_du_tableau_11(self):
        """Seules les trois lignes signalées par une remarque ont des stades qui ne somment pas au total imprimé."""
        incoherentes = {(l.culture_fao, l.region) for lignes in LIGNES_FAO56.values() for l in lignes
                        if l.initial + l.developpement + l.mi_saison + l.fin != l.total}
        self.assertEqual(incoherentes, {("Sorghum", "USA, Pakis., Med."), ("Sorghum", "Arid Region"),
                                        ("Green gram, cowpeas", "Mediterranean")})

    def test_cultures_du_tableau_connues(self):
        self.assertTrue(set(LIGNES_FAO56) <= set(CULTURES))

    def test_regle_de_choix(self):
        """Valeurs attendues lues dans le tableau 11 et calculées à la main selon la règle du module."""
        attendus = {
            "coton": (195, 180, 225, "lignes reste de l'Afrique"),
            "maïs": (125, 125, 180, "lignes Afrique de l'Ouest"),
            "sorgho": (135, 130, 140, "médiane de toutes les lignes"),
            "mil": (123, 105, 140, "médiane de toutes les lignes"),
            "arachide": (130, 130, 140, "lignes Afrique de l'Ouest"),
            "niébé": (110, 110, 110, "médiane de toutes les lignes"),
            "soja": (85, 85, 150, "lignes tropiques"),
            "riz pluvial": (165, 150, 180, "lignes tropiques"),
        }
        for culture, (jours, bas, haut, regle) in attendus.items():
            duree = duree_cycle(culture)
            self.assertEqual((duree.jours, duree.bas, duree.haut, duree.regle), (jours, bas, haut, regle), culture)
            self.assertEqual(duree.niveau, "hypothese")

    def test_culture_absente_du_tableau(self):
        for culture in ["igname", "mucuna"]:
            duree = duree_cycle(culture)
            self.assertIsNone(duree.jours)
            self.assertEqual(duree.niveau, "hypothese")
            self.assertEqual(duree.lignes, ())


if __name__ == "__main__":
    unittest.main()

import unittest

import json

import numpy as np

from moteur.cultures import (CULTURES, avec_stades_coton, variantes_duree_coton, KC_FAO56, LIGNES_FAO56, courbe_kc, courbes_kc_comparees, cultures_comparees,
                             duree_cycle, mi_saisons_comparees, semis_coton, tableau_cultures)
from moteur.recommander import EXEMPLE


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
        """Lignes lues dans le tableau 11, ligne médiane choisie à la main, la plus courte si le nombre est pair."""
        attendus = {
            "coton": (195, 180, 225, "Egypt; Pakistan; Calif.", (30, 50, 60, 55)),
            "maïs": (125, 125, 180, "Nigeria (humid)", (20, 35, 40, 30)),
            "sorgho": (130, 130, 140, "USA, Pakis., Med.", (20, 35, 40, 35)),
            "mil": (105, 105, 140, "Pakistan", (15, 25, 40, 25)),
            "arachide": (130, 130, 140, "West Africa", (25, 35, 45, 25)),
            "niébé": (110, 110, 110, "Mediterranean", (20, 30, 30, 30)),
            "soja": (85, 85, 150, "Tropics", (15, 15, 40, 15)),
            "riz pluvial": (150, 150, 180, "Tropics; Mediterranean", (30, 30, 60, 30)),
        }
        for culture, (jours, bas, haut, region, stades) in attendus.items():
            duree = duree_cycle(culture)
            self.assertEqual((duree.jours, duree.bas, duree.haut, duree.ligne.region), (jours, bas, haut, region), culture)
            self.assertEqual(duree.stades(), stades, culture)
            self.assertEqual(sum(duree.stades()), jours, culture)
            self.assertEqual(duree.niveau, "hypothese")

    def test_culture_absente_du_tableau(self):
        for culture in ["igname", "mucuna"]:
            duree = duree_cycle(culture)
            self.assertIsNone(duree.jours)
            self.assertEqual(duree.niveau, "hypothese")
            self.assertIsNone(duree.ligne)


class TestCoefficientCultural(unittest.TestCase):
    def test_exemple_28_fao56(self):
        """Haricot sec, stades 25, 25, 30 et 20 jours, Kc 0,15, 1,19 et 0,35, Kc publiés 0,15, 0,77, 1,19 et 0,56."""
        kc = courbe_kc((25, 25, 30, 20), 0.15, 1.19, 0.35)
        self.assertEqual(len(kc), 100)
        for jour, attendu in [(20, 0.15), (40, 0.77), (70, 1.19), (95, 0.56)]:
            self.assertAlmostEqual(kc[jour - 1], attendu, places=2)

    def test_coefficients_du_tableau_12(self):
        """Kc ini du groupe, milieu des plages imprimées, coton 1,175 à mi-saison et 0,60 en fin."""
        for culture, attendu in [("coton", (0.35, 1.175, 0.60)), ("maïs", (0.3, 1.20, 0.475))]:
            for valeur, cible in zip(KC_FAO56[culture].reference(), attendu):
                self.assertAlmostEqual(valeur, cible)
        self.assertEqual(KC_FAO56["arachide"].ini, 0.4)

    def test_courbes_et_tableau(self):
        courbes = courbes_kc_comparees()
        self.assertEqual(list(courbes), cultures_comparees())
        self.assertEqual(len(courbes["coton"]), 195)
        tableau = {ligne["culture"]: ligne for ligne in tableau_cultures()}
        self.assertEqual(tableau["mil"]["durée"], 105)
        self.assertEqual(tableau["mil"]["ligne du tableau 11"], "Pakistan")
        self.assertIsNone(tableau["igname"]["durée"])

    def test_mi_saison_d_apres_les_stades(self):
        """Coton 30, 50, 60 et 55 jours, mi-saison du jour 81 au jour 140. Niébé 20, 30, 30 et 30, du jour 51 au jour 80."""
        mi_saisons = mi_saisons_comparees()
        self.assertEqual(mi_saisons["coton"], (81, 140))
        self.assertEqual(mi_saisons["niébé"], (51, 80))

    def test_semis_du_coton_selon_gnapi_2025(self):
        """Fenêtres du 1er au 30 juin au nord et du 11 juin au 10 juillet au sud, milieux le 15 et le 25 juin."""
        self.assertEqual(semis_coton("korhogo"), {"coton": "06-15"})
        self.assertEqual(semis_coton("bouake"), {"coton": "06-25"})
        self.assertEqual(semis_coton("bouake", "debut"), {"coton": "06-11"})
        self.assertEqual(semis_coton("bouake", "fin"), {"coton": "07-10"})

    def test_variantes_de_duree_du_coton(self):
        """Texas 30, 50, 55, 45. Calif. Desert 45, 90, 45, 45. Hypothèse 150 jours, 30, 50 et 60 fois 150/195,
        arrondis à 23, 38 et 46, la fin complétant à 150, 43.
        """
        variantes = variantes_duree_coton()
        self.assertEqual(variantes["fao56_texas_180"], (30, 50, 55, 45))
        self.assertEqual(variantes["fao56_californie_225"], (45, 90, 45, 45))
        self.assertEqual(variantes["hypothese_150"], (23, 38, 46, 43))
        courbes, mi_saisons = avec_stades_coton(variantes["hypothese_150"])
        self.assertEqual(len(courbes["coton"]), 150)
        self.assertEqual(mi_saisons["coton"], (62, 107))
        self.assertEqual(len(courbes["maïs"]), 125)

    def test_igname_et_mucuna_hors_comparaison(self):
        comparees = cultures_comparees()
        self.assertEqual(comparees, ["coton", "maïs", "sorgho", "mil", "arachide", "niébé", "soja", "riz pluvial"])
        self.assertTrue(all(len(courbe_kc(duree_cycle(c).stades(), *KC_FAO56[c].reference())) == duree_cycle(c).jours
                            for c in comparees))

    def test_strategies_de_l_exemple_restent_comparables(self):
        """Les trois stratégies de l'exemple n'utilisent ni igname ni mucuna."""
        strategies = json.loads(EXEMPLE.read_text(encoding="utf-8"))["strategies"]
        self.assertGreaterEqual(len(strategies), 3)
        for strategie in strategies:
            self.assertTrue(set(strategie["cultures"]) <= set(cultures_comparees()), strategie["id"])


if __name__ == "__main__":
    unittest.main()

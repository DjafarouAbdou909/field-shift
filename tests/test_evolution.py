import unittest

import numpy as np
import pandas as pd

from moteur import evolution


def serie(valeurs_avant, valeurs_apres):
    return pd.Series(list(valeurs_avant) + list(valeurs_apres), index=range(2001, 2001 + len(valeurs_avant) + len(valeurs_apres)))


class TestEvolution(unittest.TestCase):
    def test_ecart_solide(self):
        r = evolution.comparer(serie(np.full(12, 90.0) + np.arange(12) % 3, np.full(13, 112.0) + np.arange(13) % 3))
        self.assertAlmostEqual(r["ecart"], 22.0, delta=1)
        self.assertTrue(r["solide"])
        self.assertLess(r["p_mann_kendall"], 0.05)

    def test_sans_changement(self):
        """Les mêmes valeurs dans les deux périodes, dans un autre ordre, ne font pas un changement."""
        valeurs = [88, 95, 102, 91, 110, 99, 85, 104, 97, 93, 108, 100]
        r = evolution.comparer(serie(valeurs, list(reversed(valeurs)) + [96]))
        self.assertFalse(r["solide"])

    def test_confirmation_exige_deux_sources_d_accord(self):
        plus_tard = {"solide": True, "ecart": 22.0}
        self.assertTrue(evolution.confirme(plus_tard, {"solide": True, "ecart": 10.0}))
        self.assertFalse(evolution.confirme(plus_tard, {"solide": True, "ecart": -22.0}), "sources contraires")
        self.assertFalse(evolution.confirme(plus_tard, {"solide": False, "ecart": 20.0}), "contrôle non solide")

    def test_reproductible(self):
        s = serie(range(12), range(10, 23))
        self.assertEqual(evolution.comparer(s), evolution.comparer(s))


class TestEvolutionSurDonneesReelles(unittest.TestCase):
    def test_korhogo_sources_contraires_rien_n_est_annonce(self):
        """Constat du 15 novembre 2026, IMERG et MERRA-2 donnent des tendances opposées pour le début des pluies."""
        table = evolution.evolution_du_lieu("korhogo")
        imerg = table.loc["début des pluies, jour de l'année, IMERG"]
        merra = table.loc["début des pluies, jour de l'année, MERRA-2"]
        self.assertTrue(imerg["solide"] and imerg["ecart"] > 0)
        self.assertTrue(merra["ecart"] < 0)
        self.assertFalse(table.attrs["debut_confirme"])
        self.assertEqual(evolution.changements_confirmes("korhogo"), [])


if __name__ == "__main__":
    unittest.main()

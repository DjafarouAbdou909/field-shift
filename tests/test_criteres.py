import unittest

import pandas as pd

from moteur import criteres
from moteur.contrat import Poids
from moteur.criteres import (Contexte, Evaluation, evaluer, scores_criteres, sensibilite, tableau_scenarios,
                             tableau_scores)
from moteur.rotations import Strategie

COTON_MAIS = Strategie("coton_mais", "Coton puis maïs", ("coton", "maïs"), True)
COTON_NIEBE_MAIS = Strategie("coton_niebe_mais", "Coton, niébé puis maïs", ("coton", "niébé", "maïs"), False)
POIDS_EAU = Poids(eau=0.6, revenu=0.2, sol=0.2)


def cycles(ecarts: dict[str, list[float]], besoins: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame([{"culture": c, "annee": 2001 + k, "pluie_moins_etc_mm": e, "etc_cycle_mm": besoins[c]}
                         for c, valeurs in ecarts.items() for k, e in enumerate(valeurs)])


REFERENCE = Contexte("essai", "reference", cycles(
    {"coton": [10, -5, 20, 30], "maïs": [5, 5, -1, 8], "niébé": [1, 2, 3, 4]},
    {"coton": 505.0, "maïs": 400.0, "niébé": 300.0}))


class TestCriteres(unittest.TestCase):
    def test_indicateurs_coton_mais(self):
        """Couverture 3/4 pour le coton et le maïs, score 3,75. Besoin 452,5 mm entre 300 et 505, score 5 fois 52,5/205.

        Aucune légumineuse, sol 0. Coton une année sur deux, revenu 2,5.
        """
        evaluations = {e.indicateur: e for e in evaluer(COTON_MAIS, REFERENCE)}
        self.assertAlmostEqual(evaluations["couverture_du_besoin"].score, 3.75)
        self.assertAlmostEqual(evaluations["besoin_en_eau"].valeur, 452.5)
        self.assertAlmostEqual(evaluations["besoin_en_eau"].score, 5 * 52.5 / 205)
        self.assertEqual(evaluations["part_de_legumineuses"].score, 0)
        self.assertEqual(evaluations["part_de_culture_de_rente"].score, 2.5)
        self.assertEqual(evaluations["couverture_du_besoin"].niveau, "calcule")
        self.assertEqual(evaluations["part_de_culture_de_rente"].niveau, "hypothese")

    def test_note_et_rang(self):
        """Coton, niébé, maïs, eau (5 fois 5/6 + 5 fois 103,33/205) / 2, sol et revenu 5/3.

        Note 0,6 fois 3,3435 + 0,2 fois 5/3 + 0,2 fois 5/3 = 2,6728, contre 2,0091 pour coton puis maïs.
        """
        table = tableau_scores([COTON_MAIS, COTON_NIEBE_MAIS], REFERENCE, POIDS_EAU)
        self.assertEqual(list(table.index), ["coton_niebe_mais", "coton_mais"])
        self.assertAlmostEqual(table.loc["coton_niebe_mais", "note"], 0.6 * (25 / 6 + 5 * (505 - 1205 / 3) / 205) / 2
                               + 0.2 * 5 / 3 + 0.2 * 5 / 3)
        self.assertAlmostEqual(table.loc["coton_mais", "note"], 0.6 * (3.75 + 5 * 52.5 / 205) / 2 + 0.2 * 2.5)
        self.assertEqual(table.loc["coton_niebe_mais", "rang"], 1)

    def test_indicateur_sans_donnees_ignore(self):
        """Un indicateur futur qui retourne None ne change pas le score du critère."""
        avant = scores_criteres(evaluer(COTON_MAIS, REFERENCE))
        futur = lambda strategie, contexte: contexte.surfaces.get("smap") and Evaluation(
            "eau", "smap", "", 0, "", 0, "mesure", "SMAP")
        criteres.INDICATEURS["eau"].append(futur)
        try:
            self.assertEqual(scores_criteres(evaluer(COTON_MAIS, REFERENCE)), avant)
        finally:
            criteres.INDICATEURS["eau"].remove(futur)

    def test_valeurs_par_scenario(self):
        """Couverture de coton puis maïs, 3/4 en référence et 1 dans le scénario où toutes les années couvrent le besoin."""
        humide = Contexte("essai", "humide", cycles({"coton": [1, 1], "maïs": [1, 1], "niébé": [1, 1]},
                                                    {"coton": 505.0, "maïs": 400.0, "niébé": 300.0}))
        table = tableau_scenarios([COTON_MAIS], {"reference": REFERENCE, "humide": humide})
        self.assertEqual(table.loc[("coton_mais", "couverture_du_besoin"), "reference"], 0.75)
        self.assertEqual(table.loc[("coton_mais", "couverture_du_besoin"), "humide"], 1.0)

    def test_scenario_qui_change_le_classement(self):
        """Poids 0,8, 0,1 et 0,1. Référence, coton puis maïs 0,8 fois 2,5152 + 0,25 = 2,262, l'autre 3,008.

        Scénario sec, le niébé ne couvre plus son besoin. Eau de coton puis maïs (5 + 1,2805) / 2 = 3,140, note
        2,762. Eau de l'autre (10/3 + 2,5203) / 2 = 2,927, note 2,342 + 0,333 = 2,675. Le classement s'inverse.
        """
        sec = Contexte("essai", "sec", cycles(
            {"coton": [10, 5, 20, 30], "maïs": [5, 5, 1, 8], "niébé": [-1, -2, -3, -4]},
            {"coton": 505.0, "maïs": 400.0, "niébé": 300.0}))
        rangs, stable, changeants = sensibilite([COTON_MAIS, COTON_NIEBE_MAIS],
                                                {"reference": REFERENCE, "sec": sec},
                                                Poids(eau=0.8, revenu=0.1, sol=0.1))
        self.assertFalse(stable)
        self.assertEqual(changeants, ["sec"])
        self.assertEqual(rangs.loc["coton_mais", "sec"], 1)


if __name__ == "__main__":
    unittest.main()

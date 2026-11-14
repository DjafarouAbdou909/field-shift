import unittest

import pandas as pd

from moteur import criteres
from moteur.contrat import Poids
from moteur.criteres import (Contexte, Evaluation, comparer_semis, evaluer, intervalle_annees, parts_par_culture, scores_criteres,
                             sensibilite,
                             tableau_scenarios, tableau_scores)
from moteur.rotations import Strategie

COTON_MAIS = Strategie("coton_mais", "Coton puis maïs", ("coton", "maïs"), True)
COTON_NIEBE_MAIS = Strategie("coton_niebe_mais", "Coton, niébé puis maïs", ("coton", "niébé", "maïs"), False)
POIDS_EAU = Poids(eau=0.6, revenu=0.2, sol=0.2)


def cycles(ecarts: dict[str, list[float]], secheresses: dict[str, list[float]] | None = None) -> pd.DataFrame:
    lignes = []
    for culture, valeurs in ecarts.items():
        for k, ecart in enumerate(valeurs):
            ligne = {"culture": culture, "annee": 2001 + k, "pluie_moins_etc_mm": ecart}
            if secheresses:
                ligne["sequence_seche_mi_saison_jours"] = secheresses[culture][k]
            lignes.append(ligne)
    return pd.DataFrame(lignes)


REFERENCE = Contexte("essai", "reference", cycles({"coton": [10, -5, 20, 30], "maïs": [5, 5, -1, 8],
                                                   "niébé": [1, 2, 3, 4]}))


class TestCriteres(unittest.TestCase):
    def test_couverture_annee_par_annee(self):
        """Coton couvert en 2001, 2003 et 2004, maïs en 2001, 2002 et 2004.

        Parts annuelles de coton puis maïs 1, 1/2, 1/2 et 1, moyenne 3/4, score 3,75. Aucune légumineuse,
        azote 0. Coton une année sur deux, débouché 2,5.
        """
        evaluations = {e.indicateur: e for e in evaluer(COTON_MAIS, REFERENCE)}
        self.assertAlmostEqual(evaluations["couverture_du_besoin"].valeur, 0.75)
        self.assertAlmostEqual(evaluations["couverture_du_besoin"].score, 3.75)
        self.assertNotIn("secheresse_mi_saison", evaluations)
        self.assertEqual(evaluations["apport_azote_legumineuses"].score, 0)
        self.assertEqual(evaluations["acces_debouche_organise"].score, 2.5)
        self.assertEqual(evaluations["acces_debouche_organise"].source, "ZAGBAI2006")
        self.assertEqual(evaluations["couverture_du_besoin"].niveau, "calcule")

    def test_secheresse_mi_saison(self):
        """Seuil de 7 jours. Coton 5, 9, 7 et 3 jours, maïs 8, 2, 2 et 2 jours.

        Parts annuelles sans séquence de plus de 7 jours 1/2, 1/2, 1 et 1, moyenne 3/4.
        """
        contexte = Contexte("essai", "reference", cycles({"coton": [1, 1, 1, 1], "maïs": [1, 1, 1, 1]},
                                                         {"coton": [5, 9, 7, 3], "maïs": [8, 2, 2, 2]}))
        evaluations = {e.indicateur: e for e in evaluer(COTON_MAIS, contexte)}
        self.assertAlmostEqual(evaluations["secheresse_mi_saison"].valeur, 0.75)
        self.assertAlmostEqual(scores_criteres(evaluer(COTON_MAIS, contexte))["eau"], (5 + 3.75) / 2)

    def test_parts_par_culture(self):
        """Coton 5, 9, 7 et 3 jours, trois années sur quatre sans séquence de plus de 7 jours, médiane 6."""
        contexte = Contexte("essai", "reference", cycles({"coton": [1, -1, 1, 1]}, {"coton": [5, 9, 7, 3]}))
        table = parts_par_culture(contexte)
        self.assertEqual(table.loc["coton", "couverture_du_besoin"], 0.75)
        self.assertEqual(table.loc["coton", "sans_secheresse_mi_saison"], 0.75)
        self.assertEqual(table.loc["coton", "sequence_seche_mi_saison_mediane_jours"], 6.0)

    def test_intervalle_par_reechantillonnage(self):
        constante = pd.Series([0.5] * 10)
        self.assertEqual(intervalle_annees(constante), (0.5, 0.5))
        valeurs = pd.Series([0.0, 1.0] * 10)
        bas, haut = intervalle_annees(valeurs)
        self.assertLess(bas, 0.5)
        self.assertGreater(haut, 0.5)
        self.assertEqual(intervalle_annees(valeurs), (bas, haut))

    def test_note_et_rang(self):
        """Coton, niébé puis maïs, parts annuelles 1, 2/3, 2/3 et 1, eau 5 fois 5/6, azote et débouché 5/3.

        Note 0,6 fois 25/6 + 0,4 fois 5/3 = 3,1667, contre 0,6 fois 3,75 + 0,2 fois 2,5 = 2,75 pour coton puis maïs.
        """
        table = tableau_scores([COTON_MAIS, COTON_NIEBE_MAIS], REFERENCE, POIDS_EAU)
        self.assertEqual(list(table.index), ["coton_niebe_mais", "coton_mais"])
        self.assertAlmostEqual(table.loc["coton_niebe_mais", "note"], 0.6 * 25 / 6 + 0.4 * 5 / 3)
        self.assertAlmostEqual(table.loc["coton_mais", "note"], 2.75)

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
        humide = Contexte("essai", "humide", cycles({"coton": [1, 1], "maïs": [1, 1], "niébé": [1, 1]}))
        table = tableau_scenarios([COTON_MAIS], {"reference": REFERENCE, "humide": humide})
        self.assertEqual(table.loc[("coton_mais", "couverture_du_besoin"), "reference"], 0.75)
        self.assertEqual(table.loc[("coton_mais", "couverture_du_besoin"), "humide"], 1.0)

    def test_comparer_semis(self):
        """Semis au début des pluies, coton couvert 3 années sur 4. Semis tardif, coton couvert les 4 années."""
        tardif = Contexte("essai", "reference", cycles({"coton": [1, 1, 1, 1], "maïs": [5, 5, -1, 8],
                                                         "niébé": [1, 2, 3, 4]}))
        rangs, coton = comparer_semis([COTON_MAIS, COTON_NIEBE_MAIS],
                                      {"debut_des_pluies": {"reference": REFERENCE}, "tardif": {"reference": tardif}})
        self.assertEqual(coton.loc["couverture_du_besoin", "debut_des_pluies"], 0.75)
        self.assertEqual(coton.loc["couverture_du_besoin", "tardif"], 1.0)
        self.assertEqual(set(rangs.columns.get_level_values(1)), {"debut_des_pluies", "tardif"})
        self.assertTrue(pd.isna(coton.loc["sans_secheresse_mi_saison", "tardif"]))

    def test_scenario_qui_change_le_classement(self):
        """Poids 0,8, 0,1 et 0,1. Référence, coton puis maïs 0,8 fois 3,75 + 0,25 = 3,25, l'autre 3,667.

        Scénario sec, le niébé ne couvre jamais son besoin. Coton puis maïs 0,8 fois 5 + 0,25 = 4,25, l'autre
        0,8 fois 10/3 + 1/3 = 3,0. Le classement s'inverse.
        """
        sec = Contexte("essai", "sec", cycles({"coton": [10, 5, 20, 30], "maïs": [5, 5, 1, 8],
                                               "niébé": [-1, -2, -3, -4]}))
        rangs, stable, changeants = sensibilite([COTON_MAIS, COTON_NIEBE_MAIS],
                                                {"reference": REFERENCE, "sec": sec},
                                                Poids(eau=0.8, revenu=0.1, sol=0.1))
        self.assertFalse(stable)
        self.assertEqual(changeants, ["sec"])
        self.assertEqual(rangs.loc["coton_mais", "sec"], 1)


if __name__ == "__main__":
    unittest.main()

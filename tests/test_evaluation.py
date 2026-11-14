import unittest

import pandas as pd

from moteur import charger_exemple
from moteur.evaluation import bon_sens_cultures, bon_sens_strategies, classements, scores_publies, verifier_contrat


class TestEvaluation(unittest.TestCase):
    def test_exemple_fictif_signale(self):
        """L'exemple porte des données fictives et un classement instable sans scénario nommé."""
        conformite = verifier_contrat(charger_exemple())
        self.assertFalse(conformite["donnees_reelles"])
        self.assertFalse(conformite["instabilite_nommee"])
        self.assertTrue(conformite["au_moins_trois_strategies"])
        self.assertTrue(conformite["mesure_et_calcule_sources"])

    def test_bon_sens_sur_les_scores(self):
        """Dans l'exemple, azote 3 et 3 avec légumineuse contre 1 sans, eau 4 pour sorgho puis niébé contre 2."""
        lignes = {l["verification"][:30]: l for l in bon_sens_strategies(charger_exemple())}
        self.assertTrue(all(l["resultat"] for l in lignes.values()))
        self.assertIn("sans [1.0]", next(l["valeurs"] for l in lignes.values() if "azote" in l["verification"]))

    def test_bon_sens_par_culture(self):
        """Mil couvert 0,9 des années contre 0,96 pour le maïs, la vérification de couverture du mil échoue."""
        parts = pd.DataFrame({"couverture_du_besoin": [0.96, 1.0, 0.9]}, index=["maïs", "sorgho", "mil"])
        besoins = pd.Series({"maïs": 480.0, "sorgho": 450.0, "mil": 380.0})
        resultats = {l["verification"]: l["resultat"] for l in bon_sens_cultures(parts, besoins)}
        self.assertTrue(resultats["le sorgho demande moins d'eau que le maïs sur son cycle"])
        self.assertTrue(resultats["la pluie couvre le besoin du sorgho au moins aussi souvent que celui du maïs"])
        self.assertFalse(resultats["la pluie couvre le besoin du mil au moins aussi souvent que celui du maïs"])

    def test_scores_publies(self):
        table = scores_publies({"exemple": charger_exemple()})
        self.assertEqual(table.loc["sorgho_niebe", ("exemple", "eau")], 4.0)
        self.assertEqual(table.loc["coton_mais", ("exemple", "sol")], 1.0)

    def test_classements(self):
        reco = charger_exemple()
        table = classements({"a": reco})
        self.assertEqual(table.loc["sorgho_niebe", "a"], 1)
        self.assertEqual(table.loc["coton_mais", "a"], 3)


if __name__ == "__main__":
    unittest.main()

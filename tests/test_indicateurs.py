import unittest

import numpy as np
import pandas as pd

from moteur.indicateurs import (RegleSaison, debut_saison, evapotranspiration_reference, evapotranspiration_serie,
                                indicateurs_annuels, indicateurs_cycle, mann_kendall, pente_theil_sen,
                                plus_longue_sequence_seche, pression_saturante, rayonnement_extraterrestre,
                                troncature_debut)


def annee_synthetique() -> tuple[pd.Series, pd.DataFrame]:
    """Pluie et météo de 2021 et de janvier 2022, construites pour être suivies à la main.

    Faux départ de 21 mm du 10 au 12 mai, suivi de 19 jours secs. Vrai départ de 24 mm
    du 1er au 3 juin, puis 2 mm tous les cinq jours du 8 juin au 27 août, 17 jours. Pluie
    de 2 mm les 5 et 10 septembre, puis 3 mm le 15 octobre. Chaleur de 36 °C le 5 juin et
    le 1er décembre, 30 °C les autres jours.
    """
    dates = pd.date_range("2021-01-01", "2022-01-31", freq="D")
    pluie = pd.Series(0.0, index=dates)
    pluie.loc[["2021-05-10", "2021-05-11", "2021-05-12"]] = [10.0, 6.0, 5.0]
    pluie.loc[["2021-06-01", "2021-06-02", "2021-06-03"]] = 8.0
    pluie.loc[pd.date_range("2021-06-08", "2021-08-27", freq="5D")] = 2.0
    pluie.loc[["2021-09-05", "2021-09-10"]] = 2.0
    pluie.loc["2021-10-15"] = 3.0
    meteo = pd.DataFrame({"T2M_MAX": 30.0, "T2M_MIN": 20.0, "T2MDEW": 15.0, "ALLSKY_SFC_SW_DWN": 20.0,
                          "WS2M": 2.0}, index=dates)
    meteo.loc[["2021-06-05", "2021-12-01"], "T2M_MAX"] = 36.0
    return pluie, meteo


class TestFAO56(unittest.TestCase):
    def test_rayonnement_extraterrestre_exemple_8(self):
        """Exemple 8 du bulletin FAO-56, 3 septembre, jour 246, à 20 degrés sud, 32,2 MJ par m²."""
        self.assertAlmostEqual(rayonnement_extraterrestre(-20.0, 246), 32.2, delta=0.1)

    def test_evapotranspiration_exemple_18(self):
        """Exemple 18 du bulletin FAO-56, Bruxelles le 6 juillet, 3,9 mm par jour.

        La pression de vapeur réelle de 1,409 kPa de l'exemple est convertie en point de rosée.
        """
        tdew = 237.3 * np.log(1.409 / 0.6108) / (17.27 - np.log(1.409 / 0.6108))
        self.assertAlmostEqual(pression_saturante(tdew), 1.409, places=4)
        et0 = evapotranspiration_reference(21.5, 12.3, tdew, 22.07, 2.078, 50.8, 100, 187)
        self.assertAlmostEqual(et0, 3.9, delta=0.05)


class TestSaison(unittest.TestCase):
    def setUp(self):
        self.pluie, self.meteo = annee_synthetique()

    def test_plus_longue_sequence_seche(self):
        self.assertEqual(plus_longue_sequence_seche(np.array([0.0, 0.5, 3.0, 0.0, 0.0, 0.0, 1.0, 0.9])), 3)
        self.assertEqual(plus_longue_sequence_seche(np.array([2.0, 1.0])), 0)

    def test_debut_ecarte_le_faux_depart(self):
        """Le 10 mai ouvre 21 mm mais 19 jours secs suivent. Le 1er juin, 24 mm et au plus 4 jours secs."""
        self.assertEqual(RegleSaison().recherche_debut, "03-01")
        self.assertEqual(debut_saison(self.pluie, 2021), pd.Timestamp("2021-06-01"))
        self.assertTrue(pd.isna(debut_saison(self.pluie, 2021, RegleSaison(recherche_debut="06-02"))))

    def test_indicateurs_annuels(self):
        """Pluie annuelle 21 + 24 + 17 fois 2 + 2 fois 2 + 3 = 86 mm, début le 1er juin, jour 152.

        Séquence sèche des 60 premiers jours de 4 jours. 2022 n'a que janvier et n'est pas retenue.
        """
        table = indicateurs_annuels(self.pluie, self.meteo, 9.458, 350.0)
        self.assertEqual(list(table.index), [2021])
        ligne = table.loc[2021]
        self.assertEqual(ligne["debut_jour"], 152)
        self.assertEqual(ligne["pluie_annuelle_mm"], 86.0)
        self.assertEqual(ligne["sequence_seche_debut_jours"], 4)
        self.assertAlmostEqual(ligne["indice_aridite"], 86.0 / ligne["et0_annuelle_mm"])
        self.assertNotIn("jours_35_annee", table.columns)

    def test_cycle_de_dix_jours(self):
        """Du 1er au 10 juin, pluie 3 fois 8 + 2 = 26 mm, température maximale (9 fois 30 + 36) / 10 = 30,6 °C.

        Plus longue séquence sèche du 4 au 7 juin, 4 jours.
        """
        et0 = evapotranspiration_serie(self.meteo, 9.458, 350.0)
        cycle = indicateurs_cycle(self.pluie, self.meteo["T2M_MAX"], et0, pd.Timestamp("2021-06-01"), 10)
        self.assertEqual(cycle["pluie_cycle_mm"], 26.0)
        self.assertAlmostEqual(cycle["tmax_moyenne_cycle"], 30.6)
        self.assertEqual(cycle["sequence_seche_cycle_jours"], 4)
        self.assertAlmostEqual(cycle["et0_cycle_mm"], et0.loc["2021-06-01":"2021-06-10"].sum())
        self.assertAlmostEqual(cycle["bilan_cycle_mm"], 26.0 - cycle["et0_cycle_mm"])

    def test_cycle_incomplet_ou_sans_debut(self):
        """Un cycle de 20 jours au 20 janvier 2022 dépasse le 31 janvier, fin des séries."""
        et0 = evapotranspiration_serie(self.meteo, 9.458, 350.0)
        for debut in [pd.Timestamp("2022-01-20"), pd.NaT]:
            cycle = indicateurs_cycle(self.pluie, self.meteo["T2M_MAX"], et0, debut, 20)
            self.assertTrue(all(np.isnan(v) for v in cycle.values()))

    def test_troncature_par_la_date_de_recherche(self):
        """Recherche au jour 60. Écarts 0, 2, 10 et 20 jours. Un début témoin au jour 45 précède la recherche."""
        debuts = pd.Series([60, 62, 70, 80, np.nan])
        temoin = pd.Series([45, 62, 70, 80, np.nan])
        resume = troncature_debut(debuts, temoin)
        self.assertEqual(resume["annees"], 4)
        self.assertEqual(resume["debut_le_jour_de_recherche"], 1)
        self.assertEqual(resume["debut_dans_les_7_jours"], 2)
        self.assertEqual(resume["debut_entre_7_et_13_jours"], 1)
        self.assertEqual(resume["debut_temoin_avant_la_recherche"], 1)


class TestTendance(unittest.TestCase):
    def test_pente_theil_sen(self):
        """Pentes -1, 0,5, 1, 4/3, 2 et 3, médiane (1 + 4/3) / 2 = 7/6."""
        self.assertAlmostEqual(pente_theil_sen(np.array([0, 1, 2, 3]), np.array([1.0, 3.0, 2.0, 5.0])), 7 / 6)

    def test_mann_kendall_sans_ex_aequo(self):
        """S = 10, variance 5 fois 4 fois 15 sur 18, z = 9 / 4,0825 = 2,2045, p = 0,0275."""
        s, variance, p = mann_kendall(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        self.assertEqual(s, 10)
        self.assertAlmostEqual(variance, 300 / 18)
        self.assertAlmostEqual(p, 0.0275, delta=0.0003)

    def test_mann_kendall_avec_ex_aequo(self):
        """S = 0 + 1 + 1 = 2, variance (3 fois 2 fois 11 - 2 fois 1 fois 9) / 18 = 48 / 18."""
        s, variance, _ = mann_kendall(np.array([1.0, 1.0, 2.0]))
        self.assertEqual(s, 2)
        self.assertAlmostEqual(variance, 48 / 18)


if __name__ == "__main__":
    unittest.main()

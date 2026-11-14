import csv
import gzip
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from moteur.controles import (comparer_pluies, comparer_station, comparer_tmax_station, controler_serie,
                              ecart_case_moyenne)
from moteur.donnees import (altitude_power, centre_case_imerg, empreinte_sha256, lire_pluie_station, lire_power,
                            lire_tmax_station, nom_fichier, pluie_lieu, reponse_complete, telecharger_point,
                            voisinage_imerg)

ENTETE = "-BEGIN HEADER-\nNASA/POWER\n-END HEADER-\n"
TROIS_JOURS = ENTETE + "YEAR,DOY,IMERG_PRECTOT\n2024,366,1.5\n2025,1,-999\n2025,2,0.0\n"


class TestDonnees(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.chemin = Path(self.dossier.name)

    def tearDown(self):
        self.dossier.cleanup()

    def test_reponse_complete(self):
        self.assertTrue(reponse_complete(TROIS_JOURS, "20241231", "20250102"))
        self.assertFalse(reponse_complete(TROIS_JOURS, "20241231", "20250103"))
        self.assertFalse(reponse_complete("erreur", "20241231", "20250102"))

    def test_lire_power_dates_et_manquants(self):
        fichier = self.chemin / "imerg.csv.gz"
        with gzip.open(fichier, "wt", encoding="utf-8") as sortie:
            sortie.write(TROIS_JOURS)
        serie = lire_power(fichier)
        self.assertEqual(list(serie.index), list(pd.to_datetime(["2024-12-31", "2025-01-01", "2025-01-02"])))
        self.assertTrue(np.isnan(serie.loc["2025-01-01", "IMERG_PRECTOT"]))
        self.assertEqual(serie.loc["2024-12-31", "IMERG_PRECTOT"], 1.5)

    def test_altitude_lue_dans_l_entete(self):
        fichier = self.chemin / "power.csv.gz"
        with gzip.open(fichier, "wt", encoding="utf-8") as sortie:
            sortie.write("-BEGIN HEADER-\nelevation from MERRA-2: Average for 0.5 x 0.625 degree lat/lon region = 351.91 meters\n"
                         "-END HEADER-\nYEAR,DOY,T2M_MAX\n2025,1,30.0\n")
        self.assertEqual(altitude_power(fichier), 351.91)

    def test_pluie_du_lieu_moyenne_des_cases(self):
        """Deux cases, 1 et 3 mm le 31 décembre, moyenne 2 mm. Une case manque le 1er janvier, la moyenne aussi."""
        for case, valeurs in [((9.45, -5.65), ["1.0", "0.0", "0.0"]), ((9.55, -5.65), ["3.0", "-999", "4.0"])]:
            with gzip.open(self.chemin / nom_fichier("imerg", *case), "wt", encoding="utf-8") as sortie:
                sortie.write(ENTETE + "YEAR,DOY,IMERG_PRECTOT\n" + "".join(
                    f"{a},{j},{v}\n" for (a, j), v in zip([(2024, 366), (2025, 1), (2025, 2)], valeurs)))
        pluie = pluie_lieu([(9.45, -5.65), (9.55, -5.65)], self.chemin)
        self.assertEqual(pluie.loc["2024-12-31", "moyenne"], 2.0)
        self.assertTrue(np.isnan(pluie.loc["2025-01-01", "moyenne"]))
        self.assertEqual(pluie.loc["2025-01-02", "moyenne"], 2.0)

    def test_telechargement_retente_puis_consigne(self):
        tronquee = mock.Mock(status_code=200, text=ENTETE + "YEAR,DOY,IMERG_PRECTOT\n2024,366,1.5\n", url="u")
        complete = mock.Mock(status_code=200, text=TROIS_JOURS, url="https://exemple/u")
        registre = self.chemin / "registre.csv"
        with mock.patch("moteur.donnees.requests.get", side_effect=[tronquee, complete]) as appel, \
                mock.patch("moteur.donnees.time.sleep"):
            fichier = telecharger_point(9.45, -5.65, "imerg", self.chemin, registre, "20241231", "20250102")
            self.assertEqual(appel.call_count, 2)
            telecharger_point(9.45, -5.65, "imerg", self.chemin, registre, "20241231", "20250102")
            self.assertEqual(appel.call_count, 2)
        with registre.open(encoding="utf-8") as lecture:
            lignes = list(csv.DictReader(lecture))
        self.assertEqual(len(lignes), 1)
        self.assertEqual(lignes[0]["sha256"], empreinte_sha256(fichier))
        self.assertEqual(lignes[0]["url"], "https://exemple/u")


    def test_station_en_dixiemes_de_mm(self):
        fichier = self.chemin / "station.csv"
        fichier.write_text('"STATION","DATE","PRCP"\n"X","2025-08-01","125"\n"X","2025-08-02",""\n', encoding="utf-8")
        serie = lire_pluie_station(fichier)
        self.assertEqual(len(serie), 1)
        self.assertEqual(serie.loc["2025-08-01"], 12.5)

    def test_temperature_station_en_dixiemes_de_degre(self):
        fichier = self.chemin / "station.csv"
        fichier.write_text('"STATION","DATE","TMAX"\n"X","2025-03-01","362"\n', encoding="utf-8")
        self.assertEqual(lire_tmax_station(fichier).loc["2025-03-01"], 36.2)


class TestControles(unittest.TestCase):
    def test_case_imerg_de_korhogo(self):
        """9,458 est dans la case 9,4 à 9,5 et -5,629 dans la case -5,7 à -5,6."""
        self.assertEqual(centre_case_imerg(9.458, -5.629), (9.45, -5.65))
        voisins = voisinage_imerg(9.458, -5.629)
        self.assertEqual(voisins[0], (9.45, -5.65))
        self.assertEqual(len(set(voisins)), 9)
        self.assertIn((9.35, -5.75), voisins)
        self.assertIn((9.55, -5.55), voisins)

    def test_bornes_physiques(self):
        dates = pd.date_range("2025-01-01", periods=3, freq="D")
        serie = pd.DataFrame({
            "T2M_MAX": [30.0, 30.0, 30.0], "T2M_MIN": [20.0, 31.0, 20.0], "T2MDEW": [15.0, 15.0, 32.0],
            "ALLSKY_SFC_SW_DWN": [20.0, 60.0, -1.0], "PRECTOTCORR": [0.0, 250.0, np.nan],
        }, index=dates)
        resume = controler_serie(serie, 9.458, "2025-01-01", "2025-01-04")
        self.assertEqual(resume["dates_manquantes"], 1)
        self.assertEqual(resume["T2M_MIN supérieur à T2M_MAX"], 1)
        self.assertEqual(resume["T2MDEW supérieur à T2M_MAX"], 1)
        self.assertEqual(resume["ALLSKY_SFC_SW_DWN négatif"], 1)
        self.assertEqual(resume["rayonnement supérieur au rayonnement extraterrestre"], 1)
        self.assertEqual(resume["PRECTOTCORR au-delà de 200 mm"], 1)
        self.assertEqual(resume["PRECTOTCORR manquants"], 1)

    def test_comparaison_des_pluies(self):
        """Cumuls 2024 de 6 et 9 mm, rapport 1,5, corrélation de 1 car 9 = 1,5 fois 6 jour par jour."""
        dates = pd.date_range("2024-12-29", periods=4, freq="D")
        imerg = pd.Series([0.0, 2.0, 4.0, 5.0], index=dates)
        prectotcorr = pd.Series([0.0, 3.0, 6.0, 1.0], index=dates)
        table = comparer_pluies(imerg, prectotcorr)
        self.assertEqual(table.loc[2024, "imerg_mm"], 6.0)
        self.assertEqual(table.loc[2024, "prectotcorr_mm"], 9.0)
        self.assertEqual(table.loc[2024, "rapport"], 1.5)
        self.assertEqual(table.loc[2024, "correlation_journaliere"], 1.0)
        self.assertEqual(table.loc[2025, "rapport"], 0.2)

    def test_ecart_case_moyenne(self):
        """2001, case 110 pour moyenne 100, +10 mm, +10 %. 2013, case 90 pour 100, -10 mm, -10 %."""
        dispersion = pd.DataFrame({"case_du_lieu_mm": [110.0, 90.0], "moyenne_9_cases_mm": [100.0, 100.0]},
                                  index=[2001, 2013])
        table = ecart_case_moyenne(dispersion)
        self.assertEqual(table.loc["2001-2012", "ecart_moyen_pct"], 10.0)
        self.assertEqual(table.loc["2013-2025", "ecart_moyen_mm"], -10.0)
        self.assertEqual(table.loc["2001-2025", "ecart_moyen_pct"], 0.0)
        self.assertEqual(table.loc["2001-2025", "ecart_min_pct"], -10.0)

    def test_temperature_comparee_au_thermometre(self):
        """Trois jours communs, écarts de 1 °C. Au-delà de 35 °C, 35,5 à la station et 36,5 pour MERRA-2, 35,0 ne comptant pas."""
        dates = pd.date_range("2025-03-01", periods=4, freq="D")
        station = pd.Series([34.0, 35.5, 30.0], index=dates[[0, 1, 3]])
        merra = pd.Series([35.0, 36.5, 99.0, 31.0], index=dates)
        resume = comparer_tmax_station(station, merra)
        self.assertEqual(resume["jours_communs"], 3)
        self.assertEqual(resume["ecart_moyen_merra_moins_station"], 1.0)
        self.assertEqual(resume["part_jours_station_au_dela_de_35"], round(1 / 3, 3))
        self.assertEqual(resume["part_jours_merra_au_dela_de_35"], round(1 / 3, 3))

    def test_comparaison_a_la_station_sur_jours_communs(self):
        """La station manque le 2 août et IMERG n'a pas de veille au 1er août, restent les 3 et 4 août.

        Station 2 et 3 mm, IMERG 2 et 3 mm, donc sommes de 5 mm et corrélation de 1.
        """
        dates = pd.date_range("2025-08-01", periods=4, freq="D")
        station = pd.Series([1.0, 2.0, 3.0], index=dates[[0, 2, 3]])
        imerg = pd.Series([9.0, 1.0, 2.0, 3.0], index=dates)
        prectotcorr = pd.Series([4.0, 0.0, 4.0, 5.0], index=dates)
        resume = comparer_station(station, imerg, prectotcorr)
        self.assertEqual(resume["jours_communs"], 2)
        self.assertEqual(resume["somme_station_mm"], 5.0)
        self.assertEqual(resume["somme_imerg_mm"], 5.0)
        self.assertEqual(resume["correlation_station_imerg"], 1.0)


if __name__ == "__main__":
    unittest.main()

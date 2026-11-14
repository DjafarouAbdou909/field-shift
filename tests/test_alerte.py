import unittest

import numpy as np
import pandas as pd

from moteur.alerte import (construire_alerte, dans_la_fenetre, etat_vegetation, observation_claire,
                           observations_claires, requete_hls, taux_d_alertes)


def serie_synthetique(annees=range(2015, 2025), courantes=(0.30, 0.32)) -> pd.Series:
    """Trois observations par année les 10, 15 et 20 août, 0,50 + 0,01 fois le rang de l'année, puis l'année 2025."""
    valeurs = {}
    for rang, annee in enumerate(annees):
        for jour in (10, 15, 20):
            valeurs[pd.Timestamp(f"{annee}-08-{jour}")] = 0.50 + 0.01 * rang
    for jour, valeur in zip((12, 16), courantes):
        valeurs[pd.Timestamp(f"2025-08-{jour}")] = valeur
    return pd.Series(valeurs).sort_index()


class TestMasque(unittest.TestCase):
    def test_bits_de_fmask(self):
        """0 clair, 1 bit réservé clair, 64 aérosols faibles clair. Nuage 2, voisinage 4, ombre 8, neige 16, eau 32
        et aérosols élevés 192 écartés."""
        codes = pd.Series([0, 1, 64, 2, 4, 8, 16, 32, 192])
        self.assertEqual(observation_claire(codes).tolist(), [True, True, True] + [False] * 6)

    def test_observations_claires(self):
        table = pd.DataFrame({"date": ["2025-08-10", "2025-08-11", "2025-08-12", "2025-08-13"],
                              "ndvi": [0.5, -19999.0, 0.6, 0.7], "fmask": [0, 0, 2, np.nan]})
        self.assertEqual(observations_claires(table).tolist(), [0.5])

    def test_fenetre_autour_du_nouvel_an(self):
        dates = pd.DatetimeIndex(["2024-12-30", "2024-12-20", "2025-01-03"])
        self.assertEqual(dans_la_fenetre(dates, pd.Timestamp("2025-01-03"), 8).tolist(), [True, False, True])


class TestEtat(unittest.TestCase):
    def test_vegetation_faible(self):
        """30 observations de référence sur 10 années, 10e centile à la position 2,9, 0,50 + 0,9 fois 0,01 = 0,509.

        Médiane courante (0,30 + 0,32) / 2 = 0,31, sous le seuil.
        """
        etat = etat_vegetation(serie_synthetique(), "2025-08-15")
        self.assertEqual(etat["statut"], "faible")
        self.assertAlmostEqual(etat["seuil"], 0.509)
        self.assertAlmostEqual(etat["valeur"], 0.31)
        self.assertEqual((etat["observations_reference"], etat["annees_reference"]), (30, 10))

    def test_vegetation_normale(self):
        etat = etat_vegetation(serie_synthetique(courantes=(0.60, 0.62)), "2025-08-15")
        self.assertEqual(etat["statut"], "normale")

    def test_indisponible_sous_les_minimums(self):
        """Quatre années de référence seulement, ou 12 observations, ou aucune observation courante."""
        self.assertEqual(etat_vegetation(serie_synthetique(range(2021, 2025)), "2025-08-15")["statut"], "indisponible")
        self.assertEqual(etat_vegetation(serie_synthetique(), "2025-08-15", observations_min=31)["statut"], "indisponible")
        self.assertEqual(etat_vegetation(serie_synthetique(), "2025-06-15")["statut"], "indisponible")

    def test_taux_d_alertes(self):
        """Sur les années de référence elles-mêmes, la plus basse, 2015 à 0,50, passe sous le 10e centile des autres."""
        taux = taux_d_alertes(serie_synthetique(), [f"{a}-08-15" for a in range(2015, 2025)])
        self.assertEqual(taux["etats_disponibles"], 10)
        self.assertAlmostEqual(taux["part_faible"], 0.1)


class TestContratAlerte(unittest.TestCase):
    def test_alerte_conforme_et_sans_cause(self):
        alerte = construire_alerte("korhogo", "2025-08-15", etat_vegetation(serie_synthetique(), "2025-08-15"))
        self.assertEqual((alerte.statut, alerte.valeur, alerte.seuil), ("faible", 0.31, 0.509))
        self.assertFalse(alerte.donnees_fictives)
        self.assertEqual(alerte.observations_reference, 30)
        self.assertIn("conseiller ANADER", alerte.avertissement)
        for mot in ["maladie", "sécheresse", "ravageur", "engrais", "traitement"]:
            self.assertNotIn(mot, alerte.texte.lower())

    def test_alerte_indisponible_conforme(self):
        alerte = construire_alerte("bouake", "2025-06-15", etat_vegetation(serie_synthetique(), "2025-06-15"))
        self.assertEqual(alerte.statut, "indisponible")
        self.assertIsNone(alerte.valeur)

    def test_requete_hls(self):
        requete = requete_hls("hls_essai", [{"id": "a", "latitude": 9.4, "longitude": -5.6, "category": "korhogo"}],
                              "11-14-2026")
        self.assertEqual([c["layer"] for c in requete["params"]["layers"]], ["NDVI", "NDVI", "Fmask", "Fmask"])
        self.assertEqual(requete["params"]["dates"][0]["startDate"], "04-11-2013")


if __name__ == "__main__":
    unittest.main()

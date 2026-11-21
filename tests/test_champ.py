"""Carte de santé d'un champ, sur des images HLS synthétiques, sans réseau."""

import unittest

import numpy as np
import pandas as pd

from moteur import champ
from moteur.champ import CarteChamp, carte_du_champ, direction, ndvi_clair, position_pour_le_catalogue


def image(identifiant: str, date: str, tuile: str = "T29PRL") -> dict:
    return {"id": f"HLS-VI.S30.{tuile}.{identifiant}.v2.0", "properties": {"datetime": f"{date}T10:40:00Z"},
            "assets": {}}


class FauxCiel:
    """Images de 2013 à 2026 autour du 14 novembre, un coin de champ plus faible en 2026."""

    def __init__(self, nuageux=False):
        self.nuageux = nuageux
        self.recherches = []

    def chercheur(self, latitude, longitude, debut, fin):
        self.recherches.append((latitude, longitude))
        dates = [d for annee in range(2013, 2027) for d in pd.date_range(f"{annee}-11-07", f"{annee}-11-21", freq="3D")
                 if debut <= d <= fin]
        images = [image(f"{d:%Y%j}T104000", f"{d:%Y-%m-%d}") for d in dates]
        return images + [image(f"{d:%Y%j}T104001", f"{d:%Y-%m-%d}", "T30PTR") for d in dates[:1]]

    def lecteur(self, img, latitude, longitude, demi_cote):
        date = champ.date_image(img)
        valeurs = np.full((15, 15), 0.6 + 0.01 * (date.year % 5))
        if date.year == 2026:
            valeurs[0:3, 12:15] = 0.3
        if self.nuageux and date.year == 2026:
            valeurs[:] = np.nan
        return valeurs


class TestCarteDuChamp(unittest.TestCase):
    def test_coin_nord_est_plus_faible(self):
        ciel = FauxCiel()
        carte = carte_du_champ(9.5512, -5.7489, pd.Timestamp("2026-11-20"), ciel.chercheur, ciel.lecteur)
        self.assertEqual(carte.date, "2026-11-19")
        self.assertEqual(carte.tuile, "T29PRL")
        self.assertEqual(carte.compte("faible"), 9)
        self.assertEqual(carte.compte("normale"), 216)
        self.assertEqual(direction(carte.statuts), "vers le nord-est")
        self.assertEqual(carte.reference_annees, list(range(2013, 2026)))
        self.assertTrue(all(p == (9.55, -5.75) for p in ciel.recherches), "seule la position arrondie part")

    def test_nuages_cette_annee(self):
        ciel = FauxCiel(nuageux=True)
        carte = carte_du_champ(9.55, -5.75, pd.Timestamp("2026-11-20"), ciel.chercheur, ciel.lecteur)
        self.assertIsNone(carte.date)
        self.assertEqual(carte.compte("indisponible"), 225)

    def test_aucune_image(self):
        carte = carte_du_champ(9.55, -5.75, pd.Timestamp("2026-11-20"), lambda *a: [], None)
        self.assertIsNone(carte.date)

    def test_image_illisible_comptee_comme_nuageuse(self):
        ciel = FauxCiel()
        lectures = []

        def lecteur(img, *args):
            lectures.append(img["id"])
            if len(lectures) == 1:
                raise OSError("réseau")
            return ciel.lecteur(img, *args)

        champ.time.sleep, sommeil = (lambda s: None), champ.time.sleep
        try:
            carte = carte_du_champ(9.55, -5.75, pd.Timestamp("2026-11-20"), ciel.chercheur, lecteur)
        finally:
            champ.time.sleep = sommeil
        self.assertEqual(carte.compte("faible"), 9)


class TestPannes(unittest.TestCase):
    def test_toutes_les_images_illisibles_est_une_panne_pas_des_nuages(self):
        ciel = FauxCiel()

        def illisible(*args):
            raise OSError("authentification")

        champ.time.sleep, sommeil = (lambda s: None), champ.time.sleep
        try:
            with self.assertRaises(RuntimeError):
                carte_du_champ(9.55, -5.75, pd.Timestamp("2026-11-20"), ciel.chercheur, illisible)
        finally:
            champ.time.sleep = sommeil

    def test_adresse_signee_avec_un_jeton(self):
        import os
        from unittest import mock

        session = mock.Mock()
        session.get.return_value.status_code = 303
        session.get.return_value.headers = {"location": "https://stockage.example/signe"}
        with mock.patch.dict(os.environ, {"EARTHDATA_TOKEN": "jeton-de-test"}):
            self.assertEqual(champ.adresse_lisible("https://data.example/f.tif", session), "https://stockage.example/signe")
        self.assertEqual(session.get.call_args.kwargs["headers"]["Authorization"], "Bearer jeton-de-test")
        self.assertFalse(session.get.call_args.kwargs["allow_redirects"])
        with mock.patch.dict(os.environ, {"EARTHDATA_TOKEN": ""}):
            self.assertEqual(champ.adresse_lisible("https://data.example/f.tif", session), "https://data.example/f.tif")


class TestMasqueEtPosition(unittest.TestCase):
    def test_masque_des_nuages_de_l_alerte(self):
        brut = np.array([[6000, 6000, 6000, -19999, 12000]])
        fmask = np.array([[64, 2, 192, 64, 64]])
        self.assertEqual(np.isnan(ndvi_clair(brut, fmask)).tolist(), [[False, True, True, True, True]])
        self.assertAlmostEqual(ndvi_clair(brut, fmask)[0, 0], 0.6)

    def test_position_arrondie_a_5_km(self):
        self.assertEqual(position_pour_le_catalogue(9.5512, -5.7489), (9.55, -5.75))
        self.assertEqual(position_pour_le_catalogue(5.3399, -4.0281), (5.35, -4.05))

    def test_direction(self):
        statuts = np.full((15, 15), "normale", dtype=object)
        self.assertIsNone(direction(statuts))
        statuts[12:15, 6:9] = "faible"
        self.assertEqual(direction(statuts), "vers le sud")
        statuts[:] = "normale"
        statuts[6:9, 6:9] = "faible"
        self.assertEqual(direction(statuts), "au centre")

    def test_dessin_png(self):
        from bot.langage.gabarits import date_en_mots

        carte = CarteChamp("2026-11-14", np.full((15, 15), "normale", dtype=object), 57, "T29PRL")
        self.assertTrue(champ.dessiner(carte, date_en_mots).startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()

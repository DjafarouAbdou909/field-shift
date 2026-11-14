import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from donnees import power
from donnees.config import charger, points
from donnees.registre import Registre, ecrire_atomique
from moteur.criteres import classer, groupes
from moteur.exporter import de_la, texte_stabilite, texte_tendance
from moteur.fao56 import et0, kc_journalier, rayonnement_extraterrestre
from moteur.saison import debut_des_pluies, plus_longue_sequence_seche
from moteur.statistiques import proportion_wilson


class TestFao56(unittest.TestCase):
    def test_exemple_18_uccle(self):
        """FAO 56, exemple 18, ETo de 3,88 mm par jour le 6 juillet à Uccle."""
        self.assertAlmostEqual(rayonnement_extraterrestre(50.80, 187), 41.09, delta=0.02)
        self.assertAlmostEqual(et0(21.5, 12.3, 1.409, 22.07, 2.078, 100, 50.80, 187), 3.88, delta=0.02)

    def test_courbe_kc(self):
        courbe = kc_journalier([2, 2, 3, 2], [0.4, 1.2, 0.6])
        self.assertEqual(len(courbe), 9)
        self.assertEqual(courbe[:2], [0.4, 0.4])
        self.assertAlmostEqual(courbe[3], 1.2)
        self.assertEqual(courbe[4:7], [1.2, 1.2, 1.2])
        self.assertAlmostEqual(courbe[-1], 0.6)


class TestSaison(unittest.TestCase):
    critere = {"debut_recherche": "03-01", "fin_recherche": "07-31", "cumul_mm": 20.0, "jours_cumul": 3,
               "jour_sec_mm": 1.0, "sequence_seche_max_jours": 7, "horizon_jours": 30}

    def serie(self, pluies: dict[int, float]):
        jours = [date(2020, 1, 1) + timedelta(days=i) for i in range(366)]
        return jours, [pluies.get(i, 0.0) for i in range(366)]

    def test_sequence_seche(self):
        self.assertEqual(plus_longue_sequence_seche([0, 0, 5, 0, 0, 0, 2], 1.0), 3)

    def test_faux_depart_ignore(self):
        # 25 mm le 15 mars puis 23 jours secs, faux départ. Le 10 avril, 24 mm en 3 jours,
        # puis une pluie tous les 3 jours, vrai début.
        pluies = {74: 25.0, 100: 8.0, 101: 8.0, 102: 8.0}
        pluies.update({i: 8.0 for i in range(105, 160, 3)})
        jours, pluie = self.serie(pluies)
        self.assertEqual(debut_des_pluies(jours, pluie, 2020, self.critere), date(2020, 4, 10))

    def test_aucun_debut(self):
        jours, pluie = self.serie({})
        self.assertIsNone(debut_des_pluies(jours, pluie, 2020, self.critere))


class TestCriteres(unittest.TestCase):
    def test_egalite_partage_le_rang(self):
        scores = {"a": {"eau": 0.5, "sol": 0.0}, "b": {"eau": 0.5, "sol": 0.0}, "c": {"eau": 0.2, "sol": 0.0}}
        classement = classer(scores, {"eau": 1.0, "sol": 0.0})
        self.assertEqual([rang for _, _, rang in classement], [1, 1, 3])
        self.assertEqual(groupes(classement), [["a", "b"], ["c"]])

    def test_wilson(self):
        bas, haut = proportion_wilson(5, 10)
        self.assertAlmostEqual(bas, 0.2366, places=3)
        self.assertAlmostEqual(haut, 0.7634, places=3)

    def test_tendance_annoncee_seulement_si_robuste(self):
        robuste = [(7, 10.0, 2.0, 18.0), (10, 8.0, 1.0, 15.0)]
        fragile = [(7, 10.0, 2.0, 18.0), (10, 3.0, -4.0, 9.0)]
        self.assertIn("plus tard", texte_tendance(robuste)[0])
        self.assertIn("Aucune tendance robuste", texte_tendance(fragile)[0])

    def test_stabilite_nomme_le_scenario(self):
        s = {"facteur_pluie": 0.8, "retard_jours": 14}
        ordres = {"reference": [["a"], ["b"]], "pluie_reduite": [["b"], ["a"]], "semis_retarde": [["a"], ["b"]]}
        texte = texte_stabilite(ordres, s)
        self.assertIn("change si la pluie baisse de 20 %", texte)
        self.assertIn("tient si les pluies démarrent 14 jours plus tard", texte)

    def test_article(self):
        self.assertEqual(de_la("arachide"), "de l'arachide")
        self.assertEqual(de_la("maïs"), "du maïs")


class TestDonnees(unittest.TestCase):
    def setUp(self):
        self.config = charger()

    def test_imerg_en_temps_universel(self):
        self.assertIn("time-standard=UTC", power.url(points(self.config)[0], self.config))

    def test_grille(self):
        grille = points(self.config)
        self.assertEqual(len(grille), 18)
        centre = [p for p in grille if p.lieu == "korhogo"][4]
        self.assertEqual((centre.lat, centre.lon), (9.45, -5.65))

    def test_registre_detecte_alteration_et_changement_de_requete(self):
        with tempfile.TemporaryDirectory() as dossier:
            racine = Path(dossier)
            fichier = racine / "a.json"
            ecrire_atomique(fichier, b"{}")
            registre = Registre(racine / "registre.csv", racine)
            registre.consigner(fichier, "u1")
            self.assertTrue(Registre(racine / "registre.csv", racine).est_acquis(fichier, "u1"))
            self.assertFalse(registre.est_acquis(fichier, "u2"))
            fichier.write_bytes(b"{ }")
            self.assertFalse(registre.est_acquis(fichier, "u1"))

    def test_controle_power(self):
        self.config["periode"] = {"debut": "2020-08-01", "fin": "2020-08-02"}
        self.config["power"]["parametres"] = ["IMERG_PRECTOT"]
        self.assertEqual(power.controler(
            {"properties": {"parameter": {"IMERG_PRECTOT": {"20200801": 3.5, "20200802": -999.0}}}},
            self.config), {"IMERG_PRECTOT": 1})
        with self.assertRaises(ValueError):
            power.controler({"properties": {"parameter": {}}}, self.config)


if __name__ == "__main__":
    unittest.main()

"""Villes couvertes dans toute la Côte d'Ivoire, et lieu dit par l'agriculteur, sans réseau."""

import unittest
from unittest import mock

from bot import geocodage
from moteur.cultures import semis_coton
from moteur.lieux import LIEUX, chef_lieu_de_region, distance_km, lieux_de_zone, rotation_disponible, ville_la_plus_proche


class TestVillesCouvertes(unittest.TestCase):
    def test_trente_et_une_regions_et_deux_districts(self):
        self.assertEqual(len(LIEUX), 33)
        self.assertEqual(len({l["region"] for l in LIEUX.values()}), 33)
        self.assertTrue(all(4.3 < l["lat"] < 10.8 and -8.7 < l["lon"] < -2.4 for l in LIEUX.values()))

    def test_korhogo_et_bouake_inchanges(self):
        self.assertEqual((LIEUX["korhogo"]["lat"], LIEUX["korhogo"]["lon"]), (9.458, -5.629))
        self.assertEqual((LIEUX["bouake"]["lat"], LIEUX["bouake"]["lon"]), (7.690, -5.030))

    def test_zones(self):
        self.assertIn("korhogo", lieux_de_zone("savane"))
        self.assertIn("bouake", lieux_de_zone("savane"))
        self.assertIn("abidjan", lieux_de_zone("foret"))
        self.assertTrue(rotation_disponible("odienne"))
        self.assertFalse(rotation_disponible("san_pedro"))

    def test_distance_et_ville_la_plus_proche(self):
        self.assertAlmostEqual(distance_km(0, 0, 1, 0), 111.2, delta=0.2)
        identifiant, distance = ville_la_plus_proche(9.55, -5.75)
        self.assertEqual(identifiant, "korhogo")
        self.assertLess(distance, 20)
        self.assertIsNone(ville_la_plus_proche(12.64, -8.0), "Bamako est hors de la zone couverte")

    def test_chef_lieu_de_la_region_nommee_par_openstreetmap(self):
        self.assertEqual(chef_lieu_de_region("Poro"), "korhogo")
        self.assertEqual(chef_lieu_de_region("Mé"), "adzope")
        self.assertEqual(chef_lieu_de_region("N’zi"), "dimbokro")
        self.assertEqual(chef_lieu_de_region("Abidjan"), "abidjan")
        self.assertEqual(chef_lieu_de_region("Gbêkê"), "bouake")
        self.assertIsNone(chef_lieu_de_region("Savanes"), "un district n'est pas une région")
        self.assertIsNone(chef_lieu_de_region(None))

    def test_fenetre_de_semis_du_coton_selon_le_9e_parallele(self):
        self.assertEqual(semis_coton("boundiali"), semis_coton("korhogo"))
        self.assertEqual(semis_coton("katiola"), semis_coton("bouake"))


class TestLieuDit(unittest.TestCase):
    def test_ville_ou_region_dans_une_phrase(self):
        self.assertEqual(geocodage.ville_nommee("mon champ est vers Ferké"), "ferkessedougou")
        self.assertEqual(geocodage.ville_nommee("je suis à San Pedro"), "san_pedro")
        self.assertEqual(geocodage.ville_nommee("dans le Poro"), "korhogo")
        self.assertEqual(geocodage.ville_nommee("Bouaké"), "bouake")
        self.assertIsNone(geocodage.ville_nommee("je ne sais pas"))
        self.assertIsNone(geocodage.ville_nommee("mancozèbe"), "un mot qui contient Man n'est pas Man")

    def test_mots_du_lieu_seuls_partent_chez_openstreetmap(self):
        self.assertEqual(geocodage.nom_a_chercher("j'habite à Sinématiali"), "sinematiali")
        self.assertEqual(geocodage.nom_a_chercher("mon champ est près de Niakaramandougou"), "niakaramandougou")

    def test_recherche_limitee_a_la_cote_d_ivoire_et_identifiee(self):
        geocodage.chercher.cache_clear()
        session = mock.Mock()
        session.get.return_value.json.return_value = [{"lat": "9.583", "lon": "-5.383", "name": "Sinématiali",
                                                       "address": {"state_district": "Poro", "state": "Savanes"}}]
        with mock.patch.object(geocodage, "INTERVALLE_SECONDES", 0):
            self.assertEqual(geocodage.chercher("sinematiali", session), (9.583, -5.383, "Sinématiali", "Poro"))
        appel = session.get.call_args
        self.assertEqual(appel.kwargs["params"]["countrycodes"], "ci")
        self.assertEqual(appel.kwargs["headers"]["User-Agent"], geocodage.AGENT)
        geocodage.chercher.cache_clear()

    def test_panne_ou_phrase_trop_longue(self):
        geocodage.chercher.cache_clear()
        session = mock.Mock()
        session.get.side_effect = OSError("réseau")
        with mock.patch.object(geocodage, "INTERVALLE_SECONDES", 0):
            self.assertIsNone(geocodage.chercher("sinematiali", session))
        self.assertIsNone(geocodage.chercher("un deux trois quatre cinq", session))
        self.assertIsNone(geocodage.chercher("ab", session))
        geocodage.chercher.cache_clear()


if __name__ == "__main__":
    unittest.main()

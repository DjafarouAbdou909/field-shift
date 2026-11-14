import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from moteur import appeears


class TestAppeears(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.chemin = Path(self.dossier.name)

    def tearDown(self):
        self.dossier.cleanup()

    def test_grille_de_961_points(self):
        """Pas de 0,01 degré sur 0,15 de part et d'autre, soit 31 fois 31 points."""
        points = appeears.grille_points("korhogo", 9.45, -5.65)
        self.assertEqual(len(points), 961)
        self.assertEqual(len({p["id"] for p in points}), 961)
        self.assertEqual((points[0]["latitude"], points[0]["longitude"]), (9.3, -5.8))
        self.assertEqual((points[-1]["latitude"], points[-1]["longitude"]), (9.6, -5.5))

    def test_requete_points(self):
        requete = appeears.requete_points("essai", [("MCD12Q1.061", "LC_Type1")], [{"id": "a"}], "01-01-2001", "12-31-2025")
        self.assertEqual(requete["task_type"], "point")
        self.assertEqual(requete["params"]["layers"], [{"product": "MCD12Q1.061", "layer": "LC_Type1"}])
        self.assertEqual(requete["params"]["dates"], [{"startDate": "01-01-2001", "endDate": "12-31-2025"}])

    def test_identifiants_lus_dans_netrc(self):
        fichier = self.chemin / "netrc"
        fichier.write_text("machine urs.earthdata.nasa.gov login utilisateur password secret\n", encoding="utf-8")
        os.chmod(fichier, 0o600)
        self.assertEqual(appeears.identifiants(str(fichier)), ("utilisateur", "secret"))
        fichier.write_text("machine autre.exemple login a password b\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            appeears.identifiants(str(fichier))

    def test_tache_consignee_non_resoumise(self):
        journal = self.chemin / "taches.json"
        requete = appeears.requete_points("essai", [], [], "01-01-2001", "12-31-2001")
        with mock.patch("moteur.appeears.requests.post") as post:
            post.return_value = mock.Mock(json=lambda: {"task_id": "t1"}, raise_for_status=lambda: None)
            self.assertEqual(appeears.soumettre("jeton", requete, journal), "t1")
            self.assertEqual(appeears.soumettre("jeton", requete, journal), "t1")
            self.assertEqual(post.call_count, 1)
        self.assertEqual(json.loads(journal.read_text(encoding="utf-8"))["essai"]["task_id"], "t1")

    def test_empreinte_verifiee_au_telechargement(self):
        contenu = b"ID,Date\n1,2025-01-01\n"
        bon = hashlib.sha256(contenu).hexdigest()
        liste = mock.Mock(json=lambda: {"files": [{"file_name": "a.csv", "file_id": "f1", "sha256": bon},
                                                   {"file_name": "README.md", "file_id": "f2", "sha256": "x"}]},
                          raise_for_status=lambda: None)
        fichier = mock.Mock(content=contenu, raise_for_status=lambda: None)
        dossier = appeears.DOSSIER_APPEEARS
        with mock.patch.object(appeears, "DOSSIER_APPEEARS", self.chemin), \
                mock.patch("moteur.appeears.requests.get", side_effect=[liste, fichier]):
            chemins = appeears.telecharger_resultats("jeton", "t1", self.chemin / "essai")
        self.assertEqual([c.name for c in chemins], ["a.csv"])
        self.assertTrue((self.chemin / "registre.csv").exists())
        mauvais = mock.Mock(json=lambda: {"files": [{"file_name": "b.csv", "file_id": "f3", "sha256": "0" * 64}]},
                            raise_for_status=lambda: None)
        with mock.patch.object(appeears, "DOSSIER_APPEEARS", self.chemin), \
                mock.patch("moteur.appeears.requests.get", side_effect=[mauvais, fichier]):
            with self.assertRaises(ValueError):
                appeears.telecharger_resultats("jeton", "t1", self.chemin / "essai")
        self.assertFalse((self.chemin / "essai" / "b.csv").exists())
        self.assertEqual(appeears.DOSSIER_APPEEARS, dossier)


if __name__ == "__main__":
    unittest.main()

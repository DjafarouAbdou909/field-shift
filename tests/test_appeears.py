import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

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

    def session(self, *reponses):
        """Session dont la connexion est simulée et dont les requêtes renvoient les réponses données."""
        session = appeears.SessionAppeears()
        self.session_creee = session
        self.connexion = mock.patch("moteur.appeears.connexion", side_effect=lambda: f"jeton{session.connexions + 1}")
        self.requete = mock.patch("moteur.appeears.requests.request", side_effect=list(reponses))
        self.addCleanup(self.connexion.stop)
        self.addCleanup(self.requete.stop)
        self.connexion.start()
        self.appels = self.requete.start()
        return session

    @staticmethod
    def reponse(code, contenu=None, octets=b""):
        r = mock.Mock(status_code=code, content=octets)
        r.json = lambda: contenu
        r.raise_for_status = (lambda: None) if code < 400 else mock.Mock(side_effect=requests.HTTPError(str(code)))
        return r

    def test_une_seule_connexion_pour_plusieurs_requetes(self):
        session = self.session(self.reponse(200, {"status": "pending"}), self.reponse(200, {"status": "done"}))
        self.assertEqual(appeears.etat(session, "t1"), "pending")
        self.assertEqual(appeears.etat(session, "t1"), "done")
        self.assertEqual(session.connexions, 1)

    def test_reconnexion_unique_sur_refus(self):
        """Un 401 provoque une reconnexion et la requête est rejouée avec le nouveau jeton."""
        session = self.session(self.reponse(401), self.reponse(200, {"status": "done"}))
        self.assertEqual(appeears.etat(session, "t1"), "done")
        self.assertEqual(session.connexions, 2)
        self.assertEqual(self.appels.call_args_list[1].kwargs["headers"], {"Authorization": "Bearer jeton2"})

    def test_refus_persistant_leve_l_erreur(self):
        session = self.session(self.reponse(403), self.reponse(403))
        with self.assertRaises(requests.HTTPError):
            appeears.etat(session, "t1")
        self.assertEqual(session.connexions, 2)
        self.assertEqual(self.appels.call_count, 2)

    def test_tache_consignee_non_resoumise(self):
        journal = self.chemin / "taches.json"
        requete = appeears.requete_points("essai", [], [], "01-01-2001", "12-31-2001")
        session = self.session(self.reponse(200, {"task_id": "t1"}))
        self.assertEqual(appeears.soumettre(session, requete, journal), "t1")
        self.assertEqual(appeears.soumettre(session, requete, journal), "t1")
        self.assertEqual(self.appels.call_count, 1)
        self.assertEqual(json.loads(journal.read_text(encoding="utf-8"))["essai"]["task_id"], "t1")

    def test_empreinte_verifiee_au_telechargement(self):
        contenu = b"ID,Date\n1,2025-01-01\n"
        bon = hashlib.sha256(contenu).hexdigest()
        liste = self.reponse(200, {"files": [{"file_name": "a.csv", "file_id": "f1", "sha256": bon},
                                             {"file_name": "README.md", "file_id": "f2", "sha256": "x"}]})
        mauvais = self.reponse(200, {"files": [{"file_name": "b.csv", "file_id": "f3", "sha256": "0" * 64}]})
        fichier = self.reponse(200, octets=contenu)
        session = self.session(liste, fichier, mauvais, self.reponse(200, octets=contenu))
        with mock.patch.object(appeears, "DOSSIER_APPEEARS", self.chemin):
            chemins = appeears.telecharger_resultats(session, "t1", self.chemin / "essai")
            self.assertEqual([c.name for c in chemins], ["a.csv"])
            self.assertTrue((self.chemin / "registre.csv").exists())
            with self.assertRaises(ValueError):
                appeears.telecharger_resultats(session, "t1", self.chemin / "essai")
        self.assertFalse((self.chemin / "essai" / "b.csv").exists())

    def test_surveillance_continue_apres_un_refus_persistant(self):
        """Premier passage, deux refus 403, signalés sans arrêt. Second passage, un refus, une reconnexion, puis une réponse."""
        journal = self.chemin / "taches.json"
        journal.write_text(json.dumps({"essai": {"task_id": "t1"}}), encoding="utf-8")
        self.session(self.reponse(403), self.reponse(403), self.reponse(403), self.reponse(200, {"status": "processing"}))
        with mock.patch.object(appeears, "JOURNAL_TACHES", journal), mock.patch("moteur.appeears.time.sleep"), \
                mock.patch("moteur.appeears.SessionAppeears", return_value=self.session_creee):
            appeears.surveiller(intervalle=0, passages=2)
        self.assertEqual(self.appels.call_count, 4)
        self.assertEqual(self.session_creee.connexions, 3)

    def test_aucune_deconnexion(self):
        source = Path(appeears.__file__).read_text(encoding="utf-8")
        self.assertNotIn("/logout", source)

if __name__ == "__main__":
    unittest.main()

import re
import unittest
from pathlib import Path

from moteur.donnees import DOSSIER_POWER

RACINE = Path(__file__).resolve().parents[1]
DONNEES_PRESENTES = (DOSSIER_POWER / "registre.csv").exists()


class TestAucuneDonneeFictive(unittest.TestCase):
    def test_interfaces_sans_exemple_fictif(self):
        """Ni l'application ni le bot ne chargent l'exemple fictif, réservé aux tests."""
        for fichier in list((RACINE / "app").rglob("*.py")) + list((RACINE / "bot").rglob("*.py")):
            texte = fichier.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"charger_exemple|exemple[_a-z]*\.json", texte), fichier.name)


@unittest.skipUnless(DONNEES_PRESENTES, "séries NASA absentes de data/raw, lancer venv/bin/python -m moteur.controles")
class TestApplication(unittest.TestCase):
    def test_vrais_resultats_et_parametres_d_url(self):
        from streamlit.testing.v1 import AppTest
        application = AppTest.from_file(str(RACINE / "app" / "app.py"), default_timeout=600)
        application.query_params["lieu"] = "bouake"
        application.query_params["priorite"] = "sol"
        application.run()
        self.assertEqual(list(application.exception), [])
        self.assertEqual([t.value for t in application.title], ["Rotations comparées pour Bouaké"])
        self.assertEqual(list(application.error), [])
        self.assertEqual(len(application.expander), 3)
        self.assertIn("1120 mm", application.dataframe[0].value.iloc[0, 1])


if __name__ == "__main__":
    unittest.main()

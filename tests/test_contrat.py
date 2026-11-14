import json
import unittest

from pydantic import ValidationError

from moteur import charger_exemple
from moteur.contrat import Element, Indicateur, Poids, Recommandation
from moteur.recommander import EXEMPLE


class TestContrat(unittest.TestCase):
    def setUp(self):
        self.donnees = json.loads(EXEMPLE.read_text(encoding="utf-8"))

    def test_exemple_valide_et_marque_fictif(self):
        reco = charger_exemple()
        self.assertTrue(reco.donnees_fictives)
        self.assertIn("FICTIVES", reco.avertissement)

    def test_element_mesure_sans_source_refuse(self):
        with self.assertRaises(ValidationError):
            Element(texte="Pluie de 900 mm", niveau="mesure")
        Element(texte="Les légumineuses fixent l'azote", niveau="hypothese")

    def test_indicateur_hors_plage_refuse(self):
        indicateur = dict(self.donnees["indicateurs"][0], valeur=50)
        with self.assertRaises(ValidationError):
            Indicateur.model_validate(indicateur)

    def test_poids_doivent_sommer_a_un(self):
        with self.assertRaises(ValidationError):
            Poids(eau=0.5, revenu=0.5, sol=0.5)

    def test_moins_de_trois_strategies_refuse(self):
        self.donnees["strategies"] = self.donnees["strategies"][:2]
        with self.assertRaises(ValidationError):
            Recommandation.model_validate(self.donnees)

    def test_une_seule_rotation_actuelle(self):
        self.donnees["strategies"][1]["actuelle"] = True
        with self.assertRaises(ValidationError):
            Recommandation.model_validate(self.donnees)

    def test_classement_complet(self):
        self.donnees["classement"] = self.donnees["classement"][:2]
        with self.assertRaises(ValidationError):
            Recommandation.model_validate(self.donnees)

    def test_champ_inconnu_refuse(self):
        self.donnees["rendement_garanti"] = 3
        with self.assertRaises(ValidationError):
            Recommandation.model_validate(self.donnees)


if __name__ == "__main__":
    unittest.main()

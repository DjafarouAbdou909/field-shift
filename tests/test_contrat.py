import json
import unittest

from pydantic import ValidationError

from moteur import charger_exemple, charger_exemple_alerte, charger_exemple_diagnostic
from moteur.contrat import MESSAGES_DIAGNOSTIC, AlerteVegetation, Diagnostic, Element, Indicateur, Poids, Recommandation
from moteur.recommander import EXEMPLE, EXEMPLE_ALERTE, EXEMPLE_DIAGNOSTIC


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



class TestContratVersion2(unittest.TestCase):
    def setUp(self):
        self.alerte = json.loads(EXEMPLE_ALERTE.read_text(encoding="utf-8"))
        self.diagnostic = json.loads(EXEMPLE_DIAGNOSTIC.read_text(encoding="utf-8"))

    def test_version_2_et_exemples_fictifs(self):
        self.assertEqual(charger_exemple().version, "2")
        self.assertTrue(charger_exemple_alerte().donnees_fictives)
        self.assertTrue(charger_exemple_diagnostic().donnees_fictives)

    def test_alerte_faible_exige_une_valeur_sous_le_seuil(self):
        with self.assertRaises(ValidationError):
            AlerteVegetation.model_validate(dict(self.alerte, valeur=0.5))
        AlerteVegetation.model_validate(dict(self.alerte, valeur=0.5, statut="normale"))

    def test_alerte_indisponible_sans_valeur(self):
        AlerteVegetation.model_validate(dict(self.alerte, statut="indisponible", valeur=None, seuil=None))
        with self.assertRaises(ValidationError):
            AlerteVegetation.model_validate(dict(self.alerte, statut="indisponible"))

    def test_diagnostic_dans_la_liste_fermee(self):
        with self.assertRaises(ValidationError):
            Diagnostic.model_validate(dict(self.diagnostic, maladie="maladie hors liste"))
        Diagnostic.model_validate(dict(self.diagnostic, statut="inconnu", maladie=None, source_maladie=None))
        with self.assertRaises(ValidationError):
            Diagnostic.model_validate(dict(self.diagnostic, statut="inconnu"))

    def test_aucune_maladie_reconnue_ne_nomme_aucune_maladie(self):
        sans_maladie = dict(self.diagnostic, statut="aucune_maladie_reconnue", maladie=None, source_maladie=None,
                            avertissement=MESSAGES_DIAGNOSTIC["aucune_maladie_reconnue"])
        Diagnostic.model_validate(sans_maladie)
        with self.assertRaises(ValidationError):
            Diagnostic.model_validate(dict(sans_maladie, maladie="maladie fictive A"))
        with self.assertRaises(ValidationError):
            Diagnostic.model_validate(dict(sans_maladie, statut="saine"))

    def test_chaque_message_renvoie_au_conseiller(self):
        for message in MESSAGES_DIAGNOSTIC.values():
            self.assertIn("conseiller ANADER", message)

    def test_diagnostic_renvoie_au_conseiller(self):
        with self.assertRaises(ValidationError):
            Diagnostic.model_validate(dict(self.diagnostic, avertissement="Maladie possible."))


if __name__ == "__main__":
    unittest.main()

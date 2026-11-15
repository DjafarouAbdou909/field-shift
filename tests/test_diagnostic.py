import json
import unittest
from unittest import mock

from moteur import diagnostic
from moteur.contrat import MESSAGES_DIAGNOSTIC


def interaction(texte, statut="completed"):
    return {"status": statut, "steps": [{"type": "model_output", "content": [{"type": "text", "text": texte}]}]}


class TestDiagnostic(unittest.TestCase):
    def test_requete_figee(self):
        """Modèle figé, aucune conservation par l'API, schéma fermé, image en ligne."""
        corps = diagnostic.requete(b"\xff\xd8image", "image/jpeg", "maïs")
        self.assertEqual(corps["model"], "gemini-4-hydrogen")
        self.assertIs(corps["store"], False)
        enum = corps["response_format"]["schema"]["properties"]["reponse"]["enum"]
        self.assertEqual(enum, ["striure du maïs", "rouille commune du maïs", "helminthosporiose du maïs",
                                "aucune_maladie_reconnue", "inconnu"])
        self.assertEqual(corps["input"][0]["type"], "user_input")
        self.assertEqual([c["type"] for c in corps["input"][0]["content"]], ["text", "image"])

    def test_requete_refusee(self):
        with self.assertRaises(ValueError):
            diagnostic.requete(b"x", "image/jpeg", "igname")
        with self.assertRaises(ValueError):
            diagnostic.requete(b"x", "image/gif", "coton")
        with self.assertRaises(ValueError):
            diagnostic.requete(b"x" * (diagnostic.TAILLE_MAX_OCTETS + 1), "image/jpeg", "coton")

    def test_maladie_de_la_liste(self):
        d = diagnostic.interpreter(json.dumps({"reponse": "bactériose du coton", "confiance": 0.8}), "coton")
        self.assertEqual((d.statut, d.maladie, d.confiance), ("maladie_possible", "bactériose du coton", 0.8))
        self.assertIsNotNone(d.source_maladie)
        self.assertEqual(d.avertissement, MESSAGES_DIAGNOSTIC["maladie_possible"])

    def test_aucune_maladie_reconnue(self):
        d = diagnostic.interpreter(json.dumps({"reponse": "aucune_maladie_reconnue", "confiance": 0.7}), "maïs")
        self.assertEqual((d.statut, d.maladie), ("aucune_maladie_reconnue", None))

    def test_tout_ecart_devient_inconnu(self):
        """Maladie hors liste, maladie d'une autre culture, JSON illisible, confiance hors bornes, sortie vide."""
        for texte in [json.dumps({"reponse": "alternariose du coton", "confiance": 0.9}),
                      json.dumps({"reponse": "striure du maïs", "confiance": 0.9}),
                      "pas du JSON", json.dumps({"reponse": "bactériose du coton", "confiance": 3}),
                      json.dumps({"confiance": 0.5}), None]:
            d = diagnostic.interpreter(texte, "coton")
            self.assertEqual((d.statut, d.maladie, d.confiance), ("inconnu", None, 0.0), texte)
            self.assertEqual(d.avertissement, MESSAGES_DIAGNOSTIC["inconnu"])

    def test_interaction_non_terminee(self):
        self.assertIsNone(diagnostic.texte_de_sortie(interaction("{}", statut="incomplete")))
        self.assertEqual(diagnostic.texte_de_sortie(interaction("{}")), "{}")

    def test_appel_avec_cle_en_entete(self):
        session = mock.Mock()
        session.post.return_value.json.return_value = interaction(
            json.dumps({"reponse": "rouille commune du maïs", "confiance": 0.6}))
        d = diagnostic.diagnostiquer(b"\x89PNG", "image/png", "maïs", session=session, cle="cle-de-test")
        self.assertEqual(d.maladie, "rouille commune du maïs")
        appel = session.post.call_args
        self.assertEqual(appel.args[0], "https://generativelanguage.googleapis.com/v1/interactions")
        self.assertEqual(appel.kwargs["headers"]["x-goog-api-key"], "cle-de-test")

    def test_sans_cle(self):
        with mock.patch.dict("os.environ", {}, clear=True), self.assertRaises(RuntimeError):
            diagnostic.appeler({}, session=mock.Mock())


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest import mock

from moteur import diagnostic
from moteur.contrat import AVERTISSEMENT_DIAGNOSTIC

JPEG = b"\xff\xd8\xff" + b"0" * 200


def interaction(texte, statut="completed"):
    return {"status": statut, "steps": [{"type": "model_output", "content": [{"type": "text", "text": texte}]}]}


REPONSE = ("*Plante identifiée* : feuille de maïs.\n*Diagnostic probable* : rouille.\n"
           "*Explication simple* : champignon favorisé par l'humidité.\n*Recommandation concrète* : action.\n\n"
           + AVERTISSEMENT_DIAGNOSTIC)


class TestRequete(unittest.TestCase):
    def test_requete_figee(self):
        """Modèle figé, aucune conservation par l'API, texte et image dans une étape user_input."""
        corps = diagnostic.requete(JPEG, "image/jpeg", "maïs")
        self.assertEqual(corps["model"], "gemini-4-hydrogen")
        self.assertIs(corps["store"], False)
        self.assertEqual(corps["input"][0]["type"], "user_input")
        self.assertEqual([c["type"] for c in corps["input"][0]["content"]], ["text", "image"])
        self.assertNotIn("response_format", corps)

    def test_consigne_d_agri_bot(self):
        """Les quatre parties de la consigne de agri-bot, la culture déclarée et l'avertissement final."""
        texte = diagnostic.consigne("coton")
        for partie in ("*Plante identifiée*", "*Diagnostic probable*", "*Explication simple*",
                       "*Recommandation concrète*", "Culture déclarée par l'agriculteur : coton",
                       AVERTISSEMENT_DIAGNOSTIC):
            self.assertIn(partie, texte)
        self.assertIn("non précisée", diagnostic.consigne(None))


class TestDiagnostic(unittest.TestCase):
    def appel(self, *reponses):
        session = mock.Mock()
        session.post.return_value.status_code = 200
        session.post.return_value.json.side_effect = list(reponses)
        return session

    def test_texte_du_modele_rendu_tel_quel(self):
        d = diagnostic.diagnostiquer(JPEG, "image/jpeg", "maïs", session=self.appel(interaction(REPONSE)), cle="c")
        self.assertEqual((d.statut, d.texte, d.culture_declaree), ("analyse", REPONSE, "maïs"))

    def test_avertissement_retabli(self):
        """Absent ou reformulé, l'avertissement final est remplacé par le texte exact."""
        for texte in ("*Diagnostic probable* : rouille.",
                      "*Diagnostic probable* : rouille.\n⚠️ Avis indicatif, voyez un agent agricole."):
            d = diagnostic.diagnostiquer(JPEG, "image/jpeg", None, session=self.appel(interaction(texte)), cle="c")
            self.assertEqual(d.texte, "*Diagnostic probable* : rouille.\n\n" + AVERTISSEMENT_DIAGNOSTIC)

    def test_photo_inexploitable(self):
        for image, type_image, message in ((b"", "image/jpeg", diagnostic.ILLISIBLE),
                                           (b'{"erreur": 1}' + b" " * 200, "image/jpeg", diagnostic.ILLISIBLE),
                                           (JPEG, "image/gif", diagnostic.FORMAT_REFUSE)):
            d = diagnostic.diagnostiquer(image, type_image, session=mock.Mock(), cle="c")
            self.assertEqual((d.statut, d.texte), ("echec", message))

    def test_formats_d_agri_bot(self):
        self.assertEqual(diagnostic.TYPES_IMAGE, {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"})
        self.assertEqual(diagnostic.type_de_base("image/JPEG; charset=x"), "image/jpeg")

    def test_reponse_vide_ou_bloquee(self):
        for reponse in (interaction(""), interaction(REPONSE, statut="failed")):
            d = diagnostic.diagnostiquer(JPEG, "image/png", session=self.appel(reponse), cle="c")
            self.assertEqual((d.statut, d.texte), ("echec", diagnostic.A_REESSAYER))

    def test_panne_du_service(self):
        session = mock.Mock()
        session.post.side_effect = RuntimeError("réseau")
        d = diagnostic.diagnostiquer(JPEG, "image/jpeg", session=session, cle="c")
        self.assertEqual((d.statut, d.texte), ("echec", diagnostic.A_REESSAYER))

    def test_cle_en_entete(self):
        session = self.appel(interaction(REPONSE))
        diagnostic.diagnostiquer(JPEG, "image/jpeg", session=session, cle="cle-de-test")
        appel = session.post.call_args
        self.assertEqual(appel.args[0], "https://generativelanguage.googleapis.com/v1/interactions")
        self.assertEqual(appel.kwargs["headers"]["x-goog-api-key"], "cle-de-test")

    def test_nouvel_essai_si_erreur_passagere(self):
        session = mock.Mock()
        surcharge, succes = mock.Mock(status_code=503), mock.Mock(status_code=200)
        succes.json.return_value = interaction(REPONSE)
        session.post.side_effect = [surcharge, succes]
        with mock.patch.object(diagnostic.time, "sleep") as pause:
            d = diagnostic.diagnostiquer(JPEG, "image/jpeg", session=session, cle="c")
        self.assertEqual(d.statut, "analyse")
        self.assertEqual(session.post.call_count, 2)
        pause.assert_called_once()

    def test_sans_cle(self):
        with mock.patch.dict("os.environ", {}, clear=True), self.assertRaises(RuntimeError):
            diagnostic.appeler({}, session=mock.Mock())


if __name__ == "__main__":
    unittest.main()

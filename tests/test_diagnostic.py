import unittest
from unittest import mock

from moteur import diagnostic
from moteur.contrat import AVERTISSEMENT_DIAGNOSTIC

JPEG = b"\xff\xd8\xff" + b"0" * 200


def interaction(texte, statut="completed"):
    return {"status": statut, "steps": [{"type": "model_output", "content": [{"type": "text", "text": texte}]}]}


REPONSE = ("Cette photo montre une feuille de maïs avec de petites pustules orange.\n\n"
           "Il s'agit probablement de la rouille, un champignon favorisé par l'humidité.\n\n"
           "Regardez les plants voisins et montrez la plante à votre conseiller.\n\n" + AVERTISSEMENT_DIAGNOSTIC)


class TestRequete(unittest.TestCase):
    def test_requete_figee(self):
        """Modèle figé, aucune conservation par l'API, texte et image dans une étape user_input."""
        corps = diagnostic.requete(JPEG, "image/jpeg", "maïs")
        self.assertEqual(corps["model"], "gemini-3.5-flash")
        self.assertEqual(corps["generation_config"]["thinking_level"], "minimal")
        self.assertIs(corps["store"], False)
        self.assertEqual(corps["input"][0]["type"], "user_input")
        self.assertEqual([c["type"] for c in corps["input"][0]["content"]], ["text", "image"])
        self.assertNotIn("response_format", corps)

    def test_consigne_explication_suivie(self):
        """Explication suivie sans numéro, contenu attendu, aucun produit, culture déclarée et avertissement."""
        texte = diagnostic.consigne("coton")
        for partie in ("sans aucun numéro", "signes", "problème le plus probable", "ce qu'il peut faire à la récolte",
                       "gestes concrets", "Ne nomme JAMAIS de produit", "ANADER",
                       "Culture déclarée par l'agriculteur : coton", AVERTISSEMENT_DIAGNOSTIC):
            self.assertIn(partie, texte)
        self.assertNotIn("1.", texte)
        self.assertIn("non précisée", diagnostic.consigne(None))

    def test_numerotation_retiree(self):
        """Une réponse numérotée malgré la consigne devient un texte suivi, sans titres en gras."""
        texte = ("1. *Plante identifiée* : feuille de maïs.\n2) **Diagnostic probable** : rouille.\n"
                 "- Arrachez les plants très atteints.\nLe *champignon* aime l'humidité.")
        self.assertEqual(diagnostic.sans_liste(texte), "feuille de maïs.\nrouille.\nArrachez les plants très "
                                                        "atteints.\nLe champignon aime l'humidité.")
        self.assertEqual(diagnostic.sans_liste("Pluie de 20 mm en 3 jours."), "Pluie de 20 mm en 3 jours.")


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
        for texte in ("Il s'agit probablement de la rouille.",
                      "Il s'agit probablement de la rouille.\n⚠️ Avis indicatif, voyez un agent agricole."):
            d = diagnostic.diagnostiquer(JPEG, "image/jpeg", None, session=self.appel(interaction(texte)), cle="c")
            self.assertEqual(d.texte, "Il s'agit probablement de la rouille.\n\n" + AVERTISSEMENT_DIAGNOSTIC)

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

    def test_quota_epuise_met_gemini_en_pause(self):
        """Après un 429, les appels suivants échouent aussitôt, sans requête ni pause."""
        session = mock.Mock()
        session.post.return_value = mock.Mock(status_code=429)
        try:
            with self.assertRaises(diagnostic.QuotaEpuise):
                diagnostic.appeler({}, session=session, cle="c")
            with self.assertRaises(diagnostic.QuotaEpuise):
                diagnostic.appeler({}, session=session, cle="c")
            self.assertEqual(session.post.call_count, 1)
        finally:
            diagnostic._quota_epuise_jusqua.clear()

    def test_modele_de_secours_si_le_premier_echoue(self):
        """Quota épuisé ou panne du premier modèle, la photo est analysée par le second."""
        def poste(adresse, json, timeout, headers):
            if json["model"] == "gemini-3.5-flash":
                return mock.Mock(status_code=429)
            reponse = mock.Mock(status_code=200)
            reponse.json.return_value = interaction(REPONSE)
            return reponse
        session = mock.Mock()
        session.post.side_effect = poste
        try:
            d = diagnostic.diagnostiquer(JPEG, "image/jpeg", "maïs", session=session, cle="c")
            self.assertEqual(d.statut, "analyse")
            self.assertEqual([c.kwargs["json"]["model"] for c in session.post.call_args_list],
                             ["gemini-3.5-flash", "gemini-3.5-flash-lite"])
            session.post.reset_mock()
            diagnostic.diagnostiquer(JPEG, "image/jpeg", "maïs", session=session, cle="c")
            self.assertEqual([c.kwargs["json"]["model"] for c in session.post.call_args_list],
                             ["gemini-3.5-flash-lite"], "le modèle épuisé reste en pause")
        finally:
            diagnostic._quota_epuise_jusqua.clear()

    def test_delai_court(self):
        """Une attente de plus de 40 secondes passe au modèle de secours au lieu de bloquer l'agriculteur."""
        self.assertLessEqual(diagnostic.DELAI_SECONDES, 45)

    def test_agent_platform_si_configure(self):
        with mock.patch.dict("os.environ", {"AGENT_PLATFORM_PROJET": "mon-projet", "AGENT_PLATFORM_API_KEY": "cle-ap",
                                            "GEMINI_API_KEY": "cle-studio"}):
            adresse, cle = diagnostic.acces()
        self.assertEqual(adresse, "https://aiplatform.googleapis.com/v1/projects/mon-projet/locations/global/interactions")
        self.assertEqual(cle, "cle-ap")
        with mock.patch.dict("os.environ", {"AGENT_PLATFORM_PROJET": "", "GEMINI_API_KEY": "cle-studio"}):
            self.assertEqual(diagnostic.acces(), (diagnostic.ADRESSE, "cle-studio"))

    def test_sans_cle(self):
        with mock.patch.dict("os.environ", {}, clear=True), self.assertRaises(RuntimeError):
            diagnostic.appeler({}, session=mock.Mock())


if __name__ == "__main__":
    unittest.main()

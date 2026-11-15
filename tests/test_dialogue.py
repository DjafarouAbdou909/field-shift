import os
import unittest
from unittest import mock

from bot import dialogue
from bot.langage import gabarits
from bot.sessions import Sessions
from moteur.contrat import AVERTISSEMENT_DIAGNOSTIC, Diagnostic
from moteur.diagnostic import ORIGINE

NUMERO = "2250700000000"


class FauxCanal:
    """Garde les envois au lieu de les faire, et sert une image ou un audio de test."""

    def __init__(self):
        self.envois = []

    def envoyer_texte(self, destinataire, texte):
        self.envois.append(("texte", destinataire, texte))

    def envoyer_boutons(self, destinataire, texte, boutons):
        self.envois.append(("boutons", destinataire, texte, dict(boutons)))

    def envoyer_liste(self, destinataire, texte, lignes, libelle):
        self.envois.append(("liste", destinataire, texte, dict(lignes)))

    def envoyer_audio(self, destinataire, audio):
        self.envois.append(("audio", destinataire, audio))

    def telecharger_media(self, media_id):
        return b"contenu-" + media_id.encode()


def texte(corps):
    return {"from": NUMERO, "id": "w", "type": "text", "text": {"body": corps}}


def bouton(identifiant):
    return {"from": NUMERO, "id": "w", "type": "interactive",
            "interactive": {"type": "button_reply", "button_reply": {"id": identifiant, "title": "x"}}}


def ligne(identifiant):
    return {"from": NUMERO, "id": "w", "type": "interactive",
            "interactive": {"type": "list_reply", "list_reply": {"id": identifiant, "title": "x"}}}


def position(lat, lon):
    return {"from": NUMERO, "id": "w", "type": "location", "location": {"latitude": lat, "longitude": lon}}


def image(mime="image/jpeg", legende=None):
    contenu = {"id": "img1", "mime_type": mime}
    if legende:
        contenu["caption"] = legende
    return {"from": NUMERO, "id": "w", "type": "image", "image": contenu}


def audio():
    return {"from": NUMERO, "id": "w", "type": "audio",
            "audio": {"id": "aud1", "mime_type": "audio/ogg; codecs=opus", "voice": True}}


class Base(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"SEL_NUMEROS": "sel-de-test"})
        self.env.start()
        self.canal, self.magasin = FauxCanal(), Sessions(":memory:")
        # Aucun appel réseau dans les tests, Gemini et Aethex sont simulés au besoin.
        self.sans_reseau = [mock.patch.object(dialogue.comprehension, "appeler", side_effect=RuntimeError("hors ligne")),
                            mock.patch.object(dialogue.conversation, "appeler", side_effect=RuntimeError("hors ligne")),
                            mock.patch.object(dialogue.voix, "synthetiser", return_value=b"OggS-voix"),
                            mock.patch.object(dialogue.transcription_locale, "transcrire",
                                              side_effect=RuntimeError("modèle non chargé"))]
        for patch in self.sans_reseau:
            patch.start()

    def tearDown(self):
        for patch in self.sans_reseau:
            patch.stop()
        self.env.stop()

    def envoyer(self, *messages):
        self.canal.envois.clear()
        for message in messages:
            dialogue.traiter(message, canal=self.canal, magasin=self.magasin)
        return self.canal.envois

    def session(self):
        from bot.securite import empreinte_numero
        return self.magasin.lire(empreinte_numero(NUMERO, "sel-de-test"))

    def consentir(self):
        self.envoyer(texte("Bonjour"), bouton("accepte"))


class TestConsentement(Base):
    def test_premier_message_demande_le_consentement(self):
        envois = self.envoyer(texte("Salut"))
        self.assertEqual(envois, [("boutons", NUMERO, gabarits.accueil(), gabarits.BOUTONS_CONSENTEMENT)])
        self.assertEqual(self.session().etat, "consentement")

    def test_acceptation_puis_menu(self):
        envois = self.envoyer(texte("Bonjour"), bouton("accepte"))
        self.assertEqual(envois[-1][3], gabarits.BOUTONS_MENU)
        self.assertTrue(self.session().consentement)

    def test_refus_efface_tout(self):
        envois = self.envoyer(texte("Bonjour"), bouton("refuse"))
        self.assertEqual(envois[-1][2], gabarits.refus())
        self.assertEqual(self.session().etat, "accueil")
        self.assertFalse(self.session().consentement)

    def test_rien_sans_consentement(self):
        """Un choix envoyé avant le consentement ramène à l'accueil."""
        envois = self.envoyer(ligne("korhogo"))
        self.assertEqual(envois[-1][2], gabarits.accueil())

    def test_stop_efface(self):
        self.consentir()
        envois = self.envoyer(texte("STOP"))
        self.assertEqual(envois[-1][2], gabarits.efface())
        self.assertFalse(self.session().consentement)

    def test_numero_jamais_stocke_en_clair(self):
        self.consentir()
        lignes = self.magasin._connexion.execute("SELECT * FROM sessions").fetchall()
        self.assertTrue(lignes)
        self.assertNotIn(NUMERO, repr(lignes))


class TestConseilDeRotation(Base):
    def test_parcours_complet_sur_donnees_reelles(self):
        self.consentir()
        envois = self.envoyer(bouton("rotation"))
        self.assertEqual(envois[-1][3], gabarits.LIGNES_LIEUX)
        envois = self.envoyer(ligne("korhogo"))
        self.assertEqual(envois[-1][3], gabarits.LIGNES_ROTATIONS)
        envois = self.envoyer(ligne("coton_mais"))
        self.assertEqual(envois[-1][3], gabarits.BOUTONS_PRIORITE)
        envois = self.envoyer(bouton("eau"))
        resume = envois[1][2]
        self.assertIn("Pour Korhogo", resume)
        self.assertIn("conseiller ANADER", resume)
        self.assertEqual(envois[-1][3], gabarits.BOUTONS_RESULTAT)
        self.assertEqual(self.session().etat, "resultat")
        self.assertIn("Pourquoi", self.envoyer(bouton("pourquoi"))[0][2])
        self.assertIn("lieu=korhogo", self.envoyer(bouton("detail"))[0][2])

    def test_texte_a_la_place_des_boutons(self):
        """Le titre, l'identifiant ou le numéro d'une option valent un clic."""
        self.consentir()
        self.envoyer(texte("Conseil rotation"), texte("Bouaké"), texte("2"))
        s = self.session()
        self.assertEqual((s.lieu, s.rotation, s.etat), ("bouake", "coton_niebe_mais", "priorite"))

    def test_position_dans_la_zone(self):
        self.consentir()
        self.envoyer(bouton("rotation"))
        self.envoyer(position(9.5, -5.6))
        self.assertEqual(self.session().lieu, "korhogo")

    def test_position_hors_zone(self):
        self.consentir()
        self.envoyer(bouton("rotation"))
        envois = self.envoyer(position(5.35, -4.0))
        self.assertEqual(envois[0][2], gabarits.zone_non_couverte())
        self.assertEqual(self.session().etat, "lieu")

    def test_question_libre_sous_garde_fou(self):
        self.consentir()
        self.envoyer(bouton("rotation"), ligne("korhogo"), ligne("coton_mais"), bouton("eau"))
        with mock.patch.object(dialogue.reformulation, "appeler", side_effect=RuntimeError("sans réseau")):
            envois = self.envoyer(texte("Et si je plante du manioc ?"))
        self.assertIn("Pour Korhogo", envois[0][2])

    def test_ecouter_sans_voix(self):
        self.consentir()
        self.envoyer(bouton("rotation"), ligne("korhogo"), ligne("coton_mais"), bouton("eau"))
        with mock.patch.object(dialogue.voix, "configuree", return_value=False):
            envois = self.envoyer(bouton("ecouter"))
        self.assertEqual(envois[0][2], gabarits.voix_indisponible())

    def test_ecouter_avec_voix(self):
        self.consentir()
        self.envoyer(bouton("rotation"), ligne("korhogo"), ligne("coton_mais"), bouton("eau"))
        with mock.patch.object(dialogue.voix, "configuree", return_value=True), \
                mock.patch.object(dialogue.voix, "synthetiser", return_value=b"OggS-note"):
            envois = self.envoyer(bouton("ecouter"))
        self.assertEqual(envois[0], ("audio", NUMERO, b"OggS-note"))


class TestPhoto(Base):
    TEXTE = "*Plante identifiée* : feuille de coton.\n*Recommandation concrète* : action.\n\n" + AVERTISSEMENT_DIAGNOSTIC

    def diagnostic(self, contenu, type_image, culture=None):
        self.recu = (contenu, type_image, culture)
        return Diagnostic(donnees_fictives=False, culture_declaree=culture, statut="analyse", texte=self.TEXTE,
                          origine_images=ORIGINE)

    def test_parcours_par_le_menu(self):
        self.consentir()
        envois = self.envoyer(bouton("photo"))
        self.assertEqual(envois[-1][2], gabarits.consentement_photo())
        envois = self.envoyer(bouton("photo_accepte"))
        self.assertEqual(envois[-1][2], gabarits.demande_photo())
        with mock.patch.object(dialogue, "diagnostiquer", side_effect=self.diagnostic):
            envois = self.envoyer(image(legende="coton"))
        self.assertEqual(self.recu, (b"contenu-img1", "image/jpeg", "coton"))
        self.assertEqual(envois[0][2], self.TEXTE)
        self.assertEqual(self.session().etat, "menu")
        envois = self.envoyer(bouton("photo"))
        self.assertEqual(envois[-1][2], gabarits.demande_photo(), "le consentement photo est demandé une fois")

    def test_photo_envoyee_directement_puis_consentement(self):
        """Comme dans agri-bot, une photo peut arriver à toute étape, elle attend l'accord puis est analysée."""
        self.consentir()
        self.envoyer(bouton("rotation"), ligne("korhogo"))
        with mock.patch.object(dialogue, "diagnostiquer", side_effect=self.diagnostic) as appel:
            envois = self.envoyer(image())
            appel.assert_not_called()
            self.assertEqual(envois[-1][2], gabarits.consentement_photo())
            self.assertEqual(self.session().photo_en_attente, "img1|image/jpeg")
            envois = self.envoyer(bouton("photo_accepte"))
        self.assertEqual(self.recu, (b"contenu-img1", "image/jpeg", None))
        self.assertEqual(envois[0][2], self.TEXTE)
        self.assertIsNone(self.session().photo_en_attente)
        self.assertTrue(self.session().consentement_photo)

    def test_photo_analysee_sans_redemander(self):
        self.consentir()
        self.envoyer(bouton("photo"), bouton("photo_accepte"))
        with mock.patch.object(dialogue, "diagnostiquer", side_effect=self.diagnostic):
            envois = self.envoyer(image())
        self.assertEqual(envois[0][2], self.TEXTE)

    def test_refus_de_la_photo_oublie_l_attente(self):
        self.consentir()
        self.envoyer(image())
        envois = self.envoyer(bouton("photo_refuse"))
        self.assertIn(("texte", NUMERO, gabarits.refus_photo()), envois)
        self.assertFalse(self.session().consentement_photo)
        self.assertIsNone(self.session().photo_en_attente)

    def test_image_hors_format(self):
        self.consentir()
        self.envoyer(bouton("photo"), bouton("photo_accepte"))
        with mock.patch.object(dialogue, "diagnostiquer") as appel:
            envois = self.envoyer(image("image/gif"))
        appel.assert_not_called()
        self.assertEqual(envois[0][2], dialogue.FORMAT_REFUSE)


class TestVocal(Base):
    """Si l'agriculteur parle, le bot répond seulement en note vocale, les boutons restant sous un signe."""

    def vocal(self, ecoute=None, configuree=True, transcription=""):
        with mock.patch.object(dialogue.voix, "configuree", return_value=configuree), \
                mock.patch.object(dialogue.comprehension, "ecouter", return_value=ecoute) as ecouter, \
                mock.patch.object(dialogue.voix, "transcrire", return_value=transcription):
            envois = self.envoyer(audio())
        self.ecouter = ecouter
        return envois

    def types(self, envois):
        return [e[0] for e in envois]

    def test_accueil_parle_sans_texte(self):
        envois = self.vocal()
        self.ecouter.assert_not_called()
        self.assertEqual(self.types(envois), ["audio", "boutons"])
        self.assertEqual(envois[1][2], gabarits.INVITE_CHOIX)

    def test_consentement_donne_a_la_voix(self):
        self.envoyer(texte("Bonjour"))
        envois = self.vocal(("Oui je suis d'accord", "accepte"))
        self.assertTrue(self.session().consentement)
        self.assertEqual(self.types(envois), ["audio", "boutons"])
        self.assertEqual(envois[-1][3], gabarits.BOUTONS_MENU)

    def test_question_vocale_recoit_une_reponse_vocale(self):
        """Une question dite reçoit une réponse dite, sans lancer de calcul de rotation."""
        self.consentir()
        with mock.patch.object(dialogue.conversation, "repondre",
                               return_value=("question", "Semez le niébé après les premières pluies.", "Quand semer ?")):
            envois = self.vocal()
        self.assertEqual(self.types(envois), ["audio"])
        self.assertEqual(self.session().etat, "menu")

    def test_demande_de_rotation_dite(self):
        self.consentir()
        with mock.patch.object(dialogue.conversation, "repondre", return_value=("rotation", "", "je veux une rotation")):
            envois = self.vocal()
        self.assertEqual(self.types(envois), ["audio", "liste"])
        self.assertEqual(envois[-1][3], gabarits.LIGNES_LIEUX)
        self.assertEqual(self.session().etat, "lieu")

    def test_choix_dits_jusqu_au_resultat(self):
        self.consentir()
        with mock.patch.object(dialogue.conversation, "repondre", return_value=("rotation", "", "rotation")):
            self.vocal()
        self.vocal(("à côté de Korhogo", "korhogo"))
        self.vocal(("coton et maïs", "coton_mais"))
        envois = self.vocal(("l'eau", "eau"))
        s = self.session()
        self.assertEqual((s.lieu, s.rotation, s.priorite, s.etat), ("korhogo", "coton_mais", "eau", "resultat"))
        self.assertNotIn("texte", self.types(envois), "aucun texte quand l'agriculteur parle")

    def test_stop_dit_en_discussion(self):
        self.consentir()
        with mock.patch.object(dialogue.conversation, "repondre", return_value=("question", "x", "Stop.")):
            self.vocal()
        self.assertFalse(self.session().consentement)

    def test_voix_en_panne_repli_sur_le_texte(self):
        self.consentir()
        with mock.patch.object(dialogue.voix, "synthetiser", side_effect=RuntimeError("Aethex")), \
                mock.patch.object(dialogue.conversation, "repondre", return_value=("question", "Réponse.", "q")):
            envois = self.vocal()
        self.assertEqual(envois, [("texte", NUMERO, "Réponse.")])

    def test_secours_local_en_discussion(self):
        """Gemini à court de quota, Whisper transcrit la note et la demande de rotation est comprise."""
        self.consentir()
        with mock.patch.object(dialogue.transcription_locale, "transcrire",
                               return_value="Je voudrais savoir quelle rotation faire") as locale:
            envois = self.vocal()
        locale.assert_called_once()
        self.assertEqual(self.types(envois), ["audio", "liste"])
        self.assertEqual(self.session().etat, "lieu")

    def test_secours_local_question_libre(self):
        self.consentir()
        with mock.patch.object(dialogue.transcription_locale, "transcrire", return_value="Quand semer le maïs ?"):
            envois = self.vocal()
        self.assertEqual(self.types(envois), ["audio"])
        self.assertEqual(self.session().etat, "menu")

    def test_secours_local_pour_un_choix(self):
        self.consentir()
        self.envoyer(bouton("rotation"))
        with mock.patch.object(dialogue.transcription_locale, "transcrire", return_value="Mon champ est à Korhogo"):
            self.vocal(None)
        self.assertEqual(self.session().lieu, "korhogo")

    def test_vocal_sans_service_hors_discussion(self):
        self.consentir()
        self.envoyer(bouton("rotation"))
        envois = self.vocal(None, configuree=False)
        self.assertEqual(envois[0][2], gabarits.vocal_indisponible())

    def test_vocal_vide(self):
        self.consentir()
        self.envoyer(bouton("rotation"))
        envois = self.vocal(("", None))
        self.assertEqual(self.types(envois), ["audio"])
        self.assertEqual(self.session().etat, "lieu")


class TestDiscussion(Base):
    def test_question_ecrite_reponse_ecrite(self):
        self.consentir()
        with mock.patch.object(dialogue.conversation, "repondre",
                               return_value=("question", "Le niébé enrichit le sol en azote.", "q")) as repondre:
            envois = self.envoyer(texte("À quoi sert le niébé ?"))
        self.assertEqual(envois, [("texte", NUMERO, "Le niébé enrichit le sol en azote.")])
        self.assertEqual(repondre.call_args.kwargs["question"], "À quoi sert le niébé ?")

    def test_demande_de_rotation_ecrite(self):
        self.consentir()
        with mock.patch.object(dialogue.conversation, "repondre", return_value=("rotation", "", "q")):
            envois = self.envoyer(texte("Je veux un conseil de rotation pour mon champ"))
        self.assertEqual(envois[-1][3], gabarits.LIGNES_LIEUX)

    def test_service_indisponible(self):
        """Sans Gemini, une question libre reçoit un message honnête, une demande de rotation est comprise."""
        self.consentir()
        envois = self.envoyer(texte("Quand semer le maïs ?"))
        self.assertEqual(envois, [("texte", NUMERO, gabarits.discussion_indisponible())])
        envois = self.envoyer(texte("Je veux un conseil de rotation"))
        self.assertEqual(envois[-1][3], gabarits.LIGNES_LIEUX)

    def test_diagnostic_sans_produit(self):
        self.consentir()
        self.envoyer(bouton("photo"), bouton("photo_accepte"))
        texte_modele = ("*Recommandation concrète* : Arrachez les plants atteints. Pulvérisez un fongicide.\n\n"
                        + AVERTISSEMENT_DIAGNOSTIC)
        resultat = Diagnostic(donnees_fictives=False, statut="analyse", texte=texte_modele, origine_images=ORIGINE)
        with mock.patch.object(dialogue, "diagnostiquer", return_value=resultat):
            envois = self.envoyer(image())
        self.assertNotIn("fongicide", envois[0][2])
        self.assertIn("Arrachez les plants atteints.", envois[0][2])
        self.assertTrue(envois[0][2].endswith(AVERTISSEMENT_DIAGNOSTIC))


class TestErreurs(Base):
    def test_erreur_technique_annoncee(self):
        self.consentir()
        self.envoyer(bouton("rotation"), ligne("korhogo"), ligne("coton_mais"))
        with mock.patch.object(dialogue, "recommander", side_effect=RuntimeError("panne")):
            envois = self.envoyer(bouton("eau"))
        self.assertEqual(envois[-1][2], gabarits.erreur_technique())

    def test_message_sans_numero_ignore(self):
        self.envoyer({"id": "w", "type": "text", "text": {"body": "Bonjour"}})
        self.assertEqual(self.canal.envois, [])


if __name__ == "__main__":
    unittest.main()

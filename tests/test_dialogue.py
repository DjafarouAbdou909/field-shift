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

    def envoyer_image(self, destinataire, image, legende=""):
        self.envois.append(("image", destinataire, image[:8], legende))

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
        self.env = mock.patch.dict(os.environ, {"SEL_NUMEROS": "sel-de-test", "GROQ_API_KEY": ""})
        self.env.start()
        self.canal, self.magasin = FauxCanal(), Sessions(":memory:")
        # Aucun appel réseau dans les tests, Gemini et Aethex sont simulés au besoin.
        self.sans_reseau = [mock.patch.object(dialogue.voix, "synthetiser", return_value=b"OggS-voix"),
                            mock.patch.object(dialogue.voix, "synthetiser_phrase_fixe", return_value=b"OggS-voix"),
                            mock.patch.object(dialogue.transcription_locale, "transcrire",
                                              side_effect=RuntimeError("modèle non chargé")),
                            mock.patch.object(dialogue.geocodage, "chercher", return_value=None),
                            mock.patch.object(dialogue, "en_fond", side_effect=lambda tache: tache())]
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
        self.assertEqual(envois, [("texte", NUMERO, gabarits.accueil()),
                                  ("boutons", NUMERO, gabarits.consentement(), gabarits.BOUTONS_CONSENTEMENT)])
        self.assertIn("https://conseil-rotation-ci.netlify.app", envois[0][2])
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
        self.assertEqual(envois[0][2], gabarits.accueil())

    def test_stop_efface(self):
        self.consentir()
        envois = self.envoyer(texte("STOP"))
        self.assertEqual(envois[-1][2], gabarits.efface())
        self.assertFalse(self.session().consentement)

    def test_booleens_relus_correctement(self):
        """Une colonne ajoutée après coup rend 0 sous la forme '0', qui ne doit pas valoir vrai."""
        self.consentir()
        self.magasin._connexion.execute("UPDATE sessions SET mode_vocal = '0', consentement_photo = '0'")
        s = self.session()
        self.assertFalse(s.mode_vocal)
        self.assertFalse(s.consentement_photo)
        self.assertTrue(s.consentement)

    def test_numero_jamais_stocke_en_clair(self):
        self.consentir()
        lignes = self.magasin._connexion.execute("SELECT * FROM sessions").fetchall()
        self.assertTrue(lignes)
        self.assertNotIn(NUMERO, repr(lignes))


class TestConseilDeRotation(Base):
    def test_parcours_complet_sur_donnees_reelles(self):
        self.consentir()
        envois = self.envoyer(bouton("rotation"))
        self.assertEqual(envois[-1][2], gabarits.demande_lieu())
        envois = self.envoyer(ligne("korhogo"))
        self.assertEqual(envois[-1][3], gabarits.LIGNES_ROTATIONS)
        envois = self.envoyer(ligne("coton_mais"))
        self.assertEqual(envois[-1][3], gabarits.BOUTONS_PRIORITE)
        envois = self.envoyer(bouton("eau"))
        resume = envois[1][2]
        self.assertIn("À Korhogo", resume)
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
        """Bamako est à plus de 150 km de toute ville couverte."""
        self.consentir()
        self.envoyer(bouton("rotation"))
        envois = self.envoyer(position(12.64, -8.0))
        self.assertEqual(envois[0][2], gabarits.zone_non_couverte())
        self.assertEqual(self.session().etat, "lieu")

    def test_position_loin_d_une_ville_annoncee(self):
        self.consentir()
        self.envoyer(bouton("rotation"))
        envois = self.envoyer(position(9.75, -5.95))
        self.assertTrue(envois[0][2].startswith("Votre champ est à environ"), envois[0][2])
        self.assertEqual(self.session().lieu, "korhogo")

    def test_nouvelle_ville_de_savane_nommee_dans_une_phrase(self):
        self.consentir()
        self.envoyer(bouton("rotation"))
        envois = self.envoyer(texte("mon champ est vers Ferké"))
        self.assertEqual((self.session().lieu, self.session().etat), ("ferkessedougou", "rotation"))
        self.assertEqual(envois[-1][3], gabarits.LIGNES_ROTATIONS)

    def test_village_retrouve_sur_openstreetmap(self):
        """Un village fictif près de Korhogo, qui n'est pas une ville couverte, est rattaché à la plus proche."""
        self.consentir()
        self.envoyer(bouton("rotation"))
        with mock.patch.object(dialogue.geocodage, "chercher", return_value=(9.55, -5.75, "Villagetest", None)) as cherche:
            envois = self.envoyer(texte("j'habite à Villagetest"))
        cherche.assert_called_once_with("villagetest")
        self.assertIn("Villagetest, d'après OpenStreetMap, est à environ", envois[0][2])
        self.assertIn("Korhogo", envois[0][2])
        self.assertEqual(self.session().lieu, "korhogo")

    def test_village_rattache_au_chef_lieu_de_sa_region(self):
        """Un village fictif du Poro, plus proche de Ferkessédougou, prend les données de Korhogo, chef-lieu du Poro."""
        self.consentir()
        self.envoyer(bouton("rotation"))
        with mock.patch.object(dialogue.geocodage, "chercher", return_value=(9.58, -5.38, "Villagetest", "Poro")):
            envois = self.envoyer(texte("Villagetest"))
        self.assertIn("est dans la région Poro, à environ", envois[0][2])
        self.assertEqual(self.session().lieu, "korhogo")

    def test_sud_forestier_sans_rotation_pour_l_instant(self):
        self.consentir()
        self.envoyer(bouton("rotation"))
        envois = self.envoyer(position(5.35, -4.0))
        self.assertTrue(envois[-1][2].startswith("Voici ce que disent 25 ans de mesures satellite de la NASA"))
        self.assertIn("zone d'Abidjan", envois[-1][2])
        self.assertIn("conseiller ANADER", envois[-1][2])
        self.assertEqual((self.session().lieu, self.session().etat), ("abidjan", "menu"))

    def test_question_libre_sous_garde_fou(self):
        self.consentir()
        self.envoyer(bouton("rotation"), ligne("korhogo"), ligne("coton_mais"), bouton("eau"))
        envois = self.envoyer(texte("Et si je plante du manioc ?"))
        self.assertIn("À Korhogo", envois[0][2])

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


class TestAlerteDeVegetation(Base):
    """Bouton Végétation, alerte HLS de la zone en mots simples, la ville étant demandée si elle manque."""

    def alerte(self, statut="normale"):
        from moteur.alerte import construire_alerte
        return construire_alerte("korhogo", "2026-11-02", {
            "statut": statut, "valeur": 0.654 if statut == "normale" else 0.55, "seuil": 0.601, "observations_reference": 30, "annees_reference": 13,
            "observations_courantes": 3})

    def test_ville_demandee_puis_alerte(self):
        self.consentir()
        with mock.patch.object(dialogue, "alerte_du_lieu", return_value=self.alerte()) as calcul:
            envois = self.envoyer(bouton("vegetation"))
            self.assertEqual(envois[-1][2], gabarits.demande_lieu_vegetation())
            self.assertEqual(self.session().etat, "alerte_lieu")
            envois = self.envoyer(ligne("korhogo"))
        calcul.assert_called_once_with("korhogo")
        self.assertIn("2 novembre 2026", envois[0][2])
        self.assertIn("valeurs habituelles", envois[0][2])
        self.assertEqual((self.session().etat, self.session().lieu), ("menu", "korhogo"))

    def test_ville_deja_connue(self):
        self.consentir()
        self.envoyer(bouton("rotation"), ligne("korhogo"))
        self.envoyer(texte("bonjour"))
        with mock.patch.object(dialogue, "alerte_du_lieu", return_value=self.alerte("faible")):
            envois = self.envoyer(bouton("vegetation"))
        self.assertIn("plus faible que d'habitude", envois[0][2])

    def test_demande_dite_avec_le_mot_vegetation(self):
        self.consentir()
        with mock.patch.object(dialogue.groq, "configure", return_value=True), \
                mock.patch.object(dialogue.groq, "repondre") as groq:
            envois = self.envoyer(texte("Comment va la végétation chez moi ?"))
        groq.assert_not_called()
        self.assertEqual(envois[-1][2], gabarits.demande_lieu_vegetation())

    def test_alerte_en_panne(self):
        self.consentir()
        with mock.patch.object(dialogue, "alerte_du_lieu", side_effect=ValueError("hls")):
            envois = self.envoyer(bouton("vegetation"), ligne("bouake"))
        self.assertTrue(envois[-1][2].startswith(gabarits.alerte_indisponible()))
        self.assertTrue(envois[-1][2].endswith(gabarits.invitation_champ()))

    def test_ville_sans_images_satellite(self):
        """Une nouvelle ville n'a pas encore d'extraction HLS, le bot le dit au lieu d'une panne."""
        self.consentir()
        envois = self.envoyer(bouton("vegetation"), texte("Odienné"))
        self.assertTrue(envois[-1][2].startswith(gabarits.alerte_pas_encore("Odienné")))

    def carte(self, faibles=0, date="2026-11-14"):
        import numpy as np
        from moteur.champ import CarteChamp
        statuts = np.full((15, 15), "normale", dtype=object)
        statuts[2:4, 10:13] = "faible" if faibles else "normale"
        return CarteChamp(date, statuts, 57, "T29PRL", list(range(2013, 2026)))

    def test_position_envoyee_donne_la_carte_du_champ(self):
        """Le satellite fait le tour du champ, la carte arrive en image avec son explication."""
        self.consentir()
        self.envoyer(bouton("vegetation"))
        with mock.patch.object(dialogue, "carte_du_jour", return_value=self.carte(faibles=6)) as calcul:
            envois = self.envoyer(position(9.55, -5.75))
        calcul.assert_called_once_with(9.55, -5.75)
        self.assertEqual([e[0] for e in envois], ["texte", "image", "texte"])
        self.assertEqual(envois[0][2], gabarits.carte_en_cours())
        self.assertEqual(envois[1][2], b"\x89PNG\r\n\x1a\n", "une vraie image PNG")
        self.assertIn("6 carrés sur 225 sont en rouge", envois[2][2])
        self.assertIn("vers le nord-est", envois[2][2])
        self.assertIn("Quelques carrés rouges isolés", envois[2][2])
        self.assertEqual(self.session().etat, "menu")
        self.assertIsNone(self.session().lieu, "la position du champ n'est jamais gardée")

    def test_position_au_menu_donne_aussi_la_carte(self):
        self.consentir()
        with mock.patch.object(dialogue, "carte_du_jour", return_value=self.carte()):
            envois = self.envoyer(position(9.55, -5.75))
        self.assertIn("Toute la partie mesurée est verte", envois[-1][2])

    def test_nuages_partout_sans_image(self):
        self.consentir()
        with mock.patch.object(dialogue, "carte_du_jour", return_value=self.carte(date=None)):
            envois = self.envoyer(position(9.55, -5.75))
        self.assertEqual([e[0] for e in envois], ["texte", "texte"])
        self.assertIn("nuages ont caché votre champ", envois[-1][2])

    def test_carte_en_panne(self):
        self.consentir()
        with mock.patch.object(dialogue, "carte_du_jour", side_effect=RuntimeError("Earthdata")):
            envois = self.envoyer(position(9.55, -5.75))
        self.assertEqual(envois[-1][2], gabarits.carte_indisponible())


class TestPhoto(Base):
    TEXTE = "*Plante identifiée* : feuille de coton.\n*Recommandation concrète* : action.\n\n" + AVERTISSEMENT_DIAGNOSTIC

    def diagnostic(self, contenu, type_image, culture=None):
        self.recu = (contenu, type_image, culture)
        return Diagnostic(donnees_fictives=False, culture_declaree=culture, statut="analyse", texte=self.TEXTE,
                          origine_images=ORIGINE)

    def test_parcours_par_le_menu(self):
        self.consentir()
        envois = self.envoyer(bouton("photo"))
        self.assertEqual(envois[-1][2], gabarits.demande_photo(), "aucun second accord pour les photos")
        with mock.patch.object(dialogue, "diagnostiquer", side_effect=self.diagnostic):
            envois = self.envoyer(image(legende="coton"))
        self.assertEqual(self.recu, (b"contenu-img1", "image/jpeg", "coton"))
        self.assertEqual(envois[0][2], self.TEXTE)
        self.assertEqual(self.session().etat, "menu")

    def test_photo_envoyee_directement_analysee_aussitot(self):
        """Comme dans agri-bot, une photo peut arriver à toute étape, et elle est analysée sans question."""
        self.consentir()
        self.envoyer(bouton("rotation"), ligne("korhogo"))
        with mock.patch.object(dialogue, "diagnostiquer", side_effect=self.diagnostic):
            envois = self.envoyer(image())
        self.assertEqual(self.recu, (b"contenu-img1", "image/jpeg", None))
        self.assertEqual(envois[0][2], self.TEXTE)
        self.assertEqual(len(envois), 1)

    def test_photo_avant_l_accord_analysee_apres_le_oui(self):
        with mock.patch.object(dialogue, "diagnostiquer", side_effect=self.diagnostic) as appel:
            envois = self.envoyer(image())
            appel.assert_not_called()
            self.assertEqual(envois[-1][2], gabarits.consentement())
            self.assertEqual(self.session().photo_en_attente, "img1|image/jpeg")
            envois = self.envoyer(bouton("accepte"))
        self.assertEqual(envois[0][2], self.TEXTE)
        self.assertIsNone(self.session().photo_en_attente)
        self.assertTrue(self.session().consentement)

    def test_photo_avant_un_refus_oubliee(self):
        self.envoyer(image())
        with mock.patch.object(dialogue, "diagnostiquer") as appel:
            self.envoyer(bouton("refuse"))
        appel.assert_not_called()
        self.assertFalse(self.magasin._connexion.execute(
            "SELECT 1 FROM sessions WHERE photo_en_attente IS NOT NULL").fetchall(), "le refus efface la photo en attente")

    def test_ancienne_etape_d_accord_photo(self):
        """Une session restée sur l'ancienne étape d'accord photo passe à la photo."""
        self.consentir()
        self.magasin._connexion.execute("UPDATE sessions SET etat = 'consentement_photo'")
        envois = self.envoyer(texte("oui"))
        self.assertEqual(envois[-1][2], gabarits.demande_photo())

    def test_image_hors_format(self):
        self.consentir()
        with mock.patch.object(dialogue, "diagnostiquer") as appel:
            envois = self.envoyer(image("image/gif"))
        appel.assert_not_called()
        self.assertEqual(envois[0][2], dialogue.FORMAT_REFUSE)


class TestVocal(Base):
    """Si l'agriculteur parle, le bot répond seulement en note vocale, les boutons restant sous un signe."""

    def vocal(self, transcription="", configuree=True):
        with mock.patch.object(dialogue.voix, "configuree", return_value=configuree), \
                mock.patch.object(dialogue, "transcrire_note", return_value=transcription) as transcrire:
            envois = self.envoyer(audio())
        self.transcrire = transcrire
        return envois

    def avec_groq(self, **reponses):
        """Groq disponible, ses fonctions remplacées par des réponses fixes."""
        patches = [mock.patch.object(dialogue.groq, "configure", return_value=True)]
        patches += [mock.patch.object(dialogue.groq, nom, return_value=valeur) for nom, valeur in reponses.items()]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def types(self, envois):
        return [e[0] for e in envois]

    def test_accueil_parle_avec_le_lien_ecrit(self):
        """L'accueil est dit, son lien part par écrit puisqu'un lien ne se dit pas, puis le consentement est dit."""
        envois = self.vocal("peu importe")
        self.transcrire.assert_not_called()
        self.assertEqual(self.types(envois), ["audio", "texte", "audio", "boutons"])
        self.assertEqual(envois[1][2], gabarits.PLATEFORME)
        self.assertEqual(envois[3][2], gabarits.INVITE_CHOIX)

    def test_consentement_donne_a_la_voix(self):
        self.envoyer(texte("Bonjour"))
        envois = self.vocal("Oui je suis d'accord")
        self.assertTrue(self.session().consentement)
        self.assertEqual(self.types(envois), ["audio", "boutons"])
        self.assertEqual(envois[-1][3], gabarits.BOUTONS_MENU)

    def test_question_vocale_recoit_une_reponse_vocale(self):
        """Une question dite reçoit une réponse dite, sans lancer de calcul de rotation."""
        self.consentir()
        self.avec_groq(repondre=("question", "Semez le niébé après les premières pluies."))
        envois = self.vocal("Quand semer le niébé ?")
        self.assertEqual(self.types(envois), ["audio"])
        self.assertEqual(self.session().etat, "menu")

    def test_demande_de_rotation_dite(self):
        self.consentir()
        self.avec_groq(repondre=("rotation", ""))
        envois = self.vocal("Je voudrais savoir quelle rotation faire")
        self.assertEqual(self.types(envois), ["audio"], "la ville est demandée à voix haute, sans liste")
        self.assertEqual(self.session().etat, "lieu")

    def test_choix_dits_jusqu_au_resultat(self):
        self.consentir()
        self.avec_groq(repondre=("rotation", ""))
        self.vocal("Je veux une rotation")
        self.vocal("Mon champ est à côté de Korhogo")
        self.vocal("Je fais du coton et du maïs")
        envois = self.vocal("C'est l'eau qui compte")
        s = self.session()
        self.assertEqual((s.lieu, s.rotation, s.priorite, s.etat), ("korhogo", "coton_mais", "eau", "resultat"))
        self.assertNotIn("texte", self.types(envois), "aucun texte quand l'agriculteur parle")

    def test_groq_comprend_un_choix_deforme(self):
        self.consentir()
        self.envoyer(bouton("rotation"))
        self.avec_groq(choisir="korhogo")
        self.vocal("Mon chat est à côté du robot")
        self.assertEqual(self.session().lieu, "korhogo")

    def test_notes_fixes_identiques_a_celles_du_parcours(self):
        """Les notes préparées au démarrage sont exactement celles que le parcours dit, donc déjà prêtes."""
        dites = []
        with mock.patch.object(dialogue.voix, "synthetiser_phrase_fixe", side_effect=lambda t: dites.append(t) or b"OggS"):
            self.vocal("Bonjour")
            self.vocal("Oui j'accepte")
            self.avec_groq(repondre=("rotation", ""))
            self.vocal("Je veux une rotation")
        self.assertTrue(dites)
        self.assertTrue(set(dites) <= set(dialogue.phrases_fixes()), set(dites) - set(dialogue.phrases_fixes()))

    def test_stop_dit_en_discussion(self):
        self.consentir()
        self.vocal("Stop.")
        self.assertFalse(self.session().consentement)

    def test_voix_en_panne_repli_sur_le_texte(self):
        self.consentir()
        self.avec_groq(repondre=("question", "Réponse."))
        with mock.patch.object(dialogue.voix, "synthetiser", side_effect=RuntimeError("Aethex")), \
                mock.patch.object(dialogue.voix, "synthetiser_phrase_fixe", side_effect=RuntimeError("Aethex")):
            envois = self.vocal("Une question")
        self.assertEqual(envois, [("texte", NUMERO, "Réponse.")])

    def test_sans_groq_message_honnete(self):
        self.consentir()
        envois = self.vocal("Quand semer le maïs ?")
        self.assertEqual(self.types(envois), ["audio"])
        self.assertEqual(self.session().etat, "menu")

    def test_sans_groq_rotation_par_mots_cles(self):
        self.consentir()
        self.vocal("Je veux une rotation")
        self.assertEqual(self.session().etat, "lieu")

    def test_aucune_transcription_possible(self):
        self.consentir()
        envois = self.vocal(None, configuree=False)
        self.assertEqual(envois[0][2], gabarits.vocal_indisponible())

    def test_vocal_vide(self):
        self.consentir()
        self.envoyer(bouton("rotation"))
        envois = self.vocal("")
        self.assertEqual(self.types(envois), ["audio"])
        self.assertEqual(self.session().etat, "lieu")


class TestTranscription(Base):
    def test_groq_puis_local_puis_aethex(self):
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "g"}), \
                mock.patch.object(dialogue.groq, "transcrire", side_effect=RuntimeError("Groq")) as groq_t, \
                mock.patch.object(dialogue.transcription_locale, "transcrire", side_effect=RuntimeError("local")), \
                mock.patch.object(dialogue.voix, "configuree", return_value=True), \
                mock.patch.object(dialogue.voix, "transcrire", return_value="par Aethex") as aethex:
            self.assertEqual(dialogue.transcrire_note(b"OggS", "audio/ogg"), "par Aethex")
        groq_t.assert_called_once()
        aethex.assert_called_once()

    def test_groq_suffit(self):
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "g"}), \
                mock.patch.object(dialogue.groq, "transcrire", return_value="par Groq"), \
                mock.patch.object(dialogue.transcription_locale, "transcrire") as local:
            self.assertEqual(dialogue.transcrire_note(b"OggS", "audio/ogg"), "par Groq")
        local.assert_not_called()


class TestVoixALaDemande(Base):
    """« Je ne sais pas lire, une note vocale stp », échange réel du 20 novembre 2026."""

    DIAGNOSTIC = ("Le problème le plus probable est une attaque de petits insectes sur les jeunes feuilles.\n\n"
                  + AVERTISSEMENT_DIAGNOSTIC)

    def setUp(self):
        super().setUp()
        self.configuree = mock.patch.object(dialogue.voix, "configuree", return_value=True)
        self.configuree.start()
        self.addCleanup(self.configuree.stop)
        dialogue.conversation._memoire.clear()
        self.addCleanup(dialogue.conversation._memoire.clear)

    def diagnostic(self, contenu, type_image, culture=None):
        return Diagnostic(donnees_fictives=False, culture_declaree=culture, statut="analyse",
                          texte=self.DIAGNOSTIC, origine_images=ORIGINE)

    def photo_puis(self, *messages):
        self.consentir()
        with mock.patch.object(dialogue, "diagnostiquer", side_effect=self.diagnostic):
            self.envoyer(image())
        return self.envoyer(*messages)

    def test_relit_le_diagnostic_a_voix_haute(self):
        envois = self.photo_puis(texte("je ne sais pas lire, une note vocale stp"))
        self.assertEqual([e[0] for e in envois], ["audio", "audio"], "un mot qui rassure, puis la relecture")
        dialogue.voix.synthetiser_phrase_fixe.assert_called_with(dialogue.pour_la_voix(gabarits.rassurer_lecture()))
        dialogue.voix.synthetiser.assert_called_with(dialogue.pour_la_voix(self.DIAGNOSTIC))
        self.assertTrue(self.session().voix_demandee)

    def test_ne_sait_pas_ecrire_est_rassure(self):
        """« Je ne sais pas écrire » reçoit d'abord « Pas de souci », échange réel du 20 novembre 2026."""
        self.consentir()
        envois = self.envoyer(texte("je ne sais pas écrire"))
        self.assertEqual([e[0] for e in envois], ["audio"], "le menu n'est pas relu sans un mot")
        dialogue.voix.synthetiser_phrase_fixe.assert_called_with(dialogue.pour_la_voix(gabarits.rassurer_ecriture()))
        self.assertTrue(gabarits.rassurer_ecriture().startswith("Pas de souci, ce n'est pas grave"))
        self.assertTrue(self.session().voix_demandee)

    def test_bonjour_de_retour_et_merci_apres_l_accord(self):
        envois = self.envoyer(texte("Bonjour"), bouton("accepte"))
        self.assertTrue(envois[-1][2].startswith("Merci pour votre confiance."))
        envois = self.envoyer(texte("bonjour"))
        self.assertTrue(envois[-1][2].startswith("Bonjour, content de vous retrouver."))
        self.assertEqual(envois[-1][3], gabarits.BOUTONS_MENU)

    def test_groq_rassure_celui_qui_prefere_parler(self):
        self.consentir()
        mot = "Pas de souci. Parlez-moi avec le micro, je vous réponds à l'oral."
        with mock.patch.object(dialogue.groq, "configure", return_value=True), \
                mock.patch.object(dialogue.groq, "repondre", return_value=("parler", mot)):
            envois = self.envoyer(texte("l'écrit c'est dur pour moi"))
        self.assertEqual([e[0] for e in envois], ["audio"])
        dialogue.voix.synthetiser.assert_called_with(dialogue.pour_la_voix(mot))
        self.assertTrue(self.session().voix_demandee)

    def test_reste_en_voix_meme_a_l_ecrit_puis_revient_a_l_ecrit(self):
        self.photo_puis(texte("en audio svp"))
        envois = self.envoyer(bouton("rotation"))
        self.assertIn("audio", [e[0] for e in envois], "la suite du parcours est dite à voix haute")
        envois = self.envoyer(texte("par écrit stp"))
        self.assertEqual(envois, [("texte", NUMERO, gabarits.ecrit_active())])
        self.assertFalse(self.session().voix_demandee)

    def test_demande_longue_avec_question_repondue_par_la_voix(self):
        self.consentir()
        with mock.patch.object(dialogue.groq, "configure", return_value=True), \
                mock.patch.object(dialogue.groq, "repondre", return_value=("question", "Semez après une bonne pluie.")):
            envois = self.envoyer(texte("je ne sais pas lire, dites moi en vocal quand je dois semer le maïs cette année"))
        self.assertEqual([e[0] for e in envois], ["audio"])
        self.assertTrue(self.session().voix_demandee)

    def test_intention_voix_comprise_par_groq(self):
        self.consentir()
        with mock.patch.object(dialogue.groq, "configure", return_value=True), \
                mock.patch.object(dialogue.groq, "repondre", return_value=("voix", "")):
            envois = self.envoyer(texte("redis moi ça avec ta bouche"))
        self.assertEqual([e[0] for e in envois], ["audio"])

    def test_voix_en_panne(self):
        self.consentir()
        self.configuree.stop()
        with mock.patch.object(dialogue.voix, "configuree", return_value=False):
            envois = self.envoyer(texte("une note vocale stp"))
        self.configuree.start()
        self.assertEqual(envois, [("texte", NUMERO, gabarits.voix_indisponible())])

    def test_parle_moi_de_reste_une_question(self):
        self.assertIsNone(gabarits.DEMANDE_VOIX.search(dialogue.normaliser("parle moi de la pluie à Korhogo")))


class TestDiscussion(Base):
    def test_question_ecrite_reponse_ecrite(self):
        self.consentir()
        with mock.patch.object(dialogue.groq, "configure", return_value=True), \
                mock.patch.object(dialogue.groq, "repondre",
                                  return_value=("question", "Le niébé enrichit le sol en azote.")) as repondre:
            envois = self.envoyer(texte("À quoi sert le niébé ?"))
        self.assertEqual(envois, [("texte", NUMERO, "Le niébé enrichit le sol en azote.")])
        self.assertEqual(repondre.call_args.args[1], "À quoi sert le niébé ?")

    def test_demande_de_rotation_ecrite(self):
        self.consentir()
        with mock.patch.object(dialogue.groq, "configure", return_value=True), \
                mock.patch.object(dialogue.groq, "repondre", return_value=("rotation", "")):
            envois = self.envoyer(texte("Je veux un conseil de rotation pour mon champ"))
        self.assertEqual(envois[-1][2], gabarits.demande_lieu())

    def test_groq_indisponible(self):
        """Sans Groq, une question libre reçoit un message honnête, une demande de rotation est comprise."""
        self.consentir()
        envois = self.envoyer(texte("Quand semer le maïs ?"))
        self.assertEqual(envois, [("texte", NUMERO, gabarits.discussion_indisponible())])
        envois = self.envoyer(texte("Je veux un conseil de rotation"))
        self.assertEqual(envois[-1][2], gabarits.demande_lieu())

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

    def test_saisie_signalee_des_la_reception(self):
        saisies = []
        self.canal.indiquer_saisie = saisies.append
        with mock.patch("threading.Thread") as fil:
            fil.side_effect = lambda target, daemon: mock.Mock(start=target)
            self.envoyer(texte("Bonjour"))
        self.assertEqual(saisies, ["w"])

    def test_message_sans_numero_ignore(self):
        self.envoyer({"id": "w", "type": "text", "text": {"body": "Bonjour"}})
        self.assertEqual(self.canal.envois, [])


if __name__ == "__main__":
    unittest.main()

"""Machine à états du dialogue avec l'agriculteur.

Parcours
    ACCUEIL             présentation et demande de consentement
    CONSENTEMENT        l'agriculteur accepte ou refuse, un refus efface tout
    MENU                discussion agricole libre, à l'écrit ou à la voix
    LIEU                position WhatsApp ou liste des zones couvertes
    ROTATION            liste des rotations actuelles possibles
    PRIORITE            trois boutons, eau, débouché, sol
    RESULTAT            résumé, boutons Pourquoi, Écouter, Détail, questions sur le conseil
    CONSENTEMENT_PHOTO  ancienne étape, une session qui y était passe à la photo
    PHOTO               la photo est analysée puis oubliée

Discussion, décision du responsable du 15 novembre 2026. Après le consentement,
l'agriculteur échange librement avec le bot sur l'agriculture. Groq rédige la réponse avec
les règles de bot.langage.conversation, qui ne nomme aucun produit et ne parle jamais au nom
de l'ANADER. Une question reçoit une réponse, sans lancer de calcul. Le parcours de
rotation, à choix multiples, ne démarre que si l'agriculteur le demande, par un bouton ou
par ses mots.

Une seule forme de réponse. Si l'agriculteur parle, le bot répond seulement en note
vocale, lue par Aethex, les boutons restant affichés sous un simple signe pour qui veut
toucher son choix. S'il écrit, le bot répond seulement par écrit. Seul le lien de la page
de détail part toujours par écrit, un lien ne se disant pas.

Une note vocale est transcrite par Groq, puis par Whisper sur la machine du bot, puis par
Aethex. Elle n'est transcrite qu'après le consentement ou en réponse à sa question, qui
annonce cette écoute. Gemini ne sert qu'à l'analyse des photos. Sans Groq, les choix et la
demande d'une rotation se comprennent encore par leurs mots-clés, et une question libre
reçoit un message qui dit que la discussion est momentanément indisponible.

Diagnostic par photo, à la manière du projet agri-bot. Une photo est acceptée à toute
étape après le consentement, sa légende servant de culture déclarée. Reçue avant le
consentement à son envoi chez Google, elle attend par son seul identifiant WhatsApp. Toute
phrase du diagnostic qui nommerait un produit est retirée.

STOP efface la session et la mémoire de la conversation, Bonjour ou Menu ramène à la
discussion. Une position hors des zones couvertes reçoit un message honnête. Les textes
fixes viennent de bot.langage.gabarits.

Zone couverte. Une position est rattachée à une ville si elle tombe à 0,15 degré au plus
de son centre en latitude et en longitude, l'emprise approximative des neuf cases de pluie
IMERG qui fondent le conseil, décrites dans docs/donnees.md.

Aucune photo ni aucun audio n'est écrit sur disque, et aucune question libre n'est gardée
sur disque.
"""

import functools
import logging
import re
import time
from enum import Enum

from moteur import recommander
from moteur.criteres import POIDS_PAR_PRIORITE
from moteur.contrat import AVERTISSEMENT_DIAGNOSTIC
from moteur.diagnostic import FORMAT_REFUSE, TYPES_IMAGE, diagnostiquer, echec, type_de_base
from moteur.lieux import LIEUX

from . import whatsapp
from .config import parametres
from .langage import comprehension, conversation, gabarits, groq, reformulation, transcription_locale, voix
from .langage.comprehension import normaliser
from .securite import empreinte_numero
from .sessions import Session, Sessions

journal = logging.getLogger("bot")
RAYON_DEGRES = 0.15
COMMANDES_DEBUT = {"bonjour", "bonsoir", "salut", "menu", "recommencer", "start", "hello"}
COMMANDE_EFFACER = "stop"


class Etat(str, Enum):
    ACCUEIL = "accueil"
    CONSENTEMENT = "consentement"
    MENU = "menu"
    LIEU = "lieu"
    ROTATION = "rotation"
    PRIORITE = "priorite"
    RESULTAT = "resultat"
    CONSENTEMENT_PHOTO = "consentement_photo"
    PHOTO = "photo"


@functools.cache
def sessions(chemin: str) -> Sessions:
    return Sessions(chemin)


def choisir(entree: dict, options: dict[str, str], souple: bool = True) -> str | None:
    """Identifiant choisi par un bouton, une ligne de liste, ou une phrase dite ou écrite.

    souple à vrai, une phrase libre est comprise par ses mots-clés puis par Groq. À faux,
    seuls le titre, l'identifiant ou le numéro exacts comptent, pour laisser les questions
    libres du résultat aller à la reformulation.
    """
    if entree.get("choix") in options:
        return entree["choix"]
    texte = entree.get("texte")
    if not texte:
        return None
    if souple:
        return comprehension.comprendre(texte, options)
    texte = normaliser(texte)
    for rang, (identifiant, titre) in enumerate(options.items(), start=1):
        if texte in (normaliser(identifiant), normaliser(titre), str(rang)):
            return identifiant
    return None


def phrases_fixes() -> list[str]:
    """Textes dits à l'identique à chaque fois, préparés en notes vocales au démarrage du bot."""
    avec_choix = [(gabarits.consentement(), gabarits.BOUTONS_CONSENTEMENT), (gabarits.menu(), gabarits.BOUTONS_MENU),
                  (gabarits.demande_lieu(), gabarits.LIGNES_LIEUX),
                  (gabarits.demande_rotation(), gabarits.LIGNES_ROTATIONS),
                  (gabarits.demande_priorite(), gabarits.BOUTONS_PRIORITE),
                  (gabarits.suite(), gabarits.BOUTONS_RESULTAT)]
    seuls = [gabarits.accueil(), gabarits.calcul_en_cours(), gabarits.demande_photo(), gabarits.discussion_indisponible(),
             gabarits.incompris(), gabarits.efface(), gabarits.zone_non_couverte(),
             gabarits.erreur_technique()]
    return [pour_la_voix(f"{texte}\n{gabarits.choix_a_dire(choix)}") for texte, choix in avec_choix] + \
        [pour_la_voix(texte) for texte in seuls]


@functools.cache
def _phrases_fixes() -> frozenset:
    return frozenset(phrases_fixes())


class _PhrasesFixes:
    def __contains__(self, texte: str) -> bool:
        return texte in _phrases_fixes()


PHRASES_FIXES = _PhrasesFixes()


def pour_la_voix(texte: str) -> str:
    """Texte à lire à voix haute, sans la mise en forme ni les signes de WhatsApp."""
    sans_lien = re.sub(r"https?://\S+", "", texte)
    return re.sub(r"[*_~👇📸⚠️]", "", sans_lien).replace("\ufe0f", "").strip()


def sans_produit(texte: str) -> str:
    """Retire du diagnostic toute phrase qui nomme un produit, en gardant l'avertissement final."""
    if not texte.rstrip().endswith(AVERTISSEMENT_DIAGNOSTIC):
        return texte
    corps = texte.rstrip()[:-len(AVERTISSEMENT_DIAGNOSTIC)]
    return f"{conversation.filtrer(corps)}\n\n{AVERTISSEMENT_DIAGNOSTIC}"


def transcrire_note(audio: bytes, type_audio: str) -> str | None:
    """Texte d'une note vocale, par Groq, puis par Whisper sur la machine, puis par Aethex. None si tout échoue."""
    if groq.configure():
        try:
            return groq.transcrire(audio, type_audio)
        except Exception as erreur:
            journal.warning("transcription Groq indisponible, %s", type(erreur).__name__)
    try:
        return transcription_locale.transcrire(audio)
    except Exception as erreur:
        journal.warning("transcription locale indisponible, %s", type(erreur).__name__)
    if voix.configuree():
        try:
            return voix.transcrire(audio, type_audio)
        except Exception as erreur:
            journal.warning("transcription Aethex indisponible, %s", type(erreur).__name__)
    return None


def lieu_proche(latitude: float, longitude: float) -> str | None:
    for identifiant, lieu in LIEUX.items():
        if abs(latitude - lieu["lat"]) <= RAYON_DEGRES and abs(longitude - lieu["lon"]) <= RAYON_DEGRES:
            return identifiant
    return None


def lire(message: dict) -> dict:
    """Ce que dit un message entrant, sous une forme commune à tous ses types."""
    genre = message.get("type")
    if genre == "text":
        return {"texte": message.get("text", {}).get("body", "")}
    if genre == "interactive":
        interactif = message.get("interactive", {})
        reponse = interactif.get(interactif.get("type", ""), {})
        return {"choix": reponse.get("id")}
    if genre == "location":
        position = message.get("location", {})
        return {"position": (position.get("latitude"), position.get("longitude"))}
    if genre == "image":
        image = message["image"]
        return {"image": (image["id"], image.get("mime_type", "")), "legende": (image.get("caption") or "").strip()}
    if genre == "audio":
        return {"audio": (message["audio"]["id"], message["audio"].get("mime_type", ""))}
    return {}


class Conversation:
    """Une étape du dialogue pour un expéditeur. canal envoie et télécharge, par défaut bot.whatsapp."""

    def __init__(self, numero: str, session: Session, canal, magasin: Sessions):
        self.numero, self.session, self.canal, self.magasin = numero, session, canal, magasin

    def etape(self, etat: Etat, **changements) -> None:
        self.session = self.magasin.ecrire(self.session.avec(etat=etat.value, **changements))

    @property
    def vocal(self) -> bool:
        return self.session.mode_vocal and voix.configuree()

    def dire(self, texte: str) -> bool:
        """Envoie le texte en note vocale, et dit s'il a pu partir. Une phrase fixe ne coûte aucun crédit."""
        texte = pour_la_voix(texte)
        try:
            note = voix.synthetiser_phrase_fixe(texte) if texte in PHRASES_FIXES else voix.synthetiser(texte)
            self.canal.envoyer_audio(self.numero, note)
            return True
        except Exception as erreur:
            journal.warning("note vocale non envoyée, %s", type(erreur).__name__)
            return False

    def texte(self, texte: str) -> None:
        """Un message, en note vocale si l'agriculteur parle, par écrit sinon, jamais les deux."""
        if not (self.vocal and self.dire(texte)):
            self.canal.envoyer_texte(self.numero, texte)

    def lien(self, texte: str) -> None:
        self.canal.envoyer_texte(self.numero, texte)

    def boutons(self, texte: str, boutons: dict[str, str]) -> None:
        if self.vocal and self.dire(f"{texte}\n{gabarits.choix_a_dire(boutons)}"):
            texte = gabarits.INVITE_CHOIX
        self.canal.envoyer_boutons(self.numero, texte, boutons)

    def liste(self, texte: str, lignes: dict[str, str]) -> None:
        if self.vocal and self.dire(f"{texte}\n{gabarits.choix_a_dire(lignes)}"):
            texte = gabarits.INVITE_CHOIX
        self.canal.envoyer_liste(self.numero, texte, lignes, gabarits.LIBELLE_LISTE)

    # Débuts et menu

    def accueillir(self) -> None:
        """Accueil, puis consentement. En vocal, l'accueil est dit et son lien part toujours par écrit."""
        if self.vocal and self.dire(gabarits.accueil()):
            self.lien(gabarits.PLATEFORME)
        else:
            self.canal.envoyer_texte(self.numero, gabarits.accueil())
        self.boutons(gabarits.consentement(), gabarits.BOUTONS_CONSENTEMENT)
        self.etape(Etat.CONSENTEMENT)

    def montrer_menu(self) -> None:
        self.boutons(gabarits.menu(), gabarits.BOUTONS_MENU)
        self.etape(Etat.MENU)

    def demander_lieu(self) -> None:
        self.liste(gabarits.demande_lieu(), gabarits.LIGNES_LIEUX)
        self.etape(Etat.LIEU)

    def demander_photo(self) -> None:
        self.texte(gabarits.demande_photo())
        self.etape(Etat.PHOTO)

    # Conseil de rotation

    def recommandation(self):
        s = self.session
        return recommander(s.lieu, s.rotation, POIDS_PAR_PRIORITE[s.priorite])

    def donner_resultat(self) -> None:
        self.texte(gabarits.calcul_en_cours())
        reco = self.recommandation()
        self.texte(gabarits.resume(reco))
        self.boutons(gabarits.suite(), gabarits.BOUTONS_RESULTAT)
        self.etape(Etat.RESULTAT)

    def suite_du_resultat(self, entree: dict) -> None:
        choix = choisir(entree, gabarits.BOUTONS_RESULTAT, souple=False)
        reco = self.recommandation()
        if choix == "pourquoi":
            raisons = gabarits.pourquoi(reco)
            self.texte(" ".join(raisons.split("\n")[:2]) if self.vocal else raisons)
        elif choix == "detail":
            self.lien(gabarits.detail(reco))
        elif choix == "ecouter":
            if not (voix.configuree() and self.dire(gabarits.resume(reco))):
                self.canal.envoyer_texte(self.numero, gabarits.voix_indisponible())
        elif entree.get("texte"):
            self.texte(reformulation.repondre(entree["texte"], reco, secours=gabarits.resume(reco)))
        else:
            self.texte(gabarits.incompris())
        self.boutons(gabarits.suite(), gabarits.BOUTONS_RESULTAT)

    # Diagnostic par photo

    def recevoir_photo(self, image: tuple[str, str], legende: str | None) -> None:
        """Analyse aussitôt, le consentement du premier message couvrant les photos.

        Décision du responsable du 15 novembre 2026, un second accord propre aux photos
        demandant un temps que les agriculteurs n'ont pas.
        """
        self.analyser_photo(image, legende)

    def analyser_photo(self, image: tuple[str, str], legende: str | None) -> None:
        media_id, type_image = image
        if type_de_base(type_image) in TYPES_IMAGE:
            contenu = self.canal.telecharger_media(media_id)
            resultat = diagnostiquer(contenu, type_image, legende or None)
            del contenu
        else:
            resultat = echec(FORMAT_REFUSE, legende or None)
        self.texte(sans_produit(gabarits.diagnostic(resultat)))
        self.etape(Etat.MENU, photo_en_attente=None)

    # Discussion

    def discuter(self, texte: str) -> None:
        """Répond à une question écrite ou dite, ou lance le parcours de rotation s'il est demandé.

        Groq rédige la réponse. Sans Groq, la demande d'une rotation ou d'une photo se
        comprend par mots-clés stricts, et une question reçoit un message d'indisponibilité.
        """
        if normaliser(texte) in (COMMANDE_EFFACER, *COMMANDES_DEBUT):
            self.avancer({"texte": texte})
            return
        intention, reponse = groq.repondre(self.session.empreinte, texte) if groq.configure() else ("indisponible", "")
        if intention == "rotation":
            self.demander_lieu()
            return
        if intention == "question":
            self.texte(reponse)
            self.etape(Etat.MENU)
            return
        demande = comprehension.par_les_mots(texte, gabarits.BOUTONS_MENU, gabarits.MOTS_DEMANDE)
        if demande == "rotation":
            self.demander_lieu()
        elif demande == "photo":
            self.demander_photo()
        else:
            self.texte(gabarits.discussion_indisponible())
            self.etape(Etat.MENU)

    def avancer(self, entree: dict) -> None:
        s, etat = self.session, Etat(self.session.etat)
        texte = normaliser(entree.get("texte") or "")
        if texte == COMMANDE_EFFACER:
            self.magasin.effacer(s.empreinte)
            conversation.oublier(s.empreinte)
            self.texte(gabarits.efface())
            return
        if "image" in entree and not s.consentement:
            # Une photo envoyée avant l'accord attend celui-ci, puis est analysée sans être redemandée.
            self.session = s = s.avec(photo_en_attente="|".join(entree["image"]))
            self.accueillir()
            return
        if not s.consentement and etat != Etat.CONSENTEMENT:
            self.accueillir()
            return
        if texte in COMMANDES_DEBUT:
            self.montrer_menu() if s.consentement else self.accueillir()
            return
        if "image" in entree and etat != Etat.CONSENTEMENT:
            self.recevoir_photo(entree["image"], entree.get("legende"))
            return

        if etat == Etat.CONSENTEMENT:
            choix = choisir(entree, gabarits.BOUTONS_CONSENTEMENT)
            if choix == "accepte":
                self.session = s.avec(consentement=True)
                if s.photo_en_attente:
                    self.analyser_photo(tuple(s.photo_en_attente.split("|", 1)), None)
                else:
                    self.montrer_menu()
            elif choix == "refuse":
                self.magasin.effacer(s.empreinte)
                self.texte(gabarits.refus())
            else:
                self.accueillir()

        elif etat == Etat.MENU:
            choix = choisir(entree, gabarits.BOUTONS_MENU, souple=False)
            if choix == "rotation":
                self.demander_lieu()
            elif choix == "photo":
                self.demander_photo()
            elif entree.get("texte"):
                self.discuter(entree["texte"])
            else:
                self.montrer_menu()

        elif etat == Etat.LIEU:
            lieu = choisir(entree, gabarits.LIGNES_LIEUX)
            if lieu is None and entree.get("position"):
                lieu = lieu_proche(*entree["position"])
                if lieu is None:
                    self.texte(gabarits.zone_non_couverte())
            if lieu:
                self.liste(gabarits.demande_rotation(), gabarits.LIGNES_ROTATIONS)
                self.etape(Etat.ROTATION, lieu=lieu)
            else:
                self.demander_lieu()

        elif etat == Etat.ROTATION:
            rotation = choisir(entree, gabarits.LIGNES_ROTATIONS)
            if rotation:
                self.boutons(gabarits.demande_priorite(), gabarits.BOUTONS_PRIORITE)
                self.etape(Etat.PRIORITE, rotation=rotation)
            else:
                self.liste(gabarits.demande_rotation(), gabarits.LIGNES_ROTATIONS)

        elif etat == Etat.PRIORITE:
            priorite = choisir(entree, gabarits.BOUTONS_PRIORITE)
            if priorite:
                self.session = s.avec(priorite=priorite)
                self.donner_resultat()
            else:
                self.boutons(gabarits.demande_priorite(), gabarits.BOUTONS_PRIORITE)

        elif etat == Etat.RESULTAT:
            self.suite_du_resultat(entree)

        elif etat == Etat.CONSENTEMENT_PHOTO:
            if s.photo_en_attente:
                self.analyser_photo(tuple(s.photo_en_attente.split("|", 1)), None)
            else:
                self.demander_photo()

        elif etat == Etat.PHOTO:
            self.texte(gabarits.demande_photo())

        else:
            self.accueillir()


def signaler_saisie(canal, message_id: str | None) -> None:
    """Affiche aussitôt « en train d'écrire », sans retarder la préparation de la réponse."""
    import threading

    indiquer = getattr(canal, "indiquer_saisie", None)
    if not (indiquer and message_id):
        return

    def envoyer():
        try:
            indiquer(message_id)
        except Exception as erreur:
            journal.warning("indicateur de saisie non envoyé, %s", type(erreur).__name__)
    threading.Thread(target=envoyer, daemon=True).start()


def traiter(message: dict, canal=whatsapp, magasin: Sessions | None = None) -> None:
    """Fait avancer la conversation de l'expéditeur d'un message entrant."""
    numero = message.get("from")
    if not numero:
        journal.warning("message sans numéro d'expéditeur ignoré")
        return
    reglages = parametres()
    magasin = magasin or sessions(reglages.base_de_donnees)
    session = magasin.lire(empreinte_numero(numero, reglages.sel_numeros))
    debut = time.monotonic()
    signaler_saisie(canal, message.get("id"))
    echange = Conversation(numero, session, canal, magasin)
    try:
        entree = lire(message)
        if "audio" in entree or "texte" in entree:
            echange.session = session.avec(mode_vocal="audio" in entree)
        if "audio" in entree:
            # La réponse à la question du consentement, qui annonce l'écoute, peut être écoutée.
            if not session.consentement and session.etat != Etat.CONSENTEMENT.value:
                echange.accueillir()
                return
            media_id, type_audio = entree["audio"]
            texte = transcrire_note(echange.canal.telecharger_media(media_id), type_audio)
            if texte is None:
                echange.texte(gabarits.vocal_indisponible())
                return
            entree = {"texte": texte}
            journal.info("note vocale transcrite, %s caractères", len(entree["texte"]))
            if not entree["texte"]:
                echange.texte(gabarits.incompris())
                echange.etape(Etat(echange.session.etat))
                return
        echange.avancer(entree)
        journal.info("réponse envoyée %.1f s après la réception", time.monotonic() - debut)
    except Exception as erreur:
        journal.exception("erreur pendant le dialogue, %s", type(erreur).__name__)
        try:
            echange.texte(gabarits.erreur_technique())
        except Exception:
            journal.exception("message d'erreur non envoyé")

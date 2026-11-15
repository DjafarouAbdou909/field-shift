"""Machine à états du dialogue avec l'agriculteur.

Parcours
    ACCUEIL             présentation et demande de consentement
    CONSENTEMENT        l'agriculteur accepte ou refuse, un refus efface tout
    MENU                conseil de rotation ou photo de feuille
    LIEU                position WhatsApp ou liste des zones couvertes
    ROTATION            liste des rotations actuelles possibles
    PRIORITE            trois boutons, eau, débouché, sol
    RESULTAT            résumé, boutons Pourquoi, Écouter, Détail, questions libres
    CULTURE_PHOTO       maïs ou coton
    CONSENTEMENT_PHOTO  accord pour envoyer la photo à Google, demandé une fois
    PHOTO               la photo est analysée puis oubliée

Un message vocal est transcrit par bot.langage.voix puis traité comme un texte, et
seulement après le consentement. Un texte peut remplacer un bouton, par son titre, son
identifiant ou son numéro dans l'ordre affiché. STOP efface la session, Bonjour ou Menu
ramène au début. Une position hors des zones couvertes reçoit un message honnête. Les
textes viennent de bot.langage.gabarits, jamais d'une chaîne écrite ici.

Zone couverte. Une position est rattachée à une ville si elle tombe à 0,15 degré au plus
de son centre en latitude et en longitude, l'emprise approximative des neuf cases de pluie
IMERG qui fondent le conseil, décrites dans docs/donnees.md.

Aucune photo ni aucun audio n'est écrit sur disque, et aucune question libre n'est gardée.
"""

import functools
import logging
import unicodedata
from enum import Enum

from moteur import recommander
from moteur.criteres import POIDS_PAR_PRIORITE
from moteur.diagnostic import TYPES_IMAGE, diagnostiquer
from moteur.lieux import LIEUX

from . import whatsapp
from .config import parametres
from .langage import gabarits, reformulation, voix
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
    CULTURE_PHOTO = "culture_photo"
    CONSENTEMENT_PHOTO = "consentement_photo"
    PHOTO = "photo"


@functools.cache
def sessions(chemin: str) -> Sessions:
    return Sessions(chemin)


def normaliser(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower().strip().rstrip(" .!?"))
    return "".join(c for c in decompose if not unicodedata.combining(c))


def choisir(entree: dict, options: dict[str, str]) -> str | None:
    """Identifiant choisi par un bouton, une ligne de liste, ou un texte qui reprend un titre ou un numéro."""
    if entree.get("choix") in options:
        return entree["choix"]
    texte = entree.get("texte")
    if not texte:
        return None
    texte = normaliser(texte)
    for rang, (identifiant, titre) in enumerate(options.items(), start=1):
        if texte in (normaliser(identifiant), normaliser(titre), str(rang)):
            return identifiant
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
        return {"image": (message["image"]["id"], message["image"].get("mime_type", ""))}
    if genre == "audio":
        return {"audio": (message["audio"]["id"], message["audio"].get("mime_type", ""))}
    return {}


class Conversation:
    """Une étape du dialogue pour un expéditeur. canal envoie et télécharge, par défaut bot.whatsapp."""

    def __init__(self, numero: str, session: Session, canal, magasin: Sessions):
        self.numero, self.session, self.canal, self.magasin = numero, session, canal, magasin

    def etape(self, etat: Etat, **changements) -> None:
        self.session = self.magasin.ecrire(self.session.avec(etat=etat.value, **changements))

    def texte(self, texte: str) -> None:
        self.canal.envoyer_texte(self.numero, texte)

    def boutons(self, texte: str, boutons: dict[str, str]) -> None:
        self.canal.envoyer_boutons(self.numero, texte, boutons)

    def liste(self, texte: str, lignes: dict[str, str]) -> None:
        self.canal.envoyer_liste(self.numero, texte, lignes, gabarits.LIBELLE_LISTE)

    # Débuts et menu

    def accueillir(self) -> None:
        self.boutons(gabarits.accueil(), gabarits.BOUTONS_CONSENTEMENT)
        self.etape(Etat.CONSENTEMENT)

    def montrer_menu(self) -> None:
        self.boutons(gabarits.menu(), gabarits.BOUTONS_MENU)
        self.etape(Etat.MENU)

    def demander_lieu(self) -> None:
        self.liste(gabarits.demande_lieu(), gabarits.LIGNES_LIEUX)
        self.etape(Etat.LIEU)

    def demander_culture_photo(self) -> None:
        self.boutons(gabarits.demande_culture_photo(), gabarits.BOUTONS_CULTURE_PHOTO)
        self.etape(Etat.CULTURE_PHOTO)

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
        choix = choisir(entree, gabarits.BOUTONS_RESULTAT)
        reco = self.recommandation()
        if choix == "pourquoi":
            self.texte(gabarits.pourquoi(reco))
        elif choix == "detail":
            self.texte(gabarits.detail(reco))
        elif choix == "ecouter":
            if voix.configuree():
                self.canal.envoyer_audio(self.numero, voix.synthetiser(gabarits.resume(reco)))
            else:
                self.texte(gabarits.voix_indisponible())
        elif entree.get("texte"):
            self.texte(reformulation.repondre(entree["texte"], reco, secours=gabarits.resume(reco)))
        else:
            self.texte(gabarits.incompris())
        self.boutons(gabarits.suite(), gabarits.BOUTONS_RESULTAT)

    # Diagnostic par photo

    def analyser_photo(self, image: tuple[str, str]) -> None:
        media_id, type_image = image
        type_image = type_image.split(";")[0].strip()
        if type_image not in TYPES_IMAGE:
            self.texte(gabarits.photo_illisible())
            return
        contenu = self.canal.telecharger_media(media_id)
        resultat = diagnostiquer(contenu, type_image, self.session.culture_photo)
        del contenu
        self.texte(gabarits.diagnostic(resultat))
        self.montrer_menu()

    # Aiguillage

    def avancer(self, entree: dict) -> None:
        s, etat = self.session, Etat(self.session.etat)
        texte = normaliser(entree.get("texte") or "")
        if texte == COMMANDE_EFFACER:
            self.magasin.effacer(s.empreinte)
            self.texte(gabarits.efface())
            return
        if not s.consentement and etat != Etat.CONSENTEMENT:
            self.accueillir()
            return
        if texte in COMMANDES_DEBUT:
            self.montrer_menu() if s.consentement else self.accueillir()
            return
        if "image" in entree and etat not in (Etat.PHOTO, Etat.CONSENTEMENT):
            self.demander_culture_photo()
            return

        if etat == Etat.CONSENTEMENT:
            choix = choisir(entree, gabarits.BOUTONS_CONSENTEMENT)
            if choix == "accepte":
                self.session = s.avec(consentement=True)
                self.montrer_menu()
            elif choix == "refuse":
                self.magasin.effacer(s.empreinte)
                self.texte(gabarits.refus())
            else:
                self.accueillir()

        elif etat == Etat.MENU:
            choix = choisir(entree, gabarits.BOUTONS_MENU)
            if choix == "rotation":
                self.demander_lieu()
            elif choix == "photo" or "image" in entree:
                self.demander_culture_photo()
            else:
                self.texte(gabarits.incompris())
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

        elif etat == Etat.CULTURE_PHOTO:
            culture = choisir(entree, gabarits.BOUTONS_CULTURE_PHOTO)
            if culture is None:
                self.demander_culture_photo()
            elif s.consentement_photo:
                self.texte(gabarits.demande_photo())
                self.etape(Etat.PHOTO, culture_photo=culture)
            else:
                self.boutons(gabarits.consentement_photo(), gabarits.BOUTONS_CONSENTEMENT_PHOTO)
                self.etape(Etat.CONSENTEMENT_PHOTO, culture_photo=culture)

        elif etat == Etat.CONSENTEMENT_PHOTO:
            choix = choisir(entree, gabarits.BOUTONS_CONSENTEMENT_PHOTO)
            if choix == "photo_accepte":
                self.texte(gabarits.demande_photo())
                self.etape(Etat.PHOTO, consentement_photo=True)
            elif choix == "photo_refuse":
                self.texte(gabarits.refus_photo())
                self.montrer_menu()
            else:
                self.boutons(gabarits.consentement_photo(), gabarits.BOUTONS_CONSENTEMENT_PHOTO)

        elif etat == Etat.PHOTO:
            if "image" in entree:
                self.analyser_photo(entree["image"])
            else:
                self.texte(gabarits.demande_photo())

        else:
            self.accueillir()


def traiter(message: dict, canal=whatsapp, magasin: Sessions | None = None) -> None:
    """Fait avancer la conversation de l'expéditeur d'un message entrant."""
    numero = message.get("from")
    if not numero:
        journal.warning("message sans numéro d'expéditeur ignoré")
        return
    reglages = parametres()
    magasin = magasin or sessions(reglages.base_de_donnees)
    session = magasin.lire(empreinte_numero(numero, reglages.sel_numeros))
    conversation = Conversation(numero, session, canal, magasin)
    try:
        entree = lire(message)
        if "audio" in entree:
            if not session.consentement:
                conversation.accueillir()
                return
            if not voix.configuree():
                conversation.texte(gabarits.vocal_indisponible())
                return
            media_id, type_audio = entree["audio"]
            entree = {"texte": voix.transcrire(canal.telecharger_media(media_id), type_audio)}
            if not entree["texte"]:
                conversation.texte(gabarits.incompris())
                return
        conversation.avancer(entree)
    except Exception as erreur:
        journal.exception("erreur pendant le dialogue, %s", type(erreur).__name__)
        try:
            conversation.texte(gabarits.erreur_technique())
        except Exception:
            journal.exception("message d'erreur non envoyé")

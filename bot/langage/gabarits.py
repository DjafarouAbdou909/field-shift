"""Messages déterministes du bot, construits à partir des objets du moteur.

Ce sont les messages envoyés par défaut, un par étape du parcours décrit dans
bot/dialogue.py. Ils restent courts, en français simple, et ne contiennent aucun chiffre
ni aucune culture qui ne vienne du moteur, ce que vérifie bot/langage/garde_fou.py. Les
textes sont ici et jamais dans le dialogue.

Boutons et listes. Chaque dictionnaire associe un identifiant, lu par le dialogue, à un
titre affiché. Trois boutons au plus par message et dix lignes au plus par liste, selon
bot/whatsapp.py. Les titres restent sous 20 caractères, limite à confirmer dans la
documentation de WhatsApp Cloud API par le membre A.

Diagnostic par photo. Depuis le 15 novembre 2026, le texte est rédigé librement par le
modèle, à la manière du projet agri-bot, avec une recommandation concrète, et il se
termine toujours par l'avertissement du diagnostic. La photo part chez Google pour
analyse, d'où le consentement demandé avant le premier envoi, et elle n'est jamais
conservée.
"""

import os

from moteur.contrat import AlerteVegetation, Diagnostic, Recommandation
from moteur.lieux import LIEUX
from moteur.rotations import STRATEGIES


def nombre(valeur: float) -> str:
    """Écrit un nombre à la française, sans séparateur de milliers."""
    return f"{valeur:g}".replace(".", ",")


def zones_couvertes() -> str:
    return " et ".join(f"{lieu['nom']}, {lieu['region']}" for lieu in LIEUX.values())


# Accueil et consentement à la conversation

PLATEFORME = os.environ.get("PLATEFORME_URL") or "https://conseil-rotation-ci.netlify.app"


def accueil() -> str:
    """Premier message, texte du responsable du 15 novembre 2026, le lien restant toujours écrit."""
    return ("Bonjour, j'espère que vous allez bien. Je suis AgriBot, votre assistant agricole, accessible directement "
            "sur WhatsApp quand vous avez une connexion, ou sur notre plateforme en l'absence de connexion.\n"
            f"{PLATEFORME}\n"
            "Je suis disponible pour vos conseils agricoles et le diagnostic de certaines cultures. Je peux aussi vous "
            "recommander des rotations.")


def consentement() -> str:
    return ("Pour vous aider, je garde seulement vos choix. Vos messages et vos photos passent par des services "
            "d'intelligence artificielle. Ce service est pour les adultes. Dites stop pour tout effacer. "
            "Êtes-vous d'accord ?")


BOUTONS_CONSENTEMENT = {"accepte": "Oui, d'accord", "refuse": "Non merci"}


def refus() -> str:
    return "D'accord, je ne garde rien. Dites bonjour si vous changez d'avis."


def efface() -> str:
    return "C'est fait, j'ai tout effacé. Dites bonjour pour recommencer."


# Menu

def menu() -> str:
    return ("Que voulez-vous ? Posez votre question, demandez quoi semer, ou envoyez la photo d'une plante malade.")


INVITE_CHOIX = "👇"


BOUTONS_MENU = {"rotation": "Quoi semer ?", "photo": "Plante malade"}
LIBELLE_LISTE = "Choisir"


# Lieu

def demande_lieu() -> str:
    return "Où est votre champ ? Choisissez votre ville, ou envoyez votre position."


LIGNES_LIEUX = {identifiant: lieu["nom"] for identifiant, lieu in LIEUX.items()}


def zone_non_couverte() -> str:
    villes = " et ".join(lieu["nom"] for lieu in LIEUX.values())
    return f"Désolé, je connais seulement {villes} pour le moment. Votre conseiller ANADER peut vous aider."


# Rotation actuelle et priorité

def demande_rotation() -> str:
    return "Qu'est-ce que vous cultivez dans ce champ, d'une année à l'autre ?"


LIGNES_ROTATIONS = {strategie.id: strategie.nom for strategie in STRATEGIES}


def demande_priorite() -> str:
    return ("Qu'est-ce qui compte le plus pour vous ? Avoir assez d'eau, bien vendre votre récolte, "
            "ou enrichir votre terre ?")


BOUTONS_PRIORITE = {"eau": "Assez d'eau", "revenu": "Bien vendre", "sol": "Enrichir la terre"}
BUTS = {"eau": "pour avoir assez d'eau", "revenu": "pour bien vendre votre récolte",
        "sol": "pour enrichir votre terre"}


# Résultat

RANGS = {1: "en premier", 2: "en deuxième", 3: "en troisième", 4: "en quatrième", 5: "en cinquième"}


def _en_phrase(nom: str) -> str:
    return nom[0].lower() + nom[1:]


def scenario(reco: Recommandation) -> str | None:
    """La phrase de l'avertissement du moteur qui dit ce qui changerait le conseil, en mots simples."""
    for phrase in reco.avertissement.split(". "):
        if phrase.startswith("Ce classement change si"):
            return "Ce conseil peut changer si" + phrase.removeprefix("Ce classement change si").rstrip(".") + "."
    return None


def resume(reco: Recommandation) -> str:
    """Le conseil en deux ou trois phrases, compréhensible à la première écoute.

    La réponse vient d'abord, sans chiffre ni source, le détail restant sur les boutons
    Pourquoi et Détail. Décision du responsable du 15 novembre 2026.
    """
    strategies = {s.id: s for s in reco.strategies}
    premiere = strategies[reco.classement[0]]
    actuelle = next(s for s in reco.strategies if s.actuelle)
    but = BUTS.get(reco.priorite or "", "")
    lignes = ["[TEST, données fictives]"] if reco.donnees_fictives else []
    debut = f"À {reco.lieu.nom}{', ' + but if but else ''}, "
    if premiere.id == actuelle.id:
        lignes.append(f"{debut}continuez avec {_en_phrase(premiere.nom)}, c'est le mieux.")
    else:
        dernier = reco.classement.index(actuelle.id) == len(reco.classement) - 1
        place = "en dernier" if dernier else RANGS.get(reco.classement.index(actuelle.id) + 1, "")
        lignes.append(f"{debut}le mieux est de faire {_en_phrase(premiere.nom)}.")
        lignes.append(f"Ce que vous faites aujourd'hui, {_en_phrase(actuelle.nom)}, vient {place}.")
    if not reco.classement_stable and (changement := scenario(reco)):
        lignes.append(changement)
    lignes.append("Parlez-en avec votre conseiller ANADER.")
    return " ".join(lignes)


BOUTONS_RESULTAT = {"pourquoi": "Pourquoi ?", "ecouter": "Écouter", "detail": "Détail"}


def pourquoi(reco: Recommandation) -> str:
    """Raisons, preuves et limites de la stratégie classée première."""
    premiere = next(s for s in reco.strategies if s.id == reco.classement[0])
    lignes = [f"Pourquoi {premiere.nom} arrive en tête."]
    lignes += [element.texte for element in premiere.pourquoi + premiere.preuves]
    if premiere.lacunes:
        lignes.append("Ce qui reste incertain.")
        lignes += [element.texte for element in premiere.lacunes]
    lignes.append("Avis à discuter avec votre conseiller ANADER.")
    return "\n".join(lignes)


def suite() -> str:
    return "Voulez-vous savoir pourquoi ? Vous pouvez aussi me poser une question."


def calcul_en_cours() -> str:
    return "Un instant, je regarde pour votre champ."


def voix_indisponible() -> str:
    return "La réponse vocale n'est pas disponible pour l'instant. Le texte ci-dessus reste valable."


def detail(reco: Recommandation) -> str:
    if reco.lien_detail:
        return f"Les chiffres, leurs sources et leurs limites sont sur cette page.\n{reco.lien_detail}"
    return "La page de détail n'est pas disponible pour l'instant."


# Alerte de végétation

def alerte(a: AlerteVegetation) -> str:
    """Texte de l'alerte et son avertissement, sans aucune cause déduite."""
    lignes = []
    if a.donnees_fictives:
        lignes.append("[TEST, données fictives]")
    lignes += [a.texte, a.avertissement]
    return "\n".join(lignes)


# Diagnostic par photo

def demande_photo() -> str:
    return "Envoyez une photo nette de la partie malade de la plante, prise de près, à la lumière du jour."


def diagnostic(d: Diagnostic) -> str:
    """Texte du diagnostic rédigé par le modèle, ou message d'échec, tel quel."""
    return f"[TEST, données fictives]\n{d.texte}" if d.donnees_fictives else d.texte


# Réponses dites à voix haute

MOTS_CLES = {
    "accepte": ["oui", "j'accepte", "accepte", "d'accord", "daccord", "ok", "okay", "vas y", "c'est bon"],
    "refuse": ["non", "refuse", "pas d'accord"],
    "photo_accepte": ["oui", "j'accepte", "accepte", "d'accord", "daccord", "ok", "okay", "vas y", "c'est bon"],
    "photo_refuse": ["non", "refuse", "pas d'accord"],
    "rotation": ["quoi semer", "rotation", "conseil", "rotations", "cultiver", "cultures", "semer", "planter", "quoi semer"],
    "photo": ["photo", "maladie", "malade", "feuille", "feuilles", "diagnostic", "image", "plante malade"],
    "korhogo": ["korhogo", "poro", "nord"],
    "bouake": ["bouake", "gbeke", "centre"],
    "coton_mais": ["coton+mais", "coton puis mais", "coton et mais", "coton mais", "coton avec mais", "coton et le mais"],
    "coton_niebe_mais": ["coton+niebe", "niebe", "coton niebe", "coton et niebe", "coton niebe mais"],
    "sorgho_niebe": ["sorgho+niebe", "sorgho", "sorgho niebe", "sorgho et niebe", "sorgho puis niebe"],
    "eau": ["eau", "pluie", "secheresse", "sec", "arrosage"],
    "revenu": ["bien vendre", "debouche", "revenu", "argent", "vendre", "vente", "filiere"],
    "sol": ["sol", "terre", "azote", "fertilite", "enrichir"],
    "pourquoi": ["pourquoi", "explique", "expliquer", "raison", "raisons"],
    "ecouter": ["ecouter", "ecoute", "voix", "audio", "lis", "lire", "parle"],
    "detail": ["detail", "details", "chiffres", "page", "lien", "plus"],
}


# Sans Gemini, seules ces demandes lancent un parcours depuis la discussion, une question
# qui parle de semer ou de cultures restant une question.
MOTS_DEMANDE = {"rotation": ["rotation", "rotations", "quoi semer"], "photo": ["photo", "maladie", "malade"]}


def choix_a_dire(options: dict[str, str]) -> str:
    """Phrase qui lit les choix à voix haute, pour qui ne lit pas les boutons."""
    titres = [t.rstrip(" ?") for t in options.values()]
    return f"Dites {', '.join(titres[:-1])} ou {titres[-1]}." if len(titres) > 1 else f"Dites {titres[0]}."


# Messages communs

def discussion_indisponible() -> str:
    return ("Je ne peux pas répondre aux questions libres pour le moment. Je peux comparer des rotations pour votre "
            "champ, dites ou écrivez rotation, ou regarder la photo d'une plante malade, envoyez-la-moi.")


def vocal_indisponible() -> str:
    return "Je ne peux pas écouter les messages vocaux pour l'instant. Répondez avec les boutons ou par écrit."


def incompris() -> str:
    return "Je n'ai pas compris. Répondez avec les boutons ou par un message vocal, ou dites Bonjour pour recommencer."


def erreur_technique() -> str:
    return "Un problème technique m'empêche de répondre. Réessayez dans quelques minutes."

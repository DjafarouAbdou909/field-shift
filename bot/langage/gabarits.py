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

from moteur.contrat import AlerteVegetation, Diagnostic, Recommandation
from moteur.lieux import LIEUX
from moteur.rotations import STRATEGIES


def nombre(valeur: float) -> str:
    """Écrit un nombre à la française, sans séparateur de milliers."""
    return f"{valeur:g}".replace(".", ",")


def zones_couvertes() -> str:
    return " et ".join(f"{lieu['nom']}, {lieu['region']}" for lieu in LIEUX.values())


# Accueil et consentement à la conversation

def accueil() -> str:
    return ("Bonjour, je suis Field Shift. Je compare des rotations de cultures pour votre zone, avec les données "
            "de pluie des satellites de la NASA depuis 2001. Mes conseils sont indicatifs et ne remplacent pas "
            "votre conseiller ANADER.\n"
            "Ce service est réservé aux personnes de 18 ans ou plus.\n"
            "Pour vous répondre, je garde votre zone, votre rotation et votre priorité, sans votre numéro en clair. "
            "Vos messages et vos questions sont compris par le service Gemini de Google, et mes réponses vocales "
            "sont lues par le service Aethex. Pour suivre la conversation, je garde vos derniers échanges en "
            "mémoire trente minutes, sans les enregistrer. Dites ou écrivez STOP à tout moment pour tout effacer. "
            "Acceptez-vous ?")


BOUTONS_CONSENTEMENT = {"accepte": "J'accepte", "refuse": "Non merci"}


def refus() -> str:
    return "D'accord, je ne garde rien. Écrivez Bonjour si vous changez d'avis."


def efface() -> str:
    return "C'est fait, je ne garde plus rien de notre conversation. Écrivez Bonjour pour recommencer."


# Menu

def menu() -> str:
    return ("Posez-moi vos questions sur vos cultures, par écrit ou par message vocal. Je peux aussi comparer des "
            "rotations pour votre champ, ou regarder la photo d'une plante malade.")


INVITE_CHOIX = "👇"


BOUTONS_MENU = {"rotation": "Conseil rotation", "photo": "Photo de plante"}
LIBELLE_LISTE = "Choisir"


# Lieu

def demande_lieu() -> str:
    return "Où se trouve votre champ ? Partagez votre position, ou choisissez votre zone dans la liste."


LIGNES_LIEUX = {identifiant: lieu["nom"] for identifiant, lieu in LIEUX.items()}


def zone_non_couverte() -> str:
    return (f"Désolé, votre champ est hors de la zone que je couvre pour l'instant, {zones_couvertes()}. "
            "Je ne peux pas vous conseiller sans les données de votre zone. Votre conseiller ANADER peut vous aider.")


# Rotation actuelle et priorité

def demande_rotation() -> str:
    return "Quelle rotation faites-vous aujourd'hui dans ce champ ?"


LIGNES_ROTATIONS = {strategie.id: strategie.nom for strategie in STRATEGIES}


def demande_priorite() -> str:
    return ("Qu'est-ce qui compte le plus pour vous ?\n"
            "Eau, une rotation qui manque moins d'eau.\n"
            "Débouché, garder une culture vendue par une filière organisée.\n"
            "Sol, enrichir le sol en azote avec une légumineuse.")


BOUTONS_PRIORITE = {"eau": "Eau", "revenu": "Débouché", "sol": "Sol"}


# Résultat

def resume(reco: Recommandation) -> str:
    """Résumé des stratégies dans l'ordre du classement, avec l'indicateur principal et l'avertissement."""
    strategies = {s.id: s for s in reco.strategies}
    lignes = []
    if reco.donnees_fictives:
        lignes.append("[TEST, données fictives]")
    lignes.append(f"Pour {reco.lieu.nom}, voici {len(reco.strategies)} rotations comparées.")
    indicateur = reco.indicateurs[0]
    lignes.append(
        f"Données NASA. {indicateur.texte}, {nombre(indicateur.valeur)} {indicateur.unite}, "
        f"entre {nombre(indicateur.bas)} et {nombre(indicateur.haut)} selon les années."
    )
    for rang, identifiant in enumerate(reco.classement, start=1):
        strategie = strategies[identifiant]
        actuelle = ", votre rotation actuelle" if strategie.actuelle else ""
        lignes.append(f"{rang}. {strategie.nom}{actuelle}. {strategie.pourquoi[0].texte}")
    if not reco.classement_stable:
        lignes.append("Attention, ce classement est incertain. La raison est donnée ci-dessous.")
    lignes.append(reco.avertissement)
    return "\n".join(lignes)


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
    return "Voulez-vous en savoir plus ? Vous pouvez aussi me poser votre question."


def calcul_en_cours() -> str:
    return "Je compare les rotations avec les données de la NASA, cela prend quelques secondes."


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

def consentement_photo() -> str:
    return ("Pour analyser votre plante, votre photo est envoyée à Google, qui l'analyse. Field Shift ne garde pas "
            "la photo. Le résultat est un diagnostic indicatif, qui ne remplace pas votre conseiller ANADER. "
            "Acceptez-vous d'envoyer votre photo ?")


BOUTONS_CONSENTEMENT_PHOTO = {"photo_accepte": "J'accepte", "photo_refuse": "Non merci"}


def demande_photo() -> str:
    return ("Envoyez une photo nette de la partie malade de la plante, feuille, tige ou fruit, prise de près et à "
            "la lumière du jour. Vous pouvez écrire le nom de la culture en légende de la photo.")


def refus_photo() -> str:
    return "D'accord, aucune photo n'est envoyée. Votre conseiller ANADER peut examiner la plante."


def diagnostic(d: Diagnostic) -> str:
    """Texte du diagnostic rédigé par le modèle, ou message d'échec, tel quel."""
    return f"[TEST, données fictives]\n{d.texte}" if d.donnees_fictives else d.texte


# Réponses dites à voix haute

MOTS_CLES = {
    "accepte": ["oui", "j'accepte", "accepte", "d'accord", "daccord", "ok", "okay", "vas y", "c'est bon"],
    "refuse": ["non", "refuse", "pas d'accord"],
    "photo_accepte": ["oui", "j'accepte", "accepte", "d'accord", "daccord", "ok", "okay", "vas y", "c'est bon"],
    "photo_refuse": ["non", "refuse", "pas d'accord"],
    "rotation": ["rotation", "conseil", "rotations", "cultiver", "cultures", "semer", "planter", "quoi semer"],
    "photo": ["photo", "maladie", "malade", "feuille", "feuilles", "diagnostic", "image", "plante malade"],
    "korhogo": ["korhogo", "poro", "nord"],
    "bouake": ["bouake", "gbeke", "centre"],
    "coton_mais": ["coton+mais", "coton puis mais", "coton et mais", "coton mais", "coton avec mais", "coton et le mais"],
    "coton_niebe_mais": ["coton+niebe", "niebe", "coton niebe", "coton et niebe", "coton niebe mais"],
    "sorgho_niebe": ["sorgho+niebe", "sorgho", "sorgho niebe", "sorgho et niebe", "sorgho puis niebe"],
    "eau": ["eau", "pluie", "secheresse", "sec", "arrosage"],
    "revenu": ["debouche", "revenu", "argent", "vendre", "vente", "filiere"],
    "sol": ["sol", "terre", "azote", "fertilite", "enrichir"],
    "pourquoi": ["pourquoi", "explique", "expliquer", "raison", "raisons"],
    "ecouter": ["ecouter", "ecoute", "voix", "audio", "lis", "lire", "parle"],
    "detail": ["detail", "details", "chiffres", "page", "lien", "plus"],
}


# Sans Gemini, seules ces demandes lancent un parcours depuis la discussion, une question
# qui parle de semer ou de cultures restant une question.
MOTS_DEMANDE = {"rotation": ["rotation", "rotations"], "photo": ["photo", "maladie", "malade"]}


def choix_a_dire(options: dict[str, str]) -> str:
    """Phrase qui lit les choix à voix haute, pour qui ne lit pas les boutons."""
    titres = [t.rstrip(" ?") for t in options.values()]
    enumeres = ", ".join(titres[:-1]) + f", ou {titres[-1]}" if len(titres) > 1 else titres[0]
    return f"Vous pouvez répondre en disant, {enumeres}."


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

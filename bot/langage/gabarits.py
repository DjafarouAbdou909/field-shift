"""Messages déterministes du bot, construits à partir des objets du moteur.

Ce sont les messages envoyés par défaut, un par étape du parcours décrit dans
bot/dialogue.py. Ils restent courts, en français simple, et ne contiennent aucun chiffre
ni aucune culture qui ne vienne du moteur, ce que vérifie bot/langage/garde_fou.py. Les
textes sont ici et jamais dans le dialogue.

Boutons et listes. Chaque dictionnaire associe un identifiant, lu par le dialogue, à un
titre affiché. Trois boutons au plus par message et dix lignes au plus par liste, selon
bot/whatsapp.py. Les titres restent sous 20 caractères, limite à confirmer dans la
documentation de WhatsApp Cloud API par le membre A.

Diagnostic par photo. Le bot ne recommande jamais de traitement ni de produit. Une maladie
possible est toujours dite « maladie possible, à faire confirmer par votre conseiller
ANADER ». La photo part chez Google pour analyse, d'où le consentement demandé avant le
premier envoi, et elle n'est jamais conservée.
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
            "Pour vous répondre, je garde votre zone, votre rotation et votre priorité, sans votre numéro en clair. "
            "Vos messages vocaux sont transcrits par le service Aethex, et Field Shift ne les garde pas. "
            "Acceptez-vous ?")


BOUTONS_CONSENTEMENT = {"accepte": "J'accepte", "refuse": "Non merci"}


def refus() -> str:
    return "D'accord, je ne garde rien. Écrivez Bonjour si vous changez d'avis."


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

def demande_culture_photo() -> str:
    return "De quelle culture est la feuille que vous voulez montrer ?"


BOUTONS_CULTURE_PHOTO = {"maïs": "Maïs", "coton": "Coton"}


def consentement_photo() -> str:
    return ("Pour reconnaître une maladie, votre photo est envoyée à Google, qui l'analyse. Field Shift ne garde pas "
            "la photo. Le résultat est un avis à faire confirmer par votre conseiller ANADER. Acceptez-vous d'envoyer "
            "votre photo ?")


BOUTONS_CONSENTEMENT_PHOTO = {"photo_accepte": "J'accepte", "photo_refuse": "Non merci"}


def demande_photo() -> str:
    return "Envoyez une photo nette d'une seule feuille, prise à la lumière du jour."


def refus_photo() -> str:
    return "D'accord, aucune photo n'est envoyée. Votre conseiller ANADER peut examiner la plante."


def diagnostic(d: Diagnostic) -> str:
    """Message du diagnostic. Une maladie possible est toujours à faire confirmer, jamais suivie d'un traitement."""
    lignes = []
    if d.donnees_fictives:
        lignes.append("[TEST, données fictives]")
    if d.statut == "maladie_possible":
        lignes.append(f"Maladie possible, {d.maladie}, à faire confirmer par votre conseiller ANADER.")
    else:
        lignes.append(d.avertissement)
    return "\n".join(lignes)


# Messages communs

def incompris() -> str:
    return "Je n'ai pas compris. Répondez avec les boutons, ou écrivez Bonjour pour recommencer."


def erreur_technique() -> str:
    return "Un problème technique m'empêche de répondre. Réessayez dans quelques minutes."

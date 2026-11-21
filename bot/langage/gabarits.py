"""Messages déterministes du bot, construits à partir des objets du moteur.

Ce sont les messages envoyés par défaut, un par étape du parcours décrit dans
bot/dialogue.py. Ils restent courts, en français simple, et ne contiennent aucun chiffre
ni aucune culture qui ne vienne du moteur, ce que vérifie bot/langage/garde_fou.py. Les
textes sont ici et jamais dans le dialogue.

Boutons et listes. Chaque dictionnaire associe un identifiant, lu par le dialogue, à un
titre affiché. Trois boutons au plus par message et dix lignes au plus par liste, selon
bot/whatsapp.py. Les titres restent sous 20 caractères, limite des boutons de réponse de
WhatsApp Cloud API.

Diagnostic par photo. Depuis le 15 novembre 2026, le texte est rédigé librement par le
modèle, à la manière du projet agri-bot, avec une recommandation concrète, et il se
termine toujours par l'avertissement du diagnostic. La photo part chez Google pour
analyse, ce qu'annonce le consentement du premier message, et le bot ne la conserve
jamais.
"""

import os
import re

from moteur.contrat import AlerteVegetation, Diagnostic, Recommandation
from moteur.lieux import LIEUX
from moteur.rotations import STRATEGIES


def nombre(valeur: float) -> str:
    """Écrit un nombre à la française, sans séparateur de milliers."""
    return f"{valeur:g}".replace(".", ",")


def zones_couvertes() -> str:
    return f"les {len(LIEUX)} chefs-lieux de région et de district de la Côte d'Ivoire"


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
    return ("Avant de commencer, une petite chose. Pour vous aider, je garde seulement vos choix. Vos messages et vos "
            "photos passent par des services d'intelligence artificielle. Ce service est pour les adultes, et vous "
            "pouvez dire stop à tout moment pour tout effacer. Êtes-vous d'accord ?")


BOUTONS_CONSENTEMENT = {"accepte": "Oui, d'accord", "refuse": "Non merci"}


def refus() -> str:
    return "D'accord, je respecte votre choix et je ne garde rien. Si vous changez d'avis, dites simplement bonjour."


def efface() -> str:
    return "C'est fait, j'ai tout effacé. Quand vous voudrez, dites bonjour et on recommence ensemble."


# Menu

SALUTATIONS = {"": "", "retour": "Bonjour, content de vous retrouver. ", "merci": "Merci pour votre confiance. "}


def menu(salutation: str = "") -> str:
    """Le menu, précédé d'un bonjour pour qui revient ou d'un merci après l'accord."""
    return (f"{SALUTATIONS[salutation]}Comment puis-je vous aider aujourd'hui ? Vous pouvez me poser une question, "
            "me demander quoi semer, m'envoyer la photo d'une plante malade, ou savoir comment va la végétation "
            "de votre zone.")


INVITE_CHOIX = "👇"


BOUTONS_MENU = {"rotation": "Quoi semer ?", "photo": "Plante malade", "vegetation": "Végétation"}
LIBELLE_LISTE = "Choisir"


# Lieu

def demande_lieu() -> str:
    return ("Avec plaisir. Où se trouve votre champ ? Dites-moi le nom de votre ville ou de votre village, "
            "ou envoyez-moi votre position.")


# Identifiants et noms des villes couvertes, pour comprendre une réponse libre, jamais affichés en liste,
# WhatsApp limitant une liste à dix lignes.
LIGNES_LIEUX = {identifiant: lieu["nom"] for identifiant, lieu in LIEUX.items()}


def zone_non_couverte() -> str:
    return ("Je suis désolé, je ne trouve pas ce lieu en Côte d'Ivoire. Dites-moi le nom de la ville la plus "
            "proche de votre champ, ou envoyez-moi votre position.")


def lieu_rattache(village: str, ville: str, distance: float, region: str | None = None) -> str:
    """Le village trouvé sur OpenStreetMap est rattaché au chef-lieu de sa région, ou à la ville couverte la plus proche."""
    ou = f"est dans la région {region}, à environ" if region else "est à environ"
    return (f"{village}, d'après OpenStreetMap, {ou} {round(distance)} km de {ville}. "
            f"Je prends les données de {ville}.")



def position_rattachee(ville: str, distance: float) -> str:
    return f"Votre champ est à environ {round(distance)} km de {ville}. Je prends les données de {ville}."


def mm(valeur: float) -> str:
    """Une quantité de pluie arrondie à la dizaine, sans fausse précision."""
    return f"{nombre(round(valeur, -1))} mm"


def de(nom: str) -> str:
    """« de » élidé devant une voyelle, d'Abidjan, de Man."""
    return f"d'{nom}" if nom[0].lower() in "aeiouyéèêâîôû" else f"de {nom}"


def climat(c) -> str:
    """Ce que dit la pluie NASA de 2001 à 2025 pour la zone d'une ville, sans date de début de saison.

    Chaque nombre vient de moteur.climat, arrondi à la dizaine. Le message renvoie au
    conseiller pour le choix des cultures et des dates de semis.
    """
    mois = lambda m: MOIS[m - 1]
    pluie = c.pluie_par_mois
    lignes = [
        f"Voici ce que disent {c.annees[1] - c.annees[0] + 1} ans de mesures satellite de la NASA, de {c.annees[0]} à "
        f"{c.annees[1]}, pour la zone {de(c.nom)}.",
        f"Il tombe en général environ {mm(c.pluie_annuelle_mediane)} de pluie par an, et moins de "
        f"{mm(c.pluie_annuelle_q10)} une année sur dix.",
        f"Les mois les plus pluvieux sont {mois(c.mois_pic_grande_saison)}, avec environ "
        f"{mm(pluie[c.mois_pic_grande_saison])}, et {mois(c.mois_pic_seconde)}, avec environ "
        f"{mm(pluie[c.mois_pic_seconde])}. Entre les deux, {mois(c.mois_creux)} n'en reçoit qu'environ "
        f"{mm(pluie[c.mois_creux])}.",
        f"De mars à juillet, la pluie change beaucoup d'une année à l'autre, d'environ {mm(c.grande_saison_q10)} "
        f"les années sèches à environ {mm(c.grande_saison_q90)} les années humides.",
        "Pour choisir vos cultures et vos dates de semis, parlez-en avec votre conseiller ANADER. La comparaison des "
        "rotations pour votre zone arrive bientôt.",
    ]
    return "\n".join(lignes)


def rotation_pas_encore(ville: str) -> str:
    return (f"Pour {ville} et le sud forestier, la comparaison des rotations arrive bientôt, avec les cultures "
            "et les deux saisons des pluies de votre zone. En attendant, je peux regarder la photo d'une plante "
            "malade ou répondre à vos questions.")


# Rotation actuelle et priorité

def demande_rotation() -> str:
    return "Très bien. Et dans ce champ, que cultivez-vous d'une année à l'autre ?"


LIGNES_ROTATIONS = {strategie.id: strategie.nom for strategie in STRATEGIES}


def demande_priorite() -> str:
    return ("Dernière question. Qu'est-ce qui compte le plus pour vous cette saison ? Avoir assez d'eau, "
            "bien vendre votre récolte, ou enrichir votre terre ?")


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
            texte = "Ce conseil peut changer si" + phrase.removeprefix("Ce classement change si").rstrip(".") + "."
            # Le résumé se comprend à la première écoute, sans chiffre.
            return texte.replace("de 20 %", "d'un cinquième").replace("de 14 jours", "de deux semaines")
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
        lignes.append(f"Bonne nouvelle. {debut}continuez avec {_en_phrase(premiere.nom)}, c'est le meilleur choix.")
    else:
        dernier = reco.classement.index(actuelle.id) == len(reco.classement) - 1
        place = "en dernier" if dernier else RANGS.get(reco.classement.index(actuelle.id) + 1, "")
        lignes.append(f"{debut}le mieux est de faire {_en_phrase(premiere.nom)}.")
        lignes.append(f"Ce que vous faites aujourd'hui, {_en_phrase(actuelle.nom)}, vient {place}.")
    if not reco.classement_stable and (changement := scenario(reco)):
        lignes.append(changement)
    lignes.append("Parlez-en aussi avec votre conseiller ANADER avant de décider.")
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
    return "Voulez-vous savoir pourquoi je vous conseille cela ? Vous pouvez aussi me poser toute autre question."


def calcul_en_cours() -> str:
    return "Merci. Je regarde les données de pluie et de climat de la NASA pour votre champ, un petit instant."


def voix_indisponible() -> str:
    return "Désolé, je ne peux pas vous parler à l'oral pour le moment. Le message écrit plus haut reste valable."


def detail(reco: Recommandation) -> str:
    if reco.lien_detail:
        return f"Les chiffres, leurs sources et leurs limites sont sur cette page.\n{reco.lien_detail}"
    return "La page de détail n'est pas disponible pour l'instant."


# Alerte de végétation

MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre")


def date_en_mots(date: str) -> str:
    """2026-11-02 devient 2 novembre 2026, les nombres restant ceux de la date du moteur."""
    annee, mois, jour = (int(x) for x in date.split("-"))
    return f"{jour} {MOIS[mois - 1]} {annee}"


def alerte(a: AlerteVegetation) -> str:
    """L'alerte en mots simples, avec la date des images, sans aucune cause déduite.

    Décision du responsable du 15 novembre 2026. La date des images vient d'abord, puis le
    constat du moteur, puis le rappel que les images ne disent pas la cause et le renvoi au
    conseiller ANADER. Le détail technique reste dans l'avertissement de l'objet.
    """
    lignes = ["[TEST, données fictives]"] if a.donnees_fictives else []
    conseil = "Regardez vos plants et parlez-en avec votre conseiller ANADER."
    lignes += [f"D'après les images satellite du {date_en_mots(a.date)} :", a.texte,
               conseil if a.statut == "indisponible" else f"Ces images ne disent pas pourquoi. {conseil}"]
    return "\n".join(lignes)


def alerte_indisponible() -> str:
    return "Désolé, je n'arrive pas à voir la végétation de votre zone pour le moment. Réessayez un peu plus tard."


def invitation_champ() -> str:
    return "Pour voir votre propre champ depuis le satellite, envoyez-moi sa position en étant dans le champ."


def demande_lieu_vegetation() -> str:
    return ("Pour voir votre champ depuis le satellite, envoyez-moi sa position en étant dans le champ, avec le "
            "trombone ou le plus, puis Position. Vous pouvez aussi me dire le nom de votre ville.")


def carte_en_cours() -> str:
    return ("Merci. Je regarde votre champ avec les images satellite de la NASA, de cette année et des années "
            "passées. La carte arrive dans une vingtaine de secondes.")


def carte_indisponible() -> str:
    return ("Désolé, je n'ai pas pu préparer la carte de votre champ pour le moment. Réessayez plus tard, ou "
            "envoyez-moi la photo d'une plante qui vous inquiète.")


def carte_champ(carte) -> str:
    """Explication de la carte du champ, en mots simples, sans aucune cause déduite.

    Le 10e centile de la règle fait qu'environ un carré sur dix peut être rouge sans problème
    réel, ce que le message dit pour ne pas inquiéter l'agriculteur à tort.
    """
    from moteur.champ import direction

    if carte.date is None:
        return ("Les nuages ont caché votre champ sur toutes les images de ces 30 derniers jours. Je ne peux pas "
                "encore le comparer. Réessayez dans quelques jours.")
    total = carte.statuts.size
    faibles, gris = carte.compte("faible"), carte.compte("indisponible")
    lignes = [f"Voici votre champ vu par les satellites de la NASA le {date_en_mots(carte.date)}. Chaque carré fait "
              "30 mètres de côté, et le rond blanc est l'endroit où vous étiez."]
    if faibles == 0:
        lignes.append("Toute la partie mesurée est verte, dans les valeurs habituelles pour cette période.")
    else:
        ou = direction(carte.statuts)
        ou = "tout près de l'endroit où vous étiez" if ou == "au centre" else ou
        lignes.append(f"{faibles} carrés sur {total} sont en rouge, plus faibles que d'habitude, surtout {ou}. "
                      "Quelques carrés rouges isolés peuvent apparaître même quand tout va bien. Allez voir surtout "
                      "s'ils sont nombreux et regroupés, et envoyez-moi la photo d'une plante.")
    if gris:
        lignes.append(f"{gris} carrés sont gris, cachés par les nuages, sans mesure.")
    lignes.append("Les images ne disent pas pourquoi. Parlez-en avec votre conseiller ANADER.")
    return "\n".join(lignes)


def alerte_pas_encore(ville: str) -> str:
    return (f"Je n'ai pas encore les images satellite de la zone de {ville}. Elles arrivent bientôt. "
            "Pour l'instant, je les ai pour Korhogo et Bouaké.")


# Diagnostic par photo

def demande_photo() -> str:
    return ("D'accord, montrez-moi la plante. Prenez une photo nette de la partie malade, de près et à la lumière "
            "du jour, puis envoyez-la-moi.")


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
    "vegetation": ["vegetation", "satellite", "verdure", "etat de ma zone", "ma zone"],
    **{identifiant: [lieu["nom"]] + ([] if lieu["region"].startswith("District") else [lieu["region"]])
       for identifiant, lieu in LIEUX.items()},
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
MOTS_DEMANDE = {"rotation": ["rotation", "rotations", "quoi semer"], "photo": ["photo", "maladie", "malade"],
                "vegetation": ["vegetation", "satellite"]}


def choix_a_dire(options: dict[str, str]) -> str:
    """Phrase qui lit les choix à voix haute, pour qui ne lit pas les boutons."""
    titres = [t.rstrip(" ?") for t in options.values()]
    return (f"Dites simplement {', '.join(titres[:-1])} ou {titres[-1]}." if len(titres) > 1
            else f"Dites simplement {titres[0]}.")


# Messages communs

def discussion_indisponible() -> str:
    return ("Désolé, je ne peux pas répondre aux questions libres en ce moment. Je peux quand même comparer des "
            "rotations pour votre champ, dites ou écrivez rotation, ou regarder la photo d'une plante malade, "
            "envoyez-la-moi.")


def vocal_indisponible() -> str:
    return "Désolé, je n'arrive pas à écouter les messages vocaux pour le moment. Utilisez les boutons ou écrivez-moi."


def incompris() -> str:
    return ("Pardon, je n'ai pas bien compris. Vous pouvez utiliser les boutons, m'envoyer un message vocal, "
            "ou dire bonjour pour recommencer.")


def erreur_technique() -> str:
    return "Désolé, j'ai un petit souci technique. Réessayez dans quelques minutes, je serai là."


# Voix ou écrit, à la demande de l'agriculteur

DEMANDE_VOIX = re.compile(r"\b(notes? vocales?|vocal|vocale|audio|a l'oral|a voix haute|en voix|par la voix|"
                          r"lis moi|lisez moi|relis|relisez|je ne sais pas lire|je sais pas lire|"
                          r"je ne lis pas|je ne peux pas lire|j'arrive pas a lire|je n'arrive pas a lire)\b")
DEMANDE_ECRIT = re.compile(r"\b(par ecrit|a l'ecrit|en ecrit|ecris moi|ecrivez moi|en texte|plus de vocal|"
                           r"pas de vocal|sans vocal|arrete les vocaux|arretez les vocaux)\b")


DIFFICULTE_LIRE = re.compile(r"\b(je ne sais pas lire|je sais pas lire|je ne lis pas|je ne peux pas lire|"
                             r"j'arrive pas a lire|je n'arrive pas a lire)\b")
DIFFICULTE_ECRIRE = re.compile(r"\b(je ne sais pas ecrire|je sais pas ecrire|je n'ecris pas|j'ecris pas|"
                               r"je ne peux pas ecrire|j'arrive pas a ecrire|je n'arrive pas a ecrire)\b")


def rassurer_lecture() -> str:
    return ("Pas de souci, ce n'est pas grave. Je vais vous parler à l'oral, "
            "et vous pouvez me répondre par message vocal, avec le micro de WhatsApp.")


def rassurer_ecriture() -> str:
    return ("Pas de souci, ce n'est pas grave, vous n'avez pas besoin d'écrire. Appuyez sur le micro de WhatsApp "
            "et parlez-moi, je vous répondrai aussi à l'oral. Comment puis-je vous aider ?")


def accueil_de_la_voix(phrase: str) -> tuple[str | None, bool]:
    """Phrase qui rassure l'agriculteur avant de passer à la voix, et s'il faut relire le dernier message."""
    if DIFFICULTE_ECRIRE.search(phrase):
        return rassurer_ecriture(), False
    if DIFFICULTE_LIRE.search(phrase):
        return rassurer_lecture(), True
    return None, True


def voix_activee() -> str:
    return "Avec plaisir, je vous parle maintenant à l'oral. Je vous écoute."


def ecrit_active() -> str:
    return "D'accord, je vous écris maintenant."

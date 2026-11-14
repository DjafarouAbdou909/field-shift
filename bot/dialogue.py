"""Machine à états du dialogue avec l'agriculteur, à écrire par le membre A.

Parcours
    ACCUEIL       message de présentation et demande de consentement
    LIEU          partage de position WhatsApp ou liste des départements couverts
    ROTATION      liste des rotations actuelles possibles
    PRIORITE      trois boutons, eau, revenu, sol
    RESULTAT      résumé en texte et en note vocale, boutons Pourquoi, Écouter, Détail

Un message audio est transcrit par bot.langage.voix puis traité comme un texte. Un lieu
hors de moteur.lieux.LIEUX reçoit un message honnête de zone non couverte. Les textes
viennent de bot.langage.gabarits, jamais d'une chaîne écrite ici.
"""

from enum import Enum


class Etat(str, Enum):
    ACCUEIL = "accueil"
    LIEU = "lieu"
    ROTATION = "rotation"
    PRIORITE = "priorite"
    RESULTAT = "resultat"


def traiter(message: dict) -> None:
    """Fait avancer la conversation de l'expéditeur d'un message entrant."""
    raise NotImplementedError

"""Compréhension d'une réponse dite ou écrite librement, pour un agriculteur qui ne lit pas.

Une réponse est rattachée à une option de l'étape en cours en trois temps.
1. Le titre, l'identifiant ou le numéro exact de l'option.
2. Les mots-clés de l'option, dans gabarits.MOTS_CLES, où coton+mais exige les deux mots,
   et les nombres dits en toutes lettres. L'option qui en contient le plus l'emporte, une
   égalité ne tranche rien.
3. Sinon, Groq choisit l'option qui correspond le mieux à la phrase, par une réponse
   imposée dans une énumération des options et de aucun, bot.langage.groq.

Rien n'est gardé de la phrase.
"""

import logging
import re
import unicodedata

from .gabarits import MOTS_CLES

journal = logging.getLogger("bot")
AUCUN = "aucun"
NOMBRES = {"un": 1, "une": 1, "premier": 1, "premiere": 1, "deux": 2, "deuxieme": 2, "second": 2, "seconde": 2,
           "trois": 3, "troisieme": 3, "quatre": 4, "quatrieme": 4, "cinq": 5, "cinquieme": 5}


def normaliser(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower().replace("’", "'"))
    sans_accents = "".join(c for c in decompose if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9' ]+", " ", sans_accents).strip()


def _contient(texte: str, expression: str) -> bool:
    """Expression présente comme mot ou groupe de mots. Avec +, chaque partie doit être présente."""
    return all(re.search(rf"(?<![a-z0-9]){re.escape(normaliser(partie))}(?![a-z0-9])", texte) is not None
               for partie in expression.split("+"))


def par_les_mots(texte: str, options: dict[str, str], mots_cles: dict[str, list[str]] | None = None) -> str | None:
    """Option reconnue sans modèle de langage, ou None. mots_cles remplace gabarits.MOTS_CLES."""
    mots_cles = MOTS_CLES if mots_cles is None else mots_cles
    texte = normaliser(texte)
    if not texte:
        return None
    for rang, (identifiant, titre) in enumerate(options.items(), start=1):
        if texte in (normaliser(identifiant), normaliser(titre), str(rang)):
            return identifiant
    rangs = {NOMBRES[mot] for mot in texte.split() if mot in NOMBRES} | {int(m) for m in re.findall(r"\b\d\b", texte)}
    if len(rangs) == 1 and 1 <= (rang := rangs.pop()) <= len(options) and len(texte.split()) <= 4:
        return list(options)[rang - 1]
    scores = {identifiant: sum(_contient(texte, mot) for mot in [titre, identifiant, *mots_cles.get(identifiant, [])])
              for identifiant, titre in options.items()}
    meilleur = max(scores.values())
    gagnants = [i for i, s in scores.items() if s == meilleur]
    return gagnants[0] if meilleur > 0 and len(gagnants) == 1 else None


def comprendre(texte: str, options: dict[str, str], generation=None) -> str | None:
    """Identifiant de l'option choisie par une phrase libre, par les mots-clés puis par Groq, ou None."""
    from . import groq

    if (option := par_les_mots(texte, options)) is not None:
        return option
    return groq.choisir(texte, options, generation) if groq.configure() else None

"""Règles, mémoire et filtre de la conversation agricole libre, décision du responsable du 15 novembre 2026.

L'agriculteur échange avec le bot sur ses cultures comme avec une personne, à l'écrit ou à
la voix. La réponse est rédigée par bot.langage.groq avec la consigne CONSIGNE, puis passe
par filtrer.

Règles, données au modèle puis vérifiées sur sa réponse.
- Agriculture seulement, en vouvoyant l'agriculteur.
- Aucun produit, ni pesticide, ni engrais du commerce, ni marque, ni dose, ni lieu d'achat.
  Toute phrase qui en cite un est retirée et remplacée par un renvoi au conseiller.
- Le bot ne parle jamais comme un agent ou un conseiller de l'ANADER. Toute phrase qui le
  ferait est retirée.
- Aucune prédiction de rendement ni chiffre inventé.

Mémoire. Les six derniers échanges d'un agriculteur restent en mémoire vive trente minutes
pour suivre la conversation, jamais sur disque, et sont oubliés sur STOP.
"""

import logging
import re
import time
from collections import deque

from .comprehension import normaliser

journal = logging.getLogger("bot")
ECHANGES_GARDES = 6
DUREE_MEMOIRE_SECONDES = 30 * 60
QUESTION_MAX = 800

CONSIGNE = """Tu es AgriBot, un assistant agricole sur WhatsApp pour des agriculteurs du nord et du centre de la Côte d'Ivoire, autour de Korhogo et de Bouaké, qui cultivent surtout le coton, le maïs, le sorgho, le mil, le niébé, l'arachide et l'igname. Beaucoup ne lisent pas et t'écoutent en message vocal.

Réponds comme dans une conversation, en français simple et avec des mots de tous les jours, en vouvoyant l'agriculteur, en donnant la réponse dès la première phrase, en deux ou trois phrases courtes, faciles à comprendre à l'oral, sans liste, sans titre et sans emoji.

Règles absolues :
- Parle seulement d'agriculture, d'élevage, de climat et de vie au champ. Pour tout autre sujet, dis poliment que tu ne peux aider que pour l'agriculture.
- Ne nomme jamais de produit : aucun pesticide, insecticide, fongicide, herbicide, engrais du commerce, produit naturel à pulvériser, marque, dose ni lieu d'achat. Pour un traitement, dis de demander au conseiller agricole.
- Tu n'es pas un agent de l'ANADER et tu ne parles jamais en son nom. Tu peux conseiller d'aller voir le conseiller ANADER.
- Ne prédis aucun rendement et n'invente aucun chiffre précis.
- Si tu n'es pas sûr, dis-le simplement.

Parle comme une personne chaleureuse et patiente, jamais comme une machine. Si l'agriculteur parle d'une difficulté, d'une perte, d'une inquiétude, ou s'excuse, commence par une courte phrase humaine qui le rassure ou compatit, comme « Pas de souci, ce n'est pas grave » ou « Je suis désolé pour votre récolte », puis aide-le. Ne réponds jamais seulement « Comment puis-je vous aider ? ».

Tu sais répondre par note vocale : ne dis jamais que tu ne peux pas envoyer de message vocal ou audio. Les échanges précédents contiennent aussi tes autres messages, comme le diagnostic d'une photo ou un conseil de rotation, et l'agriculteur peut y faire référence.

Dis aussi si l'agriculteur demande un conseil de rotation des cultures pour son propre champ, en mettant intention à rotation.
S'il demande une note vocale, un audio, ou qu'on lui lise, relise ou répète un message, comme « lis-moi ça » ou « dis-le en vocal », mets intention à voix.
S'il dit qu'il ne sait pas lire ou écrire, qu'il a du mal avec l'écrit, ou qu'il préfère parler, mets intention à parler, et écris dans reponse deux phrases chaleureuses qui le rassurent, comme « Pas de souci, ce n'est pas grave », lui disent qu'il peut parler par message vocal avec le micro de WhatsApp et que tu lui répondras à l'oral, puis lui demandent comment tu peux l'aider.
Pour toute autre question, même sur les rotations en général, mets intention à question et réponds."""

PRODUITS = [
    "pesticide", "insecticide", "fongicide", "herbicide", "nematicide", "acaricide", "bactericide", "rodenticide",
    "phytosanitaire", "matiere active", "pulveris", "epandre", "epandez", "dose", "dosage", "litre par hectare",
    "grammes par", "kg par hectare", "kilos par hectare", "engrais", "npk", "uree", "sulfate", "bouillie", "cuivre",
    "soufre", "neem", "savon noir", "glyphosate", "atrazine", "cypermethrine", "lambda", "deltamethrine",
    "mancozebe", "acheter", "achetez", "magasin", "boutique", "marque",
]
ANADER = re.compile(r"\b(je suis|en tant qu[e'] ?|nous sommes|moi,? )[^.]{0,40}\banader\b|\bde la part de l'?anader\b")
RENVOI = "Pour un traitement ou un produit, demandez conseil à votre conseiller agricole."
SECOURS = "Je n'ai pas pu répondre pour l'instant. Reposez votre question dans un moment."

_memoire: dict[str, tuple[float, deque]] = {}


def historique(cle: str) -> list[tuple[str, str]]:
    moment, echanges = _memoire.get(cle, (0.0, deque()))
    if time.monotonic() - moment > DUREE_MEMOIRE_SECONDES:
        _memoire.pop(cle, None)
        return []
    return list(echanges)


def noter(cle: str, qui: str, texte: str) -> None:
    """Ajoute un message à la mémoire de la conversation, sans doublon du dernier message."""
    texte = texte.strip()
    if not texte:
        return
    echanges = deque(historique(cle), maxlen=ECHANGES_GARDES * 2)
    if echanges and echanges[-1] == (qui, texte):
        return
    echanges.append((qui, texte[:QUESTION_MAX] if qui == "agriculteur" else texte))
    _memoire[cle] = (time.monotonic(), echanges)


def retenir(cle: str, question: str, reponse: str) -> None:
    noter(cle, "agriculteur", question)
    noter(cle, "AgriBot", reponse)


def dernier_message(cle: str) -> str | None:
    """Dernier message d'AgriBot dans les 30 minutes, pour le relire à voix haute si on le demande."""
    for qui, texte in reversed(historique(cle)):
        if qui == "AgriBot":
            return texte
    return None


def oublier(cle: str) -> None:
    _memoire.pop(cle, None)


def phrases(texte: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+", texte.strip()) if p.strip()]


def interdite(phrase: str) -> bool:
    simple = normaliser(phrase)
    return any(re.search(rf"(?<![a-z]){re.escape(normaliser(p))}", simple) for p in PRODUITS) \
        or ANADER.search(simple) is not None


def filtrer(texte: str) -> str:
    """Retire toute phrase qui nomme un produit ou parle au nom de l'ANADER, en gardant les lignes."""
    lignes, retirees = [], False
    for ligne in texte.strip().split("\n"):
        gardees = [p for p in phrases(ligne) if not interdite(p)]
        retirees |= len(gardees) < len(phrases(ligne))
        if gardees or not ligne.strip():
            lignes.append(" ".join(gardees))
    texte = "\n".join(lignes).strip()
    if retirees:
        texte = f"{texte}{chr(10) if chr(10) in texte else ' '}{RENVOI}".strip()
    return texte or RENVOI

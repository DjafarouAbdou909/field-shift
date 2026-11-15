"""Transcription, compréhension et réponses écrites avec l'API de Groq, décision du responsable du 15 novembre 2026.

Gemini ne garde que l'analyse des photos, Groq n'ayant aucun modèle qui regarde les images.
Groq transcrit les notes vocales, comprend les choix qui ne sont pas exacts, rédige les
réponses aux questions libres et aux questions sur le conseil de rotation.

Documentation officielle lue le 15 novembre 2026 sur https://console.groq.com/docs, et
liste des modèles rendue par l'API avec la clé du responsable.
- Clé GROQ_API_KEY dans l'en-tête Authorization Bearer, jamais dans le dépôt.
- Réponses, POST https://api.groq.com/openai/v1/chat/completions, modèle
  openai/gpt-oss-120b, réponse imposée par un schéma JSON strict, raisonnement low, pages
  structured-outputs, reasoning et model/openai/gpt-oss-120b.
- Transcription, POST https://api.groq.com/openai/v1/audio/transcriptions, modèle
  whisper-large-v3-turbo, fichier OGG accepté, 25 Mo au plus au niveau gratuit, langue fr et
  amorce de 224 jetons au plus, page speech-to-text.
- Données. Groq ne conserve pas par défaut les requêtes, mais peut journaliser entrées et
  sorties jusqu'à 30 jours en cas de panne ou de soupçon d'abus, sauf si la rétention zéro
  est activée dans les réglages du compte, page your-data. L'usage pour l'entraînement
  n'est pas documenté sur les pages lues.
- Limites lues pour la formule Developer, 30 requêtes par minute et 1 000 par jour pour
  gpt-oss-120b, 20 par minute et 2 000 par jour pour la transcription. Celles de la formule
  gratuite n'étaient pas lisibles, page rate-limits.
"""

import functools
import json
import logging
import os

import requests

from . import conversation
from .transcription_locale import AMORCE

journal = logging.getLogger("bot")
URL = "https://api.groq.com/openai/v1"
MODELE_TEXTE = "openai/gpt-oss-120b"
MODELE_AUDIO = "whisper-large-v3-turbo"
MODELES_VERIFIES_LE = "2026-11-15"
AUCUN = "aucun"


def configure() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))


def _entetes() -> dict[str, str]:
    cle = os.environ.get("GROQ_API_KEY")
    if not cle:
        raise RuntimeError("clé GROQ_API_KEY absente de l'environnement")
    return {"Authorization": f"Bearer {cle}"}


@functools.cache
def _session() -> requests.Session:
    """Connexion gardée ouverte d'une requête à l'autre, pour gagner la négociation TLS."""
    return requests.Session()


def _poster(chemin: str, session=None, **arguments) -> requests.Response:
    reponse = (session or _session()).post(f"{URL}{chemin}", headers=_entetes(), timeout=30, **arguments)
    if reponse.status_code >= 400:
        journal.warning("Groq a refusé la requête, code %s", reponse.status_code)
    reponse.raise_for_status()
    return reponse


def schema(nom: str, proprietes: dict) -> dict:
    return {"type": "json_schema", "json_schema": {"name": nom, "strict": True, "schema": {
        "type": "object", "additionalProperties": False, "properties": proprietes, "required": list(proprietes)}}}


def generer(systeme: str, message: str, format_reponse: dict, session=None) -> dict:
    """Réponse JSON du modèle de texte, conforme au schéma demandé."""
    corps = {"model": MODELE_TEXTE, "reasoning_effort": "low", "response_format": format_reponse,
             "messages": [{"role": "system", "content": systeme}, {"role": "user", "content": message}]}
    contenu = _poster("/chat/completions", session, json=corps).json()["choices"][0]["message"]["content"]
    return json.loads(contenu)


def transcrire(audio: bytes, type_audio: str, session=None) -> str:
    """Texte d'une note vocale, par Whisper sur les serveurs de Groq."""
    nom = "note.ogg" if "ogg" in type_audio else "note.wav"
    reponse = _poster("/audio/transcriptions", session,
                      files={"file": (nom, audio, type_audio.split(";")[0].strip())},
                      data={"model": MODELE_AUDIO, "language": "fr", "prompt": AMORCE, "response_format": "json"})
    return (reponse.json().get("text") or "").strip()


def repondre(cle: str, question: str, generation=None) -> tuple[str, str]:
    """Intention, rotation, question ou indisponible, et réponse filtrée à une question écrite ou transcrite."""
    contexte = "\n".join(f"{qui} : {quoi}" for qui, quoi in conversation.historique(cle)) or "aucun"
    try:
        sortie = (generation or generer)(
            conversation.CONSIGNE,
            f"Échanges précédents\n{contexte}\n\nNouveau message de l'agriculteur\n"
            f"{question[:conversation.QUESTION_MAX]}",
            schema("reponse_agricole", {"intention": {"type": "string", "enum": ["rotation", "question"]},
                                        "reponse": {"type": "string"}}))
    except Exception as erreur:
        journal.warning("Groq indisponible pour répondre, %s", type(erreur).__name__)
        return "indisponible", conversation.SECOURS
    if sortie.get("intention") == "rotation":
        return "rotation", ""
    reponse = conversation.filtrer(sortie.get("reponse") or "") if sortie.get("reponse") else conversation.SECOURS
    conversation.retenir(cle, question, reponse)
    return "question", reponse


def choisir(texte: str, options: dict[str, str], generation=None) -> str | None:
    """Option choisie par une phrase libre, souvent transcrite avec des erreurs, ou None."""
    liste = "; ".join(f"{i}, {t}" for i, t in options.items())
    try:
        sortie = (generation or generer)(
            "Tu aides un assistant agricole sur WhatsApp à comprendre la réponse d'un agriculteur ivoirien, "
            "souvent un message vocal transcrit avec des erreurs.",
            f"L'agriculteur a dit « {texte[:300]} ». Les options possibles, sous la forme identifiant, titre, sont "
            f"{liste}. Rends l'identifiant de l'option qu'il choisit, ou {AUCUN} si sa phrase ne correspond à aucune.",
            schema("choix", {"option": {"type": "string", "enum": [*options, AUCUN]}}))
    except Exception as erreur:
        journal.warning("Groq indisponible pour comprendre, %s", type(erreur).__name__)
        return None
    option = sortie.get("option")
    return option if option in options else None


def reformuler(systeme: str, message: str, generation=None) -> str | None:
    """Texte libre rédigé par le modèle, pour les questions sur le conseil de rotation, ou None."""
    try:
        sortie = (generation or generer)(systeme, message, schema("reponse", {"reponse": {"type": "string"}}))
    except Exception as erreur:
        journal.warning("Groq indisponible pour reformuler, %s", type(erreur).__name__)
        return None
    return sortie.get("reponse") or None

"""Réponses de secours avec Grok de xAI, quand Gemini ne répond pas, demande du responsable du 15 novembre 2026.

Quand le quota de Gemini est épuisé, la note vocale est transcrite par Whisper sur la
machine du bot, puis Grok rédige la réponse et Aethex la lit. Grok reçoit la même consigne
que Gemini, sa réponse passe par le même filtre des produits et de l'ANADER, et les
échanges rejoignent la même mémoire de trente minutes.

Documentation officielle lue le 15 novembre 2026 sur https://docs.x.ai.
- POST https://api.x.ai/v1/chat/completions, clé XAI_API_KEY dans l'en-tête Authorization
  Bearer, page developers/rest-api-reference/inference/chat-completions.
- Réponse imposée par response_format de type json_schema, page
  developers/model-capabilities/text/structured-outputs.
- Modèle grok-4.20-0309-non-reasoning, 1,25 dollar par million de jetons en entrée et
  2,50 en sortie, page developers/pricing. L'API n'est pas gratuite, la page de démarrage
  demandant de charger le compte en crédits avant tout usage.
- La conservation des données envoyées n'a pas pu être vérifiée, les pages juridiques de
  x.ai refusant l'accès, code 403, et la page de questions fréquentes répondant 404.
"""

import json
import logging
import os

import requests

from . import conversation

journal = logging.getLogger("bot")
ADRESSE = "https://api.x.ai/v1/chat/completions"
MODELE = "grok-4.20-0309-non-reasoning"
MODELE_VERIFIE_LE = "2026-11-15"


def configure() -> bool:
    return bool(os.environ.get("XAI_API_KEY"))


def requete(question: str, passe: list[tuple[str, str]]) -> dict:
    contexte = "\n".join(f"{qui} : {quoi}" for qui, quoi in passe) or "aucun"
    return {"model": MODELE,
            "messages": [{"role": "system", "content": conversation.CONSIGNE},
                         {"role": "user", "content": f"Échanges précédents\n{contexte}\n\nNouveau message de "
                                                     f"l'agriculteur\n{question[:conversation.QUESTION_MAX]}"}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "reponse_agricole", "strict": True,
                                "schema": {"type": "object", "additionalProperties": False,
                                           "properties": {"intention": {"type": "string",
                                                                        "enum": ["rotation", "question"]},
                                                          "reponse": {"type": "string"}},
                                           "required": ["intention", "reponse"]}}}}


def appeler(corps: dict, session: requests.Session | None = None) -> dict:
    cle = os.environ.get("XAI_API_KEY")
    if not cle:
        raise RuntimeError("clé XAI_API_KEY absente de l'environnement")
    reponse = (session or requests).post(ADRESSE, json=corps, timeout=60,
                                         headers={"Authorization": f"Bearer {cle}"})
    if reponse.status_code >= 400:
        journal.warning("Grok a refusé la requête, code %s", reponse.status_code)
    reponse.raise_for_status()
    return reponse.json()


def repondre(cle: str, question: str, appel=None) -> tuple[str, str]:
    """Intention, rotation, question ou indisponible, et réponse filtrée à une question écrite ou transcrite."""
    try:
        contenu = (appel or appeler)(requete(question, conversation.historique(cle)))["choices"][0]["message"]["content"]
        sortie = json.loads(contenu)
    except Exception as erreur:
        journal.warning("Grok indisponible, %s", type(erreur).__name__)
        return "indisponible", conversation.SECOURS
    if sortie.get("intention") == "rotation":
        return "rotation", ""
    reponse = conversation.filtrer(sortie.get("reponse") or "") if sortie.get("reponse") else conversation.SECOURS
    conversation.retenir(cle, question, reponse)
    return "question", reponse

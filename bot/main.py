"""Service FastAPI du bot WhatsApp.

Lancement local, depuis la racine du dépôt
    uvicorn bot.main:app --port 8000
"""

import functools
import hmac
import json
import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from . import dialogue
from .config import parametres
from .securite import RegistreMessages, signature_valide
from .whatsapp import messages_entrants

journal = logging.getLogger("bot")
app = FastAPI(title="Field Shift CI, bot WhatsApp")


@functools.cache
def registre(chemin: str) -> RegistreMessages:
    return RegistreMessages(chemin)


@app.get("/sante")
def sante():
    return {"statut": "ok"}


@app.get("/webhook", response_class=PlainTextResponse)
def verifier_webhook(
    mode: str = Query("", alias="hub.mode"),
    jeton: str = Query("", alias="hub.verify_token"),
    defi: str = Query("", alias="hub.challenge"),
):
    """Répond à la vérification de l'abonnement demandée par Meta."""
    attendu = parametres().verify_token
    if mode == "subscribe" and attendu and hmac.compare_digest(jeton.encode(), attendu.encode()):
        return defi
    raise HTTPException(status_code=403)


@app.post("/webhook")
async def recevoir(requete: Request, taches: BackgroundTasks):
    """Vérifie la signature, répond aussitôt et traite chaque nouveau message en tâche de fond."""
    corps = await requete.body()
    reglages = parametres()
    if not signature_valide(corps, requete.headers.get("X-Hub-Signature-256"), reglages.app_secret):
        raise HTTPException(status_code=403)
    for message in messages_entrants(json.loads(corps)):
        if registre(reglages.base_de_donnees).deja_vu(message["id"]):
            journal.info("message déjà traité ignoré")
            continue
        taches.add_task(dialogue.traiter, message)
    return {"statut": "recu"}

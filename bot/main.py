"""Service FastAPI du bot WhatsApp.

Lancement local, depuis la racine du dépôt
    uvicorn bot.main:app --port 8000
"""

import functools
import hmac
import json
import time
import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from . import dialogue
from .config import parametres
from .securite import RegistreMessages, signature_valide
from .whatsapp import messages_entrants

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
journal = logging.getLogger("bot")
app = FastAPI(title="AgriBot, bot WhatsApp de Field Shift CI")


@functools.cache
def registre(chemin: str) -> RegistreMessages:
    return RegistreMessages(chemin)


def preparer_notes_fixes() -> None:
    """Téléverse les notes des questions fixes déjà gardées sur disque, sans aucun appel à Aethex.

    Une phrase fixe est synthétisée à sa première vraie utilisation, puis gardée, si bien
    qu'un redémarrage ne coûte aucun crédit et qu'une phrase jamais dite n'en coûte pas.
    """
    from . import whatsapp
    from .dialogue import phrases_fixes
    from .langage import voix

    if not (voix.configuree() and parametres().access_token):
        return
    for phrase in phrases_fixes():
        if (note := voix.note_gardee(phrase)) is not None:
            whatsapp.televerser_audio(note)


def prechauffer() -> None:
    """Charge au démarrage ce qui ralentirait le premier message, les données NASA, Whisper et la voix."""
    import time

    from moteur.lieux import LIEUX
    from moteur.recommander import donnees_du_lieu

    from .langage import transcription_locale, voix

    debut = time.monotonic()
    from moteur.alerte import alerte_du_lieu

    for etape, action in [("données NASA", lambda: [donnees_du_lieu(lieu) for lieu in LIEUX]),
                          ("alertes de végétation HLS", lambda: [alerte_du_lieu(lieu) for lieu in LIEUX]),
                          ("Whisper", transcription_locale._modele),
                          ("voix Aethex", lambda: voix.configuree() and voix.voix()),
                          ("notes vocales fixes", preparer_notes_fixes)]:
        try:
            action()
        except Exception as erreur:
            journal.warning("préchauffage de %s impossible, %s", etape, type(erreur).__name__)
    journal.info("préchauffage terminé en %.0f s", time.monotonic() - debut)


@app.on_event("startup")
def demarrer() -> None:
    import threading

    threading.Thread(target=prechauffer, daemon=True).start()


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
        # L'âge du message, d'après l'heure d'envoi donnée par WhatsApp, révèle un message livré en retard.
        # Aucun contenu n'est écrit dans le journal, seulement le type, l'âge et la longueur d'un texte.
        try:
            age = max(0, int(time.time()) - int(message.get("timestamp", 0))) if message.get("timestamp") else None
        except (TypeError, ValueError):
            age = None
        longueur = len((message.get("text") or {}).get("body", "")) if message.get("type") == "text" else None
        journal.info("message %s reçu%s%s", message.get("type"),
                     f", envoyé il y a {age} s" if age is not None else "",
                     f", {longueur} caractères" if longueur is not None else "")
        taches.add_task(dialogue.traiter, message)
    return {"statut": "recu"}

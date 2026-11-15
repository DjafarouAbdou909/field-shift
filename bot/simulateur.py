"""Conversation avec le bot dans le terminal, sans WhatsApp.

Le vrai dialogue, le vrai moteur et, si leurs clés sont dans l'environnement, les vrais
services Gemini et Aethex. Les messages du bot s'affichent au lieu d'être envoyés, les
boutons et les listes sont numérotés, et l'on répond par le numéro ou le titre.

Lancement depuis la racine du dépôt
    set -a; . ./.env; set +a
    venv/bin/python -m bot.simulateur

Commandes
    /photo chemin.jpg       envoie une photo de feuille
    /position 9.45 -5.63    envoie une position
    /vocal chemin.ogg       envoie une note vocale
    /quitter                termine
"""

import mimetypes
import os
import sys
from pathlib import Path

from . import dialogue
from .sessions import Sessions

NUMERO = "simulateur"


class CanalTerminal:
    def __init__(self):
        self.medias: dict[str, bytes] = {}

    def envoyer_texte(self, destinataire, texte):
        print(f"\nField Shift\n{texte}")

    def envoyer_boutons(self, destinataire, texte, boutons):
        print(f"\nField Shift\n{texte}")
        for rang, titre in enumerate(boutons.values(), start=1):
            print(f"  [{rang}] {titre}")

    def envoyer_liste(self, destinataire, texte, lignes, libelle):
        self.envoyer_boutons(destinataire, texte, lignes)

    def envoyer_audio(self, destinataire, audio):
        chemin = Path("data/simulateur_reponse.ogg")
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_bytes(audio)
        print(f"\nField Shift\n[note vocale enregistrée dans {chemin}, à écouter puis à effacer]")

    def telecharger_media(self, media_id):
        return self.medias.pop(media_id)


def message(ligne: str, canal: CanalTerminal) -> dict | None:
    base = {"from": NUMERO, "id": str(len(canal.medias))}
    mots = ligne.split(maxsplit=1)
    if mots and mots[0] in ("/photo", "/vocal") and len(mots) == 2:
        chemin = Path(mots[1]).expanduser()
        if not chemin.is_file():
            print(f"fichier introuvable, {chemin}")
            return None
        media_id = f"media-{chemin.name}"
        canal.medias[media_id] = chemin.read_bytes()
        type_mime = mimetypes.guess_type(chemin.name)[0] or "application/octet-stream"
        if mots[0] == "/photo":
            return {**base, "type": "image", "image": {"id": media_id, "mime_type": type_mime}}
        return {**base, "type": "audio", "audio": {"id": media_id, "mime_type": "audio/ogg; codecs=opus"}}
    if mots and mots[0] == "/position":
        try:
            latitude, longitude = (float(x) for x in mots[1].split())
        except (IndexError, ValueError):
            print("usage, /position 9.45 -5.63")
            return None
        return {**base, "type": "location", "location": {"latitude": latitude, "longitude": longitude}}
    return {**base, "type": "text", "text": {"body": ligne}}


def main() -> None:
    if not os.environ.get("SEL_NUMEROS"):
        os.environ["SEL_NUMEROS"] = "sel-du-simulateur"
    canal, magasin = CanalTerminal(), Sessions(":memory:")
    print("Simulateur Field Shift. Écrivez Bonjour pour commencer, /quitter pour finir.")
    for ligne in sys.stdin if not sys.stdin.isatty() else iter(lambda: input("\nVous > "), None):
        ligne = ligne.strip()
        if ligne == "/quitter":
            break
        if ligne and (entrant := message(ligne, canal)):
            dialogue.traiter(entrant, canal=canal, magasin=magasin)


if __name__ == "__main__":
    main()

"""Échanges avec WhatsApp Cloud API.

Formats lus le 15 novembre 2026 dans la documentation officielle de Meta,
https://developers.facebook.com/docs/whatsapp/cloud-api, pages des messages texte, des
boutons de réponse, des listes, de l'audio, des médias et du webhook messages. Version de
l'API v27.0, la plus récente selon https://developers.facebook.com/docs/graph-api/changelog.

- Envoi, POST https://graph.facebook.com/v27.0/<phone_number_id>/messages, jeton dans
  l'en-tête Authorization Bearer. Texte de 4 096 caractères au plus.
- Boutons, 3 au plus, titre de 20 caractères au plus et unique, corps de 1 024 caractères.
- Liste, 10 lignes au plus, titre de ligne et de section de 24 caractères, libellé du
  bouton de 20 caractères, corps de 4 096 caractères.
- Média reçu, GET /<media_id> donne une adresse valable 5 minutes, téléchargée avec le
  même jeton.
- Note vocale envoyée, fichier OGG encodé en Opus, mono, 16 Mo au plus, téléversé par
  POST /<phone_number_id>/media puis envoyé par son identifiant avec voice à vrai.

Une réponse libre n'est possible que dans les 24 heures qui suivent le dernier message de
l'agriculteur, ce qui est toujours le cas ici, le bot ne faisant que répondre.
"""

import functools
from collections.abc import Iterator

import httpx

from .config import parametres

VERSION_API = "v27.0"
URL_GRAPH = f"https://graph.facebook.com/{VERSION_API}"
TEXTE_MAX, CORPS_BOUTONS_MAX, TITRE_BOUTON_MAX, BOUTONS_MAX = 4096, 1024, 20, 3
LIGNES_MAX, TITRE_LIGNE_MAX, LIBELLE_LISTE_MAX = 10, 24, 20
AUDIO_MAX_OCTETS = 16 * 1024 * 1024
IMAGE_MAX_OCTETS = 5 * 1024 * 1024


def messages_entrants(charge: dict) -> Iterator[dict]:
    """Parcourt les messages d'une notification de webhook, en ignorant les statuts de livraison."""
    for entree in charge.get("entry", []):
        for changement in entree.get("changes", []):
            yield from changement.get("value", {}).get("messages", [])


@functools.cache
def _http() -> httpx.Client:
    """Client gardé ouvert d'un message à l'autre. Mesuré le 15 novembre 2026, une requête à Meta prend
    0,3 à 0,6 seconde sur une connexion gardée, contre 0,6 à 2,1 secondes sur une connexion neuve."""
    return httpx.Client(timeout=30, follow_redirects=True)


def _entetes() -> dict[str, str]:
    jeton = parametres().access_token
    if not jeton:
        raise RuntimeError("jeton WHATSAPP_ACCESS_TOKEN absent de l'environnement")
    return {"Authorization": f"Bearer {jeton}"}


def _numero() -> str:
    numero = parametres().phone_number_id
    if not numero:
        raise RuntimeError("identifiant WHATSAPP_PHONE_NUMBER_ID absent de l'environnement")
    return numero


def _envoyer(destinataire: str, type_message: str, contenu: dict) -> dict:
    corps = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": destinataire,
             "type": type_message, type_message: contenu}
    reponse = _http().post(f"{URL_GRAPH}/{_numero()}/messages", json=corps, headers=_entetes())
    reponse.raise_for_status()
    return reponse.json()


def morceaux(texte: str, taille: int = TEXTE_MAX) -> list[str]:
    """Découpe un long texte aux sauts de ligne pour rester sous la limite de WhatsApp."""
    parties, courante = [], ""
    for ligne in texte.split("\n"):
        while len(ligne) > taille:
            parties.append(ligne[:taille])
            ligne = ligne[taille:]
        if courante and len(courante) + 1 + len(ligne) > taille:
            parties.append(courante)
            courante = ligne
        else:
            courante = f"{courante}\n{ligne}" if courante else ligne
    return parties + [courante] if courante else parties


def indiquer_saisie(message_id: str) -> None:
    """Marque le message comme lu et affiche « en train d'écrire » jusqu'à la réponse, 25 secondes au plus.

    Page Typing indicators de la documentation de Meta, lue le 15 novembre 2026.
    """
    reponse = _http().post(f"{URL_GRAPH}/{_numero()}/messages", headers=_entetes(),
                           json={"messaging_product": "whatsapp", "status": "read", "message_id": message_id,
                                 "typing_indicator": {"type": "text"}})
    reponse.raise_for_status()


def envoyer_texte(destinataire: str, texte: str) -> None:
    for partie in morceaux(texte):
        _envoyer(destinataire, "text", {"body": partie})


def verifier_boutons(texte: str, boutons: dict[str, str]) -> None:
    titres = list(boutons.values())
    if not 1 <= len(boutons) <= BOUTONS_MAX or len(set(titres)) != len(titres):
        raise ValueError("de 1 à 3 boutons aux titres uniques")
    if any(len(t) > TITRE_BOUTON_MAX for t in titres) or len(texte) > CORPS_BOUTONS_MAX:
        raise ValueError("titre de bouton ou corps trop long")


def envoyer_boutons(destinataire: str, texte: str, boutons: dict[str, str]) -> None:
    """boutons associe un identifiant à un titre court, 3 au plus."""
    verifier_boutons(texte, boutons)
    _envoyer(destinataire, "interactive", {
        "type": "button", "body": {"text": texte},
        "action": {"buttons": [{"type": "reply", "reply": {"id": i, "title": t}} for i, t in boutons.items()]}})


def verifier_liste(texte: str, lignes: dict[str, str], libelle: str) -> None:
    if not 1 <= len(lignes) <= LIGNES_MAX or len(texte) > TEXTE_MAX or len(libelle) > LIBELLE_LISTE_MAX:
        raise ValueError("de 1 à 10 lignes, libellé de 20 caractères au plus")
    if any(len(t) > TITRE_LIGNE_MAX for t in lignes.values()):
        raise ValueError("titre de ligne de plus de 24 caractères")


def envoyer_liste(destinataire: str, texte: str, lignes: dict[str, str], libelle: str = "Choisir") -> None:
    """lignes associe un identifiant à un titre, 10 au plus."""
    verifier_liste(texte, lignes, libelle)
    _envoyer(destinataire, "interactive", {
        "type": "list", "body": {"text": texte},
        "action": {"button": libelle, "sections": [{"title": libelle, "rows": [
            {"id": i, "title": t} for i, t in lignes.items()]}]}})


def telecharger_media(media_id: str) -> bytes:
    """Récupère l'adresse du média par son identifiant, puis son contenu, avec le jeton. Rien n'est écrit."""
    entetes = _entetes()
    infos = _http().get(f"{URL_GRAPH}/{media_id}", headers=entetes)
    infos.raise_for_status()
    contenu = _http().get(infos.json()["url"], headers=entetes, timeout=60)
    contenu.raise_for_status()
    return contenu.content


# Identifiants des notes déjà téléversées, par empreinte. Meta garde un média 30 jours.
_medias: dict[str, tuple[float, str]] = {}
DUREE_MEDIA_SECONDES = 29 * 24 * 3600


def televerser_audio(audio_ogg_opus: bytes) -> str:
    """Identifiant WhatsApp de la note vocale, téléversée une seule fois pour un même contenu."""
    import hashlib
    import time

    if len(audio_ogg_opus) > AUDIO_MAX_OCTETS:
        raise ValueError("note vocale de plus de 16 Mo")
    empreinte = hashlib.sha256(audio_ogg_opus).hexdigest()
    moment, identifiant = _medias.get(empreinte, (0.0, ""))
    if identifiant and time.monotonic() - moment < DUREE_MEDIA_SECONDES:
        return identifiant
    televersement = _http().post(f"{URL_GRAPH}/{_numero()}/media", headers=_entetes(), timeout=60,
                               data={"messaging_product": "whatsapp", "type": "audio/ogg"},
                               files={"file": ("reponse.ogg", audio_ogg_opus, "audio/ogg")})
    televersement.raise_for_status()
    identifiant = televersement.json()["id"]
    _medias[empreinte] = (time.monotonic(), identifiant)
    return identifiant


def envoyer_audio(destinataire: str, audio_ogg_opus: bytes) -> None:
    """Envoie la note vocale comme message vocal, par l'identifiant de son téléversement."""
    _envoyer(destinataire, "audio", {"id": televerser_audio(audio_ogg_opus), "voice": True})


def envoyer_image(destinataire: str, image_png: bytes, legende: str = "") -> None:
    """Envoie une image PNG, la carte du champ, téléversée puis envoyée par son identifiant."""
    if len(image_png) > IMAGE_MAX_OCTETS:
        raise ValueError("image de plus de 5 Mo")
    televersement = _http().post(f"{URL_GRAPH}/{_numero()}/media", headers=_entetes(), timeout=60,
                               data={"messaging_product": "whatsapp", "type": "image/png"},
                               files={"file": ("carte.png", image_png, "image/png")})
    televersement.raise_for_status()
    _envoyer(destinataire, "image", {"id": televersement.json()["id"], "caption": legende[:1024]})

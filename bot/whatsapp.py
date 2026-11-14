"""Échanges avec WhatsApp Cloud API.

messages_entrants est écrit. Les fonctions d'envoi sont à écrire par le membre A, avec
httpx, l'URL https://graph.facebook.com/<version>/<phone_number_id>/messages et le jeton
de config.parametres(). Limites à respecter, 3 boutons au plus par message avec des
titres très courts, 10 lignes au plus par liste.
"""

from collections.abc import Iterator


def messages_entrants(charge: dict) -> Iterator[dict]:
    """Parcourt les messages d'une notification de webhook, en ignorant les statuts de livraison."""
    for entree in charge.get("entry", []):
        for changement in entree.get("changes", []):
            yield from changement.get("value", {}).get("messages", [])


def envoyer_texte(destinataire: str, texte: str) -> None:
    raise NotImplementedError


def envoyer_boutons(destinataire: str, texte: str, boutons: dict[str, str]) -> None:
    """boutons associe un identifiant à un titre court, 3 au plus."""
    raise NotImplementedError


def envoyer_liste(destinataire: str, texte: str, lignes: dict[str, str]) -> None:
    """lignes associe un identifiant à un titre, 10 au plus."""
    raise NotImplementedError


def telecharger_media(media_id: str) -> bytes:
    """Récupère l'URL du média par son identifiant, puis son contenu, avec le jeton."""
    raise NotImplementedError


def envoyer_audio(destinataire: str, audio_ogg_opus: bytes) -> None:
    """Téléverse l'audio, puis l'envoie par son identifiant."""
    raise NotImplementedError

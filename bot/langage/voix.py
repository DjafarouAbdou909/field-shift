"""Transcription des notes vocales et synthèse vocale, à écrire par le membre B.

Les notes vocales WhatsApp arrivent en OGG Opus. La synthèse est convertie en OGG Opus
avec ffmpeg avant l'envoi. Les audios reçus sont supprimés après transcription.
"""


def transcrire(audio: bytes, type_mime: str) -> str:
    raise NotImplementedError


def synthetiser(texte: str) -> bytes:
    """Retourne une note vocale en OGG Opus."""
    raise NotImplementedError

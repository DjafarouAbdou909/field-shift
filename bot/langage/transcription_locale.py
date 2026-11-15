"""Transcription locale des notes vocales avec Whisper, secours quand Gemini ne répond pas.

Demande du responsable du 15 novembre 2026, pour que le bot comprenne encore les notes
vocales quand le quota de Gemini est épuisé, la clé au niveau gratuit étant limitée à
20 requêtes par jour. Le calcul se fait sur la machine du bot, sans réseau ni quota, avec
faster-whisper 1.2.1, licence MIT, https://github.com/SYSTRAN/faster-whisper, et le
modèle Whisper small, téléchargé une fois dans data/modeles.

Le modèle reçoit en amorce les noms du projet, ce qui lui fait reconnaître Korhogo là où
Aethex entendait robot, lors d'un essai du 15 novembre 2026 sur une note de synthèse.
Une note de plus de 120 secondes est refusée, comme dans voix.py. Rien n'est écrit sur
disque, sauf le modèle.
"""

import logging
import os
from functools import cache

import numpy as np

from .voix import DUREE_MAX_SECONDES, TAUX_TRANSCRIPTION, _pcm_mono

journal = logging.getLogger("bot")
DOSSIER_MODELES = "data/modeles"
AMORCE = ("Korhogo, Bouaké, Poro, Gbêkê, coton, maïs, sorgho, niébé, mil, igname, arachide, rotation, champ, "
          "ANADER.")


def taille() -> str:
    return os.environ.get("WHISPER_MODELE", "small")


@cache
def _modele():
    from faster_whisper import WhisperModel

    return WhisperModel(taille(), device="cpu", compute_type="int8", download_root=DOSSIER_MODELES)


def transcrire(audio: bytes) -> str:
    """Texte d'une note vocale, chaîne vide si rien n'est entendu."""
    pcm, duree = _pcm_mono(audio, TAUX_TRANSCRIPTION)
    if duree > DUREE_MAX_SECONDES:
        raise ValueError(f"note vocale de plus de {DUREE_MAX_SECONDES} secondes")
    signal = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
    segments, _ = _modele().transcribe(signal, language="fr", initial_prompt=AMORCE, beam_size=5)
    return " ".join(segment.text.strip() for segment in segments).strip()

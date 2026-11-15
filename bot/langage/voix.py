"""Transcription des notes vocales et synthèse vocale avec Aethex AI.

Décision du responsable du 14 novembre 2026, qui a déjà employé Aethex pour la voix et la
transcription dans un autre projet. La documentation développeur coupant la connexion le
14 novembre 2026, les points d'accès sont lus dans le code source du SDK officiel
aethexai 1.0.2, licence MIT, https://github.com/aethexai/aethexai-python, fichier kora.py.

- Transcription, POST /api/v1/transcribe, fichier envoyé en multipart avec la langue. Le
  SDK découpe un WAV de plus de 35 secondes en morceaux et recolle les textes.
- Synthèse, POST /api/v1/tts, texte, voix et langue, réponse en WAV. L'API refuse plus de
  650 caractères par requête, d'où un découpage aux fins de phrase et un recollage en une
  seule note vocale.
- Voix, GET /api/v1/voices, filtrée par langue et par pays.
- Clé AETHEX_API_KEY, lue dans l'environnement et jamais écrite dans le dépôt, envoyée
  dans l'en-tête X-API-Key par le SDK.

Formats. WhatsApp envoie les notes vocales en OGG Opus. Elles sont converties en WAV mono
à 16 kHz avant l'envoi, les formats acceptés par Aethex n'ayant pas pu être lus. La voix
de synthèse, en WAV, est convertie en OGG Opus mono à 48 kHz pour WhatsApp. Les
conversions passent par PyAV, en mémoire. Aucun audio n'est écrit sur disque ni gardé.

Langue french, comme dans l'autre projet. Voix fixée par AETHEX_VOICE_ID si elle est
définie, sinon la première voix française de Côte d'Ivoire, sinon la première voix
française proposée.

Limites. La durée de conservation des audios et des textes par Aethex pour ces points
d'accès n'est pas documentée dans ce qui a été lu. La politique de confidentialité
d'Aethex du 10 avril 2026 prévoit l'usage des données pour améliorer ses services et une
conservation d'au plus un an. L'autre projet note qu'avec une vraie voix la transcription
d'Aethex déformait des phrases. La qualité en français ivoirien reste à mesurer.
"""

import io
import os
import wave
from functools import cache, lru_cache

import av

URL_API = "https://api.aethexai.com"
LANGUE = "french"
PAYS = "CI"
DUREE_MAX_SECONDES = 120
TAUX_TRANSCRIPTION = 16000
TAUX_OPUS = 48000
# 24 kbit/s suffisent pour la voix et gardent une note de 2 minutes sous 512 Ko, taille au-delà de
# laquelle WhatsApp n'affiche plus l'icône de lecture, selon la documentation de Meta lue le 15 novembre 2026.
DEBIT_OPUS = 24000
SYNTHESE_MAX_CARACTERES = 600  # Aethex refuse plus de 650 caractères par requête, message lu le 15 novembre 2026


def configuree() -> bool:
    return bool(os.environ.get("AETHEX_API_KEY"))


@cache
def _kora():
    from aethexai import Kora

    cle = os.environ.get("AETHEX_API_KEY")
    if not cle:
        raise RuntimeError("clé AETHEX_API_KEY absente de l'environnement")
    return Kora(URL_API, cle, timeout=60)


def _pcm_mono(audio: bytes, taux: int) -> tuple[bytes, float]:
    """Décode un audio quelconque en PCM 16 bits mono au taux voulu, avec sa durée en secondes."""
    reechantillonneur = av.AudioResampler(format="s16", layout="mono", rate=taux)
    morceaux = []
    with av.open(io.BytesIO(audio)) as conteneur:
        for trame in conteneur.decode(audio=0):
            morceaux += [t.to_ndarray().tobytes() for t in reechantillonneur.resample(trame)]
    morceaux += [t.to_ndarray().tobytes() for t in reechantillonneur.resample(None)]
    pcm = b"".join(morceaux)
    return pcm, len(pcm) / 2 / taux


def vers_wav(audio: bytes) -> bytes:
    """Convertit un audio, une note vocale OGG Opus par exemple, en WAV mono à 16 kHz."""
    pcm, duree = _pcm_mono(audio, TAUX_TRANSCRIPTION)
    if duree > DUREE_MAX_SECONDES:
        raise ValueError(f"note vocale de plus de {DUREE_MAX_SECONDES} secondes")
    sortie = io.BytesIO()
    with wave.open(sortie, "wb") as fichier:
        fichier.setnchannels(1)
        fichier.setsampwidth(2)
        fichier.setframerate(TAUX_TRANSCRIPTION)
        fichier.writeframes(pcm)
    return sortie.getvalue()


def pcm_vers_ogg_opus(pcm: bytes) -> bytes:
    """Encode du PCM 16 bits mono à 48 kHz en note vocale OGG Opus."""
    import numpy as np

    sortie = io.BytesIO()
    with av.open(sortie, "w", format="ogg") as conteneur:
        flux = conteneur.add_stream("libopus", rate=TAUX_OPUS, layout="mono")
        flux.bit_rate = DEBIT_OPUS
        echantillons = np.frombuffer(pcm, dtype=np.int16)
        for debut in range(0, len(echantillons), TAUX_OPUS // 50):
            morceau = echantillons[debut:debut + TAUX_OPUS // 50].reshape(1, -1)
            trame = av.AudioFrame.from_ndarray(morceau, format="s16", layout="mono")
            trame.sample_rate = TAUX_OPUS
            conteneur.mux(flux.encode(trame))
        conteneur.mux(flux.encode(None))
    return sortie.getvalue()


def vers_ogg_opus(*audios: bytes) -> bytes:
    """Convertit un ou plusieurs audios, les WAV de la synthèse par exemple, en une note vocale OGG Opus mono."""
    return pcm_vers_ogg_opus(b"".join(_pcm_mono(audio, TAUX_OPUS)[0] for audio in audios))


def morceaux(texte: str, taille: int) -> list[str]:
    """Découpe un texte en morceaux de taille limitée, aux fins de phrase, sinon aux espaces."""
    import re

    resultat, courant = [], ""
    for phrase in re.split(r"(?<=[.!?:])\s+", texte.strip()):
        while len(phrase) > taille:
            coupe = phrase.rfind(" ", 0, taille)
            coupe = coupe if coupe > 0 else taille
            if courant:
                resultat.append(courant)
                courant = ""
            resultat.append(phrase[:coupe].strip())
            phrase = phrase[coupe:].strip()
        if courant and len(courant) + 1 + len(phrase) > taille:
            resultat.append(courant)
            courant = phrase
        else:
            courant = f"{courant} {phrase}".strip()
    return [m for m in resultat + [courant] if m]


@cache
def voix() -> str | None:
    """Voix de synthèse, fixée par AETHEX_VOICE_ID, sinon une voix française de Côte d'Ivoire, sinon française."""
    if os.environ.get("AETHEX_VOICE_ID"):
        return os.environ["AETHEX_VOICE_ID"]
    kora = _kora()
    trouvees = kora.list_voices(language=LANGUE, country=PAYS, limit=1) or kora.list_voices(language=LANGUE, limit=1)
    return trouvees[0].id if trouvees else None


def transcrire(audio: bytes, type_mime: str) -> str:
    """Texte d'une note vocale, chaîne vide si rien n'est compris. L'audio n'est jamais conservé."""
    wav = audio if type_mime.split(";")[0].strip() in ("audio/wav", "audio/x-wav") else vers_wav(audio)
    resultat = _kora().transcribe(wav, language=LANGUE, file_name="note.wav", mime_type="audio/wav")
    return (getattr(resultat, "text", "") or "").strip()


@lru_cache(maxsize=256)
def synthetiser(texte: str) -> bytes:
    """Retourne une note vocale en OGG Opus, gardée en mémoire pour un texte déjà dit.

    Les morceaux d'un texte long sont synthétisés en parallèle, puis recollés dans l'ordre.
    """
    from concurrent.futures import ThreadPoolExecutor

    identifiant = voix()
    if identifiant is None:
        raise RuntimeError("aucune voix française proposée par Aethex")
    parties = morceaux(texte, SYNTHESE_MAX_CARACTERES)
    with ThreadPoolExecutor(max_workers=min(4, len(parties)) or 1) as executeur:
        wavs = list(executeur.map(lambda morceau: _kora().synthesize_speech(morceau, identifiant, language=LANGUE),
                                  parties))
    return vers_ogg_opus(*wavs)

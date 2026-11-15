"""Transcription des notes vocales et synthèse vocale avec Aethex AI.

Décision du responsable du 14 novembre 2026, qui a déjà employé Aethex pour la voix et la
transcription dans un autre projet. La documentation développeur coupant la connexion le
14 novembre 2026, les points d'accès sont lus dans le code source du SDK officiel
aethexai 1.0.2, licence MIT, https://github.com/aethexai/aethexai-python, fichier kora.py.

- Transcription, POST /api/v1/transcribe, fichier envoyé en multipart avec la langue. Le
  SDK découpe un WAV de plus de 35 secondes en morceaux et recolle les textes.
- Synthèse en flux, POST /api/v1/tts/stream, texte, voix et langue, réponse en PCM 16 bits
  mono à 24 kHz livrée au fil de la génération, selon la docstring de stream_speech du SDK.
  Mesure du 15 novembre 2026 sur une phrase de 182 caractères, 1,6 seconde en flux contre
  4,2 secondes par POST /api/v1/tts, qui répond en WAV et reste le secours si le flux
  échoue. L'API refuse plus de 650 caractères par requête, d'où un découpage aux fins de
  phrase et un recollage en une seule note vocale.
- Voix, GET /api/v1/voices, filtrée par langue et par pays.
- Clé AETHEX_API_KEY, lue dans l'environnement et jamais écrite dans le dépôt, envoyée
  dans l'en-tête X-API-Key par le SDK.

Formats. WhatsApp envoie les notes vocales en OGG Opus. Elles sont converties en WAV mono
à 16 kHz avant l'envoi, les formats acceptés par Aethex n'ayant pas pu être lus. La voix
de synthèse, en WAV, est convertie en OGG Opus mono à 48 kHz pour WhatsApp. Les
conversions passent par PyAV, en mémoire. Le PCM du flux est encodé tel quel en Opus à
  24 kHz, taux que Opus accepte, sans rééchantillonnage. Aucun audio d'agriculteur n'est
  écrit sur disque ni gardé.

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

import logging

import av

journal = logging.getLogger("bot")
URL_API = "https://api.aethexai.com"
LANGUE = "french"
PAYS = "CI"
DUREE_MAX_SECONDES = 120
TAUX_TRANSCRIPTION = 16000
TAUX_OPUS = 48000
TAUX_FLUX = 24000  # PCM 16 bits mono du flux de synthèse d'Aethex
# 24 kbit/s suffisent pour la voix et gardent une note de 2 minutes sous 512 Ko, taille au-delà de
# laquelle WhatsApp n'affiche plus l'icône de lecture, selon la documentation de Meta lue le 15 novembre 2026.
DEBIT_OPUS = 24000
SYNTHESE_MAX_CARACTERES = 600  # Aethex refuse plus de 650 caractères par requête, message lu le 15 novembre 2026


PAUSE_CREDITS_SECONDES = 15 * 60
_en_pause_jusqua = 0.0


def configuree() -> bool:
    """Vrai si Aethex a une clé et n'est pas en pause après un refus pour crédits épuisés."""
    import time

    return bool(os.environ.get("AETHEX_API_KEY")) and time.monotonic() >= _en_pause_jusqua


def _refus_de_paiement(erreur: Exception) -> bool:
    return getattr(erreur, "status_code", None) == 402 or "credits" in str(erreur).lower()


def _signaler_refus(erreur: Exception) -> None:
    """Met Aethex en pause quinze minutes après un refus de paiement, code 402."""
    import time

    global _en_pause_jusqua
    if _refus_de_paiement(erreur):
        _en_pause_jusqua = time.monotonic() + PAUSE_CREDITS_SECONDES
        journal.warning("crédits Aethex épuisés, voix mise en pause %s minutes", PAUSE_CREDITS_SECONDES // 60)


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


def pcm_vers_ogg_opus(pcm: bytes, taux: int = TAUX_OPUS) -> bytes:
    """Encode du PCM 16 bits mono, à 48 kHz ou à un autre taux accepté par Opus, en note vocale OGG Opus."""
    import numpy as np

    sortie = io.BytesIO()
    with av.open(sortie, "w", format="ogg") as conteneur:
        flux = conteneur.add_stream("libopus", rate=taux, layout="mono")
        flux.bit_rate = DEBIT_OPUS
        echantillons = np.frombuffer(pcm, dtype=np.int16)
        # Tranches d'une seconde, PyAV redécoupant pour Opus, au lieu de milliers de tranches de 20 ms.
        for debut in range(0, len(echantillons), taux):
            morceau = echantillons[debut:debut + taux].reshape(1, -1)
            trame = av.AudioFrame.from_ndarray(morceau, format="s16", layout="mono")
            trame.sample_rate = taux
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


DOSSIER_NOTES = "data/voix"
CARACTERES_PAR_JOUR = int(os.environ.get("AETHEX_CARACTERES_PAR_JOUR") or "8000")
_depense = {"jour": "", "caracteres": 0}


def _reserver(caracteres: int) -> None:
    """Compte les caractères envoyés à Aethex dans la journée, et refuse au-delà du plafond."""
    import time

    jour = time.strftime("%Y-%m-%d")
    if _depense["jour"] != jour:
        _depense.update(jour=jour, caracteres=0)
    if _depense["caracteres"] + caracteres > CARACTERES_PAR_JOUR:
        raise RuntimeError("plafond quotidien de caractères Aethex atteint")
    _depense["caracteres"] += caracteres


def _note_sur_disque(texte: str):
    import hashlib
    from pathlib import Path

    return Path(DOSSIER_NOTES) / f"{hashlib.sha256(f'{voix()}|{texte}'.encode()).hexdigest()}.ogg"


def _pcm_du_flux(morceau: str, identifiant: str) -> bytes:
    """PCM 16 bits mono à 24 kHz d'un morceau, par le flux de synthèse d'Aethex."""
    donnees = b"".join(_kora().stream_speech(morceau, identifiant, language=LANGUE))
    if donnees[:4] == b"RIFF":
        return _pcm_mono(donnees, TAUX_FLUX)[0]
    return donnees[:len(donnees) - len(donnees) % 2]


def _pcm_synthetise(morceau: str, identifiant: str) -> bytes:
    """PCM d'un morceau, par le flux, sinon par la synthèse en WAV. Un refus de paiement n'est pas retenté."""
    try:
        pcm = _pcm_du_flux(morceau, identifiant)
        if pcm:
            return pcm
        journal.warning("flux Aethex vide, synthèse en WAV")
    except Exception as erreur:
        if _refus_de_paiement(erreur):
            raise
        journal.warning("flux Aethex indisponible, %s, synthèse en WAV", type(erreur).__name__)
    return _pcm_mono(_kora().synthesize_speech(morceau, identifiant, language=LANGUE), TAUX_FLUX)[0]


@lru_cache(maxsize=256)
def synthetiser(texte: str) -> bytes:
    """Retourne une note vocale en OGG Opus. Une phrase déjà dite ne coûte plus aucun crédit.

    Les notes sont gardées en mémoire, et sur disque dans data/voix pour les phrases fixes
    du bot, qui survivent ainsi aux redémarrages. Les caractères envoyés à Aethex sont
    plafonnés chaque jour par AETHEX_CARACTERES_PAR_JOUR, 8 000 par défaut, soit environ
    64 000 crédits au tarif de 4 000 crédits pour 500 caractères, page des prix d'Aethex.
    Les morceaux d'un texte long sont synthétisés en parallèle, par le flux d'Aethex, puis
    recollés dans l'ordre et encodés en une seule note à 24 kHz.
    """
    from concurrent.futures import ThreadPoolExecutor

    identifiant = voix()
    if identifiant is None:
        raise RuntimeError("aucune voix française proposée par Aethex")
    parties = morceaux(texte, SYNTHESE_MAX_CARACTERES)
    _reserver(sum(len(partie) for partie in parties))
    try:
        with ThreadPoolExecutor(max_workers=min(4, len(parties)) or 1) as executeur:
            pcms = list(executeur.map(lambda morceau: _pcm_synthetise(morceau, identifiant), parties))
    except Exception as erreur:
        _signaler_refus(erreur)
        raise
    return pcm_vers_ogg_opus(b"".join(pcms), TAUX_FLUX)


def note_gardee(texte: str) -> bytes | None:
    """Note d'une phrase fixe déjà synthétisée et gardée sur disque, sans aucun appel à Aethex."""
    chemin = _note_sur_disque(texte)
    return chemin.read_bytes() if chemin.exists() else None


def synthetiser_phrase_fixe(texte: str) -> bytes:
    """Note d'une phrase fixe du bot, relue sur disque si elle a déjà été synthétisée. Aucune donnée d'agriculteur."""
    chemin = _note_sur_disque(texte)
    if chemin.exists():
        return chemin.read_bytes()
    note = synthetiser(texte)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(note)
    return note

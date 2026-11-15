"""Compréhension d'une réponse dite ou écrite librement, pour un agriculteur qui ne lit pas.

Une réponse est rattachée à une option de l'étape en cours en trois temps.
1. Le titre, l'identifiant ou le numéro exact de l'option.
2. Les mots-clés de l'option, dans gabarits.MOTS_CLES, où coton+mais exige les deux mots,
   et les nombres dits en toutes lettres. L'option qui en contient le plus l'emporte, une
   égalité ne tranche rien.
3. Sinon, Gemini choisit l'option qui correspond le mieux à la phrase, par une réponse
   imposée dans une énumération des options et de aucun. Même modèle et mêmes réglages
   que le diagnostic, store à faux.

Une note vocale est écoutée directement par Gemini, qui rend sa transcription et l'option
choisie, la transcription d'Aethex servant de secours.

Rien n'est gardé de la phrase ni de l'audio.
"""

import logging
import re
import unicodedata

from moteur.diagnostic import GRAINE, MODELE, appeler, texte_de_sortie

from .gabarits import MOTS_CLES

journal = logging.getLogger("bot")
AUCUN = "aucun"
NOMBRES = {"un": 1, "une": 1, "premier": 1, "premiere": 1, "deux": 2, "deuxieme": 2, "second": 2, "seconde": 2,
           "trois": 3, "troisieme": 3, "quatre": 4, "quatrieme": 4, "cinq": 5, "cinquieme": 5}


def normaliser(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower().replace("’", "'"))
    sans_accents = "".join(c for c in decompose if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9' ]+", " ", sans_accents).strip()


def _contient(texte: str, expression: str) -> bool:
    """Expression présente comme mot ou groupe de mots. Avec +, chaque partie doit être présente."""
    return all(re.search(rf"(?<![a-z0-9]){re.escape(normaliser(partie))}(?![a-z0-9])", texte) is not None
               for partie in expression.split("+"))


def par_les_mots(texte: str, options: dict[str, str], mots_cles: dict[str, list[str]] | None = None) -> str | None:
    """Option reconnue sans modèle de langage, ou None. mots_cles remplace gabarits.MOTS_CLES."""
    mots_cles = MOTS_CLES if mots_cles is None else mots_cles
    texte = normaliser(texte)
    if not texte:
        return None
    for rang, (identifiant, titre) in enumerate(options.items(), start=1):
        if texte in (normaliser(identifiant), normaliser(titre), str(rang)):
            return identifiant
    rangs = {NOMBRES[mot] for mot in texte.split() if mot in NOMBRES} | {int(m) for m in re.findall(r"\b\d\b", texte)}
    if len(rangs) == 1 and 1 <= (rang := rangs.pop()) <= len(options) and len(texte.split()) <= 4:
        return list(options)[rang - 1]
    scores = {identifiant: sum(_contient(texte, mot) for mot in [titre, identifiant, *mots_cles.get(identifiant, [])])
              for identifiant, titre in options.items()}
    meilleur = max(scores.values())
    gagnants = [i for i, s in scores.items() if s == meilleur]
    return gagnants[0] if meilleur > 0 and len(gagnants) == 1 else None


def requete(texte: str, options: dict[str, str]) -> dict:
    liste = "; ".join(f"{i}, {t}" for i, t in options.items())
    return {"model": MODELE, "store": False,
            "input": (f"Un agriculteur ivoirien répond à un assistant agricole sur WhatsApp, souvent par un message "
                      f"vocal transcrit avec des erreurs. Il a dit « {texte[:300]} ». Les options possibles, sous la "
                      f"forme identifiant, titre, sont {liste}. Rends l'identifiant de l'option qu'il choisit, ou "
                      f"{AUCUN} si sa phrase ne correspond à aucune."),
            "generation_config": {"seed": GRAINE, "thinking_level": "low"},
            "response_format": {"type": "text", "mime_type": "application/json", "schema": {
                "type": "object", "properties": {"option": {"type": "string", "enum": [*options, AUCUN]}},
                "required": ["option"]}}}


def par_le_modele(texte: str, options: dict[str, str], appel=None) -> str | None:
    import json
    try:
        sortie = json.loads(texte_de_sortie((appel or appeler)(requete(texte, options))) or "{}")
    except Exception as erreur:
        journal.warning("compréhension par le modèle indisponible, %s", type(erreur).__name__)
        return None
    option = sortie.get("option")
    return option if option in options else None


def requete_audio(audio: bytes, type_audio: str, options: dict[str, str]) -> dict:
    import base64
    liste = "; ".join(f"{i}, {t}" for i, t in options.items()) or "aucune option à cette étape"
    consigne = ("Un agriculteur ivoirien parle à un assistant agricole sur WhatsApp, en français, parfois avec des "
                "noms de lieux de Côte d'Ivoire comme Korhogo, Bouaké, le Poro ou le Gbêkê, et des cultures comme "
                "le coton, le maïs, le sorgho ou le niébé. Transcris fidèlement sa note vocale. Puis, si elle choisit "
                f"clairement l'une des options suivantes, sous la forme identifiant, titre, {liste}, rends son "
                f"identifiant. Si c'est une question libre ou si rien ne correspond, rends {AUCUN}.")
    return {"model": MODELE, "store": False,
            "input": [{"type": "user_input", "content": [
                {"type": "text", "text": consigne},
                {"type": "audio", "data": base64.b64encode(audio).decode("ascii"), "mime_type": type_audio}]}],
            "generation_config": {"seed": GRAINE, "thinking_level": "low"},
            "response_format": {"type": "text", "mime_type": "application/json", "schema": {
                "type": "object",
                "properties": {"transcription": {"type": "string"}, "option": {"type": "string", "enum": [*options, AUCUN]}},
                "required": ["transcription", "option"]}}}


def ecouter(audio: bytes, type_audio: str, options: dict[str, str], appel=None) -> tuple[str, str | None] | None:
    """Transcription d'une note vocale et option choisie, par Gemini qui écoute l'audio, ou None en cas d'échec.

    Gemini accepte l'OGG des notes vocales WhatsApp, page docs/audio de sa documentation,
    lue le 15 novembre 2026. La transcription séparée d'Aethex déformait les noms de lieux,
    Korhogo étant transcrit robot lors d'un essai du même jour.
    """
    import json
    try:
        sortie = json.loads(texte_de_sortie((appel or appeler)(requete_audio(audio, type_audio.split(";")[0].strip(), options)))
                            or "{}")
    except Exception as erreur:
        journal.warning("écoute par le modèle indisponible, %s", type(erreur).__name__)
        return None
    transcription = (sortie.get("transcription") or "").strip()
    option = sortie.get("option")
    return transcription, option if option in options else None


def comprendre(texte: str, options: dict[str, str], appel=None) -> str | None:
    """Identifiant de l'option choisie par une phrase libre, ou None."""
    return par_les_mots(texte, options) or par_le_modele(texte, options, appel)

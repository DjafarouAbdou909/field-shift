"""Diagnostic d'une photo de plante avec l'API Gemini de Google, à la manière du projet agri-bot.

Décision du responsable du 15 novembre 2026. Le modèle répond librement, pour toute
culture, en identifiant la plante, en donnant le diagnostic probable, en l'expliquant et
en recommandant un geste concret au champ, sans jamais nommer de produit, règle rétablie
par le responsable le même jour. Depuis une seconde décision du même jour, la réponse est une
explication suivie, en trois ou quatre petits paragraphes sans numéro ni titre, plus
complète sur les signes vus, la cause, le risque pour la récolte et les gestes à faire,
pour être claire à l'écrit comme à la voix. Une numérotation que le modèle produirait
malgré la consigne est retirée par sans_liste. La consigne reprend celle de agri-bot,
backend/nlp/prompts.py, DIAGNOSIS_PROMPT_TEMPLATE, et ses messages d'échec ceux de
backend/vision/disease_client.py, le vouvoiement et le conseiller ANADER remplaçant le
tutoiement et l'agent agricole, et l'interdiction des produits étant ajoutée. Le bot retire
en plus toute phrase qui nommerait un produit, par bot.langage.conversation.filtrer, et
l'avertissement final est toujours rétabli.

Modèle, adresse et réglages vérifiés le 14 novembre 2026 dans la documentation officielle,
https://aistudio.google.com/docs, vers laquelle renvoie https://ai.google.dev/gemini-api/docs.

- Modèle gemini-4-hydrogen, version stable, entrées texte et image, page
  docs/models/gemini-4-hydrogen.
- API Interactions en version v1, la version stable. Texte et image vont dans une étape
  user_input, l'image seule dans input étant refusée par l'API le 15 novembre 2026.
- store à faux. Sinon l'API conserve chaque interaction 55 jours au niveau payant.
- Niveau payant obligatoire. Au niveau gratuit, Google utilise les images envoyées pour
  améliorer ses produits et des personnes peuvent les relire. Conditions additionnelles
  de l'API Gemini en vigueur depuis le 23 mars 2026, page docs/terms.
- Formats JPEG, PNG, WebP, HEIC et HEIF, ceux de agri-bot, tous listés par la page
  docs/image-understanding. Image envoyée en ligne, encodée en base64, jamais écrite sur
  disque. Requête limitée à 20 Mo.
- Résolution high, environ 1 120 jetons par image, page docs/media-resolution.
"""

import base64
import logging
import os
import re
import time

import requests

from .contrat import AVERTISSEMENT_DIAGNOSTIC, Diagnostic

journal = logging.getLogger("moteur")

MODELE = "gemini-4-hydrogen"
MODELE_VERIFIE_LE = "2026-11-14"
ADRESSE = "https://generativelanguage.googleapis.com/v1/interactions"
ADRESSE_AGENT_PLATFORM = "https://aiplatform.googleapis.com/v1/projects/{projet}/locations/global/interactions"


def acces() -> tuple[str, str | None]:
    """Adresse et clé de Gemini. Agent Platform si sa clé et son projet sont donnés, AI Studio sinon.

    Agent Platform, anciennement Vertex AI, est payable avec le crédit d'essai de Google Cloud
    pour un essai ouvert avant le 16 novembre 2026, alors que l'API Gemini d'AI Studio ne
    l'est pas, page Google Cloud Free Program lue le 15 novembre 2026. Google n'y utilise
    pas les données pour entraîner ses modèles, page Zero data retention. L'API Interactions
    y est servie à l'adresse globale ci-dessus, page Interactions de la documentation
    d'Agent Platform.
    """
    projet, cle = os.environ.get("AGENT_PLATFORM_PROJET"), os.environ.get("AGENT_PLATFORM_API_KEY")
    if projet and cle:
        return ADRESSE_AGENT_PLATFORM.format(projet=projet), cle
    return ADRESSE, os.environ.get("GEMINI_API_KEY")
RESOLUTION = "high"
NIVEAU_DE_REFLEXION = "low"
GRAINE = 2026
TENTATIVES, PAUSE_SECONDES, ERREURS_PASSAGERES = 2, 1, {500, 502, 503, 504}
QUOTA_PAUSE_SECONDES = 15 * 60
_quota_epuise_jusqua = 0.0


class QuotaEpuise(RuntimeError):
    """Gemini a répondu 429. Les appels suivants échouent aussitôt pendant QUOTA_PAUSE_SECONDES."""
TAILLE_MIN_OCTETS = 100
TAILLE_MAX_OCTETS = 14 * 1024 * 1024  # base64 grossit de 4 tiers, la requête reste sous 20 Mo
TYPES_IMAGE = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
ORIGINE = (f"Photo envoyée par l'utilisateur, analysée par Google Gemini, modèle {MODELE}, sans conservation "
           "par Field Shift.")

CONSIGNE = """Tu es un assistant agricole qui aide un agriculteur ivoirien à comprendre ce qui arrive à sa plante. Tu n'es pas un laboratoire phytosanitaire certifié.

IMPORTANT : la conversation est déjà en cours. Ne commence JAMAIS par une salutation. Va directement à l'explication.

Regarde la photo et explique à l'agriculteur, en français simple et avec le vouvoiement, comme un technicien qui lui parle au bord du champ. Ta réponse peut être lue à voix haute. Écris donc des phrases complètes, en trois ou quatre petits paragraphes, sans aucun numéro, aucune liste, aucun titre, aucun astérisque et aucun tiret en début de ligne.

Commence par ce que montre la photo, la culture et la partie de la plante, et décris précisément les signes que tu vois, leur couleur, leur forme et leur place sur la plante. Base-toi uniquement sur ce que tu vois. Dis ensuite le problème le plus probable, maladie, ravageur, manque d'eau ou sol pauvre, et pourquoi tu le penses. Si tu hésites entre deux problèmes, nomme les deux et dis quel signe permet de les distinguer au champ. Explique ensuite d'où vient ce problème, ce qui le favorise, comme l'humidité ou la chaleur, et ce qu'il peut faire à la récolte si rien n'est fait. Termine par deux ou trois gestes concrets que l'agriculteur peut faire dès aujourd'hui, par exemple regarder les plants voisins et le dessous des feuilles, arracher et éloigner les plants très atteints, nettoyer ses outils, ne pas travailler les plants mouillés, et dis-lui quand montrer la plante au conseiller agricole.

Ne nomme JAMAIS de produit : aucun pesticide, insecticide, fongicide, herbicide, engrais, produit naturel à pulvériser, marque ni dose. Pour un traitement, dis de demander au conseiller agricole.

Tu n'es pas un agent de l'ANADER et tu ne parles jamais en son nom.

Reste entre 120 et 200 mots, sans compter la phrase finale.

Si la plante que tu vois NE correspond PAS à la culture déclarée par l'agriculteur ci-dessous, dis-le dès ta première phrase (ex : "Cette image montre du cacao, pas de la tomate comme vous l'aviez mentionné.").

Si l'image n'est pas une plante, ou si elle est trop floue pour juger, dis-le simplement, n'invente pas de diagnostic, et demande une photo nette prise de près à la lumière du jour.

Termine TOUJOURS par cette phrase, seule sur sa dernière ligne : "{avertissement}"

Culture déclarée par l'agriculteur : {culture}
"""

ILLISIBLE = "Je n'ai pas pu lire cette image. Réessayez de l'envoyer 📸"
FORMAT_REFUSE = "Ce format d'image n'est pas pris en charge. Envoyez une photo, en JPEG ou en PNG 📸"
A_REESSAYER = "Je n'ai pas pu analyser cette image. Essayez une photo plus nette, de près, sous bonne lumière 📸"


def consigne(culture: str | None) -> str:
    return CONSIGNE.format(avertissement=AVERTISSEMENT_DIAGNOSTIC, culture=culture or "non précisée")


def requete(image: bytes, type_image: str, culture: str | None) -> dict:
    """Corps de la requête à l'API Interactions."""
    return {"model": MODELE, "store": False,
            "input": [{"type": "user_input", "content": [
                {"type": "text", "text": consigne(culture)},
                {"type": "image", "data": base64.b64encode(image).decode("ascii"), "mime_type": type_image,
                 "resolution": RESOLUTION}]}],
            "generation_config": {"seed": GRAINE, "thinking_level": NIVEAU_DE_REFLEXION}}


def texte_de_sortie(interaction: dict) -> str | None:
    """Texte de la sortie du modèle, ou None si l'interaction n'est pas terminée."""
    if interaction.get("status") != "completed":
        return None
    textes = [c.get("text", "") for etape in interaction.get("steps", []) if etape.get("type") == "model_output"
              for c in etape.get("content", []) if c.get("type") == "text"]
    return "".join(textes) or None


DEBUT_DE_LISTE = re.compile(r"^\s*(?:\d+\s*[.)\-:]|[-•*]\s)\s*")
TITRE_EN_TETE = re.compile(r"^\s*\*{1,2}[^*\n]{1,40}\*{1,2}\s*:\s*")
ASTERISQUES = re.compile(r"\*{1,2}([^*\n]+)\*{1,2}")


def sans_liste(texte: str) -> str:
    """Retire numéros, puces, titres en gras et astérisques de début de ligne, pour un texte suivi."""
    lignes = [ASTERISQUES.sub(r"\1", TITRE_EN_TETE.sub("", DEBUT_DE_LISTE.sub("", ligne)))
              for ligne in texte.split("\n")]
    return "\n".join(lignes)


def avec_avertissement(texte: str) -> str:
    """Rétablit l'avertissement final, en remplaçant une dernière ligne d'avertissement reformulée."""
    lignes = texte.rstrip().split("\n")
    if lignes and lignes[-1].strip().startswith("⚠️"):
        lignes = lignes[:-1]
    return "\n".join(lignes).rstrip() + "\n\n" + AVERTISSEMENT_DIAGNOSTIC


def echec(message: str, culture: str | None) -> Diagnostic:
    return Diagnostic(donnees_fictives=False, culture_declaree=culture, statut="echec", texte=message,
                      origine_images=ORIGINE)


def interpreter(texte: str | None, culture: str | None) -> Diagnostic:
    if not texte or not texte.strip():
        return echec(A_REESSAYER, culture)
    return Diagnostic(donnees_fictives=False, culture_declaree=culture, statut="analyse",
                      texte=avec_avertissement(sans_liste(texte.strip())), origine_images=ORIGINE)


def appeler(corps: dict, session: requests.Session | None = None, cle: str | None = None) -> dict:
    """Envoie la requête et rend l'interaction. La clé vient de GEMINI_API_KEY, jamais du dépôt."""
    global _quota_epuise_jusqua
    adresse, cle_env = acces()
    cle = cle or cle_env
    if not cle:
        raise RuntimeError("clé GEMINI_API_KEY ou AGENT_PLATFORM_API_KEY absente de l'environnement")
    if time.monotonic() < _quota_epuise_jusqua:
        raise QuotaEpuise("quota Gemini épuisé, appel sauté")
    for tentative in range(TENTATIVES):
        reponse = (session or requests).post(adresse, json=corps, timeout=120,
                                             headers={"x-goog-api-key": cle, "Content-Type": "application/json"})
        if reponse.status_code not in ERREURS_PASSAGERES or tentative == TENTATIVES - 1:
            break
        journal.warning("Gemini indisponible, code %s, nouvel essai", reponse.status_code)
        time.sleep(PAUSE_SECONDES)
    if reponse.status_code == 429:
        _quota_epuise_jusqua = time.monotonic() + QUOTA_PAUSE_SECONDES
        journal.warning("quota Gemini épuisé, Gemini mis en pause %s minutes", QUOTA_PAUSE_SECONDES // 60)
        raise QuotaEpuise("quota Gemini épuisé")
    if reponse.status_code >= 400:
        journal.warning("Gemini a refusé la requête, code %s", reponse.status_code)
    reponse.raise_for_status()
    return reponse.json()


def type_de_base(type_image: str | None) -> str:
    return (type_image or "image/jpeg").split(";")[0].strip().lower()


def diagnostiquer(image: bytes, type_image: str | None, culture: str | None = None,
                  session: requests.Session | None = None, cle: str | None = None) -> Diagnostic:
    """Diagnostic d'une photo de plante. L'image reste en mémoire et n'est jamais écrite."""
    if not image or len(image) < TAILLE_MIN_OCTETS or len(image) > TAILLE_MAX_OCTETS or image.lstrip()[:1] == b"{":
        journal.warning("contenu d'image suspect, %s octets", len(image or b""))
        return echec(ILLISIBLE, culture)
    type_image = type_de_base(type_image)
    if type_image not in TYPES_IMAGE:
        return echec(FORMAT_REFUSE, culture)
    try:
        interaction = appeler(requete(image, type_image, culture), session, cle)
    except Exception as erreur:
        journal.error("échec du diagnostic, %s", type(erreur).__name__)
        return echec(A_REESSAYER, culture)
    return interpreter(texte_de_sortie(interaction), culture)

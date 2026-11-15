"""Diagnostic d'une photo de plante avec l'API Gemini de Google, à la manière du projet agri-bot.

Décision du responsable du 15 novembre 2026. Le modèle répond librement, pour toute
culture, en identifiant la plante, en donnant le diagnostic probable, en l'expliquant et
en recommandant un geste concret au champ, sans jamais nommer de produit, règle rétablie
par le responsable le même jour. La consigne reprend celle de agri-bot,
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
import time

import requests

from .contrat import AVERTISSEMENT_DIAGNOSTIC, Diagnostic

journal = logging.getLogger("moteur")

MODELE = "gemini-4-hydrogen"
MODELE_VERIFIE_LE = "2026-11-14"
ADRESSE = "https://generativelanguage.googleapis.com/v1/interactions"
RESOLUTION = "high"
NIVEAU_DE_REFLEXION = "low"
GRAINE = 2026
TENTATIVES, PAUSE_SECONDES, ERREURS_PASSAGERES = 2, 2, {429, 500, 502, 503, 504}
TAILLE_MIN_OCTETS = 100
TAILLE_MAX_OCTETS = 14 * 1024 * 1024  # base64 grossit de 4 tiers, la requête reste sous 20 Mo
TYPES_IMAGE = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
ORIGINE = (f"Photo envoyée par l'utilisateur, analysée par Google Gemini, modèle {MODELE}, sans conservation "
           "par Field Shift.")

CONSIGNE = """Tu es un assistant agricole qui aide à orienter un agriculteur, pas un laboratoire phytosanitaire certifié.

IMPORTANT : la conversation est déjà en cours avec cet agriculteur. Ne commence JAMAIS ta réponse par une salutation ("Salut", "Bonjour", "Salut l'ami agriculteur", etc.). Va directement au diagnostic.

Analyse cette image de plante et réponds en français simple, format WhatsApp (court) :

1. *Plante identifiée* : identifie ce que montre réellement l'image (fruit, feuille, tige de quelle culture ?). Base-toi UNIQUEMENT sur ce que tu vois, pas sur la culture déclarée par l'agriculteur ci-dessous.
2. *Diagnostic probable* : la maladie ou le problème le plus probable visible. En cas de doute entre 2 possibilités proches, mentionne les deux brièvement.
3. *Explication simple* : 1-2 phrases sur la cause probable.
4. *Recommandation concrète* : geste immédiat à faire au champ, comme observer le dessous des feuilles, arracher et éloigner les plants très atteints, ou montrer la plante au conseiller agricole. Ne nomme JAMAIS de produit : aucun pesticide, insecticide, fongicide, engrais, produit naturel à pulvériser, marque ni dose. Pour un traitement, dis de demander au conseiller agricole.

Tu n'es pas un agent de l'ANADER et tu ne parles jamais en son nom.

Si la plante identifiée à l'étape 1 NE correspond PAS à la culture déclarée par l'agriculteur ci-dessous, dis-le clairement dès le début de ta réponse (ex : "Cette image montre du cacao, pas de la tomate comme vous l'aviez mentionné.").

Si l'image n'est pas une plante, dis-le clairement et n'invente pas de diagnostic.

Termine TOUJOURS par : "{avertissement}"

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
                      texte=avec_avertissement(texte.strip()), origine_images=ORIGINE)


def appeler(corps: dict, session: requests.Session | None = None, cle: str | None = None) -> dict:
    """Envoie la requête et rend l'interaction. La clé vient de GEMINI_API_KEY, jamais du dépôt."""
    cle = cle or os.environ.get("GEMINI_API_KEY")
    if not cle:
        raise RuntimeError("clé GEMINI_API_KEY absente de l'environnement")
    for tentative in range(TENTATIVES):
        reponse = (session or requests).post(ADRESSE, json=corps, timeout=120,
                                             headers={"x-goog-api-key": cle, "Content-Type": "application/json"})
        if reponse.status_code not in ERREURS_PASSAGERES or tentative == TENTATIVES - 1:
            break
        journal.warning("Gemini indisponible, code %s, nouvel essai", reponse.status_code)
        time.sleep(PAUSE_SECONDES)
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

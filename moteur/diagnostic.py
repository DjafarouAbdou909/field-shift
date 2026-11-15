"""Diagnostic par photo d'une feuille avec l'API Gemini de Google, décision du 14 novembre 2026.

Modèle, adresse et réglages vérifiés le 14 novembre 2026 dans la documentation officielle,
https://aistudio.google.com/docs, vers laquelle renvoie https://ai.google.dev/gemini-api/docs.

- Modèle gemini-4-hydrogen, version stable, entrées texte et image, sorties structurées,
  page docs/models/gemini-4-hydrogen. La page docs/models définit une version stable
  comme un modèle précis qui ne change habituellement pas, contrairement aux alias latest.
- API Interactions en version v1, la version stable, page api-reference/api-versions.
- store à faux. Sinon l'API conserve chaque interaction 55 jours au niveau payant, page
  docs/interactions-overview, section Data storage and retention.
- Niveau payant obligatoire, avec un projet Cloud lié à un compte de facturation actif. Au
  niveau gratuit, Google utilise les images envoyées pour améliorer ses produits et des
  personnes peuvent les relire. Au niveau payant, il ne les utilise pas à cette fin et les
  journalise pour une durée limitée, pour la seule détection des abus. Conditions
  additionnelles de l'API Gemini, en vigueur depuis le 23 mars 2026, page docs/terms.
- Image envoyée en ligne, encodée en base64, jamais écrite sur disque par ce module. La
  requête est limitée à 20 Mo, page docs/image-understanding. En v1, texte et image vont
  dans une étape user_input, l'image seule dans input étant refusée par l'API le 15 novembre
  2026 avec le message que ce type n'existe qu'en v1beta.
- Résolution high, environ 1 120 jetons par image, réglage recommandé pour les images par
  la page docs/media-resolution.

La réponse est imposée par un schéma JSON à deux champs, reponse, prise dans une
énumération de la liste fermée de la culture, de aucune_maladie_reconnue et de inconnu, et
confiance, de 0 à 1. Tout ce qui sort de la liste, et toute réponse illisible, devient
inconnu. Le modèle ne rend aucun texte libre, si bien qu'aucun traitement ni produit ne
peut apparaître. La confiance est celle que déclare le modèle, sans calibration.
"""

import base64
import json
import os

import requests

from .contrat import MESSAGES_DIAGNOSTIC, Diagnostic
from .maladies import MALADIES, liste, source_maladie

MODELE = "gemini-4-hydrogen"
MODELE_VERIFIE_LE = "2026-11-14"
ADRESSE = "https://generativelanguage.googleapis.com/v1/interactions"
RESOLUTION = "high"
NIVEAU_DE_REFLEXION = "low"
GRAINE = 2026
TAILLE_MAX_OCTETS = 14 * 1024 * 1024  # base64 grossit de 4 tiers, la requête reste sous 20 Mo
TYPES_IMAGE = {"image/jpeg", "image/png"}
CULTURES = sorted({maladie["culture"] for maladie in MALADIES.values()})
AUCUNE, INCONNU = "aucune_maladie_reconnue", "inconnu"
ORIGINE = (f"Photo envoyée par l'utilisateur, analysée par Google Gemini, modèle {MODELE}, sans conservation "
           "par Field Shift.")


def reponses_permises(culture: str) -> list[str]:
    return liste(culture) + [AUCUNE, INCONNU]


def schema(culture: str) -> dict:
    """Schéma JSON imposé à la réponse du modèle."""
    return {"type": "object",
            "properties": {"reponse": {"type": "string", "enum": reponses_permises(culture)},
                           "confiance": {"type": "number", "minimum": 0, "maximum": 1}},
            "required": ["reponse", "confiance"]}


def consigne(culture: str) -> str:
    """Consigne envoyée avec la photo, sans description de symptôme non sourcée."""
    maladies = "; ".join(f"{nom}, agent {MALADIES[nom]['agent']}" for nom in liste(culture))
    return (f"Tu examines la photo d'une feuille de {culture} prise au champ en Côte d'Ivoire. Réponds par une seule "
            f"valeur de la liste permise. Les maladies que tu peux nommer sont {maladies}. Si la feuille montre "
            f"clairement l'une d'elles, réponds son nom. Si la feuille ne montre aucun signe de maladie, réponds "
            f"{AUCUNE}. Si la photo n'est pas une feuille de {culture}, si elle est floue, trop sombre ou montre "
            f"plusieurs plantes sans détail, si la feuille montre une autre maladie, un ravageur ou un dégât, ou si "
            f"tu hésites, réponds {INCONNU}. Donne ta confiance de 0 à 1 dans cette réponse.")


def requete(image: bytes, type_image: str, culture: str) -> dict:
    """Corps de la requête à l'API Interactions."""
    if culture not in CULTURES:
        raise ValueError(f"culture hors de la liste, {culture}")
    if type_image not in TYPES_IMAGE:
        raise ValueError(f"type d'image non pris en charge, {type_image}")
    if len(image) > TAILLE_MAX_OCTETS:
        raise ValueError("image trop lourde pour une requête en ligne")
    return {"model": MODELE, "store": False,
            "input": [{"type": "user_input", "content": [
                {"type": "text", "text": consigne(culture)},
                {"type": "image", "data": base64.b64encode(image).decode("ascii"), "mime_type": type_image,
                 "resolution": RESOLUTION}]}],
            "generation_config": {"seed": GRAINE, "thinking_level": NIVEAU_DE_REFLEXION},
            "response_format": {"type": "text", "mime_type": "application/json", "schema": schema(culture)}}


def texte_de_sortie(interaction: dict) -> str | None:
    """Texte de la sortie du modèle, ou None si l'interaction n'est pas terminée."""
    if interaction.get("status") != "completed":
        return None
    textes = [c.get("text", "") for etape in interaction.get("steps", []) if etape.get("type") == "model_output"
              for c in etape.get("content", []) if c.get("type") == "text"]
    return "".join(textes) or None


def interpreter(texte: str | None, culture: str) -> Diagnostic:
    """Diagnostic du contrat à partir du texte JSON rendu par le modèle. Tout écart devient inconnu."""
    try:
        sortie = json.loads(texte)
        reponse, confiance = sortie["reponse"], float(sortie["confiance"])
        if not 0 <= confiance <= 1:
            raise ValueError
    except (TypeError, ValueError, KeyError):
        reponse, confiance = INCONNU, 0.0
    if reponse not in reponses_permises(culture):
        reponse, confiance = INCONNU, 0.0
    malade = reponse not in (AUCUNE, INCONNU)
    statut = "maladie_possible" if malade else reponse
    return Diagnostic(donnees_fictives=False, culture=culture, statut=statut, maladie=reponse if malade else None,
                      confiance=confiance, liste=liste(culture),
                      source_maladie=source_maladie(reponse) if malade else None, origine_images=ORIGINE,
                      avertissement=MESSAGES_DIAGNOSTIC[statut])


def appeler(corps: dict, session: requests.Session | None = None, cle: str | None = None) -> dict:
    """Envoie la requête et rend l'interaction. La clé vient de GEMINI_API_KEY, jamais du dépôt."""
    cle = cle or os.environ.get("GEMINI_API_KEY")
    if not cle:
        raise RuntimeError("clé GEMINI_API_KEY absente de l'environnement")
    reponse = (session or requests).post(ADRESSE, json=corps, timeout=120,
                                         headers={"x-goog-api-key": cle, "Content-Type": "application/json"})
    reponse.raise_for_status()
    return reponse.json()


def diagnostiquer(image: bytes, type_image: str, culture: str, session: requests.Session | None = None,
                  cle: str | None = None) -> Diagnostic:
    """Diagnostic d'une photo de feuille. L'image reste en mémoire et n'est jamais écrite."""
    return interpreter(texte_de_sortie(appeler(requete(image, type_image, culture), session, cle)), culture)

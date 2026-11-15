"""Réponses en langage libre aux questions écrites de l'agriculteur.

Le modèle reçoit la question et la recommandation en JSON, avec la consigne de ne rien
affirmer qui n'y figure pas. Sa réponse passe toujours par garde_fou.texte_sur, avec un
gabarit comme secours, si bien qu'un chiffre, une culture, une maladie, un traitement ou
un produit absent du moteur fait envoyer le gabarit à la place.

Fournisseur. Même modèle et même API que le diagnostic, Google Gemini gemini-4-hydrogen
par l'API Interactions v1, avec store à faux, figés dans moteur/diagnostic.py, décision du
responsable du 15 novembre 2026. La clé GEMINI_API_KEY doit appartenir à un projet au
niveau payant, où Google n'utilise pas les contenus pour améliorer ses produits.
"""

import logging

from bot.langage.garde_fou import texte_sur
from moteur.contrat import Recommandation
from moteur.diagnostic import GRAINE, MODELE, appeler, texte_de_sortie

journal = logging.getLogger("bot")
QUESTION_MAX = 500
CONSIGNE = (
    "Tu es Field Shift, un assistant pour des agriculteurs du nord et du centre de la Côte d'Ivoire. Réponds en "
    "français simple, en trois phrases au plus, à la question de l'agriculteur, en t'appuyant uniquement sur la "
    "recommandation JSON fournie. N'ajoute aucun chiffre, aucune culture, aucune maladie, aucun traitement, "
    "aucun produit ni aucun prix qui n'y figure pas. Ne prédis aucun rendement. Si la recommandation ne permet "
    "pas de répondre, dis-le et conseille de demander au conseiller ANADER."
)


def requete(question: str, reco: Recommandation) -> dict:
    return {"model": MODELE, "store": False, "system_instruction": CONSIGNE,
            "input": f"Recommandation JSON\n{reco.model_dump_json()}\n\nQuestion de l'agriculteur\n"
                     f"{question[:QUESTION_MAX]}",
            "generation_config": {"seed": GRAINE, "thinking_level": "low"}}


def repondre(question: str, reco: Recommandation, secours: str, appel=None) -> str:
    """Réponse du modèle si elle est fidèle à la recommandation, sinon le texte de secours."""
    try:
        texte = texte_de_sortie((appel or appeler)(requete(question, reco)))
    except Exception as erreur:  # le secours vaut mieux qu'un silence
        journal.warning("reformulation indisponible, %s", type(erreur).__name__)
        texte = None
    return texte_sur(texte, reco, secours)

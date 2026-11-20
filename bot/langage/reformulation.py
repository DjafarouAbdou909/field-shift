"""Réponses en langage libre aux questions écrites de l'agriculteur.

Le modèle reçoit la question et la recommandation en JSON, avec la consigne de ne rien
affirmer qui n'y figure pas. Sa réponse passe toujours par garde_fou.texte_sur, avec un
gabarit comme secours, si bien qu'un chiffre, une culture, une maladie, un traitement ou
un produit absent du moteur fait envoyer le gabarit à la place.

Fournisseur. Groq, modèle openai/gpt-oss-120b, par bot.langage.groq, décision du
responsable du 15 novembre 2026, Gemini ne gardant que l'analyse des photos.
"""

import logging

from bot.langage.garde_fou import texte_sur
from moteur.contrat import Recommandation

journal = logging.getLogger("bot")
QUESTION_MAX = 500
CONSIGNE = (
    "Tu es AgriBot, un assistant pour des agriculteurs du nord et du centre de la Côte d'Ivoire. Réponds en "
    "français simple et chaleureux, comme une personne qui parle au bord du champ, en reprenant les mots de "
    "l'agriculteur, en trois phrases au plus, à la question de l'agriculteur, en t'appuyant uniquement sur la "
    "recommandation JSON fournie. N'ajoute aucun chiffre, aucune culture, aucune maladie, aucun traitement, "
    "aucun produit ni aucun prix qui n'y figure pas. Vouvoie l'agriculteur. Ne prédis aucun rendement. Si la recommandation ne permet "
    "pas de répondre, dis-le et conseille de demander au conseiller ANADER."
)


def message(question: str, reco: Recommandation) -> str:
    return f"Recommandation JSON\n{reco.model_dump_json()}\n\nQuestion de l'agriculteur\n{question[:QUESTION_MAX]}"


def repondre(question: str, reco: Recommandation, secours: str, generation=None) -> str:
    """Réponse du modèle si elle est fidèle à la recommandation, sinon le texte de secours."""
    from . import groq

    texte = groq.reformuler(CONSIGNE, message(question, reco), generation) if groq.configure() else None
    return texte_sur(texte, reco, secours)

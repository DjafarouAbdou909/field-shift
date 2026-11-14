"""Réponses en langage libre, à écrire par le membre B.

Le modèle de langage reçoit la question de l'agriculteur et la recommandation en JSON,
avec la consigne de ne rien affirmer qui n'y figure pas. Sa réponse passe toujours par
garde_fou.texte_sur, avec un gabarit comme secours. Le fournisseur et le nom exact du
modèle sont consignés dans docs/decisions.md.
"""

from moteur.contrat import Recommandation


def repondre(question: str, reco: Recommandation) -> str:
    raise NotImplementedError

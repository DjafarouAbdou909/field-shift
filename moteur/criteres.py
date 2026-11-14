"""Scores eau, revenu et sol, pondérations et analyse de sensibilité.

Les poids par priorité sont un choix de conception de l'équipe, pas un résultat. Ils
sont affichés dans l'application et réglables par l'utilisateur.
"""

from .contrat import Poids

POIDS_PAR_PRIORITE = {
    "eau": Poids(eau=0.6, revenu=0.2, sol=0.2),
    "revenu": Poids(eau=0.2, revenu=0.6, sol=0.2),
    "sol": Poids(eau=0.2, revenu=0.2, sol=0.6),
}

"""Messages déterministes construits à partir d'une recommandation, à enrichir par le membre B.

Ce sont les messages envoyés par défaut. Ils restent courts, en français simple, et se
terminent toujours par l'avertissement du moteur.
"""

from moteur.contrat import Recommandation


def nombre(valeur: float) -> str:
    """Écrit un nombre à la française, sans séparateur de milliers."""
    return f"{valeur:g}".replace(".", ",")


def resume(reco: Recommandation) -> str:
    """Résumé des stratégies dans l'ordre du classement, avec l'indicateur principal."""
    strategies = {s.id: s for s in reco.strategies}
    lignes = []
    if reco.donnees_fictives:
        lignes.append("[TEST, données fictives]")
    lignes.append(f"Pour {reco.lieu.nom}, voici {len(reco.strategies)} rotations comparées.")
    indicateur = reco.indicateurs[0]
    lignes.append(
        f"Données NASA. {indicateur.texte}, {nombre(indicateur.valeur)} {indicateur.unite}, "
        f"entre {nombre(indicateur.bas)} et {nombre(indicateur.haut)} selon les années."
    )
    for rang, identifiant in enumerate(reco.classement, start=1):
        strategie = strategies[identifiant]
        actuelle = ", votre rotation actuelle" if strategie.actuelle else ""
        lignes.append(f"{rang}. {strategie.nom}{actuelle}. {strategie.pourquoi[0].texte}")
    if not reco.classement_stable:
        lignes.append("Attention, ce classement change si la saison est plus sèche.")
    lignes.append(reco.avertissement)
    return "\n".join(lignes)

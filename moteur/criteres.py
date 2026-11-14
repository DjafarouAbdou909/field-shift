"""Scores eau, revenu et sol, pondérations et analyse de sensibilité.

Les poids par priorité sont un choix de conception de l'équipe, pas un résultat. Ils
sont affichés dans l'application et réglables par l'utilisateur.

Chaque critère est une liste d'indicateurs. Un indicateur est une fonction qui reçoit
une stratégie et le contexte d'un lieu, et retourne une Evaluation, ou None si les
données qu'il demande manquent encore. Le score d'un critère est la moyenne des scores
de ses indicateurs disponibles. Un indicateur tiré de SMAP ou de MODIS s'ajoute en
écrivant sa fonction et en l'inscrivant dans INDICATEURS, sans toucher au reste, et ses
données passent par le champ surfaces du Contexte.

Règles de départ, toutes à valider par l'équipe.
    eau, couverture du besoin, part des années où la pluie du cycle couvre le besoin en
        eau de la culture, moyenne sur les cultures de la rotation, score 5 fois cette
        part, niveau calcule
    eau, besoin en eau, besoin moyen par saison des cultures de la rotation, placé entre
        la culture comparée la plus économe, score 5, et la plus exigeante, score 0, au
        même lieu et dans le même scénario, niveau calcule
    sol, part de légumineuses, part des années de la rotation en légumineuse, score 5
        fois cette part, niveau hypothese, appuyée sur YUSUF2009 et CATTAN2001
    revenu, part de culture de rente, part des années en coton, seule culture comparée
        à débouché organisé selon GUENOT2014, score 5 fois cette part, niveau hypothese.
        C'est un indicateur qualitatif de l'accès au marché, pas un revenu, faute de
        prix sourcés pour chaque culture.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .contrat import Poids

POIDS_PAR_PRIORITE = {
    "eau": Poids(eau=0.6, revenu=0.2, sol=0.2),
    "revenu": Poids(eau=0.2, revenu=0.6, sol=0.2),
    "sol": Poids(eau=0.2, revenu=0.2, sol=0.6),
}
CRITERES = ("eau", "revenu", "sol")
LEGUMINEUSES = {"niébé", "arachide", "soja"}
CULTURES_DE_RENTE = {"coton"}
SCENARIOS = {"reference": {"facteur_pluie": 1.0, "retard_jours": 0},
             "pluie_moins_20_pourcent": {"facteur_pluie": 0.8, "retard_jours": 0},
             "debut_retarde_de_14_jours": {"facteur_pluie": 1.0, "retard_jours": 14}}


@dataclass(frozen=True)
class Evaluation:
    critere: str
    indicateur: str
    texte: str
    valeur: float
    unite: str
    score: float
    niveau: str
    source: str
    bas: float | None = None
    haut: float | None = None


@dataclass(frozen=True)
class Contexte:
    lieu: str
    scenario: str
    cycles: pd.DataFrame
    surfaces: dict = field(default_factory=dict)


def couverture_du_besoin(strategie, contexte: Contexte) -> Evaluation | None:
    parts = {}
    for culture in strategie.cultures:
        ecarts = contexte.cycles.loc[contexte.cycles["culture"] == culture, "pluie_moins_etc_mm"].dropna()
        if ecarts.empty:
            return None
        parts[culture] = float((ecarts >= 0).mean())
    part = float(np.mean(list(parts.values())))
    return Evaluation("eau", "couverture_du_besoin",
                      f"La pluie du cycle couvre le besoin en eau {part:.0%} des années, en moyenne sur les cultures "
                      "de la rotation.", part, "part des années", 5 * part, "calcule",
                      "FAO56_T11_T12, IMERG, POWER", min(parts.values()), max(parts.values()))


def besoin_en_eau(strategie, contexte: Contexte) -> Evaluation | None:
    besoins = contexte.cycles.groupby("culture")["etc_cycle_mm"].median()
    if not set(strategie.cultures) <= set(besoins.index):
        return None
    besoin = float(besoins[list(strategie.cultures)].mean())
    plus_econome, plus_exigeante = float(besoins.min()), float(besoins.max())
    score = 5 * (plus_exigeante - besoin) / (plus_exigeante - plus_econome)
    return Evaluation("eau", "besoin_en_eau",
                      f"Les cultures de la rotation demandent {besoin:.0f} mm d'eau par saison en médiane, entre "
                      f"{plus_econome:.0f} mm pour la culture comparée la plus économe et {plus_exigeante:.0f} mm "
                      "pour la plus exigeante.", besoin, "mm par saison", score, "calcule", "FAO56_T11_T12, POWER",
                      float(besoins[list(strategie.cultures)].min()), float(besoins[list(strategie.cultures)].max()))


def part_de_legumineuses(strategie, contexte: Contexte) -> Evaluation:
    part = sum(c in LEGUMINEUSES for c in strategie.cultures) / len(strategie.cultures)
    return Evaluation("sol", "part_de_legumineuses",
                      f"Une légumineuse occupe {part:.0%} des années de la rotation.", part, "part des années",
                      5 * part, "hypothese", "YUSUF2009, CATTAN2001")


def part_de_culture_de_rente(strategie, contexte: Contexte) -> Evaluation:
    part = sum(c in CULTURES_DE_RENTE for c in strategie.cultures) / len(strategie.cultures)
    return Evaluation("revenu", "part_de_culture_de_rente",
                      f"Le coton, culture à débouché organisé, occupe {part:.0%} des années de la rotation. Le revenu "
                      "n'est pas chiffré, faute de prix sourcés pour chaque culture.", part, "part des années",
                      5 * part, "hypothese", "GUENOT2014")


INDICATEURS: dict[str, list[Callable]] = {
    "eau": [couverture_du_besoin, besoin_en_eau],
    "revenu": [part_de_culture_de_rente],
    "sol": [part_de_legumineuses],
}


def evaluer(strategie, contexte: Contexte) -> list[Evaluation]:
    """Évalue une stratégie par tous les indicateurs dont les données sont disponibles."""
    evaluations = []
    for critere in CRITERES:
        for indicateur in INDICATEURS[critere]:
            evaluation = indicateur(strategie, contexte)
            if evaluation is not None:
                evaluations.append(evaluation)
    return evaluations


def scores_criteres(evaluations: list[Evaluation]) -> dict[str, float]:
    """Score de chaque critère, moyenne des scores de ses indicateurs disponibles."""
    return {critere: float(np.mean([e.score for e in evaluations if e.critere == critere])) for critere in CRITERES}


def note(scores: dict[str, float], poids: Poids) -> float:
    return sum(getattr(poids, critere) * scores[critere] for critere in CRITERES)


def tableau_scores(strategies, contexte: Contexte, poids: Poids) -> pd.DataFrame:
    """Scores par critère, note pondérée et rang de chaque stratégie, le rang 1 étant la meilleure note."""
    lignes = {s.id: {**scores_criteres(evaluer(s, contexte)), "actuelle": s.actuelle} for s in strategies}
    table = pd.DataFrame.from_dict(lignes, orient="index")
    table["note"] = [note(table.loc[i, list(CRITERES)].to_dict(), poids) for i in table.index]
    table["rang"] = table["note"].rank(ascending=False, method="min").astype(int)
    return table.sort_values("rang")


def sensibilite(strategies, contextes: dict[str, Contexte], poids: Poids) -> tuple[pd.DataFrame, bool, list[str]]:
    """Rang de chaque stratégie dans chaque scénario, stabilité du classement et scénarios qui le changent."""
    rangs = pd.DataFrame({nom: tableau_scores(strategies, contexte, poids)["rang"] for nom, contexte in contextes.items()})
    changeants = [nom for nom in rangs.columns if not rangs[nom].equals(rangs["reference"])]
    return rangs.sort_values("reference"), not changeants, changeants


def contextes_du_lieu(identifiant: str) -> dict[str, Contexte]:
    """Contexte de chaque scénario de sensibilité, pluie réduite ou début de saison retardé."""
    from .cultures import courbes_kc_comparees
    from .donnees import altitude_power, lire_power, pluie_lieu, telecharger_point, voisinage_imerg
    from .indicateurs import evapotranspiration_serie, indicateurs_annuels, indicateurs_cultures
    from .lieux import LIEUX

    lieu = LIEUX[identifiant]
    chemin_power = telecharger_point(lieu["lat"], lieu["lon"], "power")
    meteo, altitude = lire_power(chemin_power), altitude_power(chemin_power)
    et0 = evapotranspiration_serie(meteo, lieu["lat"], altitude)
    pluie_reference = pluie_lieu(voisinage_imerg(lieu["lat"], lieu["lon"]))["moyenne"]
    courbes = courbes_kc_comparees()
    contextes = {}
    for nom, scenario in SCENARIOS.items():
        pluie = pluie_reference * scenario["facteur_pluie"]
        debuts = indicateurs_annuels(pluie, meteo, lieu["lat"], altitude)["debut_jour"] + scenario["retard_jours"]
        contextes[nom] = Contexte(identifiant, nom, indicateurs_cultures(pluie, meteo, et0, debuts, courbes))
    return contextes


def tableau_evaluations(strategies, contexte: Contexte) -> pd.DataFrame:
    """Valeur, plage, score, niveau et source de chaque indicateur de chaque stratégie."""
    return pd.DataFrame([{"strategie": s.id, "critere": e.critere, "indicateur": e.indicateur, "valeur": e.valeur,
                          "bas": e.bas, "haut": e.haut, "unite": e.unite, "score": e.score, "niveau": e.niveau,
                          "source": e.source} for s in strategies for e in evaluer(s, contexte)])



def tableau_scenarios(strategies, contextes: dict[str, Contexte]) -> pd.DataFrame:
    """Valeur de chaque indicateur de chaque stratégie dans chaque scénario."""
    return pd.concat({nom: tableau_evaluations(strategies, contexte).set_index(["strategie", "indicateur"])["valeur"]
                      for nom, contexte in contextes.items()}, axis=1)


def executer() -> None:
    from .lieux import LIEUX
    from .rotations import STRATEGIES

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    for identifiant, lieu in LIEUX.items():
        contextes = contextes_du_lieu(identifiant)
        print(f"\n===== {lieu['nom']}")
        print(tableau_evaluations(STRATEGIES, contextes["reference"]).round(3).to_string(index=False))
        for priorite, poids in POIDS_PAR_PRIORITE.items():
            print(f"\nPriorité {priorite}, {poids}")
            print(tableau_scores(STRATEGIES, contextes["reference"], poids).round(3).to_string())
            rangs, stable, changeants = sensibilite(STRATEGIES, contextes, poids)
            print(rangs.to_string())
            print(f"classement stable {stable}, scénarios qui le changent {changeants}")


if __name__ == "__main__":
    executer()

"""Scores eau, revenu et sol, pondérations et analyse de sensibilité.

Les poids par priorité sont un choix de conception de l'équipe, pas un résultat. Ils
sont affichés dans l'application et réglables par l'utilisateur.

Chaque critère est une liste d'indicateurs. Un indicateur est une fonction qui reçoit
une stratégie et le contexte d'un lieu, et retourne une Evaluation, ou None si les
données qu'il demande manquent encore. Le score d'un critère est la moyenne des scores
de ses indicateurs disponibles. Un indicateur tiré de SMAP ou de MODIS s'ajoute en
écrivant sa fonction et en l'inscrivant dans INDICATEURS, sans toucher au reste, et ses
données passent par le champ surfaces du Contexte.

Règles validées comme approximations par le responsable le 14 novembre 2026, nommées par
ce qu'elles mesurent. Les clés eau, revenu et sol du contrat restent inchangées.
    eau, couverture du besoin, pour chaque culture et chaque année, la pluie IMERG du
        cycle couvre-t-elle son besoin en eau, coefficient cultural FAO-56 fois
        évapotranspiration de référence depuis le début des pluies. La part des années
        couvertes, moyenne sur les cultures de la rotation, donne le score, 5 fois cette
        part, et le rééchantillonnage des années son intervalle à 90 %. Niveau calcule.
    eau, séquences sèches à la mi-saison, part des années sans séquence sèche de plus de
        7 jours pendant le stade de mi-saison, le plus sensible au manque d'eau selon les
        chapitres 5 et 8 de FAO-56. Le seuil de 7 jours est celui du début de saison.
        Score 5 fois cette part, intervalle par rééchantillonnage, niveau calcule.
    revenu, libellé accès à un débouché organisé, part des années en coton, principale
        ressource économique des zones de savane selon ZAGBAI2006, page 325, score 5 fois
        cette part, niveau hypothese. Cet indicateur pénalise mécaniquement toute rotation
        qui réduit le coton, et ne mesure pas un revenu, faute de prix sourcés.
    sol, libellé apport d'azote par les légumineuses, part des années de la rotation en
        légumineuse, score 5 fois cette part, niveau hypothese, appuyée sur YUSUF2009.
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
# Le coton est semé dans la fenêtre observée par le CNRA, GNAPI2025, sauf dans le scénario
# où il est semé au début des pluies, décision du responsable du 14 novembre 2026.
SCENARIOS = {"reference": {"facteur_pluie": 1.0, "retard_jours": 0, "semis_coton": "fenetre"},
             "pluie_moins_20_pourcent": {"facteur_pluie": 0.8, "retard_jours": 0, "semis_coton": "fenetre"},
             "debut_retarde_de_14_jours": {"facteur_pluie": 1.0, "retard_jours": 14, "semis_coton": "fenetre"},
             "coton_seme_au_debut_des_pluies": {"facteur_pluie": 1.0, "retard_jours": 0,
                                                "semis_coton": "debut_des_pluies"}}


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


SEQUENCE_SECHE_ADMISE = 7
TIRAGES, GRAINE = 2000, 2026


def intervalle_annees(valeurs: pd.Series, tirages: int = TIRAGES, graine: int = GRAINE) -> tuple[float, float]:
    """Intervalle à 90 % de la moyenne d'une valeur annuelle, par rééchantillonnage des années avec remise."""
    generateur = np.random.default_rng(graine)
    tableau = valeurs.to_numpy(dtype=float)
    moyennes = generateur.choice(tableau, size=(tirages, len(tableau)), replace=True).mean(axis=1)
    return float(np.quantile(moyennes, 0.05)), float(np.quantile(moyennes, 0.95))


def part_annuelle(strategie, contexte: Contexte, condition: Callable[[pd.DataFrame], pd.Series]) -> pd.Series | None:
    """Pour chaque année où toutes les cultures ont un cycle, part des cultures de la rotation qui remplissent la condition."""
    lignes = contexte.cycles[contexte.cycles["culture"].isin(strategie.cultures)].dropna(subset=["pluie_moins_etc_mm"])
    if not set(strategie.cultures) <= set(lignes["culture"]):
        return None
    remplie = condition(lignes).astype(float).groupby(lignes["annee"]).agg(["mean", "size"])
    return remplie.loc[remplie["size"] == len(set(strategie.cultures)), "mean"]


def couverture_du_besoin(strategie, contexte: Contexte) -> Evaluation | None:
    parts = part_annuelle(strategie, contexte, lambda l: l["pluie_moins_etc_mm"] >= 0)
    if parts is None:
        return None
    part, (bas, haut) = float(parts.mean()), intervalle_annees(parts)
    return Evaluation("eau", "couverture_du_besoin",
                      f"La pluie du cycle couvre le besoin en eau des cultures {part:.0%} des années, de {bas:.0%} à "
                      f"{haut:.0%} selon le rééchantillonnage des années.", part, "part des années", 5 * part,
                      "calcule", "FAO56_T11_T12, IMERG, POWER", bas, haut)


def secheresse_mi_saison(strategie, contexte: Contexte) -> Evaluation | None:
    if "sequence_seche_mi_saison_jours" not in contexte.cycles or contexte.cycles["sequence_seche_mi_saison_jours"].isna().all():
        return None
    parts = part_annuelle(strategie, contexte, lambda l: l["sequence_seche_mi_saison_jours"] <= SEQUENCE_SECHE_ADMISE)
    if parts is None:
        return None
    part, (bas, haut) = float(parts.mean()), intervalle_annees(parts)
    return Evaluation("eau", "secheresse_mi_saison",
                      f"Aucune séquence sèche de plus de {SEQUENCE_SECHE_ADMISE} jours au stade de mi-saison {part:.0%} "
                      f"des années, de {bas:.0%} à {haut:.0%} selon le rééchantillonnage des années.", part,
                      "part des années", 5 * part, "calcule", "FAO56_C5_C8, FAO56_T11_T12, IMERG", bas, haut)


def apport_azote_legumineuses(strategie, contexte: Contexte) -> Evaluation:
    part = sum(c in LEGUMINEUSES for c in strategie.cultures) / len(strategie.cultures)
    return Evaluation("sol", "apport_azote_legumineuses",
                      f"Une légumineuse, qui apporte de l'azote à la culture suivante, occupe {part:.0%} des années de "
                      "la rotation.", part, "part des années", 5 * part, "hypothese", "YUSUF2009")


def acces_debouche_organise(strategie, contexte: Contexte) -> Evaluation:
    part = sum(c in CULTURES_DE_RENTE for c in strategie.cultures) / len(strategie.cultures)
    return Evaluation("revenu", "acces_debouche_organise",
                      f"Le coton, principale ressource économique des zones de savane, occupe {part:.0%} des années de "
                      "la rotation. Cet indicateur pénalise mécaniquement toute rotation qui réduit le coton, et ne "
                      "mesure pas un revenu.", part, "part des années", 5 * part, "hypothese", "ZAGBAI2006")


INDICATEURS: dict[str, list[Callable]] = {
    "eau": [couverture_du_besoin, secheresse_mi_saison],
    "revenu": [acces_debouche_organise],
    "sol": [apport_azote_legumineuses],
}
LIBELLES = {"eau": "eau", "revenu": "accès à un débouché organisé", "sol": "apport d'azote par les légumineuses"}


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


def contextes_du_lieu(identifiant: str, position_semis_coton: str = "milieu",
                      courbes: dict[str, np.ndarray] | None = None,
                      mi_saisons: dict[str, tuple[int, int]] | None = None) -> dict[str, Contexte]:
    """Contexte de chaque scénario de sensibilité.

    Le coton est semé au début, au milieu ou à la fin de la fenêtre observée par le CNRA
    selon position_semis_coton, sauf dans le scénario où il est semé au début des pluies.
    courbes et mi_saisons remplacent celles de référence, pour tester une autre durée de cycle.
    """
    from .cultures import courbes_kc_comparees, mi_saisons_comparees, semis_coton
    from .donnees import altitude_power, lire_power, pluie_lieu, telecharger_point, voisinage_imerg
    from .indicateurs import evapotranspiration_serie, indicateurs_annuels, indicateurs_cultures
    from .lieux import LIEUX

    lieu = LIEUX[identifiant]
    chemin_power = telecharger_point(lieu["lat"], lieu["lon"], "power")
    meteo, altitude = lire_power(chemin_power), altitude_power(chemin_power)
    et0 = evapotranspiration_serie(meteo, lieu["lat"], altitude)
    pluie_reference = pluie_lieu(voisinage_imerg(lieu["lat"], lieu["lon"]))["moyenne"]
    courbes, mi_saisons = courbes or courbes_kc_comparees(), mi_saisons or mi_saisons_comparees()
    contextes = {}
    for nom, scenario in SCENARIOS.items():
        pluie = pluie_reference * scenario["facteur_pluie"]
        debuts = indicateurs_annuels(pluie, meteo, lieu["lat"], altitude)["debut_jour"] + scenario["retard_jours"]
        semis = semis_coton(identifiant, position_semis_coton) if scenario["semis_coton"] == "fenetre" else None
        contextes[nom] = Contexte(identifiant, nom, indicateurs_cultures(pluie, meteo, et0, debuts, courbes, mi_saisons,
                                                                         semis))
    return contextes


def tableau_evaluations(strategies, contexte: Contexte) -> pd.DataFrame:
    """Valeur, plage, score, niveau et source de chaque indicateur de chaque stratégie."""
    return pd.DataFrame([{"strategie": s.id, "critere": e.critere, "indicateur": e.indicateur, "valeur": e.valeur,
                          "bas": e.bas, "haut": e.haut, "unite": e.unite, "score": e.score, "niveau": e.niveau,
                          "source": e.source} for s in strategies for e in evaluer(s, contexte)])




def parts_par_culture(contexte: Contexte) -> pd.DataFrame:
    """Pour chaque culture, part des années où la pluie couvre le besoin et part sans séquence sèche à la mi-saison."""
    cycles = contexte.cycles.dropna(subset=["pluie_moins_etc_mm"])
    if "sequence_seche_mi_saison_jours" not in cycles:
        cycles = cycles.assign(sequence_seche_mi_saison_jours=np.nan)
    groupes = cycles.groupby("culture", sort=False)
    return pd.DataFrame({
        "annees": groupes.size(),
        "couverture_du_besoin": groupes["pluie_moins_etc_mm"].apply(lambda s: float((s >= 0).mean())),
        "sans_secheresse_mi_saison": groupes["sequence_seche_mi_saison_jours"].apply(
            lambda s: float((s.dropna() <= SEQUENCE_SECHE_ADMISE).mean()) if s.notna().any() else np.nan),
        "sequence_seche_mi_saison_mediane_jours": groupes["sequence_seche_mi_saison_jours"].median(),
    })


def tableau_scenarios(strategies, contextes: dict[str, Contexte]) -> pd.DataFrame:
    """Valeur de chaque indicateur de chaque stratégie dans chaque scénario."""
    return pd.concat({nom: tableau_evaluations(strategies, contexte).set_index(["strategie", "indicateur"])["valeur"]
                      for nom, contexte in contextes.items()}, axis=1)



def comparer_semis(strategies, contextes_par_semis: dict[str, dict[str, Contexte]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rang de chaque stratégie et indicateurs d'eau du coton selon le scénario de semis, en scénario de référence."""
    rangs = pd.DataFrame({(priorite, semis): tableau_scores(strategies, contextes["reference"], poids)["rang"]
                          for semis, contextes in contextes_par_semis.items()
                          for priorite, poids in POIDS_PAR_PRIORITE.items()})
    coton = pd.DataFrame({semis: parts_par_culture(contextes["reference"]).loc["coton"]
                          for semis, contextes in contextes_par_semis.items()})
    return rangs.sort_index(axis=1), coton


def executer() -> None:
    from .cultures import avec_stades_coton, variantes_duree_coton
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
        semis = {"debut_des_pluies": {"reference": contextes["coton_seme_au_debut_des_pluies"]}}
        for position in ["debut", "milieu", "fin"]:
            semis[f"coton_{position}_fenetre"] = contextes_du_lieu(identifiant, position)
        rangs, coton = comparer_semis(STRATEGIES, semis)
        print("\nRang selon la date de semis du coton, fenêtre de GNAPI2025, autres cultures au début des pluies")
        print(rangs.to_string())
        print(coton.round(3).to_string())
        for semis_nom, position in [("semis de référence", "milieu"), ("semis au début des pluies", None)]:
            variantes = {}
            for nom, stades in variantes_duree_coton().items():
                contextes_variante = contextes_du_lieu(identifiant, "milieu", *avec_stades_coton(stades))
                cle = "reference" if position else "coton_seme_au_debut_des_pluies"
                variantes[nom] = {"reference": contextes_variante[cle]}
            rangs, coton = comparer_semis(STRATEGIES, variantes)
            print(f"\nRang selon la durée du cycle du coton, {semis_nom}")
            print(rangs.to_string())
            print(coton.round(3).to_string())


if __name__ == "__main__":
    executer()

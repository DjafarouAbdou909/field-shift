"""Début de la saison des pluies et séquences sèches."""

from datetime import date


def plus_longue_sequence_seche(pluie: list[float], seuil: float) -> int:
    plus_longue = courante = 0
    for valeur in pluie:
        courante = courante + 1 if valeur < seuil else 0
        plus_longue = max(plus_longue, courante)
    return plus_longue


def debut_des_pluies(jours: list[date], pluie: list[float], annee: int, critere: dict) -> date | None:
    """Premier jour de la fenêtre de recherche qui satisfait le critère de config/projet.toml.

    La pluie cumulée sur jours_cumul jours, à partir de ce jour, atteint cumul_mm, et la
    plus longue séquence sèche des horizon_jours jours suivants ne dépasse pas
    sequence_seche_max_jours. Retourne None si aucun jour ne convient.
    """
    debut = date.fromisoformat(f"{annee}-{critere['debut_recherche']}")
    fin = date.fromisoformat(f"{annee}-{critere['fin_recherche']}")
    index = {jour: i for i, jour in enumerate(jours)}
    n, horizon = critere["jours_cumul"], critere["horizon_jours"]
    for jour, i in index.items():
        if not debut <= jour <= fin or i + n + horizon > len(pluie):
            continue
        if sum(pluie[i:i + n]) < critere["cumul_mm"]:
            continue
        suite = pluie[i + n:i + n + horizon]
        if plus_longue_sequence_seche(suite, critere["jour_sec_mm"]) <= critere["sequence_seche_max_jours"]:
            return jour
    return None


def premieres_pluies(jours: list[date], pluie: list[float], annee: int, critere: dict) -> date | None:
    """Premier jour de la fenêtre où la pluie cumulée sur jours_cumul jours atteint cumul_mm, sans autre condition."""
    debut = date.fromisoformat(f"{annee}-{critere['debut_recherche']}")
    fin = date.fromisoformat(f"{annee}-{critere['fin_recherche']}")
    n = critere["jours_cumul"]
    for i, jour in enumerate(jours):
        if debut <= jour <= fin and sum(pluie[i:i + n]) >= critere["cumul_mm"]:
            return jour
    return None


def faux_departs(jours: list[date], pluie: list[float], debuts: dict, critere: dict) -> tuple[int, int]:
    """Nombre d'années où les premières pluies précèdent le vrai début, et nombre d'années évaluées.

    Un faux départ est une première pluie suivie d'une séquence sèche trop longue pour que
    le critère de début des pluies soit satisfait ce jour-là.
    """
    faux = evaluees = 0
    for annee, debut in debuts.items():
        premiere = premieres_pluies(jours, pluie, annee, critere)
        if premiere is None or debut is None:
            continue
        evaluees += 1
        faux += premiere < debut
    return faux, evaluees

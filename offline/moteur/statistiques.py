"""Statistiques descriptives sans dépendance externe."""

import math
import random
import statistics


def quartiles(valeurs: list[float]) -> tuple[float, float, float]:
    q1, mediane, q3 = statistics.quantiles(valeurs, n=4, method="inclusive")
    return q1, mediane, q3


def proportion_wilson(succes: int, total: int, z: float = 1.959964) -> tuple[float, float]:
    """Intervalle de confiance à 95 % de Wilson pour une proportion."""
    if total == 0:
        return math.nan, math.nan
    p = succes / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    demi = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return max(0.0, centre - demi), min(1.0, centre + demi)


def tendance(annees: list[int], valeurs: list[float], tirages: int = 2000, graine: int = 20261114):
    """Pente par décennie par moindres carrés, avec intervalle à 95 % par bootstrap des années."""
    pente = 10 * statistics.linear_regression(annees, valeurs).slope
    generateur, pentes = random.Random(graine), []
    couples = list(zip(annees, valeurs))
    while len(pentes) < tirages:
        tirage = [generateur.choice(couples) for _ in couples]
        if len({a for a, _ in tirage}) < 3:
            continue
        x, y = zip(*tirage)
        pentes.append(10 * statistics.linear_regression(x, y).slope)
    pentes.sort()
    return pente, pentes[int(0.025 * tirages)], pentes[int(0.975 * tirages) - 1]

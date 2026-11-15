"""Séries journalières de chaque lieu, moyennes sur sa grille de points."""

import math
from datetime import date

from donnees import power
from donnees.config import points

from .fao56 import et0, pression_saturante


def serie_point(contenu: dict, latitude: float) -> dict[date, tuple[float, float]]:
    """Pluie et évapotranspiration de référence de chaque jour pour un point, NaN si une donnée manque."""
    p = contenu["properties"]["parameter"]
    altitude = contenu["geometry"]["coordinates"][2]
    resultat = {}
    for cle in p["IMERG_PRECTOT"]:
        jour = date(int(cle[:4]), int(cle[4:6]), int(cle[6:]))
        valeurs = [p[n][cle] for n in ("IMERG_PRECTOT", "T2M_MAX", "T2M_MIN", "T2MDEW", "ALLSKY_SFC_SW_DWN", "WS2M")]
        pluie, tmax, tmin, tdew, rs, u2 = (math.nan if v == power.VALEUR_MANQUANTE else v for v in valeurs)
        evapo = math.nan if math.isnan(tmax + tmin + tdew + rs + u2) else et0(
            tmax, tmin, pression_saturante(tdew), rs, u2, altitude, latitude, jour.timetuple().tm_yday)
        resultat[jour] = (pluie, evapo)
    return resultat


def moyenne_connue(valeurs: list[float]) -> float:
    connues = [v for v in valeurs if not math.isnan(v)]
    return sum(connues) / len(connues) if connues else math.nan


def series_lieux(config: dict, lire=power.lire) -> dict[str, dict]:
    """Pour chaque lieu, les jours, la pluie et l'évapotranspiration moyennes sur ses points."""
    par_lieu = {}
    for point in points(config):
        par_lieu.setdefault(point.lieu, []).append(serie_point(lire(point), point.lat))
    resultat = {}
    for lieu, series in par_lieu.items():
        jours = sorted(series[0])
        resultat[lieu] = {
            "jours": jours,
            "pluie": [moyenne_connue([s[j][0] for s in series]) for j in jours],
            "et0": [moyenne_connue([s[j][1] for s in series]) for j in jours],
        }
    return resultat

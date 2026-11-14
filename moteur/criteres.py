"""Critères de comparaison des rotations, classement et sensibilité.

Le critère eau est calculé à partir des données NASA et de FAO 56. Les critères sol et
débouché reposent sur des hypothèses déclarées comme telles.
"""

import math

from .fao56 import kc_journalier
from .saison import debut_des_pluies
from .statistiques import proportion_wilson


def debuts_par_annee(serie: dict, config: dict) -> dict:
    annees = sorted({j.year for j in serie["jours"]})
    return {a: debut_des_pluies(serie["jours"], serie["pluie"], a, config["saison"]) for a in annees}


def bilan_mi_saison(serie: dict, culture: dict, debut, facteur_pluie: float = 1.0, retard: int = 0):
    """Pluie et besoin en eau au stade de mi-saison pour un semis au début des pluies, ou None."""
    if debut is None:
        return None
    i = serie["jours"].index(debut) + retard
    l_ini, l_dev, l_mid, _ = culture["stades"]
    a, b = i + l_ini + l_dev, i + l_ini + l_dev + l_mid
    if b > len(serie["jours"]):
        return None
    kc = kc_journalier(culture["stades"], culture["kc"])[l_ini + l_dev:l_ini + l_dev + l_mid]
    pluie = facteur_pluie * sum(serie["pluie"][a:b])
    besoin = sum(k * e for k, e in zip(kc, serie["et0"][a:b]))
    return None if math.isnan(pluie + besoin) else (pluie, besoin)


def couverture(serie: dict, culture: dict, debuts: dict, facteur_pluie=1.0, retard=0) -> dict:
    """Nombre d'années où la pluie couvre le besoin en eau de mi-saison, sur les années évaluables."""
    bilans = [bilan_mi_saison(serie, culture, d, facteur_pluie, retard) for d in debuts.values()]
    bilans = [b for b in bilans if b is not None]
    couvertes = sum(p >= besoin for p, besoin in bilans)
    bas, haut = proportion_wilson(couvertes, len(bilans))
    return {"couvertes": couvertes, "annees": len(bilans), "part": couvertes / len(bilans) if bilans else math.nan,
            "bas": bas, "haut": haut}


def scores_rotations(serie: dict, config: dict, debuts: dict, facteur_pluie=1.0, retard=0) -> dict:
    cultures = config["cultures"]
    par_culture = {c: couverture(serie, cultures[c], debuts, facteur_pluie, retard) for c in cultures}
    resultat = {}
    for rotation in config["rotations"]:
        liste = rotation["cultures"]
        resultat[rotation["id"]] = {
            "eau": sum(par_culture[c]["part"] for c in liste) / len(liste),
            "sol": sum(cultures[c]["legumineuse"] for c in liste) / len(liste),
            "debouche": liste.count("coton") / len(liste),
            "cultures": {c: par_culture[c] for c in liste},
        }
    return resultat


def classer(scores: dict, poids: dict) -> list[tuple[str, float, int]]:
    """Rotations triées par total décroissant, avec leur rang. Des totaux égaux partagent le rang."""
    totaux = sorted(((r, sum(poids[k] * s[k] for k in poids)) for r, s in scores.items()),
                    key=lambda t: (-t[1], t[0]))
    resultat = []
    for i, (r, total) in enumerate(totaux):
        egal = resultat and abs(total - resultat[-1][1]) < 1e-9
        resultat.append((r, total, resultat[-1][2] if egal else i + 1))
    return resultat


def groupes(classement: list[tuple[str, float, int]]) -> list[list[str]]:
    """Classement sous forme de groupes ex aequo, pour comparer deux scénarios."""
    resultat = {}
    for r, _, rang in classement:
        resultat.setdefault(rang, []).append(r)
    return [sorted(g) for _, g in sorted(resultat.items())]


def sensibilite(serie: dict, config: dict, debuts: dict, poids: dict) -> dict:
    """Classement de référence et classements sous les scénarios de config/projet.toml."""
    s = config["sensibilite"]
    scenarios = {
        "reference": scores_rotations(serie, config, debuts),
        "pluie_reduite": scores_rotations(serie, config, debuts, facteur_pluie=s["facteur_pluie"]),
        "semis_retarde": scores_rotations(serie, config, debuts, retard=s["retard_jours"]),
    }
    ordres = {n: groupes(classer(sc, poids)) for n, sc in scenarios.items()}
    return {"scores": scenarios["reference"], "classement": classer(scenarios["reference"], poids),
            "ordres": ordres, "stable": len({str(o) for o in ordres.values()}) == 1}

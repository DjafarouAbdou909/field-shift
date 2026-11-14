"""Calcule toutes les recommandations et les exporte pour l'application hors connexion.

    python -m moteur.exporter

Chaque texte est produit ici, à partir des résultats du moteur. L'application ne fait
que les afficher, et ne calcule ni n'invente aucun chiffre.
"""

import copy
import json
import statistics
from datetime import datetime, timezone

from donnees.config import RACINE, charger

from .criteres import debuts_par_annee, sensibilite
from .series import series_lieux
from .statistiques import quartiles, tendance

SORTIE = RACINE / "app" / "donnees" / "recommandations.json"
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
SOURCE_NASA = "NASA GPM IMERG et NASA POWER, 2001 à 2024"
SOURCE_FAO = "FAO 56, tableaux 11 et 12"
CRITERES = {"eau": "Eau", "sol": "Sol", "debouche": "Débouché"}


def nombre(x: float, decimales: int = 0) -> str:
    return f"{x:.{decimales}f}".replace(".", ",").replace("-", "moins ")


def date_texte(jour_annee: float) -> str:
    from datetime import date, timedelta
    d = date(2001, 1, 1) + timedelta(days=round(jour_annee) - 1)
    return f"{d.day} {MOIS[d.month - 1]}"


def de_la(nom: str) -> str:
    return f"de l'{nom}" if nom[0] in "aeiouéèh" else f"du {nom}"


def tendances_debut(serie: dict, config: dict) -> list[tuple[int, float, float, float]]:
    """Tendance du début des pluies avec le critère retenu, puis avec chaque variante."""
    resultat = []
    for duree in [config["saison"]["sequence_seche_max_jours"]] + config["saison"]["variantes_sequence_seche"]:
        variante = copy.deepcopy(config)
        variante["saison"]["sequence_seche_max_jours"] = duree
        trouves = {a: d.timetuple().tm_yday for a, d in debuts_par_annee(serie, variante).items() if d}
        resultat.append((duree, *tendance(list(trouves), list(trouves.values()))))
    return resultat


def texte_tendance(tendances: list) -> tuple[str, str]:
    duree, pente, bas, haut = tendances[0]
    robuste = all(b > 0 for _, _, b, _ in tendances) or all(h < 0 for _, _, _, h in tendances)
    detail = " ".join(f"Avec {d} jours secs au plus, {nombre(p, 1)} jours par décennie, intervalle à 95 % "
                      f"de {nombre(b, 1)} à {nombre(h, 1)}." for d, p, b, h in tendances)
    if robuste:
        sens = "plus tard" if pente > 0 else "plus tôt"
        return (f"Le début des pluies arrive de plus en plus {sens}, d'environ {nombre(abs(pente), 0)} jours "
                f"par décennie, quel que soit le critère retenu.", detail)
    return ("Aucune tendance robuste du début des pluies n'est établie, le résultat dépend du critère retenu.",
            detail)


def indicateurs(serie: dict, debuts: dict, config: dict) -> list[dict]:
    trouves = {a: d.timetuple().tm_yday for a, d in debuts.items() if d}
    q1, med, q3 = quartiles(list(trouves.values()))
    texte, detail = texte_tendance(tendances_debut(serie, config))
    annuelles = {}
    for jour, pluie in zip(serie["jours"], serie["pluie"]):
        annuelles[jour.year] = annuelles.get(jour.year, 0.0) + pluie
    p_pente, p_bas, p_haut = tendance(list(annuelles), list(annuelles.values()))
    return [
        {"texte": f"Les pluies démarrent en général vers le {date_texte(med)}, entre le {date_texte(q1)} "
                  f"et le {date_texte(q3)} une année sur deux.",
         "niveau": "calcule", "source": SOURCE_NASA,
         "detail": f"Début trouvé {len(trouves)} années sur {len(debuts)}."},
        {"texte": texte, "niveau": "calcule", "source": SOURCE_NASA, "detail": detail},
        {"texte": f"Pluie annuelle moyenne {nombre(statistics.mean(annuelles.values()))} mm, écart type "
                  f"{nombre(statistics.stdev(annuelles.values()))} mm.",
         "niveau": "mesure", "source": SOURCE_NASA, "detail": ""},
        {"texte": f"Tendance de la pluie annuelle, {nombre(p_pente)} mm par décennie, intervalle à 95 % "
                  f"de {nombre(p_bas)} à {nombre(p_haut)}.",
         "niveau": "calcule", "source": SOURCE_NASA, "detail": ""},
    ]


def explications(rotation: dict, scores: dict, cultures: dict) -> list[dict]:
    elements = []
    for c, couv in scores["cultures"].items():
        elements.append({
            "texte": f"Au stade de pleine croissance, la pluie a couvert le besoin en eau "
                     f"{de_la(cultures[c]['nom'])} {couv['couvertes']} années sur {couv['annees']}.",
            "niveau": "calcule", "source": f"{SOURCE_NASA}, {SOURCE_FAO}",
            "detail": f"Intervalle à 95 % de {nombre(100 * couv['bas'])} à {nombre(100 * couv['haut'])} %."})
    n, leg = len(rotation["cultures"]), sum(cultures[c]["legumineuse"] for c in rotation["cultures"])
    elements.append({
        "texte": f"{leg} année de légumineuse sur {n}." if leg else f"Aucune légumineuse sur {n} années.",
        "niveau": "hypothese", "source": "",
        "detail": "On suppose que les légumineuses enrichissent le sol en azote. À confirmer localement."})
    elements.append({
        "texte": f"{rotation['cultures'].count('coton')} année de coton sur {n}.",
        "niveau": "hypothese", "source": "",
        "detail": "On suppose que le coton offre un débouché organisé. À confirmer localement."})
    return elements


def construire(config: dict) -> dict:
    series = series_lieux(config)
    rotations = {r["id"]: r for r in config["rotations"]}
    sortie = {
        "version": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        "periode": f"{config['periode']['debut'][:4]} à {config['periode']['fin'][:4]}",
        "rayon_couverture_km": config["rayon_couverture_km"],
        "avertissement": "Conseil indicatif, fondé sur le climat passé. À discuter avec votre conseiller ANADER.",
        "priorites": {k: v["libelle"] for k, v in config["priorites"].items()},
        "rotation_actuelle": next(r["id"] for r in config["rotations"] if r["actuelle"]),
        "lieux": {},
    }
    s = config["sensibilite"]
    for lieu in config["lieux"]:
        serie, debuts = series[lieu["id"]], debuts_par_annee(series[lieu["id"]], config)
        resultats = {}
        for priorite, p in config["priorites"].items():
            analyse = sensibilite(serie, config, debuts, p["poids"])
            resultats[priorite] = {
                "stable": analyse["stable"],
                "stabilite": "Ce classement tient si la pluie baisse de "
                             f"{nombre(100 * (1 - s['facteur_pluie']))} % ou si les pluies démarrent "
                             f"{s['retard_jours']} jours plus tard." if analyse["stable"] else
                             "Attention, ce classement change si la pluie baisse de "
                             f"{nombre(100 * (1 - s['facteur_pluie']))} % ou si les pluies démarrent "
                             f"{s['retard_jours']} jours plus tard.",
                "ordres": analyse["ordres"],
                "strategies": [{
                    "id": r, "nom": rotations[r]["nom"], "actuelle": rotations[r]["actuelle"],
                    "rang": rang, "total": round(total, 4),
                    "scores": {k: round(analyse["scores"][r][k], 4) for k in CRITERES},
                    "explications": explications(rotations[r], analyse["scores"][r], config["cultures"]),
                } for r, total, rang in analyse["classement"]],
            }
        sortie["lieux"][lieu["id"]] = {"nom": lieu["nom"], "lat": lieu["lat"], "lon": lieu["lon"],
                                      "indicateurs": indicateurs(serie, debuts, config), "resultats": resultats}
    return sortie


def main() -> None:
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(construire(charger()), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Recommandations écrites dans {SORTIE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()

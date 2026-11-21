"""Contrôles des séries POWER et IMERG de la phase 2, sans modification des données.

Exécution depuis la racine du dépôt, qui télécharge les séries absentes puis affiche
les tableaux cités dans docs/donnees.md
    venv/bin/python -m moteur.controles

Les bornes physiques ne supposent aucun seuil climatique. La pluie, le vent et le
rayonnement ne sont pas négatifs, le minimum journalier de température ne dépasse pas
le maximum, le point de rosée ne dépasse pas la température maximale, et le
rayonnement au sol ne dépasse pas le rayonnement extraterrestre de FAO-56. Le seuil de
200 mm par jour est celui du projet antérieur, qui y repérait les cumuls aberrants de
PRECTOTCORR, et sert ici de repère, pas de borne.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from .donnees import (DOSSIER_POWER, PRODUITS, STATIONS_GHCN, centre_case_imerg, lire_pluie_station, lire_power, lire_tmax_station,
                      telecharger_point, telecharger_station, voisinage_imerg)
from .indicateurs import rayonnement_extraterrestre
from .lieux import LIEUX, LIEUX_ETUDE

SEUIL_CUMUL_SUSPECT = 200.0


POINTS_ESSAI_RESOLUTION = {"case 9,4 à 9,5 et -5,7 à -5,6, premier point": (9.42, -5.68),
                           "même case, second point": (9.48, -5.62),
                           "case voisine au nord": (9.52, -5.62)}


def essai_resolution_imerg(dossier: Path = DOSSIER_POWER / "essai_resolution", debut: str = "20250801",
                           fin: str = "20250810") -> pd.DataFrame:
    """Pluie IMERG de POWER en trois points, deux dans une même case de 0,1 degré et un dans la case voisine.

    Des valeurs identiques dans la même case et différentes dans la case voisine montrent
    que POWER sert IMERG à sa résolution native de 0,1 degré. Les fichiers de l'essai sont
    rangés à part, pour ne pas être confondus avec les séries complètes.
    """
    return pd.DataFrame({
        nom: lire_power(telecharger_point(*point, "imerg", dossier, dossier / "registre.csv", debut, fin))["IMERG_PRECTOT"]
        for nom, point in POINTS_ESSAI_RESOLUTION.items()
    })


def controler_serie(serie: pd.DataFrame, latitude: float, debut: str, fin: str) -> dict:
    """Résume la couverture, les manques et les violations de bornes physiques d'une série."""
    attendues = pd.date_range(debut, fin, freq="D")
    resume = {
        "jours": len(serie),
        "jours_attendus": len(attendues),
        "dates_uniques": bool(serie.index.is_unique),
        "dates_manquantes": int(len(attendues.difference(serie.index))),
    }
    for variable in serie.columns:
        resume[f"{variable} manquants"] = int(serie[variable].isna().sum())
        resume[f"{variable} min"] = float(serie[variable].min())
        resume[f"{variable} max"] = float(serie[variable].max())
    violations = {}
    for variable in ["IMERG_PRECTOT", "PRECTOTCORR", "WS2M", "ALLSKY_SFC_SW_DWN"]:
        if variable in serie:
            violations[f"{variable} négatif"] = int((serie[variable] < 0).sum())
    if {"T2M_MIN", "T2M_MAX"} <= set(serie.columns):
        violations["T2M_MIN supérieur à T2M_MAX"] = int((serie["T2M_MIN"] > serie["T2M_MAX"]).sum())
    if {"T2MDEW", "T2M_MAX"} <= set(serie.columns):
        violations["T2MDEW supérieur à T2M_MAX"] = int((serie["T2MDEW"] > serie["T2M_MAX"]).sum())
    if "ALLSKY_SFC_SW_DWN" in serie:
        ra = rayonnement_extraterrestre(latitude, serie.index.dayofyear.to_numpy())
        violations["rayonnement supérieur au rayonnement extraterrestre"] = int((serie["ALLSKY_SFC_SW_DWN"] > ra).sum())
    for variable in ["IMERG_PRECTOT", "PRECTOTCORR"]:
        if variable in serie:
            violations[f"{variable} au-delà de 200 mm"] = int((serie[variable] > SEUIL_CUMUL_SUSPECT).sum())
    resume.update(violations)
    return resume


def comparer_pluies(imerg: pd.Series, prectotcorr: pd.Series) -> pd.DataFrame:
    """Compare par année les cumuls et la corrélation journalière des deux sources.

    IMERG est en temps universel et POWER en temps solaire local, décalés d'environ
    22 minutes à la longitude de Korhogo et de 20 minutes à celle de Bouaké, ce qui ne
    change pas l'attribution des pluies à un jour pour l'essentiel.
    """
    communs = pd.concat({"imerg": imerg, "prectotcorr": prectotcorr}, axis=1).dropna()
    annees = communs.groupby(communs.index.year)
    table = annees.sum().rename(columns={"imerg": "imerg_mm", "prectotcorr": "prectotcorr_mm"})
    table["rapport"] = table["prectotcorr_mm"] / table["imerg_mm"]
    table["correlation_journaliere"] = annees.apply(
        lambda g: g["imerg"].corr(g["prectotcorr"]) if len(g) > 2 else np.nan)
    return table.round(3)


def comparer_station(station: pd.Series, imerg: pd.Series, prectotcorr: pd.Series) -> pd.Series:
    """Compare chaque source satellitaire au pluviomètre sur les seuls jours où il a une valeur.

    Les jours déclarés par la station ne forment pas un échantillon tiré au hasard, si
    bien que les sommes ne disent rien du cumul annuel. Seule la comparaison des deux
    sources sur les mêmes jours a un sens. Le décalage d'un jour sert à vérifier
    l'alignement des dates.
    """
    jours = pd.concat({"station": station, "imerg": imerg, "imerg_veille": imerg.shift(1),
                       "prectotcorr": prectotcorr}, axis=1, sort=True).dropna()
    return pd.Series({
        "jours_communs": len(jours),
        "annees_avec_donnees": jours.index.year.nunique(),
        "correlation_station_imerg": jours["station"].corr(jours["imerg"]),
        "correlation_station_imerg_veille": jours["station"].corr(jours["imerg_veille"]),
        "correlation_station_prectotcorr": jours["station"].corr(jours["prectotcorr"]),
        "somme_station_mm": jours["station"].sum(),
        "somme_imerg_mm": jours["imerg"].sum(),
        "somme_prectotcorr_mm": jours["prectotcorr"].sum(),
    }).round(3)


def comparer_tmax_station(station: pd.Series, merra: pd.Series, seuil: float = 35.0) -> pd.Series:
    """Compare la température maximale de MERRA-2 au thermomètre, sur les jours communs."""
    jours = pd.concat({"station": station, "merra": merra}, axis=1, sort=True).dropna()
    return pd.Series({
        "jours_communs": len(jours),
        "annees_avec_donnees": jours.index.year.nunique(),
        "ecart_moyen_merra_moins_station": (jours["merra"] - jours["station"]).mean(),
        "correlation": jours["merra"].corr(jours["station"]),
        f"part_jours_station_au_dela_de_{seuil:.0f}": (jours["station"] > seuil).mean(),
        f"part_jours_merra_au_dela_de_{seuil:.0f}": (jours["merra"] > seuil).mean(),
    }).round(3)


def dispersion_voisinage(series: dict[tuple[float, float], pd.Series]) -> pd.DataFrame:
    """Compare la case du lieu aux huit cases voisines, en cumul annuel et au jour le jour."""
    cles = list(series)
    centre = series[cles[0]]
    annuels = pd.DataFrame({cle: s.groupby(s.index.year).sum() for cle, s in series.items()})
    return pd.DataFrame({
        "case_du_lieu_mm": annuels[cles[0]],
        "min_9_cases_mm": annuels.min(axis=1),
        "max_9_cases_mm": annuels.max(axis=1),
        "moyenne_9_cases_mm": annuels.mean(axis=1),
        "rang_case_du_lieu": annuels.rank(axis=1, ascending=False)[cles[0]],
        "correlation_journaliere_mediane_avec_voisines": pd.Series({
            annee: np.median([centre[centre.index.year == annee].corr(series[c][series[c].index.year == annee])
                              for c in cles[1:]])
            for annee in annuels.index
        }),
    }).round(3)


def ecart_case_moyenne(dispersion: pd.DataFrame) -> pd.DataFrame:
    """Écart annuel de la case du lieu à la moyenne des neuf cases, en mm et en %, par période."""
    ecart_mm = dispersion["case_du_lieu_mm"] - dispersion["moyenne_9_cases_mm"]
    ecart_pct = 100 * ecart_mm / dispersion["moyenne_9_cases_mm"]
    periodes = {"2001-2012": slice(2001, 2012), "2013-2025": slice(2013, 2025), "2001-2025": slice(2001, 2025)}
    return pd.DataFrame({
        nom: {"ecart_moyen_mm": ecart_mm.loc[p].mean(), "ecart_moyen_pct": ecart_pct.loc[p].mean(),
              "ecart_min_pct": ecart_pct.loc[p].min(), "ecart_max_pct": ecart_pct.loc[p].max()}
        for nom, p in periodes.items()
    }).T.round(1)


def climatologie_mensuelle(pluie: pd.Series) -> pd.DataFrame:
    """Pluie mensuelle moyenne, avec ses quantiles 10 et 90 % entre années."""
    mensuel = pluie.groupby([pluie.index.year, pluie.index.month]).sum().unstack()
    return pd.DataFrame({"moyenne_mm": mensuel.mean(), "q10_mm": mensuel.quantile(0.1),
                         "q90_mm": mensuel.quantile(0.9)}).round(1)


DEBUT_SERIES, FIN_SERIES = "2001-01-01", "2025-12-31"


def charger_lieu(identifiant: str) -> dict:
    """Charge les séries d'un lieu, en les téléchargeant si elles manquent.

    Le résultat contient la météo POWER, la pluie IMERG des neuf cases, la case du lieu en
    tête, la pluie IMERG de la case du pluviomètre, et la pluie et la température maximale
    du pluviomètre GHCN-Daily sur la période des séries.
    """
    lieu = LIEUX[identifiant]
    cases = voisinage_imerg(lieu["lat"], lieu["lon"])
    station, lat_station, lon_station = STATIONS_GHCN[identifiant]
    case_station = centre_case_imerg(lat_station, lon_station)
    fichier_station = telecharger_station(station)
    return {
        "power": lire_power(telecharger_point(lieu["lat"], lieu["lon"], "power")),
        "cases": cases,
        "imerg": {case: lire_power(telecharger_point(*case, "imerg"))["IMERG_PRECTOT"] for case in cases},
        "station": station,
        "case_station": case_station,
        "imerg_station": lire_power(telecharger_point(*case_station, "imerg"))["IMERG_PRECTOT"],
        "pluie_station": lire_pluie_station(fichier_station).loc[DEBUT_SERIES:FIN_SERIES],
        "tmax_station": lire_tmax_station(fichier_station).loc[DEBUT_SERIES:FIN_SERIES],
    }


def rupture_rapport(comparaison: pd.DataFrame, annee: int = 2020) -> pd.Series:
    """Moyenne et écart-type du rapport PRECTOTCORR sur IMERG avant et à partir d'une année."""
    avant, apres = comparaison.loc[:annee - 1, "rapport"], comparaison.loc[annee:, "rapport"]
    return pd.Series({"moyenne_avant": avant.mean(), "ecart_type_avant": avant.std(),
                      "moyenne_apres": apres.mean(), "ecart_type_apres": apres.std()})


def case_la_plus_arrosee(dispersion: pd.DataFrame, coupure: int = 2013) -> pd.Series:
    """Nombre d'années où la case du lieu est la plus arrosée des neuf, avant et à partir d'une année."""
    premiere = dispersion["rang_case_du_lieu"] == 1
    return pd.Series({"annees_avant": int((dispersion.index < coupure).sum()),
                      "premiere_avant": int(premiere[dispersion.index < coupure].sum()),
                      "annees_apres": int((dispersion.index >= coupure).sum()),
                      "premiere_apres": int(premiere[dispersion.index >= coupure].sum())})


def jours_par_annee(serie: pd.Series) -> pd.Series:
    """Nombre de jours renseignés par année."""
    return serie.dropna().groupby(serie.dropna().index.year).size()


def executer() -> None:
    debut, fin = DEBUT_SERIES, FIN_SERIES
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    for identifiant, lieu in LIEUX_ETUDE.items():
        lat, lon = lieu["lat"], lieu["lon"]
        series = charger_lieu(identifiant)
        power, cases, imerg = series["power"], series["cases"], series["imerg"]
        pluie = imerg[cases[0]]
        print(f"\n===== {lieu['nom']}, point {lat}, {lon}, case IMERG centrée en {cases[0]}")
        print("\nContrôles POWER")
        print(pd.Series(controler_serie(power, lat, debut, fin)).to_string())
        print("\nContrôles IMERG, case du lieu")
        print(pd.Series(controler_serie(pluie.to_frame(), lat, debut, fin)).to_string())
        print("\nComparaison annuelle IMERG et PRECTOTCORR")
        comparaison = comparer_pluies(pluie, power["PRECTOTCORR"])
        print(comparaison.to_string())
        rupture = rupture_rapport(comparaison)
        print(f"rapport moyen 2001-2019 {rupture['moyenne_avant']:.3f}, écart-type {rupture['ecart_type_avant']:.3f}, "
              f"2020-2025 {rupture['moyenne_apres']:.3f}, écart-type {rupture['ecart_type_apres']:.3f}")
        print(f"cumul annuel moyen 2001-2025, IMERG {comparaison['imerg_mm'].mean():.0f} mm, "
              f"PRECTOTCORR {comparaison['prectotcorr_mm'].mean():.0f} mm")
        print("\nDispersion entre la case du lieu et ses huit voisines")
        dispersion = dispersion_voisinage(imerg)
        print(dispersion.to_string())
        premiere = case_la_plus_arrosee(dispersion)
        print(f"case du lieu la plus arrosée des neuf, {premiere['premiere_avant']} années sur {premiere['annees_avant']} "
              f"de 2001 à 2012, {premiere['premiere_apres']} sur {premiere['annees_apres']} de 2013 à 2025")
        print("\nÉcart de la case du lieu à la moyenne des neuf cases, pluie retenue pour le lieu")
        print(ecart_case_moyenne(dispersion).to_string())
        print("\nClimatologie mensuelle IMERG, case du lieu")
        print(climatologie_mensuelle(pluie).to_string())
        station, case_station = series["station"], series["case_station"]
        print(f"\nComparaison au pluviomètre GHCN-Daily {station}, case IMERG {case_station}")
        print(comparer_station(series["pluie_station"], series["imerg_station"], power["PRECTOTCORR"]).to_string())
        print("jours de station par année")
        print(jours_par_annee(series["pluie_station"]).rename_axis("date").to_string())
        print(f"\nTempérature maximale de MERRA-2 et du thermomètre {station}")
        print(comparer_tmax_station(series["tmax_station"], power["T2M_MAX"]).to_string())
    print(f"\nParamètres téléchargés {PRODUITS}")


if __name__ == "__main__":
    executer()

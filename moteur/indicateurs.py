"""Indicateurs climatiques annuels par lieu, avec tendance et variabilité interannuelle.

Exécution depuis la racine du dépôt, qui écrit data/processed/indicateurs_<lieu>_<variante>.csv
et affiche les résumés cités dans docs/donnees.md
    venv/bin/python -m moteur.indicateurs

Origine. pression_saturante, rayonnement_extraterrestre, evapotranspiration_reference et
leurs constantes viennent sans modification de src/features/indicateurs.py dans
~/African-Crop-Yield-Intelligence au commit 2b4c18c, de même que le seuil de 1 mm qui
distingue un jour de pluie d'un jour sec.

Règles de saison. Le début est le premier jour, à partir d'une date de recherche, qui
ouvre trois jours cumulant au moins 20 mm, sans séquence sèche de plus de 7 jours dans
les 30 jours qui commencent ce jour-là. La fin est le dernier jour de pluie, à partir du
1er septembre, suivi de 20 jours secs. Ces seuils sont attribués à Sivakumar, 1988,
Agricultural and Forest Meteorology 42, pages 295 à 305, par des sources secondaires.
L'article original n'a pas été lu, l'attribution reste donc à vérifier. Les seuils sont
des paramètres de RegleSaison, visibles et modifiables, et chaque indicateur qui en
dépend est de niveau calcule.
"""

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

SEUIL_JOUR_PLUIE = 1.0
ALBEDO = 0.23
CONSTANTE_SOLAIRE = 0.0820
STEFAN_BOLTZMANN = 4.903e-9
SEUIL_CHALEUR = 35.0


def pression_saturante(temperature):
    """Retourne la pression de vapeur saturante en kilopascals, équation 11 de FAO-56."""
    return 0.6108 * np.exp(17.27 * temperature / (temperature + 237.3))


def rayonnement_extraterrestre(latitude, jour):
    """Retourne le rayonnement extraterrestre journalier en MJ par m², équation 21 de FAO-56."""
    phi = np.radians(latitude)
    dr = 1 + 0.033 * np.cos(2 * np.pi * jour / 365)
    declinaison = 0.409 * np.sin(2 * np.pi * jour / 365 - 1.39)
    omega = np.arccos(np.clip(-np.tan(phi) * np.tan(declinaison), -1, 1))
    return 24 * 60 / np.pi * CONSTANTE_SOLAIRE * dr * (
        omega * np.sin(phi) * np.sin(declinaison) + np.cos(phi) * np.cos(declinaison) * np.sin(omega)
    )


def evapotranspiration_reference(tmax, tmin, tdew, rayonnement, vent, latitude, altitude, jour):
    """Retourne l'évapotranspiration de référence journalière en millimètres, équation 6 de FAO-56.

    Les températures sont en degrés Celsius, le rayonnement incident en MJ par m² et par
    jour, le vent à 2 m en mètres par seconde et l'altitude en mètres.
    """
    tmoy = (tmax + tmin) / 2
    pente = 4098 * pression_saturante(tmoy) / (tmoy + 237.3) ** 2
    pression = 101.3 * ((293 - 0.0065 * altitude) / 293) ** 5.26
    gamma = 0.000665 * pression
    es = (pression_saturante(tmax) + pression_saturante(tmin)) / 2
    ea = pression_saturante(tdew)
    ra = rayonnement_extraterrestre(latitude, jour)
    rso = (0.75 + 2e-5 * altitude) * ra
    rapport = np.clip(rayonnement / np.where(rso > 0, rso, np.nan), 0, 1)
    rnl = STEFAN_BOLTZMANN * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 * (
        0.34 - 0.14 * np.sqrt(ea)
    ) * (1.35 * rapport - 0.35)
    rn = (1 - ALBEDO) * rayonnement - rnl
    return (0.408 * pente * rn + gamma * 900 / (tmoy + 273) * vent * (es - ea)) / (pente + gamma * (1 + 0.34 * vent))


@dataclass(frozen=True)
class RegleSaison:
    recherche_debut: str = "05-01"
    cumul_debut_mm: float = 20.0
    jours_cumul: int = 3
    jours_controle: int = 30
    sequence_seche_admise: int = 7
    recherche_fin: str = "09-01"
    jours_secs_fin: int = 20
    jours_debut_saison: int = 60


def plus_longue_sequence_seche(pluie: np.ndarray, seuil: float = SEUIL_JOUR_PLUIE) -> int:
    """Retourne le plus grand nombre de jours consécutifs sous le seuil de pluie."""
    plus_longue = courante = 0
    for valeur in pluie:
        courante = courante + 1 if valeur < seuil else 0
        plus_longue = max(plus_longue, courante)
    return plus_longue


def debut_saison(pluie: pd.Series, annee: int, regle: RegleSaison = RegleSaison()) -> pd.Timestamp:
    """Retourne la date de début de saison d'une année, ou NaT si la règle n'est jamais remplie."""
    valeurs = pluie.to_numpy()
    depart = pluie.index.get_loc(pd.Timestamp(f"{annee}-{regle.recherche_debut}"))
    limite = pluie.index.get_loc(pd.Timestamp(f"{annee}-12-31"))
    for jour in range(depart, limite + 1):
        if jour + regle.jours_controle > len(valeurs):
            break
        if valeurs[jour:jour + regle.jours_cumul].sum() < regle.cumul_debut_mm:
            continue
        if plus_longue_sequence_seche(valeurs[jour:jour + regle.jours_controle]) <= regle.sequence_seche_admise:
            return pluie.index[jour]
    return pd.NaT


def fin_saison(pluie: pd.Series, annee: int, regle: RegleSaison = RegleSaison()) -> pd.Timestamp:
    """Retourne le dernier jour de pluie de l'année suivi de jours secs, ou NaT faute d'un tel jour.

    Le jour de fin appartient à l'année, mais les jours secs qui le suivent peuvent
    déborder sur janvier.
    """
    valeurs = pluie.to_numpy()
    depart = pluie.index.get_loc(pd.Timestamp(f"{annee}-{regle.recherche_fin}"))
    limite = pluie.index.get_loc(pd.Timestamp(f"{annee}-12-31"))
    for jour in range(depart, min(limite + 1, len(valeurs) - regle.jours_secs_fin)):
        if valeurs[jour] >= SEUIL_JOUR_PLUIE and (valeurs[jour + 1:jour + 1 + regle.jours_secs_fin] < SEUIL_JOUR_PLUIE).all():
            return pluie.index[jour]
    return pd.NaT


def indicateurs_annuels(pluie: pd.Series, meteo: pd.DataFrame, latitude: float, altitude: float,
                        regle: RegleSaison = RegleSaison()) -> pd.DataFrame:
    """Calcule les indicateurs de chaque année complète des séries d'un lieu."""
    et0 = pd.Series(evapotranspiration_reference(
        meteo["T2M_MAX"], meteo["T2M_MIN"], meteo["T2MDEW"], meteo["ALLSKY_SFC_SW_DWN"], meteo["WS2M"],
        latitude, altitude, meteo.index.dayofyear.to_numpy()), index=meteo.index)
    lignes = {}
    for annee in sorted(set(pluie.index.year)):
        annee_pluie = pluie.loc[str(annee)]
        if len(annee_pluie) < 365:
            continue
        debut, fin = debut_saison(pluie, annee, regle), fin_saison(pluie, annee, regle)
        ligne = {
            "pluie_annuelle_mm": annee_pluie.sum(),
            "et0_annuelle_mm": et0.loc[str(annee)].sum(),
            "jours_35_annee": int((meteo["T2M_MAX"].loc[str(annee)] > SEUIL_CHALEUR).sum()),
            "debut_jour": debut.dayofyear if pd.notna(debut) else np.nan,
            "fin_jour": fin.dayofyear if pd.notna(fin) else np.nan,
        }
        ligne["indice_aridite"] = ligne["pluie_annuelle_mm"] / ligne["et0_annuelle_mm"]
        if pd.notna(debut) and pd.notna(fin) and fin > debut:
            saison = slice(debut, fin)
            ligne["longueur_jours"] = (fin - debut).days + 1
            ligne["pluie_saison_mm"] = pluie.loc[saison].sum()
            ligne["et0_saison_mm"] = et0.loc[saison].sum()
            ligne["bilan_saison_mm"] = ligne["pluie_saison_mm"] - ligne["et0_saison_mm"]
            ligne["jours_35_saison"] = int((meteo["T2M_MAX"].loc[saison] > SEUIL_CHALEUR).sum())
            debut_saison_pluie = pluie.loc[debut:].to_numpy()[:regle.jours_debut_saison]
            ligne["sequence_seche_debut_jours"] = plus_longue_sequence_seche(debut_saison_pluie)
        lignes[annee] = ligne
    return pd.DataFrame.from_dict(lignes, orient="index")


def pente_theil_sen(annees: np.ndarray, valeurs: np.ndarray) -> float:
    """Médiane des pentes entre toutes les paires d'années, par an."""
    pentes = [(valeurs[j] - valeurs[i]) / (annees[j] - annees[i])
              for i in range(len(valeurs)) for j in range(i + 1, len(valeurs))]
    return float(np.median(pentes))


def mann_kendall(valeurs: np.ndarray) -> tuple[float, float, float]:
    """Retourne la statistique S, sa variance corrigée des ex aequo et la probabilité bilatérale.

    La loi de S est approchée par une loi normale avec correction de continuité.
    """
    n = len(valeurs)
    s = sum(np.sign(valeurs[j] - valeurs[i]) for i in range(n) for j in range(i + 1, n))
    _, effectifs = np.unique(valeurs, return_counts=True)
    variance = (n * (n - 1) * (2 * n + 5) - sum(t * (t - 1) * (2 * t + 5) for t in effectifs)) / 18
    z = 0.0 if s == 0 else (s - np.sign(s)) / math.sqrt(variance)
    return float(s), float(variance), math.erfc(abs(z) / math.sqrt(2))


def resume_interannuel(table: pd.DataFrame) -> pd.DataFrame:
    """Médiane, quantiles 10 et 90 %, extrêmes, pente de Theil-Sen par décennie et test de Mann-Kendall."""
    lignes = {}
    for colonne in table.columns:
        serie = table[colonne].dropna()
        annees, valeurs = serie.index.to_numpy(dtype=float), serie.to_numpy(dtype=float)
        lignes[colonne] = {
            "annees": len(serie), "mediane": serie.median(), "q10": serie.quantile(0.1),
            "q90": serie.quantile(0.9), "min": serie.min(), "max": serie.max(),
            "pente_par_decennie": 10 * pente_theil_sen(annees, valeurs),
            "p_mann_kendall": mann_kendall(valeurs)[2],
        }
    return pd.DataFrame.from_dict(lignes, orient="index").round(3)


def executer() -> None:
    from .donnees import DOSSIER_POWER, RACINE, altitude_power, lire_power, pluie_lieu, telecharger_point, voisinage_imerg
    from .lieux import LIEUX

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    sortie = RACINE / "data" / "processed"
    sortie.mkdir(parents=True, exist_ok=True)
    variantes = {"recherche_1er_mars": RegleSaison(recherche_debut="03-01"), "recherche_1er_mai": RegleSaison()}
    for identifiant, lieu in LIEUX.items():
        chemin_power = telecharger_point(lieu["lat"], lieu["lon"], "power", DOSSIER_POWER)
        meteo, altitude = lire_power(chemin_power), altitude_power(chemin_power)
        cases = voisinage_imerg(lieu["lat"], lieu["lon"])
        cases_pluie = pluie_lieu(cases)
        pluie = cases_pluie["moyenne"]
        debuts = {}
        for nom, regle in variantes.items():
            table = indicateurs_annuels(pluie, meteo, lieu["lat"], altitude, regle)
            table.to_csv(sortie / f"indicateurs_{identifiant}_{nom}.csv", float_format="%.3f")
            debuts[nom] = table["debut_jour"]
            jour_recherche = pd.Timestamp(f"2001-{regle.recherche_debut}").dayofyear
            print(f"\n===== {lieu['nom']}, {nom}, altitude de la maille {altitude} m, {regle}")
            print(resume_interannuel(table).to_string())
            print(f"années sans début {table['debut_jour'].isna().sum()}, sans fin {table['fin_jour'].isna().sum()}, "
                  f"début le jour même de la recherche {(table['debut_jour'] == jour_recherche).sum()}")
        avant_mai = (debuts["recherche_1er_mars"] < 121).sum()
        print(f"\nDiagnostic {lieu['nom']}. Début avant le 1er mai selon la recherche du 1er mars, "
              f"{avant_mai} années sur {len(debuts['recherche_1er_mars'])}, que la recherche du 1er mai ne peut pas voir")
        ville = cases_pluie[cases[0]]
        annuel = lambda s: s.groupby(s.index.year)
        print(f"jours d'au moins 1 mm par an, médiane, case de la ville {annuel(ville >= SEUIL_JOUR_PLUIE).sum().median()}, "
              f"moyenne des neuf cases {annuel(pluie >= SEUIL_JOUR_PLUIE).sum().median()}")
        fins_ville = pd.Series({a: fin_saison(ville, a) for a in range(2001, 2026)})
        print(f"fin de saison avec la seule case de la ville, jour médian {fins_ville.dropna().dt.dayofyear.median()}, "
              f"années sans fin {fins_ville.isna().sum()}")
        novembre = pluie.index.month == 11
        print(f"part des jours de novembre d'au moins 1 mm, moyenne des neuf cases "
              f"{(pluie[novembre] >= SEUIL_JOUR_PLUIE).mean():.3f}")


if __name__ == "__main__":
    executer()

"""Indicateurs climatiques annuels par lieu, avec tendance et variabilité interannuelle.

Exécution depuis la racine du dépôt, qui écrit data/processed/indicateurs_<lieu>.csv et
affiche les résumés cités dans docs/donnees.md
    venv/bin/python -m moteur.indicateurs

Origine. pression_saturante, rayonnement_extraterrestre, evapotranspiration_reference et
leurs constantes viennent sans modification de src/features/indicateurs.py dans
~/African-Crop-Yield-Intelligence au commit 2b4c18c, de même que le seuil de 1 mm qui
distingue un jour de pluie d'un jour sec.

Début de saison. C'est le premier jour, à partir du 1er mars, qui ouvre trois jours
cumulant au moins 20 mm, sans séquence sèche de plus de 7 jours dans les 30 jours qui
commencent ce jour-là. Ces seuils sont attribués à Sivakumar, 1988, Agricultural and
Forest Meteorology 42, pages 295 à 305, par des sources secondaires. L'article original
n'a pas été lu, l'attribution reste donc à vérifier. Le 1er mars vaut pour les deux
villes, décision du 14 novembre 2026, et seule la première saison des pluies de Bouaké
est traitée. Les seuils sont des paramètres de RegleSaison, et chaque indicateur qui en
dépend est de niveau calcule.

Aucune fin de saison n'est calculée. La pluie, l'évapotranspiration et la température
maximale moyenne se mesurent sur la durée du cycle de chaque culture à partir du début,
par indicateurs_cycle, avec des durées sourcées en phase 4.
"""

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

SEUIL_JOUR_PLUIE = 1.0
ALBEDO = 0.23
CONSTANTE_SOLAIRE = 0.0820
STEFAN_BOLTZMANN = 4.903e-9


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
    recherche_debut: str = "03-01"
    cumul_debut_mm: float = 20.0
    jours_cumul: int = 3
    jours_controle: int = 30
    sequence_seche_admise: int = 7
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


def evapotranspiration_serie(meteo: pd.DataFrame, latitude: float, altitude: float) -> pd.Series:
    """Évapotranspiration de référence de chaque jour des séries POWER d'un lieu."""
    return pd.Series(evapotranspiration_reference(
        meteo["T2M_MAX"], meteo["T2M_MIN"], meteo["T2MDEW"], meteo["ALLSKY_SFC_SW_DWN"], meteo["WS2M"],
        latitude, altitude, meteo.index.dayofyear.to_numpy()), index=meteo.index)


def indicateurs_cycle(pluie: pd.Series, tmax: pd.Series, et0: pd.Series, debut: pd.Timestamp,
                      duree_jours: int, kc: np.ndarray | None = None,
                      mi_saison: tuple[int, int] | None = None) -> dict:
    """Indicateurs d'un cycle de culture qui commence au début de saison et dure duree_jours.

    Avec la courbe journalière kc du coefficient cultural, le besoin en eau de la culture
    est la somme de kc fois l'évapotranspiration de référence, équation 56 de FAO-56,
    comparée à la pluie du cycle. Avec mi_saison, premier et dernier jour du stade de
    mi-saison comptés depuis 1, la plus longue séquence sèche de ce stade est relevée,
    FAO-56 situant au chapitre 8 la plus forte sensibilité au manque d'eau à la floraison
    et à la formation du rendement, que son chapitre 5 place à partir de la couverture
    effective du sol. Tout est manquant si le début manque ou si le cycle dépasse la fin
    des séries.
    """
    if kc is not None and len(kc) != duree_jours:
        raise ValueError("la courbe du coefficient cultural doit couvrir chaque jour du cycle")
    noms = ["pluie_cycle_mm", "et0_cycle_mm", "bilan_cycle_mm", "etc_cycle_mm", "pluie_moins_etc_mm",
            "tmax_moyenne_cycle", "sequence_seche_cycle_jours", "sequence_seche_mi_saison_jours"]
    if pd.isna(debut):
        return dict.fromkeys(noms, np.nan)
    cycle = pd.date_range(debut, periods=duree_jours, freq="D")
    if cycle[-1] > min(pluie.index[-1], tmax.index[-1], et0.index[-1]):
        return dict.fromkeys(noms, np.nan)
    pluie_cycle, et0_cycle = pluie.loc[cycle].sum(), et0.loc[cycle].sum()
    etc_cycle = float((kc * et0.loc[cycle].to_numpy()).sum()) if kc is not None else np.nan
    return {
        "pluie_cycle_mm": pluie_cycle, "et0_cycle_mm": et0_cycle, "bilan_cycle_mm": pluie_cycle - et0_cycle,
        "etc_cycle_mm": etc_cycle, "pluie_moins_etc_mm": pluie_cycle - etc_cycle,
        "tmax_moyenne_cycle": tmax.loc[cycle].mean(),
        "sequence_seche_cycle_jours": plus_longue_sequence_seche(pluie.loc[cycle].to_numpy()),
        "sequence_seche_mi_saison_jours": plus_longue_sequence_seche(
            pluie.loc[cycle].to_numpy()[mi_saison[0] - 1:mi_saison[1]]) if mi_saison else np.nan,
    }


def indicateurs_annuels(pluie: pd.Series, meteo: pd.DataFrame, latitude: float, altitude: float,
                        regle: RegleSaison = RegleSaison()) -> pd.DataFrame:
    """Calcule les indicateurs de chaque année complète des séries d'un lieu."""
    et0 = evapotranspiration_serie(meteo, latitude, altitude)
    lignes = {}
    for annee in sorted(set(pluie.index.year)):
        annee_pluie = pluie.loc[str(annee)]
        if len(annee_pluie) < 365:
            continue
        debut = debut_saison(pluie, annee, regle)
        ligne = {
            "pluie_annuelle_mm": annee_pluie.sum(),
            "et0_annuelle_mm": et0.loc[str(annee)].sum(),
            "debut_jour": debut.dayofyear if pd.notna(debut) else np.nan,
        }
        ligne["indice_aridite"] = ligne["pluie_annuelle_mm"] / ligne["et0_annuelle_mm"]
        if pd.notna(debut):
            debut_saison_pluie = pluie.loc[debut:].to_numpy()[:regle.jours_debut_saison]
            ligne["sequence_seche_debut_jours"] = plus_longue_sequence_seche(debut_saison_pluie)
        lignes[annee] = ligne
    return pd.DataFrame.from_dict(lignes, orient="index")


def troncature_debut(debuts: pd.Series, debuts_temoin: pd.Series, regle: RegleSaison = RegleSaison()) -> pd.Series:
    """Mesure si la date de recherche coupe la distribution des débuts.

    debuts_temoin vient d'une recherche plus précoce. Un début témoin antérieur à la date
    de recherche signale une saison que la recherche retenue ne peut pas voir.
    """
    jour_recherche = pd.Timestamp(f"2001-{regle.recherche_debut}").dayofyear
    ecart = debuts.dropna() - jour_recherche
    return pd.Series({
        "annees": len(ecart),
        "debut_le_jour_de_recherche": int((ecart == 0).sum()),
        "debut_dans_les_7_jours": int((ecart < 7).sum()),
        "debut_entre_7_et_13_jours": int(((ecart >= 7) & (ecart < 14)).sum()),
        "debut_temoin_avant_la_recherche": int((debuts_temoin.dropna() < jour_recherche).sum()),
    })


def ecart_recherches(debuts_retenus: pd.Series, debuts_precoces: pd.Series) -> pd.Series:
    """Compare année par année deux dates de recherche du début, en jours de l'année."""
    communs = pd.concat({"retenu": debuts_retenus, "precoce": debuts_precoces}, axis=1).dropna()
    ecart = communs["retenu"] - communs["precoce"]
    return pd.Series({
        "annees": len(ecart),
        "annees_differentes": int((ecart != 0).sum()),
        "mediane_retenue": communs["retenu"].median(),
        "mediane_precoce": communs["precoce"].median(),
        "ecart_moyen_jours": ecart.mean(),
        "ecart_median_jours": ecart.median(),
        "ecart_max_jours": ecart.max(),
    })


def indicateurs_cultures(pluie: pd.Series, meteo: pd.DataFrame, et0: pd.Series, debuts: pd.Series,
                         courbes_kc: dict[str, np.ndarray],
                         mi_saisons: dict[str, tuple[int, int]] | None = None,
                         semis: dict[str, str] | None = None) -> pd.DataFrame:
    """Indicateurs de cycle de chaque culture et de chaque année, à partir du début de saison de l'année.

    La durée du cycle d'une culture est la longueur de sa courbe de coefficient cultural.
    semis associe à une culture une date fixe au format MM-JJ. Elle est alors semée à cette
    date, ou au début de saison s'il survient plus tard, les autres cultures restant semées
    au début de saison.
    """
    lignes = []
    for culture, kc in courbes_kc.items():
        for annee, jour in debuts.items():
            debut = pd.NaT if pd.isna(jour) else pd.Timestamp(f"{annee}-01-01") + pd.Timedelta(days=int(jour) - 1)
            if semis and culture in semis and pd.notna(debut):
                debut = max(debut, pd.Timestamp(f"{annee}-{semis[culture]}"))
            lignes.append({"culture": culture, "annee": annee, "duree_jours": len(kc),
                           **indicateurs_cycle(pluie, meteo["T2M_MAX"], et0, debut, len(kc), kc,
                                               (mi_saisons or {}).get(culture))})
    return pd.DataFrame(lignes)


def resume_cultures(table: pd.DataFrame) -> pd.DataFrame:
    """Médiane et quantiles 10 et 90 % entre années des indicateurs de cycle, par culture."""
    colonnes = ["pluie_cycle_mm", "etc_cycle_mm", "pluie_moins_etc_mm", "tmax_moyenne_cycle",
                "sequence_seche_cycle_jours"]
    groupes = table.groupby("culture", sort=False)
    resume = pd.concat({
        "duree": groupes["duree_jours"].first(),
        "annees": groupes["pluie_cycle_mm"].count(),
        "annees_pluie_sous_besoin": groupes["pluie_moins_etc_mm"].apply(lambda s: int((s < 0).sum())),
        **{f"{c} mediane": groupes[c].median() for c in colonnes},
        **{f"{c} q10": groupes[c].quantile(0.1) for c in colonnes},
        **{f"{c} q90": groupes[c].quantile(0.9) for c in colonnes},
    }, axis=1)
    return resume.round(1)


def pente_theil_sen(annees: np.ndarray, valeurs: np.ndarray) -> float:
    """Médiane des pentes entre toutes les paires d'années, par an."""
    pentes = [(valeurs[j] - valeurs[i]) / (annees[j] - annees[i])
              for i in range(len(valeurs)) for j in range(i + 1, len(valeurs))]
    return float(np.median(pentes))


def tendance_theil_sen(serie: pd.Series) -> pd.Series:
    """Droite de Theil-Sen d'une série annuelle, ordonnée à l'origine médiane des résidus."""
    serie = serie.dropna()
    annees, valeurs = serie.index.to_numpy(dtype=float), serie.to_numpy(dtype=float)
    pente = pente_theil_sen(annees, valeurs)
    origine = float(np.median(valeurs - pente * annees))
    return pd.Series(origine + pente * annees, index=serie.index)


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
    from .cultures import CULTURES, courbes_kc_comparees, mi_saisons_comparees
    from .lieux import LIEUX_ETUDE as LIEUX

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    sortie = RACINE / "data" / "processed"
    sortie.mkdir(parents=True, exist_ok=True)
    regle, temoin, fevrier = RegleSaison(), RegleSaison(recherche_debut="01-01"), RegleSaison(recherche_debut="02-01")
    for identifiant, lieu in LIEUX.items():
        chemin_power = telecharger_point(lieu["lat"], lieu["lon"], "power", DOSSIER_POWER)
        meteo, altitude = lire_power(chemin_power), altitude_power(chemin_power)
        pluie = pluie_lieu(voisinage_imerg(lieu["lat"], lieu["lon"]))["moyenne"]
        table = indicateurs_annuels(pluie, meteo, lieu["lat"], altitude, regle)
        table.to_csv(sortie / f"indicateurs_{identifiant}.csv", float_format="%.3f")
        print(f"\n===== {lieu['nom']}, altitude de la maille {altitude} m, {regle}")
        print(resume_interannuel(table).to_string())
        debuts_temoin = indicateurs_annuels(pluie, meteo, lieu["lat"], altitude, temoin)["debut_jour"]
        print("\nTroncature par la date de recherche, avec une recherche témoin à partir du 1er janvier")
        print(troncature_debut(table["debut_jour"], debuts_temoin, regle).to_string())
        print("jours de début, recherche du 1er mars", sorted(table["debut_jour"].dropna().astype(int).tolist()))
        print("jours de début, recherche témoin", sorted(debuts_temoin.dropna().astype(int).tolist()))
        debuts_fevrier = indicateurs_annuels(pluie, meteo, lieu["lat"], altitude, fevrier)["debut_jour"]
        print("\nRecherche du 1er mars comparée à une recherche du 1er février, jours de l'année")
        print(ecart_recherches(table["debut_jour"], debuts_fevrier).to_string())
        print("début par année, 1er mars puis 1er février", {a: (int(table["debut_jour"][a]), int(debuts_fevrier[a]))
                                                             for a in table.index if table["debut_jour"][a] != debuts_fevrier[a]})
        courbes = courbes_kc_comparees()
        cycles = indicateurs_cultures(pluie, meteo, evapotranspiration_serie(meteo, lieu["lat"], altitude),
                                      table["debut_jour"], courbes, mi_saisons_comparees())
        cycles.to_csv(sortie / f"cycles_{identifiant}.csv", index=False, float_format="%.3f")
        print("\nIndicateurs sur le cycle de chaque culture, durée et coefficient cultural FAO-56, début du 1er mars")
        print(resume_cultures(cycles).to_string())
        print("cultures hors comparaison chiffrée", [c for c in CULTURES if c not in courbes])


if __name__ == "__main__":
    executer()

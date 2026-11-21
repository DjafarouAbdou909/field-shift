"""Alerte de végétation à partir de l'indice NDVI des produits NASA HLS.

La végétation d'un point est jugée plus faible que d'habitude quand la médiane de ses
NDVI sans nuages, dans une fenêtre de jours autour de la date, tombe sous le 10e centile
des NDVI sans nuages des autres années dans la même fenêtre de calendrier. Le 10e
centile, la demi-fenêtre de 8 jours et les minimums de 20 observations de référence sur
5 années sont des choix de conception déclarés, décision du 14 novembre 2026. Sous ces
minimums, l'alerte est indisponible. Aucune cause n'est jamais déduite.

Végétation de la zone. Décision du responsable du 15 novembre 2026. Les 50 points HLS de
chaque ville sont tirés dans la végétation de toute la zone, MCD12Q1 n'y voyant presque
aucun champ. Pour chaque date, le NDVI de la zone est la médiane des observations sans
nuages des 50 points, Landsat et Sentinel-2 réunis, quand au moins 10 observations sans
nuages existent ce jour-là, seuil déclaré comme les autres. L'alerte porte sur la dernière
date ainsi disponible. Premier calcul du 15 novembre 2026, sur les données AppEEARS
reçues le même jour, d'avril 2013 au 4 novembre 2026. Korhogo, 322 dates retenues,
végétation normale le 2 novembre 2026, NDVI 0,654 pour un seuil de 0,601 tiré de 30
observations de 13 années. Bouaké, plus nuageuse, 202 dates retenues, alerte
indisponible le 4 novembre 2026, 14 observations de référence seulement pour un minimum
de 20.

Masque des nuages. La couche Fmask des produits HLSL30.020 et HLSS30.020 code le nuage
au bit 1, le voisinage d'un nuage ou d'une ombre au bit 2, l'ombre au bit 3, la neige au
bit 4, l'eau au bit 5 et le niveau d'aérosols aux bits 6 et 7, selon le décodage de
l'API AppEEARS, https://appeears.earthdatacloud.nasa.gov/api/quality/HLSL30.020/Fmask,
lu le 14 novembre 2026. Une observation est gardée si les bits 1 à 5 sont nuls et si
les aérosols ne sont pas au niveau élevé, 3.
"""

import functools

import numpy as np
import pandas as pd

from .contrat import AlerteVegetation, Lieu
from .sources import SOURCES

CENTILE = 0.1
DEMI_FENETRE_JOURS = 8
OBSERVATIONS_MIN = 20
ANNEES_MIN = 5
AEROSOLS_ELEVES = 3
COUCHES_HLS = [("HLSL30_VI.020", "NDVI"), ("HLSS30_VI.020", "NDVI"), ("HLSL30.020", "Fmask"), ("HLSS30.020", "Fmask")]


def observation_claire(fmask: pd.Series) -> pd.Series:
    """Vrai si ni nuage, ni voisinage de nuage, ni ombre, ni neige, ni eau, et des aérosols qui ne sont pas élevés."""
    codes = fmask.astype(int).to_numpy()
    claire = (((codes >> 1) & 0b11111) == 0) & (((codes >> 6) & 0b11) != AEROSOLS_ELEVES)
    return pd.Series(claire, index=fmask.index)


def observations_claires(table: pd.DataFrame) -> pd.Series:
    """NDVI sans nuages et dans ses bornes, indexé par date, à partir de colonnes date, ndvi et fmask."""
    valides = table["ndvi"].between(-1, 1) & table["fmask"].notna()
    gardees = table[valides & observation_claire(table["fmask"].where(valides, 0))]
    return gardees.set_index(pd.to_datetime(gardees["date"]))["ndvi"].sort_index()


def dans_la_fenetre(dates: pd.DatetimeIndex, cible: pd.Timestamp, demi_fenetre: int) -> np.ndarray:
    """Vrai pour les dates dont le jour de l'année est à au plus demi_fenetre jours de celui de la cible."""
    ecart = np.abs(dates.dayofyear - cible.dayofyear)
    return np.minimum(ecart, 365 - ecart) <= demi_fenetre


def etat_vegetation(ndvi: pd.Series, date: str, demi_fenetre: int = DEMI_FENETRE_JOURS,
                    observations_min: int = OBSERVATIONS_MIN, annees_min: int = ANNEES_MIN) -> dict:
    """Compare la végétation de l'année de la date aux mêmes dates des autres années."""
    cible = pd.Timestamp(date)
    fenetre = ndvi[dans_la_fenetre(ndvi.index, cible, demi_fenetre)]
    courantes = fenetre[(fenetre.index.year == cible.year) & (fenetre.index <= cible + pd.Timedelta(days=demi_fenetre))]
    reference = fenetre[fenetre.index.year != cible.year]
    etat = {"observations_reference": int(len(reference)), "annees_reference": int(reference.index.year.nunique()),
            "observations_courantes": int(len(courantes)), "valeur": None, "seuil": None}
    if courantes.empty or etat["observations_reference"] < observations_min or etat["annees_reference"] < annees_min:
        return {**etat, "statut": "indisponible"}
    valeur, seuil = float(courantes.median()), float(reference.quantile(CENTILE))
    return {**etat, "valeur": valeur, "seuil": seuil, "statut": "faible" if valeur < seuil else "normale"}


def taux_d_alertes(ndvi: pd.Series, dates: list[str], **reglages) -> pd.Series:
    """Part des alertes faibles parmi les états disponibles, et nombre d'états évalués, sur des dates passées."""
    statuts = pd.Series([etat_vegetation(ndvi, d, **reglages)["statut"] for d in dates])
    disponibles = statuts[statuts != "indisponible"]
    return pd.Series({"etats_evalues": len(statuts), "etats_disponibles": len(disponibles),
                      "part_faible": float((disponibles == "faible").mean()) if len(disponibles) else np.nan})


TEXTES = {"faible": "La végétation de votre zone est plus faible que d'habitude pour cette période.",
          "normale": "La végétation de votre zone est dans les valeurs habituelles pour cette période.",
          "indisponible": "Pas assez d'images sans nuages pour comparer la végétation de votre zone à cette période."}
AVERTISSEMENT = ("Comparaison d'images satellitaires de 30 m aux mêmes dates des autres années, sans aucune cause "
                 "déduite. À vérifier au champ avec votre conseiller ANADER.")


def construire_alerte(identifiant: str, date: str, etat: dict) -> AlerteVegetation:
    """Alerte du contrat à partir de l'état calculé par etat_vegetation, valeurs arrondies au millième."""
    from .lieux import LIEUX

    lieu = LIEUX[identifiant]
    arrondi = lambda x: None if x is None else round(x, 3)
    return AlerteVegetation(
        donnees_fictives=False, lieu=Lieu(id=identifiant, nom=lieu["nom"], lat=lieu["lat"], lon=lieu["lon"]),
        date=date, indice="NDVI", statut=etat["statut"], valeur=arrondi(etat["valeur"]), seuil=arrondi(etat["seuil"]),
        observations_reference=etat["observations_reference"], annees_reference=etat["annees_reference"],
        texte=TEXTES[etat["statut"]], niveau="calcule", source=SOURCES["HLS"], avertissement=AVERTISSEMENT)


# Classes IGBP de MCD12Q1 exclues du suivi, zones bâties, neige et glace, sol nu, eau.
CLASSES_EXCLUES = {13, 15, 16, 17}
POINTS_HLS = 50
GRAINE_POINTS = 2026


def points_de_vegetation(table: pd.DataFrame, nombre: int = POINTS_HLS, graine: int = GRAINE_POINTS) -> list[dict]:
    """Points à suivre par HLS, tirés parmi ceux que MCD12Q1 n'a jamais classés hors végétation.

    Décision du responsable du 15 novembre 2026. Autour de Korhogo, MCD12Q1 classe environ
    97 % des points en prairies et presque aucun en cultures, les petits champs mêlés à la
    savane échappant sans doute à sa résolution de 500 m, si bien que l'alerte suit la
    végétation de toute la zone et non les seuls champs. table est le fichier de résultats
    AppEEARS de MCD12Q1, avec les colonnes ID, Category, Latitude, Longitude et la classe.
    """
    classe = [c for c in table.columns if c.endswith("LC_Type1")][0]
    exclus = set(table.loc[table[classe].isin(CLASSES_EXCLUES), "ID"])
    candidats = table[~table["ID"].isin(exclus)].drop_duplicates("ID").sort_values("ID")
    tires = candidats.sample(n=min(nombre, len(candidats)), random_state=graine).sort_values("ID")
    return [{"id": r.ID, "category": r.Category, "latitude": float(r.Latitude), "longitude": float(r.Longitude)}
            for r in tires.itertuples()]


def requete_hls(nom: str, points: list[dict], fin: str) -> dict:
    """Tâche AppEEARS des quatre couches HLS sur des points, depuis le début de Landsat dans HLS, date MM-DD-YYYY."""
    from .appeears import requete_points
    return requete_points(nom, COUCHES_HLS, points, "04-11-2013", fin)



DOSSIER_HLS = "data/raw/appeears"
CAPTEURS_HLS = ("HLSL30", "HLSS30")
OBSERVATIONS_CLAIRES_PAR_DATE = 10
SANS_VALEUR = -19999


def lire_hls(identifiant: str, dossier: str = DOSSIER_HLS) -> pd.DataFrame:
    """NDVI et Fmask des points HLS d'une ville, colonnes ID, date, ndvi et fmask, Landsat et Sentinel-2 réunis."""
    from pathlib import Path

    tables = []
    for capteur in CAPTEURS_HLS:
        base = Path(dossier) / f"hls_{identifiant}" / f"hls-{identifiant}-{capteur}"
        indice = pd.read_csv(f"{base}-VI-020-results.csv")
        masque = pd.read_csv(f"{base}-020-results.csv",
                             usecols=lambda c: c in ("ID", "Date", "HLS_Tile") or c.endswith("_Fmask"))
        indice = indice.rename(columns={indice.columns[-1]: "ndvi"})
        masque = masque.rename(columns={[c for c in masque.columns if c.endswith("_Fmask")][0]: "fmask"})
        tables.append(indice.merge(masque, on=["ID", "Date", "HLS_Tile"], how="inner"))
    table = pd.concat(tables, ignore_index=True).rename(columns={"Date": "date"})
    table["ndvi"] = table["ndvi"].where(table["ndvi"] != SANS_VALEUR)
    return table[["ID", "date", "ndvi", "fmask"]]


def ndvi_de_la_zone(table: pd.DataFrame, minimum: int = OBSERVATIONS_CLAIRES_PAR_DATE) -> pd.Series:
    """Médiane par date des NDVI sans nuages des points de la zone, pour les dates assez observées."""
    claires = observations_claires(table)
    par_date = claires.groupby(level=0).agg(["size", "median"])
    return par_date.loc[par_date["size"] >= minimum, "median"].rename("ndvi")


@functools.cache
def alerte_du_lieu(identifiant: str) -> AlerteVegetation:
    """Alerte de végétation de la zone d'une ville, à la dernière date d'images HLS disponible."""
    serie = ndvi_de_la_zone(lire_hls(identifiant))
    if serie.empty:
        raise ValueError(f"aucune date HLS assez observée pour {identifiant}")
    date = str(serie.index.max().date())
    return construire_alerte(identifiant, date, etat_vegetation(serie, date))


def executer() -> None:
    from pathlib import Path

    from .lieux import LIEUX

    for identifiant in [i for i in LIEUX if (Path(DOSSIER_HLS) / f"hls_{i}").is_dir()]:
        serie = ndvi_de_la_zone(lire_hls(identifiant))
        alerte = alerte_du_lieu(identifiant)
        dates = [str(d.date()) for d in serie.index if d.year < serie.index.max().year]
        print(f"{identifiant}, {len(serie)} dates retenues, {alerte.date}, {alerte.statut}, valeur {alerte.valeur}, "
              f"seuil {alerte.seuil}, {alerte.observations_reference} observations de référence sur "
              f"{alerte.annees_reference} années")
        print("  taux d'alertes sur les dates passées", taux_d_alertes(serie, dates).round(3).to_dict())


if __name__ == "__main__":
    executer()

"""Alerte de végétation à partir de l'indice NDVI des produits NASA HLS.

La végétation d'un point est jugée plus faible que d'habitude quand la médiane de ses
NDVI sans nuages, dans une fenêtre de jours autour de la date, tombe sous le 10e centile
des NDVI sans nuages des autres années dans la même fenêtre de calendrier. Le 10e
centile, la demi-fenêtre de 8 jours et les minimums de 20 observations de référence sur
5 années sont des choix de conception déclarés, décision du 14 novembre 2026. Sous ces
minimums, l'alerte est indisponible. Aucune cause n'est jamais déduite.

Masque des nuages. La couche Fmask des produits HLSL30.020 et HLSS30.020 code le nuage
au bit 1, le voisinage d'un nuage ou d'une ombre au bit 2, l'ombre au bit 3, la neige au
bit 4, l'eau au bit 5 et le niveau d'aérosols aux bits 6 et 7, selon le décodage de
l'API AppEEARS, https://appeears.earthdatacloud.nasa.gov/api/quality/HLSL30.020/Fmask,
lu le 14 novembre 2026. Une observation est gardée si les bits 1 à 5 sont nuls et si
les aérosols ne sont pas au niveau élevé, 3.
"""

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


def requete_hls(nom: str, points: list[dict], fin: str) -> dict:
    """Tâche AppEEARS des quatre couches HLS sur des points, depuis le début de Landsat dans HLS, date MM-DD-YYYY."""
    from .appeears import requete_points
    return requete_points(nom, COUCHES_HLS, points, "04-11-2013", fin)


"""Téléchargement vérifié des séries journalières NASA POWER et IMERG pour les lieux couverts.

Origine. empreinte_sha256 vient de src/data/load.py, consigner de
src/features/acquisition.py, telecharger_point et lire_power de telecharger_maille et
lire_power dans src/features/climat.py, tous dans ~/African-Crop-Yield-Intelligence au
commit 2b4c18c. Modifications, une requête par point au lieu d'une grille de mailles,
période 2001 à 2025, GWETROOT retiré, registre propre à ce dépôt.

Constats de la phase 2, détaillés dans docs/donnees.md. IMERG_PRECTOT est servi à la
résolution native d'IMERG, 0,1 degré, et en temps universel seulement. Les paramètres
de MERRA-2 et de CERES sont communs à toute une maille de 0,5 par 0,625 degré.
PRECTOTCORR n'est téléchargé que pour la comparaison avec IMERG, jamais comme pluie.
"""

import csv
import gzip
import hashlib
import io
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

URL_POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
DEBUT = "20010101"
FIN = "20251231"
VALEUR_MANQUANTE = -999.0
PRODUITS = {
    "power": {"parametres": ["T2M_MAX", "T2M_MIN", "T2MDEW", "ALLSKY_SFC_SW_DWN", "WS2M", "PRECTOTCORR"],
              "temps": "LST"},
    "imerg": {"parametres": ["IMERG_PRECTOT"], "temps": "UTC"},
}
RACINE = Path(__file__).resolve().parents[1]
DOSSIER_POWER = RACINE / "data" / "raw" / "power"
REGISTRE = DOSSIER_POWER / "registre.csv"
COLONNES_REGISTRE = ["fichier", "url", "date_telechargement", "octets", "sha256"]


def empreinte_sha256(chemin: Path) -> str:
    empreinte = hashlib.sha256()
    with open(chemin, "rb") as fichier:
        for bloc in iter(lambda: fichier.read(1 << 20), b""):
            empreinte.update(bloc)
    return empreinte.hexdigest()


def consigner(chemin: Path, url: str, registre: Path = REGISTRE) -> None:
    """Ajoute un fichier téléchargé au registre, avec sa taille et son empreinte."""
    nouveau = not registre.exists()
    with open(registre, "a", newline="", encoding="utf-8") as fichier:
        ecrivain = csv.writer(fichier)
        if nouveau:
            ecrivain.writerow(COLONNES_REGISTRE)
        ecrivain.writerow([
            chemin.relative_to(registre.parent).as_posix(), url,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            chemin.stat().st_size, empreinte_sha256(chemin),
        ])


def nom_fichier(produit: str, latitude: float, longitude: float) -> str:
    return f"{produit}_{latitude:+07.3f}_{longitude:+08.3f}.csv.gz"


def reponse_complete(texte: str, debut: str, fin: str) -> bool:
    """Vrai si la réponse contient l'en-tête et une ligne par jour de la période."""
    if "-END HEADER-" not in texte:
        return False
    lignes = texte.split("-END HEADER-", 1)[1].strip().splitlines()
    jours = (pd.Timestamp(fin) - pd.Timestamp(debut)).days + 1
    return len(lignes) == jours + 1


def telecharger_point(latitude: float, longitude: float, produit: str, dossier: Path = DOSSIER_POWER,
                      registre: Path = REGISTRE, debut: str = DEBUT, fin: str = FIN,
                      tentatives: int = 6, attente: float = 5.0) -> Path:
    """Télécharge la série d'un point si elle est absente, la compresse et la consigne.

    Le fichier n'est écrit que si la réponse est complète, ce qui évite qu'une réponse
    tronquée par le serveur passe pour une série courte.
    """
    choix = PRODUITS[produit]
    chemin = dossier / nom_fichier(produit, latitude, longitude)
    if chemin.exists():
        return chemin
    parametres = {
        "parameters": ",".join(choix["parametres"]), "community": "AG",
        "latitude": latitude, "longitude": longitude, "start": debut, "end": fin,
        "format": "CSV", "time-standard": choix["temps"],
    }
    for tentative in range(tentatives):
        try:
            reponse = requests.get(URL_POWER, params=parametres, timeout=120)
            if reponse.status_code == 200 and reponse_complete(reponse.text, debut, fin):
                dossier.mkdir(parents=True, exist_ok=True)
                temporaire = chemin.with_name(chemin.name + ".partiel")
                with gzip.open(temporaire, "wt", encoding="utf-8") as fichier:
                    fichier.write(reponse.text)
                temporaire.rename(chemin)
                consigner(chemin, reponse.url, registre)
                return chemin
        except requests.RequestException:
            pass
        time.sleep(attente * 2 ** tentative)
    raise RuntimeError(f"série {produit} indisponible au point {latitude}, {longitude}")


URL_GHCN = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/{station}.csv"
DOSSIER_GHCN = RACINE / "data" / "raw" / "ghcn"
# Identifiant et coordonnées tirés de ghcnd-stations.txt de NOAA NCEI, consulté le 14 novembre 2026.
STATIONS_GHCN = {"korhogo": ("IVM00065536", 9.387, -5.557), "bouake": ("IV000005555", 7.68, -5.03)}


def telecharger_station(station: str, dossier: Path = DOSSIER_GHCN) -> Path:
    """Télécharge la série GHCN-Daily d'une station si elle est absente et la consigne."""
    chemin = dossier / f"{station}.csv"
    if chemin.exists():
        return chemin
    url = URL_GHCN.format(station=station)
    reponse = requests.get(url, timeout=120)
    reponse.raise_for_status()
    dossier.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(reponse.content)
    consigner(chemin, url, dossier / "registre.csv")
    return chemin


def lire_pluie_station(chemin: Path) -> pd.Series:
    """Retourne la pluie journalière d'une station en mm, GHCN-Daily la diffusant en dixièmes de mm."""
    donnees = pd.read_csv(chemin, usecols=["DATE", "PRCP"], low_memory=False).dropna()
    return (donnees.set_index(pd.to_datetime(donnees["DATE"]).rename("date"))["PRCP"] / 10).rename("station")


def lire_power(chemin: Path) -> pd.DataFrame:
    """Lit une série POWER, remplace le code -999 par une valeur manquante et date chaque ligne."""
    with gzip.open(chemin, "rt", encoding="utf-8") as fichier:
        texte = fichier.read()
    donnees = pd.read_csv(io.StringIO(texte.split("-END HEADER-", 1)[1]))
    donnees = donnees.replace(VALEUR_MANQUANTE, np.nan)
    date = pd.to_datetime(donnees["YEAR"].astype(str), format="%Y") + pd.to_timedelta(donnees["DOY"] - 1, unit="D")
    return donnees.drop(columns=["YEAR", "DOY"]).set_index(date.rename("date"))

"""Séries journalières NASA POWER, dont la pluie GPM IMERG, pour chaque point."""

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from .config import DOSSIER_DONNEES, Point

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
VALEUR_MANQUANTE = -999.0
DOSSIER = DOSSIER_DONNEES / "raw" / "power"


def chemin(point: Point) -> Path:
    return DOSSIER / f"{point.id}.json"


def url(point: Point, config: dict) -> str:
    periode, power = config["periode"], config["power"]
    return URL + "?" + urlencode({
        "parameters": ",".join(power["parametres"]), "community": power["communaute"],
        "latitude": point.lat, "longitude": point.lon,
        "start": periode["debut"].replace("-", ""), "end": periode["fin"].replace("-", ""),
        "time-standard": power["standard_temps"], "format": "JSON",
    })


def jours_attendus(config: dict) -> int:
    debut, fin = (date.fromisoformat(config["periode"][c]) for c in ("debut", "fin"))
    return (fin - debut).days + 1


def controler(contenu: dict, config: dict) -> dict[str, int]:
    """Vérifie une réponse POWER et retourne le nombre de jours manquants par paramètre."""
    series = contenu.get("properties", {}).get("parameter", {})
    absents = set(config["power"]["parametres"]) - set(series)
    if absents:
        raise ValueError(f"paramètres absents de la réponse POWER {sorted(absents)}")
    manquants = {}
    for parametre, valeurs in series.items():
        if len(valeurs) != jours_attendus(config):
            raise ValueError(f"{parametre} compte {len(valeurs)} jours au lieu de {jours_attendus(config)}")
        manquants[parametre] = sum(v == VALEUR_MANQUANTE for v in valeurs.values())
    return manquants


def lire(point: Point) -> dict:
    return json.loads(chemin(point).read_text())

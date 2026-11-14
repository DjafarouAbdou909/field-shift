"""Lecture de config/projet.toml et grille de points de chaque lieu."""

import math
import tomllib
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_DONNEES = RACINE / "data"


@dataclass(frozen=True)
class Point:
    id: str
    lieu: str
    lat: float
    lon: float


def charger(chemin: Path = RACINE / "config" / "projet.toml") -> dict:
    with open(chemin, "rb") as fichier:
        return tomllib.load(fichier)


def centre_case(valeur: float, pas: float) -> float:
    return round((math.floor(valeur / pas) + 0.5) * pas, 6)


def points(config: dict) -> list[Point]:
    """Grille de points de chaque lieu, centrée sur la case qui contient la ville."""
    pas, rayon = config["grille"]["pas"], config["grille"]["rayon"]
    resultat = []
    for lieu in config["lieux"]:
        lat0, lon0 = centre_case(lieu["lat"], pas), centre_case(lieu["lon"], pas)
        numero = 0
        for i in range(-rayon, rayon + 1):
            for j in range(-rayon, rayon + 1):
                numero += 1
                resultat.append(Point(f"{lieu['id']}_{numero:02d}", lieu["id"],
                                      round(lat0 + i * pas, 6), round(lon0 + j * pas, 6)))
    return resultat

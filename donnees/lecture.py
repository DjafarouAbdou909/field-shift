"""Lecture des extractions AppEEARS, une ligne par point et par date."""

import csv
import math

from . import appeears


def colonne(entetes: list[str], couche: str) -> str | None:
    """Colonne d'une couche dans un CSV AppEEARS, dont le nom se termine par le nom de la couche."""
    trouvees = [e for e in entetes if e.endswith(couche)]
    return trouvees[0] if len(trouvees) == 1 else None


def lire_tache(nom: str) -> list[dict]:
    lignes = []
    for fichier in appeears.lire_taches().get(nom, {}).get("fichiers", []):
        with open(appeears.DOSSIER / nom / fichier, newline="", encoding="utf-8") as f:
            lignes += list(csv.DictReader(f))
    return lignes


def valeurs(lignes: list[dict], couche: str, lieu: str | None = None) -> list[float]:
    if not lignes:
        return []
    nom = colonne(list(lignes[0]), couche)
    if nom is None:
        raise KeyError(f"colonne introuvable ou ambiguë pour la couche {couche}")
    resultat = []
    for ligne in lignes:
        if lieu and ligne.get("Category") != lieu:
            continue
        try:
            v = float(ligne[nom])
        except (TypeError, ValueError):
            continue
        if not math.isnan(v):
            resultat.append(v)
    return resultat


def resume_appeears(config: dict) -> None:
    """Affiche, pour chaque extraction, le nombre de lignes et l'étendue de chaque couche par lieu."""
    for tache in config["appeears"]:
        lignes = lire_tache(tache["nom"])
        if not lignes:
            print(f"{tache['nom']}, pas encore disponible, relancer python -m donnees")
            continue
        print(f"{tache['nom']}, {len(lignes)} lignes, colonnes {list(lignes[0])}")
        for _, couche in tache["couches"]:
            for lieu in sorted({l.get('Category') for l in lignes}):
                v = valeurs(lignes, couche, lieu)
                if v:
                    print(f"  {couche} {lieu} n {len(v)} min {min(v):g} max {max(v):g} moyenne {sum(v) / len(v):.4g}")

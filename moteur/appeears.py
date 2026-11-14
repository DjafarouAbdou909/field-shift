"""Extractions par points avec l'API AppEEARS de la NASA, pour MCD12Q1, MOD13Q1, SMAP et SRTM.

L'authentification utilise le compte NASA Earthdata déclaré dans ~/.netrc pour la machine
urs.earthdata.nasa.gov. Les identifiants et le jeton ne sont jamais affichés ni écrits dans
le dépôt. Chaque tâche soumise est consignée dans data/raw/appeears/taches.json, et chaque
fichier téléchargé est vérifié contre l'empreinte SHA-256 publiée par AppEEARS, puis
consigné dans data/raw/appeears/registre.csv.

Documentation de l'API https://appeears.earthdatacloud.nasa.gov/api/, lue le 14 novembre
2026. Dates au format MM-DD-YYYY, jeton valable environ 48 heures.
"""

import json
import netrc
import os
from pathlib import Path

import numpy as np
import requests

from .donnees import RACINE, consigner, empreinte_sha256

URL_API = "https://appeears.earthdatacloud.nasa.gov/api"
MACHINE_EARTHDATA = "urs.earthdata.nasa.gov"
DOSSIER_APPEEARS = RACINE / "data" / "raw" / "appeears"
JOURNAL_TACHES = DOSSIER_APPEEARS / "taches.json"


def identifiants(fichier: str = "~/.netrc") -> tuple[str, str]:
    """Lit l'identifiant et le mot de passe Earthdata, sans jamais les afficher."""
    entree = netrc.netrc(os.path.expanduser(fichier)).authenticators(MACHINE_EARTHDATA)
    if entree is None:
        raise RuntimeError(f"aucune entrée {MACHINE_EARTHDATA} dans {fichier}")
    return entree[0], entree[2]


def connexion() -> str:
    reponse = requests.post(f"{URL_API}/login", auth=identifiants(), headers={"Content-Length": "0"}, timeout=60)
    reponse.raise_for_status()
    return reponse.json()["token"]


def entetes(jeton: str) -> dict:
    return {"Authorization": f"Bearer {jeton}"}


def grille_points(categorie: str, latitude: float, longitude: float, demi_cote: float = 0.15,
                  pas: float = 0.01) -> list[dict]:
    """Points d'une grille carrée centrée sur un point, identifiés par leur rang."""
    decalages = np.round(np.arange(-demi_cote, demi_cote + pas / 2, pas), 6)
    return [{"id": f"{categorie}_{k:04d}", "category": categorie,
             "latitude": round(latitude + dy, 4), "longitude": round(longitude + dx, 4)}
            for k, (dy, dx) in enumerate((dy, dx) for dy in decalages for dx in decalages)]


def requete_points(nom: str, couches: list[tuple[str, str]], points: list[dict], debut: str, fin: str) -> dict:
    """Corps d'une tâche par points, dates au format MM-DD-YYYY."""
    return {"task_type": "point", "task_name": nom,
            "params": {"dates": [{"startDate": debut, "endDate": fin}],
                       "layers": [{"product": produit, "layer": couche} for produit, couche in couches],
                       "coordinates": points}}


def consigner_tache(nom: str, identifiant: str, requete: dict, journal: Path = JOURNAL_TACHES) -> None:
    journal.parent.mkdir(parents=True, exist_ok=True)
    taches = json.loads(journal.read_text(encoding="utf-8")) if journal.exists() else {}
    taches[nom] = {"task_id": identifiant, "couches": requete["params"]["layers"],
                   "dates": requete["params"]["dates"], "points": len(requete["params"]["coordinates"])}
    journal.write_text(json.dumps(taches, indent=1, ensure_ascii=False), encoding="utf-8")


def soumettre(jeton: str, requete: dict, journal: Path = JOURNAL_TACHES) -> str:
    """Soumet une tâche, sauf si une tâche du même nom est déjà consignée, et retourne son identifiant."""
    if journal.exists():
        taches = json.loads(journal.read_text(encoding="utf-8"))
        if requete["task_name"] in taches:
            return taches[requete["task_name"]]["task_id"]
    reponse = requests.post(f"{URL_API}/task", json=requete, headers=entetes(jeton), timeout=120)
    reponse.raise_for_status()
    identifiant = reponse.json()["task_id"]
    consigner_tache(requete["task_name"], identifiant, requete, journal)
    return identifiant


def etat(jeton: str, identifiant: str) -> str:
    reponse = requests.get(f"{URL_API}/task/{identifiant}", headers=entetes(jeton), timeout=60)
    reponse.raise_for_status()
    return reponse.json()["status"]


def telecharger_resultats(jeton: str, identifiant: str, dossier: Path) -> list[Path]:
    """Télécharge les fichiers CSV d'une tâche terminée, vérifie leur empreinte et les consigne."""
    liste = requests.get(f"{URL_API}/bundle/{identifiant}", headers=entetes(jeton), timeout=60)
    liste.raise_for_status()
    dossier.mkdir(parents=True, exist_ok=True)
    chemins = []
    for fichier in liste.json()["files"]:
        if not fichier["file_name"].endswith(".csv"):
            continue
        chemin = dossier / Path(fichier["file_name"]).name
        if not chemin.exists():
            url = f"{URL_API}/bundle/{identifiant}/{fichier['file_id']}"
            reponse = requests.get(url, headers=entetes(jeton), timeout=300, allow_redirects=True)
            reponse.raise_for_status()
            temporaire = chemin.with_name(chemin.name + ".partiel")
            temporaire.write_bytes(reponse.content)
            if empreinte_sha256(temporaire) != fichier["sha256"]:
                temporaire.unlink()
                raise ValueError(f"empreinte inattendue pour {chemin.name}")
            temporaire.rename(chemin)
            consigner(chemin, url, DOSSIER_APPEEARS / "registre.csv")
        chemins.append(chemin)
    return chemins


def taches_occupation_du_sol() -> list[dict]:
    """Une tâche MCD12Q1 par ville, sur une grille qui recouvre les neuf cases IMERG de la ville."""
    from .lieux import LIEUX
    from .donnees import centre_case_imerg
    requetes = []
    for identifiant, lieu in LIEUX.items():
        latitude, longitude = centre_case_imerg(lieu["lat"], lieu["lon"])
        requetes.append(requete_points(f"mcd12q1_{identifiant}", [("MCD12Q1.061", "LC_Type1")],
                                       grille_points(identifiant, latitude, longitude), "01-01-2001", "12-31-2025"))
    return requetes


def executer(action: str) -> None:
    jeton = connexion()
    try:
        if action == "soumettre":
            for requete in taches_occupation_du_sol():
                print(requete["task_name"], soumettre(jeton, requete))
        elif action == "suivre":
            taches = json.loads(JOURNAL_TACHES.read_text(encoding="utf-8"))
            for nom, tache in taches.items():
                statut = etat(jeton, tache["task_id"])
                print(nom, statut)
                if statut == "done":
                    for chemin in telecharger_resultats(jeton, tache["task_id"], DOSSIER_APPEEARS / nom):
                        print("   ", chemin.name, empreinte_sha256(chemin)[:16])
    finally:
        requests.post(f"{URL_API}/logout", headers={**entetes(jeton), "Content-Length": "0"}, timeout=60)


if __name__ == "__main__":
    import sys
    executer(sys.argv[1])

"""Extractions sur les points par NASA AppEEARS, pour SRTM, MODIS et SMAP.

AppEEARS traite les demandes en différé. L'identifiant de chaque demande est gardé dans
data/raw/appeears/taches.json, si bien qu'une nouvelle exécution reprend son suivi au
lieu de la soumettre à nouveau. Les identifiants NASA Earthdata sont lus dans ~/.netrc.
"""

import hashlib
import json
import netrc
import time
from datetime import date
from pathlib import Path

from .config import DOSSIER_DONNEES, Point
from .registre import Registre, ecrire_atomique

API = "https://appeears.earthdatacloud.nasa.gov/api"
HOTE = "urs.earthdata.nasa.gov"
DOSSIER = DOSSIER_DONNEES / "raw" / "appeears"
TACHES = DOSSIER / "taches.json"
AIDE = (f"Identifiants NASA Earthdata absents de ~/.netrc. Créez un compte sur https://{HOTE}/users/new, "
        f"puis ajoutez à ~/.netrc la ligne machine {HOTE} login IDENTIFIANT password MOT_DE_PASSE "
        "et lancez chmod 600 ~/.netrc.")


class IdentifiantsManquants(RuntimeError):
    pass


def identifiants(chemin: str | None = None) -> tuple[str, str]:
    try:
        trouve = netrc.netrc(chemin).authenticators(HOTE)
    except (FileNotFoundError, netrc.NetrcParseError):
        trouve = None
    if not trouve or not trouve[0] or not trouve[2]:
        raise IdentifiantsManquants(AIDE)
    return trouve[0], trouve[2]


def requete(tache: dict, points: list[Point]) -> dict:
    jour = lambda texte: date.fromisoformat(texte).strftime("%m-%d-%Y")
    return {"task_type": "point", "task_name": f"abidjan_{tache['nom']}",
            "params": {"dates": [{"startDate": jour(tache["debut"]), "endDate": jour(tache["fin"])}],
                       "layers": [{"product": p, "layer": c} for p, c in tache["couches"]],
                       "coordinates": [{"id": p.id, "category": p.lieu, "latitude": p.lat, "longitude": p.lon}
                                       for p in points]}}


def empreinte_requete(corps: dict) -> str:
    return hashlib.sha256(json.dumps(corps, sort_keys=True).encode()).hexdigest()


def lire_taches() -> dict:
    return json.loads(TACHES.read_text()) if TACHES.exists() else {}


def est_complete(etat: dict | None, cle: str, registre: Registre, dossier: Path) -> bool:
    return bool(etat and etat.get("requete") == cle and etat.get("fichiers") and all(
        registre.est_acquis(dossier / n, etat["urls"][n]) for n in etat["fichiers"]))


class Connexion:
    """Jeton AppEEARS, renouvelé si le serveur le refuse, une nouvelle connexion au compte pouvant l'invalider."""

    def __init__(self, http):
        self.http, self.jeton = http, None

    def renouveler(self):
        r = self.http.post(f"{API}/login", auth=identifiants(), timeout=120)
        r.raise_for_status()
        self.jeton = r.json()["token"]

    def get(self, url: str, **options):
        for essai in range(2):
            if self.jeton is None:
                self.renouveler()
            r = self.http.get(url, headers={"Authorization": f"Bearer {self.jeton}"}, timeout=600, **options)
            if r.status_code not in (401, 403) or essai:
                return r
            self.jeton = None
        return r


def telecharger(points: list[Point], config: dict, registre: Registre, http, attente_minutes: float = 0) -> list[str]:
    avertissements, taches, connexion = [], lire_taches(), Connexion(http)
    for tache in config["appeears"]:
        nom, corps = tache["nom"], requete(tache, points)
        cle, dossier, etat = empreinte_requete(corps), DOSSIER / tache["nom"], taches.get(tache["nom"])
        if est_complete(etat, cle, registre, dossier):
            continue
        if not etat or etat.get("requete") != cle:
            if connexion.jeton is None:
                connexion.renouveler()
            r = http.post(f"{API}/task", json=corps, headers={"Authorization": f"Bearer {connexion.jeton}"}, timeout=120)
            r.raise_for_status()
            etat = taches[nom] = {"task_id": r.json()["task_id"], "requete": cle}
            ecrire_atomique(TACHES, json.dumps(taches, indent=1).encode())
            print(f"AppEEARS {nom} soumise")
        limite = time.monotonic() + attente_minutes * 60
        while True:
            r = connexion.get(f"{API}/task/{etat['task_id']}")
            statut = r.json()["status"] if r.ok else f"inaccessible, code HTTP {r.status_code}"
            if statut in ("done", "error") or not r.ok or time.monotonic() >= limite:
                break
            time.sleep(60)
        if statut != "done":
            avertissements.append(f"AppEEARS {nom} au statut {statut}, relancer plus tard")
            continue
        r = connexion.get(f"{API}/bundle/{etat['task_id']}")
        r.raise_for_status()
        etat["fichiers"], etat["urls"] = [], {}
        for f in r.json()["files"]:
            if not f["file_name"].endswith(".csv"):
                continue
            chemin, url = dossier / Path(f["file_name"]).name, f"{API}/bundle/{etat['task_id']}/{f['file_id']}"
            if not registre.est_acquis(chemin, url):
                contenu = connexion.get(url)
                contenu.raise_for_status()
                ecrire_atomique(chemin, contenu.content)
                registre.consigner(chemin, url)
            etat["fichiers"].append(chemin.name)
            etat["urls"][chemin.name] = url
        ecrire_atomique(TACHES, json.dumps(taches, indent=1).encode())
        print(f"AppEEARS {nom} acquise, {len(etat['fichiers'])} fichiers CSV")
    return avertissements

"""Noms des localités de Côte d'Ivoire, pour nommer la position de l'agriculteur sans connexion.

    python -m donnees.localites

Source, GeoNames, https://www.geonames.org, licence Creative Commons Attribution 4.0.
Sont retenus les lieux habités, classe P, et les subdivisions de quatrième niveau,
code ADM4, qui couvrent notamment les communes d'Abidjan comme le Plateau.
"""

import csv
import io
import json
import zipfile

import requests

from .config import DOSSIER_DONNEES, RACINE
from .registre import Registre, ecrire_atomique

URL_PAYS = "https://download.geonames.org/export/dump/CI.zip"
URL_REGIONS = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"
DOSSIER = DOSSIER_DONNEES / "raw" / "geonames"
SORTIE = RACINE / "app" / "donnees" / "localites.json"
SUFFIXES = [" Autonomous District", " District"]


def telecharger(registre: Registre) -> tuple[bytes, str]:
    contenus = []
    for url in (URL_PAYS, URL_REGIONS):
        chemin = DOSSIER / url.rsplit("/", 1)[1]
        if not registre.est_acquis(chemin, url):
            reponse = requests.get(url, timeout=180)
            reponse.raise_for_status()
            ecrire_atomique(chemin, reponse.content)
            registre.consigner(chemin, url)
        contenus.append(chemin.read_bytes())
    return contenus[0], contenus[1].decode("utf-8")


def nom_region(nom: str) -> str:
    for suffixe in SUFFIXES:
        nom = nom.removesuffix(suffixe)
    return nom


def construire(archive: bytes, regions_texte: str) -> dict:
    regions = {ligne[0].split(".")[1]: nom_region(ligne[1])
               for ligne in csv.reader(io.StringIO(regions_texte), delimiter="\t") if ligne and ligne[0].startswith("CI.")}
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        lignes = csv.reader(io.TextIOWrapper(z.open("CI.txt"), encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE)
        lieux, vus = [], set()
        for l in lignes:
            if not (l[6] == "P" or l[7] == "ADM4"):
                continue
            cle = (l[1], round(float(l[4]), 2), round(float(l[5]), 2))
            if cle in vus:
                continue
            vus.add(cle)
            lieux.append([l[1], round(float(l[4]), 4), round(float(l[5]), 4), regions.get(l[10], "")])
    # Une localité sans région reçoit celle de la localité la plus proche qui en a une.
    connues = [l for l in lieux if l[3]]
    for lieu in lieux:
        if not lieu[3]:
            lieu[3] = min(connues, key=lambda c: (c[1] - lieu[1]) ** 2 + (c[2] - lieu[2]) ** 2)[3]
    return {"source": "GeoNames, www.geonames.org, licence CC BY 4.0", "champs": ["nom", "lat", "lon", "region"],
            "lieux": lieux}


def main() -> None:
    registre = Registre(DOSSIER_DONNEES / "registre.csv", RACINE)
    donnees = construire(*telecharger(registre))
    SORTIE.write_text(json.dumps(donnees, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(donnees['lieux'])} localités écrites dans {SORTIE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()

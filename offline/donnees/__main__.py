"""Téléchargement et vérification des données du projet.

    python -m donnees              télécharge ce qui manque, puis vérifie
    python -m donnees --verifier   vérifie sans rien télécharger
    python -m donnees --attendre 60   attend jusqu'à 60 minutes les extractions AppEEARS

La commande peut être relancée sans risque. Elle saute ce qui est déjà acquis,
intact et conforme à la configuration.
"""

import argparse
import json
import sys

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import appeears, power
from .config import DOSSIER_DONNEES, RACINE, charger, points
from .registre import Registre, ecrire_atomique


def session() -> requests.Session:
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=Retry(
        total=6, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])))
    s.headers["User-Agent"] = "nasa-space-abidjan-donnees"
    return s


def main(arguments=None) -> int:
    lecteur = argparse.ArgumentParser(prog="python -m donnees")
    lecteur.add_argument("--verifier", action="store_true", help="vérifie sans rien télécharger")
    lecteur.add_argument("--attendre", type=float, default=0, metavar="MINUTES",
                         help="durée d'attente des extractions AppEEARS")
    options = lecteur.parse_args(arguments)
    config, registre = charger(), Registre(DOSSIER_DONNEES / "registre.csv", RACINE)
    grille = points(config)

    if not options.verifier:
        http = session()
        for point in grille:
            adresse = power.url(point, config)
            if registre.est_acquis(power.chemin(point), adresse):
                continue
            reponse = http.get(adresse, timeout=180)
            reponse.raise_for_status()
            manquants = power.controler(reponse.json(), config)
            ecrire_atomique(power.chemin(point), json.dumps(reponse.json()).encode())
            registre.consigner(power.chemin(point), adresse)
            alerte = ", ".join(f"{p} {n} jours manquants" for p, n in manquants.items() if n)
            print(f"POWER {point.id} acquis" + (f", {alerte}" if alerte else ""))
        try:
            taches = config["appeears"] if config.get("appeears_actif", True) else []
            for avertissement in appeears.telecharger(grille, {**config, "appeears": taches}, registre, http,
                                                      options.attendre):
                print(f"AVERTISSEMENT {avertissement}")
        except appeears.IdentifiantsManquants as erreur:
            print(f"AVERTISSEMENT {erreur}")

    absents = [f"POWER {p.id}" for p in grille if not registre.est_acquis(power.chemin(p), power.url(p, config))]
    etats = appeears.lire_taches()
    absents += [f"AppEEARS {t['nom']}" for t in (config["appeears"] if config.get("appeears_actif", True) else [])
                if not appeears.est_complete(
        etats.get(t["nom"]), appeears.empreinte_requete(appeears.requete(t, grille)), registre,
        appeears.DOSSIER / t["nom"])]
    for identifiant in absents:
        print(f"MANQUANT {identifiant}")
    print("Toutes les données attendues sont présentes et vérifiées." if not absents
          else f"{len(absents)} fichiers manquent. Relancez python -m donnees.")
    return 1 if absents else 0


if __name__ == "__main__":
    sys.exit(main())

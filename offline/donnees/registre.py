"""Registre des fichiers acquis, avec la requête d'origine et l'empreinte SHA-256."""

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

COLONNES = ["fichier", "url", "date_utc", "octets", "sha256"]


def empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


class Registre:
    def __init__(self, chemin: Path, racine: Path):
        self.chemin, self.racine, self.lignes = chemin, racine, {}
        if chemin.exists():
            with open(chemin, newline="", encoding="utf-8") as fichier:
                self.lignes = {l["fichier"]: l for l in csv.DictReader(fichier)}

    def _cle(self, chemin: Path) -> str:
        return chemin.resolve().relative_to(self.racine.resolve()).as_posix()

    def est_acquis(self, chemin: Path, url: str) -> bool:
        """Vrai si le fichier existe, répond à cette requête et n'a pas été altéré."""
        ligne = self.lignes.get(self._cle(chemin))
        return bool(ligne) and ligne["url"] == url and chemin.exists() and empreinte(chemin) == ligne["sha256"]

    def consigner(self, chemin: Path, url: str) -> None:
        self.lignes[self._cle(chemin)] = {
            "fichier": self._cle(chemin), "url": url,
            "date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "octets": chemin.stat().st_size, "sha256": empreinte(chemin),
        }
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = self.chemin.with_suffix(".tmp")
        with open(temporaire, "w", newline="", encoding="utf-8") as fichier:
            ecrivain = csv.DictWriter(fichier, fieldnames=COLONNES)
            ecrivain.writeheader()
            ecrivain.writerows(sorted(self.lignes.values(), key=lambda l: l["fichier"]))
        temporaire.replace(self.chemin)


def ecrire_atomique(chemin: Path, contenu: bytes) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    partiel = chemin.with_name(chemin.name + ".partiel")
    partiel.write_bytes(contenu)
    partiel.replace(chemin)

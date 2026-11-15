"""Conversations en cours, stockées dans SQLite.

La clé est securite.empreinte_numero, jamais le numéro en clair. Seuls l'étape du
parcours, les consentements et les choix de l'agriculteur sont gardés. Aucune photo,
aucun audio ni aucun texte libre n'est stocké. Une session est effacée quand
l'agriculteur refuse le consentement ou écrit STOP.
"""

import sqlite3
import threading
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

COLONNES = ("empreinte", "etat", "consentement", "lieu", "rotation", "priorite", "consentement_photo",
            "culture_photo", "mise_a_jour")


@dataclass(frozen=True)
class Session:
    empreinte: str
    etat: str = "accueil"
    consentement: bool = False
    lieu: str | None = None
    rotation: str | None = None
    priorite: str | None = None
    consentement_photo: bool = False
    culture_photo: str | None = None
    mise_a_jour: str = ""

    def avec(self, **changements) -> "Session":
        return replace(self, **changements)


class Sessions:
    def __init__(self, chemin: str):
        if chemin != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self._connexion = sqlite3.connect(chemin, check_same_thread=False)
        self._verrou = threading.Lock()
        with self._verrou, self._connexion:
            self._connexion.execute(
                "CREATE TABLE IF NOT EXISTS sessions (empreinte TEXT PRIMARY KEY, etat TEXT, consentement INTEGER, "
                "lieu TEXT, rotation TEXT, priorite TEXT, consentement_photo INTEGER, culture_photo TEXT, "
                "mise_a_jour TEXT)")

    def lire(self, empreinte: str) -> Session:
        with self._verrou:
            ligne = self._connexion.execute(
                f"SELECT {', '.join(COLONNES)} FROM sessions WHERE empreinte = ?", (empreinte,)).fetchone()
        if ligne is None:
            return Session(empreinte)
        valeurs = dict(zip(COLONNES, ligne))
        return Session(**{**valeurs, "consentement": bool(valeurs["consentement"]),
                          "consentement_photo": bool(valeurs["consentement_photo"])})

    def ecrire(self, session: Session) -> Session:
        session = session.avec(mise_a_jour=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        valeurs = asdict(session)
        with self._verrou, self._connexion:
            self._connexion.execute(
                f"INSERT OR REPLACE INTO sessions ({', '.join(COLONNES)}) VALUES ({', '.join('?' * len(COLONNES))})",
                [int(v) if isinstance(v, bool) else v for v in (valeurs[c] for c in COLONNES)])
        return session

    def effacer(self, empreinte: str) -> None:
        with self._verrou, self._connexion:
            self._connexion.execute("DELETE FROM sessions WHERE empreinte = ?", (empreinte,))

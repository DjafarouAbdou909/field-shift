"""Conversations en cours, stockées dans SQLite.

La clé est securite.empreinte_numero, jamais le numéro en clair. Seuls l'étape du
parcours, les consentements et les choix de l'agriculteur sont gardés, avec l'identifiant
WhatsApp et le type d'une photo reçue avant le consentement à son envoi, effacés dès
qu'elle est analysée ou refusée. Aucune photo, aucun audio ni aucun texte libre n'est
stocké. Une session est effacée quand l'agriculteur refuse le consentement ou écrit STOP.
"""

import sqlite3
import threading
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

COLONNES = ("empreinte", "etat", "consentement", "lieu", "rotation", "priorite", "consentement_photo",
            "photo_en_attente", "mode_vocal", "mise_a_jour")


@dataclass(frozen=True)
class Session:
    empreinte: str
    etat: str = "accueil"
    consentement: bool = False
    lieu: str | None = None
    rotation: str | None = None
    priorite: str | None = None
    consentement_photo: bool = False
    photo_en_attente: str | None = None
    mode_vocal: bool = False
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
                "lieu TEXT, rotation TEXT, priorite TEXT, consentement_photo INTEGER, photo_en_attente TEXT, "
                "mode_vocal INTEGER, mise_a_jour TEXT)")
            presentes = {ligne[1] for ligne in self._connexion.execute("PRAGMA table_info(sessions)")}
            for colonne in set(COLONNES) - presentes:
                self._connexion.execute(f"ALTER TABLE sessions ADD COLUMN {colonne} TEXT")

    def lire(self, empreinte: str) -> Session:
        with self._verrou:
            ligne = self._connexion.execute(
                f"SELECT {', '.join(COLONNES)} FROM sessions WHERE empreinte = ?", (empreinte,)).fetchone()
        if ligne is None:
            return Session(empreinte)
        valeurs = dict(zip(COLONNES, ligne))
        # Une colonne ajoutée par ALTER TABLE est de type TEXT et rend 0 sous la forme '0'.
        return Session(**{**valeurs, **{c: str(valeurs[c]) in ("1", "True") for c in ("consentement",
                                                                                     "consentement_photo",
                                                                                     "mode_vocal")}})

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

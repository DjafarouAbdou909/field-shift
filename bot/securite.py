"""Sécurité du webhook WhatsApp, signature, idempotence et pseudonymisation."""

import hashlib
import hmac
import sqlite3
import threading


def signature_valide(corps: bytes, entete: str | None, secret: str) -> bool:
    """Vérifie l'en-tête X-Hub-Signature-256 de Meta sur le corps brut de la requête."""
    if not secret or not entete:
        return False
    attendu = "sha256=" + hmac.new(secret.encode(), corps, hashlib.sha256).hexdigest()
    # compare_digest lève TypeError sur une chaîne non ASCII, d'où la comparaison en octets.
    return hmac.compare_digest(attendu.encode(), entete.encode())


def empreinte_numero(numero: str, sel: str) -> str:
    """Retourne l'empreinte salée d'un numéro, seule forme sous laquelle il est stocké."""
    if not sel:
        raise ValueError("le sel de pseudonymisation est vide")
    return hmac.new(sel.encode(), numero.encode(), hashlib.sha256).hexdigest()


class RegistreMessages:
    """Mémorise les identifiants wamid déjà traités, pour ignorer les renvois de Meta."""

    def __init__(self, chemin: str):
        self._connexion = sqlite3.connect(chemin, check_same_thread=False)
        self._verrou = threading.Lock()
        with self._verrou, self._connexion:
            self._connexion.execute("CREATE TABLE IF NOT EXISTS messages_vus (wamid TEXT PRIMARY KEY)")

    def deja_vu(self, wamid: str) -> bool:
        """Enregistre l'identifiant et indique s'il avait déjà été vu."""
        with self._verrou, self._connexion:
            curseur = self._connexion.execute("INSERT OR IGNORE INTO messages_vus VALUES (?)", (wamid,))
            return curseur.rowcount == 0

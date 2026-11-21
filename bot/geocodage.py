"""Lieu dit par l'agriculteur, ville couverte ou village retrouvé sur OpenStreetMap.

Extension à toute la Côte d'Ivoire du 20 novembre 2026. Un nom de ville couverte, ou de
sa région, est reconnu sans réseau dans la phrase. Sinon, les mots qui restent une fois
retirés ceux de la phrase courante sont cherchés par Nominatim, le service de recherche
d'OpenStreetMap, limité à la Côte d'Ivoire, et le village trouvé est rattaché à la ville
couverte la plus proche.

Nominatim, politique d'usage lue sur https://operations.osmfoundation.org/policies/nominatim/
le 20 novembre 2026, une requête par seconde au plus, un User-Agent qui identifie
l'application, et la mention d'OpenStreetMap, données sous licence ODbL. Seul le nom du
lieu part chez Nominatim, jamais le numéro ni le reste du message. Les réponses sont
gardées en mémoire, si bien qu'un même nom n'est demandé qu'une fois par processus.
"""

import functools
import logging
import re
import threading
import time

import requests

from moteur.lieux import LIEUX

from .langage.comprehension import normaliser

journal = logging.getLogger("bot")
URL = "https://nominatim.openstreetmap.org/search"
AGENT = "AgriBot-field-shift/1.0"
DELAI_SECONDES = 6
INTERVALLE_SECONDES = 1.1

# Noms courts ou écrits autrement, entendus ou lus pour une ville couverte.
ALIAS = {"ferke": "ferkessedougou", "ferkessedougou": "ferkessedougou", "yakro": "yamoussoukro",
         "san pedro": "san_pedro", "sanpedro": "san_pedro", "bondoukou": "bondoukou", "odiene": "odienne",
         "korogo": "korhogo", "bouake": "bouake", "seguela": "seguela"}
MOTS_VIDES = {
    "a", "au", "aux", "chez", "cote", "d'ivoire", "dans", "de", "des", "du", "en", "est", "et", "habite", "j'habite",
    "je", "la", "le", "les", "mes", "mon", "ma", "nous", "par", "pres", "proche", "sommes", "suis", "sur", "vers",
    "village", "ville", "champ", "champs", "plantation", "c'est", "cest", "moi", "on", "ici", "region", "cote",
    "ivoire", "sous", "prefecture", "departement", "quartier", "campement", "a cote", "pas", "loin",
}

_dernier_appel = 0.0
_verrou = threading.Lock()


def _noms_de_villes() -> dict[str, str]:
    """Chaque nom reconnu, ville ou région, normalisé, vers l'identifiant de sa ville."""
    noms = {}
    for identifiant, lieu in LIEUX.items():
        noms[normaliser(lieu["nom"])] = identifiant
        if not lieu["region"].startswith("District"):
            noms.setdefault(normaliser(lieu["region"]), identifiant)
    noms.update(ALIAS)
    return noms


NOMS = _noms_de_villes()


def ville_nommee(texte: str) -> str | None:
    """Ville couverte nommée dans la phrase, par son nom, un alias ou sa région, ou None."""
    phrase = f" {normaliser(texte).replace('-', ' ')} "
    trouves = [(len(nom), identifiant) for nom, identifiant in NOMS.items()
               if re.search(rf"(?<![a-z']){re.escape(nom.replace('-', ' '))}(?![a-z])", phrase)]
    return max(trouves)[1] if trouves else None


def nom_a_chercher(texte: str) -> str:
    """Les mots de la phrase qui peuvent désigner un lieu, sans les mots de la phrase courante."""
    mots = [m.strip("'") for m in normaliser(texte).replace("'", "' ").split()]
    return " ".join(m for m in mots if len(m) > 1 and m not in MOTS_VIDES)[:80]


@functools.lru_cache(maxsize=512)
def chercher(nom: str, session=None) -> tuple[float, float, str] | None:
    """Latitude, longitude et nom d'un lieu de Côte d'Ivoire selon OpenStreetMap, ou None."""
    global _dernier_appel
    if len(nom) < 3 or len(nom.split()) > 4:
        return None
    try:
        with _verrou:
            attente = INTERVALLE_SECONDES - (time.monotonic() - _dernier_appel)
            if attente > 0:
                time.sleep(attente)
            _dernier_appel = time.monotonic()
        reponse = (session or requests).get(URL, timeout=DELAI_SECONDES, headers={"User-Agent": AGENT}, params={
            "q": nom, "countrycodes": "ci", "format": "jsonv2", "limit": 1, "featureType": "settlement"})
        reponse.raise_for_status()
        resultats = reponse.json()
    except Exception as erreur:
        journal.warning("recherche du lieu impossible, %s", type(erreur).__name__)
        return None
    if not resultats:
        return None
    premier = resultats[0]
    return float(premier["lat"]), float(premier["lon"]), premier.get("name") or nom.title()

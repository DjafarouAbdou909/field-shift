"""Liste fermée des maladies du diagnostic par photo, décision du 14 novembre 2026.

Cinq maladies des feuilles du coton et du maïs, chacune citée avec une source lue sur sa
présence en Côte d'Ivoire ou en Afrique de l'Ouest, et avec des images sous licence libre.
La maladie bleue et la mosaïque du coton, les plus fréquemment rapportées en Afrique selon
SILVIE2024, n'ont aucun jeu d'images libre trouvé. Elles restent hors du modèle, qui
répond alors « inconnu », comme pour toute maladie hors de la liste. La nécrose létale du
maïs est exclue, GEDIL2019 décrivant en 2019 son arrivée en Afrique de l'Ouest et du
Centre comme imminente, donc non encore signalée.

Le diagnostic ne nomme jamais de traitement ni de produit.
"""

from .contrat import Source
from .sources import source

MALADIES = {
    "striure du maïs": {"culture": "maïs", "agent": "Maize streak virus", "sources": "EPPO_MSV, GEDIL2019"},
    "rouille commune du maïs": {"culture": "maïs", "agent": "Puccinia sorghi", "sources": "SORO2024"},
    "helminthosporiose du maïs": {"culture": "maïs", "agent": "Exserohilum turcicum",
                                  "sources": "BANKOLE2023, SORO2024"},
    "bactériose du coton": {"culture": "coton", "agent": "Xanthomonas citri pv. malvacearum",
                            "sources": "EPPO_XANTHO, SILVIE2024"},
    "alternariose du coton": {"culture": "coton", "agent": "Alternaria macrospora", "sources": "NWANOSIKE1997"},
}
HORS_MODELE = {
    "maladie bleue du coton": "aucun jeu d'images sous licence libre trouvé, SILVIE2024",
    "mosaïque du coton": "aucun jeu d'images sous licence libre trouvé, SILVIE2024",
    "nécrose létale du maïs": "arrivée en Afrique de l'Ouest et du Centre dite imminente en 2019 par GEDIL2019",
}


def liste(culture: str) -> list[str]:
    """Maladies de la liste fermée pour une culture."""
    return [nom for nom, maladie in MALADIES.items() if maladie["culture"] == culture]


def source_maladie(nom: str) -> Source:
    """Source combinée qui fonde la présence d'une maladie de la liste."""
    return source(MALADIES[nom]["sources"])

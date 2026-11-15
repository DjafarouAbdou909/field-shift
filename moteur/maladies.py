"""Liste des maladies sourcées, établie le 14 novembre 2026 pour le diagnostic par photo.

Depuis le 15 novembre 2026, le diagnostic répond librement, à la manière du projet
agri-bot, et cette liste ne lui est plus imposée. Elle sert au garde-fou, qui refuse un
nom de maladie dans un message de recommandation ou d'alerte où le moteur n'en cite pas.

Quatre maladies des feuilles du coton et du maïs, chacune citée avec une source lue sur sa
présence en Côte d'Ivoire ou en Afrique de l'Ouest, et avec des images de terrain sous
licence libre pour mesurer la fiabilité du diagnostic.

Hors de la liste, le diagnostic répond « inconnu ». C'est le cas de la maladie bleue et
de la mosaïque du coton, les plus fréquemment rapportées en Afrique selon SILVIE2024, mais
sans jeu d'images libre trouvé. C'est aussi le cas de l'alternariose du coton, retirée le
14 novembre 2026, sa seule source d'images, d'origine inconnue, ne permettant pas un test
honnête. La nécrose létale du maïs est exclue, GEDIL2019 décrivant en 2019 son arrivée en
Afrique de l'Ouest et du Centre comme imminente, donc non encore signalée.

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
}
HORS_MODELE = {
    "alternariose du coton": "une seule source d'images, d'origine inconnue, sans test honnête possible",
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

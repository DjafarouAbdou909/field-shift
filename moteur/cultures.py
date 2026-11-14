"""Caractéristiques des cultures candidates.

Chaque caractéristique est saisie avec sa source, consignée dans docs/sources.md, ou
marquée hypothese.

Durée du cycle. Elle vient du tableau 11 du chapitre 6 du bulletin FAO-56, Allen R. G.,
Pereira L. S., Raes D. et Smith M., 1998, Crop evapotranspiration, Guidelines for
computing crop water requirements, FAO Irrigation and drainage paper 56, FAO, Rome,
ISBN 92-5-104219-5, version HTML https://www.fao.org/4/x0490e/x0490e0b.htm consultée le
14 novembre 2026. Les lignes sont recopiées telles qu'imprimées, durées des stades
initial, de développement, de mi-saison et de fin, total en jours, date de semis et
région. Ces durées sont générales et ne sont pas propres aux variétés ivoiriennes, d'où
le niveau hypothese, même avec une source.

La ligne de référence d'une culture est choisie par une règle visible. D'abord les
lignes d'Afrique de l'Ouest, puis celles des tropiques, puis celles du reste de
l'Afrique, et sinon toutes les lignes. Si plusieurs lignes restent, la durée de
référence est la médiane de leurs totaux, arrondie au jour le plus proche, une
demi-journée allant au jour supérieur. La plage est celle des totaux de toutes les
lignes de la culture.
"""

import math
from dataclasses import dataclass

import numpy as np

CULTURES = [
    "coton", "maïs", "sorgho", "mil", "arachide", "niébé", "soja",
    "riz pluvial", "igname", "mucuna",
]

SOURCE_FAO56 = ("Allen R. G., Pereira L. S., Raes D., Smith M., 1998. Crop evapotranspiration, FAO Irrigation "
                "and drainage paper 56, chapitre 6, tableau 11, https://www.fao.org/4/x0490e/x0490e0b.htm")


@dataclass(frozen=True)
class LigneFAO56:
    culture_fao: str
    initial: int
    developpement: int
    mi_saison: int
    fin: int
    total: int
    semis: str
    region: str
    remarque: str = ""


LIGNES_FAO56 = {
    "coton": [
        LigneFAO56("Cotton", 30, 50, 60, 55, 195, "Mar-May", "Egypt; Pakistan; Calif."),
        LigneFAO56("Cotton", 45, 90, 45, 45, 225, "Mar", "Calif. Desert, USA"),
        LigneFAO56("Cotton", 30, 50, 60, 55, 195, "Sept", "Yemen"),
        LigneFAO56("Cotton", 30, 50, 55, 45, 180, "April", "Texas"),
    ],
    "maïs": [
        LigneFAO56("Maize (grain)", 30, 50, 60, 40, 180, "April", "East Africa (alt.)"),
        LigneFAO56("Maize (grain)", 25, 40, 45, 30, 140, "Dec/Jan", "Arid Climate"),
        LigneFAO56("Maize (grain)", 20, 35, 40, 30, 125, "June", "Nigeria (humid)"),
        LigneFAO56("Maize (grain)", 20, 35, 40, 30, 125, "October", "India (dry, cool)"),
        LigneFAO56("Maize (grain)", 30, 40, 50, 30, 150, "April", "Spain (spr, sum.); Calif."),
        LigneFAO56("Maize (grain)", 30, 40, 50, 50, 170, "April", "Idaho, USA"),
    ],
    "sorgho": [
        LigneFAO56("Sorghum", 20, 35, 40, 30, 130, "May/June", "USA, Pakis., Med.",
                   "Les stades imprimés somment à 125 jours, pas au total imprimé de 130"),
        LigneFAO56("Sorghum", 20, 35, 45, 30, 140, "Mar/April", "Arid Region",
                   "Les stades imprimés somment à 130 jours, pas au total imprimé de 140"),
    ],
    "mil": [
        LigneFAO56("Millet", 15, 25, 40, 25, 105, "June", "Pakistan"),
        LigneFAO56("Millet", 20, 30, 55, 35, 140, "April", "Central USA"),
    ],
    "arachide": [
        LigneFAO56("Groundnut", 25, 35, 45, 25, 130, "Dry", "West Africa",
                   "La version HTML répartit Dry season sur deux lignes, la date de semis reste incertaine"),
        LigneFAO56("Groundnut", 35, 35, 35, 35, 140, "season", "High Latitudes",
                   "Date de semis mal alignée dans la version HTML"),
        LigneFAO56("Groundnut", 35, 45, 35, 25, 140, "May May/June", "Mediterranean",
                   "Date de semis mal alignée dans la version HTML"),
    ],
    "niébé": [
        LigneFAO56("Green gram, cowpeas", 20, 30, 30, 20, 110, "March", "Mediterranean",
                   "Les stades imprimés somment à 100 jours, pas au total imprimé de 110"),
    ],
    "soja": [
        LigneFAO56("Soybeans", 15, 15, 40, 15, 85, "Dec", "Tropics"),
        LigneFAO56("Soybeans", 20, 35, 60, 25, 140, "May", "Central USA",
                   "Développement imprimé 30/35, la valeur 35 fait somme avec le total imprimé"),
        LigneFAO56("Soybeans", 20, 25, 75, 30, 150, "June", "Japan"),
    ],
    "riz pluvial": [
        LigneFAO56("Rice", 30, 30, 60, 30, 150, "Dec; May", "Tropics; Mediterranean",
                   "Le tableau ne distingue pas le riz pluvial du riz irrigué"),
        LigneFAO56("Rice", 30, 30, 80, 40, 180, "May", "Tropics",
                   "Développement imprimé 30. avec un point, le tableau ne distingue pas le riz pluvial"),
    ],
}

ETAPES_REGION = [("Afrique de l'Ouest", ("West Africa", "Nigeria")), ("tropiques", ("Tropics",)),
                 ("reste de l'Afrique", ("Africa", "Egypt"))]


@dataclass(frozen=True)
class DureeCycle:
    culture: str
    jours: int | None
    bas: int | None
    haut: int | None
    niveau: str
    lignes: tuple[LigneFAO56, ...]
    regle: str


def duree_cycle(culture: str) -> DureeCycle:
    """Durée de référence du cycle d'une culture, sa plage et les lignes du tableau 11 qui la fondent."""
    lignes = LIGNES_FAO56.get(culture, [])
    if not lignes:
        return DureeCycle(culture, None, None, None, "hypothese", (), "absente du tableau 11 de FAO-56")
    retenues, regle = lignes, "médiane de toutes les lignes"
    for nom, mots in ETAPES_REGION:
        choix = [l for l in lignes if any(mot in l.region for mot in mots)]
        if choix:
            retenues, regle = choix, f"lignes {nom}"
            break
    jours = math.floor(float(np.median([l.total for l in retenues])) + 0.5)
    totaux = [l.total for l in lignes]
    return DureeCycle(culture, jours, min(totaux), max(totaux), "hypothese", tuple(retenues), regle)

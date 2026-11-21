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
l'Afrique, et sinon toutes les lignes. Si plusieurs lignes restent, la ligne de
référence est celle du total médian, la plus courte des deux lignes médianes quand leur
nombre est pair, afin que la référence soit toujours une ligne réelle avec ses stades.
La plage est celle des totaux de toutes les lignes de la culture. Le total imprimé fait
foi. Quand les stades imprimés ne lui somment pas, ce qui arrive sur trois lignes
signalées par leur remarque, le stade de fin absorbe l'écart.

Coefficient cultural. Il vient du tableau 12 du même chapitre, valeurs Kc ini, Kc mid
et Kc end pour des cultures sans stress, bien conduites, en climat subhumide, humidité
relative minimale d'environ 45 % et vent d'environ 2 m/s. Une culture sans Kc ini propre
prend celui de son groupe, comme le tableau l'indique. Une valeur imprimée en plage
donne sa plage, et sa référence est le milieu de la plage. La courbe journalière suit
l'équation 66 de FAO-56, constante aux stades initial et de mi-saison, linéaire au
développement et en fin de cycle. Aucun ajustement climatique n'est appliqué.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

CULTURES = [
    "coton", "maïs", "sorgho", "mil", "arachide", "niébé", "soja",
    "riz pluvial", "igname", "mucuna",
]

SOURCE_FAO56 = ("Allen R. G., Pereira L. S., Raes D., Smith M., 1998. Crop evapotranspiration, FAO Irrigation "
                "and drainage paper 56, chapitre 6, tableaux 11 et 12, https://www.fao.org/4/x0490e/x0490e0b.htm")


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
class CoefficientFAO56:
    ligne: str
    ini: float
    mid: tuple[float, float]
    end: tuple[float, float]
    remarque: str = ""

    def reference(self) -> tuple[float, float, float]:
        return self.ini, sum(self.mid) / 2, sum(self.end) / 2


KC_FAO56 = {
    "coton": CoefficientFAO56("Cotton, Kc ini 0.35 du groupe g. Fibre Crops", 0.35, (1.15, 1.20), (0.70, 0.50)),
    "maïs": CoefficientFAO56("Maize, Field (grain) (field corn), Kc ini 0.3 du groupe i. Cereals", 0.3, (1.20, 1.20),
                             (0.60, 0.35), "Note 11, 0,60 pour une récolte humide, 0,35 après séchage au champ"),
    "sorgho": CoefficientFAO56("Sorghum - grain, Kc ini 0.3 du groupe i. Cereals", 0.3, (1.00, 1.10), (0.55, 0.55)),
    "mil": CoefficientFAO56("Millet, Kc ini 0.3 du groupe i. Cereals", 0.3, (1.00, 1.00), (0.30, 0.30)),
    "arachide": CoefficientFAO56("Groundnut (Peanut), Kc ini 0.4 du groupe e. Legumes", 0.4, (1.15, 1.15),
                                 (0.60, 0.60)),
    "niébé": CoefficientFAO56("Green Gram and Cowpeas, Kc ini 0.4 du groupe e. Legumes", 0.4, (1.05, 1.05),
                              (0.60, 0.35), "Note 6, 0,60 pour une récolte en frais, 0,35 en sec"),
    "soja": CoefficientFAO56("Soybeans, Kc ini 0.4 du groupe e. Legumes", 0.4, (1.15, 1.15), (0.50, 0.50)),
    "riz pluvial": CoefficientFAO56("Rice", 1.05, (1.20, 1.20), (0.90, 0.60),
                                    "Le tableau ne distingue pas le riz pluvial, et un Kc ini de 1,05 suppose un sol "
                                    "très souvent humide"),
}


@dataclass(frozen=True)
class DureeCycle:
    culture: str
    jours: int | None
    bas: int | None
    haut: int | None
    niveau: str
    ligne: LigneFAO56 | None
    regle: str

    def stades(self) -> tuple[int, int, int, int]:
        """Stades initial, développement, mi-saison et fin, le stade de fin complétant le total imprimé."""
        l = self.ligne
        return l.initial, l.developpement, l.mi_saison, l.total - l.initial - l.developpement - l.mi_saison


def duree_cycle(culture: str) -> DureeCycle:
    """Durée de référence du cycle d'une culture, sa plage et la ligne du tableau 11 qui la fonde."""
    lignes = LIGNES_FAO56.get(culture, [])
    if not lignes:
        return DureeCycle(culture, None, None, None, "hypothese", None, "absente du tableau 11 de FAO-56")
    retenues, regle = lignes, "ligne médiane de toutes les lignes"
    for nom, mots in ETAPES_REGION:
        choix = [l for l in lignes if any(mot in l.region for mot in mots)]
        if choix:
            retenues, regle = choix, f"ligne médiane des lignes {nom}"
            break
    ligne = sorted(retenues, key=lambda l: l.total)[(len(retenues) - 1) // 2]
    totaux = [l.total for l in lignes]
    return DureeCycle(culture, ligne.total, min(totaux), max(totaux), "hypothese", ligne, regle)


def courbe_kc(stades: tuple[int, int, int, int], kc_ini: float, kc_mid: float, kc_end: float) -> np.ndarray:
    """Coefficient cultural de chaque jour du cycle, équation 66 de FAO-56, jour i de 1 à la durée totale."""
    initial, developpement, mi_saison, fin = stades
    jours = np.arange(1, sum(stades) + 1)
    kc = np.full(len(jours), kc_mid, dtype=float)
    kc[jours <= initial] = kc_ini
    dev = (jours > initial) & (jours <= initial + developpement)
    kc[dev] = kc_ini + (jours[dev] - initial) / developpement * (kc_mid - kc_ini)
    debut_fin = initial + developpement + mi_saison
    tard = jours > debut_fin
    kc[tard] = kc_mid + (jours[tard] - debut_fin) / fin * (kc_end - kc_mid)
    return kc


def cultures_comparees() -> list[str]:
    """Cultures qui ont à la fois une durée et un coefficient cultural sourcés."""
    return [c for c in CULTURES if duree_cycle(c).jours is not None and c in KC_FAO56]


def courbes_kc_comparees() -> dict[str, np.ndarray]:
    """Courbe journalière du coefficient cultural de chaque culture comparée, sur sa durée de référence."""
    return {c: courbe_kc(duree_cycle(c).stades(), *KC_FAO56[c].reference()) for c in cultures_comparees()}



def mi_saisons_comparees() -> dict[str, tuple[int, int]]:
    """Premier et dernier jour du stade de mi-saison de chaque culture comparée, comptés depuis 1."""
    reponse = {}
    for culture in cultures_comparees():
        initial, developpement, mi_saison, _ = duree_cycle(culture).stades()
        reponse[culture] = (initial + developpement + 1, initial + developpement + mi_saison)
    return reponse


def tableau_cultures() -> list[dict]:
    """Durée, plage, ligne du tableau 11 et coefficients du tableau 12 de chaque culture candidate."""
    lignes = []
    for culture in CULTURES:
        duree, kc = duree_cycle(culture), KC_FAO56.get(culture)
        lignes.append({
            "culture": culture, "comparée": culture in cultures_comparees(), "durée": duree.jours,
            "plage": f"{duree.bas} à {duree.haut}" if duree.jours else None,
            "ligne du tableau 11": duree.ligne.region if duree.ligne else duree.regle,
            "stades": duree.stades() if duree.ligne else None,
            "Kc ini, mid, end": tuple(round(v, 3) for v in kc.reference()) if kc else None,
        })
    return lignes


# Fenêtres où sèment 70 % des producteurs de coton au nord du 9e parallèle et 80 % au sud,
# selon l'enquête du CNRA, GNAPI2025, page 1575. Chaque ville prend celle de sa latitude,
# Korhogo étant au nord et Bouaké au sud.
FENETRE_SEMIS_COTON = {"nord_du_9e_parallele": ("06-01", "06-30"), "sud_du_9e_parallele": ("06-11", "07-10")}


def fenetre_semis_coton(identifiant: str) -> tuple[str, str]:
    from .lieux import LIEUX

    return FENETRE_SEMIS_COTON["nord_du_9e_parallele" if LIEUX[identifiant]["lat"] >= 9.0 else "sud_du_9e_parallele"]


def semis_coton(identifiant: str, position: str = "milieu") -> dict[str, str]:
    """Date de semis du coton au format MM-JJ, début, milieu arrondi au jour inférieur, ou fin de la fenêtre."""
    debut, fin = (pd.Timestamp(f"2001-{jour}") for jour in fenetre_semis_coton(identifiant))
    date = {"debut": debut, "milieu": debut + (fin - debut) / 2, "fin": fin}[position]
    return {"coton": date.floor("D").strftime("%m-%d")}


def variantes_duree_coton() -> dict[str, tuple[int, int, int, int]]:
    """Stades du coton pour tester la dépendance des résultats à la durée de son cycle.

    Les lignes Texas, 180 jours, et Calif. Desert, 225 jours, sont celles du tableau 11 de
    FAO-56. La variante de 150 jours est une hypothèse sans source, aux stades
    proportionnels à ceux de la référence de 195 jours, aucune durée propre aux variétés
    ivoiriennes n'ayant été trouvée dans un document lu.
    """
    lignes = {l.region: l for l in LIGNES_FAO56["coton"]}
    reference = duree_cycle("coton").stades()
    proportionnels = [round(s * 150 / sum(reference)) for s in reference[:3]]
    return {
        "fao56_texas_180": (lignes["Texas"].initial, lignes["Texas"].developpement, lignes["Texas"].mi_saison,
                            lignes["Texas"].fin),
        "fao56_reference_195": reference,
        "fao56_californie_225": (lignes["Calif. Desert, USA"].initial, lignes["Calif. Desert, USA"].developpement,
                                 lignes["Calif. Desert, USA"].mi_saison, lignes["Calif. Desert, USA"].fin),
        "hypothese_150": (*proportionnels, 150 - sum(proportionnels)),
    }


def avec_stades_coton(stades: tuple[int, int, int, int]) -> tuple[dict[str, np.ndarray], dict[str, tuple[int, int]]]:
    """Courbes de coefficient cultural et mi-saisons des cultures comparées, le coton ayant les stades donnés."""
    courbes, mi_saisons = courbes_kc_comparees(), mi_saisons_comparees()
    courbes["coton"] = courbe_kc(stades, *KC_FAO56["coton"].reference())
    mi_saisons["coton"] = (stades[0] + stades[1] + 1, stades[0] + stades[1] + stades[2])
    return courbes, mi_saisons


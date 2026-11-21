"""Climat de la zone d'une ville du sud forestier, pour l'application hors connexion.

Mêmes grandeurs que moteur/climat.py du dépôt, décision du 20 novembre 2026, calculées sur
la pluie GPM IMERG de la grille de la ville. La règle du début des pluies, cherchée à
partir du 1er mars, est coupée par sa date de recherche dans le sud, si bien qu'aucune date
de début n'y est donnée. Un mois compte s'il a au moins 28 jours de pluie connue, une année
si ses 365 premiers jours au moins sont connus. Les quantiles suivent l'interpolation
linéaire, méthode inclusive de statistics.quantiles. Mars à juillet est la grande saison des
pluies du sud selon le profil de risque climatique de la GIZ, page 3.
"""

import math
import statistics

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]
GRANDE_SAISON = (3, 7)
SECONDE_FENETRE = (8, 11)


def quantile(valeurs: list[float], p: float) -> float:
    """Quantile à interpolation linéaire, comme pandas par défaut."""
    ordonnees = sorted(valeurs)
    position = (len(ordonnees) - 1) * p
    bas = math.floor(position)
    haut = min(bas + 1, len(ordonnees) - 1)
    return ordonnees[bas] + (ordonnees[haut] - ordonnees[bas]) * (position - bas)


def resumer(serie: dict) -> dict:
    """Pluie par mois, pluie annuelle et pluie de mars à juillet, à partir de jours et pluie journalière."""
    mensuelles, connus = {}, {}
    for jour, pluie in zip(serie["jours"], serie["pluie"]):
        cle = (jour.year, jour.month)
        connus.setdefault(cle, 0)
        mensuelles.setdefault(cle, 0.0)
        if not math.isnan(pluie):
            connus[cle] += 1
            mensuelles[cle] += pluie
    valides = {cle: v for cle, v in mensuelles.items() if connus[cle] >= 28}
    par_mois = {m: statistics.mean([v for (a, mm), v in valides.items() if mm == m]) for m in range(1, 13)}
    annees = sorted({a for a, _ in mensuelles})
    jours_connus = {a: sum(connus[(a, m)] for m in range(1, 13) if (a, m) in connus) for a in annees}
    annuelles = [sum(mensuelles[(a, m)] for m in range(1, 13)) for a in annees if jours_connus[a] >= 365]
    grandes = [sum(valides[(a, m)] for m in range(GRANDE_SAISON[0], GRANDE_SAISON[1] + 1)) for a in annees
               if all((a, m) in valides for m in range(GRANDE_SAISON[0], GRANDE_SAISON[1] + 1))]
    pic_1 = max(range(GRANDE_SAISON[0], GRANDE_SAISON[1] + 1), key=lambda m: par_mois[m])
    pic_2 = max(range(SECONDE_FENETRE[0], SECONDE_FENETRE[1] + 1), key=lambda m: par_mois[m])
    creux = min(range(pic_1, pic_2 + 1), key=lambda m: par_mois[m])
    return {"annees": (annees[0], annees[-1]), "pluie_par_mois": par_mois,
            "pluie_annuelle_mediane": statistics.median(annuelles), "pluie_annuelle_q10": quantile(annuelles, 0.1),
            "mois_pic_grande_saison": pic_1, "mois_pic_seconde": pic_2, "mois_creux": creux,
            "grande_saison_q10": quantile(grandes, 0.1), "grande_saison_q90": quantile(grandes, 0.9)}


def mm(valeur: float) -> str:
    return f"{round(valeur, -1):.0f} mm"


def de(nom: str) -> str:
    return f"d'{nom}" if nom[0].lower() in "aeiouyéèêâîôû" else f"de {nom}"


def texte(c: dict, nom: str) -> str:
    """Message lu à voix haute, chaque nombre arrondi à la dizaine, avec le renvoi au conseiller."""
    p = c["pluie_par_mois"]
    pic_1, pic_2, creux = c["mois_pic_grande_saison"], c["mois_pic_seconde"], c["mois_creux"]
    debut, fin = c["annees"]
    return "\n".join([
        f"Voici ce que disent {fin - debut + 1} ans de mesures satellite de la NASA, de {debut} à {fin}, pour la "
        f"zone {de(nom)}.",
        f"Il tombe en général environ {mm(c['pluie_annuelle_mediane'])} de pluie par an, et moins de "
        f"{mm(c['pluie_annuelle_q10'])} une année sur dix.",
        f"Les mois les plus pluvieux sont {MOIS[pic_1 - 1]}, avec environ {mm(p[pic_1])}, et {MOIS[pic_2 - 1]}, avec "
        f"environ {mm(p[pic_2])}. Entre les deux, {MOIS[creux - 1]} n'en reçoit qu'environ {mm(p[creux])}.",
        f"De mars à juillet, la pluie change beaucoup d'une année à l'autre, d'environ {mm(c['grande_saison_q10'])} "
        f"les années sèches à environ {mm(c['grande_saison_q90'])} les années humides.",
        "Pour choisir vos cultures et vos dates de semis, parlez-en avec votre conseiller ANADER.",
    ])

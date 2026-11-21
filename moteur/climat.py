"""Climat de la zone d'une ville, tiré de la seule pluie NASA GPM IMERG de 2001 à 2025.

Décision du responsable du 20 novembre 2026. Pour les villes du sud forestier, où les
rotations comparées par moteur/rotations.py n'ont pas de sens, AgriBot donne ce que
mesure la pluie, sans aucune règle de début de saison. La règle de début des pluies de
moteur/indicateurs.py, qui cherche à partir du 1er mars, y est coupée par sa date de
recherche, le début témoin cherché dès le 1er janvier tombant avant mars jusqu'à 23
années sur 25, si bien qu'une date de début y serait un artefact du calcul.

Les grandeurs, toutes de niveau calcule, sont la pluie annuelle médiane et son quantile
de 10 %, la pluie moyenne de chaque mois, le mois le plus pluvieux de mars à juillet, le
mois le plus pluvieux d'août à novembre et le mois le moins pluvieux entre les deux, et
les quantiles de 10 et 90 % de la pluie de mars à juillet. Mars à juillet est la grande
saison des pluies du sud selon le profil de risque climatique de la GIZ, GIZ_PROFIL, page 3,
qui place la petite saison en octobre et novembre. La fenêtre d'août à novembre englobe
aussi le maximum de septembre de l'ouest du pays.
"""

import functools
from dataclasses import dataclass

import pandas as pd

ANNEES = (2001, 2025)
GRANDE_SAISON = (3, 7)
SECONDE_FENETRE = (8, 11)


@dataclass(frozen=True)
class Climat:
    lieu: str
    nom: str
    annees: tuple[int, int]
    pluie_annuelle_mediane: float
    pluie_annuelle_q10: float
    pluie_par_mois: dict[int, float]
    mois_pic_grande_saison: int
    mois_pic_seconde: int
    mois_creux: int
    grande_saison_q10: float
    grande_saison_q90: float


def resumer(pluie: pd.Series, lieu: str, nom: str, annees: tuple[int, int] = ANNEES) -> Climat:
    """Climat d'une série de pluie journalière, en mm, sur les années complètes demandées."""
    pluie = pluie.loc[str(annees[0]):str(annees[1])]
    mensuelle = pluie.resample("MS").sum(min_count=28)
    par_mois = mensuelle.groupby(mensuelle.index.month).mean()
    annuelle = pluie.resample("YS").sum(min_count=365).dropna()
    grande = mensuelle[mensuelle.index.month.isin(range(GRANDE_SAISON[0], GRANDE_SAISON[1] + 1))]
    grande = grande.groupby(grande.index.year).sum(min_count=5).dropna()
    pic_1 = int(par_mois.loc[GRANDE_SAISON[0]:GRANDE_SAISON[1]].idxmax())
    pic_2 = int(par_mois.loc[SECONDE_FENETRE[0]:SECONDE_FENETRE[1]].idxmax())
    creux = int(par_mois.loc[pic_1:pic_2].idxmin())
    return Climat(lieu=lieu, nom=nom, annees=annees,
                  pluie_annuelle_mediane=float(annuelle.median()), pluie_annuelle_q10=float(annuelle.quantile(0.1)),
                  pluie_par_mois={int(m): float(v) for m, v in par_mois.items()},
                  mois_pic_grande_saison=pic_1, mois_pic_seconde=pic_2, mois_creux=creux,
                  grande_saison_q10=float(grande.quantile(0.1)), grande_saison_q90=float(grande.quantile(0.9)))


@functools.cache
def climat_du_lieu(identifiant: str) -> Climat:
    from .donnees import pluie_lieu, voisinage_imerg
    from .lieux import LIEUX

    lieu = LIEUX[identifiant]
    pluie = pluie_lieu(voisinage_imerg(lieu["lat"], lieu["lon"]))["moyenne"]
    return resumer(pluie, identifiant, lieu["nom"])


def executer() -> None:
    from .lieux import LIEUX

    for identifiant in LIEUX:
        c = climat_du_lieu(identifiant)
        print(f"{identifiant}, pluie annuelle médiane {c.pluie_annuelle_mediane:.0f} mm, q10 {c.pluie_annuelle_q10:.0f}, "
              f"pics {c.mois_pic_grande_saison} et {c.mois_pic_seconde}, creux {c.mois_creux}, mars à juillet de "
              f"{c.grande_saison_q10:.0f} à {c.grande_saison_q90:.0f} mm")


if __name__ == "__main__":
    executer()

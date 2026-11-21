"""Ce qui a changé entre 2001-2012 et 2013-2025, demande du responsable du 15 novembre 2026.

Le conseil repose sur des médianes 2001-2025. Ce module regarde si le climat de chaque lieu
a changé entre les deux moitiés de la période, ce qui est le cœur du défi Field Shift.

Méthode. Pour chaque indicateur, l'écart des médianes des deux périodes, son intervalle à
90 % par rééchantillonnage des années, 2 000 tirages et graine 2026, la tendance de
Mann-Kendall et la pente de Theil-Sen sur les 25 ans. Un écart est solide si son intervalle
exclut zéro. Le début des pluies est recalculé avec une seconde source de pluie
indépendante, PRECTOTCORR de MERRA-2. Un changement n'est confirmé, donc dicible à un
agriculteur, que s'il est solide avec IMERG et de même sens et solide avec MERRA-2.

Constat du 15 novembre 2026. À Korhogo, IMERG place le début des pluies 22 jours plus tard
en 2013-2025, intervalle de 9 à 29 jours, p de Mann-Kendall 0,04, même sans la case de la
ville, mais MERRA-2 le place 22 jours plus tôt, p 0,04. Les pluviomètres GHCN n'ont aucune
année complète de mars à juillet pour départager. Aucun changement n'est donc confirmé, et
AgriBot n'en annonce aucun. La baisse de la température moyenne des cycles de maïs et de
sorgho à Korhogo suit le décalage du calendrier vers des mois plus frais, et non un
refroidissement.

Limites des deux sources, notées le 17 novembre 2026. La coupure entre 2012 et 2013 tombe
près du passage d'IMERG de l'ère TRMM à l'ère GPM, le satellite GPM ayant été lancé en
2014, si bien que l'écart vu par IMERG peut venir en partie des instruments, hypothèse
non testée. La pluie corrigée de MERRA-2 avait déjà été écartée comme source principale
pour son désaccord avec IMERG et le pluviomètre de Korhogo, et sa rupture de 2020
établie sur l'Afrique ne se voit pas aux deux villes, docs/donnees.md, constat 5. Le
désaccord entre les deux sources se lit donc comme une limite des données.
"""

import numpy as np
import pandas as pd

from .indicateurs import debut_saison, mann_kendall, pente_theil_sen

FIN_PREMIERE_PERIODE = 2012
TIRAGES = 2000
GRAINE = 2026
NIVEAU = 0.90


def comparer(serie: pd.Series, fin_premiere: int = FIN_PREMIERE_PERIODE) -> dict:
    """Écart des médianes entre les deux périodes, avec son intervalle, et tendance sur toute la série."""
    serie = serie.dropna().astype(float)
    avant, apres = serie[serie.index <= fin_premiere].to_numpy(), serie[serie.index > fin_premiere].to_numpy()
    tirage = np.random.default_rng(GRAINE)
    ecarts = [np.median(tirage.choice(apres, len(apres))) - np.median(tirage.choice(avant, len(avant)))
              for _ in range(TIRAGES)]
    bas, haut = np.percentile(ecarts, [(1 - NIVEAU) / 2 * 100, (1 + NIVEAU) / 2 * 100])
    return {"mediane_avant": float(np.median(avant)), "mediane_apres": float(np.median(apres)),
            "ecart": float(np.median(apres) - np.median(avant)), "bas": float(bas), "haut": float(haut),
            "solide": bool(bas > 0 or haut < 0), "p_mann_kendall": float(mann_kendall(serie.to_numpy())[2]),
            "pente_par_decennie": float(pente_theil_sen(serie.index.to_numpy(float), serie.to_numpy()) * 10)}


def debuts(pluie: pd.Series, annees: range = range(2001, 2026)) -> pd.Series:
    return pd.Series({annee: debut_saison(pluie, annee).dayofyear for annee in annees}, dtype=float)


def confirme(principal: dict, controle: dict) -> bool:
    """Changement dicible, solide avec la source principale et de même sens et solide avec le contrôle."""
    return principal["solide"] and controle["solide"] and np.sign(principal["ecart"]) == np.sign(controle["ecart"])


def evolution_du_lieu(identifiant: str) -> pd.DataFrame:
    """Comparaison des deux périodes pour les indicateurs du lieu, et contrôle du début des pluies par MERRA-2."""
    from .donnees import lire_power, telecharger_point
    from .lieux import LIEUX
    from .recommander import donnees_du_lieu

    lieu = LIEUX[identifiant]
    annuels, contextes = donnees_du_lieu(identifiant)
    cycles = contextes["reference"].cycles
    series = {"début des pluies, jour de l'année, IMERG": annuels["debut_jour"],
              "début des pluies, jour de l'année, MERRA-2": debuts(
                  lire_power(telecharger_point(lieu["lat"], lieu["lon"], "power"))["PRECTOTCORR"]),
              "pluie annuelle, mm, IMERG": annuels["pluie_annuelle_mm"],
              "plus longue séquence sèche après le début, jours, IMERG": annuels["sequence_seche_debut_jours"]}
    for culture in ("maïs", "coton", "sorgho"):
        cycle = cycles[cycles["culture"] == culture].set_index("annee")
        series[f"{culture}, pluie moins besoin du cycle, mm"] = cycle["pluie_moins_etc_mm"]
        series[f"{culture}, séquence sèche à mi-saison, jours"] = cycle["sequence_seche_mi_saison_jours"]
    table = pd.DataFrame({nom: comparer(serie) for nom, serie in series.items()}).T
    imerg, merra = (table.loc[f"début des pluies, jour de l'année, {source}"] for source in ("IMERG", "MERRA-2"))
    table.attrs["debut_confirme"] = confirme(imerg, merra)
    return table


def changements_confirmes(identifiant: str) -> list[str]:
    """Phrases simples à dire à un agriculteur, seulement pour un changement confirmé par deux sources."""
    table = evolution_du_lieu(identifiant)
    if not table.attrs["debut_confirme"]:
        return []
    ecart = table.loc["début des pluies, jour de l'année, IMERG", "ecart"]
    semaines = round(abs(ecart) / 7)
    if semaines == 0:
        return []
    sens = "plus tard" if ecart > 0 else "plus tôt"
    return [f"Ces dernières années, les pluies commencent environ {semaines} semaine{'s' if semaines > 1 else ''} "
            f"{sens} qu'avant."]


def executer() -> None:
    from .lieux import LIEUX_ETUDE as LIEUX

    pd.set_option("display.width", 200)
    for identifiant in LIEUX:
        table = evolution_du_lieu(identifiant)
        print(f"===== {identifiant}, début des pluies confirmé par deux sources {table.attrs['debut_confirme']}")
        print(table.round(2).to_string())


if __name__ == "__main__":
    executer()

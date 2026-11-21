"""Point d'entrée unique du moteur.

recommander compare les trois stratégies retenues pour un lieu couvert et retourne une
Recommandation réelle, donnees_fictives à faux, conforme à moteur/contrat.py. Les
valeurs publiées sont arrondies, au millimètre ou au jour pour les grandeurs physiques et
au centième pour les indices et les scores, afin que les messages du bot les reprennent
exactement et que le garde-fou les retrouve.

Confiance d'une stratégie. Faible si elle contient du coton, dont la durée de cycle n'est
pas propre aux variétés ivoiriennes, ou si son rang change dans un scénario de
sensibilité. Moyenne sinon. Jamais élevée, aucun bénéfice n'étant validé localement.
"""

import functools
import json
import os
from pathlib import Path

import pandas as pd

from .contrat import (AlerteVegetation, Diagnostic, Element, Indicateur, Lieu, Poids, Recommandation, Scores, Source,
                      Strategie)
from .criteres import (CRITERES, LIBELLES, POIDS_PAR_PRIORITE, Contexte, contextes_du_lieu, evaluer, scores_criteres,
                       sensibilite, tableau_scores)
from .lieux import LIEUX
from .rotations import STRATEGIES
from .sources import source

EXEMPLE = Path(__file__).with_name("exemple.json")
EXEMPLE_ALERTE = Path(__file__).with_name("exemple_alerte.json")
EXEMPLE_DIAGNOSTIC = Path(__file__).with_name("exemple_diagnostic.json")
NOTATION = Source(nom="Notation Field Shift CI, règles visibles appliquées aux données NASA et à FAO-56",
                  reference="moteur/criteres.py et docs/decisions.md du dépôt field-shift")
SCENARIOS_EN_CLAIR = {"pluie_moins_20_pourcent": "la pluie baisse de 20 %",
                      "debut_retarde_de_14_jours": "le début des pluies est retardé de 14 jours",
                      "coton_seme_au_debut_des_pluies": "le coton est semé au début des pluies"}
INDICATEURS_PUBLIES = [
    ("pluie_annuelle", "pluie_annuelle_mm", "Pluie annuelle, moyenne des neuf cases IMERG autour de la ville",
     "mm", "mesure", "IMERG", 0),
    ("evapotranspiration_annuelle", "et0_annuelle_mm", "Évapotranspiration de référence annuelle, FAO-56",
     "mm", "calcule", "POWER, FAO56_ET0", 0),
    ("indice_aridite", "indice_aridite", "Indice d'aridité, pluie annuelle sur évapotranspiration de référence",
     "", "calcule", "IMERG, POWER, FAO56_ET0", 2),
    ("debut_saison", "debut_jour", "Début de la saison des pluies, cherché à partir du 1er mars",
     "jour de l'année", "calcule", "IMERG", 0),
    ("sequence_seche_debut", "sequence_seche_debut_jours", "Plus longue séquence sèche des 60 jours après le début",
     "jours", "calcule", "IMERG", 0),
]
AVERTISSEMENT = ("Conseil indicatif, fondé sur les données de la NASA de 2001 à 2025 et sur des connaissances "
                 "générales à confirmer localement. Il ne prédit aucun rendement. À discuter avec votre conseiller "
                 "ANADER.")


def charger_exemple() -> Recommandation:
    """Retourne la recommandation fictive qui sert à développer et tester les interfaces."""
    return Recommandation.model_validate(json.loads(EXEMPLE.read_text(encoding="utf-8")))


def charger_exemple_alerte() -> AlerteVegetation:
    """Retourne l'alerte fictive qui sert à développer et tester les interfaces."""
    return AlerteVegetation.model_validate(json.loads(EXEMPLE_ALERTE.read_text(encoding="utf-8")))


def charger_exemple_diagnostic() -> Diagnostic:
    """Retourne le diagnostic fictif qui sert à développer et tester les interfaces."""
    return Diagnostic.model_validate(json.loads(EXEMPLE_DIAGNOSTIC.read_text(encoding="utf-8")))


def arrondi(valeur: float, decimales: int) -> float:
    return float(round(valeur, decimales)) if decimales else float(round(valeur))


def indicateurs_publies(annuels: pd.DataFrame) -> list[Indicateur]:
    """Médiane de 2001 à 2025 et plage des quantiles 10 à 90 % des indicateurs annuels du lieu."""
    publies = []
    for code, colonne, texte, unite, niveau, codes, decimales in INDICATEURS_PUBLIES:
        serie = annuels[colonne].dropna()
        publies.append(Indicateur(
            code=code, texte=f"{texte}, médiane de {serie.index.min()} à {serie.index.max()}", unite=unite,
            valeur=arrondi(serie.median(), decimales), bas=arrondi(serie.quantile(0.1), decimales),
            haut=arrondi(serie.quantile(0.9), decimales), niveau=niveau, source=source(codes)))
    return publies


def en_francais(valeur: float) -> str:
    """Écrit un nombre arrondi avec une virgule décimale, sans zéro inutile."""
    return f"{valeur:g}".replace(".", ",")


def element(texte: str, niveau: str, codes: str | None) -> Element:
    return Element(texte=texte, niveau=niveau, source=source(codes) if codes else None)


def construire(identifiant: str, rotation_actuelle: str, poids: Poids, annuels: pd.DataFrame,
               contextes: dict[str, Contexte], lien_detail: str | None = None) -> Recommandation:
    """Construit la recommandation d'un lieu à partir de ses indicateurs annuels et de ses contextes de notation."""
    lieu = LIEUX[identifiant]
    table = tableau_scores(STRATEGIES, contextes["reference"], poids)
    rangs, stable, changeants = sensibilite(STRATEGIES, contextes, poids)
    strategies = []
    for s in STRATEGIES:
        scores = {c: arrondi(min(max(v, 0.0), 5.0), 2) for c, v in scores_criteres(evaluer(s, contextes["reference"])).items()}
        rang, note = int(table.loc[s.id, "rang"]), arrondi(table.loc[s.id, "note"], 2)
        changements = [f"Son rang passe de {rang} à {int(rangs.loc[s.id, nom])} si {SCENARIOS_EN_CLAIR[nom]}."
                       for nom in rangs.columns if nom != "reference" and rangs.loc[s.id, nom] != rang]
        pourquoi = [Element(texte=f"Classée {rang} sur {len(STRATEGIES)} pour ces priorités, note {en_francais(note)} sur "
                                  f"5, eau {en_francais(scores['eau'])}, {LIBELLES['revenu']} "
                                  f"{en_francais(scores['revenu'])}, {LIBELLES['sol']} {en_francais(scores['sol'])}.",
                            niveau="calcule", source=NOTATION)]
        if s.id == rotation_actuelle:
            pourquoi.append(element("Votre rotation actuelle, qui sert de référence.", "hypothese", None))
        strategies.append(Strategie(
            id=s.id, nom=s.nom, actuelle=s.id == rotation_actuelle, cultures=list(s.cultures),
            scores=Scores(**scores), pourquoi=pourquoi,
            preuves=[element(e.texte, e.niveau, e.source) for e in evaluer(s, contextes["reference"])],
            benefices=[element(a.texte, a.niveau, a.source) for a in s.benefices],
            lacunes=[element(a.texte, a.niveau, a.source) for a in s.lacunes]
            + [Element(texte=t, niveau="calcule", source=NOTATION) for t in changements],
            risques=[element(a.texte, a.niveau, a.source) for a in s.risques],
            confiance="faible" if "coton" in s.cultures or changements else "moyenne"))
    avertissement = AVERTISSEMENT
    if not stable:
        avertissement += " Ce classement change si " + " ou si ".join(SCENARIOS_EN_CLAIR[n] for n in changeants) + "."
    priorite = next((p for p, w in POIDS_PAR_PRIORITE.items()
                     if all(abs(getattr(w, c) - getattr(poids, c)) < 1e-9 for c in CRITERES)), None)
    return Recommandation(
        donnees_fictives=False, lieu=Lieu(id=identifiant, nom=lieu["nom"], lat=lieu["lat"], lon=lieu["lon"]),
        priorite=priorite, poids=poids, indicateurs=indicateurs_publies(annuels), strategies=strategies,
        classement=list(table.index), classement_stable=stable, lien_detail=lien_detail, avertissement=avertissement)


@functools.lru_cache(maxsize=None)
def donnees_du_lieu(identifiant: str) -> tuple[pd.DataFrame, dict[str, Contexte]]:
    """Indicateurs annuels et contextes de notation d'un lieu, calculés une fois par processus."""
    from .donnees import altitude_power, lire_power, pluie_lieu, telecharger_point, voisinage_imerg
    from .indicateurs import indicateurs_annuels

    lieu = LIEUX[identifiant]
    chemin_power = telecharger_point(lieu["lat"], lieu["lon"], "power")
    pluie = pluie_lieu(voisinage_imerg(lieu["lat"], lieu["lon"]))["moyenne"]
    annuels = indicateurs_annuels(pluie, lire_power(chemin_power), lieu["lat"], altitude_power(chemin_power))
    return annuels, contextes_du_lieu(identifiant)


def recommander(lieu: str, rotation_actuelle: str, poids: Poids) -> Recommandation:
    """Compare les stratégies retenues, dont la rotation actuelle, pour un lieu couvert."""
    if lieu not in LIEUX:
        raise ValueError(f"lieu hors de la zone couverte, lieux couverts {sorted(LIEUX)}")
    if LIEUX[lieu]["zone"] != "savane":
        raise ValueError(f"pas encore de rotations comparées pour la zone {LIEUX[lieu]['zone']} de {lieu}")
    if rotation_actuelle not in {s.id for s in STRATEGIES}:
        raise ValueError(f"rotation inconnue, rotations comparées {[s.id for s in STRATEGIES]}")
    priorite = next((p for p, w in POIDS_PAR_PRIORITE.items() if w == poids), "")
    lien = (f"{os.environ.get('URL_APPLICATION', 'http://localhost:8501')}/?lieu={lieu}&rotation={rotation_actuelle}"
            f"&priorite={priorite}")
    annuels, contextes = donnees_du_lieu(lieu)
    return construire(lieu, rotation_actuelle, poids, annuels, contextes, lien)

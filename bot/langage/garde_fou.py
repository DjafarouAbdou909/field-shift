"""Garde-fou de fidélité, aucun chiffre ni aucune culture qui ne vienne du moteur.

Tout texte produit par un modèle de langage passe par texte_sur avant d'être envoyé. Les
gabarits passent aussi le contrôle, ce que vérifient les tests. Les gabarits écrivent
les nombres sans séparateur de milliers, que le contrôle lirait comme deux nombres.

Limites connues
    Le contrôle vérifie qu'un nombre figure dans la recommandation, pas qu'il est attaché
    à la bonne grandeur. Un petit entier présent parmi les scores ou les rangs passe
    toujours, ce que fige le test test_limite_connue_petits_entiers. Renforcement prévu,
    contrôler les couples nombre et unité.
    Le contrôle des cultures ignore les accents, si bien que la conjonction mais est lue
    comme la culture maïs. L'erreur va dans le sens prudent, le gabarit est alors envoyé.
"""

import re
import unicodedata

from moteur.contrat import Recommandation
from moteur.cultures import CULTURES

NOMBRE = re.compile(r"\d+(?:[.,]\d+)?")
CULTURES_SURVEILLEES = CULTURES + [
    "manioc", "cacao", "café", "anacarde", "cajou", "hévéa", "palmier", "banane",
    "plantain", "tomate", "oignon", "piment", "gombo", "aubergine", "fonio", "sésame",
    "tournesol", "patate douce", "taro", "canne à sucre",
]


def _sans_accents(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if not unicodedata.combining(c))


def nombres(texte: str) -> set[float]:
    return {float(n.replace(",", ".")) for n in NOMBRE.findall(texte)}


def nombres_autorises(objet) -> set[float]:
    """Rassemble les nombres d'une recommandation, y compris ceux écrits dans ses textes."""
    if isinstance(objet, bool) or objet is None:
        return set()
    if isinstance(objet, (int, float)):
        return {abs(float(objet))}
    if isinstance(objet, str):
        return nombres(objet)
    if isinstance(objet, dict):
        objet = list(objet.values())
    if isinstance(objet, list):
        return set().union(*(nombres_autorises(v) for v in objet)) if objet else set()
    return set()


def cultures_citees(texte: str) -> set[str]:
    texte = _sans_accents(texte)
    return {c for c in CULTURES_SURVEILLEES if re.search(rf"\b{re.escape(_sans_accents(c))}\b", texte)}


def ecarts(texte: str, reco: Recommandation) -> list[str]:
    """Liste ce que le texte affirme sans que la recommandation le contienne."""
    donnees = reco.model_dump(mode="json")
    autorises = nombres_autorises(donnees) | {float(i) for i in range(1, len(reco.strategies) + 1)}
    cultures = {_sans_accents(c) for s in reco.strategies for c in s.cultures}
    problemes = [f"nombre absent du moteur {n:g}" for n in sorted(nombres(texte) - autorises)]
    problemes += [f"culture absente du moteur {c}" for c in sorted(cultures_citees(texte))
                  if _sans_accents(c) not in cultures]
    return problemes


def message_fidele(texte: str, reco: Recommandation) -> bool:
    return not ecarts(texte, reco)


def texte_sur(texte_modele: str | None, reco: Recommandation, secours: str) -> str:
    """Retourne le texte du modèle s'il est fidèle, sinon le texte de secours issu d'un gabarit."""
    if texte_modele and message_fidele(texte_modele, reco):
        return texte_modele
    return secours

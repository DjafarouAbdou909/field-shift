"""Garde-fou de fidélité, rien qui ne vienne du moteur.

Tout texte produit par un modèle de langage passe par texte_sur avant d'être envoyé, avec
un gabarit comme secours. Les gabarits passent aussi le contrôle, ce que vérifient les
tests. Le contrôle vaut pour les trois objets du contrat, la Recommandation,
l'AlerteVegetation et le Diagnostic.

Un texte est refusé s'il contient
    un nombre absent de l'objet du moteur, les rangs d'une recommandation étant permis ;
    une culture absente de l'objet du moteur ;
    un mot de traitement ou de produit, fongicide, pulvériser, dose ou acheter par exemple ;
    un nom de maladie absent de l'objet du moteur ;
    pour une alerte, une cause, sécheresse, ravageur ou maladie par exemple, l'alerte ne
    déduisant jamais de cause.
Un mot surveillé reste permis quand l'objet du moteur l'emploie lui-même, comme les
engrais cités dans une lacune d'une stratégie.

Limites connues
    Le contrôle vérifie qu'un nombre figure dans l'objet, pas qu'il est attaché à la bonne
    grandeur. Un petit entier présent parmi les scores ou les rangs passe toujours, ce que
    fige le test test_limite_connue_petits_entiers. Renforcement prévu, contrôler les
    couples nombre et unité.
    Le contrôle des cultures ignore les accents, si bien que la conjonction mais est lue
    comme la culture maïs. L'erreur va dans le sens prudent, le gabarit est alors envoyé.
    Les listes de mots surveillés sont fermées. Un traitement nommé autrement passe, d'où
    l'absence de texte libre dans le diagnostic du moteur.
    Les gabarits écrivent les nombres sans séparateur de milliers, que le contrôle lirait
    comme deux nombres.
"""

import re
import unicodedata

from moteur.contrat import AlerteVegetation, Diagnostic, Recommandation
from moteur.cultures import CULTURES
from moteur.maladies import HORS_MODELE, MALADIES

NOMBRE = re.compile(r"\d+(?:[.,]\d+)?")
CULTURES_SURVEILLEES = CULTURES + [
    "manioc", "cacao", "café", "anacarde", "cajou", "hévéa", "palmier", "banane",
    "plantain", "tomate", "oignon", "piment", "gombo", "aubergine", "fonio", "sésame",
    "tournesol", "patate douce", "taro", "canne à sucre",
]
# Racines, cherchées en début de mot et sans accents.
TRAITEMENTS = [
    "traitement", "traiter", "traitez", "fongicide", "insecticide", "pesticide", "herbicide", "bactericide",
    "nematicide", "acaricide", "phytosanitaire", "matiere active", "pulveris", "epand", "dose", "dosage",
    "produit", "acheter", "achetez", "engrais", "uree", "npk", "bouillie", "soufre", "cuivre",
]
MALADIES_SURVEILLEES = sorted(set(MALADIES) | set(HORS_MODELE) | {
    "striure", "rouille", "helminthosporiose", "bacteriose", "alternariose", "mosaique", "maladie bleue",
    "mildiou", "charbon", "virose", "fusariose", "verticilliose", "curvulariose", "anthracnose",
    "cercosporiose", "pourriture", "necrose", "fletrissement", "tache grise",
})
CAUSES = ["secheresse", "manque d'eau", "maladie", "ravageur", "chenille", "insecte", "criquet", "engrais",
          "carence", "inondation", "feu", "brulis", "pluie"]


def _sans_accents(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower().replace("’", "'"))
    return "".join(c for c in decompose if not unicodedata.combining(c))


def _contient(texte: str, terme: str, racine: bool = False) -> bool:
    fin = "" if racine else r"(?:s|x)?\b"
    return re.search(rf"\b{re.escape(_sans_accents(terme))}{fin}", _sans_accents(texte)) is not None


def nombres(texte: str) -> set[float]:
    return {float(n.replace(",", ".")) for n in NOMBRE.findall(texte)}


def nombres_autorises(objet) -> set[float]:
    """Rassemble les nombres d'un objet du moteur, y compris ceux écrits dans ses textes."""
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


def textes(objet) -> str:
    """Tous les textes d'un objet du moteur, mis bout à bout."""
    if isinstance(objet, str):
        return objet
    if isinstance(objet, dict):
        objet = list(objet.values())
    if isinstance(objet, list):
        return " ".join(textes(v) for v in objet)
    return ""


def cultures_citees(texte: str) -> set[str]:
    return {c for c in CULTURES_SURVEILLEES if _contient(texte, c)}


def ecarts(texte: str, objet: Recommandation | AlerteVegetation | Diagnostic) -> list[str]:
    """Liste ce que le texte affirme sans que l'objet du moteur le contienne."""
    donnees = objet.model_dump(mode="json")
    # La liste fermée d'un diagnostic n'autorise pas à nommer une autre maladie que celle retenue.
    moteur = textes({k: v for k, v in donnees.items() if k != "liste"})
    autorises = nombres_autorises(donnees)
    if isinstance(objet, Recommandation):
        autorises |= {float(i) for i in range(1, len(objet.strategies) + 1)}
        cultures = {_sans_accents(c) for s in objet.strategies for c in s.cultures}
    elif isinstance(objet, Diagnostic):
        cultures = {_sans_accents(objet.culture)}
    else:
        cultures = set()
    problemes = [f"nombre absent du moteur {n:g}" for n in sorted(nombres(texte) - autorises)]
    problemes += [f"culture absente du moteur {c}" for c in sorted(cultures_citees(texte))
                  if _sans_accents(c) not in cultures]
    problemes += [f"traitement ou produit {t}" for t in TRAITEMENTS
                  if _contient(texte, t, racine=True) and not _contient(moteur, t, racine=True)]
    problemes += [f"maladie absente du moteur {m}" for m in MALADIES_SURVEILLEES
                  if _contient(texte, m) and not _contient(moteur, m)]
    if isinstance(objet, AlerteVegetation):
        problemes += [f"cause non déduite par le moteur {c}" for c in CAUSES
                      if _contient(texte, c) and not _contient(moteur, c)]
    return problemes


def message_fidele(texte: str, objet: Recommandation | AlerteVegetation | Diagnostic) -> bool:
    return not ecarts(texte, objet)


def texte_sur(texte_modele: str | None, objet: Recommandation | AlerteVegetation | Diagnostic, secours: str) -> str:
    """Retourne le texte du modèle s'il est fidèle, sinon le texte de secours issu d'un gabarit."""
    if texte_modele and message_fidele(texte_modele, objet):
        return texte_modele
    return secours

"""Point d'entrée unique du moteur."""

import json
from pathlib import Path

from .contrat import Poids, Recommandation

EXEMPLE = Path(__file__).with_name("exemple.json")


def charger_exemple() -> Recommandation:
    """Retourne la recommandation fictive qui sert à développer les interfaces."""
    return Recommandation.model_validate(json.loads(EXEMPLE.read_text(encoding="utf-8")))


def recommander(lieu: str, rotation_actuelle: str, poids: Poids) -> Recommandation:
    """Compare au moins trois rotations, dont la rotation actuelle, pour un lieu.

    À écrire par le rôle données et moteur. En attendant, les interfaces utilisent
    charger_exemple().
    """
    raise NotImplementedError("moteur pas encore branché, utiliser charger_exemple()")

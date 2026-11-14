"""Moteur de comparaison des rotations, à partir des données de la NASA."""

from .contrat import AlerteVegetation, Diagnostic, Recommandation
from .recommander import charger_exemple, charger_exemple_alerte, charger_exemple_diagnostic, recommander

__all__ = ["AlerteVegetation", "Diagnostic", "Recommandation", "charger_exemple", "charger_exemple_alerte",
           "charger_exemple_diagnostic", "recommander"]

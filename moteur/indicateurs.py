"""Indicateurs climatiques et de sol par lieu, avec tendance et variabilité interannuelle.

À écrire par le rôle données et moteur. L'évapotranspiration FAO-56 et la plus longue
séquence sèche se reprennent de src/features/indicateurs.py, l'indice d'aridité de
src/recherche/zones_climatiques.py, avec mention d'origine.

Origine. rayonnement_extraterrestre et CONSTANTE_SOLAIRE viennent sans modification de
src/features/indicateurs.py dans ~/African-Crop-Yield-Intelligence au commit 2b4c18c.
"""

import numpy as np

CONSTANTE_SOLAIRE = 0.0820


def rayonnement_extraterrestre(latitude, jour):
    """Retourne le rayonnement extraterrestre journalier en MJ par m², équation 21 de FAO-56."""
    phi = np.radians(latitude)
    dr = 1 + 0.033 * np.cos(2 * np.pi * jour / 365)
    declinaison = 0.409 * np.sin(2 * np.pi * jour / 365 - 1.39)
    omega = np.arccos(np.clip(-np.tan(phi) * np.tan(declinaison), -1, 1))
    return 24 * 60 / np.pi * CONSTANTE_SOLAIRE * dr * (
        omega * np.sin(phi) * np.sin(declinaison) + np.cos(phi) * np.cos(declinaison) * np.sin(omega)
    )

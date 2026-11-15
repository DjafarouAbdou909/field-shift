"""Évapotranspiration de référence et coefficient cultural selon FAO 56.

Allen, Pereira, Raes et Smith, 1998, Crop evapotranspiration, FAO Irrigation and
Drainage Paper 56. Les numéros d'équation renvoient à ce document.
"""

import math

SIGMA = 4.903e-9  # constante de Stefan-Boltzmann, MJ K-4 m-2 jour-1


def pression_saturante(temperature: float) -> float:
    """Équation 11, en kPa."""
    return 0.6108 * math.exp(17.27 * temperature / (temperature + 237.3))


def rayonnement_extraterrestre(latitude: float, jour: int) -> float:
    """Équations 21 à 25, en MJ m-2 jour-1."""
    phi = math.radians(latitude)
    dr = 1 + 0.033 * math.cos(2 * math.pi * jour / 365)
    delta = 0.409 * math.sin(2 * math.pi * jour / 365 - 1.39)
    omega = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta))))
    return 24 * 60 / math.pi * 0.0820 * dr * (
        omega * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(omega))


def et0(tmax: float, tmin: float, ea: float, rs: float, u2: float,
        altitude: float, latitude: float, jour: int) -> float:
    """Équation 6, évapotranspiration de référence journalière en mm, avec G nul."""
    pression = 101.3 * ((293 - 0.0065 * altitude) / 293) ** 5.26
    gamma = 0.665e-3 * pression
    tmoy = (tmax + tmin) / 2
    pente = 4098 * pression_saturante(tmoy) / (tmoy + 237.3) ** 2
    es = (pression_saturante(tmax) + pression_saturante(tmin)) / 2
    rso = (0.75 + 2e-5 * altitude) * rayonnement_extraterrestre(latitude, jour)
    rnl = SIGMA * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 \
        * (0.34 - 0.14 * math.sqrt(ea)) * (1.35 * min(rs / rso, 1.0) - 0.35)
    rn = 0.77 * rs - rnl
    return (0.408 * pente * rn + gamma * 900 / (tmoy + 273) * u2 * (es - ea)) \
        / (pente + gamma * (1 + 0.34 * u2))


def kc_journalier(stades: list[int], kc: list[float]) -> list[float]:
    """Courbe du coefficient cultural jour par jour, figure 25 et équation 66."""
    l_ini, l_dev, l_mid, l_late = stades
    kc_ini, kc_mid, kc_end = kc
    courbe = [kc_ini] * l_ini
    courbe += [kc_ini + (i + 1) / l_dev * (kc_mid - kc_ini) for i in range(l_dev)]
    courbe += [kc_mid] * l_mid
    courbe += [kc_mid + (i + 1) / l_late * (kc_end - kc_mid) for i in range(l_late)]
    return courbe

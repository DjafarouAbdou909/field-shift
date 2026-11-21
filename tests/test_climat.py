"""Climat de la zone d'une ville du sud, sur une pluie synthétique puis sur les données NASA."""

import unittest

import numpy as np
import pandas as pd

from bot.dialogue import pour_la_voix
from bot.langage import gabarits
from moteur.climat import climat_du_lieu, resumer


def pluie_a_deux_saisons() -> pd.Series:
    """Pluie journalière de 2001 à 2025, forte en juin et en octobre, faible en août, et une année sur deux plus sèche."""
    jours = pd.date_range("2001-01-01", "2025-12-31", freq="D")
    par_mois = {1: 0.5, 2: 1.5, 3: 3, 4: 4, 5: 6, 6: 10, 7: 3, 8: 1.5, 9: 2.5, 10: 7, 11: 4, 12: 1}
    facteur = np.where(jours.year % 2 == 0, 0.8, 1.2)
    return pd.Series([par_mois[m] for m in jours.month], index=jours) * facteur


class TestClimat(unittest.TestCase):
    def test_saisons_et_creux(self):
        c = resumer(pluie_a_deux_saisons(), "essai", "Essai")
        self.assertEqual((c.mois_pic_grande_saison, c.mois_pic_seconde, c.mois_creux), (6, 10, 8))
        self.assertLess(c.pluie_annuelle_q10, c.pluie_annuelle_mediane)
        self.assertLess(c.grande_saison_q10, c.grande_saison_q90)
        self.assertEqual(c.annees, (2001, 2025))

    def test_message_sans_date_de_debut_et_lu_en_entier(self):
        texte = gabarits.climat(resumer(pluie_a_deux_saisons(), "essai", "Abidjan"))
        self.assertIn("zone d'Abidjan", texte)
        self.assertIn("juin", texte)
        self.assertIn("octobre", texte)
        self.assertIn("août", texte)
        self.assertNotIn("commencent", texte)
        self.assertIn("millimètres", pour_la_voix(texte))

    def test_abidjan_sur_les_donnees_nasa(self):
        c = climat_du_lieu("abidjan")
        self.assertEqual((c.mois_pic_grande_saison, c.mois_pic_seconde, c.mois_creux), (6, 10, 8))
        self.assertGreater(c.pluie_par_mois[6], 2 * c.pluie_par_mois[8])


if __name__ == "__main__":
    unittest.main()

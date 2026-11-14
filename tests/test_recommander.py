import re
import unittest
from pathlib import Path

import pandas as pd

from bot.langage.gabarits import resume
from bot.langage.garde_fou import ecarts
from moteur.contrat import Recommandation
from moteur.criteres import POIDS_PAR_PRIORITE, Contexte
from moteur.donnees import DOSSIER_POWER
from moteur.recommander import construire, recommander
from moteur.sources import SOURCES

REGISTRE = Path(__file__).resolve().parents[1] / "docs" / "sources.md"
DONNEES_PRESENTES = (DOSSIER_POWER / "registre.csv").exists()


def cycles(ecarts_par_culture: dict[str, list[float]]) -> pd.DataFrame:
    return pd.DataFrame([{"culture": c, "annee": 2001 + k, "pluie_moins_etc_mm": e, "sequence_seche_mi_saison_jours": 3}
                         for c, valeurs in ecarts_par_culture.items() for k, e in enumerate(valeurs)])


def annuels() -> pd.DataFrame:
    """Dix années, pluie de 1000 à 1900 mm par pas de 100, médiane 1450, quantiles 10 et 90 % 1090 et 1810."""
    return pd.DataFrame({"pluie_annuelle_mm": [1000.0 + 100 * k for k in range(10)],
                         "et0_annuelle_mm": [2000.0] * 10, "indice_aridite": [0.5 + 0.05 * k for k in range(10)],
                         "debut_jour": [100.0] * 10, "sequence_seche_debut_jours": [5.0] * 10},
                        index=range(2001, 2011))


def contextes(secheresse_coton: bool = False) -> dict[str, Contexte]:
    reference = cycles({c: [1.0] * 4 for c in ["coton", "maïs", "niébé", "sorgho"]})
    sec = cycles({"coton": [-1.0] * 4, "maïs": [-1.0] * 4, "niébé": [1.0] * 4, "sorgho": [1.0] * 4})
    return {"reference": Contexte("korhogo", "reference", reference),
            "pluie_moins_20_pourcent": Contexte("korhogo", "pluie_moins_20_pourcent", sec if secheresse_coton else reference)}


class TestConstruire(unittest.TestCase):
    def test_recommandation_valide_et_reelle(self):
        """Indicateur de pluie, médiane 1450 mm, plage 1090 à 1810 mm, niveau mesure avec sa source."""
        reco = construire("korhogo", "coton_mais", POIDS_PAR_PRIORITE["eau"], annuels(), contextes())
        self.assertIsInstance(reco, Recommandation)
        self.assertFalse(reco.donnees_fictives)
        self.assertEqual(reco.priorite, "eau")
        pluie = next(i for i in reco.indicateurs if i.code == "pluie_annuelle")
        self.assertEqual((pluie.valeur, pluie.bas, pluie.haut, pluie.niveau), (1450.0, 1090.0, 1810.0, "mesure"))
        self.assertEqual(sum(s.actuelle for s in reco.strategies), 1)
        self.assertTrue(next(s for s in reco.strategies if s.id == "coton_mais").actuelle)
        self.assertTrue(reco.classement_stable)

    def test_scenario_qui_change_le_classement_est_nomme(self):
        """Priorité eau. Référence, eau 5 partout, coton, niébé puis maïs 3 + 1/3 + 1/3 = 3,667, les autres 3,5.

        Scénario sec, coton et maïs ne couvrent plus leur besoin. Coton puis maïs, eau (0 + 5) / 2, note 1,5 + 0,5 = 2.
        Coton, niébé puis maïs, eau (5/3 + 5) / 2, note 2 + 2/3 = 2,667. Sorgho puis niébé, eau 5, note 3,5, premier.
        """
        reco = construire("korhogo", "coton_mais", POIDS_PAR_PRIORITE["eau"], annuels(), contextes(True))
        self.assertFalse(reco.classement_stable)
        self.assertIn("la pluie baisse de 20 %", reco.avertissement)
        lacunes = [e.texte for s in reco.strategies for e in s.lacunes]
        self.assertTrue(any("Son rang passe de" in t for t in lacunes))

    def test_confiance(self):
        reco = construire("korhogo", "coton_mais", POIDS_PAR_PRIORITE["eau"], annuels(), contextes())
        confiances = {s.id: s.confiance for s in reco.strategies}
        self.assertEqual(confiances, {"coton_mais": "faible", "coton_niebe_mais": "faible", "sorgho_niebe": "moyenne"})

    def test_rotation_ou_lieu_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            recommander("abidjan", "coton_mais", POIDS_PAR_PRIORITE["eau"])
        with self.assertRaises(ValueError):
            recommander("korhogo", "igname_mais", POIDS_PAR_PRIORITE["eau"])

    def test_codes_de_sources_au_registre(self):
        codes = set(re.findall(r"^\| ([A-Z0-9_]+) \|", REGISTRE.read_text(encoding="utf-8"), flags=re.M))
        self.assertTrue(set(SOURCES) - {"IMERG", "POWER"} <= codes, set(SOURCES) - codes)


@unittest.skipUnless(DONNEES_PRESENTES, "séries NASA absentes de data/raw, lancer venv/bin/python -m moteur.controles")
class TestRecommanderDonneesReelles(unittest.TestCase):
    def test_korhogo_et_bouake_pour_chaque_priorite(self):
        for lieu in ["korhogo", "bouake"]:
            for priorite, poids in POIDS_PAR_PRIORITE.items():
                reco = recommander(lieu, "coton_mais", poids)
                self.assertFalse(reco.donnees_fictives)
                self.assertEqual(reco.priorite, priorite)
                self.assertEqual(len(reco.strategies), 3)
                elements = [e for s in reco.strategies for e in s.pourquoi + s.preuves + s.benefices + s.lacunes + s.risques]
                self.assertTrue(all(e.source is not None for e in elements if e.niveau != "hypothese"))
                self.assertEqual(ecarts(resume(reco), reco), [], f"{lieu} {priorite}")

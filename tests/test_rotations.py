import re
import unittest
from pathlib import Path

from moteur.cultures import cultures_comparees
from moteur.rotations import STRATEGIES

REGISTRE = Path(__file__).resolve().parents[1] / "docs" / "sources.md"


class TestStrategies(unittest.TestCase):
    def test_trois_strategies_dont_une_actuelle(self):
        self.assertGreaterEqual(len(STRATEGIES), 3)
        self.assertEqual(sum(s.actuelle for s in STRATEGIES), 1)
        self.assertEqual(len({s.id for s in STRATEGIES}), len(STRATEGIES))

    def test_cultures_comparees_seulement(self):
        for strategie in STRATEGIES:
            self.assertTrue(set(strategie.cultures) <= set(cultures_comparees()), strategie.id)
            self.assertNotIn("arachide", strategie.cultures)

    def test_chaque_appui_a_un_niveau_et_une_source_connue(self):
        codes = set(re.findall(r"^\| ([A-Z0-9_]+) \|", REGISTRE.read_text(encoding="utf-8"), flags=re.M))
        for strategie in STRATEGIES:
            for appui in strategie.benefices + strategie.lacunes + strategie.risques:
                self.assertIn(appui.niveau, {"mesure", "calcule", "hypothese"})
                if appui.niveau != "hypothese":
                    self.assertIsNotNone(appui.source, appui.texte)
                if appui.source:
                    for code in appui.source.split(", "):
                        self.assertIn(code, codes, appui.texte)

    def test_au_moins_un_benefice_source_par_strategie(self):
        for strategie in STRATEGIES:
            self.assertTrue(any(a.source for a in strategie.benefices), strategie.id)


if __name__ == "__main__":
    unittest.main()

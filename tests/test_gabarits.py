import unittest

from bot.langage import gabarits
from bot.langage.garde_fou import _contient, TRAITEMENTS, ecarts, message_fidele
from moteur import charger_exemple, charger_exemple_alerte, charger_exemple_diagnostic, recommander
from moteur.contrat import MESSAGES_DIAGNOSTIC, Diagnostic
from moteur.criteres import POIDS_PAR_PRIORITE
from moteur.diagnostic import ORIGINE
from moteur.lieux import LIEUX
from moteur.maladies import liste, source_maladie
from moteur.rotations import STRATEGIES


def diagnostic(statut, maladie=None, culture="maïs"):
    return Diagnostic(donnees_fictives=False, culture=culture, statut=statut, maladie=maladie, confiance=0.8,
                      liste=liste(culture), source_maladie=source_maladie(maladie) if maladie else None,
                      origine_images=ORIGINE, avertissement=MESSAGES_DIAGNOSTIC[statut])


class TestGabaritsSurDonneesReelles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recos = [recommander(lieu, rotation.id, poids) for lieu in LIEUX for rotation in STRATEGIES
                     for poids in POIDS_PAR_PRIORITE.values()]

    def test_messages_du_resultat_fideles(self):
        """Résumé, raisons et détail passent le garde-fou pour chaque lieu, rotation et priorité."""
        for reco in self.recos:
            for message in (gabarits.resume(reco), gabarits.pourquoi(reco), gabarits.detail(reco)):
                self.assertEqual(ecarts(message, reco), [], message)

    def test_classement_instable_sans_cause_inventee(self):
        """L'ancien gabarit annonçait à tort une saison plus sèche, le scénario vient de l'avertissement du moteur."""
        instables = [r for r in self.recos if not r.classement_stable]
        self.assertTrue(instables)
        for reco in instables:
            texte = gabarits.resume(reco)
            self.assertNotIn("plus sèche", texte)
            self.assertIn("Ce classement change si", texte)


class TestGabarits(unittest.TestCase):
    def test_boutons_et_listes_dans_les_limites(self):
        for boutons in (gabarits.BOUTONS_CONSENTEMENT, gabarits.BOUTONS_PRIORITE, gabarits.BOUTONS_RESULTAT,
                        gabarits.BOUTONS_CULTURE_PHOTO, gabarits.BOUTONS_CONSENTEMENT_PHOTO):
            self.assertLessEqual(len(boutons), 3)
            self.assertTrue(all(len(titre) <= 20 for titre in boutons.values()), boutons)
        for lignes in (gabarits.LIGNES_LIEUX, gabarits.LIGNES_ROTATIONS):
            self.assertLessEqual(len(lignes), 10)
            self.assertTrue(all(len(titre) <= 24 for titre in lignes.values()), lignes)

    def test_identifiants_reconnus_par_le_moteur(self):
        self.assertEqual(set(gabarits.BOUTONS_PRIORITE), set(POIDS_PAR_PRIORITE))
        self.assertEqual(set(gabarits.LIGNES_LIEUX), set(LIEUX))
        self.assertEqual(set(gabarits.LIGNES_ROTATIONS), {s.id for s in STRATEGIES})
        self.assertEqual(set(gabarits.BOUTONS_CULTURE_PHOTO), {"maïs", "coton"})

    def test_messages_fixes_sans_traitement(self):
        for message in (gabarits.accueil(), gabarits.refus(), gabarits.demande_lieu(), gabarits.zone_non_couverte(),
                        gabarits.demande_rotation(), gabarits.demande_priorite(), gabarits.demande_culture_photo(),
                        gabarits.consentement_photo(), gabarits.demande_photo(), gabarits.refus_photo(),
                        gabarits.incompris(), gabarits.erreur_technique()):
            self.assertFalse([t for t in TRAITEMENTS if _contient(message, t, racine=True)], message)

    def test_consentement_photo_explicite(self):
        texte = gabarits.consentement_photo()
        self.assertIn("Google", texte)
        self.assertIn("ne garde pas", texte)

    def test_zone_non_couverte_nomme_les_zones(self):
        texte = gabarits.zone_non_couverte()
        self.assertTrue(all(lieu["nom"] in texte for lieu in LIEUX.values()))

    def test_diagnostic_maladie_possible(self):
        d = diagnostic("maladie_possible", "striure du maïs")
        texte = gabarits.diagnostic(d)
        self.assertEqual(texte, "Maladie possible, striure du maïs, à faire confirmer par votre conseiller ANADER.")
        self.assertEqual(ecarts(texte, d), [])

    def test_diagnostic_sans_maladie(self):
        for statut in ("aucune_maladie_reconnue", "inconnu"):
            d = diagnostic(statut)
            self.assertEqual(gabarits.diagnostic(d), MESSAGES_DIAGNOSTIC[statut])
            self.assertEqual(ecarts(gabarits.diagnostic(d), d), [])

    def test_exemples_fictifs_marques(self):
        self.assertTrue(gabarits.alerte(charger_exemple_alerte()).startswith("[TEST"))
        self.assertTrue(gabarits.diagnostic(charger_exemple_diagnostic()).startswith("[TEST"))
        self.assertTrue(gabarits.resume(charger_exemple()).startswith("[TEST"))

    def test_alerte_fidele(self):
        a = charger_exemple_alerte()
        self.assertEqual(ecarts(gabarits.alerte(a), a), [])


class TestGardeFouEtendu(unittest.TestCase):
    def test_traitement_refuse(self):
        d = diagnostic("maladie_possible", "rouille commune du maïs")
        for texte in ("Pulvérisez un fongicide sur les feuilles.", "Achetez le bon produit.",
                      "Appliquez une dose de cuivre.", "Un traitement s'impose."):
            self.assertFalse(message_fidele(texte, d), texte)

    def test_autre_maladie_refusee(self):
        d = diagnostic("maladie_possible", "striure du maïs")
        self.assertFalse(message_fidele("Maladie possible, rouille commune du maïs.", d))
        self.assertFalse(message_fidele("Cela ressemble à du mildiou.", d))
        self.assertTrue(message_fidele("Maladie possible, striure du maïs.", d))

    def test_aucune_maladie_ne_nomme_rien(self):
        d = diagnostic("aucune_maladie_reconnue")
        self.assertFalse(message_fidele("Ce n'est pas de la striure.", d))

    def test_alerte_sans_cause(self):
        a = charger_exemple_alerte()
        for texte in ("La végétation est faible à cause de la sécheresse.", "Des chenilles attaquent le champ.",
                      "Il manque de l'engrais."):
            self.assertFalse(message_fidele(texte, a), texte)
        self.assertTrue(message_fidele("Regardez les feuilles au champ.", a), "feuille n'est pas le mot feu")

    def test_mot_permis_quand_le_moteur_l_emploie(self):
        """Une lacune du moteur parle des engrais du coton, un texte qui la reprend reste fidèle."""
        reco = recommander("korhogo", "coton_mais", POIDS_PAR_PRIORITE["revenu"])
        self.assertTrue(any("engrais" in e.texte for s in reco.strategies for e in s.lacunes))
        self.assertTrue(message_fidele("L'arrière-effet des engrais du coton n'est pas prouvé.", reco))
        self.assertFalse(message_fidele("Pulvérisez un herbicide.", reco))


if __name__ == "__main__":
    unittest.main()

"""Évaluation de la sortie de recommander, phase 5 de CRISP-DM.

Il n'existe pas de vérité terrain sur la meilleure rotation. L'évaluation ne mesure donc
pas une précision. Elle vérifie que chaque recommandation est conforme au contrat, que
ses résultats ne contredisent pas les connaissances agronomiques établies, et comment son
classement dépend des choix incertains, date de semis et durée du cycle du coton.

Exécution depuis la racine du dépôt
    venv/bin/python -m moteur.evaluation
"""

import pandas as pd

from .contrat import Recommandation

LEGUMINEUSES = {"niébé", "arachide", "soja"}
KY_FAO56 = {"maïs": 1.25, "sorgho": 0.9, "coton": 0.85, "soja": 0.85, "arachide": 0.70}


def verifier_contrat(reco: Recommandation) -> dict[str, bool]:
    """Conformité d'une recommandation aux exigences du cadrage et de CLAUDE.md."""
    elements = [e for s in reco.strategies for e in s.pourquoi + s.preuves + s.benefices + s.lacunes + s.risques]
    return {
        "donnees_reelles": not reco.donnees_fictives,
        "au_moins_trois_strategies": len(reco.strategies) >= 3,
        "une_seule_rotation_actuelle": sum(s.actuelle for s in reco.strategies) == 1,
        "mesure_et_calcule_sources": all(e.source is not None for e in elements if e.niveau != "hypothese"),
        "indicateurs_avec_plage": all(i.bas <= i.valeur <= i.haut and i.bas < i.haut for i in reco.indicateurs),
        "chaque_strategie_a_ses_elements": all(s.pourquoi and s.preuves for s in reco.strategies),
        "instabilite_nommee": reco.classement_stable or "Ce classement change si" in reco.avertissement,
    }


def score(reco: Recommandation, strategie: str, critere: str) -> float:
    return getattr(next(s for s in reco.strategies if s.id == strategie).scores, critere)


def bon_sens_strategies(reco: Recommandation) -> list[dict]:
    """Vérifications portant sur les scores publiés d'une recommandation."""
    avec_legumineuse = [s for s in reco.strategies if LEGUMINEUSES & set(s.cultures)]
    sans_legumineuse = [s for s in reco.strategies if not LEGUMINEUSES & set(s.cultures)]
    return [
        {"verification": "une rotation avec légumineuse a un meilleur score d'apport d'azote qu'une rotation sans",
         "resultat": min(s.scores.sol for s in avec_legumineuse) > max(s.scores.sol for s in sans_legumineuse),
         "valeurs": f"avec {sorted(s.scores.sol for s in avec_legumineuse)}, sans "
                    f"{sorted(s.scores.sol for s in sans_legumineuse)}",
         "portee": "vrai par construction du critère, ce n'est pas une vérification indépendante"},
        {"verification": "sorgho puis niébé a un score d'eau au moins égal à coton puis maïs",
         "resultat": score(reco, "sorgho_niebe", "eau") >= score(reco, "coton_mais", "eau"),
         "valeurs": f"{score(reco, 'sorgho_niebe', 'eau')} contre {score(reco, 'coton_mais', 'eau')}",
         "portee": "compare deux rotations qui diffèrent par le coton autant que par le maïs"},
    ]


def bon_sens_cultures(parts: pd.DataFrame, besoins: pd.Series) -> list[dict]:
    """Vérifications culture par culture, sorgho et mil face au maïs, et cohérence avec le facteur Ky de FAO-56.

    parts vient de criteres.parts_par_culture, besoins est le besoin en eau médian par culture.
    """
    lignes = []
    for culture in ["sorgho", "mil"]:
        lignes.append({
            "verification": f"le {culture} demande moins d'eau que le maïs sur son cycle",
            "resultat": bool(besoins[culture] < besoins["maïs"]),
            "valeurs": f"{besoins[culture]:.0f} mm contre {besoins['maïs']:.0f} mm",
            "portee": "besoin FAO-56 en conditions standard, pas une tolérance à la sécheresse"})
        lignes.append({
            "verification": f"la pluie couvre le besoin du {culture} au moins aussi souvent que celui du maïs",
            "resultat": bool(parts.loc[culture, "couverture_du_besoin"] >= parts.loc["maïs", "couverture_du_besoin"]),
            "valeurs": f"{parts.loc[culture, 'couverture_du_besoin']:.2f} contre "
                       f"{parts.loc['maïs', 'couverture_du_besoin']:.2f}",
            "portee": "dépend aussi de la durée du cycle et de la date de semis"})
    lignes.append({
        "verification": "FAO-56 attribue au maïs une plus forte sensibilité du rendement au manque d'eau qu'au sorgho",
        "resultat": KY_FAO56["maïs"] > KY_FAO56["sorgho"],
        "valeurs": f"Ky {KY_FAO56['maïs']} contre {KY_FAO56['sorgho']}, tableau 24",
        "portee": "connaissance sourcée, le facteur Ky n'entre pas dans les scores"})
    return lignes


def scores_publies(recommandations: dict[str, Recommandation]) -> pd.DataFrame:
    """Scores publiés de chaque stratégie, par recommandation et par critère."""
    return pd.DataFrame({(nom, critere): {s.id: getattr(s.scores, critere) for s in r.strategies}
                         for nom, r in recommandations.items() for critere in ["eau", "revenu", "sol"]})


def classements(recommandations: dict[str, Recommandation]) -> pd.DataFrame:
    """Classement publié de chaque recommandation, une colonne par variante."""
    return pd.DataFrame({nom: {sid: rang for rang, sid in enumerate(r.classement, start=1)}
                         for nom, r in recommandations.items()})


def variantes_coton(identifiant: str, poids) -> dict[str, Recommandation]:
    """Recommandations construites comme recommander, avec chaque date de semis et chaque durée du coton."""
    from .criteres import contextes_du_lieu
    from .cultures import avec_stades_coton, variantes_duree_coton
    from .recommander import construire, donnees_du_lieu

    annuels, contextes = donnees_du_lieu(identifiant)
    resultats = {"reference": construire(identifiant, "coton_mais", poids, annuels, contextes)}
    semis_pluies = dict(contextes, reference=contextes["coton_seme_au_debut_des_pluies"])
    resultats["semis_au_debut_des_pluies"] = construire(identifiant, "coton_mais", poids, annuels, semis_pluies)
    for position in ["debut", "fin"]:
        resultats[f"semis_{position}_de_fenetre"] = construire(identifiant, "coton_mais", poids, annuels,
                                                               contextes_du_lieu(identifiant, position))
    for nom, stades in variantes_duree_coton().items():
        if nom != "fao56_reference_195":
            resultats[nom] = construire(identifiant, "coton_mais", poids, annuels,
                                        contextes_du_lieu(identifiant, "milieu", *avec_stades_coton(stades)))
    return resultats


def executer() -> None:
    from bot.langage.gabarits import resume
    from bot.langage.garde_fou import ecarts

    from .criteres import POIDS_PAR_PRIORITE, parts_par_culture
    from .lieux import LIEUX
    from .recommander import donnees_du_lieu, recommander

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.max_colwidth", 90)
    conformite = {}
    for identifiant, lieu in LIEUX.items():
        for priorite, poids in POIDS_PAR_PRIORITE.items():
            reco = recommander(identifiant, "coton_mais", poids)
            conformite[(lieu["nom"], priorite)] = {**verifier_contrat(reco), "message_du_bot_fidele": not ecarts(resume(reco), reco)}
    print("===== Conformité de chaque recommandation")
    print(pd.DataFrame(conformite).to_string())
    print("\n===== Scores publiés, priorité eau")
    print(scores_publies({lieu["nom"]: recommander(i, "coton_mais", POIDS_PAR_PRIORITE["eau"])
                          for i, lieu in LIEUX.items()}).to_string())
    for identifiant, lieu in LIEUX.items():
        _, contextes = donnees_du_lieu(identifiant)
        cycles = contextes["reference"].cycles
        besoins = cycles.groupby("culture")["etc_cycle_mm"].median()
        print(f"\n===== Bon sens, {lieu['nom']}")
        reco = recommander(identifiant, "coton_mais", POIDS_PAR_PRIORITE["eau"])
        print(pd.DataFrame(bon_sens_strategies(reco) + bon_sens_cultures(parts_par_culture(contextes["reference"]),
                                                                         besoins)).to_string(index=False))
        for priorite, poids in POIDS_PAR_PRIORITE.items():
            print(f"\nClassement publié selon le semis et la durée du coton, {lieu['nom']}, priorité {priorite}")
            print(classements(variantes_coton(identifiant, poids)).to_string())


if __name__ == "__main__":
    executer()

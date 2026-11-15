"""Calcule toutes les recommandations et les exporte pour l'application hors connexion.

    python -m moteur.exporter

Chaque texte est produit ici, à partir des résultats du moteur. L'application ne fait
que les afficher, et ne calcule ni n'invente aucun chiffre.
"""

import copy
import json
import statistics
from datetime import datetime, timezone

from donnees.config import RACINE, charger

from .criteres import debuts_par_annee, sensibilite
from .saison import faux_departs
from .series import series_lieux
from .statistiques import quartiles, tendance

SORTIE = RACINE / "app" / "donnees" / "recommandations.json"
DOSSIER_AUDIO = RACINE / "app" / "audio"
FORMATS_AUDIO = [".mp3", ".m4a", ".ogg"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
SOURCE_NASA = "NASA GPM IMERG et NASA POWER, 2001 à 2024"
SOURCE_FAO = "FAO 56, tableaux 11 et 12"
CRITERES = {"eau": "Eau", "sol": "Sol", "debouche": "Débouché"}


def nombre(x: float, decimales: int = 0) -> str:
    return f"{x:.{decimales}f}".replace(".", ",").replace("-", "moins ")


def date_texte(jour_annee: float) -> str:
    from datetime import date, timedelta
    d = date(2001, 1, 1) + timedelta(days=round(jour_annee) - 1)
    return f"{d.day} {MOIS[d.month - 1]}"


def de_la(nom: str) -> str:
    return f"de l'{nom}" if nom[0] in "aeiouéèh" else f"du {nom}"


def tendances_debut(serie: dict, config: dict) -> list[tuple[int, float, float, float]]:
    """Tendance du début des pluies avec le critère retenu, puis avec chaque variante."""
    resultat = []
    for duree in [config["saison"]["sequence_seche_max_jours"]] + config["saison"]["variantes_sequence_seche"]:
        variante = copy.deepcopy(config)
        variante["saison"]["sequence_seche_max_jours"] = duree
        trouves = {a: d.timetuple().tm_yday for a, d in debuts_par_annee(serie, variante).items() if d}
        resultat.append((duree, *tendance(list(trouves), list(trouves.values()))))
    return resultat


def texte_tendance(tendances: list) -> tuple[str, str]:
    duree, pente, bas, haut = tendances[0]
    robuste = all(b > 0 for _, _, b, _ in tendances) or all(h < 0 for _, _, _, h in tendances)
    detail = " ".join(f"Avec {d} jours secs au plus, {nombre(p, 1)} jours par décennie, intervalle à 95 % "
                      f"de {nombre(b, 1)} à {nombre(h, 1)}." for d, p, b, h in tendances)
    if robuste:
        sens = "plus tard" if pente > 0 else "plus tôt"
        return (f"Le début des pluies arrive de plus en plus {sens}, d'environ {nombre(abs(pente), 0)} jours "
                f"par décennie, quel que soit le critère retenu.", detail)
    return ("Aucune tendance robuste du début des pluies n'est établie, le résultat dépend du critère retenu.",
            detail)


def indicateurs(serie: dict, debuts: dict, config: dict) -> list[dict]:
    trouves = {a: d.timetuple().tm_yday for a, d in debuts.items() if d}
    q1, med, q3 = quartiles(list(trouves.values()))
    texte, detail = texte_tendance(tendances_debut(serie, config))
    annuelles = {}
    for jour, pluie in zip(serie["jours"], serie["pluie"]):
        annuelles[jour.year] = annuelles.get(jour.year, 0.0) + pluie
    p_pente, p_bas, p_haut = tendance(list(annuelles), list(annuelles.values()))
    return [
        {"texte": f"Les pluies démarrent en général vers le {date_texte(med)}, entre le {date_texte(q1)} "
                  f"et le {date_texte(q3)} une année sur deux.",
         "niveau": "calcule", "source": SOURCE_NASA,
         "detail": f"Début trouvé {len(trouves)} années sur {len(debuts)}."},
        {"texte": texte, "niveau": "calcule", "source": SOURCE_NASA, "detail": detail},
        {"texte": f"Pluie annuelle moyenne {nombre(statistics.mean(annuelles.values()))} mm, écart type "
                  f"{nombre(statistics.stdev(annuelles.values()))} mm.",
         "niveau": "mesure", "source": SOURCE_NASA, "detail": ""},
        {"texte": f"Tendance de la pluie annuelle, {nombre(p_pente)} mm par décennie, intervalle à 95 % "
                  f"de {nombre(p_bas)} à {nombre(p_haut)}.",
         "niveau": "calcule", "source": SOURCE_NASA, "detail": ""},
    ]


def explications(rotation: dict, scores: dict, cultures: dict) -> list[dict]:
    elements = []
    for c, couv in scores["cultures"].items():
        elements.append({
            "texte": f"Au stade de pleine croissance, la pluie a couvert le besoin en eau "
                     f"{de_la(cultures[c]['nom'])} {couv['couvertes']} années sur {couv['annees']}.",
            "niveau": "calcule", "source": f"{SOURCE_NASA}, {SOURCE_FAO}",
            "detail": f"Intervalle à 95 % de {nombre(100 * couv['bas'])} à {nombre(100 * couv['haut'])} %."})
    n, leg = len(rotation["cultures"]), sum(cultures[c]["legumineuse"] for c in rotation["cultures"])
    elements.append({
        "texte": f"{leg} année de légumineuse sur {n}." if leg else f"Aucune légumineuse sur {n} années.",
        "niveau": "hypothese", "source": "",
        "detail": "On suppose que les légumineuses enrichissent le sol en azote. À confirmer localement."})
    elements.append({
        "texte": f"{rotation['cultures'].count('coton')} année de coton sur {n}.",
        "niveau": "hypothese", "source": "",
        "detail": "On suppose que le coton offre un débouché organisé. À confirmer localement."})
    return elements


def le_la(nom: str) -> str:
    return f"l'{nom}" if nom[0] in "aeiouéèh" else f"le {nom}"


def au(nom: str) -> str:
    return f"à l'{nom}" if nom[0] in "aeiouéèh" else f"au {nom}"


def conseil_court(priorite: str, strategies: list[dict], couvertures: dict, cultures: dict) -> str:
    """Trois phrases au plus, pour un agriculteur. Le détail chiffré est dans conseil.

    La raison retenue est celle du critère de la priorité si l'écart avec la rotation
    actuelle atteint 0,05, sinon celle du premier autre critère qui atteint cet écart.
    """
    actuelle = next(s for s in strategies if s["actuelle"])
    tete = [s for s in strategies if s["rang"] == 1]
    fin = "Parlez-en à votre agent ANADER avant de changer."
    if actuelle in tete and len(tete) == 1:
        return (f"Gardez votre rotation actuelle, {actuelle['nom'].lower()}.\n"
                "Chez vous, les autres rotations ne font pas mieux pour ce qui compte pour vous.\n" + fin)
    conseillees = [s for s in tete if not s["actuelle"]]
    if len(conseillees) == 1:
        ligne = f"Rotation conseillée, {conseillees[0]['nom'].lower()}."
    else:
        ligne = f"{len(conseillees)} rotations sont conseillées, au choix.\n" + "\n".join(
            f"{i}. {s['nom']}" for i, s in enumerate(conseillees, start=1))
    meilleure = conseillees[0]
    plusieurs = len(conseillees) > 1
    raisons = []
    for critere in [priorite] + [c for c in ("eau", "sol", "debouche") if c != priorite]:
        if critere == "eau":
            nouvelles = [c for c in meilleure["cultures"] if c not in actuelle["cultures"]]
            remplacees = [c for c in actuelle["cultures"] if c not in meilleure["cultures"]]
            part = lambda c: couvertures[c]["couvertes"] / couvertures[c]["annees"]
            for n in sorted(nouvelles, key=part, reverse=True):
                for r in remplacees:
                    if part(n) - part(r) >= 0.05:
                        avec = f"Avec la rotation {meilleure['nom'].lower()}, la" if plusieurs else "Chez vous, la"
                        raisons.append(f"{avec} pluie suffit plus souvent {au(cultures[n]['nom'])} "
                                       f"qu'{au(cultures[r]['nom'])}.")
                        break
                if raisons:
                    break
        elif meilleure["scores"][critere] - actuelle["scores"][critere] >= 0.05:
            if critere == "sol" and plusieurs and all(
                    any(cultures[c]["legumineuse"] for c in s["cultures"]) for s in conseillees):
                raisons.append("Toutes deux ajoutent une légumineuse, qui peut enrichir votre sol."
                               if len(conseillees) == 2 else "Toutes ajoutent une légumineuse, qui peut enrichir votre sol.")
            elif critere == "sol":
                legume = next(c for c in meilleure["cultures"] if cultures[c]["legumineuse"])
                sujet = f"La rotation {meilleure['nom'].lower()} ajoute" if plusieurs else "Elle ajoute"
                raisons.append(f"{sujet} {le_la(cultures[legume]['nom'])}, une légumineuse qui peut enrichir votre sol.")
            else:
                raisons.append("Elle garde plus de coton à vendre.")
        if raisons:
            break
    return "\n".join([ligne] + raisons[:1] + [fin])


def texte_faux_departs(faux: int, evaluees: int, critere: dict) -> str:
    return (f"Attention aux faux départs. Chez vous, {faux} années sur {evaluees}, les premières pluies ont été "
            f"suivies de plus de {critere['sequence_seche_max_jours']} jours sans pluie. Attendez que la pluie soit "
            "bien installée, et demandez conseil à votre agent ANADER.")


def conseil(contexte: dict, strategies: list[dict], couvertures: dict, cultures: dict) -> str:
    """Message de résultat, affiché et lu à voix haute, écrit pour un agriculteur.

    contexte contient lieu, priorite, debut_pluies, stabilite et avertissement.
    couvertures donne, par culture, les années où la pluie a couvert le besoin en eau.
    Chaque chiffre vient du moteur. Les comparaisons tolèrent un écart de 0,05 sur des
    scores de 0 à 1, en deçà duquel deux rotations sont dites équivalentes.
    """
    actuelle = next(s for s in strategies if s["actuelle"])
    tete = [s for s in strategies if s["rang"] == 1]
    lignes = [f"Pour votre champ près de {contexte['lieu']}, avec la priorité {contexte['priorite'].lower()}.",
              f"Chez vous, les pluies démarrent en général vers le {contexte['debut_pluies']}."]
    if actuelle in tete and len(tete) == 1:
        lignes.append(f"Votre rotation actuelle, {actuelle['nom'].lower()}, reste la mieux placée pour cette priorité.")
    else:
        conseillees = [s for s in tete if not s["actuelle"]]
        if len(tete) == 1:
            lignes.append(f"Je vous propose d'étudier la rotation {conseillees[0]['nom'].lower()}.")
        else:
            noms = " et ".join(s["nom"].lower() for s in tete)
            lignes.append(f"{len(tete)} rotations arrivent à égalité en tête, {noms}.")
        meilleure = conseillees[0]
        nouvelles = [c for c in meilleure["cultures"] if c not in actuelle["cultures"]]
        for c in nouvelles:
            couv = couvertures[c]
            lignes.append(f"Au moment où la plante a le plus besoin d'eau, la pluie a suffi pour "
                          f"{le_la(cultures[c]['nom'])} {couv['couvertes']} années sur {couv['annees']}.")
            if cultures[c]["legumineuse"]:
                lignes.append(f"{le_la(cultures[c]['nom']).capitalize()} est une légumineuse, qui peut enrichir le sol "
                              "en azote. C'est à confirmer avec votre conseiller.")
        ecart = meilleure["scores"]["eau"] - actuelle["scores"]["eau"]
        nom = meilleure["nom"].lower()
        lignes.append(f"Pour l'eau, la rotation {nom} " + (
            "fait mieux que votre rotation actuelle." if ecart >= 0.05 else
            "fait un peu moins bien que votre rotation actuelle." if ecart <= -0.05 else
            "fait à peu près comme votre rotation actuelle."))
        if meilleure["scores"]["debouche"] - actuelle["scores"]["debouche"] <= -0.05:
            lignes.append("Elle laisse moins de place au coton, ce qui peut réduire vos ventes de coton.")
        faible = min(actuelle["cultures"], key=lambda c: couvertures[c]["couvertes"] / couvertures[c]["annees"])
        couv = couvertures[faible]
        lignes.append(f"Votre rotation actuelle arrive en position {actuelle['rang']}. Avec elle, "
                      f"{le_la(cultures[faible]['nom'])} n'a eu assez d'eau au moment clé que {couv['couvertes']} "
                      f"années sur {couv['annees']}.")
    lignes.append(contexte["stabilite"])
    classement = []
    for s in strategies:
        egal = ", à égalité" if sum(t["rang"] == s["rang"] for t in strategies) > 1 else ""
        classement.append(f"{s['rang']}{egal}. {s['nom']}{', votre rotation actuelle' if s['actuelle'] else ''}")
    lignes.append("Classement complet.\n" + "\n".join(classement))
    lignes.append(contexte["avertissement"])
    return "\n".join(lignes)


def enregistrement(cle: str) -> str | None:
    """Chemin relatif de l'enregistrement vocal du message, s'il existe dans app/audio."""
    for extension in FORMATS_AUDIO:
        if (DOSSIER_AUDIO / f"{cle}{extension}").exists():
            return f"audio/{cle}{extension}"
    return None


def respecte(reference: list[list[str]], scenario: list[list[str]]) -> bool:
    """Vrai si le scénario garde chaque écart strict du classement de référence."""
    rang_ref = {r: i for i, g in enumerate(reference) for r in g}
    rang_sc = {r: i for i, g in enumerate(scenario) for r in g}
    return all(rang_sc[a] < rang_sc[b] for a in rang_ref for b in rang_ref if rang_ref[a] < rang_ref[b])


def texte_stabilite(ordres: dict, sensibilite_config: dict) -> str:
    """Dit lesquels des scénarios de sensibilité changent le classement de référence."""
    scenarios = {
        "pluie_reduite": f"si la pluie baisse de {nombre(100 * (1 - sensibilite_config['facteur_pluie']))} %",
        "semis_retarde": f"si les pluies démarrent {sensibilite_config['retard_jours']} jours plus tard",
    }
    reference = ordres["reference"]
    changent = [t for n, t in scenarios.items() if not respecte(reference, ordres[n])]
    departagent = [t for n, t in scenarios.items() if respecte(reference, ordres[n]) and ordres[n] != reference]
    if changent:
        tiennent = [t for t in scenarios.values() if t not in changent]
        return (f"Attention, ce classement change {' et '.join(changent)}."
                + (f" Il tient {' et '.join(tiennent)}." if tiennent else ""))
    if departagent:
        return (f"Ce classement tient {' et '.join(scenarios.values())}. Les rotations à égalité se départagent "
                f"alors, différemment selon le scénario, et doivent être considérées comme équivalentes.")
    return f"Ce classement tient {' et '.join(scenarios.values())}."


def construire(config: dict) -> dict:
    series = series_lieux(config)
    rotations = {r["id"]: r for r in config["rotations"]}
    sortie = {
        "version": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        "periode": f"{config['periode']['debut'][:4]} à {config['periode']['fin'][:4]}",
        "rayon_couverture_km": config["rayon_couverture_km"],
        "avertissement": "Conseil indicatif, fondé sur le climat passé. À discuter avec votre conseiller ANADER.",
        "priorites": {k: v["libelle"] for k, v in config["priorites"].items()},
        "rotation_actuelle": next(r["id"] for r in config["rotations"] if r["actuelle"]),
        "lieux": {},
    }
    s = config["sensibilite"]
    for lieu in config["lieux"]:
        serie, debuts = series[lieu["id"]], debuts_par_annee(series[lieu["id"]], config)
        faux, evaluees = faux_departs(serie["jours"], serie["pluie"], debuts, config["saison"])
        debut_median = date_texte(quartiles([d.timetuple().tm_yday for d in debuts.values() if d])[1])
        resultats = {}
        for priorite, p in config["priorites"].items():
            analyse = sensibilite(serie, config, debuts, p["poids"])
            resultats[priorite] = {
                "stable": analyse["stable"],
                "stabilite": texte_stabilite(analyse["ordres"], s),
                "ordres": analyse["ordres"],
                "strategies": [{
                    "id": r, "nom": rotations[r]["nom"], "actuelle": rotations[r]["actuelle"],
                    "rang": rang, "total": round(total, 4),
                    "scores": {k: round(analyse["scores"][r][k], 4) for k in CRITERES},
                    "explications": explications(rotations[r], analyse["scores"][r], config["cultures"]),
                } for r, total, rang in analyse["classement"]],
            }
            r = resultats[priorite]
            for strategie in r["strategies"]:
                strategie["cultures"] = rotations[strategie["id"]]["cultures"]
            couvertures = {c: v for sc in analyse["scores"].values() for c, v in sc["cultures"].items()}
            r["resume"] = conseil_court(priorite, r["strategies"], couvertures, config["cultures"])
            r["detail"] = conseil({"lieu": lieu["nom"], "priorite": p["libelle"], "debut_pluies": debut_median,
                                   "stabilite": r["stabilite"], "avertissement": sortie["avertissement"]},
                                  r["strategies"], couvertures, config["cultures"])
            r["cle_audio"] = f"{lieu['id']}_{priorite}"
            r["audio"] = enregistrement(r["cle_audio"])
        sortie["lieux"][lieu["id"]] = {"nom": lieu["nom"], "lat": lieu["lat"], "lon": lieu["lon"],
                                      "alerte": texte_faux_departs(faux, evaluees, config["saison"]),
                                      "indicateurs": indicateurs(serie, debuts, config), "resultats": resultats}
    return sortie


def main() -> None:
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    donnees = construire(charger())
    SORTIE.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
    textes = ["# Textes à enregistrer", "", "Fichier généré par python -m moteur.exporter, à ne pas modifier.", ""]
    for lieu in donnees["lieux"].values():
        for r in lieu["resultats"].values():
            etat = f"enregistré, {r['audio']}" if r["audio"] else "à enregistrer"
            textes += [f"## {r['cle_audio']}, {etat}", "", r["resume"], ""]
    (DOSSIER_AUDIO / "textes_a_enregistrer.md").write_text("\n".join(textes), encoding="utf-8")
    print(f"Recommandations écrites dans {SORTIE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()

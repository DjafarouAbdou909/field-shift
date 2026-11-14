"""Application Streamlit pour le conseiller agricole et le jury.

Lancement, depuis la racine du dépôt
    venv/bin/streamlit run app/app.py
Paramètres d'URL lus, lieu, rotation et priorite, pour les liens envoyés par le bot. Les
résultats viennent de moteur.recommander, jamais de l'exemple fictif.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from moteur import recommander  # noqa: E402
from moteur.criteres import LIBELLES, POIDS_PAR_PRIORITE  # noqa: E402
from moteur.lieux import LIEUX  # noqa: E402
from moteur.rotations import STRATEGIES  # noqa: E402

st.set_page_config(page_title="Field Shift CI", layout="wide")


def choix(cle: str, options: list[str], defaut: str) -> str:
    """Valeur du paramètre d'URL si elle est valide, sinon la valeur par défaut."""
    valeur = st.query_params.get(cle, defaut)
    return valeur if valeur in options else defaut


def nombre(valeur: float) -> str:
    return f"{valeur:g}".replace(".", ",")


def lisible(indicateur) -> str:
    """Valeur et plage d'un indicateur, le jour de l'année étant écrit comme une date."""
    if indicateur.unite == "jour de l'année":
        en_date = lambda jour: (date(2001, 1, 1) + timedelta(days=int(jour) - 1)).strftime("%d/%m")
        return f"{en_date(indicateur.valeur)}, du {en_date(indicateur.bas)} au {en_date(indicateur.haut)}"
    unite = f" {indicateur.unite}" if indicateur.unite else ""
    return f"{nombre(indicateur.valeur)}{unite}, de {nombre(indicateur.bas)} à {nombre(indicateur.haut)}{unite}"


identifiants_lieux = list(LIEUX)
identifiants_rotations = [s.id for s in STRATEGIES]
with st.sidebar:
    lieu = st.selectbox("Lieu", identifiants_lieux, format_func=lambda i: LIEUX[i]["nom"],
                        index=identifiants_lieux.index(choix("lieu", identifiants_lieux, "korhogo")))
    rotation = st.selectbox("Rotation actuelle", identifiants_rotations,
                            format_func=lambda i: next(s.nom for s in STRATEGIES if s.id == i),
                            index=identifiants_rotations.index(choix("rotation", identifiants_rotations, "coton_mais")))
    priorites = list(POIDS_PAR_PRIORITE)
    priorite = st.radio("Priorité", priorites, format_func=lambda p: LIBELLES[p],
                        index=priorites.index(choix("priorite", priorites, "eau")))

with st.spinner("Calcul à partir des données de la NASA"):
    reco = recommander(lieu, rotation, POIDS_PAR_PRIORITE[priorite])

if reco.donnees_fictives:
    st.error("Données fictives, à ne jamais présenter.")
st.title(f"Rotations comparées pour {reco.lieu.nom}")
st.caption(reco.avertissement)
if not reco.classement_stable:
    st.warning("Le classement n'est pas stable face aux scénarios testés. Voir les lacunes de chaque stratégie.")

st.subheader("Ce que montrent les données, de 2001 à 2025")
st.dataframe(pd.DataFrame([
    {"Indicateur": i.texte, "Médiane et plage des quantiles 10 à 90 %": lisible(i), "Niveau": i.niveau,
     "Source": i.source.nom}
    for i in reco.indicateurs
]), hide_index=True)

st.subheader("Stratégies, dans l'ordre du classement")
strategies = {s.id: s for s in reco.strategies}
for rang, identifiant in enumerate(reco.classement, start=1):
    s = strategies[identifiant]
    with st.expander(f"{rang}. {s.nom}" + ("  (rotation actuelle)" if s.actuelle else ""), expanded=rang == 1):
        st.write(f"Scores sur 5, eau {nombre(s.scores.eau)}, {LIBELLES['revenu']} {nombre(s.scores.revenu)}, "
                 f"{LIBELLES['sol']} {nombre(s.scores.sol)}. Confiance {s.confiance}.")
        for titre, elements in [("Pourquoi", s.pourquoi), ("Preuves", s.preuves), ("Bénéfices", s.benefices),
                                ("Lacunes", s.lacunes), ("Risques", s.risques)]:
            if elements:
                st.markdown(f"**{titre}**")
            for e in elements:
                source = f", source {e.source.nom}" if e.source else ""
                st.markdown(f"- {e.texte} *{e.niveau}{source}*")

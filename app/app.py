"""Application Streamlit pour le conseiller agricole et le jury.

Lancement, depuis la racine du dépôt
    streamlit run app/app.py
Paramètres d'URL prévus, lieu, rotation et priorite, pour les liens envoyés par le bot.
Ils ne sont pas encore lus, l'application affiche toujours l'exemple fictif.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from moteur import charger_exemple  # noqa: E402

st.set_page_config(page_title="Field Shift CI", layout="wide")
reco = charger_exemple()

if reco.donnees_fictives:
    st.error("Données fictives de développement, à ne jamais présenter.")

st.title(f"Rotations comparées pour {reco.lieu.nom}")
st.caption(reco.avertissement)

st.subheader("Ce que montrent les données")
st.dataframe(pd.DataFrame([
    {"Indicateur": i.texte, "Valeur": i.valeur, "Plage": f"{i.bas} à {i.haut}", "Unité": i.unite,
     "Niveau": i.niveau, "Source": i.source.nom}
    for i in reco.indicateurs
]), hide_index=True)

st.subheader("Stratégies, dans l'ordre du classement")
strategies = {s.id: s for s in reco.strategies}
for rang, identifiant in enumerate(reco.classement, start=1):
    s = strategies[identifiant]
    with st.expander(f"{rang}. {s.nom}" + ("  (rotation actuelle)" if s.actuelle else ""), expanded=rang == 1):
        st.write(f"Scores eau {s.scores.eau}, revenu {s.scores.revenu}, sol {s.scores.sol}. Confiance {s.confiance}.")
        for titre, elements in [("Pourquoi", s.pourquoi), ("Preuves", s.preuves), ("Bénéfices", s.benefices),
                                ("Lacunes", s.lacunes), ("Risques", s.risques)]:
            st.markdown(f"**{titre}**")
            for e in elements:
                source = f", source {e.source.nom}" if e.source else ""
                st.markdown(f"- {e.texte} *{e.niveau}{source}*")

"""
Lift Planner Eigenbetrieb · Einstieg
Konzeptprototyp TH Köln × STIHL: Lastplanung je Flug und Kosten einer eigenen Lastendrohne in Steillagen.

Aufbau
  config/   Parameter und Szenarien (YAML)        → einzige Quelle aller Rechenwerte
  data/     Gerätekatalog, Vorlagen, Standorte    → aus Transportbox Sprint 5-6
  core/     Rechenkern ohne Oberfläche            → testbar, Rechenweg wird mitprotokolliert
  ui/       Theme, Bausteine, Diagramme, Sitzungszustand
  views/    eine Datei je Seite
"""
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).parent / "assets"
st.set_page_config(page_title="Lift Planner Eigenbetrieb", page_icon="🟧", layout="wide")

from ui import state, theme  # noqa: E402

theme.inject()
state.init()

st.logo(str(ASSETS / "logo.svg"), size="large", icon_image=str(ASSETS / "logo_mark.svg"))

pages = {
    "Planung": [
        st.Page(path, title=title, icon=icon, default=(i == 0))
        for i, ((path, title), icon) in enumerate(zip(state.PLAN_PAGES, [
            ":material/map:", ":material/landscape:", ":material/partly_cloudy_day:", ":material/shopping_cart:",
            ":material/flight_takeoff:",
            ":material/euro:"]))
    ],
    "Einstellungen": [
        st.Page("views/parameter.py", title="Annahmen & Parameter", icon=":material/tune:"),
        st.Page("views/katalog.py", title="Gerätekatalog", icon=":material/inventory_2:"),
    ],
}
nav = st.navigation(pages)

with st.sidebar:
    n = len(state.changed_keys())
    st.markdown(
        f"<div class='sb-scn'>Eigenbetrieb · Szenario <b>{state.S.szenario}</b><br>"
        f"{n} Wert{'e' if n != 1 else ''} abweichend von der Basis</div>"
        "<div class='sb-foot'>Konzeptprototyp<br>TH Köln × STIHL<br>Arbeiten in Steillagen</div>",
        unsafe_allow_html=True,
    )

nav.run()

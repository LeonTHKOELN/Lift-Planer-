"""Einstellungen · Gerätekatalog und Vorlagen aus der Tabelle Transportszenarien."""
import pandas as pd
import streamlit as st

from core import katalog
from core.fmt import de
from ui import state
from ui.components import footer, note, simple_head

S = state.S
simple_head("Einstellungen", "Gerätekatalog",
            "Artikel für die Lastplanung. Quelle: Transportbox Sprint 5-6, Blatt Transportszenarien.")
note("Gewichte aus Herstellerangaben (Q-Nummern) oder als Schätzung gekennzeichnet. Positionen mit "
     "„Schätzung“ noch durch Wiegen bestätigen. Änderungen dauerhaft in <code>data/katalog.csv</code> im Repo.")
st.write("")
tab_k, tab_v = st.tabs(["Katalog", "Vorlagen S1 bis S5"])
with tab_k:
    kat = st.pills("Kategorie", katalog.KATEGORIEN, selection_mode="multi", key="kat_filter")
    rows = [a for a in state.KATALOG.values() if not kat or a["kategorie"] in kat]
    df = pd.DataFrame([{"Kategorie": a["kategorie"], "Artikel": a["name"], "kg": a["gewicht_kg"],
                        "Einheit": a["einheit"], "Gefahrgut": a["gefahrgut_text"],
                        "Länge mm": a["laenge_mm"], "Energie Wh": a["energie_wh"], "Quelle": a["quelle"],
                        "Hinweis": a["hinweis"]} for a in rows])
    st.dataframe(df, hide_index=True, width="stretch", height=min(38 * (len(df) + 1), 900),
                 column_config={"kg": st.column_config.NumberColumn(format="%.2f"),
                                "Länge mm": st.column_config.NumberColumn(format="%.0f"),
                                "Energie Wh": st.column_config.NumberColumn(format="%.0f")})
    st.caption(f"{len(state.KATALOG)} Artikel. Kettenöl aus beiden Tabellenzeilen ist zu einem Artikel "
               "zusammengefasst (gleiches Gewicht je Liter).")
with tab_v:
    for v in state.VORLAGEN:
        pos = [(state.KATALOG[x["artikel"]], x["menge"]) for x in v["positionen"]]
        summe = sum(a["gewicht_kg"] * m for a, m in pos)
        gg = sum(a["gewicht_kg"] * m for a, m in pos if a["gefahrgut"])
        with st.expander(f"{v['name']} · {de(summe, 1)} kg · davon Gefahrgut {de(gg, 1)} kg"):
            st.dataframe(pd.DataFrame([{"Artikel": a["name"], "Menge": m, "Einheit": a["einheit"],
                                        "kg": a["gewicht_kg"] * m, "Gefahrgut": a["gefahrgut_text"]}
                                       for a, m in pos]), hide_index=True, width="stretch",
                         column_config={"kg": st.column_config.NumberColumn(format="%.2f")})
footer()

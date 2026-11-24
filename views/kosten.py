"""Schritt 3 · Kosten im Eigenbetrieb und Vergleich mit Helikopter und Tragen."""
import pandas as pd
import streamlit as st

from core.fmt import de, fmt_min
from ui import charts, state
from ui.components import dg_note, footer, kpi_html, kpis, nav, note, page_head, section_title

PATH = "views/kosten.py"
R = state.result()
d, h, c, j = R["drohne"], R["heli"], R["manuell"], R["job"]
kg = R["kg_hoch"] + R["kg_runter"]

page_head(PATH, "Kosten im Eigenbetrieb", "Was der geplante Einsatz mit eigener Drohne kostet, und was die "
                                          "gleiche Fracht per Helikopter oder getragen kosten würde.")
if not d["fluege"]:
    note("Noch keine Flüge geplant. Auf der Seite <b>Flugplanung</b> Flüge anlegen.", warn=True, icon="!")
    nav(PATH)
    footer()
    st.stop()
if R["fehler"]:
    note("Flug " + ", ".join(map(str, R["fehler"])) + " liegt über der Lastgrenze. Die Kosten sind deshalb zu "
         "niedrig gerechnet.", warn=True, icon="!")
    st.write("")

st.markdown(
    f"""<div class="lp-hero">
      <div><div class="t">Kosten Eigenbetrieb</div><div class="big">{de(d['Kosten (€)'])} €</div>
        <div class="sub">{d['fluege']} Flüge an {d['tage']} Einsatztag(en)</div></div><div class="div"></div>
      <div><div class="t">Je kg Fracht</div><div class="big">{de(d['Kosten (€)'] / kg, 2) if kg else "–"} €</div>
        <div class="sub">{de(kg, 1)} kg bewegt (hoch + runter)</div></div><div class="div"></div>
      <div><div class="t">Je Flug</div><div class="big">{de(d['Kosten (€)'] / d['fluege'])} €</div>
        <div class="sub">inkl. Anteil Tageskosten</div></div>
    </div>""", unsafe_allow_html=True)
st.write("")
kpis([kpi_html("Variable Kosten", de(d["variabel"]), "€", "Flugzeit und Energie"),
      kpi_html("Fixe Kosten", de(d["fix"]), "€", "je Einsatztag: Drohne, Aufbau, Abbau"),
      kpi_html("Zeit vor Ort", fmt_min(d["Zeit (min)"]), "", f"{de(d['kwh'], 1)} kWh Energie")])

st.write("")
section_title("Kostenpositionen")
with st.container(border=True):
    pos = pd.DataFrame(d["positionen"])
    pos["Betrag €"] = pos["Betrag"].round(0)
    st.dataframe(pos[["Position", "Art", "Eingesetzt", "Betrag €"]], hide_index=True, width="stretch")

st.write("")
t1, t2 = st.container(), st.container()
with t1:
    section_title("Je Flug")
    df = pd.DataFrame(d["je_flug"])
    st.dataframe(df[["Flug", "Tag", "Minuten", "kg", "kWh", "Personal", "Wartung und Akku", "Strom", "Summe"]],
                 hide_index=True, width="stretch",
                 column_config={x: st.column_config.NumberColumn(format="%.1f") for x in
                                ("Minuten", "kg", "kWh")} | {x: st.column_config.NumberColumn(format="%.2f €") for x in
                                                             ("Personal", "Wartung und Akku", "Strom", "Summe")})
    st.caption("Ohne Tageskosten. kg = Ladung hoch und runter, ohne Behälter.")
with t2:
    st.write("")
    section_title("Je Einsatztag")
    st.dataframe(pd.DataFrame(d["je_tag"]), hide_index=True, width="stretch",
                 column_config={x: st.column_config.NumberColumn(format="%.0f €") for x in
                                ("Flüge (€)", "Vor Ort (€)", "Drohne fix (€)", "Summe (€)")}
                 | {"Flugzeit (min)": st.column_config.NumberColumn(format="%.0f")})

st.write("")
section_title("Vergleich mit derselben Fracht")
kpis([kpi_html("Drohne Eigenbetrieb", de(d["Kosten (€)"]), "€", f"{d['fluege']} Flüge · {fmt_min(d['Zeit (min)'])}",
               accent=True),
      kpi_html("Helikopter", de(h["Kosten (€)"]), "€", f"{h['einsaetze']} Einsätze · {h['rotationen']} Rotationen"),
      kpi_html("Tragen", de(c["Kosten (€)"]), "€", f"{c['gaenge']} Gänge · {j['team']} Personen · "
                                                   f"{fmt_min(c['Zeit (min)'])}")])
st.write("")
cmp = pd.DataFrame([{"Variante": n, **{k: x[k] for k in ("Kosten (€)", "Zeit (min)", "CO₂ (kg)")}}
                    for n, x in (("Drohne", d), ("Helikopter", h), ("Tragen", c))])
cols = st.columns(3, gap="medium")
for col, (metric, label, nd) in zip(cols, [("Kosten (€)", "Kosten in €", 0), ("Zeit (min)", "Zeit vor Ort in Minuten", 0),
                                           ("CO₂ (kg)", "CO₂ in kg", 1)]):
    with col, st.container(border=True):
        section_title(label)
        st.altair_chart(charts.compare_chart(cmp, metric, nd), width="stretch")
st.caption(f"Helikopter: je Einsatztag und Richtung mit Last ein Einsatz, Basis {R['heli_basis']['name']} "
           f"({de(R['heli_basis']['km'], 1)} km Luftlinie). Tragen: Gehzeit nach DIN 33466 mit Lastaufschlag.")

st.write("")
note("Wie jede Zahl entsteht, zeigt der Rechenweg unter <b>Annahmen & Parameter</b>. Dort lassen sich alle Werte "
     "ändern und als Szenario speichern.")
st.page_link("views/parameter.py", label="Zu Annahmen & Parameter", icon=":material/tune:")
if R["has_dg"]:
    st.write("")
    dg_note()
nav(PATH)
footer()

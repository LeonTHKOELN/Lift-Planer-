"""Schritt 6 · Kosten im Eigenbetrieb (Kalkulation FlyCart 100) und Akkuplan."""
import altair as alt
import pandas as pd
import streamlit as st

from core import kosten
from core.fmt import de, fmt_min
from ui import state
from ui.components import dg_note, footer, kpi_html, kpis, nav, note, page_head, section_title
from ui.theme import FONT, GREY_600, INK, ORANGE

PATH = "views/kosten.py"
R = state.result()
k, ak, p = R["kosten"], R["akku"], R["p"]
kg = R["kg_hoch"] + R["kg_runter"]

page_head(PATH, "Kosten im Eigenbetrieb",
          "Kalkulation FlyCart 100 je Flugminute, einmal ohne und einmal mit Abschreibung der Investition"
          + ("." if p["personal.einrechnen"] else ", ohne Personalkosten."))
if not k["fluege"]:
    note("Noch keine Flüge. Auf der Seite <b>Ausrüstung</b> Artikel in den Warenkorb legen.", warn=True, icon="!")
    nav(PATH)
    footer()
    st.stop()
if R["fehler"]:
    note("Flug " + ", ".join(map(str, R["fehler"])) + " liegt über der Lastgrenze. Bitte in der Flugplanung prüfen.",
         warn=True, icon="!")
    st.write("")

st.markdown(
    f"""<div class="lp-hero">
      <div><div class="t">Ohne Abschreibung</div><div class="big">{de(k['ohne'])} €</div>
        <div class="sub">{de(k['ohne'] / kg, 2) if kg else "–"} € je kg · {de(k['satz_ohne'], 2)} € je Flugminute</div>
      </div><div class="div"></div>
      <div><div class="t">Mit Abschreibung</div><div class="big">{de(k['mit'])} €</div>
        <div class="sub">{de(k['mit'] / kg, 2) if kg else "–"} € je kg · {de(k['satz_mit'], 2)} € je Flugminute</div>
      </div><div class="div"></div>
      <div><div class="t">Flugzeit</div><div class="big">{de(k['luft_min'], 1)} min</div>
        <div class="sub">{k['fluege']} Flüge · {de(kg, 1)} kg bewegt</div></div>
    </div>""", unsafe_allow_html=True)
st.write("")

section_title("Aufschlüsselung")
with st.container(border=True):
    rows = [("Akkuverschleiß, Laden, Wartung", "variabel", k["var"], k["var"]),
            ("Fixkosten anteilig", "über Auslastung", k["fix_ohne"], k["fix_mit"])]
    if p["personal.einrechnen"]:
        rows.append(("Personal", "Einsatzzeit × Crew", k["personal"], k["personal"]))
    rows.append(("Summe", "", k["ohne"], k["mit"]))
    df = pd.DataFrame([{"Position": a, "Art": b, "ohne Abschreibung (€)": c, "mit Abschreibung (€)": d}
                       for a, b, c, d in rows])
    st.dataframe(df, hide_index=True, width="stretch",
                 column_config={x: st.column_config.NumberColumn(format="euro") for x in
                                ("ohne Abschreibung (€)", "mit Abschreibung (€)")})
    st.caption(f"Fixkosten anteilig = {de(k['luft_min'], 1)} Flugminuten × Fixkosten pro Jahr / "
               f"({de(p['kalk.auslastung_h'])} h × 60). Investition {de(k['investition'])} €, Abschreibung "
               f"{de(k['abschreibung'])} € pro Jahr über {p['kalk.nutzungsdauer_j']} Jahre, Fixkosten "
               f"{de(p['kalk.fix_jahr_eur'])} € pro Jahr.")

# ---------- Akkus ----------
st.write("")
section_title("Akkus: Wechsel und Laden")
kpis([kpi_html("Akkuwechsel", str(ak["wechsel"]), "", f"je Satz {de(ak['nutz_min'], 1)} min nutzbar", accent=True),
      kpi_html("Ladevorgänge", str(ak["ladungen"]), "", f"{p['akku.saetze']} Sätze · {de(p['akku.ladezeit_min'])} min "
                                                         "je Ladung"),
      kpi_html("Warten auf Laden", de(ak["warte_min"]), "min",
               "Laden hält mit" if not ak["warte_min"] else f"bei {ak['warte_n']} Wechsel(n)")])
st.write("")
if ak["zu_lang"]:
    note(f"Flug {', '.join(map(str, ak['zu_lang']))} dauert länger als ein Akkusatz nutzbar hält. Route oder "
         "Landeplatz prüfen.", warn=True, icon="!")
if ak["warte_min"]:
    note(f"Die Ladung hält nicht mit: insgesamt <b>{de(ak['warte_min'])} min</b> Warten auf geladene Akkus. "
         "Mehr Akkusätze oder ein stärkeres Ladegerät einplanen.", warn=True, icon="!")
if ak["ereignisse"]:
    st.dataframe(pd.DataFrame(ak["ereignisse"]), hide_index=True, width="stretch",
                 column_config={"Rest vorher (min)": st.column_config.NumberColumn(format="localized"),
                                "Wartezeit Laden (min)": st.column_config.NumberColumn(format="localized")})
else:
    note("Ein Akkusatz reicht für alle Flüge, kein Wechsel nötig.", icon="✓")
st.caption(f"Wechsel, sobald die Restflugzeit nicht mehr für den nächsten Flug reicht. Reserve "
           f"{de(p['akku.reserve_pct'])} % bleibt immer im Akku. Einsatzzeit vor Ort: {fmt_min(k['einsatz_min'])}.")

# ---------- Je Flug ----------
st.write("")
section_title("Je Flug")
st.dataframe(pd.DataFrame(k["je_flug"]), hide_index=True, width="stretch",
             column_config={"Flugminuten": st.column_config.NumberColumn(format="localized"),
                            "kg": st.column_config.NumberColumn(format="localized")}
             | {x: st.column_config.NumberColumn(format="euro") for x in
                ("variabel (€)", "ohne Abschreibung (€)", "mit Abschreibung (€)")})

# ---------- Auslastung ----------
st.write("")
section_title("Kosten je Flugminute nach Auslastung")
with st.container(border=True):
    hs = list(range(10, 310, 10))
    kurve = pd.DataFrame([{"h": h, "Variante": v, "eur": w} for h in hs
                          for v, w in zip(("ohne Abschreibung", "mit Abschreibung"), kosten.satz_je_min(p, h))])
    farben = alt.Scale(domain=["ohne Abschreibung", "mit Abschreibung"], range=[GREY_600, ORANGE])
    linie = alt.Chart(kurve).mark_line(strokeWidth=3).encode(
        x=alt.X("h:Q", title="Flugstunden pro Jahr"),
        y=alt.Y("eur:Q", title="€ je Flugminute", scale=alt.Scale(domain=[0, 12], clamp=True)),
        color=alt.Color("Variante:N", scale=farben, legend=alt.Legend(orient="top", title=None)))
    jetzt = alt.Chart(pd.DataFrame({"h": [p["kalk.auslastung_h"]]})).mark_rule(color=INK, strokeDash=[4, 4]).encode(
        x="h:Q")
    st.altair_chart((linie + jetzt).properties(height=300).configure_axis(labelFont=FONT, titleFont=FONT)
                    .configure_legend(labelFont=FONT), width="stretch")
    st.caption(f"Gestrichelt: eingestellte Auslastung {de(p['kalk.auslastung_h'])} h pro Jahr. Größter Hebel ist "
               "die Auslastung, z. B. eine Drohne für mehrere Betriebe. Ändern unter Annahmen & Parameter.")

st.write("")
note("Quelle: Excel „FlyCart100_Kalkulation“ (Projekt-Review 6, Folie 14), Preise Online-Händler 13.11.2026, netto. "
     "Wie jede Zahl entsteht, zeigt der Rechenweg unter <b>Annahmen & Parameter</b>.")
st.page_link("views/parameter.py", label="Zu Annahmen & Parameter", icon=":material/tune:")
if R["has_dg"]:
    st.write("")
    dg_note()
nav(PATH)
footer()

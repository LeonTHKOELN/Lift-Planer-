"""Schritt 2 · Flugweg: Höhenprofil alle 30 m, geplante Flughöhe und Flugzeit."""
import streamlit as st

from core.fmt import de
from ui import charts, state
from ui.components import footer, kpi_html, kpis, nav, note, page_head, section_title
from ui.theme import GREY_400, GREY_600, GREY_900, ORANGE, ORANGE_LIGHT

PATH = "views/flugweg.py"
S = state.S
R = state.result()
P, p = R["P"], R["p"]

page_head(PATH, "Flugweg", f"Von {S.w_start_name} ({de(P['start_alt'])} m) zu {S.w_einsatz} ({de(P['ziel_alt'])} m). "
                           "Geländeprofil alle 30 m und geplante Flughöhe.")
kpis([kpi_html("Flugweg", de(P["flight_len"] / 1000, 2), "km", "je Richtung", accent=True),
      kpi_html("Höhenunterschied", ("+" if P["dh"] >= 0 else "−") + de(abs(P["dh"])), "m"),
      kpi_html("Flugzeit", de(P["out_min"] + P["back_min"], 1), "min", "hin und zurück, ohne Bodenzeit")])
# ---------- Flugprofil ----------
st.write("")
section_title("Flugprofil")
with st.container(border=True):
    st.markdown(
        f"""<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:center">
        <div style="display:flex;gap:18px;flex-wrap:wrap;font-size:.85rem;color:{GREY_900}">
          <span><span style="display:inline-block;width:22px;height:3px;background:{ORANGE};vertical-align:middle;margin-right:6px"></span>Geplante Flughöhe</span>
          <span><span style="display:inline-block;width:22px;border-top:2px dashed {GREY_600};vertical-align:middle;margin-right:6px"></span>Direktlinie</span>
          <span><span style="display:inline-block;width:14px;height:12px;background:#E4DED4;border-top:2px solid #8C8273;vertical-align:middle;margin-right:6px"></span>Gelände</span>
          <span><span style="display:inline-block;width:14px;height:12px;background:{ORANGE_LIGHT};vertical-align:middle;margin-right:6px"></span>Korridor {de(P['clear'])} bis {de(P['ceiling'])} m über Grund</span>
        </div>
        <div style="color:{GREY_600};font-size:.8rem">{P['n']} Punkte · alle {de(P['step_eff'])} m · {P['source']}</div>
        </div>""", unsafe_allow_html=True)
    st.altair_chart(charts.profile_chart(P), width="stretch")
st.write("")
kpis([kpi_html("Luftlinie", de(P["dist"] / 1000, 2), "km", "horizontal, Kartenmaß"),
      kpi_html("Flugweg", de(P["flight_len"] / 1000, 2), "km",
               f"+{de((P['flight_len'] / P['dist'] - 1) * 100 if P['dist'] else 0, 1)} % · inkl. Steigen und Sinken"),
      kpi_html("Geländelinie", de(P["terrain_len"] / 1000, 2), "km", f"↑ {de(P['asc'])} m · ↓ {de(P['desc'])} m")])
st.write("")
kpis([kpi_html("Höchster Punkt", de(P["top_alt"]), "m", f"bei {de(P['top_d'] / 1000, 2)} km"),
      kpi_html("Max. Geländeneigung", de(P["max_slope"]), "%", f"je {de(P['step_eff'])}-m-Abschnitt"),
      kpi_html("Flugzeit hin / zurück", f"{de(P['out_min'], 1)} / {de(P['back_min'], 1)}", "min",
               f"zzgl. Bodenzeit {de(p['flug.umlauf_min'], 1)} min + An-/Abhängen")])
st.write("")
direct_ok = P["direct_min_agl"] >= P["clear"] - 0.5 and P["direct_max_agl"] <= P["ceiling"] + 0.5
if not P["real"]:
    if P["error"]:
        note("<b>Höhendaten nicht erreichbar.</b> Es werden die manuellen Höhen verwendet, das Profil ist "
             "nur eine Gerade. Später erneut laden oder Höhen manuell prüfen.", warn=True, icon="!")
    else:
        note("Manuelle Höhen aktiv. Das Profil verbindet Start und Ziel linear, Geländehindernisse "
             "werden nicht berücksichtigt.")
elif direct_ok:
    note(f"<b>Direktflug möglich.</b> Die Direktlinie bleibt durchgehend zwischen {de(P['clear'])} und "
         f"{de(P['ceiling'])} m über Grund (minimal {de(P['direct_min_agl'])} m).", icon="✓")
else:
    why = (f"Die Direktlinie käme dem Gelände bis auf {de(P['direct_min_agl'])} m nahe"
           if P["direct_min_agl"] < P["clear"] else f"Die Direktlinie läge bis zu {de(P['direct_max_agl'])} m über Grund")
    note(f"<b>Geländefolgeflug nötig.</b> {why}. Die geplante Flughöhe folgt deshalb dem Gelände "
         f"im Korridor und steigt dabei insgesamt {de(P['path_climb'])} m.", warn=True, icon="!")
st.markdown(f"<div style='color:{GREY_400};font-size:.78rem;margin-top:6px'>Höhenmodell ohne zuverlässige "
            "Erfassung von Bäumen, Seilen und Leitungen. Die Flugroute ersetzt keine Prüfung durch den "
            "Piloten vor Ort.</div>", unsafe_allow_html=True)

nav(PATH)
footer()

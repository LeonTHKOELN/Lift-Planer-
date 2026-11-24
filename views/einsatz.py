"""Schritt 1 · Einsatz & Route: Standardeinsatz, Karte, Pins."""
import folium
import streamlit as st
from streamlit_folium import st_folium

from core.fmt import de
from ui import state
from ui.components import footer, kpi_html, kpis, nav, note, page_head, section_title
from ui.theme import GREY_600, INK, ORANGE

PATH = "views/einsatz.py"
S = state.S
R = state.result()
P, p = R["P"], R["p"]

page_head(PATH, "Einsatz & Route", "Standardeinsatz wählen oder Landeplatz und Einsatzort auf der Karte setzen.")
with st.container(border=True):
    c1, c2, c3 = st.columns([4, 3, 2], vertical_alignment="bottom")
    namen = [o["name"] for o in state.STANDORTE]
    c1.selectbox("Standardeinsatz", namen, key="sel_standort", placeholder="Standardeinsatz wählen …",
                 help="Hinterlegte Start- und Zielpunkte aus data/standorte.csv")
    c2.toggle("Passende Vorlage in den Warenkorb", value=True, key="standort_vorlage",
              help="Ersetzt den Warenkorb durch die Tagesladung der Vorlage (z. B. S1 Forst)")
    c3.button("Übernehmen", type="primary", width="stretch", on_click=state.standort_laden,
              disabled=not S.get("sel_standort"))
    if S.get("standort_msg"):
        st.caption(S.pop("standort_msg"))
st.write("")
left, right = st.columns([7, 5], gap="large")

with left:
    modi = ["Landeplatz", "Einsatzort"]
    if S.get("pin_mode") not in modi:
        S.pin_mode = "Landeplatz"
    cm1, cm2 = st.columns([3, 2], vertical_alignment="center")
    with cm1:
        st.segmented_control("Pin setzen", modi, key="pin_mode", label_visibility="collapsed")
    mode = S.pin_mode or "Landeplatz"
    cm2.markdown(f"<div style='color:{GREY_600};font-size:.85rem;text-align:right'>Kartenklick setzt: "
                 f"<b style='color:{ORANGE}'>{mode}</b></div>", unsafe_allow_html=True)

    start, ziel = R["job"]["start"], R["job"]["ziel"]
    m = folium.Map(location=[(start[0] + ziel[0]) / 2, (start[1] + ziel[1]) / 2],
                   zoom_start=14, tiles=None, control_scale=True)
    folium.TileLayer(tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
                     attr='Karte: © <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA), '
                          '© OpenStreetMap-Mitwirkende', name="Topo", max_zoom=17).add_to(m)
    folium.PolyLine([start, ziel], color=ORANGE, weight=5, opacity=.95, dash_array="10 8").add_to(m)
    if P["real"] and not P["top_is_end"]:
        folium.CircleMarker(P["top_pt"], radius=6, color=INK, weight=2, fill=True, fill_color="#FFFFFF",
                            fill_opacity=1, tooltip=f"Höchster Geländepunkt · {de(P['top_alt'])} m").add_to(m)
    for pos, other, label, alt_m, fill in [(start, ziel, S.w_start_name, de(P["start_alt"]), "#FFFFFF"),
                                           (ziel, start, S.w_einsatz, de(P["ziel_alt"]), ORANGE)]:
        folium.CircleMarker(pos, radius=9, color=ORANGE, weight=4, fill=True, fill_color=fill,
                            fill_opacity=1).add_to(m)
        right_side = pos[1] <= other[1]  # Label zur Außenseite der Route
        folium.Marker(pos, icon=folium.DivIcon(
            icon_size=(240, 30), icon_anchor=(-14, 14) if right_side else (254, 14),
            html=f'<div style="text-align:{"left" if right_side else "right"}">'
                 f'<span style="font-family:Barlow,sans-serif;font-size:12px;font-weight:600;background:#fff;'
                 f'border-radius:4px;padding:3px 8px;display:inline-block;box-shadow:0 1px 4px rgba(0,0,0,.25);'
                 f'white-space:nowrap">{label} · {alt_m} m</span></div>')).add_to(m)
    m.fit_bounds([start, ziel], padding=(70, 70))
    out = st_folium(m, height=430, width="100%", returned_objects=["last_clicked"],
                    key="map") or {}
    click = out.get("last_clicked")
    if click:
        sig = (round(click["lat"], 6), round(click["lng"], 6))
        if sig != S.get("last_click_sig"):
            S["last_click_sig"] = sig  # jeden Klick merken, auch beim Zeichnen, damit er später nicht nachwirkt
            S["pending_pin"] = (mode, sig[0], sig[1])  # wird in state.init() vor dem Rendern übernommen
            st.rerun()

with right:
    with st.container(border=True):
        section_title("Einsatz")
        st.text_input("Einsatzname", key="w_einsatz")
    st.write("")
    st.markdown(
        f"""<div class="lp-card"><div class="lp-card-title">Route</div><div class="lp-route">
        <div class="pin fill"></div><div class="name">{S.w_einsatz}</div><div class="alt">{de(P['ziel_alt'])} m</div>
        <div class="seg"></div><div class="mid">Flugweg {de(P['flight_len'] / 1000, 2)} km ·
          Luftlinie {de(P['dist'] / 1000, 2)} km<br>Ø Steigung {de(abs(P['dh']) / P['dist'] * 100 if P['dist'] else 0)} %</div><div></div>
        <div class="pin"></div><div class="name">{S.w_start_name}</div><div class="alt">{de(P['start_alt'])} m</div>
        </div></div>""", unsafe_allow_html=True)
    st.write("")
    kpis([kpi_html("Flugweg", de(P["flight_len"] / 1000, 2), "km", "je Richtung"),
          kpi_html("Höhe", ("+" if P["dh"] >= 0 else "−") + de(abs(P["dh"])), "m"),
          kpi_html("Flugzeit", de(P["out_min"] + P["back_min"], 1), "min", "hin und zurück, ohne Bodenzeit")])

st.write("")
note(f"<b>Eigenbetrieb:</b> eigene Drohne, eigener Pilot. Planungsgrenze <b>{de(p['drohne.nutzlast_kg'])} kg</b> "
     "am Haken je Flug, Ladung plus Behälter.")
with st.expander("Koordinaten und Höhen bearbeiten"):
    c1, c2 = st.columns(2)
    for col, prefix, title in [(c1, "start", "Landeplatz (Start)"), (c2, "ziel", "Einsatzort (Ziel)")]:
        with col:
            st.markdown(f"**{title}**")
            if prefix == "start":
                st.text_input("Bezeichnung", key="w_start_name")
            st.text_input("Koordinaten einfügen (z. B. aus Google Maps)", key=f"w_{prefix}_paste",
                          placeholder="47.0800, 9.9170", on_change=state.apply_paste, args=(prefix,))
            if S.get(f"paste_err_{prefix}"):
                st.caption(":orange[Format nicht erkannt. Beispiel: 47.0800, 9.9170]")
            a1, a2 = st.columns(2)
            a1.number_input("Breitengrad", -90.0, 90.0, format="%.6f", step=0.001, key=f"w_{prefix}_lat")
            a2.number_input("Längengrad", -180.0, 180.0, format="%.6f", step=0.001, key=f"w_{prefix}_lon")
            st.number_input("Höhe (m ü. NN)", 0, 9000, step=10, key=f"w_{prefix}_alt", disabled=not S.w_alt_manual,
                            help="Wird automatisch aus dem Höhenmodell ermittelt. Zum Ändern "
                                 "'Höhen manuell festlegen' aktivieren.")
    st.checkbox("Höhen manuell festlegen (ohne Höhen-API)", key="w_alt_manual")
    st.caption(f"Höhenquelle: {P['source']}")
nav(PATH)
footer()

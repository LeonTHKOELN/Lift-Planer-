"""Schritt 2 · Flugplanung: Flüge anlegen, Last je Richtung aus dem Gerätekatalog zusammenstellen."""
import pandas as pd
import streamlit as st

from core import fluege as flm
from core import katalog
from core.fmt import de, fmt_min
from ui import state
from ui.components import dg_note, footer, kpi_html, kpis, lastbalken, nav, note, page_head
from ui.theme import GREY_600

PATH = "views/flugplan.py"
S = state.S
KAT = state.KATALOG
FREI = "__frei"


# ---------------------------------------------------------------------------
# Callbacks (laufen vor dem nächsten Rendern, ändern S.fluege)
# ---------------------------------------------------------------------------
def _ver(fid, d):
    return S.setdefault(f"v_{fid}_{d}", 0)


def set_modus(fid):
    f = state.flug(fid)
    f["modus"] = S[f"mod_{fid}"] or f["modus"]
    S.offen = fid


def set_tag(fid):
    state.flug(fid)["tag"] = int(S[f"tag_{fid}"])
    S.offen = fid


def set_behaelter(fid, d):
    state.flug(fid)[d]["behaelter"] = S[f"beh_{fid}_{d}"]
    S.offen = fid


def edit_positionen(fid, d):
    last = state.flug(fid)[d]
    edits = S[f"ed_{fid}_{d}_{_ver(fid, d)}"]["edited_rows"]
    weg = set()
    for idx, ch in edits.items():
        i = int(idx)
        if ch.get("Entfernen"):
            weg.add(i)
        if ch.get("Menge") is not None:
            last["positionen"][i]["menge"] = max(float(ch["Menge"]), 0.0)
    last["positionen"] = [x for i, x in enumerate(last["positionen"]) if i not in weg and x["menge"] > 0]
    S[f"v_{fid}_{d}"] += 1
    S.offen = fid


def add_position(fid, d):
    last = state.flug(fid)[d]
    aid, menge = S[f"add_{fid}_{d}"], float(S[f"addm_{fid}_{d}"])
    if menge <= 0:
        return
    if aid == FREI:
        name = (S.get(f"fn_{fid}_{d}") or "").strip() or "Freie Position"
        neu = katalog.freie_position(name, S.get(f"fk_{fid}_{d}", 0.0), menge, S.get(f"fg_{fid}_{d}", ""))
    else:
        neu = katalog.position(KAT[aid], menge)
    same = next((x for x in last["positionen"] if x["artikel"] and x["artikel"] == neu["artikel"]), None)
    if same:
        same["menge"] += menge
    else:
        last["positionen"].append(neu)
    S[f"v_{fid}_{d}"] = _ver(fid, d) + 1
    S.offen = fid


def leeren(fid, d):
    state.flug(fid)[d]["positionen"] = []
    S[f"v_{fid}_{d}"] = _ver(fid, d) + 1
    S.offen = fid


def tauschen(fid):
    """Last von hoch nach runter verschieben und umgekehrt (z. B. Geräte am Abend zurück)."""
    f = state.flug(fid)
    f["hoch"], f["runter"] = f["runter"], f["hoch"]
    f["modus"] = {"hoch": "runter", "runter": "hoch", "beide": "beide"}[f["modus"]]
    S[f"mod_{fid}"] = f["modus"]
    for d in ("hoch", "runter"):
        S[f"beh_{fid}_{d}"] = f[d]["behaelter"]
        S[f"v_{fid}_{d}"] = _ver(fid, d) + 1
    S.offen = fid


def vorlage():
    state.vorlage_laden(S.vl_id, runter=S.vl_runter, ersetzen=S.vl_modus == "Flugplan ersetzen", tag=int(S.vl_tag))


# ---------------------------------------------------------------------------
# Seite
# ---------------------------------------------------------------------------
R = state.result()
p, P = R["p"], R["P"]
FL = {r["id"]: r for r in R["fl"]}
cap = p["drohne.nutzlast_kg"]

page_head(PATH, "Flugplanung",
          f"Flüge anlegen und je Richtung beladen. Grenze: {de(cap)} kg am Haken, Ladung plus Behälter.")

tage = sorted({f["tag"] for f in S.fluege})
kpis([kpi_html("Flüge", str(len(S.fluege)), "", f"an {len(tage)} Einsatztag(en)", accent=True),
      kpi_html("Last hoch / runter", f"{de(R['kg_hoch'], 1)} / {de(R['kg_runter'], 1)}", "kg",
               "Ladung ohne Behälter"),
      kpi_html("Flugzeit", fmt_min(sum(r["min"] for r in R["fl"])), "", "inkl. Bodenzeiten")])
st.write("")

c1, c2, c3, _ = st.columns([2, 2, 2, 3])
c1.button("＋ Flug hinzufügen", type="primary", width="stretch", on_click=state.flug_hinzufuegen)
with c2.popover("Vorlage laden", width="stretch"):
    ids = [v["id"] for v in state.VORLAGEN]
    st.selectbox("Tagesladung", ids, key="vl_id",
                 format_func=lambda i: next(v["name"] for v in state.VORLAGEN if v["id"] == i))
    st.toggle("Am Ende alles wieder runterfliegen", value=True, key="vl_runter",
              help="Legt zu jedem Flug hoch einen Flug runter mit derselben Last an. Verbrauchter Kraftstoff "
                   "wird nicht abgezogen (sichere Seite).")
    st.number_input("Einsatztag", 1, 30, 1, key="vl_tag")
    st.radio("Vorhandene Flüge", ["Flugplan ersetzen", "Anhängen"], key="vl_modus", horizontal=True)
    st.button("Laden", type="primary", width="stretch", on_click=vorlage)
    st.caption("Verteilt die Tagesladung automatisch auf Flüge. Kraftstoff und lose Akkus kommen in getrennte Flüge, "
               "Langgut ins Lastnetz.")
c3.button("Alle Flüge löschen", width="stretch", on_click=state.alle_loeschen, disabled=not S.fluege)

if S.get("vorlage_msg"):
    note(S.pop("vorlage_msg"), icon="✓")
if R["fehler"]:
    note("Über der Lastgrenze: Flug " + ", ".join(map(str, R["fehler"])) + ". Last verringern oder auf einen "
         "weiteren Flug verteilen.", warn=True, icon="!")
st.write("")

if not S.fluege:
    note("Noch keine Flüge. Mit <b>＋ Flug hinzufügen</b> einen leeren Flug anlegen oder eine Vorlage laden.")

OPTIONEN = [FREI] + list(KAT)


def fmt_artikel(aid):
    if aid == FREI:
        return "Freie Position (Name und Gewicht eingeben)"
    a = KAT[aid]
    gg = f" · {katalog.GG_TEXT[a['gefahrgut']]}" if a["gefahrgut"] else ""
    return f"{a['kategorie']} · {a['name']} · {de(a['gewicht_kg'], 2)} kg/{a['einheit']}{gg}"


def richtung_ui(f, r, d):
    fid, last, info = f["id"], f[d], r["richtung"][d]
    st.markdown(f"**{flm.RICHTUNGEN[d]}**")
    if not info["aktiv"]:
        st.markdown(f"<div style='color:{GREY_600};padding:22px 0;text-align:center;border:1px dashed #D6D3CE;"
                    "border-radius:8px'>Leerflug</div>", unsafe_allow_html=True)
        return
    S.setdefault(f"beh_{fid}_{d}", last["behaelter"])
    st.selectbox("Behälter", list(flm.BEHAELTER), key=f"beh_{fid}_{d}", on_change=set_behaelter, args=(fid, d),
                 format_func=lambda b: flm.BEHAELTER[b][0]
                 + (f" · {de(flm.tara(b, p), 2)} kg" if flm.BEHAELTER[b][1] else ""))
    lastbalken(info["haken"], info["ladung"], info["tara"], cap)
    if last["positionen"]:
        df = pd.DataFrame([{"Artikel": x["name"], "Menge": float(x["menge"]),
                            "kg": x["kg"] * x["menge"],
                            "GG": katalog.GG_TEXT.get(x["gg"], x["gg"]), "Entfernen": False}
                           for x in last["positionen"]])
        st.data_editor(df, key=f"ed_{fid}_{d}_{_ver(fid, d)}", hide_index=True, width="stretch",
                       on_change=edit_positionen, args=(fid, d),
                       column_config={
                           "Artikel": st.column_config.TextColumn(disabled=True, width="medium"),
                           "Menge": st.column_config.NumberColumn(min_value=0, step=0.5, format="%g", width=65),
                           "kg": st.column_config.NumberColumn(disabled=True, format="%.1f", width=60),
                           "GG": st.column_config.TextColumn(disabled=True, width=80, help="Gefahrgut"),
                           "Entfernen": st.column_config.CheckboxColumn("✕", width=40, help="Position entfernen")})
    else:
        st.caption("Noch keine Last. Artikel unten hinzufügen.")
    a1, a2, a3 = st.columns([6, 2, 1], vertical_alignment="bottom")
    a1.selectbox("Artikel hinzufügen", OPTIONEN, index=1, key=f"add_{fid}_{d}", format_func=fmt_artikel)
    a2.number_input("Menge", 0.0, 1000.0, 1.0, 0.5, key=f"addm_{fid}_{d}", format="%g")
    if S.get(f"add_{fid}_{d}") == FREI:
        b1, b2, b3 = st.columns([5, 2, 3])
        b1.text_input("Bezeichnung", key=f"fn_{fid}_{d}", placeholder="z. B. Heusack, Material")
        b2.number_input("kg je Einheit", 0.0, 500.0, 5.0, 0.5, key=f"fk_{fid}_{d}")
        b3.selectbox("Gefahrgut", list(katalog.GG_TEXT), key=f"fg_{fid}_{d}",
                     format_func=lambda g: katalog.GG_TEXT[g] or "kein Gefahrgut")
    a3.button("＋", key=f"addb_{fid}_{d}", width="stretch", on_click=add_position, args=(fid, d), type="primary",
              help="Artikel hinzufügen")
    for stufe, txt in info["hinweise"]:
        note(txt, warn=True, icon="!" if stufe == "fehler" else "i")


for f in S.fluege:
    r = FL[f["id"]]
    fid = f["id"]
    teile = []
    for d, pfeil in (("hoch", "↑"), ("runter", "↓")):
        info = r["richtung"][d]
        teile.append(f"{pfeil} {de(info['haken'], 1)} kg" if info["beladen"] else f"{pfeil} leer")
    warn = " · ⚠ prüfen" if any(i["hinweise"] for i in r["richtung"].values()) else ""
    label = (f"Flug {r['nr']} · Tag {f['tag']} · {'  '.join(teile)} · {de(r['min'], 1)} min{warn}")
    with st.expander(label, expanded=S.get("offen") == fid):
        S.setdefault(f"mod_{fid}", f["modus"])
        S.setdefault(f"tag_{fid}", f["tag"])
        st.segmented_control("Beladung", list(flm.MODI), key=f"mod_{fid}", format_func=flm.MODI.get,
                             on_change=set_modus, args=(fid,))
        h2, h3, h4, h5, h6, _ = st.columns([2, 1, 1, 2, 2, 4], vertical_alignment="bottom")
        h2.number_input("Einsatztag", 1, 30, key=f"tag_{fid}", on_change=set_tag, args=(fid,))
        h3.button("↑", key=f"up_{fid}", help="Flug nach vorne", on_click=state.flug_verschieben, args=(fid, -1),
                  width="stretch")
        h4.button("↓", key=f"dn_{fid}", help="Flug nach hinten", on_click=state.flug_verschieben, args=(fid, 1),
                  width="stretch")
        h5.button("Kopieren", key=f"cp_{fid}", on_click=state.flug_kopieren, args=(fid,), width="stretch")
        h6.button("Löschen", key=f"del_{fid}", on_click=state.flug_loeschen, args=(fid,), width="stretch")
        st.caption(f"Flugzeit {de(r['flug_min'], 1)} min + Bodenzeit {de(r['boden_min'], 1)} min · "
                   f"Energie {de(r['kwh'], 2)} kWh")
        k1, k2 = st.columns({"hoch": [3, 1], "runter": [1, 3], "beide": [1, 1]}[f["modus"]], gap="large")
        with k1:
            richtung_ui(f, r, "hoch")
        with k2:
            richtung_ui(f, r, "runter")
        if f["modus"] != "beide":
            st.button("Last in die andere Richtung verschieben", key=f"sw_{fid}", on_click=tauschen, args=(fid,),
                      help="z. B. aus einem Flug hoch einen Rücktransport machen")

if R["has_dg"]:
    st.write("")
    dg_note()
nav(PATH)
footer()

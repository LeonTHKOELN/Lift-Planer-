"""Schritt 2 · Flugplanung: Flüge anlegen, Last je Richtung aus dem Gerätekatalog zusammenstellen."""
import streamlit as st

from core import fluege as flm
from core.fmt import de, fmt_min
from ui import geraete, state
from ui.components import dg_note, footer, kpi_html, kpis, lastbalken, nav, note, page_head
from ui.theme import GREY_600

PATH = "views/flugplan.py"
S = state.S
KAT = state.KATALOG


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


# ---------------------------------------------------------------------------
# Seite
# ---------------------------------------------------------------------------
R = state.result()
p, P = R["p"], R["P"]
FL = {r["id"]: r for r in R["fl"]}
AK = R["akku"]
cap = p["drohne.nutzlast_kg"]

page_head(PATH, "Flugplanung",
          f"Flüge anlegen und je Richtung beladen. Grenze: {de(cap)} kg am Haken, Ladung plus Behälter.")

tage = sorted({f["tag"] for f in S.fluege})
kpis([kpi_html("Flüge", str(len(S.fluege)), "", f"an {len(tage)} Einsatztag(en)", accent=True),
      kpi_html("Last hoch / runter", f"{de(R['kg_hoch'], 1)} / {de(R['kg_runter'], 1)}", "kg",
               "Ladung ohne Behälter"),
      kpi_html("Flugzeit", fmt_min(sum(r["min"] for r in R["fl"])), "",
               f"inkl. Bodenzeiten · {AK['wechsel']} Akkuwechsel")])
st.write("")

c1, c2, c3, _ = st.columns([2, 2, 2, 3])
c1.button("Neu aus Warenkorb verteilen", type="primary", width="stretch", on_click=state.fluege_erzeugen,
          help="Verwirft Änderungen hier und verteilt den Warenkorb neu auf Flüge")
c2.button("＋ Leeren Flug anlegen", width="stretch", on_click=state.flug_hinzufuegen)
c3.button("Alle Flüge löschen", width="stretch", on_click=state.alle_loeschen, disabled=not S.fluege)
st.caption("Die Flüge entstehen automatisch aus dem Warenkorb auf der Seite Ausrüstung. Hier kannst du sie anpassen. "
           "Ändert sich der Warenkorb, wird neu verteilt.")
if R["fehler"]:
    note("Über der Lastgrenze: Flug " + ", ".join(map(str, R["fehler"])) + ". Last verringern oder auf einen "
         "weiteren Flug verteilen.", warn=True, icon="!")
st.write("")

if not S.fluege:
    note("Noch keine Flüge. Auf der Seite <b>Ausrüstung</b> Artikel in den Warenkorb legen.")

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
        geraete.ladeliste(fid, d)
    else:
        st.caption("Noch keine Last.")
    if st.button("＋ Artikel ergänzen", key=f"open_{fid}_{d}", width="stretch"):
        S.offen = fid
        geraete.auswahl(fid, d)
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
    if AK["je_flug"].get(r["nr"], {}).get("wechsel_danach"):
        warn += " · danach Akkuwechsel"
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
        a = AK["je_flug"].get(r["nr"], {})
        wechsel = " · <b style='color:#FF6600'>danach Akkuwechsel</b>" if a.get("wechsel_danach") else ""
        st.markdown(f"<div style='color:{GREY_600};font-size:.85rem'>Flugzeit {de(r['flug_min'], 1)} min + Bodenzeit "
                    f"{de(r['boden_min'], 1)} min · Akkusatz {a.get('satz', '–')}, danach noch "
                    f"{de(a.get('rest_min', 0), 1)} min nutzbar{wechsel}</div>", unsafe_allow_html=True)
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

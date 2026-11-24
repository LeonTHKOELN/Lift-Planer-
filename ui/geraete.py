"""Geräteauswahl mit Bild: Liste aller Katalogartikel, hinzufügen mit ＋.

Fotos: assets/geraete/<id>.jpg|png|webp. Fehlt ein Foto, erscheint ein Symbol der Kategorie.
"""
import base64
import html
from pathlib import Path

import streamlit as st

from core import fluege as flm
from core import katalog
from core.fmt import de
from ui import state

S = state.S
FOTOS = Path(__file__).resolve().parent.parent / "assets" / "geraete"
_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

# Symbole je Kategorie (STIHL-Orange auf hellem Grund)
_ICON = {
    "Geräte": '<path d="M14 40h30l8-8V24H22l-8 8z" fill="#FF6600"/><rect x="50" y="26" width="10" height="4" rx="2" '
              'fill="#1A1A1A"/><circle cx="24" cy="44" r="4" fill="#1A1A1A"/>',
    "Akkus und Energie": '<rect x="20" y="16" width="24" height="34" rx="4" fill="#FF6600"/><rect x="27" y="12" '
                         'width="10" height="5" rx="1" fill="#1A1A1A"/><path d="M33 22l-6 12h6l-2 10 8-14h-6l2-8z" '
                         'fill="#fff"/>',
    "Betriebsstoffe": '<path d="M18 22l8-8h18v38H18z" fill="#FF6600"/><rect x="30" y="8" width="10" height="6" '
                      'fill="#1A1A1A"/><path d="M31 28c-4 6-4 9 0 11 4-2 4-5 0-11z" fill="#fff"/>',
    "Werkzeug und Zubehör": '<path d="M16 46l20-20 6 6-20 20z" fill="#1A1A1A"/><path d="M38 14a10 10 0 0 0 10 14l-6 '
                            '6-10-10 6-6z" fill="#FF6600"/>',
    "Sicherheit und Verpflegung": '<rect x="14" y="20" width="36" height="28" rx="4" fill="#FF6600"/><rect x="26" '
                                  'y="14" width="12" height="7" rx="2" fill="none" stroke="#1A1A1A" stroke-width="3"/>'
                                  '<path d="M29 26h6v6h6v6h-6v6h-6v-6h-6v-6h6z" fill="#fff"/>',
    "Transportbehälter": '<path d="M10 24h44l-4 24H14z" fill="#FF6600"/><path d="M8 18h48v7H8z" fill="#1A1A1A"/>'
                         '<path d="M24 32h16" stroke="#fff" stroke-width="3"/>',
    "frei": '<rect x="14" y="18" width="36" height="30" rx="3" fill="#FF6600"/><path d="M14 26h36" stroke="#1A1A1A" '
            'stroke-width="3"/>',
}


@st.cache_data
def _foto(aid: str, stand: float):  # stand: neue Datei → neu laden
    for ext, mime in _MIME.items():
        f = FOTOS / f"{aid}{ext}"
        if f.exists():
            return f"data:{mime};base64," + base64.b64encode(f.read_bytes()).decode()
    return None


def bild(aid, kategorie, px=88):
    src = _foto(aid, FOTOS.stat().st_mtime) if aid else None
    if src:
        inner = f'<img src="{src}" style="max-width:100%;max-height:100%;object-fit:contain">'
    else:
        inner = (f'<svg viewBox="0 0 64 64" width="{int(px * .62)}" height="{int(px * .62)}">'
                 f'{_ICON.get(kategorie, _ICON["frei"])}</svg>')
    return (f'<div style="height:{px}px;display:flex;align-items:center;justify-content:center;background:#F6F5F3;'
            f'border-radius:8px">{inner}</div>')


def menge_aendern(fid, d, i, delta):
    last = state.flug(fid)[d]
    x = last["positionen"][i]
    x["menge"] = round(x["menge"] + delta, 3)
    if x["menge"] <= 0:
        last["positionen"].pop(i)
    S.offen = fid


def hinzufuegen(fid, d, aid):
    last = state.flug(fid)[d]
    same = next((x for x in last["positionen"] if x["artikel"] == aid), None)
    if same:
        same["menge"] += 1
    else:
        last["positionen"].append(katalog.position(state.KATALOG[aid], 1))
    S.offen = fid


def frei_hinzufuegen(fid, d):
    name = (S.get("dlg_fn") or "").strip() or "Freie Position"
    last = state.flug(fid)[d]
    last["positionen"].append(katalog.freie_position(name, S.get("dlg_fk", 0.0), 1, S.get("dlg_fg", "")))
    S.dlg_fn = ""
    S.offen = fid


def ladeliste(fid, d):
    """Geladene Positionen mit Bild, Gewicht und − Menge ＋."""
    last = state.flug(fid)[d]
    for i, x in enumerate(last["positionen"]):
        kat = state.KATALOG[x["artikel"]]["kategorie"] if x["artikel"] in state.KATALOG else "frei"
        c0, c1, c2, c3, c4, c5 = st.columns([1.1, 5, 1.6, 0.9, 1.1, 0.9], vertical_alignment="center", gap="small")
        c0.markdown(bild(x["artikel"], kat, 44), unsafe_allow_html=True)
        gg = f" · <span style='color:#C62828'>{katalog.GG_TEXT[x['gg']]}</span>" if x["gg"] else ""
        c1.markdown(f"<div style='line-height:1.25'><b>{html.escape(x['name'])}</b><br><span style='color:#5E5E5E;"
                    f"font-size:.8rem'>{de(x['kg'], 2)} kg/{x['einheit']}{gg}</span></div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='text-align:right'><b>{de(x['kg'] * x['menge'], 1)} kg</b></div>",
                    unsafe_allow_html=True)
        c3.button("−", key=f"mi_{fid}_{d}_{i}", on_click=menge_aendern, args=(fid, d, i, -1), width="stretch")
        c4.markdown(f"<div style='text-align:center;font-weight:700'>{de(x['menge'], 2).rstrip('0').rstrip(',')}"
                    f" {x['einheit']}</div>", unsafe_allow_html=True)
        c5.button("＋", key=f"pl_{fid}_{d}_{i}", on_click=menge_aendern, args=(fid, d, i, 1), width="stretch")


@st.dialog("Geräte hinzufügen", width="large")
def auswahl(fid, d):
    p = state.params()
    f = state.flug(fid)
    last = f[d]
    nr = next(i for i, x in enumerate(S.fluege, 1) if x["id"] == fid)
    haken, cap = flm.am_haken(last, p), p["drohne.nutzlast_kg"]
    farbe = "#C62828" if haken > cap else "#FF6600"
    st.markdown(f"Flug {nr} · {flm.RICHTUNGEN[d]} · <b style='color:{farbe}'>{de(haken, 1)} kg</b> von "
                f"{de(cap)} kg am Haken", unsafe_allow_html=True)
    k1, k2 = st.columns([3, 2], vertical_alignment="bottom")
    kats = k1.pills("Kategorie", katalog.KATEGORIEN, selection_mode="multi", key="dlg_kat")
    suche = k2.text_input("Suche", key="dlg_suche", placeholder="z. B. Akku, Säge").strip().lower()
    arts = [a for a in state.KATALOG.values() if (not kats or a["kategorie"] in kats)
            and (not suche or suche in a["name"].lower())]
    im_flug = {x["artikel"]: x["menge"] for x in last["positionen"]}
    cols = st.columns(4)
    for i, a in enumerate(arts):
        with cols[i % 4], st.container(border=True):
            st.markdown(bild(a["id"], a["kategorie"], 92), unsafe_allow_html=True)
            gg = (f"<br><span style='color:#C62828;font-size:.75rem'>{katalog.GG_TEXT[a['gefahrgut']]}</span>"
                  if a["gefahrgut"] else "<br><span style='font-size:.75rem'>&nbsp;</span>")
            st.markdown(f"<div style='font-size:.85rem;line-height:1.2;height:3.7em;overflow:hidden'>"
                        f"<b>{html.escape(a['name'])}</b></div><div style='font-size:.8rem;color:#5E5E5E'>"
                        f"{de(a['gewicht_kg'], 2)} kg/{a['einheit']}{gg}</div>", unsafe_allow_html=True)
            n = im_flug.get(a["id"])
            st.button(f"＋  ({de(n, 2).rstrip('0').rstrip(',')} im Flug)" if n else "＋", key=f"dlg_{a['id']}",
                      type="primary" if n else "secondary", width="stretch", on_click=hinzufuegen,
                      args=(fid, d, a["id"]))
    if not arts:
        st.caption("Kein Artikel gefunden.")
    with st.expander("Eigene Position (nicht im Katalog), z. B. Heusack"):
        b1, b2, b3, b4 = st.columns([4, 2, 2, 1], vertical_alignment="bottom")
        b1.text_input("Bezeichnung", key="dlg_fn", placeholder="z. B. Heusack gefüllt")
        b2.number_input("kg", 0.0, 500.0, 5.0, 0.5, key="dlg_fk")
        b3.selectbox("Gefahrgut", list(katalog.GG_TEXT), key="dlg_fg",
                     format_func=lambda g: katalog.GG_TEXT[g] or "kein")
        b4.button("＋", key="dlg_frei", on_click=frei_hinzufuegen, args=(fid, d), width="stretch")
    if st.button("Fertig", type="primary"):
        st.rerun()

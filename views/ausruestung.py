"""Schritt 4 · Ausrüstung: alle Artikel wie im Onlineshop, nach Kategorien. Der Warenkorb wird automatisch
auf Flüge bis zur Lastgrenze verteilt (Seite Flugplanung)."""
import html

import streamlit as st

from core import fluege as flm
from core import katalog
from core.fmt import de
from ui import geraete, state
from ui.components import footer, nav, note, page_head, section_title

PATH = "views/ausruestung.py"
S = state.S
R = state.result()
p = R["p"]
KAT = state.KATALOG
BEH = [b for b in flm.BEHAELTER if b != "ohne"]
BEH_INFO = {"grund": "Standard für Geräte und Werkzeug", "kassette": "Für lose Ersatzakkus (Kl. 9)",
            "ring": "Mehr Innenhöhe, z. B. Rückengeräte", "netz": "Für Langgut, das nicht in die Box passt"}


def menge_txt(n):
    return de(n, 2).rstrip("0").rstrip(",")


def vorlage():
    state.vorlage_laden(S.sh_vorlage, ersetzen=S.sh_vl_modus == "Warenkorb ersetzen")


def rueck():
    S.rueck = S.sh_rueck
    state.fluege_erzeugen()


def karte(a, key):
    n = S.warenkorb.get(a["id"], 0)
    with st.container(border=True):
        st.markdown(geraete.bild(a["id"], a["kategorie"], 118), unsafe_allow_html=True)
        gg = (f"<span class='sh-gg'>{katalog.GG_TEXT[a['gefahrgut']]}</span>" if a["gefahrgut"] else "")
        lang = (f"<span class='sh-gg' style='background:#EFEDEA;color:#1A1A1A'>Langgut {de(a['laenge_mm'])} mm</span>"
                if a["laenge_mm"] and a["laenge_mm"] > p["box.innenlaenge_mm"] else "")
        st.markdown(f"<div class='sh-name'>{html.escape(a['name'])}</div>"
                    f"<div class='sh-kg'>{de(a['gewicht_kg'], 2)} kg <span>je {a['einheit']}</span></div>"
                    f"<div class='sh-tags'>{gg}{lang}&nbsp;</div>", unsafe_allow_html=True)
        if not n:
            st.button("＋ In den Warenkorb", key=f"sh_{key}", width="stretch", on_click=state.korb_aendern,
                      args=(a["id"], 1))
        else:
            c1, c2, c3 = st.columns(3, vertical_alignment="center", gap="small")
            c1.button("", icon=":material/remove:", key=f"shm_{key}", width="stretch", on_click=state.korb_aendern,
                      args=(a["id"], -1), help="Eins weniger")
            c2.markdown(f"<div class='sh-n'>{menge_txt(n)} {a['einheit']}</div>", unsafe_allow_html=True)
            c3.button("", icon=":material/add:", key=f"shp_{key}", width="stretch", type="primary",
                      on_click=state.korb_aendern, args=(a["id"], 1), help="Eins mehr")


def raster(arts, key):
    cols = st.columns(3, gap="small")
    for i, a in enumerate(arts):
        with cols[i % 3]:
            karte(a, f"{key}_{a['id']}")


def behaelter_karte(b):
    an = b in S.behaelter_ok
    with st.container(border=True):
        st.markdown(geraete.bild("box_" + b, "Transportbehälter", 118), unsafe_allow_html=True)
        st.markdown(f"<div class='sh-name'>{flm.BEHAELTER[b][0]}</div>"
                    f"<div class='sh-kg'>{de(flm.tara(b, p), 2)} kg <span>Eigengewicht</span></div>"
                    f"<div class='sh-tags' style='color:#5E5E5E;font-size:.78rem'>{BEH_INFO[b]}</div>",
                    unsafe_allow_html=True)
        st.button("✓ verfügbar" if an else "＋ Verfügbar machen", key=f"beh_{b}", width="stretch",
                  type="primary" if an else "secondary", on_click=state.behaelter_umschalten, args=(b,))


st.markdown("""<style>
.sh-name{font-weight:700;font-size:.9rem;line-height:1.25;height:2.5em;overflow:hidden;margin-top:8px}
.sh-kg{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:1.35rem;color:#1A1A1A}
.sh-kg span{font-family:Barlow,sans-serif;font-weight:400;font-size:.78rem;color:#5E5E5E}
.sh-tags{min-height:22px}
.sh-gg{display:inline-block;background:#FDECEA;color:#C62828;border-radius:10px;padding:1px 8px;font-size:.72rem;
 font-weight:600;margin-right:4px}
.sh-n{text-align:center;font-weight:700}
.sh-row{display:flex;justify-content:space-between;gap:8px;font-size:.85rem;padding:5px 0;border-bottom:1px solid #EFEDEA}
.sh-row span:last-child{white-space:nowrap;font-weight:600}
.sh-sum{display:flex;justify-content:space-between;font-size:.9rem;padding:4px 0}
</style>""", unsafe_allow_html=True)

page_head(PATH, "Ausrüstung", "Alles, was mit auf den Hang soll, in den Warenkorb legen. Die App verteilt es "
                              f"automatisch auf Flüge bis {de(p['drohne.nutzlast_kg'])} kg am Haken.")

links, rechts = st.columns([3, 1.25], gap="large")
with links:
    t1, t2 = st.columns([3, 2], vertical_alignment="bottom")
    suche = t1.text_input("Suche", key="sh_suche", placeholder="Artikel suchen, z. B. Akku oder Säge",
                          label_visibility="collapsed").strip().lower()
    with t2.popover("Vorlage S1 bis S5 laden", icon=":material/inventory:", width="stretch"):
        ids = [v["id"] for v in state.VORLAGEN]
        st.selectbox("Vorlage", ids, key="sh_vorlage",
                     format_func=lambda i: next(v["name"] for v in state.VORLAGEN if v["id"] == i))
        st.radio("Warenkorb", ["Warenkorb ersetzen", "Hinzufügen"], key="sh_vl_modus", horizontal=True)
        st.button("Laden", type="primary", width="stretch", on_click=vorlage)
    if S.get("vorlage_msg"):
        st.caption("✓ " + S.pop("vorlage_msg"))
    if suche:
        treffer = [a for a in KAT.values() if suche in a["name"].lower() or suche in a["kategorie"].lower()]
        section_title(f"{len(treffer)} Treffer")
        raster(treffer, "s")
    else:
        KURZ = {"Akkus und Energie": "Akkus & Energie", "Werkzeug und Zubehör": "Werkzeug",
                "Sicherheit und Verpflegung": "Sicherheit"}
        tabs = st.tabs([KURZ.get(k, k) for k in katalog.KATEGORIEN] + ["Behälter", "Eigene"])
        for tab, kat in zip(tabs, katalog.KATEGORIEN):
            with tab:
                raster([a for a in KAT.values() if a["kategorie"] == kat], kat[:4])
        with tabs[-2]:
            st.caption("Welche Behälter stehen für diesen Einsatz bereit? Die App packt nur in verfügbare Behälter.")
            cols = st.columns(3, gap="small")
            for i, b in enumerate(BEH):
                with cols[i % 3]:
                    behaelter_karte(b)
        with tabs[-1]:
            st.caption("Alles, was nicht im Katalog steht, z. B. gefüllte Heusäcke, die nur ins Tal fliegen.")
            with st.container(border=True):
                e1, e2, e3 = st.columns([4, 2, 2])
                e1.text_input("Bezeichnung", key="eig_name", placeholder="z. B. Heusack gefüllt")
                e2.number_input("kg je Stück", 0.0, 500.0, 30.0, 0.5, key="eig_kg")
                e3.number_input("Anzahl", 1, 500, 1, key="eig_n")
                e4, e5, e6 = st.columns([3, 3, 2], vertical_alignment="bottom")
                e4.segmented_control("Richtung", ["hoch", "runter"], key="eig_richtung", default="runter",
                                     format_func={"hoch": "hoch (und ggf. zurück)", "runter": "nur runter"}.get)
                e5.selectbox("Gefahrgut", list(katalog.GG_TEXT), key="eig_gg",
                             format_func=lambda g: katalog.GG_TEXT[g] or "kein Gefahrgut")
                e6.button("＋ In den Warenkorb", key="eig_add", width="stretch", type="primary",
                          on_click=state.eigene_hinzufuegen)

with rechts:
    with st.container(border=True):
        section_title("Warenkorb")
        rows = []
        for aid, n in S.warenkorb.items():
            a = KAT[aid]
            rows.append(f"<div class='sh-row'><span>{menge_txt(n)} {a['einheit']} × {html.escape(a['name'])}</span>"
                        f"<span>{de(a['gewicht_kg'] * n, 1)} kg</span></div>")
        st.markdown("".join(rows) or "<div style='color:#5E5E5E;font-size:.85rem'>Noch leer.</div>",
                    unsafe_allow_html=True)
        for i, e in enumerate(S.eigene):
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            c1.markdown(f"<div class='sh-row'><span>{menge_txt(e['menge'])} × {html.escape(e['name'])}"
                        f"{' · nur runter' if e['richtung'] == 'runter' else ''}</span>"
                        f"<span>{de(e['kg'] * e['menge'], 1)} kg</span></div>", unsafe_allow_html=True)
            c2.button("✕", key=f"eig_del_{i}", on_click=state.eigene_loeschen, args=(i,), help="Entfernen")
        hoch, runter_nur = state.korb_positionen()
        kg_h = sum(x["kg"] * x["menge"] for x in hoch)
        kg_r = sum(x["kg"] * x["menge"] for x in runter_nur)
        gg = sum(x["kg"] * x["menge"] for x in hoch + runter_nur if x["gg"])
        st.write("")
        st.markdown(f"<div class='sh-sum'><span>Ladung hoch</span><b>{de(kg_h, 1)} kg</b></div>"
                    + (f"<div class='sh-sum'><span>nur runter</span><b>{de(kg_r, 1)} kg</b></div>" if kg_r else "")
                    + f"<div class='sh-sum'><span>davon Gefahrgut</span><b>{de(gg, 1)} kg</b></div>"
                    f"<div class='sh-sum'><span>Behälter</span><b>"
                    f"{', '.join(flm.BEHAELTER[b][0].replace('Grundbox mit ', '') for b in S.behaelter_ok) or 'keine'}"
                    f"</b></div>", unsafe_allow_html=True)
        S.sh_rueck = S.rueck
        st.toggle("Am Ende alles wieder runterfliegen", key="sh_rueck", on_change=rueck)
        fl = R["fl"]
        n_h = sum(1 for f in fl if f["modus"] == "hoch")
        n_r = sum(1 for f in fl if f["modus"] == "runter")
        st.markdown(f"<div class='lp-hero' style='padding:14px 16px;margin-top:6px'><div><div class='t'>Ergibt</div>"
                    f"<div class='big' style='font-size:1.9rem'>{len(fl)} Flüge</div><div class='sub'>{n_h} hoch · "
                    f"{n_r} runter</div></div></div>", unsafe_allow_html=True)
        if R["fehler"]:
            note("Ein Artikel ist schwerer als die Lastgrenze. Siehe Flugplanung.", warn=True, icon="!")
        st.write("")
        if st.button("Zur Flugplanung →", type="primary", width="stretch"):
            st.switch_page("views/flugplan.py")
        st.button("Warenkorb leeren", width="stretch", on_click=state.korb_leeren,
                  disabled=not (S.warenkorb or S.eigene))
nav(PATH)
footer()

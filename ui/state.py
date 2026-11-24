"""Sitzungszustand: Einsatzdaten (w_*), Flugplan (fluege), Parameterwerte (p.*) und Metadaten (m.*).

- w_<name>   Eingaben der Seite Einsatz (Koordinaten, Team …)
- fluege     Liste der geplanten Flüge mit Last je Richtung
- p.<key>    aktueller Wert eines Parameters aus config/parameter.yaml
- m.<key>    Status, Quelle und Kommentar eines Parameters (in der App änderbar)
"""
import copy
import csv
import re
import uuid

import streamlit as st

from core import fluege as flm
from core import akku, geo, hoehe, katalog, kosten, profil, wetter
from core import params as registry
from core.fmt import de

S = st.session_state

PLAN_PAGES = [  # Reihenfolge der Planungsschritte (Stepper und Weiter/Zurück)
    ("views/einsatz.py", "Einsatz"),
    ("views/flugweg.py", "Flugweg"),
    ("views/wetter.py", "Wetter"),
    ("views/ausruestung.py", "Ausrüstung"),
    ("views/flugplan.py", "Flugplanung"),
    ("views/kosten.py", "Kosten"),
]

JOB_DEFAULTS = {
    # Standard: Forstwirtschaft St. Gallenkirch (wie data/standorte.csv)
    "w_einsatz": "Holzernte St. Gallenkirch",
    "w_start_name": "Landeplatz Forst",
    "w_start_lat": 47.031639, "w_start_lon": 9.991611, "w_start_alt": 1000,
    "w_ziel_lat": 47.029139, "w_ziel_lon": 9.996583, "w_ziel_alt": 1200,
    "w_alt_manual": False, "w_start_paste": "", "w_ziel_paste": "",
}
EXPORT_JOB_KEYS = [k for k in JOB_DEFAULTS if not k.endswith("_paste")]
STANDORT_DATEI = katalog.DATA / "standorte.csv"


def _stand(*pfade):
    """Änderungszeitpunkt der Dateien: neuer Stand im Repo → Zwischenspeicher wird neu befüllt."""
    return tuple(pf.stat().st_mtime_ns if pf.exists() else 0 for pf in pfade)


@st.cache_resource
def load_config(stand):  # stand wird gehasht: neue Dateien im Repo → neu laden
    params, gruppen = registry.load_registry()
    with open(STANDORT_DATEI, encoding="utf-8") as f:
        orte = [dict(r, **{k: float(r[k]) for k in ("start_lat", "start_lon", "ziel_lat", "ziel_lon")})
                for r in csv.DictReader(f)]
    return params, gruppen, registry.load_scenarios(), katalog.load(), katalog.load_vorlagen(), orte


def refresh_config():
    """Konfiguration aktuell halten (wird bei jedem Seitenaufruf in init() aufgerufen)."""
    global REG, GRUPPEN, SZENARIEN, KATALOG, VORLAGEN, STANDORTE
    REG, GRUPPEN, SZENARIEN, KATALOG, VORLAGEN, STANDORTE = load_config(_stand(
        registry.CONFIG / "parameter.yaml", registry.CONFIG / "szenarien.yaml", katalog.KATALOG, katalog.VORLAGEN,
        STANDORT_DATEI))


refresh_config()


def meta_default(k):
    p = REG[k]
    return {"status": p.status, "quelle": p.quelle, "kommentar": p.kommentar}


def init():
    refresh_config()
    for k, v in JOB_DEFAULTS.items():
        S.setdefault(k, v)
    for k, p in REG.items():
        S.setdefault(f"p.{k}", p.wert)
        S.setdefault(f"m.{k}", meta_default(k))
    for k in [k for k in S.keys() if str(k).startswith(("p.", "m.")) and str(k)[2:] not in REG]:
        del S[k]  # Parameter, die es im neuen Stand nicht mehr gibt
    S.setdefault("szenario", "Basis")
    S.setdefault("ed_ver", 0)
    S.setdefault("pin_mode", "Landeplatz")
    S.setdefault("sel_standort", STANDORTE[0]["name"] if STANDORTE else None)
    if "warenkorb" not in S:
        S.warenkorb, S.eigene, S.behaelter_ok, S.rueck = {}, [], ["grund", "kassette", "netz"], True
        vorlage_laden("S1", ersetzen=True)
    # Widget-Werte über Seitenwechsel erhalten (Streamlit löscht sonst Werte nicht angezeigter Widgets)
    for k in [k for k in S.keys() if str(k).startswith("w_")]:
        S[k] = S[k]
    if "pending_pin" in S:  # Kartenklick aus dem letzten Lauf übernehmen (vor dem Rendern der Widgets)
        mode, lat, lon = S.pop("pending_pin")
        pre = "start" if mode == "Landeplatz" else "ziel"
        S[f"w_{pre}_lat"], S[f"w_{pre}_lon"] = lat, lon
        S["pin_mode"] = "Einsatzort" if mode == "Landeplatz" else "Landeplatz"


def standort_laden():
    """Standardeinsatz übernehmen: Punkte, Namen und passende Vorlage für den Flugplan."""
    o = next((x for x in STANDORTE if x["name"] == S.get("sel_standort")), None)
    if o is None:
        return
    S.w_einsatz, S.w_start_name = o["einsatz"], o["start_name"]
    S.w_start_lat, S.w_start_lon, S.w_ziel_lat, S.w_ziel_lon = o["start_lat"], o["start_lon"], o["ziel_lat"], o["ziel_lon"]
    S.w_alt_manual = False
    if o.get("vorlage") and S.get("standort_vorlage", True):
        vorlage_laden(o["vorlage"], ersetzen=True)
    S.standort_msg = f"Standardeinsatz „{o['name']}“ geladen."


# ---------------------------------------------------------------------------
# Flugplan
# ---------------------------------------------------------------------------
def _leer(behaelter="grund"):
    return {"behaelter": behaelter, "positionen": []}


def neuer_flug(tag=None, modus="hoch"):
    tag = tag or (S.fluege[-1]["tag"] if S.fluege else 1)
    return {"id": uuid.uuid4().hex[:8], "tag": tag, "modus": modus, "hoch": _leer(), "runter": _leer()}


def flug_hinzufuegen():
    S.fluege.append(neuer_flug())
    S.offen = S.fluege[-1]["id"]


def flug_kopieren(fid):
    i = next(i for i, f in enumerate(S.fluege) if f["id"] == fid)
    f = copy.deepcopy(S.fluege[i])
    f["id"] = uuid.uuid4().hex[:8]
    S.fluege.insert(i + 1, f)
    S.offen = f["id"]


def flug_loeschen(fid):
    S.fluege = [f for f in S.fluege if f["id"] != fid]


def flug_verschieben(fid, delta):
    i = next(i for i, f in enumerate(S.fluege) if f["id"] == fid)
    j = i + delta
    if 0 <= j < len(S.fluege):
        S.fluege[i], S.fluege[j] = S.fluege[j], S.fluege[i]


def flug(fid):
    return next(f for f in S.fluege if f["id"] == fid)


# ---------------------------------------------------------------------------
# Warenkorb (Seite Ausrüstung) → Flugplan
# ---------------------------------------------------------------------------
def vorlage_laden(vid, ersetzen=True):
    """Tagesladung einer Vorlage in den Warenkorb legen."""
    v = next(x for x in VORLAGEN if x["id"] == vid)
    if ersetzen:
        S.warenkorb, S.eigene = {}, []
    for x in v["positionen"]:
        S.warenkorb[x["artikel"]] = S.warenkorb.get(x["artikel"], 0) + x["menge"]
    S.vorlage_msg = f"Vorlage {v['name']} im Warenkorb."
    fluege_erzeugen()


def korb_aendern(aid, delta):
    n = round(S.warenkorb.get(aid, 0) + delta, 3)
    if n > 0:
        S.warenkorb[aid] = n
    else:
        S.warenkorb.pop(aid, None)
    fluege_erzeugen()


def behaelter_umschalten(b):
    ok = list(S.behaelter_ok)
    S.behaelter_ok = [x for x in ok if x != b] if b in ok else ok + [b]
    fluege_erzeugen()


def eigene_hinzufuegen():
    name = (S.get("eig_name") or "").strip() or "Eigene Position"
    S.eigene.append({"name": name, "kg": float(S.get("eig_kg", 0.0)), "menge": float(S.get("eig_n", 1)),
                     "gg": S.get("eig_gg", ""), "richtung": S.get("eig_richtung", "hoch")})
    S.eig_name = ""
    fluege_erzeugen()


def eigene_loeschen(i):
    S.eigene.pop(i)
    fluege_erzeugen()


def korb_leeren():
    S.warenkorb, S.eigene = {}, []
    fluege_erzeugen()


def korb_positionen():
    """Warenkorb als Ladepositionen, getrennt nach Richtung."""
    hoch = [katalog.position(KATALOG[a], m) for a, m in S.warenkorb.items() if a in KATALOG]
    runter_nur = []
    for e in S.eigene:
        pos = katalog.freie_position(e["name"], e["kg"], e["menge"], e["gg"])
        (runter_nur if e["richtung"] == "runter" else hoch).append(pos)
    return hoch, runter_nur


def fluege_erzeugen():
    """Flugplan aus dem Warenkorb: Ladung hoch auf Flüge verteilen, bei Rücktransport dieselbe Last wieder
    runter. Eigene Positionen „nur runter“ (z. B. Heusäcke) als eigene Flüge runter."""
    p = params()
    hoch, runter_nur = korb_positionen()
    erlaubt = S.behaelter_ok or ["ohne"]
    lasten_hoch = flm.packen(hoch, p, erlaubt) if hoch else []
    neu = []
    for last in lasten_hoch:
        f = neuer_flug(1, "hoch")
        f["hoch"] = copy.deepcopy(last)
        neu.append(f)
    if S.rueck:
        for last in lasten_hoch:
            f = neuer_flug(1, "runter")
            f["runter"] = copy.deepcopy(last)
            neu.append(f)
    for last in (flm.packen(runter_nur, p, erlaubt) if runter_nur else []):
        f = neuer_flug(1, "runter")
        f["runter"] = copy.deepcopy(last)
        neu.append(f)
    S.fluege = neu
    S.offen = None


def alle_loeschen():
    S.fluege = []


# ---------------------------------------------------------------------------
# Netzwerkdaten
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner="Wettervorhersage wird geladen …")
def _wetter(lat: float, lon: float, hoehe_m: int, version: int):  # version: neues Datenformat → neu laden
    return wetter.fetch(lat, lon, hoehe_m)


def wetter_laden(punkt, hoehe_m):
    """Vorhersage am Einsatzort (Koordinaten gerundet, damit kleine Verschiebungen den Cache nutzen)."""
    try:
        tage, _ = _wetter(round(punkt[0], 3), round(punkt[1], 3), int(round(hoehe_m)), wetter.FORMAT_VERSION)
        return tage, ""
    except Exception as e:  # noqa: BLE001
        return None, str(e)


@st.cache_data(ttl=7 * 24 * 3600, show_spinner="Höhendaten werden geladen …")
def _elevations(coords: tuple):
    return hoehe.fetch_elevations(list(coords))


def params() -> dict:
    return {k: S[f"p.{k}"] for k in REG}


def changed_keys() -> list:
    return [k for k, p in REG.items() if S[f"p.{k}"] != p.wert]


def job() -> dict:
    return {"einsatz": S.w_einsatz, "start_name": S.w_start_name,
            "start": (S.w_start_lat, S.w_start_lon), "ziel": (S.w_ziel_lat, S.w_ziel_lon)}


def build_profile(p, j):
    dist, pts, ds, step_eff = geo.sample_route(j["start"], j["ziel"], p["profil.raster_m"])
    terrain, source, error, real = None, "", "", False
    if not S.w_alt_manual:
        try:
            terrain, source = _elevations(tuple((round(a, 6), round(b, 6)) for a, b in pts))
            real = True
            S.w_start_alt, S.w_ziel_alt = int(round(terrain[0])), int(round(terrain[-1]))
        except Exception as e:  # noqa: BLE001
            error = str(e)
    if terrain is None:
        terrain = profil.linear_terrain(ds, S.w_start_alt, S.w_ziel_alt)
        source = "Manuelle Höhen (lineare Verbindung, kein Geländeprofil)"
    return profil.build_profile(j["start"], j["ziel"], dist, pts, ds, step_eff, terrain, source, real, error, p)


def result():
    """Komplette Rechnung für den aktuellen Stand. Wird auf jeder Seite vor den Widgets aufgerufen."""
    p, j = params(), job()
    prof = build_profile(p, j)
    fl, tr_fl = flm.auswerten(S.fluege, prof, p)
    ak = akku.plan(fl, p)
    ko = kosten.eigenbetrieb(fl, ak, p)
    kg_hoch = sum(f["richtung"]["hoch"]["ladung"] for f in fl)
    kg_runter = sum(f["richtung"]["runter"]["ladung"] for f in fl)
    return {"P": prof, "p": p, "job": j, "fl": fl, "akku": ak, "kosten": ko, "kg_hoch": kg_hoch,
            "kg_runter": kg_runter, "usecase": "Forst", "has_dg": any(f["gefahrgut"] for f in fl),
            "fehler": [f["nr"] for f in fl if f["fehler"]],
            "traces": [prof["trace"], tr_fl, ak["trace"], ko["trace"]]}


# ---------- Koordinaten einfügen ----------
COORD_RE = re.compile(r"\s*(-?\d+(?:[.,]\d+)?)\s*[,; ]\s*(-?\d+(?:[.,]\d+)?)\s*$")


def apply_paste(prefix):
    txt = S[f"w_{prefix}_paste"]
    m = COORD_RE.match(txt or "")
    ok = False
    if m:
        lat, lon = (float(g.replace(",", ".")) for g in m.groups())
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            S[f"w_{prefix}_lat"], S[f"w_{prefix}_lon"] = round(lat, 6), round(lon, 6)
            S[f"w_{prefix}_paste"] = ""
            ok = True
    S[f"paste_err_{prefix}"] = bool(txt) and not ok


__all__ = ["de"]

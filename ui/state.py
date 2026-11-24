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
from core import geo, hoehe, katalog, kosten, profil, wetter
from core import params as registry
from core.fmt import de

S = st.session_state

PLAN_PAGES = [  # Reihenfolge der Planungsschritte (Stepper und Weiter/Zurück)
    ("views/einsatz.py", "Einsatz & Route"),
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
    "w_team": 2,
}
EXPORT_JOB_KEYS = [k for k in JOB_DEFAULTS if not k.endswith("_paste")]
HELI_DATEI = katalog.DATA / "heli_basen.csv"
STANDORT_DATEI = katalog.DATA / "standorte.csv"


def _stand(*pfade):
    """Änderungszeitpunkt der Dateien: neuer Stand im Repo → Zwischenspeicher wird neu befüllt."""
    return tuple(pf.stat().st_mtime_ns for pf in pfade)


@st.cache_resource
def load_config(stand):  # stand wird gehasht: neue Dateien im Repo → neu laden
    params, gruppen = registry.load_registry()
    with open(HELI_DATEI, encoding="utf-8") as f:
        basen = [dict(r, lat=float(r["lat"]), lon=float(r["lon"])) for r in csv.DictReader(f)]
    with open(STANDORT_DATEI, encoding="utf-8") as f:
        orte = [dict(r, **{k: float(r[k]) for k in ("start_lat", "start_lon", "ziel_lat", "ziel_lon")})
                for r in csv.DictReader(f)]
    return params, gruppen, registry.load_scenarios(), katalog.load(), katalog.load_vorlagen(), basen, orte


def refresh_config():
    """Konfiguration aktuell halten (wird bei jedem Seitenaufruf in init() aufgerufen)."""
    global REG, GRUPPEN, SZENARIEN, KATALOG, VORLAGEN, HELI_BASEN, STANDORTE
    REG, GRUPPEN, SZENARIEN, KATALOG, VORLAGEN, HELI_BASEN, STANDORTE = load_config(_stand(
        registry.CONFIG / "parameter.yaml", registry.CONFIG / "szenarien.yaml", katalog.KATALOG, katalog.VORLAGEN,
        HELI_DATEI, STANDORT_DATEI))


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
    if "fluege" not in S:
        S.fluege = []
        vorlage_laden("S1", runter=True, ersetzen=True)
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
        vorlage_laden(o["vorlage"], runter=True, ersetzen=True)
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


def vorlage_laden(vid, runter=True, ersetzen=True, tag=1):
    """Tagesladung einer Vorlage auf Flüge verteilen. runter: am Ende dieselbe Last wieder ins Tal."""
    v = next(x for x in VORLAGEN if x["id"] == vid)
    pos = [katalog.position(KATALOG[x["artikel"]], x["menge"]) for x in v["positionen"]]
    p = params()
    lasten = flm.packen(pos, p)
    neu = []
    for last in lasten:
        f = neuer_flug(tag, "hoch")
        f["hoch"] = copy.deepcopy(last)
        neu.append(f)
    if runter:
        for last in lasten:
            f = neuer_flug(tag, "runter")
            f["runter"] = copy.deepcopy(last)
            neu.append(f)
    S.fluege = neu if ersetzen else S.fluege + neu
    S.offen = None
    S.vorlage_msg = (f"Vorlage {v['name']}: {len(lasten)} Flug/Flüge hoch"
                     + (f" und {len(lasten)} runter" if runter else "") + ".")


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
            "start": (S.w_start_lat, S.w_start_lon), "ziel": (S.w_ziel_lat, S.w_ziel_lon), "team": int(S.w_team)}


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


def heli_basis(landeplatz):
    basen = [{"name": b["name"], "km": geo.haversine_m(b["lat"], b["lon"], *landeplatz) / 1000} for b in HELI_BASEN]
    return min(basen, key=lambda b: b["km"]) if basen else {"name": "keine Basis hinterlegt", "km": 0.0}


def result():
    """Komplette Rechnung für den aktuellen Stand. Wird auf jeder Seite vor den Widgets aufgerufen."""
    p, j = params(), job()
    prof = build_profile(p, j)
    fl, tr_fl = flm.auswerten(S.fluege, prof, p)
    drohne = kosten.eigenbetrieb(fl, p)

    # Vergleich: dieselbe Fracht je Einsatztag und Richtung
    lasten = {}
    for f in fl:
        for d in ("hoch", "runter"):
            lasten[(f["tag"], d)] = lasten.get((f["tag"], d), 0.0) + f["richtung"][d]["ladung"]
    basis = heli_basis(j["start"])
    he = kosten.heli([{"name": f"Tag {t} {flm.RICHTUNGEN[d]}", "kg": kg} for (t, d), kg in sorted(lasten.items())],
                     p, basis)
    laeufe = [{"name": f"Tag {t} {flm.RICHTUNGEN[d]}", "kg": kg, "traglast": p["manuell.traglast_kg"],
               "richtung": d, "anzahl": 1} for (t, d), kg in sorted(lasten.items()) if kg > 0]
    ma = kosten.manuell(prof, p, j["team"], laeufe)
    kg_hoch = sum(kg for (_, d), kg in lasten.items() if d == "hoch")
    kg_runter = sum(kg for (_, d), kg in lasten.items() if d == "runter")
    return {"P": prof, "p": p, "job": j, "fl": fl, "drohne": drohne, "heli": he, "manuell": ma,
            "heli_basis": basis, "kg_hoch": kg_hoch, "kg_runter": kg_runter, "usecase": "Forst",
            "has_dg": any(f["gefahrgut"] for f in fl), "fehler": [f["nr"] for f in fl if f["fehler"]],
            "traces": [prof["trace"], tr_fl, drohne["trace"], he["trace"], ma["trace"]]}


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

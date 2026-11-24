"""Tests des Rechenkerns (ohne Oberfläche und ohne Netzwerk)."""
import math

from core import fluege as flm
from core import katalog, kosten, params, profil, geo

REG, _ = params.load_registry()
P = params.defaults(REG)
KAT = katalog.load()


def _prof():
    dist, pts, ds, step = geo.sample_route((47.0937, 9.9831), (47.1000, 9.9833), P["profil.raster_m"])
    t = profil.linear_terrain(ds, 886, 1167)
    return profil.build_profile((47.0937, 9.9831), (47.1000, 9.9833), dist, pts, ds, step, t, "test", False, "", P)


def _flug(modus="hoch", hoch=(), runter=(), beh="grund", tag=1):
    return {"id": "x", "tag": tag, "modus": modus, "hoch": {"behaelter": beh, "positionen": list(hoch)},
            "runter": {"behaelter": beh, "positionen": list(runter)}}


def test_katalog_und_vorlagen():
    assert len(KAT) == 31
    vl = katalog.load_vorlagen()
    assert [v["id"] for v in vl] == ["S1", "S2", "S3", "S4", "S5"]
    s1 = sum(KAT[x["artikel"]]["gewicht_kg"] * x["menge"] for x in vl[0]["positionen"])
    assert math.isclose(s1, 40.14, abs_tol=0.01)  # Summe Ladung S1 laut Tabelle
    assert KAT["akku_ap_300_0_pc"]["gefahrgut"] == "9L"
    assert KAT["akku_ap_300_im_geraet"]["gefahrgut"] == "9G"
    assert KAT["motorsaege_ms_261_c_m"]["gefahrgut"] == "3"


def test_last_am_haken_und_grenze():
    ms = katalog.position(KAT["motorsaege_ms_261_c_m"], 1)
    last = {"behaelter": "grund", "positionen": [ms]}
    assert math.isclose(flm.am_haken(last, P), 5.8 + P["box.grund_kg"])
    schwer = {"behaelter": "grund", "positionen": [katalog.freie_position("Sack", 66)]}
    assert any(s == "fehler" for s, _ in flm.pruefen(schwer, P))  # 66 + 5,04 > 70


def test_gefahrgut_und_langgut_hinweise():
    mix = {"behaelter": "kassette", "positionen": [katalog.position(KAT["motorsaege_ms_261_c_m"], 1),
                                                   katalog.position(KAT["akku_ap_300_0_pc"], 2)]}
    assert any("Kl. 3" in t for _, t in flm.pruefen(mix, P))
    fs = {"behaelter": "grund", "positionen": [katalog.position(KAT["freischneider_fs_461_c_em"], 1)]}
    assert any("Lastnetz" in t for _, t in flm.pruefen(fs, P))
    fs["behaelter"] = "netz"
    assert not any("Lastnetz" in t for _, t in flm.pruefen(fs, P))


def test_leerflug_und_bodenzeit():
    prof = _prof()
    ms = katalog.position(KAT["motorsaege_ms_261_c_m"], 1)
    fl, _ = flm.auswerten([_flug("hoch", hoch=[ms]), _flug("beide", hoch=[ms], runter=[ms])], prof, P)
    a, b = fl
    assert a["richtung"]["runter"]["haken"] == 0 and not a["richtung"]["runter"]["beladen"]
    assert math.isclose(a["boden_min"], P["flug.umlauf_min"] + P["flug.lastwechsel_min"])
    assert math.isclose(b["boden_min"], P["flug.umlauf_min"] + 2 * P["flug.lastwechsel_min"])
    assert math.isclose(a["richtung"]["runter"]["kwh"], P["drohne.energie_leer_kwh"])
    assert b["kwh"] > a["kwh"]


def test_packen_vorlagen():
    for v in katalog.load_vorlagen():
        pos = [katalog.position(KAT[x["artikel"]], x["menge"]) for x in v["positionen"]]
        lasten = flm.packen(pos, P)
        assert math.isclose(sum(flm.ladung(x) for x in lasten), sum(flm.ladung({"positionen": pos}) for _ in [0]))
        for last in lasten:
            assert flm.am_haken(last, P) <= P["drohne.nutzlast_kg"] + 1e-9
            ggs = {x["gg"] for x in last["positionen"]}
            assert not ("3" in ggs and "9L" in ggs)
            assert not any(s == "fehler" for s, _ in flm.pruefen(last, P))


def test_kosten_eigenbetrieb():
    prof = _prof()
    ms = katalog.position(KAT["motorsaege_ms_261_c_m"], 1)
    fl, _ = flm.auswerten([_flug("hoch", hoch=[ms]), _flug("runter", runter=[ms], tag=2)], prof, P)
    d = kosten.eigenbetrieb(fl, P)
    assert d["tage"] == 2 and d["fluege"] == 2
    assert math.isclose(d["Kosten (€)"], d["fix"] + d["variabel"])
    fix_tag = P["betrieb.abschreibung_eur_tag"] + P["betrieb.versicherung_eur_tag"] + P["betrieb.sonstiges_eur"]
    ruest = (P["einsatz.aufbau_min"] + P["einsatz.abbau_min"]) / 60 * kosten.crew_satz(P)
    assert math.isclose(d["fix"], 2 * (fix_tag + ruest))


def test_heli_je_einsatz():
    h = kosten.heli([{"name": "a", "kg": 100}, {"name": "b", "kg": 0}], P, {"name": "x", "km": 30})
    assert h["einsaetze"] == 1
    assert math.isclose(h["Kosten (€)"], max(60 / P["heli.v_kmh"] * 60 + P["heli.rotation_min"], P["heli.mindest_min"])
                        * P["heli.eur_min"] + P["heli.bereitstellung_eur"])

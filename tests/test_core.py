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


def test_kosten_eigenbetrieb_folie14():
    from core import akku
    # Folie 14: 59.343 € Investition, 16.244 € Fix mit Abschreibung, 0,79 €/min variabel
    assert math.isclose(kosten.investition(P), 59343)
    ohne, mit = kosten.satz_je_min(P, 107)
    assert math.isclose(mit, 0.79 + 16243.6 / (107 * 60), rel_tol=1e-6)
    assert abs(mit - 3.33) < 0.02  # Zielkosten Heli laut Folie bei 107 h
    prof = _prof()
    ms = katalog.position(KAT["motorsaege_ms_261_c_m"], 1)
    fl, _ = flm.auswerten([_flug("hoch", hoch=[ms]), _flug("runter", runter=[ms], tag=2)], prof, P)
    ak = akku.plan(fl, P)
    k = kosten.eigenbetrieb(fl, ak, P)
    luft = sum(f["flug_min"] for f in fl)
    assert math.isclose(k["ohne"], luft * kosten.satz_je_min(P)[0])
    assert math.isclose(k["mit"], luft * kosten.satz_je_min(P)[1])
    assert k["personal"] == 0  # standardmäßig ohne Personal


def test_akkuwechsel():
    from core import akku
    prof = _prof()
    ms = katalog.position(KAT["motorsaege_ms_261_c_m"], 1)
    fl, _ = flm.auswerten([_flug("hoch", hoch=[ms]) for _ in range(6)], prof, P)
    nutz = P["akku.flugzeit_min"] * (1 - P["akku.reserve_pct"] / 100)
    je_satz = int(nutz // fl[0]["flug_min"])
    ak = akku.plan(fl, P)
    assert ak["wechsel"] == math.ceil(6 / je_satz) - 1
    assert ak["je_flug"][je_satz]["wechsel_danach"]
    p2 = dict(P, **{"akku.saetze": 1, "akku.ladezeit_min": 60})
    assert akku.plan(fl, p2)["warte_min"] > 0  # ein Satz: Warten aufs Laden


def test_packen_nur_verfuegbare_behaelter():
    pos = [katalog.position(KAT["freischneider_fs_461_c_em"], 1), katalog.position(KAT["akku_ap_300_0_pc"], 3)]
    ohne_netz = flm.packen(pos, P, ["grund"])
    assert all(x["behaelter"] == "grund" for x in ohne_netz)
    mit = flm.packen(pos, P, ["grund", "kassette", "netz"])
    behs = {x["behaelter"] for x in mit}
    assert "netz" in behs and "kassette" in behs

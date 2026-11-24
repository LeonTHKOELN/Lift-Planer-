"""Flugplan: Last je Flugrichtung, Prüfungen und Flugzeit.

Ein Flug ist ein Umlauf Landeplatz → Einsatzort → Landeplatz.
  hoch    Hinflug beladen, Rückflug leer
  runter  Hinflug leer, Rückflug beladen
  beide   beide Richtungen beladen
Last am Haken = Ladung + Eigengewicht des Behälters. Grenze: drohne.nutzlast_kg.
"""
import math

from .fmt import de
from .trace import Trace

MODI = {"hoch": "Hin beladen · Rück leer", "runter": "Hin leer · Rück beladen", "beide": "Hin und Rück beladen"}
RICHTUNGEN = {"hoch": "Hinflug (hoch)", "runter": "Rückflug (runter)"}
BEHAELTER = {"grund": ("Grundbox", "box.grund_kg"), "kassette": ("Grundbox mit Akku-Kassette", "box.kassette_kg"),
             "ring": ("Grundbox mit 3. Aufsatzring", "box.ring_kg"), "netz": ("Lastnetz (Langgut)", "box.netz_kg"),
             "ohne": ("ohne Behälter", None)}


def richtungen(modus):
    return {"hoch": ["hoch"], "runter": ["runter"], "beide": ["hoch", "runter"]}[modus]


def tara(behaelter, p):
    key = BEHAELTER[behaelter][1]
    return float(p[key]) if key else 0.0


def ladung(last):
    return sum(x["kg"] * x["menge"] for x in last["positionen"])


def am_haken(last, p):
    lad = ladung(last)
    return lad + (tara(last["behaelter"], p) if last["positionen"] else 0.0)


def pruefen(last, p):
    """Hinweise zu einer Flugrichtung: [(stufe, text)], stufe = "fehler" | "warnung"."""
    out = []
    pos = last["positionen"]
    if not pos:
        return out
    haken, cap = am_haken(last, p), p["drohne.nutzlast_kg"]
    if haken > cap + 1e-9:
        out.append(("fehler", f"{de(haken, 1)} kg am Haken, {de(haken - cap, 1)} kg über der Grenze von {de(cap)} kg"))
    ggs = {x["gg"] for x in pos}
    if "3" in ggs and "9L" in ggs:
        out.append(("warnung", "Kraftstoff (Kl. 3) und lose Akkus (Kl. 9) im selben Flug. "
                               "Laut Tabelle getrennt transportieren"))
    if last["behaelter"] != "netz":
        lang = [x["name"] for x in pos if x["laenge_mm"] and x["laenge_mm"] > p["box.innenlaenge_mm"]]
        if lang:
            out.append(("warnung", f"Passt nicht in die Box (länger als {de(p['box.innenlaenge_mm'])} mm): "
                                   + ", ".join(lang) + ". Lastnetz wählen"))
    if "9L" in ggs and last["behaelter"] not in ("kassette", "netz", "ohne"):
        out.append(("warnung", "Lose Akkus an Bord: Grundbox mit Akku-Kassette vorgesehen"))
    return out


def energie_kwh(haken, p):
    """Energie je Flugrichtung, linear zwischen leer und maximaler Last."""
    anteil = min(max(haken / p["drohne.nutzlast_kg"], 0.0), 1.0) if p["drohne.nutzlast_kg"] else 0.0
    return p["drohne.energie_leer_kwh"] + (p["drohne.energie_voll_kwh"] - p["drohne.energie_leer_kwh"]) * anteil


def auswerten(fluege, prof, p):
    """Je Flug: Last je Richtung, Flugzeit, Energie und Prüfungen. Dazu ein Rechenweg."""
    tr = Trace("fluege", "Flugplan",
               "Je Flug: Flugzeit aus dem Flugprofil plus Bodenzeiten, Energie je Richtung nach Last am Haken.")
    tr.add("Flugzeit hin + zurück", "t_hin + t_rück aus dem Flugprofil",
           f"{de(prof['out_min'], 1)} + {de(prof['back_min'], 1)} min", prof["out_min"] + prof["back_min"], "min", 1)
    tr.add("Bodenzeit je Flug", "t_Umlauf + beladene Richtungen × t_An-/Abhängen",
           f"{de(p['flug.umlauf_min'], 1)} + n × {de(p['flug.lastwechsel_min'], 1)} min", 0,
           text="je nach Flug", kommentar="Leer: nur Umlauf. Eine Richtung beladen: + 1 ×. Beide: + 2 ×")
    tr.add("Energie je Richtung", "E = E_leer + (E_voll − E_leer) × Last am Haken / max. Last",
           f"{de(p['drohne.energie_leer_kwh'], 1)} + ({de(p['drohne.energie_voll_kwh'], 1)} − "
           f"{de(p['drohne.energie_leer_kwh'], 1)}) × m / {de(p['drohne.nutzlast_kg'])} kg", 0, text="je nach Last")
    out = []
    for i, f in enumerate(fluege, 1):
        aktiv = richtungen(f["modus"])
        r = {"nr": i, "id": f["id"], "tag": f["tag"], "modus": f["modus"], "richtung": {}}
        for d in ("hoch", "runter"):
            last = f[d]
            beladen = d in aktiv and bool(last["positionen"])
            haken = am_haken(last, p) if beladen else 0.0
            r["richtung"][d] = {"aktiv": d in aktiv, "beladen": beladen, "ladung": ladung(last) if beladen else 0.0,
                                "haken": haken, "tara": tara(last["behaelter"], p) if beladen else 0.0,
                                "kwh": energie_kwh(haken, p), "hinweise": pruefen(last, p) if d in aktiv else []}
        n_bel = sum(1 for d in r["richtung"].values() if d["beladen"])
        r["beladen_n"] = n_bel
        r["flug_min"] = prof["out_min"] + prof["back_min"]
        r["boden_min"] = p["flug.umlauf_min"] + n_bel * p["flug.lastwechsel_min"]
        r["min"] = r["flug_min"] + r["boden_min"]
        r["kwh"] = r["richtung"]["hoch"]["kwh"] + r["richtung"]["runter"]["kwh"]
        r["fehler"] = any(s == "fehler" for d in r["richtung"].values() for s, _ in d["hinweise"])
        r["gefahrgut"] = any(x["gg"] for d in aktiv for x in f[d]["positionen"])
        tr.add(f"Flug {i} (Tag {f['tag']})", "t_Flug + t_Boden · E_hin + E_rück",
               f"{de(r['flug_min'], 1)} + {de(r['boden_min'], 1)} min · "
               f"{de(r['richtung']['hoch']['kwh'], 2)} + {de(r['richtung']['runter']['kwh'], 2)} kWh",
               r["min"], "min", 1,
               kommentar=f"hoch {de(r['richtung']['hoch']['haken'], 1)} kg · runter "
                         f"{de(r['richtung']['runter']['haken'], 1)} kg am Haken")
        out.append(r)
    return out, tr


# ---------------------------------------------------------------------------
# Vorlage → Flüge (First Fit Decreasing, Gefahrgut getrennt)
# ---------------------------------------------------------------------------
def _bloecke(positionen, cap):
    """Positionen in Ladeblöcke: Stückgut über 3 kg einzeln, sonst als Ganzes; Blöcke über cap werden geteilt."""
    out = []
    for x in positionen:
        gesamt = x["kg"] * x["menge"]
        if x["einheit"] == "Stk" and x["menge"] > 1 and (x["kg"] > 3 or gesamt > cap):
            out += [dict(x, menge=1) for _ in range(int(x["menge"]))]
        elif gesamt > cap and x["kg"] > 0:
            n = math.ceil(gesamt / cap)
            out += [dict(x, menge=x["menge"] / n) for _ in range(n)]
        else:
            out.append(dict(x))
    return out


def packen(positionen, p):
    """Teilt eine Tagesladung auf Flüge auf. Ergebnis: [{behaelter, positionen}]."""
    cap = p["drohne.nutzlast_kg"]
    bins = []  # {behaelter, positionen, klasse}
    for b in sorted(_bloecke(positionen, cap - p["box.kassette_kg"]), key=lambda x: -x["kg"] * x["menge"]):
        lang = bool(b["laenge_mm"] and b["laenge_mm"] > p["box.innenlaenge_mm"])
        kl = "3" if b["gg"] == "3" else ("9L" if b["gg"] == "9L" else "")
        ziel = None
        for bn in bins:
            if kl and bn["klasse"] and kl != bn["klasse"]:
                continue
            beh = "netz" if (lang or bn["behaelter"] == "netz") else (
                "kassette" if "9L" in (kl, bn["klasse"]) else bn["behaelter"])
            if ladung(bn) + b["kg"] * b["menge"] + tara(beh, p) <= cap + 1e-9:
                ziel, bn["behaelter"] = bn, beh
                break
        if ziel is None:
            ziel = {"behaelter": "netz" if lang else ("kassette" if kl == "9L" else "grund"), "positionen": [],
                    "klasse": ""}
            bins.append(ziel)
        ziel["klasse"] = ziel["klasse"] or kl
        same = next((y for y in ziel["positionen"] if y["name"] == b["name"] and y["kg"] == b["kg"]), None)
        if same:
            same["menge"] += b["menge"]
        else:
            ziel["positionen"].append(b)
    for bn in bins:
        for y in bn["positionen"]:
            y["menge"] = round(y["menge"], 3)
    return [{"behaelter": bn["behaelter"], "positionen": bn["positionen"]} for bn in bins]

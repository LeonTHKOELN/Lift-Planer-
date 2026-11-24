"""Akkuplan: wann ein Akkuwechsel nötig ist und ob das Laden der Akkusätze mithält.

Ablauf je Einsatztag (Flüge in Reihenfolge des Flugplans, alle Sätze morgens voll):
  nutzbare Flugzeit je Satz = Flugzeit × (1 − Reserve)
  reicht die Restzeit des eingesetzten Satzes nicht für den nächsten Flug → Akkuwechsel davor.
  Der leere Satz geht ans Ladegerät und ist nach der Ladezeit wieder bereit.
  Ist beim Wechsel kein Satz bereit, wartet die Crew, bis der nächste geladen ist.
"""
import string

from .fmt import de
from .trace import Trace


def plan(fl, p):
    nutz = p["akku.flugzeit_min"] * (1 - p["akku.reserve_pct"] / 100)
    n = max(int(p["akku.saetze"]), 1)
    tr = Trace("akku", "Akkuplan",
               "Flüge in Reihenfolge, je Einsatztag starten alle Akkusätze voll. Gerechnet wird nur die Zeit in der "
               "Luft. Ein leerer Satz wird sofort geladen.")
    tr.add("Nutzbare Flugzeit je Satz", "Flugzeit × (1 − Reserve)",
           f"{de(p['akku.flugzeit_min'], 1)} min × (1 − {de(p['akku.reserve_pct'])} %)", nutz, "min", 1)
    je_flug, ereignisse = {}, []
    wechsel = warte = ladungen = 0
    warte_min = 0.0
    zu_lang = []
    for tag in sorted({f["tag"] for f in fl}):
        bereit = [0.0] * n
        t, satz, rest = 0.0, 0, nutz
        for f in [x for x in fl if x["tag"] == tag]:
            if f["flug_min"] > nutz + 1e-9:
                zu_lang.append(f["nr"])
            if f["flug_min"] > rest + 1e-9:
                bereit[satz] = t + p["akku.ladezeit_min"]
                ladungen += 1
                frei = [i for i in range(n) if i != satz] or [satz]
                neu = min(frei, key=lambda i: bereit[i])
                w = max(0.0, bereit[neu] - t)
                ereignisse.append({"Tag": tag, "vor Flug": f["nr"], "Satz": f"{string.ascii_uppercase[satz]} → "
                                   f"{string.ascii_uppercase[neu]}", "Rest vorher (min)": rest,
                                   "Wartezeit Laden (min)": w})
                wechsel += 1
                if w > 0:
                    warte += 1
                    warte_min += w
                t += w + p["akku.wechsel_min"]
                satz, rest = neu, nutz
            rest -= f["flug_min"]
            t += f["min"]
            je_flug[f["nr"]] = {"satz": string.ascii_uppercase[satz], "rest_min": max(rest, 0.0),
                                "rest_pct": max(rest, 0.0) / p["akku.flugzeit_min"] * 100 + p["akku.reserve_pct"],
                                "wechsel_danach": False}
        ladungen += 1  # eingesetzter Satz am Abend
    nrs = [f["nr"] for f in fl]
    for e in ereignisse:
        i = nrs.index(e["vor Flug"])
        if i > 0:
            je_flug[nrs[i - 1]]["wechsel_danach"] = True
    tr.add("Akkuwechsel", "Anzahl Wechsel über alle Einsatztage", f"{len(fl)} Flüge · {n} Sätze", wechsel, "", 0)
    tr.add("Wartezeit auf geladene Akkus", "Σ max(0, bereit − jetzt) beim Wechsel",
           f"Ladezeit {de(p['akku.ladezeit_min'])} min je Satz", warte_min, "min", 0,
           kommentar="Größer als 0: mehr Akkusätze oder schnellere Ladung einplanen")
    return {"nutz_min": nutz, "wechsel": wechsel, "warte_n": warte, "warte_min": warte_min, "ladungen": ladungen,
            "ereignisse": ereignisse, "je_flug": je_flug, "zu_lang": zu_lang,
            "wechsel_min": wechsel * p["akku.wechsel_min"], "trace": tr}

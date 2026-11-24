"""Kosten im Eigenbetrieb nach der Kalkulation FlyCart 100 (Projekt-Review 6, Folie 14).

Grundlage ist die Flugminute (Zeit in der Luft):
  variabel        = Flugminuten × (Akkuverschleiß + Laden + Wartung)
  fix anteilig    = Flugminuten × Fixkosten pro Jahr / (Flugstunden pro Jahr × 60)
                    ohne Abschreibung: Fixkosten pro Jahr
                    mit Abschreibung:  Fixkosten pro Jahr + Investition / Nutzungsdauer
  Personal        optional (Kalkulation ohne Personal): Einsatzzeit × Crew
"""
from .fmt import de
from .trace import Trace


def crew_satz(p):
    return p["personal.pilot_eur_h"] + p["personal.helfer_n"] * p["personal.helfer_eur_h"]


def investition(p):
    return p["kalk.invest_equipment_eur"] + p["kalk.invest_genehmigung_eur"] + p["kalk.invest_ausbildung_eur"]


def satz_je_min(p, auslastung_h=None):
    """Kosten je Flugminute ohne und mit Abschreibung bei gegebener Auslastung."""
    h = auslastung_h if auslastung_h is not None else p["kalk.auslastung_h"]
    var = p["kalk.akku_eur_min"] + p["kalk.laden_eur_min"] + p["kalk.wartung_eur_min"]
    abschr = investition(p) / p["kalk.nutzungsdauer_j"]
    return var + p["kalk.fix_jahr_eur"] / (h * 60), var + (p["kalk.fix_jahr_eur"] + abschr) / (h * 60)


def eigenbetrieb(fl, akku, p):
    tr = Trace("kosten", "Kosten im Eigenbetrieb",
               "Kalkulation FlyCart 100 je Flugminute. Fixkosten pro Jahr werden über die Flugminuten des Jahres "
               "verteilt, einmal ohne und einmal mit Abschreibung der Investition.")
    inv = tr.add("Investition", "Equipment + Genehmigung/SORA + Ausbildung",
                 f"{de(p['kalk.invest_equipment_eur'])} + {de(p['kalk.invest_genehmigung_eur'])} + "
                 f"{de(p['kalk.invest_ausbildung_eur'])} €", investition(p), "€", 0)
    abschr = tr.add("Abschreibung pro Jahr", "Investition / Nutzungsdauer (linear)",
                    f"{de(inv)} € / {p['kalk.nutzungsdauer_j']} Jahre", inv / p["kalk.nutzungsdauer_j"], "€/Jahr", 0)
    min_jahr = tr.add("Flugminuten pro Jahr", "Flugstunden pro Jahr × 60", f"{de(p['kalk.auslastung_h'])} h × 60",
                      p["kalk.auslastung_h"] * 60, "min", 0)
    var = tr.add("Variable Kosten je Flugminute", "Akkuverschleiß + Laden + Wartung",
                 f"{de(p['kalk.akku_eur_min'], 2)} + {de(p['kalk.laden_eur_min'], 2)} + "
                 f"{de(p['kalk.wartung_eur_min'], 2)} €", p["kalk.akku_eur_min"] + p["kalk.laden_eur_min"]
                 + p["kalk.wartung_eur_min"], "€/min", 2)
    fo = tr.add("Fixkosten je Flugminute ohne Abschreibung", "Fixkosten pro Jahr / Flugminuten pro Jahr",
                f"{de(p['kalk.fix_jahr_eur'])} € / {de(min_jahr)} min", p["kalk.fix_jahr_eur"] / min_jahr, "€/min", 2)
    fm = tr.add("Fixkosten je Flugminute mit Abschreibung", "(Fixkosten + Abschreibung) / Flugminuten pro Jahr",
                f"({de(p['kalk.fix_jahr_eur'])} + {de(abschr)}) € / {de(min_jahr)} min",
                (p["kalk.fix_jahr_eur"] + abschr) / min_jahr, "€/min", 2)
    leer = {"fluege": 0, "luft_min": 0.0, "ohne": 0.0, "mit": 0.0, "var": 0.0, "fix_ohne": 0.0, "fix_mit": 0.0,
            "personal": 0.0, "einsatz_min": 0.0, "je_flug": [], "satz_ohne": var + fo, "satz_mit": var + fm,
            "investition": inv, "abschreibung": abschr, "tage": 0, "trace": tr}
    if not fl:
        tr.add("Kosten", "keine Flüge geplant", "", 0, "€", 0)
        return leer
    luft = tr.add("Flugminuten dieses Einsatzes", "Σ Flugzeit aller Flüge (ohne Bodenzeit)",
                  f"{len(fl)} Flüge", sum(f["flug_min"] for f in fl), "min", 1)
    v = tr.add("Variable Kosten", "Flugminuten × variable Kosten je Minute", f"{de(luft, 1)} min × {de(var, 2)} €",
               luft * var, "€", 0)
    k_o = tr.add("Fixkosten anteilig ohne Abschreibung", "Flugminuten × Fix je Minute",
                 f"{de(luft, 1)} min × {de(fo, 2)} €", luft * fo, "€", 0)
    k_m = tr.add("Fixkosten anteilig mit Abschreibung", "Flugminuten × Fix je Minute",
                 f"{de(luft, 1)} min × {de(fm, 2)} €", luft * fm, "€", 0)
    tage = len({f["tag"] for f in fl})
    ruest = (p["einsatz.aufbau_min"] + p["einsatz.abbau_min"]) * tage
    einsatz_min = tr.add("Einsatzzeit vor Ort", "Σ Flüge inkl. Bodenzeit + Akkuwechsel + Warten auf Laden + "
                                                 "Tage × (Aufbau + Abbau)",
                         f"{de(sum(f['min'] for f in fl), 1)} + {de(akku['wechsel_min'], 1)} + "
                         f"{de(akku['warte_min'], 1)} + {de(ruest)} min",
                         sum(f["min"] for f in fl) + akku["wechsel_min"] + akku["warte_min"] + ruest, "min", 0)
    pers = 0.0
    if p["personal.einrechnen"]:
        pers = tr.add("Personal", "Einsatzzeit × (Pilot + Helfer × Satz)",
                      f"{de(einsatz_min / 60, 2)} h × {de(crew_satz(p))} €/h", einsatz_min / 60 * crew_satz(p), "€", 0)
    else:
        tr.add("Personal", "nicht eingerechnet (wie Kalkulation Folie 14)", "", 0, "€", 0)
    ohne = tr.add("Kosten ohne Abschreibung", "variabel + Fix ohne Abschreibung + Personal",
                  f"{de(v)} + {de(k_o)} + {de(pers)} €", v + k_o + pers, "€", 0)
    mit = tr.add("Kosten mit Abschreibung", "variabel + Fix mit Abschreibung + Personal",
                 f"{de(v)} + {de(k_m)} + {de(pers)} €", v + k_m + pers, "€", 0)
    je_flug = [{"Flug": f["nr"], "Tag": f["tag"], "Flugminuten": f["flug_min"],
                "kg": f["richtung"]["hoch"]["ladung"] + f["richtung"]["runter"]["ladung"],
                "variabel (€)": f["flug_min"] * var, "ohne Abschreibung (€)": f["flug_min"] * (var + fo),
                "mit Abschreibung (€)": f["flug_min"] * (var + fm)} for f in fl]
    return {**leer, "fluege": len(fl), "luft_min": luft, "ohne": ohne, "mit": mit, "var": v, "fix_ohne": k_o,
            "fix_mit": k_m, "personal": pers, "einsatz_min": einsatz_min, "je_flug": je_flug, "tage": tage}

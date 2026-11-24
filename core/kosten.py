"""Kosten, Zeit und CO₂ im Eigenbetrieb und für die Vergleichsverfahren.

Drohne (Eigenbetrieb)
  je Flug:        Flugzeit × (Personal + Wartung + Akkualterung) + Energie × Strompreis
  je Einsatztag:  Abschreibung + Versicherung + (Aufbau + Abbau + Wartezeit) × Personal + Sonstiges
Helikopter:  je Einsatztag und Richtung mit Last ein Einsatz: (Anflug + Rotationen) × €/min, mindestens
             Mindestabrechnung, + Bereitstellung
Tragen:      je Richtung Gänge × Gehzeit (DIN 33466, Lastaufschlag) × Team × Stundensatz
"""
import math

from .fmt import de
from .trace import Trace


def crew_satz(p):
    return p["personal.pilot_eur_h"] + p["personal.helfer_n"] * p["personal.helfer_eur_h"]


def eigenbetrieb(fl, p):
    """fl: Ergebnis von fluege.auswerten. Liefert Positionen je Flug und je Einsatztag."""
    tr = Trace("drohne", "Drohne · Eigenbetrieb",
               "Variable Kosten je Flug aus Flugzeit und Energie, fixe Kosten je Einsatztag.")
    crew = tr.add("Personalsatz Crew", "Pilot + Helfer × Satz Helfer",
                  f"{de(p['personal.pilot_eur_h'])} + {int(p['personal.helfer_n'])} × {de(p['personal.helfer_eur_h'])} €/h",
                  crew_satz(p), "€/h", 0)
    var_h = tr.add("Variabler Satz je Flugstunde", "Crew + Wartung + Akkualterung",
                   f"{de(crew)} + {de(p['betrieb.wartung_eur_fh'])} + {de(p['betrieb.akku_eur_fh'])} €/h",
                   crew + p["betrieb.wartung_eur_fh"] + p["betrieb.akku_eur_fh"], "€/h", 0)
    leer = {"Kosten (€)": 0.0, "Zeit (min)": 0.0, "CO₂ (kg)": 0.0, "fluege": 0, "tage": 0, "je_flug": [],
            "je_tag": [], "positionen": [], "fix": 0.0, "variabel": 0.0, "kwh": 0.0, "trace": tr}
    if not fl:
        tr.add("Kosten", "keine Flüge geplant", "", 0, "€", 0)
        return leer
    je_flug = []
    for f in fl:
        h = f["min"] / 60
        personal = h * crew
        technik = h * (p["betrieb.wartung_eur_fh"] + p["betrieb.akku_eur_fh"])
        strom = f["kwh"] * p["betrieb.strom_eur_kwh"]
        je_flug.append({"Flug": f["nr"], "Tag": f["tag"], "Minuten": f["min"], "kWh": f["kwh"],
                        "Personal": personal, "Wartung und Akku": technik, "Strom": strom,
                        "Summe": personal + technik + strom,
                        "kg": f["richtung"]["hoch"]["ladung"] + f["richtung"]["runter"]["ladung"]})
    beispiel = je_flug[0]
    tr.add("Kosten Flug 1 (Beispiel)", "t × variabler Satz + kWh × Strompreis",
           f"{de(beispiel['Minuten'] / 60, 3)} h × {de(var_h)} €/h + {de(beispiel['kWh'], 2)} kWh × "
           f"{de(p['betrieb.strom_eur_kwh'], 2)} €/kWh", beispiel["Summe"], "€", 2,
           kommentar="Alle Flüge einzeln auf der Seite Kosten")
    tage = sorted({f["tag"] for f in fl})
    ruest_h = (p["einsatz.aufbau_min"] + p["einsatz.abbau_min"]) / 60
    fix_tag = p["betrieb.abschreibung_eur_tag"] + p["betrieb.versicherung_eur_tag"] + p["betrieb.sonstiges_eur"]
    vor_ort_tag = tr.add("Personal vor Ort je Einsatztag", "(Aufbau + Abbau + Wartezeit) × Crew",
                         f"({de(ruest_h, 2)} + {de(p['personal.warte_h'], 1)}) h × {de(crew)} €/h",
                         (ruest_h + p["personal.warte_h"]) * crew, "€", 0)
    tr.add("Drohne fix je Einsatztag", "Abschreibung + Versicherung + Sonstiges",
           f"{de(p['betrieb.abschreibung_eur_tag'])} + {de(p['betrieb.versicherung_eur_tag'])} + "
           f"{de(p['betrieb.sonstiges_eur'])} €", fix_tag, "€", 0)
    je_tag = []
    for t in tage:
        fs = [x for x in je_flug if x["Tag"] == t]
        je_tag.append({"Tag": t, "Flüge": len(fs), "Flugzeit (min)": sum(x["Minuten"] for x in fs),
                       "Flüge (€)": sum(x["Summe"] for x in fs), "Vor Ort (€)": vor_ort_tag, "Drohne fix (€)": fix_tag,
                       "Summe (€)": sum(x["Summe"] for x in fs) + vor_ort_tag + fix_tag})
    n = len(tage)
    pos = [("Personal im Flug", "variabel", sum(x["Personal"] for x in je_flug), f"Flugzeit × {de(crew)} €/h"),
           ("Wartung und Akkualterung", "variabel", sum(x["Wartung und Akku"] for x in je_flug),
            f"Flugzeit × {de(p['betrieb.wartung_eur_fh'] + p['betrieb.akku_eur_fh'])} €/h"),
           ("Strom", "variabel", sum(x["Strom"] for x in je_flug),
            f"{de(sum(x['kWh'] for x in je_flug), 1)} kWh × {de(p['betrieb.strom_eur_kwh'], 2)} €/kWh"),
           ("Aufbau, Abbau, Wartezeit", "fix", n * vor_ort_tag, f"{n} Tag(e) × {de(vor_ort_tag)} €"),
           ("Abschreibung, Versicherung, Sonstiges", "fix", n * fix_tag, f"{n} Tag(e) × {de(fix_tag)} €")]
    positionen = [{"Position": a, "Art": b, "Betrag": c, "Eingesetzt": d} for a, b, c, d in pos if c]
    total = sum(x["Betrag"] for x in positionen)
    tr.add("Kosten gesamt", "Σ Flüge + Einsatztage × (Personal vor Ort + Drohne fix)",
           f"{de(sum(x['Summe'] for x in je_flug))} € + {n} × ({de(vor_ort_tag)} + {de(fix_tag)}) €", total, "€", 0)
    zeit = sum(f["min"] for f in fl) + n * ruest_h * 60
    tr.add("Zeit vor Ort", "Σ Flugzeiten + Einsatztage × (Aufbau + Abbau)", "", zeit, "min", 0,
           kommentar="Ohne Wartezeit")
    kwh = sum(f["kwh"] for f in fl)
    co2 = tr.add("CO₂", "Σ kWh × Strommix", f"{de(kwh, 1)} kWh × {de(p['co2.strom_kg_kwh'], 2)} kg/kWh",
                 kwh * p["co2.strom_kg_kwh"], "kg", 1)
    return {**leer, "Kosten (€)": total, "Zeit (min)": zeit, "CO₂ (kg)": co2, "fluege": len(fl), "tage": n,
            "je_flug": je_flug, "je_tag": je_tag, "positionen": positionen, "kwh": kwh,
            "fix": sum(x["Betrag"] for x in positionen if x["Art"] == "fix"),
            "variabel": sum(x["Betrag"] for x in positionen if x["Art"] == "variabel")}


def heli(einsaetze, p, basis):
    """einsaetze: [{name, kg}] je Einsatztag und Richtung. basis: {name, km}."""
    tr = Trace("heli", "Helikopter",
               "Je Einsatztag und Richtung mit Last ein Einsatz. Abrechnung nach Flugminuten, Anflug aus der "
               f"Luftlinie zur Basis ({basis['name']}).")
    out = {"Zeit (min)": 0.0, "Kosten (€)": 0.0, "CO₂ (kg)": 0.0, "einsaetze": 0, "rotationen": 0, "trace": tr}
    einsaetze = [e for e in einsaetze if e["kg"] > 0]
    if not einsaetze:
        tr.add("Kosten", "keine Fracht", "", 0, "€", 0)
        return out
    anflug = tr.add("Anflug je Einsatz", "2 × Luftlinie Basis ↔ Landeplatz / Transfergeschwindigkeit",
                    f"2 × {de(basis['km'], 1)} km / {de(p['heli.v_kmh'])} km/h", 2 * basis["km"] / p["heli.v_kmh"] * 60,
                    "min", 1)
    kosten = zeit = co2 = 0.0
    rot_ges = 0
    for e in einsaetze:
        rot = math.ceil(e["kg"] / p["heli.nutzlast_kg"])
        minuten = anflug + rot * p["heli.rotation_min"]
        abger = max(minuten, p["heli.mindest_min"])
        je = tr.add(e["name"], "max(Anflug + Rotationen × Dauer, Mindestabrechnung) × €/min + Bereitstellung",
                    f"max({de(anflug, 1)} + {rot} × {de(p['heli.rotation_min'])}, {de(p['heli.mindest_min'])}) min × "
                    f"{de(p['heli.eur_min'])} €/min + {de(p['heli.bereitstellung_eur'])} €",
                    abger * p["heli.eur_min"] + p["heli.bereitstellung_eur"], "€", 0, kommentar=f"{de(e['kg'], 1)} kg")
        kosten += je
        zeit += rot * p["heli.rotation_min"]
        co2 += minuten / 60 * p["heli.kerosin_l_h"] * p["co2.kerosin_kg_l"]
        rot_ges += rot
    tr.add("Kosten gesamt", "Σ Einsätze", f"{len(einsaetze)} Einsätze", kosten, "€", 0)
    tr.add("CO₂", "Σ Flugstunden × Verbrauch × Emissionsfaktor",
           f"{de(p['heli.kerosin_l_h'])} l/h × {de(p['co2.kerosin_kg_l'], 2)} kg/l", co2, "kg", 1)
    return {**out, "Zeit (min)": zeit, "Kosten (€)": kosten, "CO₂ (kg)": co2, "einsaetze": len(einsaetze),
            "rotationen": rot_ges}


# ---------------------------------------------------------------------------
# Tragen
# ---------------------------------------------------------------------------
def _din33466(km, auf, ab, p):
    """Gehzeit nach DIN 33466: max(t_horizontal, t_vertikal) + min(t_horizontal, t_vertikal) / 2."""
    th = km / p["manuell.v_horizontal_kmh"]
    tv = auf / p["manuell.aufstieg_hm_h"] + ab / p["manuell.abstieg_hm_h"]
    return max(th, tv) + min(th, tv) / 2, th, tv


def manuell(prof, p, team, laeufe, titel="Manueller Transport", trace=True):
    """laeufe: [{name, kg, traglast, richtung: "hoch" | "runter", anzahl}]
    Jeder Gang: Weg mit Last (× Lastfaktor) in Transportrichtung, leer zurück."""
    tr = Trace("manuell", titel,
               "Das Team trägt die Fracht ohne Boxen. Gehzeit nach DIN 33466 (Wanderzeitberechnung) mit "
               "Zeitaufschlag für den Weg mit Last. Strecke und Höhenmeter aus dem Geländeprofil.")
    km, auf, ab = prof["dist"] / 1000, prof["asc"], prof["desc"]
    t_hoch, th, tv_h = _din33466(km, auf, ab, p)
    t_runter, _, tv_r = _din33466(km, ab, auf, p)
    tr.add("Gehzeit bergauf", "max(t_h, t_v) + min(t_h, t_v) / 2 · t_h = km / v · t_v = ↑/v_auf + ↓/v_ab",
           f"t_h = {de(km, 2)} km / {de(p['manuell.v_horizontal_kmh'], 1)} km/h = {de(th, 2)} h · "
           f"t_v = {de(auf)}/{de(p['manuell.aufstieg_hm_h'])} + {de(ab)}/{de(p['manuell.abstieg_hm_h'])} = {de(tv_h, 2)} h",
           t_hoch, "h", 2, kommentar="Landeplatz → Einsatzort, ohne Lastaufschlag")
    tr.add("Gehzeit bergab", "wie bergauf, Höhenmeter vertauscht",
           f"t_v = {de(ab)}/{de(p['manuell.aufstieg_hm_h'])} + {de(auf)}/{de(p['manuell.abstieg_hm_h'])} = {de(tv_r, 2)} h",
           t_runter, "h", 2)
    lf = p["manuell.lastfaktor"]
    stunden, gaenge_ges = 0.0, 0
    for lauf in laeufe:
        if lauf["kg"] <= 0 or lauf["anzahl"] <= 0:
            continue
        g = math.ceil(lauf["kg"] / (team * lauf["traglast"]))
        gang = (t_hoch * lf + t_runter) if lauf["richtung"] == "hoch" else (t_runter * lf + t_hoch)
        h = tr.add(lauf["name"], "Anzahl × ⌈kg / (Team × Traglast)⌉ × (Weg mit Last × Lastfaktor + Weg leer)",
                   f"{lauf['anzahl']} × ⌈{de(lauf['kg'], 1)} / ({team} × {de(lauf['traglast'])})⌉ = "
                   f"{lauf['anzahl'] * g} Gänge × {de(gang, 2)} h", lauf["anzahl"] * g * gang, "h", 1)
        stunden += h
        gaenge_ges += lauf["anzahl"] * g
    kosten = tr.add("Kosten", "Zeit × Team × Stundensatz",
                    f"{de(stunden, 2)} h × {team} × {de(p['manuell.stundensatz_eur_h'])} €/h",
                    stunden * team * p["manuell.stundensatz_eur_h"], "€", 0,
                    kommentar="Alle Personen gehen gleichzeitig")
    return {"Zeit (min)": stunden * 60, "Kosten (€)": kosten, "CO₂ (kg)": 0.0, "gaenge": gaenge_ges, "trace": tr}

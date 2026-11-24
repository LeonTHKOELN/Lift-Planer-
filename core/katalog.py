"""Gerätekatalog und Vorlagen aus der Tabelle "Transportszenarien" (Transportbox Sprint 5-6).

Gefahrgut-Kürzel im Katalog:
  "3"   Klasse 3: Kraftstoff, betankte Geräte (UN 1203, UN 3528)
  "9L"  Klasse 9: lose Lithium-Akkus und Powerstation (UN 3480)
  "9G"  Klasse 9: Akku im Gerät eingesetzt (UN 3481)
  ""    kein Gefahrgut
"""
import csv
from pathlib import Path

import yaml

DATA = Path(__file__).resolve().parent.parent / "data"
KATALOG = DATA / "katalog.csv"
VORLAGEN = DATA / "vorlagen.yaml"
KATEGORIEN = ["Geräte", "Akkus und Energie", "Betriebsstoffe", "Werkzeug und Zubehör", "Sicherheit und Verpflegung"]
GG_TEXT = {"3": "Kl. 3", "9L": "Kl. 9 lose", "9G": "Kl. 9 im Gerät", "": ""}


def _num(v):
    return float(v) if str(v).strip() not in ("", "None") else None


def load(path: Path = KATALOG) -> dict:
    out = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["gewicht_kg"] = float(r["gewicht_kg"])
            r["laenge_mm"] = _num(r["laenge_mm"])
            r["energie_wh"] = _num(r["energie_wh"])
            out[r["id"]] = r
    return out


def load_vorlagen(path: Path = VORLAGEN) -> list:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["vorlagen"]


def position(art: dict, menge: float) -> dict:
    """Ladeposition aus einem Katalogartikel."""
    return {"artikel": art["id"], "name": art["name"], "einheit": art["einheit"], "kg": art["gewicht_kg"],
            "menge": menge, "gg": art["gefahrgut"], "laenge_mm": art["laenge_mm"], "wh": art["energie_wh"]}


def freie_position(name: str, kg: float, menge: float = 1, gg: str = "", laenge_mm=None) -> dict:
    return {"artikel": "", "name": name, "einheit": "Stk", "kg": float(kg), "menge": menge, "gg": gg,
            "laenge_mm": laenge_mm, "wh": None}

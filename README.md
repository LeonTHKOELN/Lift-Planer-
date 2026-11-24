# Lift Planner Eigenbetrieb

Streamlit-App (TH Köln × STIHL, Projekt „Arbeiten in Steillagen“): Lastplanung je Flug und Kosten einer
**eigenen** Lastendrohne, verglichen mit Helikopter und Tragen.

## Seiten
1. **Einsatz & Route**: Standardeinsatz wählen (Forstwirtschaft St. Gallenkirch, Lawinenverbauung,
   Heuernte Bartholomäberg) oder Pins auf der Karte setzen. Höhenprofil alle 30 m, Flugzeit, Wetter.
2. **Flugplanung**: Flüge hinzufügen, je Flug „Hin beladen · Rück leer“, „Hin leer · Rück beladen“ oder beides.
   Last aus dem Gerätekatalog oder als freie Position, Grenze 70 kg am Haken (Ladung + Behälter).
   Prüft Lastgrenze, Kraftstoff (Kl. 3) mit losen Akkus (Kl. 9) und Langgut. Vorlagen S1 bis S5 verteilen
   eine Tagesladung automatisch auf Flüge.
3. **Kosten**: je Flug (Flugzeit, Energie) und je Einsatztag (Drohne fix, Aufbau, Abbau), € je kg,
   Vergleich mit Helikopter und Tragen.

Einstellungen: **Annahmen & Parameter** (alle Werte mit Quelle, Rechenweg, Szenarien) und **Gerätekatalog**.

## Daten
- `data/katalog.csv`, `data/vorlagen.yaml`: aus *Transportbox_Sprint5-6_v4.xlsx*, Blatt Transportszenarien
- `data/standorte.csv`: Standardeinsätze
- `data/heli_basen.csv`: Heli-Basis für den Vergleich
- `config/parameter.yaml`, `config/szenarien.yaml`: alle Rechenwerte

## Start
```
pip install -r requirements.txt
streamlit run app.py
pytest -q tests
```

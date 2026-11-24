# Lift Planner Eigenbetrieb

Streamlit-App (TH Köln × STIHL, Projekt „Arbeiten in Steillagen“): Lastplanung je Flug und Kosten einer
**eigenen** Lastendrohne, verglichen mit Helikopter und Tragen.

## Seiten
1. **Einsatz**: Standardeinsatz (Forstwirtschaft St. Gallenkirch, Lawinenverbauung, Heuernte Bartholomäberg)
   oder Pins auf der Karte.
2. **Flugweg**: Höhenprofil alle 30 m, geplante Flughöhe, Flugzeit.
3. **Wetter**: Flug-Ampel der nächsten Tage, stündliche Werte.
4. **Ausrüstung**: alle Artikel wie im Onlineshop nach Kategorien, inkl. Behälter und eigener Positionen
   (z. B. Heusäcke nur runter). Der Warenkorb wird automatisch auf Flüge bis 70 kg am Haken verteilt.
5. **Flugplanung**: erzeugte Flüge prüfen und anpassen, Lastbalken, Gefahrgut- und Langgut-Hinweise,
   Akkusatz und Akkuwechsel je Flug.
6. **Kosten**: Eigenbetrieb nach Kalkulation FlyCart 100 (Projekt-Review 6, Folie 14), ohne und mit
   Abschreibung, je Flugminute nach Auslastung, Akkuwechsel und Laden.

Gerätefotos: `assets/geraete/<id>.jpg` (siehe README dort).

## Daten
- `data/katalog.csv`, `data/vorlagen.yaml`: aus *Transportbox_Sprint5-6_v4.xlsx*, Blatt Transportszenarien
- `data/standorte.csv`: Standardeinsätze
- `config/parameter.yaml`, `config/szenarien.yaml`: alle Rechenwerte

## Start
```
pip install -r requirements.txt
streamlit run app.py
pytest -q tests
```

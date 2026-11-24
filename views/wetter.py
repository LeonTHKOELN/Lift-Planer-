"""Schritt 3 · Wetter: Flug-Ampel der nächsten Tage und stündliche Werte am Einsatzort."""
from core.fmt import de
from ui import state, wetter_view
from ui.components import footer, nav, page_head

PATH = "views/wetter.py"
S = state.S
R = state.result()
P = R["P"]

page_head(PATH, "Wetter", f"Vorhersage für {S.w_einsatz} auf {de(P['ziel_alt'])} m. Wann ist ein Flugtag möglich?")
wetter_view.anzeigen(R)
nav(PATH)
footer()

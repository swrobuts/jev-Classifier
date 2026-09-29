"""Prüft API-Key und Verbindung und listet die verfügbaren Modelle.

    python skripte/00_verbindung_pruefen.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typesafe_sdk import Noul, TypeSafeClient, TypeSafeError  # noqa: E402

from velocity_jev.konfig import MODELL, api_key_vorhanden  # noqa: E402

if not api_key_vorhanden():
    sys.exit("TYPESAFE_API_KEY fehlt. Lege eine .env nach dem Muster von .env.example an.")

try:
    with TypeSafeClient(model=MODELL) as client:
        print("Verfügbare Modelle:")
        for m in client.models.list().models:
            print(f"  {m.name:<16} {m.release_date}  {m.description}")
        antwort = client.system_one(
            {"meldung": {"text": "Die Klingel ist abgebrochen."}},
            {"test": Noul(instructions="Beschreibt `meldung.text` einen Schaden an einem Fahrrad?")},
        )
        print(f"\nTestfrage an {antwort.model}: {antwort.nouls['test'].noul:.3f} "
              f"({antwort.usage.input_tokens} Input-Tokens)")
except TypeSafeError as fehler:
    sys.exit(f"Verbindung fehlgeschlagen: {fehler}")

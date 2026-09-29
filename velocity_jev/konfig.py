"""Gemeinsame Einstellungen der Skripte. Der API-Key kommt nur aus der Umgebung."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

WURZEL = Path(__file__).resolve().parent.parent
load_dotenv(WURZEL / ".env")

MELDUNGEN = WURZEL / "daten" / "meldungen.csv"
HOLDOUT = WURZEL / "daten" / "holdout.csv"  # erst ganz am Ende laufen lassen, siehe docs/iterationen.md
DATENSAETZE = {"meldungen": MELDUNGEN, "holdout": HOLDOUT}
ERGEBNISSE = WURZEL / "ergebnisse"

# Festes Modell statt "jev-latest": Ergebnisse bleiben reproduzierbar, und der
# Cache passt nur zu genau diesem Modell. Die API kennt nur den Namen mit Patch-Version.
MODELL = os.environ.get("JEV_MODELL", "jev-1.13.0")


def api_key_vorhanden() -> bool:
    """Ist ein Key gesetzt? Gibt nur True oder False zurück, nie den Key selbst."""
    return bool(os.environ.get("TYPESAFE_API_KEY", "").strip())

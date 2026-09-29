"""Einen Datensatz von Jev beurteilen lassen und entscheiden – für Skript und Notebook.

Ein Lauf ist: jede Meldung einmal an Jev (oder aus dem Cache), dann die Regeln
aus regeln.py anwenden. Das Ergebnis ist eine Tabelle mit einer Zeile je
Meldung und ein Wörterbuch mit den Daten des Laufs.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone

import pandas as pd
from typesafe_sdk import TypeSafeClient, TypeSafeError

from .fragen import AKTUELLER_STAND
from .pipeline import Cache, KeinCacheTreffer, beurteilen
from .protokoll import fragen_fingerabdruck, neue_lauf_id
from .regeln import REGEL_VERSION, Schwellen, entscheiden


def urteil_als_zeile(u, e) -> dict:
    """Urteil und Entscheidung zu einer flachen Tabellenzeile zusammenfügen."""
    z = asdict(u)
    z.update(entscheidung=e.entscheidung, eskalation=e.eskalation, begruendung=e.begruendung,
             wawi_kategorie=e.wawi_kategorie, wawi_schwere=e.wawi_schwere)
    for spalte in ("kategorie_wkt", "schwere_wkt"):
        z[spalte] = json.dumps(z[spalte], ensure_ascii=False)
    return z


def klassifizieren(meldungen: pd.DataFrame, *, client: TypeSafeClient | None, modell: str,
                   stand: int = AKTUELLER_STAND, schwellen: Schwellen = Schwellen(),
                   datensatz: str = "meldungen", anmerkung: str | None = None,
                   ausgabe: bool = True) -> tuple[pd.DataFrame, dict]:
    """Alle Meldungen beurteilen. Ohne Client wird nur der Cache gelesen."""
    cache = Cache()
    zeilen, fehlend = [], []
    neu = tokens_in = tokens_out = 0
    for m in meldungen.itertuples(index=False):
        try:
            u = beurteilen(m.meldung_id, m.text, m.typ_code, client=client, modell=modell,
                           cache=cache, stand=stand)
        except KeinCacheTreffer:
            fehlend.append(m.meldung_id)
            continue
        except TypeSafeError as fehler:
            print(f"{m.meldung_id}: API-Fehler – {fehler}")
            fehlend.append(m.meldung_id)
            continue
        e = entscheiden(u, schwellen)
        if not u.aus_cache:
            neu += 1
            tokens_in += u.input_tokens or 0
            tokens_out += u.output_tokens or 0
        zeilen.append(urteil_als_zeile(u, e))
        if ausgabe:
            print(f"{m.meldung_id} {e.entscheidung:<26} {u.kategorie:<16} {u.schwere_stufe:<15} "
                  f"sicher={u.sicherheitsrelevant:.2f}{'  [Cache]' if u.aus_cache else ''}")

    urteile = pd.DataFrame(zeilen)
    lauf = {
        "lauf_id": neue_lauf_id(datensatz, stand),
        "zeitpunkt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "datensatz": datensatz,
        "modell": modell,
        "fragen_stand": stand,
        "fragen_fingerabdruck": fragen_fingerabdruck(stand),
        "regel_version": REGEL_VERSION,
        "schwellen": schwellen.als_dict(),
        "meldungen": len(zeilen),
        "ohne_urteil": ", ".join(fehlend),
        "neue_requests": neu,
        # Tokens dieses Laufs (nur neue Requests) und Tokens aller Urteile, auch aus dem Cache
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "input_tokens_alle_urteile": int(urteile.input_tokens.fillna(0).sum()) if len(urteile) else 0,
        "output_tokens_alle_urteile": int(urteile.output_tokens.fillna(0).sum()) if len(urteile) else 0,
        "anmerkung": anmerkung,
    }
    return urteile, lauf

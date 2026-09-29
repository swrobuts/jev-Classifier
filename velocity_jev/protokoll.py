"""Jeden Lauf so ablegen, dass er sich später vergleichen und visualisieren lässt.

ergebnisse/laeufe/<lauf_id>/   urteile.csv, lauf.json, vergleich.csv, kennzahlen.json eines Laufs
ergebnisse/laeufe.csv          eine Zeile je Lauf: Datensatz, Fragen-Stand, Tokens, Kennzahlen
ergebnisse/urteile_lang.csv    eine Zeile je Meldung, Frage und Antwortoption (Long-Format), letzter Lauf

Lauf-Ordner werden nie überschrieben. Die Dateien direkt in ergebnisse/
(urteile.csv, lauf.json, vergleich.csv) zeigen immer den letzten Lauf.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .fragen import SCHWERE_STUFEN, fragen

NOUL_FRAGEN = {
    "ist_schadensmeldung": "soll_ist_schaden",
    "sicherheitsrelevant": "soll_sicherheitsrelevant",
    "personenschaden": "soll_personenschaden",
}


def neue_lauf_id(datensatz: str, stand: int) -> str:
    """Sortierbarer Name eines Laufs aus Zeitstempel (UTC), Datensatz und Fragen-Stand."""
    zeit = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{zeit}_{datensatz}_stand{stand}"


def fragen_fingerabdruck(stand: int) -> str:
    """Kurzer Hash über den Wortlaut aller Fragen: gleicher Fingerabdruck heißt gleiche Fragen."""
    wortlaut = {k: q.model_dump(mode="json") for k, q in sorted(fragen(stand).items())}
    roh = json.dumps(wortlaut, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()[:10]


def json_schreiben(datei: Path, daten: dict) -> None:
    """Ein Wörterbuch lesbar als JSON speichern."""
    datei.write_text(json.dumps(daten, indent=2, ensure_ascii=False), encoding="utf-8")


def lauf_ablegen(ergebnisse: Path, lauf: dict, urteile: pd.DataFrame) -> Path:
    """Urteile und Laufdaten in den Lauf-Ordner und als »letzter Lauf« nach ergebnisse/ schreiben."""
    ordner = ergebnisse / "laeufe" / lauf["lauf_id"]
    ordner.mkdir(parents=True, exist_ok=True)
    for ziel in (ordner, ergebnisse):
        urteile.to_csv(ziel / "urteile.csv", index=False)
        json_schreiben(ziel / "lauf.json", lauf)
    return ordner


def auswertung_ablegen(ergebnisse: Path, lauf: dict, vergleich: pd.DataFrame, kennzahlen: dict) -> None:
    """Vergleich, Kennzahlen und Long-Format zum Lauf legen und die Laufübersicht erneuern."""
    ordner = ergebnisse / "laeufe" / lauf["lauf_id"]
    ordner.mkdir(parents=True, exist_ok=True)
    for ziel in (ordner, ergebnisse):
        vergleich.to_csv(ziel / "vergleich.csv", index=False)
    json_schreiben(ordner / "kennzahlen.json", kennzahlen)
    urteile_lang(vergleich, lauf["lauf_id"]).to_csv(ergebnisse / "urteile_lang.csv", index=False)
    laeufe_zusammenfassen(ergebnisse)


def urteile_lang(vergleich: pd.DataFrame, lauf_id: str) -> pd.DataFrame:
    """Jede Wahrscheinlichkeit als eigene Zeile, samt Soll-Wert, für Heatmaps und Small Multiples."""
    zeilen = []
    for r in vergleich.itertuples():
        basis = {"lauf_id": lauf_id, "meldung_id": r.meldung_id, "typ_code": r.typ_code, "merkmal": r.merkmal}
        for option, p in json.loads(r.kategorie_wkt).items():
            zeilen.append({**basis, "frage": "kategorie", "primitive": "Choice", "option": option,
                           "stufe": None, "wahrscheinlichkeit": round(p, 4),
                           "ist_antwort": option == r.kategorie, "ist_soll": option == r.soll_kategorie})
        schwere_wkt = json.loads(r.schwere_wkt)
        for stufe, option in enumerate(SCHWERE_STUFEN):
            zeilen.append({**basis, "frage": "schwere", "primitive": "Score", "option": option,
                           "stufe": stufe, "wahrscheinlichkeit": round(schwere_wkt.get(option, 0.0), 4),
                           "ist_antwort": option == r.schwere_stufe, "ist_soll": option == r.soll_schwere})
        for frage, soll in NOUL_FRAGEN.items():
            p = getattr(r, frage)
            zeilen.append({**basis, "frage": frage, "primitive": "Noul", "option": "ja",
                           "stufe": None, "wahrscheinlichkeit": round(p, 4),
                           "ist_antwort": p >= 0.5, "ist_soll": bool(getattr(r, soll))})
    return pd.DataFrame(zeilen)


def laeufe_zusammenfassen(ergebnisse: Path) -> pd.DataFrame:
    """Alle Lauf-Ordner zu einer Tabelle zusammenführen, eine Zeile je Lauf."""
    zeilen = []
    for ordner in sorted((ergebnisse / "laeufe").glob("*")):
        lauf_datei, kennzahl_datei = ordner / "lauf.json", ordner / "kennzahlen.json"
        if not lauf_datei.exists():
            continue
        zeile = json.loads(lauf_datei.read_text(encoding="utf-8"))
        schwellen = zeile.pop("schwellen", {})
        zeile.update({f"schwelle_{k}": v for k, v in schwellen.items()})
        if kennzahl_datei.exists():
            zeile.update(json.loads(kennzahl_datei.read_text(encoding="utf-8")))
        zeilen.append(zeile)
    tabelle = pd.DataFrame(zeilen)
    tabelle.to_csv(ergebnisse / "laeufe.csv", index=False)
    return tabelle

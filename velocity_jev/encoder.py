"""Vergleichsmodell: ein Encoder aus der BERT-Familie, der ohne Training über NLI urteilt.

Das Modell mDeBERTa-v3-base (279 Mio. Parameter, mehrsprachig) wurde auf Natural Language
Inference trainiert: Es schätzt, ob eine Hypothese aus einem Text folgt. Jede der fünf Fragen
an Jev wird dafür in Hypothesen übersetzt. Das Modell sieht keine VeloCity-Meldung mit Label;
wie Jev urteilt es ohne Training auf diesen Daten (Zero-Shot).

Die Wahrscheinlichkeiten liegen in daten/cache/encoder_nli.csv. Das Notebook läuft deshalb
ohne Modell-Download; neu gerechnet wird nur auf Wunsch oder wenn sich eine Hypothese ändert.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from .fragen import KEINE_ZUORDNUNG
from .rohwerte import praemisse, urteile_aus_rohwerten

MODELL_NLI = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
CACHE_NLI = Path(__file__).resolve().parent.parent / "daten" / "cache" / "encoder_nli.csv"

# Je Ja/Nein-Frage eine Hypothese für "ja" und eine für "nein", wie die criteria der Fragen an Jev.
# Mit nur einer Hypothese wählt die Pipeline zwischen "folgt" und "widerspricht"; "neutral" fällt
# weg, und bei personenschaden kam fast immer "ja" heraus. Verneinungen sind vermieden, weil
# NLI-Modelle sie schlecht verarbeiten.
HYPOTHESEN = {
    "ist_schadensmeldung": {
        "ja": "Ein Bauteil des Fahrrads ist defekt, beschädigt oder funktioniert nicht richtig.",
        "nein": "Es geht um Abrechnung, App, Station, Verfügbarkeit, Parken oder Lob.",
    },
    "sicherheitsrelevant": {
        "ja": "Mit diesem Fahrrad weiterzufahren ist gefährlich.",
        "nein": "Das Fahrrad bremst, lenkt und trägt weiterhin zuverlässig.",
    },
    "personenschaden": {
        "ja": "Eine Person ist gestürzt oder wurde verletzt.",
        "nein": "Alle Beteiligten sind unverletzt geblieben.",
    },
}

# Je Kategorie ein Satzteil für die Vorlage; die Klammern folgen den Beschreibungen in fragen.py.
VORLAGE_KATEGORIE = "Die Meldung betrifft {}."
KATEGORIE_SATZTEILE = {
    "Bremse": "die Bremse (Bremshebel, Bremszug, Bremsbeläge)",
    "Reifen": "den Reifen (Mantel, Schlauch, Ventil, Luftdruck)",
    "Laufrad": "das Laufrad (Felge, Speichen, Nabe)",
    "Schaltung": "die Schaltung (Gangwechsel, Kette, Ritzel)",
    "Beleuchtung": "die Beleuchtung (Vorderlicht, Rücklicht, Dynamo)",
    "Klingel": "die Klingel",
    "Rahmen": "den Rahmen (Rahmenrohre, Schweißnähte, Lack)",
    "Gabel": "die Vordergabel",
    "Lenkung": "die Lenkung (Lenker, Vorbau, Griffe)",
    "Sattel": "den Sattel (Sattel, Sattelstütze, Sattelklemme)",
    "Pedale": "die Pedale oder Kurbeln",
    "Akku": "den Akku des E-Bikes (Ladebuchse, Reichweite)",
    "Motor": "den Motor des E-Bikes (Tretunterstützung, Display)",
    "Schloss": "das Schloss des Leihrads",
    "Ladebox": "die Transportbox des Lastenrads (Klappe, Kinderbank, Gurte)",
    KEINE_ZUORDNUNG: "kein bestimmtes Bauteil des Fahrrads",
}

# Je Schwerestufe eine Hypothese, gekürzt aus SCHWERE_BESCHREIBUNG in fragen.py, ohne Verneinung.
SCHWERE_HYPOTHESEN = {
    "gering": "Betroffen sind nur Komfort, Geräusche oder Aussehen des Fahrrads.",
    "mittel": "Eine Funktion des Fahrrads ist eingeschränkt, das Fahren bleibt aber sicher.",
    "fahruntauglich": "Weiterfahren mit dem Fahrrad ist gefährlich oder unmöglich.",
}


def hypothesen_fingerabdruck() -> str:
    """Ändert sich Modell oder Hypothese, passt der Cache nicht mehr, wie beim Cache von Jev."""
    roh = json.dumps([MODELL_NLI, HYPOTHESEN, VORLAGE_KATEGORIE, KATEGORIE_SATZTEILE, SCHWERE_HYPOTHESEN],
                     ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()[:10]


def modell_laden():
    """Lädt das Modell von Hugging Face (rund 1,1 GB beim ersten Mal) und rechnet auf der CPU."""
    from transformers import pipeline
    return pipeline("zero-shot-classification", model=MODELL_NLI, device=-1)


def als_liste(ergebnis) -> list[dict]:
    """Die Pipeline liefert bei einem einzigen Text ein Wörterbuch statt einer Liste."""
    return ergebnis if isinstance(ergebnis, list) else [ergebnis]


def verteilungen(klassifikator, texte: list[str], satzteile: dict[str, str], vorlage: str) -> list[dict[str, float]]:
    """Je Text eine Wahrscheinlichkeit je Antwort, zusammen 1, nach den Namen aus fragen.py."""
    name_zu = {satz: name for name, satz in satzteile.items()}
    ergebnisse = klassifikator(texte, candidate_labels=list(satzteile.values()),
                               hypothesis_template=vorlage, multi_label=False)
    return [{name_zu[l]: float(s) for l, s in zip(e["labels"], e["scores"])} for e in als_liste(ergebnisse)]


def rohwerte_berechnen(meldungen: pd.DataFrame, klassifikator, datensatz: str) -> pd.DataFrame:
    """Alle Wahrscheinlichkeiten des Encoders für einen Datensatz, eine Zeile je Meldung."""
    texte = [praemisse(m.text, m.typ_code) for m in meldungen.itertuples()]
    rohwerte = pd.DataFrame({"datensatz": datensatz, "meldung_id": list(meldungen.meldung_id)})
    for frage, ja_nein in HYPOTHESEN.items():
        rohwerte[frage] = [v["ja"] for v in verteilungen(klassifikator, texte, ja_nein, "{}")]
    kategorien = verteilungen(klassifikator, texte, KATEGORIE_SATZTEILE, VORLAGE_KATEGORIE)
    schweren = verteilungen(klassifikator, texte, SCHWERE_HYPOTHESEN, "{}")
    rohwerte["kategorie_wkt"] = [json.dumps(v, ensure_ascii=False) for v in kategorien]
    rohwerte["schwere_wkt"] = [json.dumps(v, ensure_ascii=False) for v in schweren]
    rohwerte["hypothesen"] = hypothesen_fingerabdruck()
    return rohwerte


def cache_lesen(datensatz: str, datei: Path = CACHE_NLI) -> pd.DataFrame | None:
    """Gespeicherte Wahrscheinlichkeiten eines Datensatzes, sofern sie zu Modell und Hypothesen passen."""
    if not datei.exists():
        return None
    alle = pd.read_csv(datei, dtype={"meldung_id": str})
    passend = alle[(alle.datensatz == datensatz) & (alle.hypothesen == hypothesen_fingerabdruck())]
    return passend.reset_index(drop=True) if len(passend) else None


def cache_schreiben(rohwerte: pd.DataFrame, datei: Path = CACHE_NLI) -> None:
    """Ersetzt im Cache die Zeilen dieses Datensatzes und behält alle anderen."""
    datensatz = rohwerte.datensatz.iloc[0]
    alle = pd.read_csv(datei, dtype={"meldung_id": str}) if datei.exists() else rohwerte.iloc[0:0]
    alle = pd.concat([alle[alle.datensatz != datensatz], rohwerte], ignore_index=True)
    datei.parent.mkdir(parents=True, exist_ok=True)
    alle.to_csv(datei, index=False)


def encoder_urteile(meldungen: pd.DataFrame, datensatz: str, neu_rechnen: bool = False,
                    datei: Path = CACHE_NLI) -> pd.DataFrame:
    """Urteile des Encoders für einen Datensatz, aus dem Cache oder neu gerechnet, entschieden mit regeln.py."""
    rohwerte = cache_lesen(datensatz, datei)
    fehlt = rohwerte is None or set(rohwerte.meldung_id) != set(meldungen.meldung_id)
    if neu_rechnen or fehlt:
        rohwerte = rohwerte_berechnen(meldungen, modell_laden(), datensatz)
        cache_schreiben(rohwerte, datei)
    return urteile_aus_rohwerten(rohwerte, MODELL_NLI)

"""Aus den Wahrscheinlichkeiten eines beliebigen Modells Urteile in der Form von Jev bilden.

Ein Vergleichsmodell liefert je Meldung drei Ja-Wahrscheinlichkeiten (ist_schadensmeldung,
sicherheitsrelevant, personenschaden) und zwei Verteilungen (Kategorie, Schwere). Daraus
entsteht dasselbe Urteil wie bei Jev, und derselbe Code in regeln.py entscheidet mit denselben
Schwellen. Unterschiede im Ergebnis gehen dann allein auf das Modell zurück.
"""

from __future__ import annotations

import json

import pandas as pd

from .ablauf import urteil_als_zeile
from .fragen import RADTYPEN, SCHWERE_STUFEN
from .pipeline import Urteil, stufe_aus_score
from .regeln import Schwellen, entscheiden


def praemisse(text: str, typ_code: str) -> str:
    """Der Text, den ein Vergleichsmodell liest: Radtyp und Meldung, wie im State von Jev."""
    return f"Radtyp: {RADTYPEN[typ_code]['typ']}. Meldung: {text}"


def erwartungswert(schwere_wkt: dict[str, float]) -> float:
    """Erwartungswert der Schwere auf der Skala 0 (gering) bis 2 (fahruntauglich), wie bei Score."""
    return sum(stufe * schwere_wkt.get(name, 0.0) for stufe, name in enumerate(SCHWERE_STUFEN))


def urteil_aus_rohwerten(zeile, modell: str) -> Urteil:
    """Ein Urteil aus einer Zeile mit Wahrscheinlichkeiten; als Konfidenz gilt die höchste Wahrscheinlichkeit."""
    kategorie_wkt = json.loads(zeile.kategorie_wkt)
    schwere_wkt = json.loads(zeile.schwere_wkt)
    kategorie = max(kategorie_wkt, key=kategorie_wkt.get)
    score = erwartungswert(schwere_wkt)
    return Urteil(
        meldung_id=zeile.meldung_id, modell=modell, ist_schadensmeldung=float(zeile.ist_schadensmeldung),
        kategorie=kategorie, kategorie_konfidenz=kategorie_wkt[kategorie], kategorie_wkt=kategorie_wkt,
        schwere_stufe=stufe_aus_score(score), schwere_score=score, schwere_konfidenz=max(schwere_wkt.values()),
        schwere_wkt=schwere_wkt, sicherheitsrelevant=float(zeile.sicherheitsrelevant),
        personenschaden=float(zeile.personenschaden),
    )


def urteile_aus_rohwerten(rohwerte: pd.DataFrame, modell: str, schwellen: Schwellen = Schwellen()) -> pd.DataFrame:
    """Urteile bilden und mit denselben Regeln wie bei Jev entscheiden, eine Zeile je Meldung."""
    zeilen = []
    for zeile in rohwerte.itertuples(index=False):
        urteil = urteil_aus_rohwerten(zeile, modell)
        zeilen.append(urteil_als_zeile(urteil, entscheiden(urteil, schwellen)))
    return pd.DataFrame(zeilen)

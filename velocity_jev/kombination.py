"""Verfahren kombinieren und die tatsächlichen Kosten der Dienste berechnen.

Zwei Strategien für Jev und ein LLM:
- Einigkeit: automatisch entscheidet der Code nur, wenn beide Verfahren zur selben
  Entscheidung kommen; sonst prüft ein Mensch. Das LLM wird nur für Meldungen gefragt,
  die Jev automatisch entscheiden würde, denn eine Prüfung bleibt ohnehin eine Prüfung.
- Zweitmeinung bei Prüfung: Jev entscheidet, und nur die Fälle, die Jev zur Prüfung
  schickt, entscheidet stattdessen das LLM.
"""

from __future__ import annotations

import pandas as pd

from .auswertung import entscheidungs_kennzahlen
from .regeln import PRUEFEN

# US-Dollar je 1 Mio. Input-Tokens; Output ist bei Jev kostenlos (docs.typesafe.ai/models, Stand 29.09.2026)
PREIS_JEV_INPUT = 0.042


def jev_kosten_dollar(urteile: pd.DataFrame) -> float:
    """Kosten der Anfragen an Jev für diese Urteile, auch wenn sie heute aus dem Cache kommen."""
    return float(urteile.input_tokens.fillna(0).sum()) * PREIS_JEV_INPUT / 1e6


def einigkeit(erste: pd.Series, zweite: pd.Series) -> pd.Series:
    """Automatisch nur, wenn beide Verfahren gleich entscheiden; sonst prüft ein Mensch."""
    return pd.Series([a if a == b else PRUEFEN for a, b in zip(erste, zweite)], index=erste.index)


def zweitmeinung_bei_pruefung(erste: pd.Series, zweite: pd.Series) -> pd.Series:
    """Das zweite Verfahren entscheidet nur die Fälle, die das erste zur Prüfung schickt."""
    return pd.Series([b if a == PRUEFEN else a for a, b in zip(erste, zweite)], index=erste.index)


def strategien_bewerten(jev: pd.DataFrame, llm: pd.DataFrame, jev_dollar: float, llm_dollar: float) -> pd.DataFrame:
    """Kennzahlen und Kosten der Anfragen je Strategie; jev und llm sind Vergleichstabellen derselben Meldungen."""
    llm = llm.set_index("meldung_id").loc[jev.meldung_id].reset_index()
    soll = jev.soll_entscheidung.reset_index(drop=True)
    erste, zweite = jev.entscheidung.reset_index(drop=True), llm.entscheidung
    anteil_automatisch = float((erste != PRUEFEN).mean())
    strategien = {
        "Jev allein": (erste, jev_dollar),
        "LLM allein": (zweite, llm_dollar),
        "Einigkeit, sonst Prüfung": (einigkeit(erste, zweite), jev_dollar + llm_dollar * anteil_automatisch),
        "LLM entscheidet Jevs Prüffälle": (zweitmeinung_bei_pruefung(erste, zweite),
                                           jev_dollar + llm_dollar * (1 - anteil_automatisch)),
    }
    zeilen = [{"strategie": name, **entscheidungs_kennzahlen(ist, soll), "anfragen_dollar": dollar}
              for name, (ist, dollar) in strategien.items()]
    return pd.DataFrame(zeilen).set_index("strategie")


def je_10000(dollar: float, meldungen: int) -> float:
    """Kosten hochgerechnet auf 10 000 Meldungen."""
    return dollar / meldungen * 10_000

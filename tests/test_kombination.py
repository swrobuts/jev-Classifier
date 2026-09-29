import matplotlib
import pandas as pd

matplotlib.use("Agg")

from velocity_jev.grafiken import dollar, euro, prozent, vergleich_zeichnen  # noqa: E402
from velocity_jev.kombination import (  # noqa: E402
    einigkeit, je_10000, jev_kosten_dollar, strategien_bewerten, zweitmeinung_bei_pruefung,
)
from velocity_jev.regeln import AUFTRAG, KEIN_SCHADEN, PRUEFEN, SPERREN  # noqa: E402


def test_einigkeit_schickt_widersprueche_zur_pruefung():
    erste = pd.Series([SPERREN, AUFTRAG, PRUEFEN])
    zweite = pd.Series([SPERREN, KEIN_SCHADEN, AUFTRAG])
    assert list(einigkeit(erste, zweite)) == [SPERREN, PRUEFEN, PRUEFEN]


def test_zweitmeinung_nur_fuer_prueffaelle():
    erste = pd.Series([SPERREN, PRUEFEN])
    zweite = pd.Series([AUFTRAG, AUFTRAG])
    assert list(zweitmeinung_bei_pruefung(erste, zweite)) == [SPERREN, AUFTRAG]


def test_kosten_der_anfragen():
    assert jev_kosten_dollar(pd.DataFrame({"input_tokens": [1_000_000, None]})) == 0.042
    assert je_10000(0.5, 50) == 100


def test_strategien_bewerten():
    jev = pd.DataFrame({"meldung_id": ["A", "B"], "entscheidung": [SPERREN, PRUEFEN],
                        "soll_entscheidung": [SPERREN, AUFTRAG]})
    llm = pd.DataFrame({"meldung_id": ["B", "A"], "entscheidung": [AUFTRAG, SPERREN]})
    s = strategien_bewerten(jev, llm, jev_dollar=0.01, llm_dollar=1.0)
    assert s.loc["LLM allein", "richtig"] == 1.0
    assert s.loc["Einigkeit, sonst Prüfung", "anfragen_dollar"] == 0.01 + 0.5
    assert s.loc["LLM entscheidet Jevs Prüffälle", "richtig"] == 1.0


def test_formate_und_diagramm():
    assert prozent(0.791) == "79 %" and euro(148.0) == "148 €" and dollar(0.0834) == "0,083 $"
    tabelle = pd.DataFrame({"Jev": [0.8, 100.0], "LLM": [0.7, 120.0]}, index=["richtig", "kosten_gesamt"])
    abbildung = vergleich_zeichnen({"A": tabelle, "B": tabelle}, [("richtig", "richtig", prozent),
                                                                  ("kosten_gesamt", "Kosten", euro)])
    assert len(abbildung.axes) == 4

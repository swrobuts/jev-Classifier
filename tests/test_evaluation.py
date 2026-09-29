import pandas as pd

from velocity_jev.evaluation import (
    JA_NEIN, entscheidungen_vergleichen, ja_nein_kennzahlen, kennzahlen_je_urteil, klassen_kennzahlen,
    konfusionsmatrix, konfusionsmatrizen, mehrklassen_kennzahlen, modelle_vergleichen,
)
from velocity_jev.regeln import AUFTRAG, KEIN_SCHADEN, PRUEFEN, SPERREN


def vergleich() -> pd.DataFrame:
    """Vier Meldungen mit Soll und Ist, in der Form von auswertung.vergleich_bauen()."""
    return pd.DataFrame({
        "meldung_id": ["A", "B", "C", "D"],
        "soll_ist_schaden": [True, True, True, False], "ist_schadensmeldung": [0.9, 0.8, 0.3, 0.1],
        "soll_sicherheitsrelevant": [True, False, False, False], "sicherheitsrelevant": [0.9, 0.6, 0.1, 0.0],
        "soll_personenschaden": [False, False, False, False], "personenschaden": [0.1, 0.1, 0.1, 0.1],
        "soll_kategorie": ["Bremse", "Klingel", "Klingel", ""], "kategorie": ["Bremse", "Klingel", "Bremse", "Klingel"],
        "soll_schwere": ["fahruntauglich", "gering", "gering", ""],
        "schwere_stufe": ["fahruntauglich", "gering", "mittel", "gering"],
        "soll_entscheidung": [SPERREN, AUFTRAG, AUFTRAG, KEIN_SCHADEN],
        "entscheidung": [SPERREN, PRUEFEN, KEIN_SCHADEN, KEIN_SCHADEN],
    })


def test_ja_nein_kennzahlen():
    k = ja_nein_kennzahlen(pd.Series([True, True, False, False]), pd.Series([True, False, True, False]))
    assert k["n"] == 4 and k["accuracy"] == 0.5 and k["precision"] == 0.5 and k["recall"] == 0.5


def test_recall_ohne_positive_vorhersage_ist_null():
    k = ja_nein_kennzahlen(pd.Series([True, False]), pd.Series([False, False]))
    assert k["recall"] == 0 and k["precision"] == 0


def test_mehrklassen_makro_ueber_die_klassen_im_soll():
    k = mehrklassen_kennzahlen(pd.Series(["a", "a", "b"]), pd.Series(["a", "b", "b"]))
    assert k["accuracy"] == 2 / 3 and round(k["recall"], 3) == 0.75


def test_konfusionsmatrix_zeilen_soll_spalten_vorhersage():
    m = konfusionsmatrix(pd.Series(["ja", "ja", "nein"]), pd.Series(["ja", "nein", "nein"]), JA_NEIN)
    assert m.loc["ja", "ja"] == 1 and m.loc["ja", "nein"] == 1 and m.loc["nein", "nein"] == 1
    assert list(m.index) == JA_NEIN and list(m.columns) == JA_NEIN


def test_kennzahlen_je_urteil_hat_alle_urteile():
    k = kennzahlen_je_urteil(vergleich()).set_index("urteil")
    assert list(k.index) == ["ist_schadensmeldung", "sicherheitsrelevant", "personenschaden",
                             "kategorie", "schwere", "entscheidung"]
    assert k.loc["sicherheitsrelevant", "n"] == 3  # nur echte Schadensmeldungen
    assert k.loc["kategorie", "accuracy"] == 2 / 3


def test_klassen_kennzahlen_zaehlen_soll_und_vorhersage():
    v = vergleich()
    k = klassen_kennzahlen(v.soll_entscheidung, v.entscheidung, [SPERREN, AUFTRAG]).set_index("klasse")
    assert k.loc[SPERREN, "recall"] == 1 and k.loc[AUFTRAG, "soll"] == 2 and k.loc[AUFTRAG, "vorhergesagt"] == 0


def test_konfusionsmatrizen_enthalten_nur_vorkommende_kategorien():
    m = konfusionsmatrizen(vergleich())
    assert list(m["kategorie"].index) == ["Bremse", "Klingel"]
    assert int(m["entscheidung"].to_numpy().sum()) == 4


def test_modelle_nebeneinander():
    v = vergleich()
    tabelle = modelle_vergleichen({"eins": v, "zwei": v})
    assert list(tabelle.columns) == ["eins", "zwei"]
    assert tabelle.loc[("kategorie", "accuracy"), "eins"] == 2 / 3
    e = entscheidungen_vergleichen({"eins": v})
    assert e.loc["sicherheitsschaden_uebersehen", "eins"] == 0

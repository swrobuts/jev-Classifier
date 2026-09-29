"""Vergleichsmodell: ein klassischer Klassifikator, trainiert auf den 48 Meldungen.

Zeichen-n-Gramme mit TF-IDF und je Frage eine logistische Regression, der Stand der
Textklassifikation vor den Sprachmodellen (siehe docs/recherche_fruehere_ansaetze.md).
Anders als Jev und der Encoder braucht er Beispiele mit Label. Trainiert wird auf
daten/meldungen.csv, geprüft auf dem Holdout. Auf den Trainingsdaten selbst wären die
Kennzahlen geschönt, weil das Modell die Antworten dort schon gesehen hat.
"""

from __future__ import annotations

import json

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from .rohwerte import praemisse, urteile_aus_rohwerten

MODELL_KLASSISCH = "TF-IDF + logistische Regression"


def neues_modell():
    """Zeichen-n-Gramme sind bei wenigen Beispielen robuster gegen Tippfehler und Dialekt als ganze Wörter."""
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True),
        LogisticRegression(max_iter=2000, class_weight="balanced"),
    )


def texte(meldungen: pd.DataFrame) -> list[str]:
    """Radtyp und Meldungstext, derselbe Text wie beim Encoder."""
    return [praemisse(m.text, m.typ_code) for m in meldungen.itertuples()]


def ja_wahrscheinlichkeiten(training: pd.DataFrame, spalte: str, test: pd.DataFrame) -> list[float]:
    """Trainiert eine Ja/Nein-Frage und liefert je Testmeldung die Wahrscheinlichkeit für "ja"."""
    modell = neues_modell().fit(texte(training), training[spalte].astype(bool))
    ja = list(modell.classes_).index(True)
    return [float(p[ja]) for p in modell.predict_proba(texte(test))]


def verteilungen(training: pd.DataFrame, spalte: str, test: pd.DataFrame) -> list[dict[str, float]]:
    """Trainiert eine Frage mit mehreren Antworten und liefert je Testmeldung eine Wahrscheinlichkeit je Antwort."""
    modell = neues_modell().fit(texte(training), training[spalte])
    return [dict(zip(modell.classes_, map(float, p))) for p in modell.predict_proba(texte(test))]


def klassisch_urteile(training: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Alle fünf Fragen trainieren, Urteile für die Testmeldungen bilden und mit regeln.py entscheiden."""
    schaden = training[training.soll_ist_schaden.astype(bool)]
    rohwerte = pd.DataFrame({"meldung_id": list(test.meldung_id)})
    rohwerte["ist_schadensmeldung"] = ja_wahrscheinlichkeiten(training, "soll_ist_schaden", test)
    rohwerte["sicherheitsrelevant"] = ja_wahrscheinlichkeiten(training, "soll_sicherheitsrelevant", test)
    rohwerte["personenschaden"] = ja_wahrscheinlichkeiten(training, "soll_personenschaden", test)
    rohwerte["kategorie_wkt"] = [json.dumps(v, ensure_ascii=False)
                                 for v in verteilungen(schaden, "soll_kategorie", test)]
    rohwerte["schwere_wkt"] = [json.dumps(v, ensure_ascii=False)
                               for v in verteilungen(schaden, "soll_schwere", test)]
    return urteile_aus_rohwerten(rohwerte, MODELL_KLASSISCH)

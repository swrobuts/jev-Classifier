import json

import pandas as pd

from velocity_jev import encoder
from velocity_jev.klassisch import klassisch_urteile
from velocity_jev.regeln import PRUEFEN, SPERREN
from velocity_jev.rohwerte import erwartungswert, praemisse, urteil_aus_rohwerten, urteile_aus_rohwerten


def rohwerte(**aenderungen) -> pd.DataFrame:
    basis = dict(meldung_id="T", ist_schadensmeldung=0.9, sicherheitsrelevant=0.95, personenschaden=0.1,
                 kategorie_wkt=json.dumps({"Bremse": 0.7, "Klingel": 0.3}),
                 schwere_wkt=json.dumps({"gering": 0.1, "mittel": 0.2, "fahruntauglich": 0.7}))
    return pd.DataFrame([{**basis, **aenderungen}])


def test_praemisse_nennt_radtyp_und_text():
    assert praemisse("Bremse kaputt", "CITY") == "Radtyp: City-Bike. Meldung: Bremse kaputt"


def test_erwartungswert_der_schwere():
    assert erwartungswert({"gering": 0.0, "mittel": 0.5, "fahruntauglich": 0.5}) == 1.5


def test_urteil_aus_rohwerten():
    u = urteil_aus_rohwerten(next(rohwerte().itertuples(index=False)), "test")
    assert u.kategorie == "Bremse" and u.kategorie_konfidenz == 0.7
    assert u.schwere_stufe == "fahruntauglich" and round(u.schwere_score, 2) == 1.6


def test_gleiche_regeln_wie_bei_jev():
    assert urteile_aus_rohwerten(rohwerte(), "test").entscheidung.iloc[0] == SPERREN
    unsicher = rohwerte(sicherheitsrelevant=0.1, kategorie_wkt=json.dumps({"Bremse": 0.4, "Klingel": 0.35, "Akku": 0.25}),
                        schwere_wkt=json.dumps({"gering": 0.8, "mittel": 0.2, "fahruntauglich": 0.0}))
    assert urteile_aus_rohwerten(unsicher, "test").entscheidung.iloc[0] == PRUEFEN


class Attrappe:
    """Antwortet wie die Zero-Shot-Pipeline: immer die erste Antwort mit 0,8, die übrigen teilen sich den Rest."""

    def __call__(self, texte, candidate_labels, hypothesis_template, multi_label):
        rest = 0.2 / max(len(candidate_labels) - 1, 1)
        antwort = {"labels": candidate_labels, "scores": [0.8] + [rest] * (len(candidate_labels) - 1)}
        return [antwort for _ in texte]


def meldungen() -> pd.DataFrame:
    return pd.DataFrame({"meldung_id": ["A", "B"], "text": ["Bremse greift nicht", "App stürzt ab"],
                         "typ_code": ["CITY", "EBIKE"]})


def test_encoder_rechnet_und_speichert(tmp_path, monkeypatch):
    monkeypatch.setattr(encoder, "modell_laden", lambda: Attrappe())
    datei = tmp_path / "encoder.csv"
    urteile = encoder.encoder_urteile(meldungen(), "test", datei=datei)
    assert list(urteile.meldung_id) == ["A", "B"] and urteile.ist_schadensmeldung.iloc[0] == 0.8
    assert urteile.kategorie.iloc[0] == "Bremse"  # erste Kategorie in KATEGORIE_SATZTEILE
    gespeichert = encoder.cache_lesen("test", datei)
    assert len(gespeichert) == 2 and gespeichert.hypothesen.iloc[0] == encoder.hypothesen_fingerabdruck()


def test_encoder_liest_aus_dem_cache(tmp_path, monkeypatch):
    datei = tmp_path / "encoder.csv"
    monkeypatch.setattr(encoder, "modell_laden", lambda: Attrappe())
    encoder.encoder_urteile(meldungen(), "test", datei=datei)
    monkeypatch.setattr(encoder, "modell_laden", lambda: (_ for _ in ()).throw(AssertionError("nicht laden")))
    assert len(encoder.encoder_urteile(meldungen(), "test", datei=datei)) == 2


def test_klassischer_klassifikator_liefert_urteile():
    training = pd.DataFrame({
        "meldung_id": [f"M{i}" for i in range(6)],
        "text": ["Bremse greift nicht", "Bremse quietscht", "Klingel klemmt", "Klingel lose",
                 "Rechnung falsch", "App stürzt ab"],
        "typ_code": ["CITY"] * 6,
        "soll_ist_schaden": [1, 1, 1, 1, 0, 0], "soll_sicherheitsrelevant": [1, 0, 0, 0, 0, 0],
        "soll_personenschaden": [1, 0, 0, 0, 0, 0],
        "soll_kategorie": ["Bremse", "Bremse", "Klingel", "Klingel", "", ""],
        "soll_schwere": ["fahruntauglich", "mittel", "gering", "gering", "", ""],
    })
    urteile = klassisch_urteile(training, training.head(2))
    assert len(urteile) == 2 and urteile.ist_schadensmeldung.between(0, 1).all()
    assert set(urteile.kategorie) <= {"Bremse", "Klingel"}

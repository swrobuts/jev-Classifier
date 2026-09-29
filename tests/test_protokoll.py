"""Fragen-Stände, Schwere-Stufe, Auswertung und Protokoll – ohne API."""

import pandas as pd

from tests.attrappe import transport
from typesafe_sdk import TypeSafeClient
from velocity_jev.ablauf import klassifizieren
from velocity_jev.auswertung import alle_kennzahlen, gruppiert, vergleich_bauen
from velocity_jev.fragen import AKTUELLER_STAND, STAENDE
from velocity_jev.konfig import HOLDOUT, MELDUNGEN
from velocity_jev.pipeline import Cache, stufe_aus_score
from velocity_jev.protokoll import auswertung_ablegen, fragen_fingerabdruck, lauf_ablegen


def test_jeder_stand_hat_eigenen_wortlaut():
    abdruecke = {fragen_fingerabdruck(s) for s in STAENDE}
    assert len(abdruecke) == len(STAENDE) and AKTUELLER_STAND in STAENDE


def test_schwere_stufe_aus_gerundetem_erwartungswert():
    assert stufe_aus_score(1.25) == "mittel"        # M027: wahrscheinlichste Stufe wäre fahruntauglich
    assert stufe_aus_score(0.49) == "gering"
    assert stufe_aus_score(1.5) == "fahruntauglich"
    assert stufe_aus_score(2.0) == "fahruntauglich"


def test_holdout_hat_dieselben_spalten_und_keine_doppelten_texte():
    m, h = pd.read_csv(MELDUNGEN), pd.read_csv(HOLDOUT)
    assert list(m.columns) == list(h.columns)
    assert not set(m.text) & set(h.text)


def test_lauf_wird_vollstaendig_protokolliert(tmp_path, monkeypatch):
    monkeypatch.setattr("velocity_jev.pipeline.CACHE_DATEI", tmp_path / "c.jsonl")
    monkeypatch.setattr(Cache.__init__, "__defaults__", (tmp_path / "c.jsonl",))
    meldungen = pd.read_csv(MELDUNGEN, dtype={"meldung_id": str}).head(4)
    with TypeSafeClient(api_key="apikey_attrappe", model="attrappe", transport=transport()) as c:
        urteile, lauf = klassifizieren(meldungen, client=c, modell="attrappe", ausgabe=False)
    assert lauf["neue_requests"] == 4 and lauf["input_tokens"] == 1200

    lauf_ablegen(tmp_path, lauf, urteile)
    vergleich = vergleich_bauen(meldungen, urteile)
    auswertung_ablegen(tmp_path, lauf, vergleich, alle_kennzahlen(vergleich))

    ordner = tmp_path / "laeufe" / lauf["lauf_id"]
    assert {p.name for p in ordner.iterdir()} == {"urteile.csv", "lauf.json", "vergleich.csv", "kennzahlen.json"}
    laeufe = pd.read_csv(tmp_path / "laeufe.csv")
    assert len(laeufe) == 1 and "kategorie_treffer" in laeufe.columns
    lang = pd.read_csv(tmp_path / "urteile_lang.csv")
    assert len(lang) == 4 * (16 + 3 + 3)  # 16 Kategorien, 3 Stufen, 3 Nouls je Meldung
    assert len(gruppiert(vergleich, "merkmal")) == vergleich.merkmal.nunique()

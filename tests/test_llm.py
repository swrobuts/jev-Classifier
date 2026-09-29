import json
from types import SimpleNamespace

import pandas as pd

from velocity_jev import llm
from velocity_jev.fragen import KATEGORIEN
from velocity_jev.regeln import SPERREN


class LlmAttrappe:
    """Antwortet wie die Chat-Completions-API mit festen Werten; zählt die Aufrufe."""

    def __init__(self):
        self.aufrufe = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **argumente):
        self.aufrufe.append(argumente)
        inhalt = {"ist_schadensmeldung": 0.9, "sicherheitsrelevant": 1.2, "personenschaden": -0.1,
                  "kategorie": {k: (2.0 if k == "Bremse" else 0.0) for k in KATEGORIEN},
                  "schwere": {"gering": 0, "mittel": 0, "fahruntauglich": 1}}
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(inhalt)))],
                               usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20))


def meldungen() -> pd.DataFrame:
    return pd.DataFrame({"meldung_id": ["A"], "text": ["Bremse greift nicht"], "typ_code": ["CITY"]})


def test_schema_verlangt_alle_felder():
    s = llm.schema()
    assert s["required"] == list(s["properties"]) and s["additionalProperties"] is False
    assert s["properties"]["kategorie"]["required"] == list(KATEGORIEN)


def test_normiert_begrenzt_und_teilt():
    assert llm.normiert({"a": 2, "b": 2}) == {"a": 0.5, "b": 0.5}
    assert llm.normiert({"a": -1, "b": 0.5}) == {"a": 0.0, "b": 1.0}
    assert llm.normiert({"a": 0, "b": 0}) == {"a": 0.5, "b": 0.5}


def test_nutzertext_enthaelt_state_und_fragen():
    text = llm.nutzertext("Bremse greift nicht", "CITY", 1)
    assert "Bremse greift nicht" in text and "City-Bike" in text and "Frage sicherheitsrelevant" in text


def test_llm_fragt_einmal_und_liest_dann_aus_dem_cache(tmp_path):
    datei = tmp_path / "llm.csv"
    attrappe = LlmAttrappe()
    r = llm.llm_rohwerte(meldungen(), "test", stand=1, client=attrappe, datei=datei)
    assert len(attrappe.aufrufe) == 1
    anfrage = attrappe.aufrufe[0]
    assert anfrage["response_format"]["json_schema"]["strict"] is True
    assert anfrage["messages"][0]["content"] == llm.SYSTEM
    assert r.sicherheitsrelevant.iloc[0] == 1.0 and r.personenschaden.iloc[0] == 0.0
    assert json.loads(r.kategorie_wkt.iloc[0])["Bremse"] == 1.0 and r.input_tokens.iloc[0] == 100
    llm.llm_rohwerte(meldungen(), "test", stand=1, client=attrappe, datei=datei)
    assert len(attrappe.aufrufe) == 1


def test_gleiche_regeln_und_kosten():
    attrappe = LlmAttrappe()
    r = llm.rohwerte_berechnen(meldungen(), attrappe, "test", 1)
    assert llm.llm_urteile(r).entscheidung.iloc[0] == SPERREN
    assert llm.kosten_dollar(r) == (100 * llm.PREIS_INPUT + 20 * llm.PREIS_OUTPUT) / 1e6

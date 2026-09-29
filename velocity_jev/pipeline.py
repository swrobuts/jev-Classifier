"""Eine Schadenmeldung an Jev schicken und die Antworten flach ablegen.

Jede Antwort landet in einem Cache (daten/cache/jev_cache.jsonl). Dieselbe
Meldung mit denselben Fragen kostet damit nur beim ersten Mal Tokens; der
Cache lässt sich an Studierende weitergeben, die dann ohne API-Key arbeiten.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from typesafe_sdk import TypeSafeClient

from .fragen import AKTUELLER_STAND, SCHWERE_STUFEN, fragen, state

CACHE_DATEI = Path(__file__).resolve().parent.parent / "daten" / "cache" / "jev_cache.jsonl"


@dataclass
class Urteil:
    """Alle Antworten von Jev zu einer Meldung, ohne jede Entscheidung."""

    meldung_id: str
    modell: str
    ist_schadensmeldung: float
    kategorie: str
    kategorie_konfidenz: float
    kategorie_wkt: dict[str, float]
    schwere_stufe: str  # gerundeter Erwartungswert, siehe stufe_aus_score()
    schwere_score: float  # Erwartungswert 0..2
    schwere_konfidenz: float
    schwere_wkt: dict[str, float]
    sicherheitsrelevant: float
    personenschaden: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    request_id: str | None = None
    aus_cache: bool = field(default=False, compare=False)


def cache_schluessel(modell: str, st: dict, fr: dict) -> str:
    """Ändert sich Modell, State oder auch nur ein Wort einer Frage, entsteht ein neuer Schlüssel."""
    nutzlast = {
        "modell": modell,
        "state": st,
        "fragen": {k: q.model_dump(mode="json") for k, q in sorted(fr.items())},
    }
    roh = json.dumps(nutzlast, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()


class Cache:
    def __init__(self, datei: Path = CACHE_DATEI):
        self.datei = datei
        self.eintraege: dict[str, dict] = {}
        if datei.exists():
            for zeile in datei.read_text(encoding="utf-8").splitlines():
                if zeile.strip():
                    e = json.loads(zeile)
                    self.eintraege[e["schluessel"]] = e["urteil"]

    def holen(self, schluessel: str) -> dict | None:
        return self.eintraege.get(schluessel)

    def ablegen(self, schluessel: str, urteil: Urteil) -> None:
        daten = asdict(urteil)
        daten.pop("aus_cache")
        self.eintraege[schluessel] = daten
        self.datei.parent.mkdir(parents=True, exist_ok=True)
        with self.datei.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"schluessel": schluessel, "urteil": daten}, ensure_ascii=False) + "\n")


def stufe_aus_score(score: float) -> str:
    """Die Stufe zum gerundeten Erwartungswert, wie es die TypeSafe-Doku für Score empfiehlt.

    Die wahrscheinlichste Stufe allein kann irreführen: Bei 0,18 / 0,39 / 0,43 wäre
    das »fahruntauglich«, der Erwartungswert 1,25 liegt aber bei »mittel«.
    """
    index = int(score + 0.5)  # kaufmännisch runden; round() würde 0,5 auf 0 abrunden
    return SCHWERE_STUFEN[min(max(index, 0), len(SCHWERE_STUFEN) - 1)]


def _aus_antwort(meldung_id: str, antwort) -> Urteil:
    kat = antwort.choices["kategorie"]
    sch = antwort.scores["schwere"]
    # Score-Wahrscheinlichkeiten sind nach Stufenindex (0, 1, 2) geordnet.
    schwere_wkt = {SCHWERE_STUFEN[int(i)]: float(p) for i, p in sch.probabilities.items()}
    try:
        request_id = antwort.request_id
    except Exception:  # z. B. bei Antworten ohne HTTP-Header
        request_id = None
    return Urteil(
        meldung_id=meldung_id,
        modell=antwort.model,
        ist_schadensmeldung=antwort.nouls["ist_schadensmeldung"].noul,
        kategorie=kat.choice,
        kategorie_konfidenz=kat.confidence,
        kategorie_wkt=dict(kat.probabilities),
        schwere_stufe=stufe_aus_score(sch.score),
        schwere_score=sch.score,
        schwere_konfidenz=sch.confidence,
        schwere_wkt=schwere_wkt,
        sicherheitsrelevant=antwort.nouls["sicherheitsrelevant"].noul,
        personenschaden=antwort.nouls["personenschaden"].noul,
        input_tokens=antwort.usage.input_tokens,
        output_tokens=antwort.usage.output_tokens,
        request_id=request_id,
    )


class KeinCacheTreffer(LookupError):
    pass


def beurteilen(
    meldung_id: str,
    text: str,
    typ_code: str,
    *,
    client: TypeSafeClient | None,
    modell: str,
    cache: Cache,
    stand: int = AKTUELLER_STAND,
) -> Urteil:
    """Ein Request je Meldung, fünf Fragen darin. Ohne Client wird nur der Cache gelesen."""
    st = state(text, typ_code)
    fr = fragen(stand)
    schluessel = cache_schluessel(modell, st, fr)

    gespeichert = cache.holen(schluessel)
    if gespeichert is not None:
        # Die Stufe neu ableiten: ältere Cache-Einträge enthalten noch die wahrscheinlichste Stufe.
        gespeichert = {**gespeichert, "meldung_id": meldung_id,
                       "schwere_stufe": stufe_aus_score(gespeichert["schwere_score"])}
        return Urteil(**gespeichert, aus_cache=True)
    if client is None:
        raise KeinCacheTreffer(meldung_id)

    antwort = client.system_one(st, fr, model=modell)
    urteil = _aus_antwort(meldung_id, antwort)
    cache.ablegen(schluessel, urteil)
    return urteil

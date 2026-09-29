"""Eine Attrappe der TypeSafe-API – nur für Tests ohne API-Key.

Sie liest die Soll-Labels aus daten/meldungen.csv und antwortet so, als hätte
Jev (fast) richtig geurteilt. Über das Verhalten von Jev sagt sie nichts aus.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

MELDUNGEN = Path(__file__).resolve().parent.parent / "daten" / "meldungen.csv"


def _soll_nach_text() -> dict[str, dict]:
    with MELDUNGEN.open(encoding="utf-8") as f:
        return {r["text"]: r for r in csv.DictReader(f)}


SOLL = _soll_nach_text()
STUFEN = ["gering", "mittel", "fahruntauglich"]


def antwort(body: dict) -> dict:
    text = body["state"]["meldung"]["text"] if isinstance(body["state"], dict) else body["state"]
    soll = SOLL.get(text)
    zufall = random.Random(text)
    antworten = {}
    for name, frage in body["questions"].items():
        if frage["type"] == "noul":
            ziel = {
                "ist_schadensmeldung": "soll_ist_schaden",
                "sicherheitsrelevant": "soll_sicherheitsrelevant",
                "personenschaden": "soll_personenschaden",
            }.get(name)
            wahr = soll is not None and ziel is not None and soll[ziel] == "1"
            p = zufall.uniform(0.75, 0.97) if wahr else zufall.uniform(0.02, 0.3)
            antworten[name] = {"type": "noul", "noul": round(p, 4)}
        elif frage["type"] == "choice":
            optionen = list(frage["criteria"])
            ziel = soll["soll_kategorie"] if soll and soll["soll_kategorie"] in optionen else optionen[-1]
            spitze = zufall.uniform(0.4, 0.95)
            rest = (1 - spitze) / (len(optionen) - 1)
            wkt = {o: (spitze if o == ziel else rest) for o in optionen}
            n = len(optionen)
            antworten[name] = {"type": "choice", "choice": ziel, "probabilities": wkt,
                               "confidence": round((n * spitze - 1) / (n - 1), 4)}
        else:
            stufen = frage["criteria"]
            ziel = STUFEN.index(soll["soll_schwere"]) if soll and soll["soll_schwere"] else 0
            # Wie bei Jev beobachtet: ein Gipfel, der Rest liegt auf den Nachbarstufen.
            spitze = zufall.uniform(0.7, 0.95)
            nachbarn = [i for i in (ziel - 1, ziel + 1) if 0 <= i < len(stufen)]
            wkt = {str(i): (spitze if i == ziel else (1 - spitze) / len(nachbarn) if i in nachbarn else 0.0)
                   for i in range(len(stufen))}
            antworten[name] = {
                "type": "score",
                "score": sum(i * p for i, p in enumerate(wkt.values())),
                "confidence": round((len(stufen) * spitze - 1) / (len(stufen) - 1), 4),
                "legend": {str(i): s for i, s in enumerate(stufen)},
                "probabilities": wkt,
            }
    return {"model": "attrappe-0.0", "answers": antworten, "usage": {"input_tokens": 300, "output_tokens": 12}}


def transport():
    """httpx2-Transport, der die Attrappe statt der echten API aufruft."""
    import httpx2

    def handler(request):
        if request.url.path.endswith("/systemone"):
            return httpx2.Response(200, json=antwort(json.loads(request.content)),
                                   headers={"x-typesafe-request-id": "attrappe"})
        return httpx2.Response(404, json={"detail": "nicht nachgebildet"})

    return httpx2.MockTransport(handler)

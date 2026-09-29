"""Was aus den Urteilen folgt – ausdrücklich im Code, nicht im Modell.

Jev liefert Wahrscheinlichkeiten und Konfidenzen. Welche Schwelle eine
Sperre auslöst, legt VeloCity fest, abhängig davon, was ein Fehler kostet.
Die Schwellen sind Startwerte zum Ausprobieren, keine Empfehlung.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .fragen import KEINE_ZUORDNUNG
from .pipeline import Urteil

REGEL_VERSION = "2026-09-29.2"

KEIN_SCHADEN = "kein_schaden_weiterleiten"  # an den Kundendienst, kein Werkstattvorgang
SPERREN = "sperren"                       # Rad sofort sperren, Schaden als fahruntauglich melden
PRUEFEN = "pruefen"                       # ein Mensch sieht sich die Meldung an
AUFTRAG = "auftrag"                       # Schaden melden, Wartungsauftrag im normalen Takt

ENTSCHEIDUNGEN = [KEIN_SCHADEN, SPERREN, PRUEFEN, AUFTRAG]


@dataclass(frozen=True)
class Schwellen:
    ist_schaden_ab: float = 0.5          # darunter: keine Schadensmeldung
    sperren_ab: float = 0.8              # Sicherheitsrelevanz, ab der ohne Rückfrage gesperrt wird
    pruefen_ab: float = 0.4              # Sicherheitsrelevanz, ab der ein Mensch draufschaut
    fahruntauglich_konfidenz_ab: float = 0.6  # Score-Konfidenz, damit "fahruntauglich" allein sperrt
    konfidenz_ab: float = 0.5            # Mindestkonfidenz für Kategorie und Schwere
    personenschaden_ab: float = 0.5      # ab hier zusätzlich Eskalation an den Kundendienst

    def als_dict(self) -> dict:
        return asdict(self)


@dataclass
class Entscheidung:
    meldung_id: str
    entscheidung: str
    eskalation: bool
    begruendung: str
    wawi_kategorie: str | None
    wawi_schwere: str | None


def entscheiden(u: Urteil, s: Schwellen = Schwellen()) -> Entscheidung:
    eskalation = u.personenschaden >= s.personenschaden_ab

    def ergebnis(art: str, grund: str, schwere: str | None = None) -> Entscheidung:
        kategorie = None if art == KEIN_SCHADEN else u.kategorie
        return Entscheidung(u.meldung_id, art, eskalation, grund, kategorie, schwere)

    if u.ist_schadensmeldung < s.ist_schaden_ab:
        # Hält Jev das Weiterfahren für gefährlich, obwohl es keinen Schaden erkennt,
        # widersprechen sich zwei Urteile. Dann entscheidet ein Mensch, statt die Meldung
        # an den Kundendienst weiterzuleiten (Iteration 2: Sturz M007 bei 0,45).
        if u.sicherheitsrelevant >= s.pruefen_ab:
            return ergebnis(PRUEFEN, f"Schadensmeldung {u.ist_schadensmeldung:.2f} < {s.ist_schaden_ab}, aber "
                                     f"sicherheitsrelevant {u.sicherheitsrelevant:.2f} ≥ {s.pruefen_ab}",
                            u.schwere_stufe)
        return ergebnis(KEIN_SCHADEN, f"Schadensmeldung {u.ist_schadensmeldung:.2f} < {s.ist_schaden_ab}")

    if u.sicherheitsrelevant >= s.sperren_ab:
        return ergebnis(SPERREN, f"sicherheitsrelevant {u.sicherheitsrelevant:.2f} ≥ {s.sperren_ab}", "fahruntauglich")

    if u.schwere_stufe == "fahruntauglich" and u.schwere_konfidenz >= s.fahruntauglich_konfidenz_ab:
        return ergebnis(SPERREN, f"fahruntauglich mit Konfidenz {u.schwere_konfidenz:.2f}", "fahruntauglich")

    gruende = []
    if u.sicherheitsrelevant >= s.pruefen_ab:
        gruende.append(f"sicherheitsrelevant {u.sicherheitsrelevant:.2f} ≥ {s.pruefen_ab}")
    if u.kategorie == KEINE_ZUORDNUNG:
        gruende.append("keine passende Kategorie")
    if u.kategorie_konfidenz < s.konfidenz_ab:
        gruende.append(f"Kategorie unsicher ({u.kategorie_konfidenz:.2f})")
    if u.schwere_konfidenz < s.konfidenz_ab:
        gruende.append(f"Schwere unsicher ({u.schwere_konfidenz:.2f})")
    if u.schwere_stufe == "fahruntauglich":
        gruende.append("fahruntauglich, aber unsicher")
    if gruende:
        return ergebnis(PRUEFEN, "; ".join(gruende), u.schwere_stufe)

    return ergebnis(AUFTRAG, f"{u.kategorie}, {u.schwere_stufe}", u.schwere_stufe)


def soll_entscheidung(soll_ist_schaden: bool, soll_sicherheitsrelevant: bool, soll_schwere: str | None,
                      soll_kategorie: str | None = None) -> str:
    """Die richtige Entscheidung laut Soll-Labels.

    PRUEFEN ist nur dann das Soll, wenn ein ungefährlicher Schaden keiner Kategorie
    zugeordnet werden kann: Die WaWi braucht eine Kategorie, die dann ein Mensch vergibt.
    """
    if not soll_ist_schaden:
        return KEIN_SCHADEN
    if soll_sicherheitsrelevant or soll_schwere == "fahruntauglich":
        return SPERREN
    if soll_kategorie == KEINE_ZUORDNUNG:
        return PRUEFEN
    return AUFTRAG

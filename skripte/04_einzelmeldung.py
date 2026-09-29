"""Eine einzelne Meldung live beurteilen – für die Vorführung in der Vorlesung.

    python skripte/04_einzelmeldung.py "Bremse hinten quietscht und greift erst ganz spät"
    python skripte/04_einzelmeldung.py --typ EBIKE "Akku wird beim Laden sehr heiß"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typesafe_sdk import TypeSafeClient  # noqa: E402

from velocity_jev.konfig import MODELL, api_key_vorhanden  # noqa: E402
from velocity_jev.pipeline import Cache, beurteilen  # noqa: E402
from velocity_jev.regeln import entscheiden  # noqa: E402


def balken(p: float, breite: int = 20) -> str:
    voll = round(p * breite)
    return "█" * voll + "·" * (breite - voll)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("text")
    p.add_argument("--typ", default="CITY", choices=["CITY", "EBIKE", "CARGO"])
    args = p.parse_args()
    if not api_key_vorhanden():
        sys.exit("TYPESAFE_API_KEY fehlt.")

    with TypeSafeClient(model=MODELL) as client:
        u = beurteilen("LIVE", args.text, args.typ, client=client, modell=MODELL, cache=Cache())
    e = entscheiden(u)

    print(f"\nModell {u.modell}{'  (aus Cache)' if u.aus_cache else ''}\n")
    print("Nouls (Wahrscheinlichkeit für »ja«)")
    for name in ("ist_schadensmeldung", "sicherheitsrelevant", "personenschaden"):
        wert = getattr(u, name)
        print(f"  {name:<20} {balken(wert)} {wert:.2f}")
    print(f"\nKategorie: {u.kategorie}  (Konfidenz {u.kategorie_konfidenz:.2f})")
    for k, w in sorted(u.kategorie_wkt.items(), key=lambda x: -x[1])[:4]:
        print(f"  {k:<20} {balken(w)} {w:.2f}")
    print(f"\nSchwere: {u.schwere_stufe}  (Erwartungswert {u.schwere_score:.2f}, Konfidenz {u.schwere_konfidenz:.2f})")
    for k, w in u.schwere_wkt.items():
        print(f"  {k:<20} {balken(w)} {w:.2f}")
    print(f"\n→ Entscheidung: {e.entscheidung.upper()}{'  + Eskalation Kundendienst' if e.eskalation else ''}")
    print(f"  Begründung: {e.begruendung}")
    if e.wawi_kategorie:
        print(f"  WaWi-Vorschlag: schaden_melden(kategorie={e.wawi_kategorie!r}, schwere={e.wawi_schwere!r})")


if __name__ == "__main__":
    main()

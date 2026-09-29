"""Alle Meldungen eines Datensatzes von Jev beurteilen lassen und entscheiden.

    python skripte/01_klassifizieren.py                     # alle Meldungen, aktueller Fragen-Stand
    python skripte/01_klassifizieren.py --limit 5           # nur die ersten fünf (zum Ausprobieren)
    python skripte/01_klassifizieren.py --stand 0           # Fragen der Übergabe (liegen im Cache)
    python skripte/01_klassifizieren.py --nur-cache         # ohne API-Key, nur gespeicherte Antworten
    python skripte/01_klassifizieren.py --datensatz holdout # erst ganz am Ende, siehe docs/iterationen.md

Ergebnis: ergebnisse/urteile.csv, ergebnisse/lauf.json und ein eigener Ordner ergebnisse/laeufe/<lauf_id>/
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
from typesafe_sdk import TypeSafeClient  # noqa: E402

from velocity_jev.ablauf import klassifizieren  # noqa: E402
from velocity_jev.fragen import AKTUELLER_STAND, STAENDE  # noqa: E402
from velocity_jev.konfig import DATENSAETZE, ERGEBNISSE, MODELL, api_key_vorhanden  # noqa: E402
from velocity_jev.protokoll import lauf_ablegen  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--nur-cache", action="store_true", help="keine API-Aufrufe, nur Cache")
    p.add_argument("--modell", default=MODELL)
    p.add_argument("--stand", type=int, default=AKTUELLER_STAND, choices=sorted(STAENDE))
    p.add_argument("--datensatz", default="meldungen", choices=sorted(DATENSAETZE))
    p.add_argument("--anmerkung", default=None)
    args = p.parse_args()

    meldungen = pd.read_csv(DATENSAETZE[args.datensatz], dtype={"meldung_id": str})
    if args.limit:
        meldungen = meldungen.head(args.limit)

    client = None
    if not args.nur_cache:
        if not api_key_vorhanden():
            sys.exit("TYPESAFE_API_KEY fehlt. Mit --nur-cache geht es ohne Key, sofern ein Cache vorliegt.")
        client = TypeSafeClient(model=args.modell)

    print(f"Datensatz {args.datensatz}, Fragen-Stand {args.stand}: {STAENDE[args.stand]}\n")
    urteile, lauf = klassifizieren(meldungen, client=client, modell=args.modell, stand=args.stand,
                                   datensatz=args.datensatz, anmerkung=args.anmerkung)
    if client is not None:
        client.close()

    ordner = lauf_ablegen(ERGEBNISSE, lauf, urteile)
    print(f"\n{lauf['meldungen']} Meldungen beurteilt, davon {lauf['neue_requests']} neu an Jev "
          f"({lauf['input_tokens']} Input-, {lauf['output_tokens']} Output-Tokens).")
    print(f"Lauf {lauf['lauf_id']} → {ordner.relative_to(ERGEBNISSE.parent)}")
    if lauf["ohne_urteil"]:
        print(f"Ohne Urteil: {lauf['ohne_urteil']}")


if __name__ == "__main__":
    main()

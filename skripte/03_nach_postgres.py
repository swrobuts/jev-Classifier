"""Läufe nach PostgreSQL/Supabase schreiben (Schema jev_labor) und für die Warenwirtschaft freigeben.

    python skripte/03_nach_postgres.py                                  # letzter Lauf aus ergebnisse/lauf.json
    python skripte/03_nach_postgres.py --lauf 20260929-083904_meldungen_stand1 --freigeben
    python skripte/03_nach_postgres.py --alle                           # jeden Lauf unter ergebnisse/laeufe/
    python skripte/03_nach_postgres.py --schema-anlegen                 # nur auf einer eigenen Datenbank

Braucht DATABASE_URL in der .env. Für die VeloCity-Datenbank ist das die Rolle
jev_schreiber, die nur in jev_labor einfügen darf; ihr Schema legt
velocity-fallstudie/db/aufbau/0026_jev_meldungseingang.sql an. --schema-anlegen
ist für eine eigene Datenbank ohne Warenwirtschaft gedacht und braucht dort
das Recht, Tabellen anzulegen. Ein Lauf, der schon in der Datenbank steht,
wird nicht doppelt geschrieben.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import psycopg  # noqa: E402

from velocity_jev.datenbank import lauf_hochladen  # noqa: E402
from velocity_jev.konfig import DATENSAETZE, ERGEBNISSE, WURZEL  # noqa: E402


def lauf_lesen(ordner: Path) -> tuple[dict, pd.DataFrame]:
    """lauf.json und urteile.csv eines Laufordners lesen."""
    lauf = json.loads((ordner / "lauf.json").read_text(encoding="utf-8"))
    urteile = pd.read_csv(ordner / "urteile.csv", dtype={"meldung_id": str})
    return lauf, urteile


def laufordner_waehlen(args) -> list[Path]:
    """Welche Läufe hochgeladen werden: einer, alle oder der zuletzt gerechnete."""
    laeufe = ERGEBNISSE / "laeufe"
    if args.alle:
        return sorted(p for p in laeufe.iterdir() if (p / "lauf.json").exists())
    if args.lauf:
        return [laeufe / args.lauf]
    letzter = json.loads((ERGEBNISSE / "lauf.json").read_text(encoding="utf-8"))
    return [laeufe / letzter["lauf_id"]]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--lauf", default=None, help="Name des Laufordners unter ergebnisse/laeufe/")
    p.add_argument("--alle", action="store_true", help="jeden Lauf unter ergebnisse/laeufe/ hochladen")
    p.add_argument("--freigeben", action="store_true", help="den Lauf in der Warenwirtschaft zeigen")
    p.add_argument("--schema-anlegen", action="store_true", help="sql/01_schema.sql vorher ausführen")
    args = p.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url or "USER:PASSWORT" in url:
        sys.exit("DATABASE_URL fehlt in der .env.")
    if args.alle and args.freigeben:
        sys.exit("--freigeben nur zusammen mit einem einzelnen Lauf.")

    if args.schema_anlegen:
        with psycopg.connect(url) as conn:
            conn.execute((WURZEL / "sql" / "01_schema.sql").read_text(encoding="utf-8"))

    for ordner in laufordner_waehlen(args):
        if not (ordner / "lauf.json").exists():
            sys.exit(f"Lauf {ordner.name} nicht gefunden.")
        lauf, urteile = lauf_lesen(ordner)
        meldungen = pd.read_csv(DATENSAETZE[lauf.get("datensatz", "meldungen")], dtype={"meldung_id": str})
        ergebnis = lauf_hochladen(url, lauf, urteile, meldungen, freigeben=args.freigeben)
        stand = "neu geschrieben" if ergebnis["neu"] else "war schon vorhanden"
        print(f"{ordner.name}: Lauf {ergebnis['lauf_id']} {stand}, {ergebnis['urteile']} Urteile"
              f"{', freigegeben' if ergebnis['freigegeben'] else ''}")


if __name__ == "__main__":
    main()

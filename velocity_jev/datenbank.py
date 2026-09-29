"""Läufe nach PostgreSQL/Supabase schreiben, in das Schema jev_labor.

Geschrieben wird mit der Rolle jev_schreiber, die nur in jev_labor einfügen
darf; die Verbindung steht in DATABASE_URL (siehe .env.example). Ein Lauf ist
über seinen Schlüssel eindeutig, den Namen seines Ordners unter
ergebnisse/laeufe/. Ein zweiter Upload desselben Laufs ändert deshalb nichts.

In der Warenwirtschaft erscheint nur ein freigegebener Lauf, und zwar der
zuletzt freigegebene (Sicht velocity.v_wawi_meldungseingang).
"""

from __future__ import annotations

import json

import pandas as pd
import psycopg
from psycopg.types.json import Jsonb

MELDUNG_SQL = """
insert into jev_labor.meldung (meldung_id, fahrrad_id, rahmennummer, typ_code, kanal, text, soll_kategorie,
    soll_schwere, soll_sicherheitsrelevant, soll_personenschaden, soll_ist_schaden, merkmal)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict (meldung_id) do update set
    fahrrad_id = excluded.fahrrad_id, rahmennummer = excluded.rahmennummer, typ_code = excluded.typ_code,
    kanal = excluded.kanal, text = excluded.text, soll_kategorie = excluded.soll_kategorie,
    soll_schwere = excluded.soll_schwere, soll_sicherheitsrelevant = excluded.soll_sicherheitsrelevant,
    soll_personenschaden = excluded.soll_personenschaden, soll_ist_schaden = excluded.soll_ist_schaden,
    merkmal = excluded.merkmal
"""

LAUF_SQL = """
insert into jev_labor.lauf (lauf_schluessel, zeitpunkt, datensatz, modell, fragen_stand, fragen_fingerabdruck,
    regel_version, schwellen, input_tokens, output_tokens, anmerkung)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
returning lauf_id
"""

URTEIL_SPALTEN = [
    "meldung_id", "modell", "ist_schadensmeldung", "kategorie", "kategorie_konfidenz", "kategorie_wkt",
    "schwere_stufe", "schwere_score", "schwere_konfidenz", "schwere_wkt", "sicherheitsrelevant",
    "personenschaden", "entscheidung", "eskalation", "begruendung", "wawi_kategorie", "wawi_schwere",
    "input_tokens", "output_tokens", "request_id",
]


def leer_zu_none(wert):
    """Leere Zellen aus pandas (NaN, leerer Text) werden in der Datenbank zu NULL."""
    return None if pd.isna(wert) or wert == "" else wert


def meldungen_schreiben(cur, meldungen: pd.DataFrame) -> int:
    """Meldungen mit Soll-Labels einfügen oder auf den Stand der CSV-Datei bringen."""
    cur.executemany(MELDUNG_SQL, [
        (r.meldung_id, int(r.fahrrad_id), r.rahmennummer, r.typ_code, r.kanal, r.text, r.soll_kategorie,
         leer_zu_none(r.soll_schwere), bool(r.soll_sicherheitsrelevant), bool(r.soll_personenschaden),
         bool(r.soll_ist_schaden), leer_zu_none(r.merkmal))
        for r in meldungen.itertuples(index=False)
    ])
    return len(meldungen)


def lauf_anlegen(cur, lauf: dict) -> tuple[int, bool]:
    """Den Lauf anlegen oder, wenn es ihn schon gibt, seine Nummer zurückgeben. Liefert (lauf_id, neu)."""
    cur.execute("select lauf_id from jev_labor.lauf where lauf_schluessel = %s", (lauf["lauf_id"],))
    vorhanden = cur.fetchone()
    if vorhanden:
        return vorhanden[0], False
    cur.execute(LAUF_SQL, (
        lauf["lauf_id"], lauf["zeitpunkt"], lauf.get("datensatz"), lauf["modell"], lauf.get("fragen_stand"),
        lauf.get("fragen_fingerabdruck"), lauf["regel_version"], Jsonb(lauf["schwellen"]),
        lauf.get("input_tokens"), lauf.get("output_tokens"), lauf.get("anmerkung"),
    ))
    return cur.fetchone()[0], True


def urteile_schreiben(cur, lauf_id: int, urteile: pd.DataFrame) -> int:
    """Die Urteile eines Laufs einfügen, eine Zeile je Meldung."""
    zeilen = []
    for r in urteile[URTEIL_SPALTEN].to_dict("records"):
        werte = {k: leer_zu_none(v) for k, v in r.items()}
        werte["kategorie_wkt"] = Jsonb(json.loads(r["kategorie_wkt"]))
        werte["schwere_wkt"] = Jsonb(json.loads(r["schwere_wkt"]))
        werte["eskalation"] = bool(r["eskalation"])
        for k in ("input_tokens", "output_tokens"):
            werte[k] = None if werte[k] is None else int(werte[k])
        zeilen.append((lauf_id, *(werte[k] for k in URTEIL_SPALTEN)))
    platzhalter = ", ".join(["%s"] * (len(URTEIL_SPALTEN) + 1))
    cur.executemany(
        f"insert into jev_labor.urteil (lauf_id, {', '.join(URTEIL_SPALTEN)}) values ({platzhalter})",
        zeilen,
    )
    return len(zeilen)


def lauf_freigeben(cur, lauf_id: int) -> None:
    """Den Lauf für die Warenwirtschaft freigeben; dort erscheint der zuletzt freigegebene."""
    cur.execute("update jev_labor.lauf set freigegeben_am = now() where lauf_id = %s", (lauf_id,))


def lauf_hochladen(url: str, lauf: dict, urteile: pd.DataFrame, meldungen: pd.DataFrame,
                   freigeben: bool = False) -> dict:
    """Meldungen, Lauf und Urteile in einer Transaktion schreiben, auf Wunsch freigeben."""
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        meldungen_schreiben(cur, meldungen)
        lauf_id, neu = lauf_anlegen(cur, lauf)
        anzahl = urteile_schreiben(cur, lauf_id, urteile) if neu else 0
        if freigeben:
            lauf_freigeben(cur, lauf_id)
    return {"lauf_id": lauf_id, "neu": neu, "urteile": anzahl, "freigegeben": freigeben}

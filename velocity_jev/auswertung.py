"""Urteile mit den Soll-Labels vergleichen und Kennzahlen berechnen.

Die Funktionen werden von skripte/02_auswerten.py und vom Notebook
VeloCity_Jev.ipynb gemeinsam genutzt, damit beide dieselben Zahlen zeigen.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pandas as pd

from .pipeline import Urteil
from .regeln import AUFTRAG, KEIN_SCHADEN, PRUEFEN, SPERREN, Schwellen, entscheiden, soll_entscheidung

# Annahmen für die Kostenrechnung – bewusst grob, zum Diskutieren gedacht.
KOSTEN = {
    "sicherheitsschaden_uebersehen": 500.0,  # Rad bleibt im Verleih, Unfallrisiko, Haftung
    "unnoetig_gesperrt": 20.0,              # entgangene Fahrten, Werkstattgang ohne Befund
    "menschliche_pruefung": 8.0,            # Arbeitszeit Disposition
    "sonstige_fehlentscheidung": 30.0,      # z. B. Werkstattauftrag für eine Abrechnungsfrage
}

STUFEN = {"gering": 0, "mittel": 1, "fahruntauglich": 2}

NOUL_FRAGEN = {
    "ist_schadensmeldung": "soll_ist_schaden",
    "sicherheitsrelevant": "soll_sicherheitsrelevant",
    "personenschaden": "soll_personenschaden",
}


def vergleich_bauen(meldungen: pd.DataFrame, urteile: pd.DataFrame) -> pd.DataFrame:
    """Meldungen mit Soll-Labels und Urteile von Jev in einer Tabelle zusammenführen."""
    df = meldungen.merge(urteile, on="meldung_id", how="inner")
    df["soll_schwere"] = df["soll_schwere"].fillna("")
    for spalte in ("soll_sicherheitsrelevant", "soll_personenschaden", "soll_ist_schaden"):
        df[spalte] = df[spalte].astype(bool)
    df["soll_entscheidung"] = [
        soll_entscheidung(r.soll_ist_schaden, r.soll_sicherheitsrelevant, r.soll_schwere or None, r.soll_kategorie)
        for r in df.itertuples()
    ]
    df["ergebnis"] = [ergebnis_art(i, s) for i, s in zip(df.entscheidung, df.soll_entscheidung)]
    return df


def ergebnis_art(ist: str, soll: str) -> str:
    """Ordnet eine Entscheidung einer von fünf Klassen zu, die sich gut gruppieren lassen."""
    if ist == soll:
        return "richtig"
    if soll == SPERREN and ist in (AUFTRAG, KEIN_SCHADEN):
        return "Sicherheitsschaden übersehen"
    if ist == SPERREN:
        return "unnötig gesperrt"
    if ist == PRUEFEN:
        return "unnötig geprüft"
    return "sonstige Fehlentscheidung"


def als_urteil(r) -> Urteil:
    """Eine Zeile der Vergleichstabelle zurück in ein Urteil verwandeln, um Schwellen neu anzuwenden."""
    return Urteil(
        meldung_id=r.meldung_id, modell=r.modell, ist_schadensmeldung=r.ist_schadensmeldung,
        kategorie=r.kategorie, kategorie_konfidenz=r.kategorie_konfidenz,
        kategorie_wkt=json.loads(r.kategorie_wkt), schwere_stufe=r.schwere_stufe,
        schwere_score=r.schwere_score, schwere_konfidenz=r.schwere_konfidenz,
        schwere_wkt=json.loads(r.schwere_wkt), sicherheitsrelevant=r.sicherheitsrelevant,
        personenschaden=r.personenschaden,
    )


def kosten(ist: str, soll: str) -> float:
    """Kosten einer einzelnen Entscheidung nach den Annahmen in KOSTEN."""
    if ist == PRUEFEN:
        return KOSTEN["menschliche_pruefung"]
    if ist == soll:
        return 0.0
    if soll == SPERREN:
        return KOSTEN["sicherheitsschaden_uebersehen"]
    if ist == SPERREN:
        return KOSTEN["unnoetig_gesperrt"]
    return KOSTEN["sonstige_fehlentscheidung"]


def entscheidungs_kennzahlen(ist: pd.Series, soll: pd.Series) -> dict:
    """Kennzahlen der Entscheidungen: Automatisierung, Fehler, übersehene Schäden, Kosten."""
    auto = ist != PRUEFEN
    return {
        "richtig": float((ist == soll).mean()),
        "automatisiert": float(auto.mean()),
        "fehler_unter_automatischen": float(((ist != soll) & auto).sum() / max(auto.sum(), 1)),
        "sicherheitsschaden_uebersehen": int(((soll == SPERREN) & ist.isin([AUFTRAG, KEIN_SCHADEN])).sum()),
        "unnoetig_gesperrt": int(((ist == SPERREN) & (soll != SPERREN)).sum()),
        "unnoetig_geprueft": int(((ist == PRUEFEN) & (soll != PRUEFEN)).sum()),
        "kosten_gesamt": float(sum(kosten(i, s) for i, s in zip(ist, soll))),
    }


def brier(p: pd.Series, y: pd.Series) -> float:
    """Mittlerer quadratischer Abstand zwischen Wahrscheinlichkeit und Wahrheit (0 = perfekt)."""
    return float(((p - y.astype(float)) ** 2).mean())


def noul_basis(df: pd.DataFrame, frage: str) -> pd.DataFrame:
    """Sicherheitsrelevanz wird nur an echten Schadensmeldungen gemessen, die anderen Nouls an allen."""
    return df[df.soll_ist_schaden] if frage == "sicherheitsrelevant" else df


def alle_kennzahlen(df: pd.DataFrame) -> dict:
    """Alle Kennzahlen eines Laufs in einem flachen Wörterbuch, eine Zeile in laeufe.csv."""
    schaden = df[df.soll_ist_schaden]
    abstand = (schaden.schwere_stufe.map(STUFEN) - schaden.soll_schwere.map(STUFEN)).abs()
    k = {
        "meldungen": len(df),
        "kategorie_treffer": float((schaden.kategorie == schaden.soll_kategorie).mean()),
        "schwere_exakt": float((abstand == 0).mean()),
        "schwere_eine_stufe_daneben": float((abstand == 1).mean()),
    }
    for frage, soll in NOUL_FRAGEN.items():
        basis = noul_basis(df, frage)
        k[f"{frage}_richtig"] = float(((basis[frage] >= 0.5) == basis[soll]).mean())
        k[f"{frage}_brier"] = brier(basis[frage], basis[soll])
    k.update(entscheidungs_kennzahlen(df.entscheidung, df.soll_entscheidung))
    return k


def kennzahlen_tabelle(k: dict) -> pd.DataFrame:
    """Die Kennzahlen als zweispaltige Tabelle mit lesbaren Namen, für das Notebook."""
    namen = {
        "meldungen": "Meldungen",
        "kategorie_treffer": "Kategorie richtig",
        "schwere_exakt": "Schwere exakt",
        "schwere_eine_stufe_daneben": "Schwere eine Stufe daneben",
        "ist_schadensmeldung_richtig": "ist_schadensmeldung richtig (Schwelle 0,5)",
        "ist_schadensmeldung_brier": "ist_schadensmeldung Brier-Score",
        "sicherheitsrelevant_richtig": "sicherheitsrelevant richtig (Schwelle 0,5)",
        "sicherheitsrelevant_brier": "sicherheitsrelevant Brier-Score",
        "personenschaden_richtig": "personenschaden richtig (Schwelle 0,5)",
        "personenschaden_brier": "personenschaden Brier-Score",
        "richtig": "Entscheidung richtig",
        "automatisiert": "automatisch entschieden",
        "fehler_unter_automatischen": "Fehler unter den automatischen",
        "sicherheitsschaden_uebersehen": "Sicherheitsschäden übersehen",
        "unnoetig_gesperrt": "unnötig gesperrt",
        "unnoetig_geprueft": "unnötig geprüft",
        "kosten_gesamt": "Kosten nach Annahmen (€)",
    }
    return pd.DataFrame({"Kennzahl": [namen[s] for s in namen], "Wert": [k[s] for s in namen]})


def schwellen_durchspielen(df: pd.DataFrame) -> pd.DataFrame:
    """Sperr- und Prüfschwelle variieren und Kennzahlen je Kombination berechnen, ohne API-Aufrufe."""
    urteile = [als_urteil(r) for r in df.itertuples()]
    basis = Schwellen()
    zeilen = []
    for sperren_ab in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
        for pruefen_ab in [0.1, 0.2, 0.3, 0.4, 0.5]:
            if pruefen_ab >= sperren_ab:
                continue
            s = replace(basis, sperren_ab=sperren_ab, pruefen_ab=pruefen_ab)
            ist = pd.Series([entscheiden(u, s).entscheidung for u in urteile], index=df.index)
            zeilen.append({"sperren_ab": sperren_ab, "pruefen_ab": pruefen_ab,
                           **entscheidungs_kennzahlen(ist, df.soll_entscheidung)})
    return pd.DataFrame(zeilen).sort_values("kosten_gesamt")


def gruppiert(df: pd.DataFrame, nach: str) -> pd.DataFrame:
    """Anzahl, Trefferquote und Fehlerarten je Gruppe, etwa je merkmal, typ_code oder soll_kategorie."""
    hilfe = df.assign(
        entscheidung_richtig=df.entscheidung == df.soll_entscheidung,
        sicherheitsschaden_uebersehen=df.ergebnis == "Sicherheitsschaden übersehen",
        unnoetig_gesperrt=df.ergebnis == "unnötig gesperrt",
        unnoetig_geprueft=df.ergebnis == "unnötig geprüft",
        sonstige_fehler=df.ergebnis == "sonstige Fehlentscheidung",
    )
    tabelle = hilfe.groupby(nach).agg(
        meldungen=("meldung_id", "count"),
        entscheidung_richtig=("entscheidung_richtig", "mean"),
        sicherheitsschaden_uebersehen=("sicherheitsschaden_uebersehen", "sum"),
        unnoetig_gesperrt=("unnoetig_gesperrt", "sum"),
        unnoetig_geprueft=("unnoetig_geprueft", "sum"),
        sonstige_fehler=("sonstige_fehler", "sum"),
        mittel_sicherheitsrelevant=("sicherheitsrelevant", "mean"),
        mittel_ist_schadensmeldung=("ist_schadensmeldung", "mean"),
    )
    return tabelle.sort_values("entscheidung_richtig").round(2).reset_index()

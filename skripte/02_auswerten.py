"""Urteile des letzten Laufs mit den Soll-Labels vergleichen und Schwellen durchspielen.

    python skripte/02_auswerten.py

Liest ergebnisse/urteile.csv und ergebnisse/lauf.json (aus 01_klassifizieren.py).
Schreibt vergleich.csv und kennzahlen.json in den Lauf-Ordner, erneuert
ergebnisse/laeufe.csv, ergebnisse/urteile_lang.csv und ergebnisse/schwellen.csv.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from velocity_jev.auswertung import (  # noqa: E402
    NOUL_FRAGEN, STUFEN, alle_kennzahlen, noul_basis, schwellen_durchspielen, vergleich_bauen,
)
from velocity_jev.konfig import DATENSAETZE, ERGEBNISSE  # noqa: E402
from velocity_jev.protokoll import auswertung_ablegen  # noqa: E402
from velocity_jev.regeln import PRUEFEN  # noqa: E402

UEBERSCHRIFT = "\n{}\n" + "─" * 60


def main() -> None:
    lauf_datei, urteil_datei = ERGEBNISSE / "lauf.json", ERGEBNISSE / "urteile.csv"
    if not (lauf_datei.exists() and urteil_datei.exists()):
        sys.exit("ergebnisse/urteile.csv fehlt – zuerst skripte/01_klassifizieren.py ausführen.")
    lauf = json.loads(lauf_datei.read_text(encoding="utf-8"))
    meldungen = pd.read_csv(DATENSAETZE[lauf.get("datensatz", "meldungen")], dtype={"meldung_id": str})
    df = vergleich_bauen(meldungen, pd.read_csv(urteil_datei, dtype={"meldung_id": str}))
    k = alle_kennzahlen(df)
    schaden = df[df.soll_ist_schaden]
    print(f"Lauf {lauf['lauf_id']}: {len(df)} Meldungen, davon {len(schaden)} echte Schadensmeldungen")

    print(UEBERSCHRIFT.format("Kategorie (Choice)"))
    print(f"Trefferquote: {k['kategorie_treffer']:.0%}")
    for r in schaden[schaden.kategorie != schaden.soll_kategorie].itertuples():
        print(f"  {r.meldung_id}: {r.soll_kategorie} → {r.kategorie} (Konf. {r.kategorie_konfidenz:.2f})  [{r.merkmal}]")

    print(UEBERSCHRIFT.format("Schwere (Score, gerundeter Erwartungswert)"))
    print(f"Exakt: {k['schwere_exakt']:.0%}   eine Stufe daneben: {k['schwere_eine_stufe_daneben']:.0%}")
    reihenfolge = list(STUFEN)
    print(pd.crosstab(schaden.soll_schwere, schaden.schwere_stufe, rownames=["soll"], colnames=["Jev"])
          .reindex(index=reihenfolge, columns=reihenfolge, fill_value=0))

    print(UEBERSCHRIFT.format("Ja/Nein-Urteile (Noul) bei Schwelle 0,5"))
    for frage, soll in NOUL_FRAGEN.items():
        basis = noul_basis(df, frage)
        print(f"{frage:<20} richtig {k[frage + '_richtig']:.0%}   Brier-Score {k[frage + '_brier']:.3f}")
        for r in basis[(basis[frage] >= 0.5) != basis[soll]].itertuples():
            print(f"    {r.meldung_id}: p={getattr(r, frage):.2f}, soll={getattr(r, soll)}  [{r.merkmal}]")

    print(UEBERSCHRIFT.format("Entscheidungen mit den Standard-Schwellen"))
    print(pd.crosstab(df.soll_entscheidung, df.entscheidung, rownames=["soll"], colnames=["Code"]))
    print(f"\nRichtig: {k['richtig']:.0%}   Automatisch entschieden: {k['automatisiert']:.0%}   "
          f"Fehler darunter: {k['fehler_unter_automatischen']:.0%}")
    print(f"Übersehene Sicherheitsschäden: {k['sicherheitsschaden_uebersehen']}   "
          f"Unnötige Sperren: {k['unnoetig_gesperrt']}   Unnötige Prüfungen: {k['unnoetig_geprueft']}   "
          f"Kosten (Annahmen): {k['kosten_gesamt']:.0f} €")
    for r in df[(df.entscheidung != df.soll_entscheidung) & (df.entscheidung != PRUEFEN)].itertuples():
        print(f"  {r.meldung_id}: soll {r.soll_entscheidung}, Code {r.entscheidung} – {r.begruendung}  [{r.merkmal}]")

    print(UEBERSCHRIFT.format("Schwellen durchspielen (ohne neue API-Aufrufe)"))
    tabelle = schwellen_durchspielen(df)
    print(tabelle.head(8).to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\nDie günstigste Kombination hängt an den Kostenannahmen in velocity_jev/auswertung.py.")

    tabelle.to_csv(ERGEBNISSE / "schwellen.csv", index=False)
    auswertung_ablegen(ERGEBNISSE, lauf, df, k)
    print(f"\nLauf {lauf['lauf_id']} ({lauf['modell']}, Fragen-Stand {lauf.get('fragen_stand', '?')}): "
          f"{lauf['neue_requests']} neue Requests, {lauf['input_tokens']} Input- / {lauf['output_tokens']} Output-Tokens")


if __name__ == "__main__":
    main()

# CLAUDE.md – VeloCity × Jev

Lehrprojekt für die Veranstaltung „Datenbasierte Fallstudien“ an der THWS Business School. Die Schadenmeldungen des fiktiven Leihradsystems VeloCity Würzburg werden mit Jev (TypeSafe System One) beurteilt, und Code entscheidet anhand von Schwellen. Aufbau, Befehle und Übungsideen stehen in `README.md`; bitte zuerst lesen.

## Stand der Übergabe

- Stand 29.09.2026: Schritte 1 bis 6 sind erledigt. Erster echter Lauf, Fehleranalyse (`docs/fehleranalyse_stand0.csv`), zwei Iterationen und ein Holdout sind in `docs/iterationen.md` protokolliert. Bester Fragen-Stand ist 1; Stand 2 wurde verworfen.
- Die API kennt das Modell nur als `jev-1.13.0`, nicht als `jev-1.13`.
- Der Cache enthält 180 Antworten (48 Meldungen × Stand 0, 1, 2 und 18 Holdout-Meldungen × Stand 0, 1).
- `VeloCity_Jev.ipynb` läuft in Deepnote und Jupyter, ohne Key nur aus dem Cache.
- Schritt 8 ist erledigt: Die WaWi prüft Kategorien nicht gegen eine feste Liste (`schadensmeldung.kategorie` ist Freitext, siehe `velocity-fallstudie/db/aufbau/0015_bereich_i_instandhaltung.sql`).
- WaWi-Anbindung live seit 29.09.2026: `velocity-fallstudie/db/aufbau/0026_jev_meldungseingang.sql` (Schema `jev_labor`, Rolle `jev_schreiber`, Sicht `v_wawi_meldungseingang`, zwei `api_`-Funktionen) und der Reiter „Meldungseingang“ in der Instandhaltung (in velocity-fallstudie nach `main` gemergt und gepusht, Commit 0b6cdde). Alle fünf Läufe liegen in `jev_labor`; freigegeben ist Lauf 14 (Meldungen, Stand 1).
- `tests/attrappe.py` sagt nichts über Jev aus; Aussagen zur Qualität stammen aus den echten Läufen.
- Foliensatz in `folien/` (40 Folien, erzeugt mit `folien/folien_bauen.py` und dem Skill thws-slides); die PDF
  exportiert PowerPoint per AppleScript direkt nach `folien/` (in diesen OneDrive-Ordner darf PowerPoint schreiben,
  in `/private/tmp` nicht ohne Rückfrage). LibreOffice setzt die Titelschrift GT Planar Medium fehlerhaft und taugt
  nur zur Layoutprüfung.

## Regeln

- **API-Key:** steht nur in `.env` und wird nie ausgegeben, geloggt, committet oder in den Chat kopiert. Fehlt er, den Nutzer bitten, ihn selbst in die `.env` einzutragen.
- **Git:** `jev/` ist ein eigenes Repository (github.com/swrobuts/jev-Classifier, privat). `.env`, `.venv/`, `ergebnisse/`, `folien/` und ZIP-Pakete sind ausgeschlossen; der Foliensatz gehört nicht nach GitHub. Vor jedem Commit prüfen, dass weder API-Key noch Datenbankpasswort in einer Datei stehen (`git grep --cached -F -e "<Wert>"`; das Passwort kann mit einem Bindestrich beginnen, deshalb `-e`).
- **Virtuelle Umgebung außerhalb von OneDrive:** Der Projektordner liegt in OneDrive, dort würde eine `.venv` tausendfach synchronisiert. Deshalb `~/.virtualenvs/velocity-jev` verwenden.
- **Modell:** fest `jev-1.13.0` (Variable `JEV_MODELL`), nicht `jev-latest`. Das Modell ist Teil des Cache-Schlüssels.
- **Cache:** `daten/cache/jev_cache.jsonl` wird nie gelöscht. Er soll später an die Studierenden gehen. Jede Änderung am Wortlaut einer Frage erzeugt neue Requests und kostet Tokens. Nach jedem Lauf die Token-Summe nennen.
- **Warenwirtschaft:** Nicht automatisch in die VeloCity-WaWi schreiben, also kein `schaden_melden`, kein `rad_status_setzen`. Lesen ist erlaubt.
- **Datenbank:** SQL ausschließlich für PostgreSQL/Supabase. Geschrieben wird nur mit der Rolle `jev_schreiber` (`DATABASE_URL` in `.env`), die nur in `jev_labor` einfügen und Läufe freigeben darf. Einen Lauf freigeben heißt, dass die Werkstatt ihn in der WaWi sieht: vorher mit dem Nutzer absprechen.
- **Soll-Labels:** in `daten/meldungen.csv` nicht eigenmächtig ändern. Hält Claude ein Label für falsch, begründet es den Vorschlag und fragt nach.
- **Kein Overfitting:** Schwellen und Fragen nicht so lange drehen, bis die 48 Meldungen passen. Wer ernsthaft optimiert, schlägt vorher einen Holdout vor, etwa neue Meldungen, die erst am Ende laufen.
- **Code-Ausgabe:** Geänderte Dateien immer vollständig ausgeben, keine Diffs und keine Ausschnitte.
- **Sprache im Lehrmaterial:** Etablierte englische Fachbegriffe bleiben englisch (Prompt Injection, Edge Cases, Threshold, Confidence). Keine Zeitschätzungen für Arbeitsschritte.
- **Kritisch mitdenken:** Vorschläge des Nutzers nicht einfach umsetzen, sondern prüfen und begründet widersprechen, wenn es eine bessere Lösung gibt.

## Arbeitsplan

1. **Umgebung einrichten.** Virtuelle Umgebung außerhalb von OneDrive anlegen, dann `pip install -r requirements.txt` und `python -m pytest`.
2. **Verbindung prüfen.** `.env` aus `.env.example` anlegen lassen; der Nutzer trägt den Key selbst ein. Dann `python skripte/00_verbindung_pruefen.py`. Wenn `jev-1.13` in der Modellliste fehlt, das tatsächlich verfügbare Modell mit festem Namen in `.env` setzen.
3. **Erster kleiner Lauf.** `python skripte/01_klassifizieren.py --limit 5`. Die Antworten ansehen: Sind die Wahrscheinlichkeiten plausibel, und kommen die Score-Stufen in der richtigen Reihenfolge an (`gering`, `mittel`, `fahruntauglich`)?
4. **Voller Lauf.** `01_klassifizieren.py` ohne Limit, danach `02_auswerten.py`.
5. **Fehleranalyse.** Jede Fehlentscheidung einer von vier Ursachen zuordnen:
   - Die Frage ist unklar formuliert. Jev liest wörtlich.
   - Das Soll-Label ist strittig.
   - Es handelt sich um eine bekannte Grenze von Jev, etwa Verneinung, Steuerversuch oder Prompt Injection.
   - Es ist ein Fehler im Code.

   Das Ergebnis nach Spalte `merkmal` gruppieren.
6. **Fragen gezielt nachschärfen.** Neue Fragen als neuen Stand in `fragen.py` anlegen, alte Stände nicht überschreiben. Jede Iteration in `docs/iterationen.md` festhalten: alte Formulierung, neue Formulierung, Wirkung auf die Kennzahlen, Tokens. Nicht mehrere Fragen gleichzeitig ändern.
7. **Sprachexperiment.** Deutsche und englische `instructions` vergleichen. Die Meldungstexte bleiben dabei deutsch. Die Umschaltung über einen Parameter in `fragen.py` lösen, sodass beide Varianten im Cache nebeneinander liegen.
8. **Kategorien der WaWi abgleichen.** Klären, ob die WaWi Kategorien gegen eine feste Liste prüft. Neun Kategorien aus `fragen.py` kommen in den bisherigen WaWi-Meldungen nicht vor. Nur lesend prüfen und die Lösung mit dem Nutzer absprechen.
9. **Kurzbericht.** Kennzahlen des besten Stands, die wichtigsten Fehlermuster und was davon für die Vorlesung taugt, etwa als Beispiele für Folien oder Übungen.

## Nützliche Stellen

- Jev-Dokumentation: https://docs.typesafe.ai/llms.txt (Index), insbesondere `model-jaggedness/jev-1.13.md` und `confidence.md`
- Skill `typesafe-ai`, falls installiert
- VeloCity-WaWi (lesend): Sichten `v_wawi_schaden`, `v_wawi_flotte`, `v_wawi_modell`

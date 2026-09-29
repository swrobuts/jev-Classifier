# VeloCity × Jev – Schadenmeldungen beurteilen

Kundinnen und Kunden von VeloCity Würzburg melden Schäden in freier Sprache. Die Warenwirtschaft braucht aber Kategorie und Schwere, um Räder zu sperren und Wartungsaufträge anzulegen. Dieses Projekt schließt die Lücke mit **Jev**, dem System-One-Modell von TypeSafe: Jev liefert zu jeder Meldung typisierte Urteile mit Wahrscheinlichkeiten, und der Code entscheidet nach ausdrücklich formulierten Regeln.

```
Meldungstext ──► Jev: 5 Fragen in einem Request ──► Urteile (Wahrscheinlichkeiten)
                                                        │
                        regeln.py (Schwellen im Code) ◄─┘
                                │
      kein_schaden_weiterleiten │ sperren │ pruefen │ auftrag   (+ Eskalation bei Personenschaden)
                                │
               Vorschlag für WaWi: schaden_melden(kategorie, schwere)
```

## Die fünf Urteile

| Frage | Primitive | Antwort |
| --- | --- | --- |
| `ist_schadensmeldung` | Noul | Wahrscheinlichkeit, dass überhaupt ein Schaden am Rad beschrieben wird |
| `kategorie` | Choice | eines von 15 Bauteilen oder `keine_zuordnung`, mit Wahrscheinlichkeit je Option und Konfidenz |
| `schwere` | Score | gering · mittel · fahruntauglich (die Stufen der WaWi), mit Verteilung und Konfidenz |
| `sicherheitsrelevant` | Noul | Wahrscheinlichkeit, dass Weiterfahren zu Sturz oder Unfall führen kann |
| `personenschaden` | Noul | Wahrscheinlichkeit, dass jemand gestürzt ist oder verletzt wurde |

Die Fragen stehen in `velocity_jev/fragen.py`, die Regeln in `velocity_jev/regeln.py`. Der State enthält nur den Meldungstext und den Radtyp – mehr Kontext lenkt Jev ab.

## In Deepnote ausführen

Das Notebook `VeloCity_Jev.ipynb` bündelt Beurteilung, Kennzahlen, interaktive Tabellen, gruppierte
Auswertung, Schwellen und den Vergleich der Fragen-Stände. Es läuft ohne API-Key, solange die Fragen
nicht umformuliert werden, weil alle Antworten im Cache liegen.

1. In Deepnote ein neues Projekt anlegen. In der rechten Seitenleiste unter **Files** über **+** die
   ZIP-Datei mit **Upload file** hochladen und `VeloCity_Jev.ipynb` mit **Upload .ipynb file** als Notebook
   importieren. Danach die Maschine (neu) starten: Erst dann liegt die ZIP-Datei im Arbeitsverzeichnis
   `/datasets/_deepnote_work`. Die erste Zelle entpackt sie dort, falls der Ordner `velocity_jev` noch
   fehlt; das dauert im Deepnote-Dateisystem einige Minuten.
2. Liegt `requirements.txt` im Projektwurzelverzeichnis, installiert Deepnote die Pakete beim Start;
   sonst übernimmt das die erste Zelle. Nötig ist Python 3.10 oder neuer (Deepnote-Standard: 3.11).
3. Für neue Anfragen an Jev: rechte Seitenleiste → **Integrations** → **Environment variables**,
   Variable `TYPESAFE_API_KEY` anlegen, mit dem Projekt verbinden, Maschine neu starten.
4. Im Notebook unter „Parameter“ `NUR_CACHE = False` setzen, wenn neue Anfragen gewünscht sind.

## Einrichtung

Voraussetzungen: Python 3.10 oder neuer, ein TypeSafe-Konto mit API-Key ([console.typesafe.ai](https://console.typesafe.ai/)).

```bash
python -m venv .venv && source .venv/bin/activate   # liegt der Ordner in OneDrive/iCloud: venv besser außerhalb anlegen
pip install -r requirements.txt
cp .env.example .env        # dann TYPESAFE_API_KEY eintragen
python skripte/00_verbindung_pruefen.py
```

Der API-Key steht ausschließlich in der `.env`. Die Datei ist in `.gitignore` eingetragen und gehört weder ins Repository noch auf Folien oder in Moodle.

## Ablauf

```bash
python skripte/01_klassifizieren.py --limit 5    # erst ein paar Meldungen ansehen
python skripte/01_klassifizieren.py              # alle 48 Meldungen mit dem besten Fragen-Stand
python skripte/01_klassifizieren.py --stand 0    # Fragen der Übergabe (liegen im Cache)
python skripte/02_auswerten.py                   # Vergleich mit den Soll-Labels, Schwellen durchspielen
python skripte/04_einzelmeldung.py "Bremse hinten quietscht und greift erst ganz spät"
```

Optional in PostgreSQL/Supabase ablegen (Schema `jev_labor`, getrennt von den WaWi-Sichten):

```bash
python skripte/03_nach_postgres.py --schema-anlegen --anmerkung "Standard-Schwellen"
```

```sql
select * from jev_labor.v_lauf_kennzahlen order by lauf_id;   -- Kennzahlen je Lauf
select * from jev_labor.v_kalibrierung_sicherheit;             -- stimmen die Wahrscheinlichkeiten?
select * from jev_labor.v_kategorie_konfusion;                 -- Konfusionsmatrix für Power BI
select * from jev_labor.v_arbeitsliste;                        -- Prüffälle und Eskalationen
```

## Cache: einmal zahlen, beliebig oft auswerten

Jede Antwort landet in `daten/cache/jev_cache.jsonl`. Der Schlüssel besteht aus Modell, State und dem genauen Wortlaut aller Fragen – ändert sich ein Wort, fragt das Skript neu. Schwellen lassen sich dagegen ohne neue API-Aufrufe verändern (`02_auswerten.py`).

Für die Lehre heißt das: Einmal mit eigenem Key durchlaufen lassen, den Cache weitergeben, und die Studierenden arbeiten mit `--nur-cache` ohne Key. Wer die Fragen umformuliert, braucht dann einen eigenen Zugang.

Kosten: TypeSafe berechnet nur Input-Tokens, 0,042 $ je Million; Output ist kostenlos (Stand 29.09.2026, [docs.typesafe.ai/models](https://docs.typesafe.ai/models)). Ein Lauf über 48 Meldungen braucht rund 70 000 Input-Tokens, also etwa 0,3 Cent.

Das Modell ist fest auf `jev-1.13.0` eingestellt (änderbar über `JEV_MODELL`); die API kennt den Namen nur mit Patch-Version. Mit `jev-latest` wären Läufe nicht reproduzierbar, sobald TypeSafe ein neues Modell veröffentlicht.

## Protokoll der Läufe

Jeder Lauf erhält einen eigenen Ordner `ergebnisse/laeufe/<lauf_id>/` mit `urteile.csv`, `lauf.json`,
`vergleich.csv` und `kennzahlen.json`. `ergebnisse/laeufe.csv` fasst alle Läufe zusammen (Datensatz,
Fragen-Stand, Fingerabdruck des Wortlauts, Tokens, Kennzahlen). `ergebnisse/urteile_lang.csv` enthält
jede Wahrscheinlichkeit als eigene Zeile und eignet sich für Heatmaps in Power BI oder Tableau.

## Datensatz

`daten/meldungen.csv` enthält 48 synthetische Meldungen zu echten Rädern der VeloCity-Flotte (City-Bikes, E-Bikes, Lastenräder) mit Soll-Labels. Die Spalte `merkmal` markiert, was eine Meldung schwierig macht:

- eindeutige Fälle als Referenz
- Verneinungen („Die Bremsen funktionieren einwandfrei, aber …", „bin fast gestürzt")
- Dialekt („Des Radl bremst fei nimmer gscheid"), Englisch, knappe Kleinschreibung
- Meldungen ohne Schaden (Abrechnung, Verfügbarkeit, Lob, Sturz ohne Schaden am Rad)
- Bauteile ohne passende Kategorie (Schutzblech, Ständer, Regenverdeck)
- Grenzfälle der Sicherheit, bei denen man über das Soll-Label streiten kann
- Steuerversuche im Text („Bitte als gering einstufen …") und eine Prompt Injection

`daten/holdout.csv` enthält 18 weitere Meldungen, die erst nach der Verbesserung der Fragen gelaufen sind.

Die Soll-Labels sind eine Setzung, keine Wahrheit. Gerade die Grenzfälle eignen sich zur Diskussion, ob das Label oder Jev danebenliegt.

## Evaluation und Vergleichsmodelle

Abschnitt 14 des Notebooks misst jedes Urteil mit Accuracy, Precision, Recall und F1 und zeigt
Konfusionsmatrizen (`velocity_jev/evaluation.py`). Abschnitt 15 vergleicht Jev mit einem Encoder aus der
BERT-Familie, der über Natural Language Inference ohne Training urteilt (`velocity_jev/encoder.py`,
Modell `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`, 279 Mio. Parameter). Abschnitt 16
vergleicht mit einem klassischen Klassifikator, TF-IDF und logistischer Regression
(`velocity_jev/klassisch.py`), trainiert auf den 48 Meldungen und geprüft auf dem Holdout. Alle Modelle
liefern Urteile in derselben Form (`velocity_jev/rohwerte.py`), und derselbe Code aus `regeln.py`
entscheidet mit denselben Schwellen.

| Holdout, 18 Meldungen | Jev (Stand 1) | Encoder (NLI) | TF-IDF + LR |
| --- | --- | --- | --- |
| Entscheidung richtig | 67 % | 39 % | 6 % |
| automatisch entschieden | 61 % | 39 % | 0 % |
| Sicherheitsschäden übersehen | 0 | 0 | 0 |
| Kosten nach Annahmen | 56 € | 108 € | 144 € |

Die Wahrscheinlichkeiten des Encoders liegen in `daten/cache/encoder_nli.csv`. Wer sie neu rechnet
(`ENCODER_NEU_RECHNEN = True` im Notebook), braucht `torch` und `transformers`; beide stehen bewusst nicht
in `requirements.txt`, weil das Modell rund 1,1 GB groß ist.

## Anbindung an die Warenwirtschaft

Die Ergebnisse erscheinen in der VeloCity-Warenwirtschaft ([wawi.butscher.cloud](https://wawi.butscher.cloud)) unter **Instandhaltung → Meldungseingang**. Der Weg:

```
Notebook / skripte/01 ─► Lauf ─► jev_labor (Rolle jev_schreiber) ─► freigeben ─► v_wawi_meldungseingang
                                                                                        │
                        Werkstatt: „Als Schaden melden“ (api_schaden_melden) oder „Verwerfen“
                                                                                        │
                                              velocity.jev_vorschlag_entscheidung = spätere Soll-Werte
```

- **Schreiben:** `skripte/03_nach_postgres.py` oder Abschnitt 13 im Notebook, mit der Rolle `jev_schreiber`. Sie darf nur in das Schema `jev_labor` einfügen und einen Lauf freigeben; sie sieht nichts aus dem Betrieb. Angelegt wird sie in `velocity-fallstudie/db/aufbau/0026_jev_meldungseingang.sql`, das Passwort steht nur in `.env` bzw. in Deepnote.
- **Anzeigen:** Die Warenwirtschaft zeigt nur den zuletzt freigegebenen Lauf, ohne Soll-Labels. Die Liste lässt sich sortieren, filtern und gruppieren.
- **Entscheiden:** Der Vorschlag bucht nichts. Erst ein Mensch aus der Werkstatt übernimmt ihn (Kategorie und Schwere sind vorbelegt und änderbar) oder verwirft ihn. Beides wird gespeichert – das ist Human-in-the-Loop und zugleich die Datengrundlage, an der sich die Vorschläge später messen lassen.
- **Kategorien:** Die WaWi prüft Kategorien nicht gegen eine feste Liste; `schadensmeldung.kategorie` ist bewusst Freitext. `keine_zuordnung` wird nicht übernommen, das Bauteil benennt die Werkstatt.

## Foliensatz

`folien/VeloCity_Jev_Schadenmeldungen.pptx` (40 Folien, THWS-Design) und die PDF daneben: Fallstudie, frühere
Ansätze der Textklassifikation, Jev und System One, Vorgehen, Ergebnisse, Anbindung an die Warenwirtschaft,
weitere Anwendungsfälle. Das Deck wird erzeugt, nicht von Hand bearbeitet; alle Zahlen kommen aus
`ergebnisse/laeufe/`:

```bash
python folien/folien_bauen.py      # braucht den Skill thws-slides unter ~/.claude/skills/thws-slides
```

Die Belege zu den früheren Ansätzen und den Anwendungsfällen stehen in `docs/recherche_fruehere_ansaetze.md`
und `docs/recherche_anwendungsfaelle.md`.

## Ideen für Übungen

1. **Schwellen und Kosten.** Die Kostenannahmen stehen oben in `02_auswerten.py`. Was passiert mit der günstigsten Schwelle, wenn ein übersehener Sicherheitsschaden 5 000 € statt 500 € kostet?
2. **Kalibrierung.** Treffen Meldungen mit `sicherheitsrelevant ≈ 0,8` in etwa acht von zehn Fällen zu? (`v_kalibrierung_sicherheit`, Brier-Score)
3. **Frage verbessern.** Eine Fehlklassifikation suchen, die Frage in `fragen.py` präziser formulieren, neu laufen lassen, vergleichen. Jev liest wörtlich: Was man zur Erklärung eines Fehlers sagen würde, gehört meist in die Frage.
4. **Neue Frage.** Ein zusätzliches Urteil ergänzen, etwa ob Vandalismus vorliegt, und eine Regel dafür schreiben.
5. **Robustheit.** Eigene Meldungen schreiben, die Jev in die Irre führen sollen. Wo hält die Regel im Code, wo nicht?
6. **Vergleich mit einem generativen LLM.** Dieselben Meldungen mit einem Prompt und JSON-Ausgabe beurteilen lassen und Trefferquote, Kosten, Latenz und die Nutzbarkeit der Konfidenz vergleichen.

## Grenzen, die man kennen sollte

- **Sprache.** Laut Modellseite der TypeSafe-Doku ist Englisch die primäre Trainingssprache; andere Sprachen werden ungenauer verarbeitet, und man soll mit eigenen Daten testen ([docs.typesafe.ai/models](https://docs.typesafe.ai/models)). Fragen und Meldungen sind hier deutsch; ob englische Fragen bessere Ergebnisse liefern, ist ein lohnendes Experiment.
- **Wörtliches Lesen, Zahlen, Datumsangaben.** Jev 1.13 nimmt Formulierungen wörtlich und ist schwach bei Zahlen und Datumsvergleichen. Rechnen bleibt im Code.
- **Konfidenz ist keine Erlaubnis.** Sie beschreibt, wie konzentriert eine Verteilung ist, nicht, ob der gesamte Ablauf richtig entscheidet.
- **Tests ohne Key.** `tests/attrappe.py` bildet die API für die Unit-Tests nach und antwortet anhand der Soll-Labels. Die Tests prüfen Code und SDK-Anbindung, über Jev sagen sie nichts aus.

```bash
python -m pytest
```

## Struktur

```
CLAUDE.md                   Kontext, Regeln und Arbeitsplan für Claude Code
docs/iterationen.md         Protokoll der Frage-Iterationen
daten/meldungen.csv         48 Meldungen mit Soll-Labels
daten/cache/                Antworten von Jev und des Encoder-Modells
VeloCity_Jev.ipynb          Notebook für Deepnote oder Jupyter
docs/fehleranalyse_stand0.csv  Ursache je Fehlentscheidung des Ausgangsstands
daten/holdout.csv           18 Meldungen für den Holdout
velocity_jev/fragen.py      die fünf Fragen in nummerierten Ständen und der State
velocity_jev/pipeline.py    Request an Jev, Cache, Urteil
velocity_jev/regeln.py      Schwellen und Entscheidung
velocity_jev/ablauf.py      einen Datensatz beurteilen (Skript und Notebook)
velocity_jev/auswertung.py  Kennzahlen, Gruppierung, Schwellen
velocity_jev/evaluation.py  Accuracy, Precision, Recall, F1, Konfusionsmatrizen, Modellvergleich
velocity_jev/rohwerte.py    Urteile aus den Wahrscheinlichkeiten eines Vergleichsmodells
velocity_jev/encoder.py     Vergleichsmodell: Encoder (BERT-Familie) mit Zero-Shot über NLI
velocity_jev/klassisch.py   Vergleichsmodell: TF-IDF und logistische Regression
velocity_jev/protokoll.py   Ablage der Läufe
velocity_jev/datenbank.py   Läufe nach PostgreSQL/Supabase schreiben und freigeben
folien/                     Foliensatz (PPTX, PDF), Bauskript und Bildschirmfotos der WaWi
skripte/00–04               Verbindung prüfen, klassifizieren, auswerten, nach Postgres, Einzelmeldung
sql/01_schema.sql           Tabellen und Auswertungssichten für PostgreSQL/Supabase
tests/                      Unit-Tests und API-Attrappe
```

Dokumentation von TypeSafe: [docs.typesafe.ai](https://docs.typesafe.ai/)

# Iterationen der Fragen

Eine Zeile je Änderung. Nur eine Frage pro Iteration ändern. Die Stände stehen in
`velocity_jev/fragen.py` (`STAENDE`); jeder Lauf liegt mit Fragen-Fingerabdruck in
`ergebnisse/laeufe.csv`. Modell in allen Läufen: `jev-1.13.0`.

## Änderungen an der Auswertung vor der ersten Iteration (29.09.2026)

Beide Änderungen kosten keine Requests; Stand 0 wurde danach aus dem Cache neu ausgewertet.

- **Soll bei fehlender Kategorie.** Für einen ungefährlichen Schaden ohne passende Kategorie
  (M013, M026, M041) ist jetzt `pruefen` das Soll: Die WaWi braucht eine Kategorie, die ein Mensch
  vergibt. Vorher erwartete `soll_entscheidung` ein `auftrag`, das die Regeln nie liefern konnten.
  Geändert in `regeln.py` und in der Sicht `jev_labor.v_urteil_vs_soll`.
- **Schwere aus dem gerundeten Erwartungswert** statt aus der wahrscheinlichsten Stufe, wie es die
  TypeSafe-Doku für Score empfiehlt. Betroffen war M027 (0,18 / 0,39 / 0,43 → Erwartungswert 1,25 → mittel).

## Iterationen auf den 48 Meldungen

| Nr. | Datum | Frage | Änderung (alt → neu) | Wirkung auf Kennzahlen | Neue Requests / Tokens |
| --- | --- | --- | --- | --- | --- |
| 0 | 29.09.2026 | – | Ausgangsstand der Übergabe (Fingerabdruck `bb845a4219`) | Entscheidung richtig 58 %, automatisiert 71 %, Fehler darunter 24 %, übersehene Sicherheitsschäden 0, unnötige Sperren 6, unnötige Prüfungen 12, Kosten 292 €. `sicherheitsrelevant` richtig 55 % (Brier 0,250), `ist_schadensmeldung` 96 % (Brier 0,024), Kategorie 100 %, Schwere exakt 86 % | 48 / 62 495 Input, 11 428 Output (erster echter Lauf) |
| 1 | 29.09.2026 | `sicherheitsrelevant` | alt: „Kann der … Mangel beim Weiterfahren zu einem Sturz, einem Unfall oder einer Verletzung führen?“ ohne criteria. → neu: „Ist das Weiterfahren mit dem … Mangel unmittelbar gefährlich?“ mit criteria: true = Rad bremst, lenkt, hält die Spur oder trägt nicht mehr zuverlässig, ein Teil kann sich lösen, Personen oder Ladung ungesichert, Brandgefahr; false = Komfort, Geräusche, Aussehen, Reichweite, Zubehör, abgestelltes Rad, kein Mangel (`38519718c8`) | Entscheidung richtig 79 %, automatisiert 77 %, Fehler darunter 5 %, übersehen 0, unnötige Sperren 0, unnötige Prüfungen 8, Kosten 148 €. `sicherheitsrelevant` 93 % (Brier 0,062). Nachteil: M015 und M027 (Soll sperren) gehen jetzt zur Prüfung statt in die Sperre | 48 / 68 687 Input, 11 428 Output |
| 2 | 29.09.2026 | `ist_schadensmeldung` | alt: „… einen technischen Mangel oder Schaden am geliehenen Rad?“, false nennt „App“. → neu: „… einen Mangel oder Schaden an einem Bauteil des geliehenen Rads, auch einen rein optischen?“, true nennt „verkratzt“ und Schloss, Akku, Zubehör, false nur „Bedienung der App“ (`ee06c6996a`) | M022 (0,42 → 0,96) und M017 (0,37 → 0,76) jetzt erkannt, aber M007 (Sturz mit verdrehtem Lenker) fällt von 0,63 auf 0,45 und wird als „kein Schaden“ weitergeleitet: 1 übersehener Sicherheitsschaden, Kosten 616 €. M017 wird zudem unnötig gesperrt. **Verworfen**, bester Stand bleibt 1 | 48 / 70 271 Input, 11 428 Output |

Rauschen: Dieselbe Frage (`sicherheitsrelevant`, Stand 1 und 2) weicht zwischen zwei Läufen im Mittel
um 0,01 ab, höchstens um 0,05. Die Veränderungen oben gehen also auf den Wortlaut zurück.

## Holdout (18 neue Meldungen, `daten/holdout.csv`)

Vor Iteration 1 geschrieben und erst nach der Wahl des besten Stands gelaufen. Die Soll-Labels
sind eine Setzung von Claude nach den Konventionen der 48 Meldungen und noch nicht geprüft.

| Stand | Entscheidung richtig | automatisiert | Fehler darunter | übersehen | unnötig gesperrt | unnötig geprüft | Kosten | `sicherheitsrelevant` richtig / Brier | Tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 67 % | 89 % | 31 % | 0 | 5 | 1 | 116 € | 53 % / 0,297 | 23 495 Input, 4 291 Output |
| 1 | 67 % | 61 % | 0 % | 0 | 0 | 6 | 56 € | 73 % / 0,140 | 25 817 Input, 4 291 Output |

Stand 1 ersetzt auch auf ungesehenen Meldungen falsche Sperren durch Prüfungen. Harmlose Mängel
liegen dort aber noch bei 0,46 bis 0,63 und damit über der Prüfschwelle 0,4; H014 (Kurbel mit
Spiel, Soll sperren) liegt bei 0,47 und geht zur Prüfung.

## Offen

- Regel statt Frage: Eine Meldung mit hoher Sicherheitsrelevanz sollte nie als „kein Schaden“
  weitergeleitet werden, sondern mindestens zur Prüfung gehen (hätte M007 in Stand 2 abgefangen).
- Prüfschwelle 0,4 erst nach einem größeren Holdout neu festlegen.

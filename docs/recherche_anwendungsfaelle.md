# Recherche: Jev-Anwendungsfälle (Subagent, 29.09.2026)

## Preis und Geschwindigkeit
- typesafe.ai Startseite: $42 je Milliarde Input-Tokens; 238x niedrigerer Input-Preis als Claude Fable 5.1; "193.6x schneller, 444.6x günstiger" (Fußnote: Workflows für System-One-Aufgaben); Demo TypeSafe $0.000081 in 0.114 s vs. LLMs $0.013880 in 8.566 s. FAQ: garantiert ist die Form der Antwort, nicht die Richtigkeit.
- Blog https://typesafe.ai/blog/introducing-system-one-models-and-jev: 70–500 ms; Faktoren sind oberes Ende.
- models.md: $0.042 je Million Input-Tokens, Output kostenlos; 250,000 Tokens/s, 1,200 Requests/min; 64k Tokens je Request, 32k für State plus längste Frage. Englisch primäre Sprache, andere Sprachen ungenauer, mit eigenen Daten testen (auch state.md).
- parallel_questions.md: 13 Fragen in einem Request $0.000497 / 0.27 s vs. 13 Requests $0.006090 / 2.71 s (12.2x günstiger, 10.0x schneller); primitives.md nennt 11.5x / 9.6x.

## Anwendungsfälle (N = Noul, C = Choice, S = Score)
1. Ticket-Triage [Doku: how-to-build, choice, fan-out, intent-routing]: C Team, N Erstattung, S Verärgerung; Konfidenz < 0,75 -> Mensch. Zendesk intelligent triage als Praxisbeispiel.
2. Moderation von Bewertungen [llm_guardrails, consistency_choice]: N personenbezogene Daten, N Angriff, N Werbung; >= 0,35 Prüfliste, >= 0,70 nicht veröffentlichen. Konsistenz: 2 von 8 Fragen wechselten in 15 Wiederholungen das Label; mit Mindestwahrscheinlichkeit 0,60 Übereinstimmung 99,2 % bei 74,2 % automatisch.
3. Schadenstriage Versicherung [consistency_noul]: N Deckung, N Ausschluss, N Dokumentation; 0,30–0,70 -> Sachbearbeitung; "covered" schwankte über 15 Läufe 0,43–0,53.
4. Rechnungs- und Belegprüfung [Übertragung; pre_parsed_value_extraction]: Regex findet Kandidaten, C wählt Gesamtbetrag; Drei-Wege-Abgleich im Code; § 14 Abs. 4 UStG Pflichtangaben.
5. Reranking [rerank_typesafe, semantic_find]: N "Beantwortet Kandidat die Anfrage?"; 40 juristische Anfragen x 30 Kandidaten: Top-1 5 % -> 18 %, Top-10 38 % -> 62 %; 1.200 Aufrufe $0.0645.
6. Lead-Qualifizierung [Stichwort use-case-map; composite-scoring]: S Konkretheit des Bedarfs, N Problem passt, N Anbieter-Anfrage.
7. Guardrails für Chatbots/RAG [llm_guardrails, classifying_rag_passages]: N Jailbreak, N Anweisungen in Passage, S Schaden; Prüfung ab 0,35, Sperre ab 0,70/0,85.
8. Prüfung von LLM-Ergebnissen [citation_check, sde_cascade]: C stützt/widerspricht/sagt nichts; N "Wert nicht belegt?" -> Reasoning-Modell ab 0,7.
9. Taxonomie-Einordnung [hierarchical_classification, classification_using_confidence]: C je Ebene, Beam Search K=3; Konfidenz >= 0,9 -> feine Kategorie; 60 Geschäftsberichte: sichere Hälfte 90 % richtig, unsichere 40 %. Choice max. 255 Optionen.
10. Dubletten in Stammdaten [entity_alignment]: S verschieden/Variante/dasselbe; 450 Paare -> 360/50/40.
11. Freitext als Merkmal [autoresearch_feature_discovery]: Weinkritiken RMSE Mittelwert 3,09; Wortzählung 2,47; direkte Frage 2,15; 18 Fragen 1,87; 38 Fragen 1,77.
12. Sprachbefehl -> Funktionsaufruf [function_calling, confidence-routing, smart-home]: C Funktion, C Argumente; Banking: < 0,6 Mensch, Überweisung erst > 0,85.
- Recruiting: Hochrisiko nach Anhang III Nr. 4(a) KI-VO -> Gegenbeispiel.

## Lehrprojekte
- BurgerMetrics: wawi.rezension (laut Projektnotiz 10.000 Zeilen; nicht live geprüft): Freigabe von Shop-Rezensionen: N personenbezogene Daten, N Beleidigung, N Bezug, C Thema {geschmack, temperatur, wartezeit, personal, preis, sauberkeit, falsche_bestellung, sonstiges}, S Stimmung 5 Stufen; Widerspruch Stimmung/Sterne melden.
- Hotel-BI: kein Freitext; erst mit Zusatzquelle (515K Hotel Reviews, Kaggle).
- FitTrack: nur Zusatzübung (Freitext-Eingabe eines Workouts).
- Siemens-Waschmaschine: passt sehr gut als Gegenmodell zum RAG: C "Welche Zeile der Störungstabelle?" (29 Zeilen + keine), N Wasseraustritt, N Brandgeruch; Abhilfe wörtlich aus dem Handbuch.
- Superstore: Produktnamen hierarchisch einordnen (3 Kategorien, 17 Unterkategorien, 1.849 Namen); 32 Product IDs mit zwei Namen, 16 Namen unter mehreren IDs -> Dubletten.

## Grenzen jev-1.13 (model-jaggedness/jev-1.13.md) und Confidence (confidence.md)
- Zitat: Jev "answers the question you wrote, not the one you meant".
- Wörtliches Lesen; Zahlen; Datum/Zeit; Indirektion; großer State; Adversarial Content; keine strukturellen Invarianten (Noul 0,22 vs. Choice 0,01; Frage + Verneinung = 1,19); Sprache.
- Confidence nur bei Choice und Score; Noul-Wert ist die Wahrscheinlichkeit. Drei Bereiche: hoch automatisch, mittel bestätigen, niedrig an Menschen. Schwellen steigen mit dem Risiko; konservativ starten; Kalibrierung gilt für Gruppen; Schwellen an feste Modellversion binden.

## URLs
https://docs.typesafe.ai/llms.txt · concepts/use-case-map.md · concepts/system-one.md · concepts/how-to-build-with-system-one.md · primitives.md · primitives/noul.md · primitives/choice.md · primitives/score.md · confidence.md · model-jaggedness/jev-1.13.md · models.md · concepts/state.md · introduction/machine-learning-primer.md · patterns/fan-out.md · patterns/composite-scoring.md · patterns/confidence-routing.md · patterns/intent-routing.md · cookbooks.md · cookbooks/function_calling.md · cookbooks/pre_parsed_value_extraction_cookbook.md · cookbooks/rerank_typesafe.md · cookbooks/hierarchical_classification.md · cookbooks/autoresearch_feature_discovery.md · cookbooks/citation_check.md · cookbooks/sde_cascade.md · cookbooks/parallel_questions.md · cookbooks/llm_guardrails.md · cookbooks/consistency_choice_cookbook.md · cookbooks/consistency_noul_cookbook.md · cookbooks/classification_using_confidence.md · cookbooks/entity_alignment.md · cookbooks/classifying_rag_passages.md · cookbooks/semantic_find.md · cookbooks/date_extraction_cookbook.md · demos/smart-home.md (alle unter https://docs.typesafe.ai/) · https://typesafe.ai · https://typesafe.ai/blog/introducing-system-one-models-and-jev · https://artificialintelligenceact.eu/annex/3/ · https://www.gesetze-im-internet.de/ustg_1980/__14.html

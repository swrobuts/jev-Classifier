# Recherche: Textklassifikation im Rückblick (Subagent, 29.09.2026)

| Stufe | Schlüsseljahr | Schlüsselquelle | Trainingsdaten | Verneinung/Dialekt/Sprache | Wahrscheinlichkeiten | Neue Kategorie |
|---|---|---|---|---|---|---|
| 1 Regeln, Schlüsselwörter, Wörterbücher | General Inquirer 1966 [1]; vorherrschend bis Ende 1980er [2]; NegEx 2001 [3] | Chapman et al. 2001 | keine; Expertenregeln | Verneinung nur per Zusatzregel (NegEx Sensitivität 77,8 %, PPV 84,5 %); jede Dialektform/Sprache eigene Einträge* | keine | neue Regeln schreiben |
| 2 BoW/TF-IDF + Naive Bayes/SVM | IDF 1972 [4]; NB/SVM 1998 [5–7] | Joachims 1998 | gelabelte Dokumente je Kategorie | Wortreihenfolge entfällt; Behelf Negations-Markierung [8] | NB drückt gegen 0/1, SVM sigmoidförmig verzerrt; nachkalibrierbar [9] | labeln, neu trainieren |
| 3 Wortvektoren + NN | word2vec 2013 [10]; CNN 2014 [11] | Kim 2014 | Vektoren ohne Labels (100 Mrd. Wörter Google News), Klassifikator mit Labels | lokale Wortfolgen; unbekannte Wörter Zufallsvektoren; Subwörter helfen [12] | Softmax oft fehlkalibriert [30] | labeln, Ausgabeschicht erweitern |
| 4 Transformer + Fine-Tuning | Transformer 2017 [13]; BERT 10/2018 arXiv, NAACL 2019 [14]; German BERT 06/2019 [16]; GBERT 2020 [17] | Devlin et al. 2019 | Vortraining ohne Labels; Fine-Tuning mit weniger Labels (ULMFiT: 100 Beispiele ≈ 100-fache Menge) [15] | beidseitiger Kontext; "can" vs. "cannot" in Lückentests nicht unterschieden [18]; Leistungsabfall bei Dialekten [20] | in-domain recht gut kalibriert, Temperature Scaling [19] | erneut feinjustieren |
| 5 Zero-Shot über NLI | Yin et al. 2019 [21]; BART 10/2019 [22]; bart-large-mnli 02/2020 [23]; Pipeline transformers 3.1.0 01.09.2020 [24] | Yin, Hay, Roth 2019 | keine aufgabenspezifischen | XNLI-Modell für 15 Sprachen inkl. Deutsch [25] | auf Summe 1 über Labelliste normiert | Label zur Laufzeit ergänzen |
| 6 Generative LLMs mit Prompt | GPT-3 2020 [26]; JSON mode 06.11.2023 [28, Sekundärquelle]; Structured Outputs 06.08.2024 [29] | Brown et al. 2020 | keine Gewichtsänderung; Beispiele im Prompt | Dialekt-Abfall [20]; Anweisungen im Text wirken mit | schwankt mit Prompt-Format [27]; verbalisierte Konfidenz überkonfident [32], uneinheitlich [33] | im Prompt/Schema ergänzen; Schema sichert Form, nicht Inhalt |

Querschnitt Kalibrierung: Guo et al. 2017 [30] moderne Netze überkonfident, Temperature Scaling; GPT-4 Basismodell ECE 0,007, nach Post-Training 0,074 [31]; Xiong et al. [32] überkonfident; Tian et al. [33] oft besser.
Querschnitt Prompt Injection: Willison 12.09.2022 [34]; Perez & Ribeiro 2022 Goal Hijacking / Prompt Leaking [35]; Greshake et al. 2023 indirekte Injection [36].
Nicht verifiziert: CONSTRUE nur über [2]; JSON-mode-Datum nur Sekundärquelle; bart-large-mnli erster Hub-Commit; Bairisch ohne spezifische Quelle.

## Quellen
[1] Stone et al. (1966): The General Inquirer. MIT Press. https://inquirer.sites.fas.harvard.edu/
[2] Sebastiani (2002): Machine Learning in Automated Text Categorization. ACM Computing Surveys 34(1). https://doi.org/10.1145/505282.505283
[3] Chapman et al. (2001): A Simple Algorithm for Identifying Negated Findings and Diseases in Discharge Summaries. J Biomed Inform 34(5). https://doi.org/10.1006/jbin.2001.1029
[4] Spärck Jones (1972): A Statistical Interpretation of Term Specificity and Its Application in Retrieval. J Documentation 28(1). https://doi.org/10.1108/eb026526
[5] Sahami et al. (1998): A Bayesian Approach to Filtering Junk E-Mail. AAAI WS-98-05. https://aaai.org/papers/055-ws98-05-009/
[6] McCallum, Nigam (1998): A Comparison of Event Models for Naive Bayes Text Classification. AAAI WS-98-05.
[7] Joachims (1998): Text Categorization with Support Vector Machines. ECML-98. https://doi.org/10.1007/BFb0026683
[8] Pang, Lee, Vaithyanathan (2002): Thumbs up? EMNLP 2002. https://aclanthology.org/W02-1011/
[9] Niculescu-Mizil, Caruana (2005): Predicting Good Probabilities with Supervised Learning. ICML 2005. https://doi.org/10.1145/1102351.1102430
[10] Mikolov et al. (2013): Efficient Estimation of Word Representations in Vector Space. https://arxiv.org/abs/1301.3781
[11] Kim (2014): Convolutional Neural Networks for Sentence Classification. EMNLP 2014. https://aclanthology.org/D14-1181/
[12] Bojanowski et al. (2017): Enriching Word Vectors with Subword Information. TACL 5. https://doi.org/10.1162/tacl_a_00051
[13] Vaswani et al. (2017): Attention Is All You Need. https://arxiv.org/abs/1706.03762
[14] Devlin et al. (2019): BERT. NAACL-HLT 2019. https://aclanthology.org/N19-1423/
[15] Howard, Ruder (2018): Universal Language Model Fine-tuning for Text Classification. ACL 2018. https://aclanthology.org/P18-1031/
[16] deepset (2019): German BERT. https://huggingface.co/google-bert/bert-base-german-cased
[17] Chan, Schweter, Möller (2020): German's Next Language Model. COLING 2020. https://aclanthology.org/2020.coling-main.598/
[18] Kassner, Schütze (2020): Negated and Misprimed Probes for Pretrained Language Models. ACL 2020. https://aclanthology.org/2020.acl-main.698/
[19] Desai, Durrett (2020): Calibration of Pre-trained Transformers. EMNLP 2020. https://doi.org/10.18653/v1/2020.emnlp-main.21
[20] Joshi et al. (2025): NLP for Dialects of a Language: A Survey. ACM Computing Surveys 57(6). https://doi.org/10.1145/3712060
[21] Yin, Hay, Roth (2019): Benchmarking Zero-shot Text Classification. EMNLP-IJCNLP 2019. https://aclanthology.org/D19-1404/
[22] Lewis et al. (2020): BART. ACL 2020. https://aclanthology.org/2020.acl-main.703/
[23] facebook/bart-large-mnli (2020). https://huggingface.co/facebook/bart-large-mnli
[24] transformers v3.1.0 (01.09.2020): zero-shot-classification pipeline. https://github.com/huggingface/transformers/releases/tag/v3.1.0
[25] joeddav/xlm-roberta-large-xnli (2020). https://huggingface.co/joeddav/xlm-roberta-large-xnli
[26] Brown et al. (2020): Language Models are Few-Shot Learners. https://arxiv.org/abs/2005.14165
[27] Zhao et al. (2021): Calibrate Before Use. ICML 2021. https://arxiv.org/abs/2102.09690
[28] OpenAI DevDay 06.11.2023 (JSON mode); Sekundär: https://decrypt.co/204516/heres-everything-announced-at-openais-dev-day
[29] OpenAI (2024): Structured Outputs, Changelog 06.08.2024. https://developers.openai.com/api/docs/guides/structured-outputs
[30] Guo et al. (2017): On Calibration of Modern Neural Networks. ICML 2017. https://proceedings.mlr.press/v70/guo17a.html
[31] OpenAI (2023): GPT-4 Technical Report, Abb. 8. https://arxiv.org/abs/2303.08774
[32] Xiong et al. (2024): Can LLMs Express Their Uncertainty? ICLR 2024. https://arxiv.org/abs/2306.13063
[33] Tian et al. (2023): Just Ask for Calibration. EMNLP 2023. https://aclanthology.org/2023.emnlp-main.330/
[34] Willison (2022): Prompt injection attacks against GPT-3. https://simonwillison.net/2022/Sep/12/prompt-injection/
[35] Perez, Ribeiro (2022): Ignore Previous Prompt. https://arxiv.org/abs/2211.09527
[36] Greshake et al. (2023): Indirect Prompt Injection. AISec 2023. https://doi.org/10.1145/3605764.3623985

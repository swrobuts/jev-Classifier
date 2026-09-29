"""Klassische Kennzahlen: Accuracy, Precision, Recall, F1 und Konfusionsmatrizen.

Alle Funktionen arbeiten auf der Vergleichstabelle aus auswertung.vergleich_bauen().
Sie gelten deshalb für Jev genauso wie für jedes Vergleichsmodell, das Urteile in
derselben Form liefert (siehe rohwerte.py).

Accuracy: Anteil der richtigen Antworten.
Precision: Von den Fällen, die das Modell als "ja" (oder als eine Klasse) meldet, wie viele stimmen?
Recall: Von den Fällen, die laut Soll "ja" (oder diese Klasse) sind, wie viele findet das Modell?
F1: harmonisches Mittel aus Precision und Recall.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from .auswertung import NOUL_FRAGEN, STUFEN, alle_kennzahlen, noul_basis
from .fragen import KATEGORIEN
from .regeln import ENTSCHEIDUNGEN

JA_NEIN = ["ja", "nein"]
SCHWERE_KLASSEN = list(STUFEN)
KATEGORIE_KLASSEN = list(KATEGORIEN)
ENTSCHEIDUNGS_KENNZAHLEN = [
    "richtig", "automatisiert", "fehler_unter_automatischen", "sicherheitsschaden_uebersehen",
    "unnoetig_gesperrt", "unnoetig_geprueft", "kosten_gesamt",
]


def ja_nein(werte: pd.Series) -> pd.Series:
    """Wahrheitswerte als "ja" und "nein", damit Tabellen und Matrizen lesbar bleiben."""
    return werte.astype(bool).map({True: "ja", False: "nein"})


def ja_nein_kennzahlen(soll: pd.Series, vorhersage: pd.Series) -> dict:
    """Accuracy, Precision, Recall und F1 einer Ja/Nein-Frage; "ja" ist die gesuchte Klasse."""
    soll, vorhersage = soll.astype(bool), vorhersage.astype(bool)
    precision, recall, f1, _ = precision_recall_fscore_support(
        soll, vorhersage, average="binary", pos_label=True, zero_division=0)
    return {"n": len(soll), "accuracy": accuracy_score(soll, vorhersage),
            "precision": precision, "recall": recall, "f1": f1}


def mehrklassen_kennzahlen(soll: pd.Series, vorhersage: pd.Series) -> dict:
    """Accuracy und Makro-Mittel von Precision, Recall und F1 über die Klassen, die im Soll vorkommen."""
    klassen = sorted(set(soll))
    precision, recall, f1, _ = precision_recall_fscore_support(
        soll, vorhersage, labels=klassen, average="macro", zero_division=0)
    return {"n": len(soll), "accuracy": accuracy_score(soll, vorhersage),
            "precision": precision, "recall": recall, "f1": f1}


def kennzahlen_je_urteil(vergleich: pd.DataFrame, schwelle: float = 0.5) -> pd.DataFrame:
    """Eine Zeile je Urteil: drei Ja/Nein-Fragen, Kategorie, Schwere und die Entscheidung des Codes."""
    zeilen = []
    for frage, soll in NOUL_FRAGEN.items():
        basis = noul_basis(vergleich, frage)
        zeilen.append({"urteil": frage, "mittelung": "Klasse ja",
                       **ja_nein_kennzahlen(basis[soll], basis[frage] >= schwelle)})
    schaden = vergleich[vergleich.soll_ist_schaden]
    zeilen.append({"urteil": "kategorie", "mittelung": "Makro",
                   **mehrklassen_kennzahlen(schaden.soll_kategorie, schaden.kategorie)})
    zeilen.append({"urteil": "schwere", "mittelung": "Makro",
                   **mehrklassen_kennzahlen(schaden.soll_schwere, schaden.schwere_stufe)})
    zeilen.append({"urteil": "entscheidung", "mittelung": "Makro",
                   **mehrklassen_kennzahlen(vergleich.soll_entscheidung, vergleich.entscheidung)})
    return pd.DataFrame(zeilen)


def klassen_kennzahlen(soll: pd.Series, vorhersage: pd.Series, klassen: list[str]) -> pd.DataFrame:
    """Precision, Recall und F1 je Klasse, dazu wie oft die Klasse im Soll und in der Vorhersage vorkommt."""
    precision, recall, f1, anzahl = precision_recall_fscore_support(
        soll, vorhersage, labels=klassen, zero_division=0)
    return pd.DataFrame({"klasse": klassen, "soll": anzahl,
                         "vorhergesagt": [int((vorhersage == k).sum()) for k in klassen],
                         "precision": precision, "recall": recall, "f1": f1})


def vorkommende_klassen(soll: pd.Series, vorhersage: pd.Series, reihenfolge: list[str]) -> list[str]:
    """Nur die Klassen, die im Soll oder in der Vorhersage vorkommen, in fester Reihenfolge."""
    vorhanden = set(soll) | set(vorhersage)
    return [k for k in reihenfolge if k in vorhanden]


def konfusionsmatrix(soll: pd.Series, vorhersage: pd.Series, klassen: list[str]) -> pd.DataFrame:
    """Zeilen: Soll, Spalten: Vorhersage. Auf der Diagonale stehen die richtigen Fälle."""
    tabelle = pd.crosstab(pd.Series(list(soll), name="Soll"), pd.Series(list(vorhersage), name="Vorhersage"))
    return tabelle.reindex(index=klassen, columns=klassen, fill_value=0)


def konfusionsmatrizen(vergleich: pd.DataFrame, schwelle: float = 0.5) -> dict[str, pd.DataFrame]:
    """Die Konfusionsmatrizen aller Urteile eines Laufs, nach Urteil benannt."""
    matrizen = {}
    for frage, soll in NOUL_FRAGEN.items():
        basis = noul_basis(vergleich, frage)
        matrizen[frage] = konfusionsmatrix(ja_nein(basis[soll]), ja_nein(basis[frage] >= schwelle), JA_NEIN)
    schaden = vergleich[vergleich.soll_ist_schaden]
    kategorien = vorkommende_klassen(schaden.soll_kategorie, schaden.kategorie, KATEGORIE_KLASSEN)
    matrizen["kategorie"] = konfusionsmatrix(schaden.soll_kategorie, schaden.kategorie, kategorien)
    matrizen["schwere"] = konfusionsmatrix(schaden.soll_schwere, schaden.schwere_stufe, SCHWERE_KLASSEN)
    matrizen["entscheidung"] = konfusionsmatrix(vergleich.soll_entscheidung, vergleich.entscheidung,
                                                ENTSCHEIDUNGEN)
    return matrizen


def konfusion_zeichnen(tabelle: pd.DataFrame, titel: str, ax) -> None:
    """Eine Konfusionsmatrix als Kachelbild: je dunkler, desto mehr Fälle; die Anzahl steht in der Kachel."""
    werte = tabelle.to_numpy()
    hoechster = max(int(werte.max()), 1)
    ax.imshow(werte, cmap="Blues", vmin=0, vmax=hoechster)
    ax.set_xticks(range(len(tabelle.columns)), tabelle.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(tabelle.index)), tabelle.index)
    ax.set_xlabel("Vorhersage")
    ax.set_ylabel("Soll")
    ax.set_title(titel, loc="left", fontsize=11)
    for zeile in range(werte.shape[0]):
        for spalte in range(werte.shape[1]):
            if werte[zeile, spalte]:
                farbe = "white" if werte[zeile, spalte] > hoechster / 2 else "#1E3A8A"
                ax.text(spalte, zeile, int(werte[zeile, spalte]), ha="center", va="center", color=farbe)
    for rand in ax.spines.values():
        rand.set_visible(False)


def matrizen_zeichnen(matrizen: dict[str, pd.DataFrame], namen: list[str], spalten: int = 3,
                      groesse: tuple[float, float] = (4.2, 3.9)):
    """Mehrere Konfusionsmatrizen nebeneinander; groesse gilt je Matrix in Zoll. Liefert die Abbildung."""
    zeilen = (len(namen) + spalten - 1) // spalten
    abbildung, achsen = plt.subplots(zeilen, spalten, figsize=(groesse[0] * spalten, groesse[1] * zeilen),
                                     squeeze=False)
    for achse, name in zip(achsen.flat, namen):
        konfusion_zeichnen(matrizen[name], name, achse)
    for achse in list(achsen.flat)[len(namen):]:
        achse.axis("off")
    abbildung.tight_layout(w_pad=3.0)
    return abbildung


def modelle_vergleichen(vergleiche: dict[str, pd.DataFrame], schwelle: float = 0.5) -> pd.DataFrame:
    """Accuracy, Precision, Recall und F1 je Urteil, eine Spalte je Modell."""
    teile = []
    for name, vergleich in vergleiche.items():
        k = kennzahlen_je_urteil(vergleich, schwelle).set_index("urteil")
        teile.append(k[["accuracy", "precision", "recall", "f1"]].stack().rename(name))
    tabelle = pd.concat(teile, axis=1)
    tabelle.index.names = ["urteil", "kennzahl"]
    return tabelle


def entscheidungen_vergleichen(vergleiche: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Automatisierung, Fehler und Kosten der Entscheidungen je Modell, bei gleichen Regeln und Schwellen."""
    return pd.DataFrame({name: {k: alle_kennzahlen(v)[k] for k in ENTSCHEIDUNGS_KENNZAHLEN}
                         for name, v in vergleiche.items()})

"""Diagramme für das Notebook.

Gestaltung wie auf den Folien: Grau ist der Normalfall, Blau hebt Jev hervor, Rot steht nur
für übersehene Sicherheitsschäden. Werte stehen an den Balken, es gibt keine Gitterlinien
und keine Legenden. Kleine Diagramme nebeneinander haben dieselbe Skala.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

from .auswertung import noul_basis

BLAU = "#003E6E"
GRAU = "#9A9A9A"
HELLGRAU = "#D9D9D9"
ROT = "#A32638"
TEXT = "#404040"
SCHRIFTEN = ["Helvetica Neue", "Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"]


def vorhandene_schriften(wunsch: list[str]) -> list[str]:
    """Nur installierte Schriften; eine fehlende Schrift meldet Matplotlib sonst bei jeder Grafik."""
    installiert = {schrift.name for schrift in font_manager.fontManager.ttflist}
    return [name for name in wunsch if name in installiert] or ["DejaVu Sans"]


plt.rcParams.update({"font.family": vorhandene_schriften(SCHRIFTEN),
                     "font.size": 11, "text.color": TEXT, "axes.labelcolor": TEXT,
                     "xtick.color": TEXT, "ytick.color": TEXT})


def prozent(wert: float) -> str:
    """Anteil als ganze Prozent im deutschen Format."""
    return f"{round(wert * 100)} %"


def euro(wert: float) -> str:
    """Betrag in ganzen Euro."""
    return f"{wert:.0f} €"


def dollar(wert: float) -> str:
    """Betrag in US-Dollar mit drei Nachkommastellen und Komma."""
    return f"{wert:.3f} $".replace(".", ",")


def anzahl(wert: float) -> str:
    """Ganze Zahl ohne Nachkommastellen."""
    return f"{wert:.0f}"


def achse_leeren(ax) -> None:
    """Rahmen und Werteachse entfernen; nur die Beschriftungen bleiben."""
    for rand in ax.spines.values():
        rand.set_visible(False)
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0)


def balken(ax, namen: list[str], werte: list[float], farben: list[str], texte: list[str], maximum: float) -> None:
    """Waagerechte Balken von oben nach unten, der Wert steht am Ende des Balkens."""
    positionen = list(range(len(namen)))[::-1]
    ax.barh(positionen, werte, color=farben, height=0.6)
    for y, wert, text, farbe in zip(positionen, werte, texte, farben):
        ax.text(wert + maximum * 0.02, y, text, va="center", color=farbe if farbe != HELLGRAU else TEXT)
    ax.set_yticks(positionen, namen)
    ax.set_xlim(0, maximum * 1.25)
    achse_leeren(ax)


def modellfarbe(name: str, wert: float, fehler: bool = False, akzent: str = "Jev") -> str:
    """Rot für übersehene Sicherheitsschäden, Blau für das hervorgehobene Verfahren, sonst Grau."""
    if fehler and wert > 0:
        return ROT
    return BLAU if name.startswith(akzent) else GRAU


def vergleich_zeichnen(tabellen: dict[str, pd.DataFrame], kennzahlen: list, akzent: str = "Jev"):
    """Small Multiples: je Kennzahl eine Zeile, je Tabelle eine Spalte, gleiche Skala in jeder Zeile.

    tabellen: Name -> Tabelle mit Kennzahlen als Zeilen und Verfahren als Spalten.
    kennzahlen: (Zeile der Tabelle, Überschrift, Formatfunktion wie prozent oder euro).
    """
    abbildung, achsen = plt.subplots(len(kennzahlen), len(tabellen), squeeze=False,
                                     figsize=(5.2 * len(tabellen), 1.9 * len(kennzahlen)))
    for zeile, (kennzahl, ueberschrift, muster) in enumerate(kennzahlen):
        maximum = max(float(t.loc[kennzahl].max()) for t in tabellen.values()) or 1.0
        for spalte, (titel, tabelle) in enumerate(tabellen.items()):
            werte = tabelle.loc[kennzahl]
            fehler = kennzahl == "sicherheitsschaden_uebersehen"
            balken(achsen[zeile][spalte], list(werte.index), list(werte.values),
                   [modellfarbe(n, v, fehler, akzent) for n, v in werte.items()],
                   [muster(v) for v in werte.values], maximum)
            achsen[zeile][spalte].set_title(f"{ueberschrift} · {titel}", loc="left", fontsize=11)
    abbildung.tight_layout(h_pad=1.5, w_pad=3)
    return abbildung


def wahrscheinlichkeiten_zeichnen(vergleiche: dict[str, pd.DataFrame], frage: str = "sicherheitsrelevant",
                                  schwellen: tuple = ((0.4, "prüfen ab 0,4"), (0.8, "sperren ab 0,8"))):
    """Je Verfahren ein Punktstreifen: jede Meldung ein Punkt, Blau heißt laut Soll ja, Grau nein."""
    soll = {"sicherheitsrelevant": "soll_sicherheitsrelevant", "ist_schadensmeldung": "soll_ist_schaden",
            "personenschaden": "soll_personenschaden"}[frage]
    abbildung, ax = plt.subplots(figsize=(10, 0.9 * len(vergleiche) + 1.2))
    for zeile, (name, vergleich) in enumerate(vergleiche.items()):
        basis = noul_basis(vergleich, frage).reset_index(drop=True)
        y = len(vergleiche) - 1 - zeile
        for i, r in basis.iterrows():
            versatz = ((i % 7) - 3) * 0.045
            ax.scatter(r[frage], y + versatz, s=34, color=BLAU if r[soll] else GRAU, alpha=0.85, linewidths=0)
    for wert, text in schwellen:
        ax.axvline(wert, color=TEXT, linewidth=0.6, linestyle=(0, (3, 3)))
        ax.text(wert, len(vergleiche) - 0.45, text, ha="center", fontsize=10)
    ax.set_yticks(range(len(vergleiche)), list(vergleiche)[::-1])
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.6, len(vergleiche) - 0.3)
    ax.set_xticks([0, 0.5, 1], ["0", "0,5", "1"])
    for rand in ("top", "right", "left"):
        ax.spines[rand].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel(f"Wahrscheinlichkeit für {frage}; blau: laut Soll ja, grau: laut Soll nein")
    abbildung.tight_layout()
    return abbildung


def ergebnisse_zeichnen(vergleich: pd.DataFrame):
    """Wie oft jede Ergebnisart vorkommt: richtig in Blau, übersehene Sicherheitsschäden in Rot, sonst Grau."""
    reihenfolge = ["richtig", "unnötig geprüft", "unnötig gesperrt", "sonstige Fehlentscheidung",
                   "Sicherheitsschaden übersehen"]
    anzahl = vergleich.ergebnis.value_counts().reindex(reihenfolge, fill_value=0)
    farben = [BLAU if n == "richtig" else (ROT if n.startswith("Sicherheit") and v else GRAU)
              for n, v in anzahl.items()]
    abbildung, ax = plt.subplots(figsize=(8, 2.6))
    balken(ax, list(anzahl.index), list(anzahl.values), farben, [str(v) for v in anzahl.values],
           max(anzahl.max(), 1))
    abbildung.tight_layout()
    return abbildung


def schwellen_zeichnen(tabelle: pd.DataFrame, sperren_ab: float = 0.8, pruefen_ab: float = 0.4):
    """Fehlerkosten je Sperr- und Prüfschwelle als Zahlentafel; das Minimum ist blau, der Standard umrandet."""
    tafel = tabelle.pivot(index="sperren_ab", columns="pruefen_ab", values="kosten_gesamt").sort_index(ascending=False)
    abbildung, ax = plt.subplots(figsize=(7, 3.6))
    minimum = tafel.min().min()
    for i, sperre in enumerate(tafel.index):
        for j, pruefung in enumerate(tafel.columns):
            wert = tafel.loc[sperre, pruefung]
            if pd.isna(wert):
                continue
            ist_minimum = wert == minimum
            if ist_minimum:
                ax.add_patch(plt.Rectangle((j - 0.45, i - 0.4), 0.9, 0.8, color="#DCE6F0"))
            if sperre == sperren_ab and pruefung == pruefen_ab:
                ax.add_patch(plt.Rectangle((j - 0.45, i - 0.4), 0.9, 0.8, fill=False, edgecolor=BLAU, linewidth=1.5))
            ax.text(j, i, f"{wert:.0f} €", ha="center", va="center", color=BLAU if ist_minimum else TEXT,
                    fontweight="bold" if ist_minimum else "normal")
    ax.set_xticks(range(len(tafel.columns)), [f"{c:.1f}".replace(".", ",") for c in tafel.columns])
    ax.set_yticks(range(len(tafel.index)), [f"{c:.2f}".rstrip("0").replace(".", ",") for c in tafel.index])
    ax.set_xlim(-0.6, len(tafel.columns) - 0.4)
    ax.set_ylim(len(tafel.index) - 0.5, -0.5)
    ax.set_xlabel("Prüfschwelle (pruefen_ab)")
    ax.set_ylabel("Sperrschwelle (sperren_ab)")
    for rand in ax.spines.values():
        rand.set_visible(False)
    ax.tick_params(length=0)
    abbildung.tight_layout()
    return abbildung

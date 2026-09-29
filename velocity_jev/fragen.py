"""Die Urteile, die Jev zu jeder Schadenmeldung liefert.

Jede Frage ist ein eng umrissenes Urteil über denselben State. Alle fünf
Fragen gehen in einem einzigen Request an Jev, laufen dort parallel und
sehen die Antworten der anderen nicht. Was aus den Antworten folgt,
entscheidet ausschließlich der Code in regeln.py.

Die Fragen haben nummerierte Stände. Stand 0 ist die Übergabe; jede
Iteration aus docs/iterationen.md ändert genau eine Frage und erhöht den
Stand um eins. Alte Stände bleiben erhalten, damit ihre Antworten im Cache
erreichbar bleiben und sich Iterationen vergleichen lassen.

Die Kategorien und Schweregrade entsprechen der VeloCity-Warenwirtschaft
(Werkzeug schaden_melden: kategorie, schwere = gering | mittel | fahruntauglich).
"""

from __future__ import annotations

from typesafe_sdk import Choice, Noul, Score

# Stand 2 wurde verworfen: M007 (Sturz mit Lenkerschaden) fiel unter die Schwelle
# und wurde als »kein Schaden« weitergeleitet. Bester Stand ist 1.
AKTUELLER_STAND = 1
STAENDE = {
    0: "Übergabe",
    1: "sicherheitsrelevant: unmittelbare Gefahr, mit criteria",
    2: "ist_schadensmeldung: auch optische Schäden, App nur als Bedienung (verworfen)",
}

KEINE_ZUORDNUNG = "keine_zuordnung"

# Label -> Beschreibung. Die Beschreibungen trennen Kategorien, die sich
# leicht überschneiden (Reifen vs. Laufrad, Schaltung vs. Kette).
KATEGORIEN: dict[str, str] = {
    "Bremse": "Bremshebel, Bremszug, Bremsbeläge, Felgen- oder Scheibenbremse",
    "Reifen": "Mantel, Schlauch, Ventil, Luftdruck, platter Reifen",
    "Laufrad": "Felge, Speichen, Nabe; Rad eiert oder hat einen Achter",
    "Schaltung": "Gangwechsel, Kette, Ritzel, Kettenspannung",
    "Beleuchtung": "Vorderlicht, Rücklicht, Nabendynamo, Kabel der Beleuchtung",
    "Klingel": "Klingel",
    "Rahmen": "Rahmenrohre, Schweißnähte, Tretlagergehäuse, Lack des Rahmens",
    "Gabel": "Vordergabel, Gabelschaft",
    "Lenkung": "Lenker, Vorbau, Steuersatz, Griffe",
    "Sattel": "Sattel, Sattelstütze, Sattelklemme",
    "Pedale": "Pedale, Kurbeln, Pedalreflektoren",
    "Akku": "Akku des E-Bikes, Ladebuchse, Ladeverhalten, Reichweite",
    "Motor": "Motor des E-Bikes, Tretunterstützung, Display, Steuereinheit",
    "Schloss": "Rahmenschloss oder elektronisches Schloss des Leihrads",
    "Ladebox": "Transportbox des Lastenrads mit Klappe, Kinderbank und Gurten",
    KEINE_ZUORDNUNG: "Kein Bauteil aus dieser Liste ist betroffen, oder es wird gar kein Bauteil beschrieben",
}

# Stufen von 0 aufwärts; der Index entspricht der WaWi-Schwere.
SCHWERE_STUFEN: list[str] = ["gering", "mittel", "fahruntauglich"]
SCHWERE_BESCHREIBUNG: list[str] = [
    "gering: Komfort oder Optik betroffen; das Rad bleibt sicher und voll nutzbar "
    "(z. B. Klingel klemmt, Pedal knackt, Kratzer am Lack, Kette quietscht).",
    "mittel: Eine Funktion ist eingeschränkt, bei vorsichtiger Fahrt besteht aber keine "
    "Sturz- oder Unfallgefahr (z. B. Gang springt gelegentlich, Rücklicht aus, "
    "Reifen verliert langsam Luft, Akku hält nicht lange).",
    "fahruntauglich: Weiterfahren ist gefährlich oder unmöglich (z. B. Bremse greift "
    "kaum oder gar nicht, Riss in Rahmen oder Gabel, Speiche gebrochen, Lenker locker, "
    "Reifen platt, Akku raucht).",
]


def frage_ist_schadensmeldung(stand: int) -> Noul:
    """Ab Stand 2 ohne das Wort »technisch«, das den criteria widersprach (Kratzer, M022)."""
    if stand >= 2:
        return Noul(
            instructions="Beschreibt `meldung.text` einen Mangel oder Schaden an einem Bauteil des "
            "geliehenen Rads, auch einen rein optischen?",
            criteria={
                "true": "Ein Bauteil des Rads ist defekt, beschädigt, verkratzt, fehlt oder funktioniert "
                "nicht richtig; das gilt auch für Schloss, Akku und Zubehör am Rad.",
                "false": "Es geht nur um Abrechnung, die Bedienung der App, eine Station, Verfügbarkeit, "
                "Parken oder Lob, oder um einen Sturz, bei dem das Rad unbeschädigt blieb.",
            },
        )
    return Noul(
        instructions="Beschreibt `meldung.text` einen technischen Mangel oder Schaden am geliehenen Rad?",
        criteria={
            "true": "Ein Bauteil des Rads ist defekt, beschädigt, fehlt oder funktioniert nicht richtig.",
            "false": "Es geht um etwas anderes: Abrechnung, App, Station, Verfügbarkeit, Parken, Lob "
            "oder einen Sturz, bei dem das Rad unbeschädigt blieb.",
        },
    )


def frage_sicherheitsrelevant(stand: int) -> Noul:
    """Ab Stand 1 mit criteria: Stand 0 fragte nur, ob ein Unfall möglich ist, und das trifft fast immer zu."""
    if stand >= 1:
        return Noul(
            instructions="Ist das Weiterfahren mit dem in `meldung.text` beschriebenen Mangel unmittelbar gefährlich?",
            criteria={
                "true": "Beim Weiterfahren droht ein Sturz oder Unfall, weil das Rad nicht mehr zuverlässig "
                "bremst, lenkt, die Spur hält oder trägt, weil sich ein Teil lösen oder abbrechen kann, "
                "weil Personen oder Ladung nicht gesichert sind oder weil Brandgefahr besteht.",
                "false": "Das Rad bremst, lenkt und trägt weiterhin zuverlässig. Der Mangel betrifft Komfort, "
                "Geräusche, Aussehen, Reichweite, Zubehör oder das abgestellte Rad, oder es wird gar kein "
                "Mangel am Rad beschrieben.",
            },
        )
    return Noul(
        instructions="Kann der in `meldung.text` beschriebene Mangel beim Weiterfahren zu einem Sturz, "
        "einem Unfall oder einer Verletzung führen?",
    )


def fragen(stand: int = AKTUELLER_STAND) -> dict:
    """Die fünf Fragen eines Requests. Die IDs sieht nur der Code, nicht das Modell."""
    return {
        "ist_schadensmeldung": frage_ist_schadensmeldung(stand),
        "kategorie": Choice(
            instructions="Welches Bauteil des Rads ist laut `meldung.text` defekt oder beschädigt? "
            "Berücksichtige den Radtyp in `rad.typ`.",
            criteria=KATEGORIEN,
        ),
        "schwere": Score(
            instructions="Wie schwer ist der in `meldung.text` beschriebene Schaden für die weitere Nutzung des Rads? "
            "Bewerte den beschriebenen Zustand des Rads, nicht die Einschätzung, um die die meldende Person bittet.",
            criteria=SCHWERE_BESCHREIBUNG,
        ),
        "sicherheitsrelevant": frage_sicherheitsrelevant(stand),
        "personenschaden": Noul(
            instructions="Schreibt die meldende Person in `meldung.text`, dass sie oder eine andere Person "
            "gestürzt ist oder verletzt wurde?",
            criteria={
                "true": "Ein Sturz oder eine Verletzung ist tatsächlich passiert.",
                "false": "Es ist niemand gestürzt oder verletzt worden; ein Beinahe-Sturz zählt nicht.",
            },
        ),
    }


RADTYPEN = {
    "CITY": {"typ": "City-Bike", "elektrisch": False},
    "EBIKE": {"typ": "E-Bike", "elektrisch": True},
    "CARGO": {"typ": "E-Lastenrad mit Transportbox", "elektrisch": True},
}


def state(text: str, typ_code: str) -> dict:
    """Nur was die Fragen brauchen: der Meldungstext und der Radtyp.

    Rahmennummer, Kanal und Zeitstempel bleiben bewusst draußen. Überflüssiger
    State lenkt Jev ab (siehe Jev-Doku „Large state full of irrelevant detail").
    """
    return {"meldung": {"text": text}, "rad": RADTYPEN[typ_code]}

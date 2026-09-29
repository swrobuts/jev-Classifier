from velocity_jev.pipeline import Urteil
from velocity_jev.regeln import AUFTRAG, KEIN_SCHADEN, PRUEFEN, SPERREN, Schwellen, entscheiden, soll_entscheidung


def urteil(**aenderungen) -> Urteil:
    basis = dict(
        meldung_id="T", modell="test", ist_schadensmeldung=0.95, kategorie="Klingel", kategorie_konfidenz=0.9,
        kategorie_wkt={}, schwere_stufe="gering", schwere_score=0.1, schwere_konfidenz=0.9, schwere_wkt={},
        sicherheitsrelevant=0.05, personenschaden=0.02,
    )
    return Urteil(**{**basis, **aenderungen})


def test_klarer_kleinschaden_wird_auftrag():
    e = entscheiden(urteil())
    assert e.entscheidung == AUFTRAG and e.wawi_kategorie == "Klingel" and e.wawi_schwere == "gering"


def test_kein_schaden_wird_weitergeleitet_auch_bei_hoher_sicherheit():
    e = entscheiden(urteil(ist_schadensmeldung=0.1, sicherheitsrelevant=0.99))
    assert e.entscheidung == KEIN_SCHADEN and e.wawi_kategorie is None


def test_hohe_sicherheitsrelevanz_sperrt():
    e = entscheiden(urteil(kategorie="Bremse", sicherheitsrelevant=0.85, schwere_stufe="mittel"))
    assert e.entscheidung == SPERREN and e.wawi_schwere == "fahruntauglich"


def test_sicher_fahruntauglich_sperrt_auch_ohne_sicherheitsnoul():
    e = entscheiden(urteil(schwere_stufe="fahruntauglich", schwere_konfidenz=0.7, sicherheitsrelevant=0.2))
    assert e.entscheidung == SPERREN


def test_unsicher_fahruntauglich_geht_zur_pruefung():
    e = entscheiden(urteil(schwere_stufe="fahruntauglich", schwere_konfidenz=0.55))
    assert e.entscheidung == PRUEFEN


def test_mittlere_sicherheitsrelevanz_geht_zur_pruefung():
    assert entscheiden(urteil(sicherheitsrelevant=0.5)).entscheidung == PRUEFEN


def test_keine_zuordnung_geht_zur_pruefung():
    assert entscheiden(urteil(kategorie="keine_zuordnung")).entscheidung == PRUEFEN


def test_unsichere_kategorie_geht_zur_pruefung():
    assert entscheiden(urteil(kategorie_konfidenz=0.3)).entscheidung == PRUEFEN


def test_personenschaden_eskaliert_zusaetzlich():
    e = entscheiden(urteil(ist_schadensmeldung=0.2, personenschaden=0.9))
    assert e.entscheidung == KEIN_SCHADEN and e.eskalation


def test_schwellen_sind_einstellbar():
    streng = Schwellen(sperren_ab=0.4)
    assert entscheiden(urteil(sicherheitsrelevant=0.5), streng).entscheidung == SPERREN


def test_soll_entscheidung():
    assert soll_entscheidung(False, True, None) == KEIN_SCHADEN
    assert soll_entscheidung(True, True, "mittel") == SPERREN
    assert soll_entscheidung(True, False, "fahruntauglich") == SPERREN
    assert soll_entscheidung(True, False, "gering") == AUFTRAG
    assert soll_entscheidung(True, False, "gering", "keine_zuordnung") == PRUEFEN
    assert soll_entscheidung(True, True, "mittel", "keine_zuordnung") == SPERREN

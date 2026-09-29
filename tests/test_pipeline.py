"""Die Pipeline gegen die echten SDK-Typen – mit der Attrappe statt der API."""

from typesafe_sdk import TypeSafeClient

from tests.attrappe import transport
from velocity_jev.pipeline import Cache, KeinCacheTreffer, beurteilen

TEXT = "Die Bremse vorne greift kaum noch, ich musste am Berliner Ring mit den Füßen bremsen."


def client():
    return TypeSafeClient(api_key="apikey_attrappe", model="attrappe", transport=transport())


def test_urteil_wird_aus_sdk_antwort_gebaut(tmp_path):
    cache = Cache(tmp_path / "c.jsonl")
    with client() as c:
        u = beurteilen("M001", TEXT, "CITY", client=c, modell="attrappe", cache=cache)
    assert u.kategorie == "Bremse"
    assert u.schwere_stufe == "fahruntauglich"
    assert set(u.schwere_wkt) == {"gering", "mittel", "fahruntauglich"}
    assert 0 <= u.sicherheitsrelevant <= 1 and u.sicherheitsrelevant > 0.5
    assert u.input_tokens == 300 and not u.aus_cache


def test_cache_spart_den_zweiten_aufruf(tmp_path):
    datei = tmp_path / "c.jsonl"
    with client() as c:
        erst = beurteilen("M001", TEXT, "CITY", client=c, modell="attrappe", cache=Cache(datei))
    zweit = beurteilen("M001", TEXT, "CITY", client=None, modell="attrappe", cache=Cache(datei))
    assert zweit.aus_cache and zweit.kategorie == erst.kategorie


def test_ohne_client_und_cache_gibt_es_keinen_treffer(tmp_path):
    try:
        beurteilen("M001", TEXT, "CITY", client=None, modell="attrappe", cache=Cache(tmp_path / "c.jsonl"))
    except KeinCacheTreffer:
        return
    raise AssertionError("KeinCacheTreffer erwartet")


def test_anderes_modell_ergibt_anderen_cache_schluessel(tmp_path):
    datei = tmp_path / "c.jsonl"
    with client() as c:
        beurteilen("M001", TEXT, "CITY", client=c, modell="attrappe", cache=Cache(datei))
    try:
        beurteilen("M001", TEXT, "CITY", client=None, modell="jev-1.13", cache=Cache(datei))
    except KeinCacheTreffer:
        return
    raise AssertionError("Cache darf modellübergreifend nicht greifen")

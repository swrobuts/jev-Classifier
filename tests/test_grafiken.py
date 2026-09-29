import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from velocity_jev.grafiken import vorhandene_schriften  # noqa: E402


def test_fehlende_schriften_fallen_weg():
    assert vorhandene_schriften(["Gibt es nicht", "DejaVu Sans"]) == ["DejaVu Sans"]


def test_ohne_installierte_wunschschrift_bleibt_dejavu():
    assert vorhandene_schriften(["Gibt es nicht", "Auch nicht"]) == ["DejaVu Sans"]


def test_keine_findfont_meldung_bei_fehlender_schrift(caplog):
    with caplog.at_level(logging.WARNING, logger="matplotlib.font_manager"):
        with plt.rc_context({"font.family": vorhandene_schriften(["Gibt es nicht", "DejaVu Sans"])}):
            abbildung, achse = plt.subplots()
            achse.set_title("Test")
            abbildung.canvas.draw()
            plt.close(abbildung)
    assert "findfont" not in caplog.text

"""Tests for the whole-instrument plan view."""

from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.svg import render_plan_view_svg


def test_plan_view_draws_every_feature_once() -> None:
    geometry = Prototype001Parameters().build()

    svg = render_plan_view_svg(geometry)

    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    # 24 frets, 12 inlay markers, 6 tuner holes + 7 body holes + jack.
    assert svg.count("<line") == 24 + 1
    assert svg.count('fill="#e8e2d0"') == 12
    assert svg.count("<circle") == 6 + 7 + 1
    # Body outline, headstock, neck, fretboard, 4 top cavities, 2 rear
    # cavities with their covers.
    assert svg.count("<path") == 4 + 12 + 4 + 4

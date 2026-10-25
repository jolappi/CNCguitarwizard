"""Tests for the back's view from behind and above: the volute, a flat
headstock's drawn root and the drawn heel."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad.script_exporter import FreeCADScriptExporter
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.prototype001 import INSTRUMENT_OVERRIDES
from cncguitarwizard.render.svg import render_volute_view_svg, volute_view
from cncguitarwizard.webapp import back_view


def test_the_back_round_the_nut_is_drawn_shaded_as_lofted() -> None:
    geometry = replace(Prototype001Parameters(), headstock_pointed_volute=True).build()
    assert geometry.volute is not None
    rows = FreeCADScriptExporter.neck_loft_rows(
        geometry.neck_surface,
        geometry.headstock,
        geometry.joint_fillet_radius,
        geometry.volute,
    )
    near = [row for row in rows if -40.0 <= row[0].x <= 20.0]

    svg = render_volute_view_svg(near)

    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert "The volute seen from behind and above" in svg
    # Shaded: the faces lit unevenly.
    fills = {part.split('"')[0] for part in svg.split('fill="rgb(')[1:]}
    assert len(fills) > 20
    assert render_volute_view_svg([]).startswith("<svg")


def test_the_web_app_draws_the_volute_or_with_it_off_the_root() -> None:
    drawing = {"headstock_pointed_volute": True, "headstock_volute_style": "drawn"}
    plain = back_view({"prototype": {}})
    arrow = back_view(
        {
            "prototype": {
                "headstock_pointed_volute": True,
                "headstock_volute_style": "arrow",
            }
        }
    )
    drawn = back_view(
        {
            "prototype": {
                **drawing,
                "headstock_volute_points": [[-5, 0], [0, 21]],
            }
        }
    )

    # With the volute off, the neck's back running into the headstock's.
    assert plain["svg"].startswith("<svg")
    assert arrow["svg"].startswith("<svg") and drawn["svg"].startswith("<svg")
    assert len({plain["svg"], arrow["svg"], drawn["svg"]}) == 3
    one_point = {**drawing, "headstock_volute_points": [[-5, 0]]}
    assert "error" in back_view({"prototype": one_point})


def test_the_root_and_heel_are_seen_too_the_heel_at_the_top() -> None:
    root = back_view(
        {"prototype": {"headstock_angle": 0.0, "headstock_root_style": "drawn"}}
    )
    heel = back_view({"prototype": {}}, "heel")

    assert root["svg"].startswith("<svg")
    assert "The heel seen from behind and above" in heel["svg"]
    # Smooth too: the joint as it is.
    assert back_view({"prototype": {}})["svg"].startswith("<svg")
    # No headstock, nothing to see round the nut.
    headless = INSTRUMENT_OVERRIDES["headless_guitar"]
    assert back_view({"prototype": {**headless}}) == {"svg": None}


def test_the_drawings_corner_is_found_once_not_at_every_corner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression: the drawing's corner was looked for again at every corner
    # drawn, and the view took seconds (on a phone, many).
    geometry = Prototype001Parameters().build()
    rows = FreeCADScriptExporter.neck_loft_rows(
        geometry.neck_surface,
        geometry.headstock,
        geometry.joint_fillet_radius,
        geometry.volute,
    )
    calls = []

    def counted_min(values: list[float]) -> float:
        calls.append(len(values))
        return min(values)

    monkeypatch.setattr(volute_view, "min", counted_min, raising=False)
    render_volute_view_svg(rows)

    assert len(calls) == 2  # the smallest x and the smallest y

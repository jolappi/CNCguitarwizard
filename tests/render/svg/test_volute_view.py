"""Tests for the volute's view from behind and above."""

from dataclasses import replace

from cncguitarwizard.backends.freecad.script_exporter import FreeCADScriptExporter
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.svg import render_volute_view_svg
from cncguitarwizard.webapp import volute_view


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


def test_the_web_app_draws_it_only_with_a_volute() -> None:
    drawing = {"headstock_pointed_volute": True, "headstock_volute_style": "drawn"}
    plain = volute_view({"prototype": {}})
    arrow = volute_view(
        {
            "prototype": {
                "headstock_pointed_volute": True,
                "headstock_volute_style": "arrow",
            }
        }
    )
    drawn = volute_view(
        {
            "prototype": {
                **drawing,
                "headstock_volute_points": [[-5, 0], [0, 21]],
            }
        }
    )

    assert plain == {"svg": None}
    assert arrow["svg"].startswith("<svg") and drawn["svg"].startswith("<svg")
    assert arrow["svg"] != drawn["svg"]
    one_point = {**drawing, "headstock_volute_points": [[-5, 0]]}
    assert "error" in volute_view({"prototype": one_point})

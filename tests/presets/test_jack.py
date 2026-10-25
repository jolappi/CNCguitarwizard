"""Tests for the output jack: on the edge, into the controls, its housings."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.prototype001 import JACK_CAVITY_OVERRUN
from cncguitarwizard.presets.styles import STYLES


def _along(jack, distance):  # type: ignore[no-untyped-def]
    import math

    radians = math.radians(jack.direction_degrees)
    return Point2D(
        jack.start_x + distance * math.cos(radians),
        jack.start_y + distance * math.sin(radians),
    )


@pytest.mark.parametrize("key", list(YOUR_DESIGN_TEMPLATES))
def test_the_jack_starts_on_the_edge_and_runs_into_the_controls(key: str) -> None:
    shape = YOUR_DESIGN_TEMPLATES[key][1]
    body = replace(Prototype001Parameters(), body_shape=shape).build().body
    jack = body.jack_hole
    outline = body.outline.points

    # Just inside the edge it is in the body, just outside it is not.
    assert point_in_polygon(_along(jack, 0.5), outline)
    assert not point_in_polygon(_along(jack, -0.5), outline)
    # It ends JACK_CAVITY_OVERRUN past the control cavity's wall.
    cavity = body.control_cavity.cavity.outline
    assert point_in_polygon(_along(jack, jack.depth), cavity)
    assert not point_in_polygon(
        _along(jack, jack.depth - JACK_CAVITY_OVERRUN - 0.5), cavity
    )


def test_a_cup_jack_gets_its_counterbore() -> None:
    geometry = replace(Prototype001Parameters(), body_jack="cup").build()
    jack = geometry.body.jack_hole

    assert (jack.cup_diameter, jack.cup_depth) == (22.2, 25.0)
    assert jack.depth > jack.cup_depth
    assert "BODY_CUTTERS.append(jack_bore)  # jack cup\n" in (
        FreeCADScriptExporter().render_prototype001(geometry)
    )


def test_a_strat_jack_is_a_cavity_from_the_top() -> None:
    body = replace(Prototype001Parameters(), body_jack="strat").build().body
    (cavity,) = [c for c in body.top_cavities if c.name == "Jack cavity"]
    jack = body.jack_hole

    # The bore runs on from the cavity's centre into the controls.
    xs = [p.x for p in cavity.outline]
    ys = [p.y for p in cavity.outline]
    assert (jack.start_x, jack.start_y) == pytest.approx(
        ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0), abs=0.01
    )
    assert max(xs) - min(xs) == pytest.approx(25.4, abs=0.1)
    assert all(point_in_polygon(p, body.outline.points) for p in cavity.outline)


def _across(jack, points):  # type: ignore[no-untyped-def]
    """Return ``points`` as (along the jack's line, across it) from its start."""
    import math

    radians = math.radians(jack.direction_degrees)
    ux, uy = math.cos(radians), math.sin(radians)
    return [
        (
            (p.x - jack.start_x) * ux + (p.y - jack.start_y) * uy,
            (p.y - jack.start_y) * ux - (p.x - jack.start_x) * uy,
        )
        for p in points
    ]


def test_a_stratocaster_has_its_oval_jack_route() -> None:
    style = STYLES["stratocaster"]
    values = style.prototype_values(style.instruments[0])
    assert values["body_jack"] == "oval"
    body = Prototype001Parameters(**values).build().body
    (cavity,) = [c for c in body.top_cavities if c.name == "Jack cavity"]
    jack = body.jack_hole

    # Its football route, as the user's Stratocaster drawing has it: 60.7
    # x 24 mm along the jack's line (the bore turned on to the controls).
    plain = replace(Prototype001Parameters(**values), body_jack_depth=40.0)
    straight = plain.build().body.jack_hole
    assert (straight.start_x, straight.start_y) == (jack.start_x, jack.start_y)
    along = _across(straight, cavity.outline)
    assert max(u for u, _ in along) - min(u for u, _ in along) == pytest.approx(
        60.7, abs=0.1
    )
    assert max(v for _, v in along) - min(v for _, v in along) == pytest.approx(
        24.0, abs=0.1
    )
    assert cavity.depth == 32.0
    assert all(point_in_polygon(p, body.outline.points) for p in cavity.outline)
    # Without the shape's inset: its edge tip 4 mm in along the line, the
    # bore from its middle (and no roundover, which would lower its rim).
    shape = replace(plain.body_shape, jack_inset=None)
    body = replace(plain, body_shape=shape, body_top_edge_radius=0.0).build().body
    (cavity,) = [c for c in body.top_cavities if c.name == "Jack cavity"]
    edge_tip = min(u for u, _ in _across(body.jack_hole, cavity.outline))
    assert edge_tip == pytest.approx(-28.98, abs=0.05)
    assert point_in_polygon(_along(body.jack_hole, edge_tip - 3.5), body.outline.points)
    assert not point_in_polygon(
        _along(body.jack_hole, edge_tip - 4.5), body.outline.points
    )


def test_a_fixed_depth_overrides_the_reach_and_a_bad_jack_is_refused() -> None:
    fixed = replace(Prototype001Parameters(), body_jack_depth=30.0).build()
    assert fixed.body.jack_hole.depth == 30.0
    with pytest.raises(BodyGeometryError, match="Unknown jack"):
        replace(Prototype001Parameters(), body_jack="banana").build()  # type: ignore[arg-type]

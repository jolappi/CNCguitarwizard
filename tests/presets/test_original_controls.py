"""Tests for the controls, jacks, pickups and guards placed as on the
originals: the Fender and Gibson styles and a Jackson Rhoads."""

import math
from dataclasses import replace
from functools import cache

import pytest

from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Geometry, Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.controls import TELE_PLATE
from cncguitarwizard.presets.prototype001 import POCKET_MOUTH
from cncguitarwizard.presets.styles import STYLES


def styled(key: str, **changes: object) -> Prototype001Parameters:
    """Return a style's electric guitar, changed as asked."""
    return replace(
        Prototype001Parameters.for_instrument("electric_guitar"),
        **{**STYLES[key].prototype_values("electric_guitar"), **changes},
    )


@cache
def built(key: str) -> Prototype001Geometry:
    """Return a style's electric guitar, built."""
    return styled(key).build()


def heel_end(parameters: Prototype001Parameters) -> float:
    outline = parameters.neck_outline()
    return outline.last_fret_position + parameters.heel_length


def control_cavity_outline(geometry: Prototype001Geometry) -> tuple[Point2D, ...]:
    body = geometry.body
    if body.control_cavity is not None:
        return body.control_cavity.cavity.outline
    (cavity,) = [c for c in body.control_top_cavities if c.name == "Control cavity"]
    return cavity.outline


def jack_reaches_the_controls(geometry: Prototype001Geometry) -> bool:
    jack = geometry.body.jack_hole
    assert jack is not None
    angle = math.radians(jack.direction_degrees)
    end = Point2D(
        jack.start_x + (jack.depth - 1.0) * math.cos(angle),
        jack.start_y + (jack.depth - 1.0) * math.sin(angle),
    )
    return point_in_polygon(end, control_cavity_outline(geometry))


def test_a_telecaster_plate_is_a_52s() -> None:
    geometry = built("telecaster")
    (plate,) = [c for c in geometry.covers if c.name == "Control plate"]
    xs = [p.x for p in plate.outline]
    ys = [p.y for p in plate.outline]
    # About 6 1/8 x 1 1/4 in, nearly along the strings, out on the treble side.
    assert max(xs) - min(xs) == pytest.approx(TELE_PLATE.length, abs=0.5)
    assert max(ys) - min(ys) == pytest.approx(TELE_PLATE.width, abs=4.0)
    assert min(ys) > 70.0
    pots = sorted(
        (h for h in plate.holes if h.name.startswith("Pot")), key=lambda h: h.center_x
    )
    assert pots[1].center_x - pots[0].center_x == pytest.approx(59.0, abs=0.5)
    # Its jack in the treble side, level with the tone pot, not in the tail.
    jack = geometry.body.jack_hole
    assert jack is not None and jack.start_y > 150.0
    assert abs(jack.start_x - pots[1].center_x) < 20.0
    assert jack_reaches_the_controls(geometry)
    # The bridge pickup slanted as a Telecaster's.
    assert styled("telecaster").body_bridge_single_coil_angle == 16.0


def test_a_stratocaster_has_its_guard_controls_and_jack_as_drawn() -> None:
    parameters = styled("stratocaster")
    geometry = built("stratocaster")
    shape = parameters.body_shape
    heel = heel_end(parameters)
    # The template's own guard, over the template's own controls.
    layout = parameters.body_layout()
    assert layout.pickguard is not None and not layout.pickguard.automatic
    (guard,) = [c for c in geometry.covers if c.name == "Pickguard"]
    pots = [h for h in guard.holes if h.name.startswith("Control pot")]
    assert [(round(h.center_x - heel, 1), round(h.center_y, 1)) for h in pots] == [
        tuple(p) for p in shape.pickguard_controls[1:]
    ]
    cavity = control_cavity_outline(geometry)
    assert [(round(p.x - heel, 1), round(p.y, 1)) for p in cavity] == [
        tuple(p) for p in shape.pickguard_cavity_points
    ]
    assert all(point_in_polygon(Point2D(h.center_x, h.center_y), cavity) for h in pots)
    # The jack's cavity in its angled plate, well in from the edge, its
    # bore wired into the control cavity.
    (jack_cavity,) = [c for c in geometry.body.top_cavities if c.name == "Jack cavity"]
    centre = Point2D(
        sum(p.x for p in jack_cavity.outline) / len(jack_cavity.outline),
        sum(p.y for p in jack_cavity.outline) / len(jack_cavity.outline),
    )
    assert centre.x - heel == pytest.approx(shape.jack_offset, abs=0.1)
    assert centre.y == pytest.approx(shape.jack_y, abs=0.1)
    assert jack_reaches_the_controls(geometry)


def test_a_les_paul_has_its_four_pots_staggered_and_a_side_jack() -> None:
    parameters = styled("les_paul")
    geometry = built("les_paul")
    heel = heel_end(parameters)
    pots = sorted(
        (h for h in geometry.body.holes if h.name.startswith("Control pot")),
        key=lambda h: (h.center_y, h.center_x),
    )
    assert sorted(
        (round(h.center_x - heel, 1), round(h.center_y, 1)) for h in pots
    ) == sorted(tuple(p) for p in parameters.body_shape.rear_pots)
    # The volumes nearer the strings, each pair stepped back.
    inner, outer = pots[:2], pots[2:]
    assert max(h.center_y for h in inner) < min(h.center_y for h in outer)
    cavity = control_cavity_outline(geometry)
    assert all(point_in_polygon(Point2D(h.center_x, h.center_y), cavity) for h in pots)
    assert jack_reaches_the_controls(geometry)
    # Its bridge pickup as far ahead of the bridge as a '59's.
    assert parameters.body_bridge_pickup_offset == pytest.approx(39.6)


def test_an_sg_has_its_jack_in_the_top_and_the_toggle_on_the_horn() -> None:
    parameters = styled("sg")
    geometry = built("sg")
    shape = parameters.body_shape
    heel = heel_end(parameters)
    assert geometry.body.jack_hole is None
    (jack,) = [h for h in geometry.body.holes if h.name == "Jack hole"]
    assert (jack.center_x - heel, jack.center_y) == pytest.approx(
        (shape.jack_offset, shape.jack_y)
    )
    # Drilled through into the control cavity, routed round it too.
    assert jack.depth == parameters.body_thickness
    assert point_in_polygon(
        Point2D(jack.center_x, jack.center_y), control_cavity_outline(geometry)
    )
    switch = geometry.body.switch_cavity
    assert switch is not None
    assert switch.cavity.center_x - heel == pytest.approx(204.5)


def test_a_jack_in_the_top_needs_a_rear_cavity_under_it() -> None:
    with pytest.raises(BodyGeometryError, match="has none"):
        styled("sg", body_controls="tele").body_layout()
    lost = replace(styled("sg").body_shape, jack_offset=60.0, jack_y=-60.0)
    with pytest.raises(BodyGeometryError, match="not under it"):
        styled("sg", body_controls="almond_2", body_shape=lost).body_layout()


def test_a_rhoads_toggle_shares_the_pots_cavity() -> None:
    geometry = built("jackson_rr")
    assert geometry.body.switch_cavity is None
    (switch,) = [h for h in geometry.body.holes if h.name == "Switch shaft hole"]
    assert point_in_polygon(
        Point2D(switch.center_x, switch.center_y), control_cavity_outline(geometry)
    )
    assert jack_reaches_the_controls(geometry)


def test_an_explorer_has_its_toggle_on_the_horn_and_its_pots_in_a_row() -> None:
    parameters = styled("explorer")
    geometry = built("explorer")
    heel = heel_end(parameters)
    switch = geometry.body.switch_cavity
    assert switch is not None and switch.cavity.center_x < heel
    pots = sorted(
        (h for h in geometry.body.holes if h.name.startswith("Control pot")),
        key=lambda h: h.center_x,
    )
    assert len(pots) == 3
    # Stepping in toward the tail along the lower treble edge.
    assert pots[0].center_y > pots[1].center_y > pots[2].center_y
    assert jack_reaches_the_controls(geometry)


@pytest.mark.parametrize(
    "key", ["telecaster", "stratocaster", "les_paul", "sg", "explorer", "jackson_rr"]
)
def test_the_originals_build_left_handed(key: str) -> None:
    styled(key, handedness="left").build()


def test_the_neck_pocket_opens_through_a_body_reaching_further_forward() -> None:
    shape = YOUR_DESIGN_TEMPLATES["telecaster"][1]
    forward = replace(
        shape,
        control_points=tuple((x - 30.0, y) for x, y in shape.control_points),
    )
    parameters = replace(Prototype001Parameters(), body_shape=forward)
    heel = heel_end(parameters)
    layout = parameters.body_layout()
    front = min(
        p.x
        for p in layout.outline.points
        if abs(p.y) <= parameters.heel_width / 2.0 and p.x < heel
    )
    start = min(p.x for p in layout.neck_pocket.outline)
    assert start == pytest.approx(front - POCKET_MOUTH, abs=0.01)
    assert heel - start > parameters.body_neck_pocket_length

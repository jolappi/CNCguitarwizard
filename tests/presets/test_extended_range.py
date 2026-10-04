"""Tests for the seven- and eight-string guitars."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.body import (
    FloydRoseSpec,
    HardtailSpec,
    KahlerBridgeSpec,
    TuneOMaticSpec,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError, NeckGeometryError
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import (
    YOUR_DESIGN_TEMPLATES,
    widen_points,
    widened_shape,
)
from cncguitarwizard.presets.pickups import pickup_route, pickup_screws, pickup_stretch


@pytest.fixture(scope="module", params=["seven_string_guitar", "eight_string_guitar"])
def extended(request):  # type: ignore[no-untyped-def]
    return request.param, Prototype001Parameters.for_instrument(request.param)


def test_the_extended_range_guitars_build_with_a_hole_per_string(extended) -> None:  # type: ignore[no-untyped-def]
    name, parameters = extended
    strings = 7 if name.startswith("seven") else 8
    geometry = parameters.build()

    assert len(geometry.tuner_layout.holes) == strings
    through = [h for h in geometry.body.holes if h.name.startswith("String")]
    assert len(through) == strings
    assert geometry.tuner_layout.minimum_side_edge_clearance >= 8.0 - 1e-9
    body = geometry.body
    for cavity in (body.neck_pickup, body.bridge_pickup):
        assert cavity is not None
        assert all(point_in_polygon(p, body.outline.points) for p in cavity.outline)


def test_the_body_opens_along_the_centreline(extended) -> None:  # type: ignore[no-untyped-def]
    name, parameters = extended
    strings = 7 if name.startswith("seven") else 8
    six = Prototype001Parameters().body_layout().outline.points
    wide = parameters.body_layout().outline.points

    assert parameters.body_widening_amount() == 12.0 * (strings - 6)
    width = max(p.y for p in wide) - min(p.y for p in wide)
    assert width == pytest.approx(
        max(p.y for p in six) - min(p.y for p in six) + 12.0 * (strings - 6)
    )
    assert replace(parameters, body_widening=0.0).body_widening_amount() == 0.0


def test_every_drawn_template_takes_an_eight_string_neck() -> None:
    base = Prototype001Parameters.for_instrument("eight_string_guitar")
    for key, (_, shape) in YOUR_DESIGN_TEMPLATES.items():
        if key.startswith("bass"):
            continue
        for pickups in ("HH", "HSS", "SSS"):
            replace(base, body_shape=shape, body_pickups=pickups).build()


def test_widening_moves_each_half_out_and_keeps_the_centreline() -> None:
    assert widen_points(((1.0, 5.0), (2.0, -5.0), (3.0, 0.0)), 10.0) == (
        (1.0, 10.0),
        (2.0, -10.0),
        (3.0, 0.0),
    )
    shape = YOUR_DESIGN_TEMPLATES["stratocaster"][1]
    moved = widened_shape(shape, 12.0)
    assert moved.jack_y == pytest.approx(shape.jack_y + 6.0)
    assert moved.pot_offsets[0][1] == pytest.approx(shape.pot_offsets[0][1] + 6.0)
    assert moved.neck_bolts == shape.neck_bolts
    assert widened_shape(shape, 0.0) is shape


def test_guitar_pickups_stretch_across_the_strings() -> None:
    assert pickup_stretch("humbucker", 6) == 0.0
    assert pickup_stretch("humbucker", 8) == 24.0
    assert pickup_stretch("jazz_bass", 8) == 0.0
    six = pickup_route("humbucker", "H", 0.0, 20.0, -1.0)
    eight = pickup_route("humbucker", "H", 0.0, 20.0, -1.0, string_count=8)
    assert six is not None and eight is not None

    def span(cavity) -> float:  # type: ignore[no-untyped-def]
        return max(p.y for p in cavity.outline) - min(p.y for p in cavity.outline)

    assert span(eight) == pytest.approx(span(six) + 24.0)
    screws = pickup_screws("humbucker", 0.0, -1.0, 79.9, string_count=8)
    assert abs(screws[0][2] - screws[1][2]) == pytest.approx(79.9 + 24.0)


def test_six_string_bridges_are_refused_for_more_strings() -> None:
    base = Prototype001Parameters.for_instrument("seven_string_guitar")
    with pytest.raises(BodyGeometryError, match="made for 6 strings"):
        replace(base, body_bridge=TuneOMaticSpec()).body_layout()
    # The Kahler and the Floyd Rose come for seven strings, set so.
    for bridge in (KahlerBridgeSpec(), FloydRoseSpec()):
        with pytest.raises(BodyGeometryError, match="set for 6 strings"):
            replace(base, body_bridge=bridge).body_layout()
    with pytest.raises(BodyGeometryError, match="6 string holes"):
        replace(base, body_bridge=HardtailSpec()).body_layout()


def test_a_4_plus_3_headstock_spreads_its_tuners_to_clear_each_other() -> None:
    base = Prototype001Parameters.for_instrument("seven_string_guitar")
    geometry = replace(base, headstock_style="4+3").build()
    layout = geometry.tuner_layout

    assert (len(layout.holes_on("bass")), len(layout.holes_on("treble"))) == (4, 3)
    six = replace(Prototype001Parameters(), headstock_style="4+2")._headstock_layout()
    assert six.stations[:2] == (50.0, 75.4)


def test_negative_widening_is_refused() -> None:
    with pytest.raises(NeckGeometryError, match="widening"):
        replace(Prototype001Parameters(), body_widening=-1.0).build()

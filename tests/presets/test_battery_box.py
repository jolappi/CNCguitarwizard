"""Tests for the optional rear 9 V battery box and its cover."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.cam import plan_cover_machining
from cncguitarwizard.cam.body import plan_body_machining
from cncguitarwizard.cam.covers import cover_setup_name
from cncguitarwizard.cam.parameters import MachiningParameters
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import (
    YOUR_DESIGN_TEMPLATES,
    DesignByJoneShape,
    YourDesignShape,
    widened_shape,
)


def with_battery(**overrides: object) -> Prototype001Parameters:
    return replace(Prototype001Parameters(), body_battery_box=True, **overrides)


def span(points):  # type: ignore[no-untyped-def]
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return max(xs) - min(xs), max(ys) - min(ys)


def test_the_battery_box_is_off_by_default() -> None:
    geometry = Prototype001Parameters().build()

    assert geometry.body.battery_cavity is None
    assert all("Battery" not in cover.name for cover in geometry.covers)


def test_the_battery_box_is_a_rear_cavity_with_a_cover_and_two_screws() -> None:
    # Square to the neck, so its sizes read straight off the outline.
    parameters = with_battery(
        body_shape=replace(
            DesignByJoneShape(),
            battery_offset=210.0,
            battery_y=-60.0,
            battery_angle_degrees=0.0,
        )
    )
    geometry = parameters.build()
    battery = geometry.body.battery_cavity

    assert battery is not None
    assert battery in geometry.body.rear_cavities
    assert battery.cavity.depth == 22.0
    assert battery.cover_recess.depth == parameters.body_cover_recess_depth
    assert span(battery.cavity.outline) == pytest.approx((56.0, 30.0), abs=0.01)
    assert span(battery.cover_recess.outline) == pytest.approx((70.0, 44.0), abs=0.01)
    # A 9 V battery (48.5 x 26.5 mm) fits inside the rounded box.
    heel_end = parameters.body_layout().heel_end
    centre_x = heel_end + parameters.body_shape.battery_offset
    centre_y = parameters.body_shape.battery_y
    corners = [
        (centre_x + sx * 24.25, centre_y + sy * 13.25)
        for sx in (-1, 1)
        for sy in (-1, 1)
    ]
    assert all(
        point_in_polygon(type(battery.cavity.outline[0])(x, y), battery.cavity.outline)
        for x, y in corners
    )
    (cover,) = [c for c in geometry.covers if c.name == "Battery cavity cover"]
    assert cover.face == "back"
    assert len(cover.holes) == 2
    marks = [
        m for m in geometry.body.control_back_marks if m.name.startswith("Battery")
    ]
    assert len(marks) == 2
    for mark, hole in zip(marks, cover.holes, strict=True):
        assert (mark.center_x, mark.center_y) == (hole.center_x, hole.center_y)
        # Each screw sits on the ledge, outside the box, inside the cover.
        assert not point_in_polygon(
            type(battery.cavity.outline[0])(mark.center_x, mark.center_y),
            battery.cavity.outline,
        )


def test_the_default_battery_box_sits_close_to_the_control_cavity() -> None:
    # The lead's channel to the controls is drilled by hand: keep it short.
    for name in ("design_by_jone_shape", "new_drawing", *YOUR_DESIGN_TEMPLATES):
        shape = BODIES[name]
        instrument = "bass_guitar" if "bass" in name else "electric_guitar"
        layout = replace(
            Prototype001Parameters.for_instrument(instrument),
            body_shape=shape,
            body_battery_box=True,
        ).body_layout()
        battery = layout.controls.battery_cavity
        assert battery is not None and layout.control_cavity is not None
        control = layout.control_cavity.cavity.outline
        gap = min(
            math.dist((p.x, p.y), (q.x, q.y))
            for p in battery.cavity.outline
            for q in control
        )
        assert gap < 35.0, name


def test_the_battery_box_turns_with_its_angle() -> None:
    shape = replace(DesignByJoneShape(), battery_angle_degrees=90.0)
    battery = with_battery(body_shape=shape).body_layout().controls.battery_cavity

    assert battery is not None
    assert span(battery.cavity.outline) == pytest.approx((30.0, 56.0), abs=0.01)


def test_a_battery_box_outside_the_body_is_rejected() -> None:
    shape = replace(DesignByJoneShape(), battery_y=400.0)

    with pytest.raises(BodyGeometryError, match="Battery cavity"):
        with_battery(body_shape=shape).build()


def test_a_battery_box_too_deep_for_the_body_is_rejected() -> None:
    with pytest.raises(BodyGeometryError, match="Battery cavity"):
        with_battery(body_battery_cavity_depth=40.0).build()


BODIES = {
    "design_by_jone_shape": DesignByJoneShape(),
    "new_drawing": YourDesignShape(),
    **{key: shape for key, (_, shape) in YOUR_DESIGN_TEMPLATES.items()},
}


@pytest.mark.parametrize("name", list(BODIES))
def test_every_body_has_room_for_its_default_battery_box(name: str) -> None:
    shape = BODIES[name]
    instrument = "bass_guitar" if "bass" in name else "electric_guitar"
    parameters = replace(
        Prototype001Parameters.for_instrument(instrument),
        body_shape=shape,
        body_battery_box=True,
    )
    for layout in ("almond_2", "gibson_4", "rear_3", "tele", "none"):
        replace(parameters, body_controls=layout).build()


def test_a_widened_body_moves_the_battery_box_out_with_its_half() -> None:
    shape = replace(DesignByJoneShape(), battery_y=40.0)

    assert widened_shape(shape, 12.0).battery_y == pytest.approx(46.0)


def test_the_battery_box_is_cut_with_the_electronics_and_its_cover_from_sheet() -> None:
    geometry = with_battery().build()
    machining = MachiningParameters()
    plan = plan_body_machining(geometry.body, machining)
    assert plan.back_controls is not None
    names = [path.name for path in plan.back_controls.toolpaths]
    assert any(name.startswith("Battery cavity") for name in names)
    covers = plan_cover_machining(geometry.covers, machining)
    assert covers is not None
    battery_cover = next(c for c in geometry.covers if c.name == "Battery cavity cover")
    assert cover_setup_name(battery_cover) == "Cover_battery_cavity"
    assert "Cover_battery_cavity" in [setup.name for setup in covers.covers]
    assert not math.isnan(battery_cover.thickness)


def test_a_box_for_two_batteries_holds_them_side_by_side() -> None:
    # Further out than the single box's test, clear of the bridge.
    shape = replace(
        DesignByJoneShape(),
        battery_offset=210.0,
        battery_y=-75.0,
        battery_angle_degrees=0.0,
    )
    one = with_battery(body_shape=shape).build().body.battery_cavity
    two = with_battery(body_shape=shape, body_battery_count=2).build()
    battery = two.body.battery_cavity

    assert one is not None and battery is not None
    # 28 mm wider: a second 26.5 mm battery and 1.5 mm between the two.
    assert span(battery.cavity.outline) == pytest.approx((56.0, 58.0), abs=0.01)
    assert span(battery.cover_recess.outline) == pytest.approx((70.0, 72.0), abs=0.01)
    (cover,) = [c for c in two.covers if c.name == "Battery cavity cover"]
    assert cover.outline == battery.cover_recess.outline
    assert len(cover.holes) == 2


@pytest.mark.parametrize("count", [0, 3])
def test_a_battery_box_holds_one_or_two_batteries(count: int) -> None:
    with pytest.raises(BodyGeometryError, match="one or two"):
        with_battery(body_battery_count=count).build()

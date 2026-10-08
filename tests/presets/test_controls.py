"""Tests for the electronics layouts: cavities, screw spots and cover plates."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.cam import MachiningParameters, plan_cover_machining
from cncguitarwizard.geometry.body import (
    FloydRoseSpec,
    cover_screw_points,
    outlines_overlap,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES, YourDesignShape
from cncguitarwizard.presets.controls import CONTROL_LABELS

LAYOUTS = tuple(CONTROL_LABELS)


def build(layout: str, **overrides: object):  # type: ignore[no-untyped-def]
    return replace(Prototype001Parameters(), body_controls=layout, **overrides).build()


def test_every_layout_has_a_label() -> None:
    assert set(LAYOUTS) == {
        "almond_2",
        "gibson_4",
        "rear_3",
        "superstrat",
        "volume_1",
        "active_4",
        "tele",
        "jazz_bass",
        "pickguard",
        "none",
    }


# The pickguard layout brings its own guard (see test_pickguard.py).
@pytest.mark.parametrize("layout", LAYOUTS)
def test_every_layout_builds_on_every_drawn_template(layout: str) -> None:
    for name, (_, shape) in YOUR_DESIGN_TEMPLATES.items():
        instrument = "bass_guitar" if "bass" in name else "electric_guitar"
        parameters = replace(
            Prototype001Parameters.for_instrument(instrument),
            body_shape=shape,
            body_controls=layout,
        )
        geometry = parameters.build()
        outline = geometry.body.outline.points
        for cover in geometry.covers:
            assert all(point_in_polygon(p, outline) for p in cover.outline), name


def test_the_gibson_layout_has_four_pots_and_two_back_covers() -> None:
    geometry = build("gibson_4")
    body = geometry.body
    pots = [hole for hole in body.holes if hole.name.startswith("Control pot")]

    assert len(pots) == 4
    assert body.control_cavity is not None and body.switch_cavity is not None
    assert [cover.name for cover in geometry.covers] == [
        "Control cavity cover",
        "Switch cavity cover",
    ]
    assert all(cover.face == "back" for cover in geometry.covers)
    for pot in pots:
        assert body.control_cavity.depth_at(pot.center) is not None


def test_cover_screws_sit_on_the_ledge_and_are_spotted_from_its_floor() -> None:
    geometry = build("gibson_4")
    body = geometry.body
    assert body.control_cavity is not None
    rear = body.control_cavity
    screws = [m for m in body.control_back_marks if m.name.startswith("Control")]

    assert len(screws) == 4
    for screw in screws:
        assert point_in_polygon(screw.center, rear.cover_recess.outline)
        assert not point_in_polygon(screw.center, rear.cavity.outline)
        assert screw.depth == pytest.approx(rear.cover_recess.depth + 1.0)
    cover = geometry.covers[0]
    assert [hole.name for hole in cover.holes] == [f"Screw {i}" for i in range(1, 5)]
    assert {(h.center_x, h.center_y) for h in cover.holes} == {
        (s.center_x, s.center_y) for s in screws
    }


def test_the_rear_layout_puts_three_pots_in_a_row() -> None:
    body = build("rear_3").body
    pots = [hole for hole in body.holes if hole.name.startswith("Control pot")]

    assert len(pots) == 3
    assert len({round(pot.center_y, 6) for pot in pots}) == 1


def test_the_tele_layout_routes_a_plate_into_the_top() -> None:
    geometry = build("tele")
    body = geometry.body

    assert body.control_cavity is None and body.switch_cavity is None
    names = [cavity.name for cavity in body.control_top_cavities]
    assert names == ["Control plate recess", "Control cavity"]
    assert all(cavity in body.top_cavities for cavity in body.control_top_cavities)
    recess, cavity = body.control_top_cavities
    assert body.step_start_depth(cavity) == pytest.approx(recess.depth)
    (plate,) = geometry.covers
    assert plate.face == "top" and plate.thickness == recess.depth
    assert [hole.name for hole in plate.holes][:2] == [
        "Pot 1 shaft hole",
        "Pot 2 shaft hole",
    ]
    assert [slot.name for slot in plate.slots] == ["Blade switch slot"]
    assert len(body.control_top_marks) == 2


def test_no_controls_leaves_no_electronics() -> None:
    geometry = build("none")
    body = geometry.body

    assert body.control_cavity is None and body.switch_cavity is None
    assert not body.control_top_cavities and not body.control_back_marks
    assert geometry.covers == ()
    assert not any("pot" in hole.name.lower() for hole in body.holes)


def test_screw_points_go_to_the_corners_of_a_rectangular_ledge() -> None:
    def rectangle(half_x: float, half_y: float) -> tuple[Point2D, ...]:
        return (
            Point2D(-half_x, -half_y),
            Point2D(half_x, -half_y),
            Point2D(half_x, half_y),
            Point2D(-half_x, half_y),
        )

    points = cover_screw_points(rectangle(30, 20), rectangle(36, 26), 4, 5.0)

    # The rays run toward the cover's corners; each screw sits halfway
    # between where its ray leaves the cavity and the cover.
    assert len(points) == 4
    assert {(round(abs(p.x), 3), round(abs(p.y), 3)) for p in points} == {
        (31.846, 23.0)
    }
    assert {(p.x > 0, p.y > 0) for p in points} == {
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    }
    # A ledge narrower than the minimum gets no screws at all.
    assert cover_screw_points(rectangle(30, 20), rectangle(32, 22), 4, 5.0) == ()


@pytest.mark.parametrize("template", ["stratocaster", "les_paul", "jackson_rr"])
def test_a_gibson_cavity_moves_clear_of_a_floyd_rose(template: str) -> None:
    # In place, the Gibson cavity would rout into the Floyd Rose's
    # fine-tuner recess with no wood between the floors; the layout moves
    # out (and along the neck) until it clears, pots and cover with it.
    shape = YOUR_DESIGN_TEMPLATES[template][1]
    parameters = replace(
        Prototype001Parameters(),
        body_shape=shape,
        body_controls="gibson_4",
        body_bridge=FloydRoseSpec(),
    )
    body = parameters.build().body
    cavity = body.control_cavity.cavity
    recess = next(c for c in body.extra_cavities if "fine-tuner" in c.name)
    assert not outlines_overlap(cavity.outline, recess.outline)
    unmoved = replace(parameters, body_bridge=Prototype001Parameters().body_bridge)
    assert cavity.min_y > unmoved.build().body.control_cavity.cavity.min_y


def test_a_floyd_rose_spring_cavity_gets_a_six_screw_cover() -> None:
    geometry = replace(Prototype001Parameters(), body_bridge=FloydRoseSpec()).build()
    (rear,) = geometry.body.extra_rear_cavities
    (cover,) = [
        c for c in geometry.covers if c.name == "Floyd Rose spring cavity cover"
    ]

    assert cover.face == "back"
    assert cover.outline == rear.cover_recess.outline
    assert cover.thickness == rear.cover_recess.depth
    assert len(cover.holes) == 6
    marks = [
        m for m in geometry.body.control_back_marks if m.name.startswith("Floyd Rose")
    ]
    assert len(marks) == 6
    for mark in marks:
        # On the ledge: inside the recess, outside the spring cavity.
        centre = Point2D(mark.center_x, mark.center_y)
        assert point_in_polygon(centre, rear.cover_recess.outline)
        assert not point_in_polygon(centre, rear.cavity.outline)
    plan = plan_cover_machining(geometry.covers, MachiningParameters())
    assert plan is not None
    assert "Cover_floyd_rose_spring_cavity" in [s.name for s in plan.covers]


def test_the_pickup_selector_can_be_a_micro_toggle() -> None:
    def switch_hole(**overrides: object) -> float:
        body = replace(Prototype001Parameters(), **overrides).build().body
        (hole,) = [h for h in body.holes if h.name == "Switch shaft hole"]
        return hole.diameter

    # A 3-way toggle's 1/2 in bushing by default, a micro toggle's 1/4 in.
    assert switch_hole() == 12.7
    assert switch_hole(body_switch="micro") == 6.35
    # A hole given by hand wins.
    assert switch_hole(body_switch="micro", body_switch_shaft_hole_diameter=7.0) == 7.0


def _centre(points):  # type: ignore[no-untyped-def]
    return (
        sum(p.x for p in points) / len(points),
        sum(p.y for p in points) / len(points),
    )


@pytest.mark.parametrize("layout", ["almond_2", "gibson_4", "rear_3"])
def test_the_control_cavity_turns_about_its_centre(layout: str) -> None:
    def build_turned(degrees: float):  # type: ignore[no-untyped-def]
        shape = replace(YourDesignShape(), control_angle_degrees=degrees)
        return (
            replace(Prototype001Parameters(), body_shape=shape, body_controls=layout)
            .build()
            .body
        )

    square, turned = build_turned(0.0), build_turned(30.0)
    before, after = square.control_cavity, turned.control_cavity
    # The same cavity, turned in place: its centre stays, its corners move.
    assert _centre(after.cavity.outline) == pytest.approx(
        _centre(before.cavity.outline), abs=1e-6
    )
    assert after.cavity.outline != before.cavity.outline
    # The cover turns with it, about the same centre.
    cx, cy = _centre(before.cavity.outline)
    (bx, by), (ax, ay) = (
        _centre(before.cover_recess.outline),
        _centre(after.cover_recess.outline),
    )
    assert math.hypot(ax - cx, ay - cy) == pytest.approx(
        math.hypot(bx - cx, by - cy), abs=0.05
    )
    if layout != "almond_2":
        # A generated layout's own pots turn about the cavity's centre.
        def pots(body):  # type: ignore[no-untyped-def]
            return [
                (h.center_x, h.center_y)
                for h in body.holes
                if h.name.startswith("Control pot")
            ]

        for (x0, y0), (x1, y1) in zip(pots(square), pots(turned), strict=True):
            assert math.hypot(x1 - cx, y1 - cy) == pytest.approx(
                math.hypot(x0 - cx, y0 - cy)
            )
            if math.hypot(x0 - cx, y0 - cy) < 1e-6:
                continue  # A pot at the centre stays put.
            bearing = math.degrees(
                math.atan2(y1 - cy, x1 - cx) - math.atan2(y0 - cy, x0 - cx)
            )
            assert (bearing + 360.0) % 360.0 == pytest.approx(30.0, abs=1e-6)


def test_the_tele_plate_turns_with_its_pots_screws_and_slot() -> None:
    shape = replace(YourDesignShape(), control_angle_degrees=8.0)
    geometry = replace(
        Prototype001Parameters(), body_shape=shape, body_controls="tele"
    ).build()
    (plate,) = geometry.covers
    recess = next(c for c in geometry.body.control_top_cavities if "recess" in c.name)

    assert plate.outline == recess.outline
    pots = [h for h in plate.holes if h.name.startswith("Pot")]
    # The two pots lie on the plate's turned long axis.
    (a, b) = pots
    assert math.degrees(
        math.atan2(b.center_y - a.center_y, b.center_x - a.center_x)
    ) == pytest.approx(8.0)
    (slot,) = plate.slots
    assert all(point_in_polygon(p, plate.outline) for p in slot.outline)


def _axis_length(outline, axis) -> float:  # type: ignore[no-untyped-def]
    along = [p.x * axis[0] + p.y * axis[1] for p in outline]
    return max(along) - min(along)


@pytest.mark.parametrize("layout", ["almond_2", "gibson_4", "rear_3"])
@pytest.mark.parametrize("stretch", [24.0, -12.0])
def test_the_control_cavity_stretches_from_its_centre(
    layout: str, stretch: float
) -> None:
    def build_stretched(amount: float):  # type: ignore[no-untyped-def]
        shape = replace(
            YourDesignShape(), control_stretch=amount, control_angle_degrees=20.0
        )
        parameters = replace(
            Prototype001Parameters(), body_shape=shape, body_controls=layout
        )
        return parameters.body_layout().controls

    plain, stretched = build_stretched(0.0), build_stretched(stretch)
    axis = (plain.control_axis.x, plain.control_axis.y)
    assert stretched.control_centre == plain.control_centre
    # Both the cavity and its cover grow (or shrink) by the stretch along
    # the turned long axis, and keep their width across it.
    across = (-axis[1], axis[0])
    for old, new in (
        (plain.control_cavity.cavity, stretched.control_cavity.cavity),
        (plain.control_cavity.cover_recess, stretched.control_cavity.cover_recess),
    ):
        assert _axis_length(new.outline, axis) == pytest.approx(
            _axis_length(old.outline, axis) + stretch, abs=0.05
        )
        assert _axis_length(new.outline, across) == pytest.approx(
            _axis_length(old.outline, across), abs=0.05
        )
    # The cover still holds the cavity and its screws sit on the ledge.
    rear = stretched.control_cavity
    assert all(
        point_in_polygon(p, rear.cover_recess.outline) for p in rear.cavity.outline
    )
    for mark in stretched.back_marks:
        if mark.name.startswith("Control cavity cover screw"):
            spot = Point2D(mark.center_x, mark.center_y)
            assert point_in_polygon(spot, rear.cover_recess.outline)
            assert not point_in_polygon(spot, rear.cavity.outline)


@pytest.mark.parametrize("layout", ["gibson_4", "rear_3"])
def test_a_stretched_layout_moves_its_end_pots_out(layout: str) -> None:
    def pots(amount: float):  # type: ignore[no-untyped-def]
        shape = replace(YourDesignShape(), control_stretch=amount)
        body = (
            replace(Prototype001Parameters(), body_shape=shape, body_controls=layout)
            .build()
            .body
        )
        return sorted(
            (h.center_x, h.center_y)
            for h in body.holes
            if h.name.startswith("Control pot")
        )

    before, after = pots(0.0), pots(20.0)
    assert after[0][0] == pytest.approx(before[0][0] - 10.0)
    assert after[-1][0] == pytest.approx(before[-1][0] + 10.0)


def test_the_tele_plate_stretches_with_its_screws_and_slot() -> None:
    def plate(amount: float):  # type: ignore[no-untyped-def]
        shape = replace(YourDesignShape(), control_stretch=amount)
        (cover,) = (
            replace(Prototype001Parameters(), body_shape=shape, body_controls="tele")
            .build()
            .covers
        )
        return cover

    before, after = plate(0.0), plate(30.0)
    assert span_x(after.outline) == pytest.approx(span_x(before.outline) + 30.0)
    screws = sorted(h.center_x for h in after.holes if h.name.startswith("Screw"))
    old_screws = sorted(h.center_x for h in before.holes if h.name.startswith("Screw"))
    assert screws[0] == pytest.approx(old_screws[0] - 15.0)
    assert screws[1] == pytest.approx(old_screws[1] + 15.0)
    (slot,) = after.slots
    assert all(point_in_polygon(p, after.outline) for p in slot.outline)


def span_x(points) -> float:  # type: ignore[no-untyped-def]
    xs = [p.x for p in points]
    return max(xs) - min(xs)


@pytest.mark.parametrize(
    ("layout", "stretch"),
    [("almond_2", -200.0), ("gibson_4", -60.0), ("tele", -150.0)],
)
def test_a_control_cavity_cannot_shrink_past_its_rounded_ends(
    layout: str, stretch: float
) -> None:
    shape = replace(YourDesignShape(), control_stretch=stretch)
    parameters = replace(
        Prototype001Parameters(), body_shape=shape, body_controls=layout
    )

    with pytest.raises(BodyGeometryError):
        parameters.body_layout()


@pytest.mark.parametrize("layout", ["almond_2", "gibson_4", "rear_3", "tele"])
@pytest.mark.parametrize("widen", [10.0, -4.0])
def test_the_control_cavity_widens_across_its_long_axis(
    layout: str, widen: float
) -> None:
    def build_widened(amount: float):  # type: ignore[no-untyped-def]
        shape = replace(
            YourDesignShape(),
            control_stretch_across=amount,
            control_angle_degrees=20.0,
        )
        parameters = replace(
            Prototype001Parameters(), body_shape=shape, body_controls=layout
        )
        return parameters.body_layout().controls

    plain, widened = build_widened(0.0), build_widened(widen)
    axis = (plain.control_axis.x, plain.control_axis.y)
    across = (-axis[1], axis[0])
    assert widened.control_centre == plain.control_centre

    def shapes(controls):  # type: ignore[no-untyped-def]
        if controls.control_cavity is not None:
            rear = controls.control_cavity
            return rear.cavity, rear.cover_recess
        return controls.top_cavities[1], controls.top_cavities[0]

    for old, new in zip(shapes(plain), shapes(widened), strict=True):
        assert _axis_length(new.outline, across) == pytest.approx(
            _axis_length(old.outline, across) + widen, abs=0.05
        )
        assert _axis_length(new.outline, axis) == pytest.approx(
            _axis_length(old.outline, axis), abs=0.05
        )


def test_a_widened_gibson_layout_moves_its_pot_rows_apart() -> None:
    def pots(amount: float):  # type: ignore[no-untyped-def]
        shape = replace(YourDesignShape(), control_stretch_across=amount)
        body = (
            replace(
                Prototype001Parameters(), body_shape=shape, body_controls="gibson_4"
            )
            .build()
            .body
        )
        return sorted(
            h.center_y for h in body.holes if h.name.startswith("Control pot")
        )

    before, after = pots(0.0), pots(12.0)
    assert after[0] == pytest.approx(before[0] - 6.0)
    assert after[-1] == pytest.approx(before[-1] + 6.0)


@pytest.mark.parametrize("layout", ["almond_2", "gibson_4", "rear_3", "tele"])
def test_a_control_cavity_cannot_be_narrower_than_a_pot(layout: str) -> None:
    shape = replace(YourDesignShape(), control_stretch_across=-60.0)
    parameters = replace(
        Prototype001Parameters(), body_shape=shape, body_controls=layout
    )

    with pytest.raises(BodyGeometryError, match="at least 16 mm"):
        parameters.body_layout()


@pytest.mark.parametrize("layout", [layout for layout in LAYOUTS if layout != "none"])
def test_a_body_no_thicker_than_the_cavity_wall_names_its_thickness(
    layout: str,
) -> None:
    # Regression: the control cavity, the body's thickness less this wall
    # deep, was left no depth and named instead.
    parameters = replace(
        Prototype001Parameters(), body_controls=layout, body_rear_cavity_top_wall=44.0
    )

    with pytest.raises(
        BodyGeometryError,
        match=r"^Body thickness \(44 mm\) must exceed the 44 mm wall the control "
        r"cavity leaves \(body_rear_cavity_top_wall\)\.$",
    ):
        parameters.build()


def test_no_controls_need_no_room_under_the_cavity_wall() -> None:
    parameters = replace(
        Prototype001Parameters(), body_controls="none", body_rear_cavity_top_wall=44.0
    )

    assert parameters.body_layout().control_cavity is None

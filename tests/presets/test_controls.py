"""Tests for the electronics layouts: cavities, screw spots and cover plates."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam import MachiningParameters, plan_cover_machining
from cncguitarwizard.geometry.body import (
    FloydRoseSpec,
    cover_screw_points,
    outlines_overlap,
)
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.controls import CONTROL_LABELS

LAYOUTS = tuple(CONTROL_LABELS)


def build(layout: str, **overrides: object):  # type: ignore[no-untyped-def]
    return replace(Prototype001Parameters(), body_controls=layout, **overrides).build()


def test_every_layout_has_a_label() -> None:
    assert set(LAYOUTS) == {"almond_2", "gibson_4", "rear_3", "tele", "none"}


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

"""Tests for edge finishes and contours."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.body import ContourCut, EdgeProfile
from cncguitarwizard.geometry.body.body_solid import (
    EDGE_RIM_TOLERANCE,
    max_radius_for,
    rim_drop,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters, YourDesignShape

# The drawn body's default starting outline (a Stratocaster-style shape).
STRAT = YourDesignShape()


def square(size: float = 200.0) -> tuple[Point2D, ...]:
    """A counter-clockwise square, densely sampled."""
    points = []
    for index in range(40):
        points.append(Point2D(-size / 2 + size * index / 40, -size / 2))
    for index in range(40):
        points.append(Point2D(size / 2, -size / 2 + size * index / 40))
    for index in range(40):
        points.append(Point2D(size / 2 - size * index / 40, size / 2))
    for index in range(40):
        points.append(Point2D(-size / 2, size / 2 - size * index / 40))
    return tuple(points)


def test_an_edge_takes_a_roundover_or_a_binding_not_both() -> None:
    assert EdgeProfile().reach == 0.0
    assert EdgeProfile(radius=6.0).reach == 6.0
    assert EdgeProfile(binding_width=1.5, binding_depth=6.0).has_binding
    with pytest.raises(BodyGeometryError, match="not both"):
        EdgeProfile(radius=3.0, binding_width=1.5, binding_depth=6.0)
    with pytest.raises(BodyGeometryError, match="needs a depth"):
        EdgeProfile(binding_width=1.5)
    with pytest.raises(BodyGeometryError, match="zero or more"):
        EdgeProfile(radius=-1.0)


def test_a_contour_is_deepest_at_its_centre_and_fades_toward_its_ends() -> None:
    outline = square()
    # Sample 20 sits at (0, -100), the middle of the bottom edge.
    contour = ContourCut.along_edge(
        "Arm contour", "top", outline, 20, 120.0, 40.0, 10.0
    )

    assert contour.depth_at(Point2D(0.0, -100.0)) == pytest.approx(10.0)
    assert contour.depth_at(Point2D(0.0, -80.0)) == pytest.approx(5.0)
    assert contour.depth_at(Point2D(0.0, -55.0)) == 0.0
    # Toward the ends both the depth and the reach shrink.
    assert contour.depth_at(Point2D(30.0, -100.0)) == pytest.approx(5.0)
    assert contour.depth_at(Point2D(70.0, -100.0)) == 0.0
    # Past the edge the ramp runs on, capped at half as deep again.
    assert contour.depth_at(Point2D(0.0, -110.0)) == pytest.approx(12.5)
    assert contour.depth_at(Point2D(0.0, -140.0)) == pytest.approx(15.0)
    arc, inward = contour.locate(Point2D(10.0, -90.0))
    assert arc == pytest.approx(10.0) and inward == pytest.approx(10.0)
    region = contour.region()
    assert min(p.y for p in region) == pytest.approx(-100.0)
    assert max(p.y for p in region) == pytest.approx(-60.0)


def test_a_contour_longer_than_the_edge_is_refused() -> None:
    with pytest.raises(BodyGeometryError, match="longer"):
        ContourCut.along_edge("Arm contour", "top", square(), 20, 900.0, 40.0, 10.0)


def test_the_preset_places_both_contours_on_the_bass_side() -> None:
    body = (
        replace(
            Prototype001Parameters(),
            body_shape=STRAT,
            body_arm_contour_depth=12.0,
            body_belly_cut_depth=10.0,
        )
        .build()
        .body
    )

    arm, belly = body.contours
    assert (arm.name, arm.face, belly.name, belly.face) == (
        "Arm contour",
        "top",
        "Belly cut",
        "back",
    )
    # The left-handed default has its bass side at -Y.
    assert all(point.y < 0.0 for point in (*arm.edge, *belly.edge))
    heel_end = body.neck_pocket.max_x
    assert arm.edge[len(arm.edge) // 2].x - heel_end > 120.0
    assert belly.edge[len(belly.edge) // 2].x < arm.edge[len(arm.edge) // 2].x
    assert arm.max_depth(body.outline.points) == 12.0


def test_a_contour_position_moves_its_deepest_point() -> None:
    body = (
        replace(
            Prototype001Parameters(),
            body_shape=STRAT,
            body_arm_contour_depth=12.0,
            body_arm_contour_position=200.0,
        )
        .build()
        .body
    )
    (arm,) = body.contours
    heel_end = body.neck_pocket.max_x

    assert arm.edge[len(arm.edge) // 2].x - heel_end == pytest.approx(200.0, abs=3.0)


def test_edge_finishes_are_checked_against_the_cavities() -> None:
    base = replace(Prototype001Parameters(), body_shape=STRAT)
    with pytest.raises(BodyGeometryError, match="edge finish reaches too deep"):
        replace(base, body_top_edge_radius=21.0).build()
    with pytest.raises(BodyGeometryError, match="keep it under"):
        replace(base, body_arm_contour_depth=25.0).build()
    # A wide arm contour over the bridge pickup would cut into its route.
    with pytest.raises(BodyGeometryError, match="Arm contour cuts into Bridge"):
        replace(
            base,
            body_arm_contour_depth=12.0,
            body_arm_contour_width=100.0,
            body_arm_contour_position=160.0,
        ).build()
    # A drawn body whose edge comes within 6 mm of the neck pickup route.
    points = list(STRAT.control_points)
    points[points.index((40.0, 150.0))] = (30.0, 45.0)
    pinched = replace(STRAT, control_points=tuple(points))
    with pytest.raises(BodyGeometryError, match="would lower its rim by"):
        replace(base, body_shape=pinched, body_top_edge_radius=12.0).build()


def test_a_roundover_may_lower_a_nearby_rim_a_little() -> None:
    assert rim_drop(12.0, 8.3) == pytest.approx(0.58, abs=0.01)
    assert rim_drop(12.0, 12.0) == 0.0
    assert rim_drop(0.0, 1.0) == 0.0
    radius = max_radius_for(8.3)
    assert rim_drop(radius, 8.3) == pytest.approx(EDGE_RIM_TOLERANCE)
    # The Design by Jone neck pickup sits 8.3 mm from the edge: a 12 mm
    # roundover lowers its rim by 0.6 mm, under the pickup ring.
    replace(Prototype001Parameters(), body_top_edge_radius=12.0).build()


def test_a_contour_and_roundover_together_stay_within_half_the_body() -> None:
    base = replace(Prototype001Parameters(), body_top_edge_radius=12.0)
    with pytest.raises(BodyGeometryError, match="reach 32 mm"):
        replace(base, body_arm_contour_depth=20.0).build()
    replace(base, body_arm_contour_depth=10.0).build()


def test_every_finish_is_off_by_default() -> None:
    body = Prototype001Parameters().build().body

    assert body.top_edge == EdgeProfile() and body.back_edge == EdgeProfile()
    assert body.contours == ()


def test_a_contour_drawn_as_a_line_reaches_in_to_it() -> None:
    outline = square()
    # A line from (-60, -100) on the edge up to 30 mm in and back out to
    # (60, -100): a flat-topped arch.
    line = (
        Point2D(-60.0, -100.0),
        Point2D(-30.0, -70.0),
        Point2D(30.0, -70.0),
        Point2D(60.0, -100.0),
    )
    contour = ContourCut.along_line("Arm contour", "top", outline, line, 10.0)

    # It runs along the edge between the line's ends...
    assert contour.length == pytest.approx(120.0, abs=6.0)
    # ...reaching in to the line: deepest (full depth) where that is widest.
    assert contour.width == pytest.approx(30.0, abs=0.5)
    assert contour.depth_at(Point2D(0.0, -100.0)) == pytest.approx(10.0, abs=0.2)
    assert contour.depth_at(Point2D(0.0, -85.0)) == pytest.approx(5.0, abs=0.2)
    assert contour.depth_at(Point2D(0.0, -69.0)) == 0.0
    # Halfway up the slope the line is 15 mm in: half as deep at the edge.
    assert contour.depth_at(Point2D(-45.0, -100.0)) == pytest.approx(5.0, abs=0.5)
    assert contour.depth_at(Point2D(-45.0, -84.0)) == 0.0


def test_a_line_outside_the_body_is_refused() -> None:
    line = (Point2D(-60.0, -100.0), Point2D(0.0, -130.0), Point2D(60.0, -100.0))
    with pytest.raises(BodyGeometryError, match="inside the body"):
        ContourCut.along_line("Arm contour", "top", square(), line, 10.0)


def test_the_preset_takes_a_drawn_arm_contour_line() -> None:
    from cncguitarwizard.webapp import body_editor_layout

    automatic = replace(Prototype001Parameters(), body_arm_contour_depth=12.0)
    (auto,) = automatic.body_layout().contours
    editor = body_editor_layout({"prototype": {"body_arm_contour_depth": 12.0}})
    assert editor["arm_contour"]["automatic"]
    # Drawn through the automatic line's handles, the middle ones a little
    # further in (the ends stay on the edge).
    line = editor["arm_contour"]["points"]
    points = tuple(
        (x, y if index in (0, len(line) - 1) else y * 0.9)
        for index, (x, y) in enumerate(line)
    )
    shape = replace(automatic.body_shape, arm_contour_points=points)
    drawn = replace(automatic, body_shape=shape)
    (cut,) = drawn.body_layout().contours

    assert cut.reaches and not auto.reaches
    assert cut.length == pytest.approx(auto.length, rel=0.05)
    assert 0.0 < cut.width < auto.width + 15.0
    assert drawn.build().body.contours == (cut,)
    editor = body_editor_layout(
        {"prototype": {"body_arm_contour_depth": 12.0, "body_shape": shape}}
    )
    assert not editor["arm_contour"]["automatic"]
    # Without the arm contour on there is no line to draw.
    assert body_editor_layout({"prototype": {}})["arm_contour"] is None


def test_the_preset_takes_a_drawn_belly_cut_line() -> None:
    from cncguitarwizard.webapp import body_editor_layout

    automatic = replace(Prototype001Parameters(), body_belly_cut_depth=10.0)
    (auto,) = automatic.body_layout().contours
    editor = body_editor_layout({"prototype": {"body_belly_cut_depth": 10.0}})
    assert editor["belly_cut"]["automatic"]
    assert editor["arm_contour"] is None
    line = editor["belly_cut"]["points"]
    points = tuple(
        (x, y if index in (0, len(line) - 1) else y * 0.9)
        for index, (x, y) in enumerate(line)
    )
    shape = replace(automatic.body_shape, belly_cut_points=points)
    drawn = replace(automatic, body_shape=shape)
    (cut,) = drawn.body_layout().contours

    assert cut.name == "Belly cut" and cut.face == "back"
    assert cut.reaches and not auto.reaches
    assert cut.length == pytest.approx(auto.length, rel=0.05)
    assert drawn.build().body.contours == (cut,)
    editor = body_editor_layout(
        {"prototype": {"body_belly_cut_depth": 10.0, "body_shape": shape}}
    )
    assert not editor["belly_cut"]["automatic"]
    # A drawn line is ignored while the belly cut is off.
    off = replace(drawn, body_belly_cut_depth=0.0)
    assert off.body_layout().contours == ()

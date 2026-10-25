"""Tests for edge finishes and contours."""

from collections.abc import Callable
from dataclasses import replace

import pytest

from cncguitarwizard.geometry.body import ContourCut, EdgeProfile
from cncguitarwizard.geometry.body.body_solid import (
    EDGE_RIM_TOLERANCE,
    max_radius_for,
    rim_drop,
)
from cncguitarwizard.geometry.body.edges import (
    AROUND_FADE,
    AROUND_ROUND_FADE,
    AROUND_TAPER,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
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
    # The right-handed default has its bass side at -Y.
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


def strat_style(**changes: object) -> Prototype001Parameters:
    """Return the Stratocaster style's guitar (its controls in the guard)."""
    from cncguitarwizard.presets.styles import STYLES

    return replace(
        Prototype001Parameters.for_instrument("electric_guitar"),
        **{**STYLES["stratocaster"].prototype_values("electric_guitar"), **changes},
    )


def test_a_leg_contour_bevels_the_back_of_the_treble_side_waist() -> None:
    # Where the body sits on the thigh when played seated: the back of the
    # treble side's waist, deepest at its innermost point.
    parameters = strat_style(body_leg_contour_depth=8.0)
    body = parameters.build().body
    leg = next(c for c in body.contours if c.name == "Leg contour")
    assert leg.face == "back"
    # The right-handed default has its treble side at +Y.
    assert all(point.y > 0.0 for point in leg.edge)
    heel_end = parameters.body_layout().heel_end
    apex = leg.edge[len(leg.edge) // 2]
    assert 40.0 <= apex.x - heel_end <= 260.0
    # Its innermost point there: further in than the edge either side.
    assert apex.y < leg.edge[0].y and apex.y < leg.edge[-1].y
    assert leg.max_depth(body.outline.points) == 8.0
    # Off unless asked for.
    off = replace(parameters, body_leg_contour_depth=0.0).build().body
    assert "Leg contour" not in [c.name for c in off.contours]
    # Cut from the back with the belly cut.
    from cncguitarwizard.cam import MachiningParameters, plan_body_machining

    plan = plan_body_machining(body, MachiningParameters())
    assert plan.back_edges is not None
    # (And the style's roundover after the contours.)
    assert [path.name for path in plan.back_edges.toolpaths][-3:] == [
        "Leg contour roughing",
        "Leg contour finishing",
        "Back edge roundover",
    ]


def test_a_belly_cut_keeps_off_a_stratocasters_horn() -> None:
    # Regression: the bass side only narrows from the horn's root to the
    # waist, so the belly cut, centred there, ran out along the horn to
    # its tip. It now starts at the horn's root and runs back past the
    # waist, deepest about there. (The automatic one: the template draws
    # the original's.)
    parameters = strat_style()
    parameters = replace(
        parameters, body_shape=replace(parameters.body_shape, belly_cut_points=())
    )
    layout = parameters.body_layout()
    (cut,) = [c for c in layout.contours if c.name == "Belly cut"]
    along = [point.x - layout.heel_end for point in cut.edge]
    horn_tip = min(point.x for point in layout.outline.points) - layout.heel_end
    assert horn_tip < -130.0
    assert min(along) > -55.0
    assert 20.0 < along[len(along) // 2] < 80.0
    assert all(point.y * parameters.bass_sign > 0.0 for point in cut.edge)


def test_the_preset_takes_a_drawn_leg_contour_line() -> None:
    from cncguitarwizard.presets.styles import STYLES
    from cncguitarwizard.webapp import body_editor_layout

    values = STYLES["stratocaster"].prototype_values("electric_guitar")
    automatic = strat_style(body_leg_contour_depth=8.0)
    editor = body_editor_layout(
        {"prototype": {**values, "body_leg_contour_depth": 8.0}}
    )
    assert editor["leg_contour"]["automatic"]
    line = editor["leg_contour"]["points"]
    points = tuple(
        (x, y if index in (0, len(line) - 1) else y * 0.95)
        for index, (x, y) in enumerate(line)
    )
    shape = replace(automatic.body_shape, leg_contour_points=points)
    drawn = replace(automatic, body_shape=shape)
    cut = next(c for c in drawn.body_layout().contours if c.name == "Leg contour")
    assert cut.face == "back" and cut.reaches


def square_outline(size: float = 200.0) -> tuple[Point2D, ...]:
    """A counter-clockwise square, densely sampled."""
    half = size / 2.0
    corners = ((-half, -half), (half, -half), (half, half), (-half, half))
    points = []
    for (ax, ay), (bx, by) in zip(corners, (*corners[1:], corners[0]), strict=True):
        for k in range(40):
            points.append(Point2D(ax + (bx - ax) * k / 40, ay + (by - ay) * k / 40))
    return tuple(points)


def test_a_bevel_all_round_keeps_its_angle_and_leaves_a_stretch_square() -> None:
    outline = square_outline()
    # Left square along the left side, where a neck would join.
    skip = [point.x <= -99.0 and abs(point.y) < 30.0 for point in outline]
    bevel = ContourCut.around("Top bevel", "top", outline, skip, 15.0, 7.0)

    assert bevel.depth_at(Point2D(99.5, 0.0)) == pytest.approx(
        7.0 * 14.5 / 15.0, abs=0.2
    )
    assert bevel.depth_at(Point2D(0.0, 99.5)) == pytest.approx(
        7.0 * 14.5 / 15.0, abs=0.2
    )
    assert bevel.depth_at(Point2D(0.0, 80.0)) == 0.0
    # Square where the neck joins.
    assert bevel.depth_at(Point2D(-99.5, 0.0)) == 0.0
    # Everywhere its depth goes with its reach: the same angle.
    for s in bevel.arc[10:-10:10]:
        if bevel.reach(s) > 1.0:
            assert bevel.depth_from(s, 0.0) / bevel.reach(s) == pytest.approx(
                7.0 / 15.0
            )


def test_a_bevel_all_round_keeps_clear_of_a_route_by_its_edge() -> None:
    outline = square_outline()
    skip = [point.x <= -99.0 and abs(point.y) < 30.0 for point in outline]
    route = (
        Point2D(88.0, -10.0),
        Point2D(95.0, -10.0),
        Point2D(95.0, 10.0),
        Point2D(88.0, 10.0),
    )
    bevel = ContourCut.around(
        "Back bevel", "back", outline, skip, 15.0, 7.0, keep_clear=[route]
    )

    assert all(bevel.depth_at(p) == 0.0 for p in route)
    # Narrower and shallower beside it, full width away from it.
    assert bevel.depth_at(Point2D(99.5, 0.0)) < 2.0
    assert bevel.depth_at(Point2D(99.5, 60.0)) > 6.0


def assert_no_notch(bevel: ContourCut) -> None:
    """Away from where it fades out (its ends and the stretches it leaves
    square) a bevel's reach changes no faster than the taper."""
    spacing = bevel.length / (len(bevel.arc) - 1)
    square = [
        bevel.arc[0],
        bevel.arc[-1],
        *(s for reach, s in zip(bevel.reaches, bevel.arc, strict=True) if reach == 0),
    ]
    away = [
        index
        for index, s in enumerate(bevel.arc)
        if min(abs(s - a) for a in square)
        > max(AROUND_FADE, AROUND_ROUND_FADE) + spacing
    ]
    steps = [
        abs(bevel.reaches[b] - bevel.reaches[a])
        for a, b in zip(away, away[1:])
        if b == a + 1
    ]
    assert steps and max(steps) <= AROUND_TAPER * spacing + 1e-9


def test_a_bevel_all_round_eases_into_a_waist_beside_a_route() -> None:
    # Capped only beside what it kept clear of, it left a notch.
    outline = square_outline()
    skip = [point.x <= -99.0 and abs(point.y) < 30.0 for point in outline]
    route = (
        Point2D(88.0, -10.0),
        Point2D(95.0, -10.0),
        Point2D(95.0, 10.0),
        Point2D(88.0, 10.0),
    )
    bevel = ContourCut.around(
        "Back bevel", "back", outline, skip, 15.0, 7.0, keep_clear=[route]
    )

    assert_no_notch(bevel)
    # 3 mm beside the route, widening at the taper past its end.
    s, _ = bevel.locate(Point2D(100.0, 30.0))
    assert bevel.reach(s) == pytest.approx(3.0 + AROUND_TAPER * 20.0, abs=1.0)


def test_a_point_on_a_bevel_all_round_is_moved_in_off_it() -> None:
    outline = square_outline()
    skip = [point.x <= -99.0 and abs(point.y) < 30.0 for point in outline]
    bevel = ContourCut.around("Top bevel", "top", outline, skip, 15.0, 7.0)

    moved = bevel.clear_of(Point2D(95.0, 0.0), 2.0)
    assert (moved.x, moved.y) == pytest.approx((83.0, 0.0), abs=0.01)
    inside = Point2D(50.0, 0.0)
    assert bevel.clear_of(inside, 2.0) is inside


def sg_style(**changes: object) -> Prototype001Parameters:
    from cncguitarwizard.presets.styles import STYLES

    return replace(
        Prototype001Parameters.for_instrument("electric_guitar"),
        **{**STYLES["sg"].prototype_values("electric_guitar"), **changes},
    )


@pytest.mark.parametrize("guard", ["sg_small", "sg_batwing"])
def test_an_sgs_bevels_run_round_it_past_its_guard_without_a_notch(guard: str) -> None:
    # The guard stopped the top bevel along the treble cutaway, and the
    # routes and covers it kept clear of notched both bevels.
    parameters = sg_style(body_pickguard_style=guard)
    layout = parameters.body_layout()
    bevels = [c for c in layout.contours if c.name.endswith("bevel")]
    assert len(bevels) == 2
    for bevel in bevels:
        assert_no_notch(bevel)
    (top,) = [c for c in bevels if c.face == "top"]
    treble = -parameters.bass_sign
    cutaway = [
        reach
        for point, reach in zip(top.edge, top.reaches, strict=True)
        if abs(point.x - layout.heel_end) <= 10.0 and point.y * treble > 50.0
    ]
    # (Narrower by the neck pickup's ring, but never stopped.)
    assert cutaway and min(cutaway) > 3.0
    guard_plate = layout.pickguard
    assert guard_plate is not None
    assert not any(top.cuts(p) for p in guard_plate.control_points)


@pytest.mark.parametrize(
    ("style", "joint", "runs_round"),
    [
        ("sg", "set", True),
        ("sg", "bolt_on", False),
        # The body beside a neck run through is the neck's own blank.
        ("mockingbird", "neck_through", False),
    ],
)
def test_a_back_bevel_runs_round_a_set_necks_heel(
    style: str, joint: str, runs_round: bool
) -> None:
    from cncguitarwizard.presets.styles import STYLES

    parameters = replace(
        Prototype001Parameters.for_instrument("electric_guitar"),
        **{
            **STYLES[style].prototype_values("electric_guitar"),
            "neck_joint": joint,
        },
    )
    # The back bevelled all round (none of the template's round points).
    parameters = replace(
        parameters, body_shape=replace(parameters.body_shape, back_round_points=())
    )
    layout = parameters.body_layout()
    (back,) = [c for c in layout.contours if c.name == "Back bevel"]
    outline = layout.outline.points
    front = min(p.x for p in outline if abs(p.y) < 20.0)
    # Beside the heel (the neck 56 mm wide), halfway from the body's
    # front to the cutaways.
    beside = [
        p for p in outline if front + 10.0 < p.x < front + 25.0 and abs(p.y) < 31.0
    ]
    assert beside
    assert all(back.cuts(p) == runs_round for p in beside)
    # Never where the neck leaves the body.
    assert not any(back.cuts(Point2D(front + 1.0, y)) for y in (-10.0, 0.0, 10.0))


@pytest.mark.parametrize("handedness", ["right", "left"])
def test_an_sgs_bevels_leave_its_tail_and_control_cavity_to_the_roundover(
    handedness: str,
) -> None:
    # Both faces bevelled round the horns and the upper bouts; the top on
    # along both lower bouts, the back only along the bass side's, the
    # treble side's (its control cavity's) rounded over as is the tail.
    parameters = sg_style(handedness=handedness)
    layout = parameters.body_layout()
    (back,) = [c for c in layout.contours if c.name == "Back bevel"]
    (top,) = [c for c in layout.contours if c.name == "Top bevel"]
    outline = layout.outline.points
    bass, heel_end = parameters.bass_sign, layout.heel_end

    def edge(where: Callable[[Point2D], bool]) -> list[Point2D]:
        return [p for p in outline if where(p)]

    def lower(side: float) -> list[Point2D]:
        return edge(
            lambda p: p.y * side > 0.0 and heel_end + 200.0 < p.x < heel_end + 240.0
        )

    bass_horn = edge(lambda p: p.y * bass > 100.0 and p.x < heel_end + 20.0)
    treble_horn = edge(lambda p: p.y * bass < -60.0 and p.x < heel_end + 20.0)
    tail = edge(lambda p: p.x > heel_end + 280.0)
    bass_lower, treble_lower = lower(bass), lower(-bass)
    assert bass_horn and treble_horn and tail and bass_lower and treble_lower
    for bevel in (top, back):
        assert any(bevel.cuts(p) for p in bass_horn)
        assert any(bevel.cuts(p) for p in treble_horn)
        assert not any(bevel.cuts(p) for p in tail)
    assert all(top.cuts(p) for p in (*bass_lower, *treble_lower))
    assert all(back.cuts(p) for p in bass_lower)
    assert not any(back.cuts(p) for p in treble_lower)
    # Its set neck's heel bevelled across the body's front edge too.
    front = min(p.x for p in outline if abs(p.y) < 10.0)
    assert all(back.cuts(Point2D(front + 1.0, y)) for y in (-10.0, 0.0, 10.0))
    assert parameters.body_top_edge_radius > 0.0 < parameters.body_back_edge_radius


def test_round_points_come_in_pairs() -> None:
    shape = replace(sg_style().body_shape, top_round_points=((270.0, -160.0),))
    with pytest.raises(BodyGeometryError, match="in pairs"):
        sg_style(body_shape=shape).body_layout()


@pytest.mark.parametrize("handedness", ["right", "left"])
def test_a_mockingbirds_sides_are_bevelled_its_neck_end_and_tail_rounded_over(
    handedness: str,
) -> None:
    # Between each pair of its round points (its tail, and its neck end
    # round the horns and the cutaways) the edge is left to the roundover,
    # top and back; along its two sides between them it is bevelled.
    from cncguitarwizard.presets.styles import STYLES

    parameters = replace(
        Prototype001Parameters.for_instrument("electric_guitar"),
        **STYLES["mockingbird"].prototype_values("electric_guitar"),
        handedness=handedness,
    )
    layout = parameters.body_layout()
    outline = layout.outline.points
    bass, heel_end = parameters.bass_sign, layout.heel_end

    def edge(where: Callable[[Point2D], bool]) -> list[Point2D]:
        return [p for p in outline if where(p)]

    bass_side = edge(lambda p: p.y * bass > 0.0 and 80.0 < p.x - heel_end < 270.0)
    treble_side = edge(
        lambda p: (
            p.y * bass < 0.0 and -60.0 < p.x - heel_end < 170.0 and abs(p.y) > 100.0
        )
    )
    tail = edge(lambda p: p.x - heel_end > 320.0)
    cutaways = edge(lambda p: p.x - heel_end < 0.0 and abs(p.y) < 60.0)
    assert bass_side and treble_side and tail and cutaways
    assert parameters.body_top_edge_radius > 0.0 < parameters.body_back_edge_radius
    for name in ("Top bevel", "Back bevel"):
        (bevel,) = [c for c in layout.contours if c.name == name]
        assert any(bevel.cuts(p) for p in bass_side)
        assert any(bevel.cuts(p) for p in treble_side)
        assert not any(bevel.cuts(p) for p in (*tail, *cutaways))


def test_a_bevel_is_terraced_in_one_region_for_each_run_of_it() -> None:
    # Left square along a stretch, a level's area is two regions either
    # side of it: one reaching across the gap cut a groove through it (as
    # round a horn's tip, where the bevel thins to nothing).
    outline = square_outline()
    neck = [point.x <= -99.0 and abs(point.y) < 30.0 for point in outline]
    rounded = [point.x >= 99.0 and abs(point.y) < 30.0 for point in outline]
    bevel = ContourCut.around(
        "Top bevel", "top", outline, neck, 15.0, 7.0, rounded=rounded
    )
    regions = bevel.level_regions(3.0)
    assert len(regions) == 2
    for region in regions:
        assert not point_in_polygon(Point2D(99.5, 0.0), region)
        assert not point_in_polygon(Point2D(0.0, 0.0), region)


def test_a_bevel_all_round_runs_out_long_into_a_rounded_stretch() -> None:
    # Into a stretch left to the roundover it fades out over
    # AROUND_ROUND_FADE, not ending at a wall; into the neck over AROUND_FADE.
    outline = square_outline()
    neck = [point.x <= -99.0 and abs(point.y) < 30.0 for point in outline]
    rounded = [point.x >= 99.0 and abs(point.y) < 30.0 for point in outline]
    bevel = ContourCut.around(
        "Top bevel", "top", outline, neck, 15.0, 7.0, rounded=rounded
    )

    def reach_at(point: Point2D) -> float:
        s, _ = bevel.locate(point)
        return bevel.reach(s)

    assert reach_at(Point2D(99.9, 0.0)) == 0.0
    # Halfway along its run-out, part of the width; full past it.
    assert 3.0 < reach_at(Point2D(99.9, 30.0 + AROUND_ROUND_FADE / 2.0)) < 12.0
    assert reach_at(Point2D(99.9, 30.0 + AROUND_ROUND_FADE + 5.0)) == pytest.approx(
        15.0
    )
    assert reach_at(Point2D(-99.9, 30.0 + AROUND_FADE + 5.0)) == pytest.approx(15.0)


def test_the_body_editor_gets_the_round_points() -> None:
    from cncguitarwizard.presets.styles import STYLES
    from cncguitarwizard.webapp import _jsonable, body_editor_layout

    values = STYLES["sg"].prototype_values("electric_guitar")
    view = body_editor_layout({"prototype": _jsonable(values)})
    shape = values["body_shape"]
    assert view["round_points"] == {
        "top": [list(p) for p in shape.top_round_points],
        "back": [list(p) for p in shape.back_round_points],
    }


def test_a_bevel_all_round_leaves_every_stretch_marked_square() -> None:
    # Two stretches left square: the bevel fades out into both.
    outline = square_outline()
    skip = [
        (point.x <= -99.0 and abs(point.y) < 30.0)
        or (point.x >= 99.0 and abs(point.y) < 30.0)
        for point in outline
    ]
    bevel = ContourCut.around("Top bevel", "top", outline, skip, 15.0, 7.0)
    assert bevel.depth_at(Point2D(-99.5, 0.0)) == 0.0
    assert bevel.depth_at(Point2D(99.5, 0.0)) == 0.0
    assert bevel.depth_at(Point2D(0.0, 99.5)) > 6.0
    assert bevel.depth_at(Point2D(0.0, -99.5)) > 6.0


def test_the_sg_and_mockingbird_styles_bevel_their_edges_all_round() -> None:
    from cncguitarwizard.cam import MachiningParameters, plan_body_machining
    from cncguitarwizard.presets.styles import STYLES

    for key, width in (("sg", 18.0), ("mockingbird", 12.0)):
        parameters = replace(
            Prototype001Parameters.for_instrument("electric_guitar"),
            **STYLES[key].prototype_values("electric_guitar"),
        )
        body = parameters.build().body
        top = next(c for c in body.contours if c.name == "Top bevel")
        back = next(c for c in body.contours if c.name == "Back bevel")
        assert top.face == "top" and back.face == "back"
        assert max(top.reaches) == pytest.approx(width)
        # Left square at the neck: nothing of it in the neck's pocket (the
        # SG's; the Mockingbird's neck runs through).
        if body.neck_pocket is not None:
            assert not any(top.cuts(p) for p in body.neck_pocket.outline)
        plan = plan_body_machining(body, MachiningParameters())
        assert plan.top_edges is not None and plan.back_edges is not None
        assert "Top bevel finishing" in [p.name for p in plan.top_edges.toolpaths]
        assert "Back bevel finishing" in [p.name for p in plan.back_edges.toolpaths]


def test_a_bevel_angle_out_of_range_is_refused() -> None:
    with pytest.raises(BodyGeometryError, match="body_bevel_angle"):
        replace(
            Prototype001Parameters(), body_top_bevel_width=10.0, body_bevel_angle=80.0
        ).body_layout()
    with pytest.raises(BodyGeometryError, match="must not be negative"):
        replace(Prototype001Parameters(), body_back_bevel_width=-1.0).body_layout()

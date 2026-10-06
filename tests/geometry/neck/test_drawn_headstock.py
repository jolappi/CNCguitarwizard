"""Tests for headstocks with drawn edges."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.geometry.exceptions import (
    HeadstockGeometryError,
    NeckGeometryError,
)
from cncguitarwizard.geometry.neck import HeadstockPlan
from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.prototype001 import distance_to_headstock_edge

BASS = ((45.0, 30.8), (80.0, 34.0), (120.0, 27.0), (170.0, 30.0))
TREBLE = ((45.0, 30.8), (95.0, 29.0), (140.0, 24.0), (170.0, 18.0))


def drawn(**overrides: object) -> Prototype001Parameters:
    values: dict[str, object] = {
        "headstock_outline": "drawn",
        "headstock_bass_edge": BASS,
        "headstock_treble_edge": TREBLE,
    }
    values.update(overrides)
    return replace(Prototype001Parameters(), **values)  # type: ignore[arg-type]


def test_a_drawn_plan_follows_its_edges_from_the_nut() -> None:
    plan = HeadstockPlan(
        170.0, 42.0, 45.0, 65.0, 40.0, bass_edge=BASS, treble_edge=TREBLE
    )

    assert plan.is_drawn
    assert plan.half_width_at(0.0, "bass") == 21.0
    assert plan.half_width_at(80.0, "bass") == pytest.approx(34.0)
    assert plan.half_width_at(170.0, "treble") == pytest.approx(18.0)
    assert plan.tip_line.start.y == pytest.approx(30.0)
    xs = [point.x for point in plan.boundary]
    assert min(xs) == pytest.approx(-170.0)


@pytest.mark.parametrize(
    ("bass", "treble", "match"),
    [
        (BASS, None, "both"),
        (((45.0, 30.0), (160.0, 25.0)), TREBLE, "end at the tip"),
        (((90.0, 30.0), (45.0, 25.0), (170.0, 20.0)), TREBLE, "doubling back"),
        (((45.0, 30.0), (170.0, -20.0)), ((45.0, 30.0), (170.0, 10.0)), "cross"),
    ],
)
def test_a_drawn_plan_rejects_bad_edges(bass, treble, match) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(HeadstockGeometryError, match=match):
        HeadstockPlan(170.0, 42.0, 45.0, 65.0, 40.0, bass_edge=bass, treble_edge=treble)


def test_the_preset_builds_a_drawn_headstock_with_its_length() -> None:
    geometry = drawn().build()
    plan = geometry.headstock.plan

    assert plan.is_drawn and plan.length == 170.0
    for hole in geometry.tuner_layout.holes:
        assert distance_to_headstock_edge(plan, hole.center) >= 14.5
    # Measured across the neck at the hole and to the tip.
    first = geometry.tuner_layout.holes_on("bass")[0]
    assert distance_to_headstock_edge(plan, first.center) == pytest.approx(
        min(
            plan.edge_y(-first.center.x, 1.0) - first.center.y,
            first.center.y - plan.edge_y(-first.center.x, -1.0),
            plan.length + first.center.x,
        )
    )


def test_a_drawn_edge_too_close_to_a_hole_is_rejected() -> None:
    # 13 mm from the hole centres: enough wood (8 mm) but under the 15 mm offset.
    squeezed = ((45.0, 30.8), (85.0, 25.2), (170.0, 22.0))
    with pytest.raises(NeckGeometryError, match="from the drawn headstock edge"):
        drawn(headstock_bass_edge=squeezed).build()


def test_empty_drawn_edges_fall_back_to_the_fitted_outline() -> None:
    plan = (
        replace(Prototype001Parameters(), headstock_outline="drawn")
        .build()
        .headstock.plan
    )

    assert not plan.is_drawn
    assert plan.length == 150.0


def test_the_tuner_centres_match_the_built_holes() -> None:
    parameters = replace(Prototype001Parameters(), headstock_style="6_inline")
    centres = parameters.tuner_centres()
    holes = parameters.build().tuner_layout.holes

    assert sorted((x, y) for _, x, y in centres) == pytest.approx(
        sorted((hole.center.x, hole.center.y) for hole in holes)
    )


@pytest.mark.parametrize(
    ("instrument", "style"),
    [
        ("electric_guitar", "3+3"),
        ("electric_guitar", "6_inline"),
        ("electric_guitar", "6_inline_reverse"),
        ("electric_guitar", "4+2"),
        ("bass_guitar", "4_inline"),
        ("bass_guitar", "2+2"),
    ],
)
def test_the_editor_start_edges_build_for_every_style(
    instrument: str, style: str
) -> None:
    import dataclasses

    from cncguitarwizard.webapp import _jsonable, headstock_editor_layout

    base = replace(
        Prototype001Parameters.for_instrument(instrument),  # type: ignore[arg-type]
        headstock_style=style,
    )
    layout = headstock_editor_layout({"prototype": _jsonable(dataclasses.asdict(base))})
    edges = {
        side: tuple(tuple(point) for point in layout["start_edges"][side])
        for side in ("bass", "treble")
    }
    plan = (
        replace(
            base,
            headstock_outline="drawn",
            headstock_bass_edge=edges["bass"],
            headstock_treble_edge=edges["treble"],
        )
        .build()
        .headstock.plan
    )

    assert plan.is_drawn


def test_the_default_headstock_is_drawn_and_starts_as_the_fitted_outline() -> None:
    default = Prototype001Parameters()
    fitted = replace(default, headstock_outline="fitted")

    assert default.headstock_outline == "drawn"
    assert default.headstock_design() == fitted.headstock_design()


def test_tip_points_shape_a_drawn_headstocks_tip() -> None:
    plan = drawn(headstock_tip_points=((12.0, 0.0),)).build().headstock.plan

    # A point 12 mm past the tip line in the middle: the tip curves out
    # through it from both corners, rounding over it.
    tip = plan.tip_outline()
    assert Point2D(-182.0, 0.0) in tip
    assert plan.reach == pytest.approx(182.0, abs=0.5)
    assert min(p.x for p in plan.boundary) == pytest.approx(-plan.reach)
    assert (tip[0].y, tip[-1].y) == (plan.edge_y(170.0, -1.0), plan.edge_y(170.0, 1.0))
    # Measured straight to the curve: nearer than the 32 mm to its apex.
    assert 20.0 < plan.tip_clearance(Point2D(-150.0, 0.0)) < 32.0


def test_a_round_tip_leaves_its_corners_along_the_edges() -> None:
    plan = drawn(headstock_tip_points=((10.0, -8.0), (14.0, 0.0), (10.0, 8.0))).build()
    tip = plan.headstock.plan.tip_outline()

    # The first span starts off along the edge: no corner at the tip.
    for start, after, y_sign in ((tip[0], tip[1], -1.0), (tip[-1], tip[-2], 1.0)):
        edge = plan.headstock.plan
        slope = (edge.edge_y(170.0, y_sign) - edge.edge_y(169.5, y_sign)) / 0.5
        # The first span heads off along the edge: its first sample (a
        # sixteenth of the way round a tight curve) within 10 degrees of it.
        turn = math.atan2(after.y - start.y, start.x - after.x) - math.atan(slope)
        assert abs(math.degrees(turn)) < 10.0


def test_a_notched_tip_keeps_the_tuners_clear_of_it() -> None:
    plan = drawn(headstock_tip_points=((-8.0, 0.0),)).build().headstock.plan

    assert Point2D(-162.0, 0.0) in plan.tip_outline()
    assert plan.tip_clearance(Point2D(-150.0, 0.0)) == pytest.approx(12.0, abs=0.1)
    # A notch deep enough to come near the last tuners is refused.
    with pytest.raises((NeckGeometryError, HeadstockGeometryError), match="tip|edge"):
        drawn(headstock_tip_points=((-80.0, 0.0),)).build()


@pytest.mark.parametrize(
    "tip",
    [((5.0, 40.0),), ((5.0, 5.0), (5.0, -5.0)), ((-130.0, 0.0),)],
    ids=["outside", "out_of_order", "past_shoulder"],
)
def test_tip_points_must_run_across_the_tip(tip: object) -> None:
    with pytest.raises(HeadstockGeometryError):
        drawn(headstock_tip_points=tip).build()


def test_only_a_drawn_headstock_takes_tip_points() -> None:
    fitted = replace(
        Prototype001Parameters(),
        headstock_outline="fitted",
        headstock_tip_points=((10.0, 0.0),),
    )
    # The fitted outline ignores them, as it ignores drawn edges.
    assert fitted.build().headstock.plan.tip_points == ()


@pytest.mark.parametrize(
    ("change", "message", "drawn_too"),
    [
        ({"headstock_length": 400.0}, "narrows to -3.1 mm at its tip, 400 mm", False),
        ({"headstock_root_length": 0.0}, "headstock_root_length \\(0 mm\\)", True),
        ({"nut_width": 0.0}, "nut_width must be positive", True),
        ({"headstock_tip_width": 0.0}, "headstock_tip_width must be positive", False),
        ({"headstock_shoulder_width": -2.0}, "headstock_shoulder_width must be", False),
    ],
)
def test_a_plan_that_cannot_be_drawn_names_its_setting(
    change: dict[str, float], message: str, drawn_too: bool
) -> None:
    # Not just "Headstock plan dimensions must be finite and positive":
    # the setting to mend.
    with pytest.raises(HeadstockGeometryError, match=message):
        replace(Prototype001Parameters(), **change).headstock_design()  # type: ignore[arg-type]
    if drawn_too:
        with pytest.raises(HeadstockGeometryError, match=message):
            drawn(**change).headstock_design()
    else:
        # A drawing is its edges: the fitted widths it would start over
        # from do not stop it (a tester's long headstock, drawn).
        plan, _ = drawn(**change).headstock_design()
        assert plan.is_drawn and plan.length == 170.0


def test_a_drawn_plan_ignores_the_fitted_widths_it_carries() -> None:
    plan = HeadstockPlan(
        170.0, 42.0, 45.0, 30.0, -11.5, bass_edge=BASS, treble_edge=TREBLE
    )
    assert plan.width_at_distance(170.0) == pytest.approx(48.0)
    with pytest.raises(HeadstockGeometryError, match="finite and positive"):
        HeadstockPlan(170.0, 42.0, 45.0, 65.0, -11.5)

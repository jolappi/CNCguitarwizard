"""Tests for asymmetric headstock plans and one-sided tuner layouts."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.exceptions import (
    HeadstockGeometryError,
    NeckGeometryError,
)
from cncguitarwizard.geometry.neck import HeadstockPlan, TunerLayout
from cncguitarwizard.presets import HEADSTOCK_STYLES, Prototype001Parameters


def test_shifted_plan_moves_its_sides_but_keeps_the_nut_centred() -> None:
    plan = HeadstockPlan(
        150.0, 42.0, 45.0, 65.0, 40.0, shoulder_shift=5.0, tip_shift=10.0
    )

    assert plan.half_width_at(0.0, "bass") == pytest.approx(21.0)
    assert plan.half_width_at(0.0, "treble") == pytest.approx(21.0)
    assert plan.half_width_at(45.0, "bass") == pytest.approx(37.5)
    assert plan.half_width_at(45.0, "treble") == pytest.approx(27.5)
    assert plan.half_width_at(150.0, "bass") == pytest.approx(30.0)
    assert plan.half_width_at(150.0, "treble") == pytest.approx(10.0)
    assert plan.width_at_distance(150.0) == pytest.approx(40.0)
    assert max(point.y for point in plan.boundary) == pytest.approx(37.5)
    assert min(point.y for point in plan.boundary) == pytest.approx(-27.5)
    assert plan.tip_line.start.y == pytest.approx(30.0)
    assert plan.tip_line.end.y == pytest.approx(-10.0)


def test_unshifted_plan_is_unchanged() -> None:
    plan = HeadstockPlan(150.0, 42.0, 45.0, 65.0, 40.0)

    assert plan.half_width_at(100.0, "bass") == plan.half_width_at(100.0, "treble")
    assert plan.width_at_distance(100.0) == pytest.approx(
        2.0 * plan.half_width_at(100.0, "bass")
    )


def test_a_tip_shift_may_carry_an_edge_to_the_centerline() -> None:
    # A banana-style in-line headstock sweeps one edge across the centre.
    plan = HeadstockPlan(150.0, 42.0, 45.0, 65.0, 40.0, tip_shift=25.0)

    assert plan.half_width_at(150.0, "treble") == pytest.approx(-5.0)
    assert plan.edge_y(150.0, -1.0) == pytest.approx(5.0)
    assert plan.edge_y(150.0, 1.0) == pytest.approx(45.0)
    assert plan.width_at_distance(150.0) == pytest.approx(40.0)
    with pytest.raises(HeadstockGeometryError, match="narrower than the nut"):
        HeadstockPlan(150.0, 42.0, 45.0, 65.0, 40.0, shoulder_shift=12.0)


def test_one_sided_layout_puts_every_hole_on_its_named_side() -> None:
    plan = HeadstockPlan(195.0, 42.0, 45.0, 65.0, 40.0, tip_shift=10.0)
    distances = tuple(50.0 + 25.4 * index for index in range(6))
    layout = TunerLayout(
        plan,
        station_distances=distances,
        side_offsets=tuple(plan.half_width_at(d, "bass") - 15.0 for d in distances),
        minimum_edge_clearance=8.0,
        sides=("bass",) * 6,
    )

    assert len(layout.holes_on("bass")) == 6 and layout.holes_on("treble") == ()
    assert [hole.index for hole in layout.holes] == [1, 2, 3, 4, 5, 6]
    assert layout.minimum_side_edge_clearance == pytest.approx(10.0)


def test_one_sided_layout_checks_the_edge_on_its_own_side() -> None:
    plan = HeadstockPlan(195.0, 42.0, 45.0, 65.0, 40.0, tip_shift=10.0)
    # 17 mm off centre is inside the wide bass side but not the narrow treble one.
    TunerLayout(plan, station_distances=(150.0,), side_offsets=(17.0,), sides=("bass",))
    with pytest.raises(HeadstockGeometryError, match="side-edge"):
        TunerLayout(
            plan, station_distances=(150.0,), side_offsets=(17.0,), sides=("treble",)
        )


def test_layout_rejects_mismatched_sides_and_unordered_stations() -> None:
    plan = HeadstockPlan(150.0, 42.0, 45.0, 65.0, 40.0)
    with pytest.raises(HeadstockGeometryError, match="one side each"):
        TunerLayout(
            plan,
            station_distances=(60.0, 95.0),
            side_offsets=(15.0, 12.0),
            sides=("bass",),
        )
    with pytest.raises(HeadstockGeometryError, match="ordered"):
        TunerLayout(
            plan,
            station_distances=(95.0, 60.0),
            side_offsets=(12.0, 15.0),
            sides=("bass", "bass"),
        )
    # The same distances on opposite sides are fine: only each side is ordered.
    TunerLayout(
        plan,
        station_distances=(95.0, 95.0),
        side_offsets=(12.0, 12.0),
        sides=("bass", "treble"),
    )


@pytest.mark.parametrize("style", list(HEADSTOCK_STYLES))
def test_every_headstock_style_builds(style: str) -> None:
    geometry = replace(Prototype001Parameters(), headstock_style=style).build()  # type: ignore[arg-type]
    layout = geometry.tuner_layout
    bass, treble = HEADSTOCK_STYLES[style]

    assert (len(layout.holes_on("bass")), len(layout.holes_on("treble"))) == (
        bass,
        treble,
    )
    assert layout.minimum_side_edge_clearance >= 8.0 - 1e-9
    assert geometry.headstock.plan.length >= 150.0


def test_the_left_handed_default_puts_the_bass_side_at_minus_y() -> None:
    geometry = Prototype001Parameters().build()

    assert geometry.headstock.plan.bass_sign == -1.0
    assert all(hole.center.y < 0 for hole in geometry.tuner_layout.holes_on("bass"))
    righty = replace(Prototype001Parameters(), headstock_bass_side="+y").build()
    assert all(hole.center.y > 0 for hole in righty.tuner_layout.holes_on("bass"))


def edge_distance(plan, hole) -> float:  # type: ignore[no-untyped-def]
    """Return the wood between a hole's centre and the nearer headstock edge."""
    distance = -hole.center.x
    return min(
        plan.edge_y(distance, 1.0) - hole.center.y,
        hole.center.y - plan.edge_y(distance, -1.0),
    )


def test_a_tuner_row_grows_the_headstock_and_runs_across_it() -> None:
    parameters = replace(Prototype001Parameters(), headstock_style="6_inline")
    geometry = parameters.build()
    plan = geometry.headstock.plan
    holes = geometry.tuner_layout.holes_on("bass")

    # Last station 177 mm + 5 mm radius + 8 mm clearance + 5 mm margin.
    assert plan.length == pytest.approx(177.0 + 5.0 + 8.0 + 5.0)
    assert [-hole.center.x for hole in holes] == pytest.approx(
        [50.0 + 25.4 * index for index in range(6)]
    )
    # Every post on its own string's line: the row crosses the centreline
    # and the bass edge follows it 15 mm out.
    ys = [hole.center.y * plan.bass_sign for hole in holes]
    assert ys == sorted(ys, reverse=True) and ys[0] > 0 > ys[-1]
    for hole in holes:
        own_edge = plan.bass_sign * plan.edge_y(-hole.center.x, plan.bass_sign)
        # The edge is one straight line; the posts are not quite collinear.
        assert own_edge - hole.center.y * plan.bass_sign == pytest.approx(15.0, abs=0.7)
    # The far edge makes room for the crossing posts.
    assert min(edge_distance(plan, hole) for hole in holes) >= 13.0 - 1e-6
    # The far side keeps room for a Strat's treble lobe.
    assert plan.half_width_at(plan.length, "treble") == pytest.approx(60.0)
    assert plan.half_width_at(plan.length, "bass") < 5.0


def test_three_plus_three_edges_follow_their_holes() -> None:
    geometry = Prototype001Parameters().build()
    plan = geometry.headstock.plan

    for hole in geometry.tuner_layout.holes:
        assert edge_distance(plan, hole) == pytest.approx(15.0, abs=0.3)
    assert plan.shoulder_shift == 0.0 and plan.tip_shift == 0.0
    assert plan.length == 150.0


def test_reverse_styles_mirror_the_row_to_the_treble_side() -> None:
    inline = replace(Prototype001Parameters(), headstock_style="6_inline").build()
    reverse = replace(
        Prototype001Parameters(), headstock_style="6_inline_reverse"
    ).build()

    assert reverse.headstock.plan.tip_shift == pytest.approx(
        -inline.headstock.plan.tip_shift
    )
    for a, b in zip(inline.tuner_layout.holes, reverse.tuner_layout.holes, strict=True):
        assert (a.center.x, a.center.y) == pytest.approx((b.center.x, -b.center.y))


def test_four_plus_two_puts_the_pair_at_the_root_opposite_the_first_two() -> None:
    geometry = replace(Prototype001Parameters(), headstock_style="4+2").build()
    row = geometry.tuner_layout.holes_on("bass")
    pair = geometry.tuner_layout.holes_on("treble")

    assert [-hole.center.x for hole in pair] == pytest.approx([62.7, 88.1])
    assert [-hole.center.x for hole in row] == pytest.approx([50.0, 75.4, 100.8, 126.2])
    # The row alone sets the length: 126.2 + 18 fits the 150 mm default.
    assert geometry.headstock.plan.length == 150.0


def test_four_plus_two_posts_sit_on_their_strings_straight_lines() -> None:
    parameters = replace(Prototype001Parameters(), headstock_style="4+2")
    geometry = parameters.build()
    plan = geometry.headstock.plan
    bass_sign = plan.bass_sign

    def string_u(string: int, distance: float) -> float:
        spacing = (
            parameters.nut_string_spacing
            + (parameters.nut_string_spacing - parameters.bridge_string_spacing)
            * distance
            / parameters.scale_length
        )
        return (3.5 - string) * spacing

    # Low E, A, D, G to the row (nearest first), the post 3 mm outboard.
    for hole, string in zip(
        geometry.tuner_layout.holes_on("bass"), (1, 2, 3, 4), strict=True
    ):
        expected = string_u(string, -hole.center.x) + 3.0
        assert hole.center.y * bass_sign == pytest.approx(expected)
    # High E nearest the nut, then B, on the treble side.
    for hole, string in zip(
        geometry.tuner_layout.holes_on("treble"), (6, 5), strict=True
    ):
        expected = string_u(string, -hole.center.x) - 3.0
        assert hole.center.y * bass_sign == pytest.approx(expected)
    # The G post ends up almost on the centreline: the row converges.
    row_y = [
        hole.center.y * bass_sign for hole in geometry.tuner_layout.holes_on("bass")
    ]
    assert row_y == sorted(row_y, reverse=True) and abs(row_y[-1]) < 1.0
    # Both edges follow their holes 15 mm out: a wide root, a narrow tip.
    for hole in geometry.tuner_layout.holes:
        assert edge_distance(plan, hole) >= 15.0 - 0.3
    # Room for a Music Man outline: a wide root lobe and a narrow tip.
    assert plan.shoulder_width == pytest.approx(76.0)
    assert plan.tip_width == pytest.approx(45.0)


def test_explicit_tip_settings_override_the_style_defaults() -> None:
    # A 100 mm tip centred on the neck still clears the diagonal row.
    geometry = replace(
        Prototype001Parameters(),
        headstock_style="6_inline",
        headstock_tip_width=100.0,
        headstock_tip_shift=0.0,
        headstock_length=200.0,
    ).build()

    assert geometry.headstock.plan.tip_width == 100.0
    assert geometry.headstock.plan.tip_shift == 0.0
    assert geometry.headstock.plan.length == 200.0
    # An override that cuts into the row's edge wood is rejected.
    with pytest.raises(HeadstockGeometryError, match="side-edge clearance"):
        replace(
            Prototype001Parameters(),
            headstock_style="6_inline",
            headstock_tip_width=30.0,
            headstock_tip_shift=-25.0,
        ).build()


def test_the_preset_rejects_bad_headstock_style_settings() -> None:
    with pytest.raises(NeckGeometryError, match="Unknown headstock style"):
        replace(Prototype001Parameters(), headstock_style="7_string").build()  # type: ignore[arg-type]
    with pytest.raises(NeckGeometryError, match="beyond the headstock root"):
        replace(
            Prototype001Parameters(),
            headstock_style="6_inline",
            tuner_inline_first_distance=30.0,
        ).build()
    with pytest.raises(NeckGeometryError, match="positive"):
        replace(Prototype001Parameters(), nut_string_spacing=0.0).build()

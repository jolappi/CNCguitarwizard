"""Tests for tuner holes placed where they are given (``tuner_hole_points``)."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import headstock_editor_layout, parameter_schema

BASS = ((45.0, 30.8), (80.0, 34.0), (120.0, 27.0), (170.0, 30.0))
TREBLE = ((45.0, 30.8), (95.0, 29.0), (140.0, 24.0), (170.0, 18.0))


def parameters(**overrides: object) -> Prototype001Parameters:
    return replace(Prototype001Parameters(), **overrides)  # type: ignore[arg-type]


def same_centres(
    first: tuple[tuple[str, float, float], ...],
    second: tuple[tuple[str, float, float], ...],
) -> bool:
    """Whether two lists of (side, x, y) hold the same holes, in order."""
    return [side for side, _, _ in first] == [side for side, _, _ in second] and [
        (x, y) for _, x, y in first
    ] == pytest.approx([(x, y) for _, x, y in second])


def points_of(params: Prototype001Parameters) -> list[list[float]]:
    """The style's holes as tuner_hole_points: (distance, offset) each."""
    points = []
    for side, x, y in params.tuner_centres():
        sign = params.bass_sign * (1.0 if side == "bass" else -1.0)
        points.append([-x, y / sign])
    return points


@pytest.mark.parametrize("style", ["3+3", "6_inline", "4+2", "2+4"])
def test_the_styles_own_places_given_back_change_nothing(style: str) -> None:
    by_style = parameters(headstock_style=style)
    given = replace(by_style, tuner_hole_points=tuple(map(tuple, points_of(by_style))))

    assert same_centres(given.tuner_centres(), by_style.tuner_centres())
    plan, tuners = given.headstock_design()
    fitted, style_tuners = by_style.headstock_design()
    assert [hole.side for hole in tuners.holes] == [
        hole.side for hole in style_tuners.holes
    ]
    assert [(hole.center.x, hole.center.y) for hole in tuners.holes] == pytest.approx(
        [(hole.center.x, hole.center.y) for hole in style_tuners.holes]
    )
    for distance in (60.0, 100.0):
        for side in ("bass", "treble"):
            assert plan.half_width_at(distance, side) == pytest.approx(
                fitted.half_width_at(distance, side)
            )


def test_a_3_plus_3_hole_moves_on_its_own_and_the_fitted_edge_follows() -> None:
    by_style = parameters()
    points = points_of(by_style)
    points[2][1] += 4.0  # the middle bass hole, 4 mm further out
    given = replace(by_style, tuner_hole_points=tuple(map(tuple, points)))

    centres = given.tuner_centres()
    before = by_style.tuner_centres()
    assert centres[2][2] == pytest.approx(before[2][2] + 4.0 * by_style.bass_sign)
    # The treble twin stays: the holes need not mirror each other.
    assert centres[3] == pytest.approx(before[3])
    plan, tuners = given.headstock_design()
    fitted, _ = by_style.headstock_design()
    assert plan.half_width_at(85.0, "bass") > fitted.half_width_at(85.0, "bass") + 1.0
    assert plan.half_width_at(85.0, "treble") == pytest.approx(
        fitted.half_width_at(85.0, "treble")
    )
    built = sorted((hole.center.x, hole.center.y) for hole in tuners.holes)
    assert built == pytest.approx(sorted((x, y) for _, x, y in centres))


def test_a_row_hole_moves_along_the_neck() -> None:
    by_style = parameters(headstock_style="6_inline")
    points = points_of(by_style)
    points[0][0] += 6.0
    given = replace(by_style, tuner_hole_points=tuple(map(tuple, points)))

    assert -given.tuner_centres()[0][1] == pytest.approx(points[0][0])
    _, tuners = given.headstock_design()
    assert len(tuners.holes) == 6


def test_the_headstock_grows_to_a_hole_past_its_tip() -> None:
    by_style = parameters()
    points = points_of(by_style)
    points[4][0] = points[5][0] = 190.0  # the last pair, far out
    given = replace(by_style, tuner_hole_points=tuple(map(tuple, points)))

    plan, _ = given.headstock_design()
    hole_edge = given.tuner_hole_diameter / 2.0 + given.tuner_edge_clearance
    assert plan.length >= 190.0 + hole_edge + given.tuner_tip_margin - 1e-9


def test_a_drawn_edge_still_keeps_its_distance_from_given_holes() -> None:
    drawn = parameters(
        headstock_outline="drawn",
        headstock_bass_edge=BASS,
        headstock_treble_edge=TREBLE,
    )
    points = points_of(drawn)
    plan, _ = drawn.headstock_design()
    # The first bass hole 14 mm from its edge: room enough for the hole,
    # but short of tuner_edge_offset (15 mm, less 0.5).
    points[0][1] = plan.half_width_at(points[0][0], "bass") - 14.0
    with pytest.raises(NeckGeometryError, match="from the drawn headstock edge"):
        replace(drawn, tuner_hole_points=tuple(map(tuple, points))).headstock_design()


@pytest.mark.parametrize(
    ("points", "match"),
    [
        (((55.0, 15.0),), "has 6 tuner holes; tuner_hole_points gives 1"),
        (((55.0, float("nan")),) * 6, "finite"),
        (
            (
                (85.0, 15.0),
                (55.0, 15.0),
                (55.0, 12.0),
                (85.0, 12.0),
                (110.0, 10.0),
                (110.0, 10.0),
            ),
            "the bass side's holes must run from the nut to the tip",
        ),
    ],
)
def test_points_that_do_not_fit_the_style_are_refused(
    points: object, match: str
) -> None:
    with pytest.raises(NeckGeometryError, match=match):
        parameters(tuner_hole_points=points).tuner_centres()


def test_the_editor_gets_the_moved_holes_and_their_clearance() -> None:
    by_style = parameters()
    points = points_of(by_style)
    points[0][0] -= 5.0
    layout = headstock_editor_layout({"prototype": {"tuner_hole_points": points}})

    assert layout["hole_clearance"] == by_style.tuner_hole_clearance
    assert [-hole["x"] for hole in layout["holes"]][0] == pytest.approx(points[0][0])
    # Its fitted start edges are fitted round the moved holes too.
    assert layout["start_edges"]["bass"]


def test_the_field_is_in_the_form_and_a_neck_template_puts_it_back() -> None:
    schema = parameter_schema()
    names = {
        field["name"] for group in schema["prototype"] for field in group["fields"]
    }
    assert "tuner_hole_points" in names
    for template in schema["neck_templates"].values():
        assert "tuner_hole_points" in template["resets"]

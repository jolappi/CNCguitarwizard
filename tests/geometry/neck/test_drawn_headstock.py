"""Tests for headstocks with drawn edges."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.exceptions import (
    HeadstockGeometryError,
    NeckGeometryError,
)
from cncguitarwizard.geometry.neck import HeadstockPlan
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

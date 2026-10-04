"""Tests for a drawn headstock whose edges meet in a point at the tip."""

import ast
import re
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import NeckMachiningParameters
from cncguitarwizard.cam.neck import plan_neck_machining
from cncguitarwizard.geometry.exceptions import HeadstockGeometryError
from cncguitarwizard.geometry.neck import HeadstockPlan
from cncguitarwizard.geometry.neck.headstock import POINT_LOFT_WIDTH, TIP_POINT_WIDTH
from cncguitarwizard.presets import Prototype001Parameters

START = ((45.0, 30.8), (80.0, 29.0), (120.0, 26.0), (140.0, 22.0))
# Narrowing past the tuners to meet 6 mm toward the bass side (bass at
# -Y on a right-handed neck: half-widths 6 and -6 meet at Y = -6).
BASS = (*START, (175.0, 6.0))
TREBLE = (*START, (175.0, -6.0))


def plan(**overrides: object) -> HeadstockPlan:
    values: dict[str, object] = {
        "bass_edge": BASS,
        "treble_edge": TREBLE,
        "bass_sign": -1.0,
    }
    values.update(overrides)
    return HeadstockPlan(175.0, 42.0, 45.0, 65.0, 40.0, **values)  # type: ignore[arg-type]


def test_edges_that_meet_at_the_tip_make_a_point() -> None:
    pointed = plan()
    assert pointed.pointed
    assert pointed.tip_point.x == pytest.approx(-175.0)
    assert pointed.tip_point.y == pytest.approx(-6.0)
    # The point once in the outline, the edges either side of it.
    tips = [p for p in pointed.boundary if p.x == pytest.approx(-175.0)]
    assert tips == [pointed.tip_point]
    assert pointed.tip_outline() == (pointed.tip_point, pointed.tip_point)
    assert pointed.reach == pytest.approx(175.0)
    # Corners less than TIP_POINT_WIDTH apart meet between them.
    nearly = plan(bass_edge=(*START, (175.0, 6.4)), treble_edge=(*START, (175.0, -6.0)))
    assert nearly.pointed and nearly.tip_point.y == pytest.approx(-6.2)
    assert TIP_POINT_WIDTH == 1.0
    # A narrow straight tip, 2 mm wide, is still a tip line.
    blunt = plan(bass_edge=(*START, (175.0, 7.0)), treble_edge=(*START, (175.0, -5.0)))
    assert not blunt.pointed
    assert blunt.width_at_distance(175.0) == pytest.approx(2.0)


@pytest.mark.parametrize(
    ("bass", "treble", "match"),
    [
        # Pinched in the middle, wide again past it.
        (
            ((45.0, 30.8), (100.0, 0.2), (175.0, 20.0)),
            ((45.0, 30.8), (100.0, 0.2), (175.0, 20.0)),
            "meet or cross 1",
        ),
        # Crossing before they meet at the tip.
        (
            (*START, (160.0, -4.0), (175.0, 1.0)),
            (*START, (160.0, 2.0), (175.0, -1.0)),
            "meet or cross",
        ),
        # Crossed at the tip, not meeting.
        ((*START, (175.0, -3.0)), (*START, (175.0, -3.0)), "cross"),
    ],
)
def test_edges_still_may_not_pinch_or_cross(
    bass: tuple[tuple[float, float], ...],
    treble: tuple[tuple[float, float], ...],
    match: str,
) -> None:
    with pytest.raises(HeadstockGeometryError, match=match):
        plan(bass_edge=bass, treble_edge=treble)


def test_a_pointed_tip_takes_no_tip_points() -> None:
    with pytest.raises(HeadstockGeometryError, match="takes no tip points"):
        plan(tip_points=((5.0, -6.0),))


def test_the_solid_is_lofted_wide_to_be_cut_back_to_the_point() -> None:
    pointed = plan()
    # Its last run under POINT_LOFT_WIDTH, lofted that wide round its middle.
    assert pointed.width_at_distance(pointed.point_start) < POINT_LOFT_WIDTH
    assert pointed.width_at_distance(pointed.point_start - 0.5) >= POINT_LOFT_WIDTH
    for distance in (pointed.point_start, 170.0, 175.0):
        wide = pointed.envelope_y(distance, 1.0) - pointed.envelope_y(distance, -1.0)
        assert wide == pytest.approx(POINT_LOFT_WIDTH)
    # Wider than that, the envelope is the edges.
    assert pointed.envelope_y(100.0, 1.0) == pytest.approx(pointed.edge_y(100.0, 1.0))


def test_a_pointed_headstock_builds_machines_and_exports() -> None:
    parameters = replace(
        Prototype001Parameters(),
        headstock_outline="drawn",
        headstock_bass_edge=((22.5, 25.9), (45.0, 30.8), (136.9, 22.4), (167.2, 7.9)),
        headstock_treble_edge=(
            (22.5, 25.9),
            (45.0, 30.8),
            (136.9, 22.4),
            (167.2, -7.9),
        ),
    )
    geometry = parameters.build()
    headstock = geometry.headstock.plan
    assert headstock.pointed
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert '"headstock tip cut"' in source
    # The neck's loft is never pinched to the point: its tip section is
    # POINT_LOFT_WIDTH wide, cut back to the point afterwards.
    sections = ast.literal_eval(
        re.search(r"^NECK_SECTION_POINTS = (.*)$", source, re.M).group(1)  # type: ignore[union-attr]
    )
    tip = min(sections, key=lambda section: section[0][0])
    assert tip[0][0] == pytest.approx(-167.2)
    assert tip[-1][1] - tip[0][1] == pytest.approx(POINT_LOFT_WIDTH, abs=0.01)
    neck = plan_neck_machining(geometry, NeckMachiningParameters())
    assert neck.setups

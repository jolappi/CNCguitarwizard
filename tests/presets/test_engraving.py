"""Tests for the decorative engraving: its random layout, area and program."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.geometry.body import Engraving
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.engraving import (
    MIN_LINE,
    MOTIF,
    ROW_STEP,
    EngravingArea,
    engraving_lines,
)
from cncguitarwizard.webapp import body_editor_layout


def _square(size: float) -> tuple[Point2D, ...]:
    half = size / 2.0
    return (
        Point2D(-half, -half),
        Point2D(half, -half),
        Point2D(half, half),
        Point2D(-half, half),
    )


def test_the_motif_is_the_drawings_five_arcs() -> None:
    radii = sorted(round(arc.radius, 2) for arc in MOTIF)

    assert radii == [16.3, 29.12, 31.85, 61.87, 81.47]


def test_the_same_seed_gives_the_same_pattern_and_another_a_new_one() -> None:
    area = EngravingArea(_square(300.0), 10.0, (), (), 4.0)

    first = engraving_lines(area, 7, 50.0)
    assert first == engraving_lines(area, 7, 50.0)
    assert first != engraving_lines(area, 8, 50.0)
    assert len(first) > 10


def test_the_lines_stay_in_the_area_clear_of_what_is_kept_out() -> None:
    keep_out = (_square(60.0),)
    hole = (Point2D(100.0, 100.0), 5.0)
    area = EngravingArea(_square(300.0), 10.0, keep_out, (hole,), 4.0)
    lines = engraving_lines(area, 3, 50.0)

    # (Tested on rows ROW_STEP apart: to within half of that.)
    inside = _square(300.0 - 2 * 10.0 + 2 * ROW_STEP)
    for line in lines:
        assert (
            sum(
                math.dist((a.x, a.y), (b.x, b.y))
                for a, b in zip(line, line[1:], strict=False)
            )
            >= MIN_LINE - 1e-9
        )
        for p in line:
            assert point_in_polygon(p, inside)
            # The kept-out square grown by the clearance stays empty.
            assert not (abs(p.x) < 30.0 + 3.9 and abs(p.y) < 30.0 + 3.9)
            assert math.dist((p.x, p.y), (100.0, 100.0)) > 5.0 + 3.9


def test_an_engraving_must_be_shallower_than_half_the_body() -> None:
    with pytest.raises(BodyGeometryError, match="positive"):
        Engraving(((Point2D(0, 0), Point2D(1, 0)),), 0.0)
    with pytest.raises(BodyGeometryError, match="half the body"):
        replace(
            Prototype001Parameters(), body_engraving=True, body_engraving_depth=25.0
        ).build()


def test_the_body_gets_an_engraving_clear_of_its_features() -> None:
    parameters = replace(
        Prototype001Parameters(),
        body_engraving=True,
        body_pickguard=True,
        body_arm_contour_depth=12.0,
    )
    layout = parameters.body_layout()
    engraving = layout.engraving
    assert engraving is not None and engraving.depth == 2.0
    assert engraving.lines

    guard = layout.pickguard
    assert guard is not None
    features = [
        layout.neck_pocket.outline,
        guard.plate.outline,
        *(c.region() for c in layout.contours),
        *(c.outline for c in (layout.neck_pickup, layout.bridge_pickup) if c),
        *(c.outline for c in layout.extra_cavities),
    ]
    for line in engraving.lines:
        for p in line:
            assert point_in_polygon(p, layout.outline.points)
            assert not any(point_in_polygon(p, f) for f in features)
    # Off by default.
    assert Prototype001Parameters().body_layout().engraving is None


def test_the_engraving_gets_its_own_v_bit_program() -> None:
    geometry = replace(Prototype001Parameters(), body_engraving=True).build()
    plan = plan_body_machining(geometry.body, MachiningParameters())

    setup = plan.top_engraving
    assert setup is not None and setup.name == "Body_top_engraving"
    assert setup in plan.setups
    (path,) = setup.toolpaths
    assert path.deepest_z() == pytest.approx(-2.0)
    # Two 1 mm passes along every line.
    engraving = geometry.body.engraving
    assert engraving is not None
    assert path.cutting_length() >= 2.0 * engraving.length() - 1e-6
    assert setup.tool is not None
    # A 60 degree V-bit 2 mm deep leaves a 2.31 mm groove.
    assert setup.tool.tool_diameter == pytest.approx(2 * 2 * math.tan(math.pi / 6))
    assert replace(Prototype001Parameters()).build().body.engraving is None


def test_the_editor_and_the_freecad_script_show_the_engraving() -> None:
    from cncguitarwizard.backends.freecad import FreeCADScriptExporter

    payload = {"prototype": {"body_engraving": True, "body_engraving_seed": 5}}
    editor = body_editor_layout(payload)
    assert editor["engraving"] and all(len(line) >= 2 for line in editor["engraving"])
    assert body_editor_layout({"prototype": {}})["engraving"] is None

    geometry = replace(Prototype001Parameters(), body_engraving=True).build()
    script = FreeCADScriptExporter().render_prototype001(geometry)
    assert "engraving_feature" in script


@pytest.mark.parametrize("seed", [1, 2, 3, 63269])
def test_no_line_stands_alone_and_no_cluster_is_too_thick(seed: int) -> None:
    from cncguitarwizard.presets.engraving import (
        CLUSTER_CELL,
        LONE_GAP,
        MAX_CLUSTER,
    )

    engraving = (
        replace(Prototype001Parameters(), body_engraving=True, body_engraving_seed=seed)
        .body_layout()
        .engraving
    )
    assert engraving is not None
    lines = engraving.lines

    # Every line has another within LONE_GAP of it.
    for index, line in enumerate(lines):
        assert any(
            math.dist((p.x, p.y), (q.x, q.y)) <= LONE_GAP
            for other, near in enumerate(lines)
            if other != index
            for q in near
            for p in line[::3]
        )
    # No three-by-three block of grid squares holds more than MAX_CLUSTER.
    cells: dict[tuple[int, int], set[int]] = {}
    for index, line in enumerate(lines):
        for p in line:
            cell = (math.floor(p.x / CLUSTER_CELL), math.floor(p.y / CLUSTER_CELL))
            cells.setdefault(cell, set()).add(index)
    for i, j in cells:
        block = set().union(
            *(
                cells.get((i + di, j + dj), set())
                for di in (-1, 0, 1)
                for dj in (-1, 0, 1)
            )
        )
        assert len(block) <= MAX_CLUSTER


def test_the_backs_cavities_are_engraved_over_unless_too_near_the_top() -> None:
    from cncguitarwizard.presets.prototype001 import ENGRAVING_WALL

    parameters = replace(Prototype001Parameters(), body_engraving=True)
    layout = parameters.body_layout()
    engraving = layout.engraving
    assert engraving is not None
    rear = layout.control_cavity
    assert rear is not None
    # 8 mm of top over the control cavity: plenty for a 2 mm engraving.
    assert parameters.body_thickness - rear.cavity.depth >= 2.0 + ENGRAVING_WALL
    assert any(
        point_in_polygon(p, rear.cover_recess.outline)
        for line in engraving.lines
        for p in line
    )
    # With 4 mm of top left the cavity is engraved round.
    thin = replace(parameters, body_rear_cavity_top_wall=4.0).body_layout()
    assert thin.engraving is not None and thin.control_cavity is not None
    assert not any(
        point_in_polygon(p, thin.control_cavity.cavity.outline)
        for line in thin.engraving.lines
        for p in line
    )

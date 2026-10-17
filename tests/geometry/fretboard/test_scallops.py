"""Tests for a scalloped fretboard: the playing surface hollowed between frets."""

import ast
import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam.fretboard import (
    FretboardMachiningParameters,
    plan_fretboard_machining,
)
from cncguitarwizard.geometry.exceptions import FretboardGeometryError
from cncguitarwizard.geometry.fretboard import (
    FretboardScallops,
    FretboardSurface,
    FretSkew,
)
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import parameter_schema


def surface(**changes: object) -> FretboardSurface:
    values: dict[str, object] = {
        "scale_length": 647.7,
        "fret_count": 22,
        "nut_width": 42.0,
        "last_fret_width": 56.0,
        "radius": 241.3,
        "center_thickness": 6.0,
    }
    return FretboardSurface(**{**values, **changes})  # type: ignore[arg-type]


def test_a_scallop_is_deepest_mid_space_and_flat_at_the_frets() -> None:
    board = surface()
    scallops = FretboardScallops(board, 15, 2.0, 1.5)
    frets = board.station_positions
    for number in scallops.fret_numbers:
        start, end = frets[number], frets[number + 1]
        middle = (start + end) / 2.0
        # As deep across the board, following its radius.
        for y in (-20.0, 0.0, 20.0):
            assert scallops.depth_at(middle, y) == pytest.approx(2.0)
        # Nothing on the fret lines or their lands.
        for x in (start, start + 1.5, end - 1.5, end):
            assert scallops.depth_at(x, 0.0) == 0.0
        # A circular arc between the lands.
        quarter = start + 1.5 + (end - start - 3.0) / 4.0
        assert 0.0 < scallops.depth_at(quarter, 0.0) < 2.0
    # The spaces before fret 15 and past the last fret are left alone.
    assert scallops.depth_at((frets[14] + frets[15]) / 2.0, 0.0) == 0.0
    assert scallops.depth_at(frets[-1] + 2.0, 0.0) == 0.0


def test_scallops_may_start_at_the_nut() -> None:
    board = surface()
    scallops = FretboardScallops(board, 0, 2.0, 1.5)
    assert list(scallops.fret_numbers) == list(range(22))
    assert scallops.depth_at(board.station_positions[1] / 2.0, 0.0) == (
        pytest.approx(2.0)
    )


def test_a_leaning_fret_leans_its_scallop() -> None:
    board = surface(skew=FretSkew(slant=0.1))
    scallops = FretboardScallops(board, 15, 2.0, 1.5)
    start, end = board.station_positions[15], board.station_positions[16]
    middle = (start + end) / 2.0
    # 20 mm off the centreline the space is 2 mm further along.
    assert scallops.depth_at(middle + 2.0, 20.0) == pytest.approx(2.0)
    assert scallops.depth_at(middle, 20.0) < 2.0


def test_the_hollowed_rows_keep_the_frets_and_dip_between_them() -> None:
    board = surface()
    scallops = FretboardScallops(board, 15, 2.0, 1.5)
    rows = scallops.rows()
    stations = [row[len(row) // 2].x for row in rows]
    assert stations == sorted(stations)
    # Every fret's own row is there, untouched.
    for row in board.mesh.rows:
        (same,) = [r for r in rows if math.isclose(r[0].x, row[0].x)]
        assert same == row
    # The deepest row is 2 mm below the crown.
    crown = board.center_thickness
    assert min(row[len(row) // 2].z for row in rows) == pytest.approx(crown - 2.0)
    assert len(rows) > len(board.mesh.rows) + 7 * 16


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"from_fret": 22}, "from 0 \\(the nut\\) to 21"),
        ({"from_fret": -1}, "from 0 \\(the nut\\) to 21"),
        ({"depth": 0.0}, "depth must be finite and positive"),
        ({"land": -0.5}, "land must be finite and non-negative"),
        ({"land": 8.0}, "too short for a 2 mm scallop"),
    ],
)
def test_scallops_the_board_cannot_take_are_refused(
    changes: dict[str, object], match: str
) -> None:
    values: dict[str, object] = {"from_fret": 15, "depth": 2.0, "land": 1.5}
    values.update(changes)
    with pytest.raises(FretboardGeometryError, match=match):
        FretboardScallops(surface(), **values)  # type: ignore[arg-type]


def test_a_scallop_leaves_wood_under_it_at_the_edge() -> None:
    # 2.5 mm under a 4.5 mm board, less its radius at the edge (1.6 mm),
    # leaves under SCALLOP_FLOOR.
    with pytest.raises(FretboardGeometryError, match="keep at least 1.5 mm"):
        FretboardScallops(surface(center_thickness=4.5), 15, 2.5, 1.5)


def strat(**changes: object) -> Prototype001Parameters:
    from cncguitarwizard.presets.styles import STYLES

    return replace(
        Prototype001Parameters.for_instrument("electric_guitar"),
        **{**STYLES["stratocaster"].prototype_values("electric_guitar"), **changes},
    )


def test_the_inlays_under_a_scallop_are_cut_deeper_than_it() -> None:
    # The scallops are cut through the set inlays: 2 mm dots under 2 mm
    # scallops would be cut away, so every pocket is cut 1 mm deeper than
    # the deepest scallop over a marker (one sheet for the pieces).
    geometry = strat(fretboard_scalloped=True).build()
    assert geometry.fretboard_scallops is not None
    assert geometry.fretboard_scallops.from_fret == 15
    assert geometry.inlay_layout.depth == pytest.approx(3.0)
    # Deep enough already, or no marker under a scallop: as set.
    deep = strat(fretboard_scalloped=True, inlay_depth=3.5).build()
    assert deep.inlay_layout.depth == 3.5
    past = strat(fretboard_scalloped=True, fretboard_scallop_from_fret=21).build()
    assert past.inlay_layout.depth == 2.0
    # Off, there are none.
    plain = strat().build()
    assert plain.fretboard_scallops is None and plain.inlay_layout.depth == 2.0


def test_the_model_lofts_the_board_and_its_binding_through_the_scallops() -> None:
    geometry = strat(fretboard_scalloped=True, fretboard_binding_width=1.5).build()
    scallops = geometry.fretboard_scallops
    assert scallops is not None
    source = FreeCADScriptExporter().render_prototype001(geometry)

    def literal(name: str) -> object:
        (line,) = [
            line for line in source.splitlines() if line.startswith(f"{name} = ")
        ]
        return ast.literal_eval(line.split("=", 1)[1])

    sections = literal("FRETBOARD_SECTION_POINTS")
    assert isinstance(sections, list)
    assert len(sections) == len(scallops.rows())
    lowest = min(point[2] for section in sections for point in section if point[2] > 0)
    assert lowest < geometry.fretboard_surface.center_thickness - 2.5
    # The binding's top follows the scallops along the edges too.
    strips = literal("FRETBOARD_BINDING_SECTIONS")
    assert isinstance(strips, list)
    assert len(strips[0]) == len(sections)
    # The slots still follow the frets' own rows.
    slots = literal("FRET_SURFACE_ROWS")
    assert isinstance(slots, list)
    assert len(slots) == geometry.fretboard_surface.fret_count


def test_the_scallops_are_cut_after_the_inlays_and_slots() -> None:
    geometry = strat(fretboard_scalloped=True).build()
    plan = plan_fretboard_machining(geometry, FretboardMachiningParameters())
    names = [setup.name for setup in plan.setups]
    assert names == [
        "Fretboard_index_pins",
        "Fretboard_radius",
        "Fretboard_inlays",
        "Fretboard_slots",
        "Fretboard_scallops",
        "Fretboard_outline",
    ]
    assert len(plan.preview_outlines) == len(plan.setups)
    assert plan.scallops is not None
    assert any("Glue the inlay pieces in" in note for note in plan.scallops.notes)
    assert any(
        "pockets are 3 mm deep" in note and "at least 1.0 mm" in note
        for note in plan.scallops.notes
    )
    moves = [move for path in plan.scallops.toolpaths for move in path.moves]
    radius = [move for path in plan.radius.toolpaths for move in path.moves]
    # 2 mm below the radius at its deepest, and only over the scalloped
    # frets (the 15th on), not nearer the nut.
    deepest = min(move.z for move in moves)
    assert deepest == pytest.approx(min(move.z for move in radius) - 2.0, abs=0.1)
    surface = geometry.fretboard_surface
    fifteenth = surface.station_positions[15] - plan.origin_x
    ball = FretboardMachiningParameters().ball.tool_radius
    cutting = [move for move in moves if not move.rapid and move.z < 0.0]
    assert min(move.x for move in cutting) >= fifteenth - ball - 1.0
    # Unscalloped, the plan is as before.
    plain = plan_fretboard_machining(strat().build(), FretboardMachiningParameters())
    assert plain.scallops is None and len(plain.setups) == 5


def test_the_form_offers_the_scallops() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    for name in (
        "fretboard_scalloped",
        "fretboard_scallop_from_fret",
        "fretboard_scallop_depth",
    ):
        assert not fields[name]["advanced"]
    assert fields["fretboard_scallop_land"]["advanced"]
    assert fields["fretboard_scallop_from_fret"]["default"] == 15

"""Tests for blind fret slots, stopped short of the fretboard's edges."""

import json
import math
import re
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import (
    FretboardMachiningParameters,
    MachiningParameters,
    plan_fretboard_machining,
)
from cncguitarwizard.geometry.exceptions import FretboardGeometryError
from cncguitarwizard.geometry.fretboard import FretLayout, shortened
from cncguitarwizard.geometry.primitives import Line2D, Point2D
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.dxf import render_plan_dxf
from cncguitarwizard.render.svg.plan_view import render_plan_view_svg

INSET = 2.5


def blind(**overrides: object) -> Prototype001Parameters:
    return replace(Prototype001Parameters(), fret_slot_end_inset=INSET, **overrides)


def slot_plan(parameters: Prototype001Parameters):  # type: ignore[no-untyped-def]
    geometry = parameters.build()
    fretboard = FretboardMachiningParameters().with_form_settings(MachiningParameters())
    return geometry, plan_fretboard_machining(geometry, fretboard)


def test_slots_are_cut_through_the_edges_by_default() -> None:
    layout = Prototype001Parameters().build().fret_layout

    assert layout.slot_end_inset == 0.0
    assert all(layout.cut_slot(slot) is slot for slot in layout.slots)


def test_a_blind_slot_stops_short_of_each_edge_along_the_fret_line() -> None:
    layout = blind(fret_slant_angle=5.0).build().fret_layout

    for slot in layout.slots:
        cut = layout.cut_slot(slot)
        assert math.dist((slot.start.x, slot.start.y), (cut.start.x, cut.start.y)) == (
            pytest.approx(INSET)
        )
        assert math.dist((slot.end.x, slot.end.y), (cut.end.x, cut.end.y)) == (
            pytest.approx(INSET)
        )
        assert cut.length == pytest.approx(slot.length - 2.0 * INSET)
    # The fret lines themselves still run edge to edge.
    assert layout.slots == replace(layout, slot_end_inset=0.0).slots


def test_shortening_that_leaves_nothing_is_rejected() -> None:
    line = Line2D(Point2D(0.0, -2.0), Point2D(0.0, 2.0))

    assert shortened(line, 1.0) == Line2D(Point2D(0.0, -1.0), Point2D(0.0, 1.0))
    with pytest.raises(FretboardGeometryError, match="leaves nothing"):
        shortened(line, 2.0)


@pytest.mark.parametrize("inset", [-1.0, math.nan])
def test_a_negative_or_unreadable_inset_is_rejected(inset: float) -> None:
    fretboard = Prototype001Parameters().build().fret_layout.fretboard

    with pytest.raises(FretboardGeometryError, match="end inset"):
        FretLayout(fretboard, 22, slot_end_inset=inset)


def test_an_inset_past_the_outer_strings_is_rejected() -> None:
    with pytest.raises(FretboardGeometryError, match="fret_slot_end_inset"):
        replace(Prototype001Parameters(), fret_slot_end_inset=4.5).build()


def test_the_cutter_stops_inset_short_of_the_edges() -> None:
    geometry, plan = slot_plan(blind())
    radius = plan.slots.tool.tool_radius if plan.slots.tool else 0.0

    for path, slot in zip(
        plan.slots.toolpaths, geometry.fret_layout.slots, strict=True
    ):
        ys = [move.y + plan.origin_y for move in path.moves if not move.rapid]
        edge = max(abs(slot.start.y), abs(slot.end.y))
        assert max(ys) == pytest.approx(edge - INSET - radius, abs=0.01)
        assert min(ys) == pytest.approx(-(edge - INSET - radius), abs=0.01)
    notes = " ".join(plan.slots.notes)
    assert f"stops {INSET:g} mm short of each of the board's edges" in notes
    assert f"Nip each fret's tang back {INSET:g} mm at both ends" in notes


def test_through_slots_still_run_out_past_the_edges() -> None:
    geometry, plan = slot_plan(Prototype001Parameters())
    slot = geometry.fret_layout.slots[0]
    ys = [move.y + plan.origin_y for move in plan.slots.toolpaths[0].moves]

    assert max(ys) > max(abs(slot.start.y), abs(slot.end.y))
    assert "past the board's edge" in " ".join(plan.slots.notes)


def test_a_blind_slot_on_fanned_frets_follows_its_fret_line() -> None:
    geometry, plan = slot_plan(blind(bass_scale_length=647.7))

    for path, slot in zip(
        plan.slots.toolpaths, geometry.fret_layout.slots, strict=True
    ):
        cut = geometry.fret_layout.cut_slot(slot)
        slope = (cut.end.x - cut.start.x) / (cut.end.y - cut.start.y)
        for move in path.moves:
            if move.rapid:
                continue
            x = move.x + plan.origin_x
            y = move.y + plan.origin_y
            assert x == pytest.approx(cut.start.x + slope * (y - cut.start.y), abs=1e-6)


def test_freecad_cuts_each_slot_on_its_row_short_of_the_edges() -> None:
    geometry = blind().build()
    source = FreeCADScriptExporter().render_prototype001(geometry)

    assert "fret_slot_side_overcut = 0.0" in source
    match = re.search(r"^FRET_SURFACE_ROWS = (.*)$", source, re.MULTILINE)
    assert match is not None
    rows = json.loads(match.group(1))
    full = geometry.fretboard_surface.mesh.rows[1]
    first = rows[0]
    # Rounded to a tenth of a micron in the script.
    assert math.dist(first[0][:2], (full[0].x, full[0].y)) == pytest.approx(
        INSET, abs=1e-3
    )
    assert math.dist(first[-1][:2], (full[-1].x, full[-1].y)) == pytest.approx(
        INSET, abs=1e-3
    )
    through = FreeCADScriptExporter().render_prototype001(
        Prototype001Parameters().build()
    )
    assert "fret_slot_side_overcut = 1.0" in through


def first_slot_line(dxf: str) -> tuple[float, float, float, float]:
    """Return the first line on the DXF's fret-slot layer: x1, y1, x2, y2."""
    lines = dxf.splitlines()
    pairs = list(zip(lines[0::2], lines[1::2], strict=False))
    for index, (code, value) in enumerate(pairs):
        if code.strip() == "0" and value == "LINE":
            entity = {}
            for inner_code, inner_value in pairs[index + 1 :]:
                if inner_code.strip() == "0":
                    break
                entity[inner_code.strip()] = inner_value
            if entity.get("8") == "FRET_SLOTS":
                return tuple(  # type: ignore[return-value]
                    float(entity[key]) for key in ("10", "20", "11", "21")
                )
    raise AssertionError("no fret slot in the DXF")


def test_the_plan_drawings_show_the_slots_as_cut() -> None:
    geometry = blind().build()
    cut = geometry.fret_layout.cut_slot(geometry.fret_layout.slots[0])

    x1, y1, x2, y2 = first_slot_line(render_plan_dxf(geometry))
    assert (x1, y1, x2, y2) == pytest.approx(
        (cut.start.x, cut.start.y, cut.end.x, cut.end.y), abs=1e-3
    )
    through = Prototype001Parameters().build()
    assert render_plan_view_svg(geometry) != render_plan_view_svg(through)

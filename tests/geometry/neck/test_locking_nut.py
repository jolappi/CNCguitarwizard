"""Tests for the top-mounted Floyd Rose locking nut."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.cam.fretboard import (
    FretboardMachiningParameters,
    fretboard_outline_polygon,
    plan_fretboard_machining,
)
from cncguitarwizard.geometry.body import FloydRoseSpec
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.neck import LOCKING_NUT_SPECS, LockingNut
from cncguitarwizard.geometry.neck.locking_nut import NUT_ABOVE_FRETS
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import parameter_schema


@pytest.fixture(scope="module")
def floyd():  # type: ignore[no-untyped-def]
    return replace(Prototype001Parameters(), body_bridge=FloydRoseSpec()).build()


def _nut(kind: str, **overrides: float) -> LockingNut:
    values = {
        "lean": 0.0,
        "neck_width": 43.0,
        "fretboard_thickness": 6.0,
        "fret_height": 1.2,
        "screw_diameter": 2.5,
        "screw_depth": 8.0,
        **overrides,
    }
    return LockingNut.placed(LOCKING_NUT_SPECS[kind], **values)  # type: ignore[arg-type]


def test_the_r2_nut_stands_on_the_fretboard_run_on_under_it() -> None:
    nut = _nut("r2")

    # Its top a little above the frets' tops: 6 + 1.2 - (5.85 - 0.38).
    assert nut.shelf_height == pytest.approx(6.0 + 1.2 - 5.85 + NUT_ABOVE_FRETS)
    assert nut.on_fretboard and nut.shim == 0.0
    assert nut.seat_length == 16.0
    a, b = nut.screw_centres()
    assert (a.x, a.y, b.x, b.y) == pytest.approx((-7.5, -6.795, -7.5, 6.795))


def test_the_deep_r3_nut_stands_on_the_neck_on_a_shim() -> None:
    nut = _nut("r3")

    assert not nut.on_fretboard
    assert nut.shim == pytest.approx(6.0 + 1.2 - 7.10 + NUT_ABOVE_FRETS)


def test_a_leaning_nut_line_leans_its_seat_and_screws() -> None:
    nut = _nut("r2", lean=0.1)

    front = nut.seat_outline()[:2]
    assert [p.x for p in front] == pytest.approx([-2.15, 2.15])
    a, b = nut.screw_centres()
    assert b.x - a.x == pytest.approx(0.1 * 13.59)


def test_a_nut_wider_than_the_neck_or_below_the_glue_face_is_refused() -> None:
    with pytest.raises(NeckGeometryError, match="nut_width must be at least"):
        _nut("r3", neck_width=42.0)
    with pytest.raises(NeckGeometryError, match="below the fretboard's glue face"):
        _nut("r3", fretboard_thickness=4.0)


def test_a_floyd_rose_bridge_brings_the_r2_nut_and_a_longer_seat(floyd) -> None:  # type: ignore[no-untyped-def]
    plain = Prototype001Parameters().build()

    assert plain.locking_nut is None
    assert plain.headstock.nut_seat_length == 5.0
    assert floyd.locking_nut.spec is LOCKING_NUT_SPECS["r2"]
    # The headstock face starts behind the nut's 16 mm seat.
    assert floyd.headstock.nut_seat_length == 16.0
    assert floyd.headstock.face_start_x(0.0) == -16.0


def test_the_nut_can_be_chosen_or_left_plain() -> None:
    parameters = replace(Prototype001Parameters(), body_bridge=FloydRoseSpec())

    assert replace(parameters, locking_nut="none").build().locking_nut is None
    r3 = replace(parameters, locking_nut="r3", nut_width=43.0).build().locking_nut
    assert r3 is not None and r3.spec.name == "Floyd Rose R3"
    with pytest.raises(NeckGeometryError, match="nut_width"):
        replace(parameters, locking_nut="r3").build()
    # A plain bridge can take one too.
    assert replace(Prototype001Parameters(), locking_nut="r2").build().locking_nut


def test_a_headstock_adjusted_truss_rod_starts_under_the_whole_seat() -> None:
    parameters = replace(
        Prototype001Parameters(),
        body_bridge=FloydRoseSpec(),
        truss_rod_adjustment="headstock",
    )
    geometry = parameters.build()
    channel = geometry.truss_rod_channel
    nut = geometry.locking_nut

    # The adjuster's pocket starts under the nut's back edge, its trough
    # behind it; the nut's screws miss the pocket on either side.
    starts = [min(p.x for p in part.boundary) for part in channel.pockets]
    assert min(starts) == pytest.approx(-16.0)
    for pocket in channel.pockets:
        half = max(abs(p.y) for p in pocket.boundary)
        for screw in nut.screw_centres():
            assert abs(screw.y) - nut.screw_diameter / 2.0 > half + 0.5


def test_the_freecad_script_runs_the_board_on_and_drills_the_screws(floyd) -> None:  # type: ignore[no-untyped-def]
    source = FreeCADScriptExporter().render_prototype001(floyd)
    plain = FreeCADScriptExporter().render_prototype001(
        Prototype001Parameters().build()
    )

    assert "locking nut shelf" in source
    assert source.count("locking_nut_screw = Part.makeCylinder(") == 2
    assert "locking nut screw 2 in the fretboard" in source
    assert "locking nut" not in plain


def test_the_r3_nut_leaves_the_fretboard_alone_but_drills_the_neck() -> None:
    geometry = replace(
        Prototype001Parameters(), locking_nut="r3", nut_width=43.0
    ).build()
    source = FreeCADScriptExporter().render_prototype001(geometry)

    assert "locking nut shelf" not in source
    assert "locking nut screw 1 in the neck" in source
    assert "in the fretboard" not in source


def test_the_fretboard_cam_mills_the_shelf_before_the_outline(floyd) -> None:  # type: ignore[no-untyped-def]
    parameters = FretboardMachiningParameters()
    plan = plan_fretboard_machining(floyd, parameters)
    outline = fretboard_outline_polygon(floyd)

    assert min(p.x for p in outline) == pytest.approx(-16.0)
    shelf, profile = plan.outline.toolpaths
    assert shelf.name == "Floyd Rose R2 locking nut shelf"
    deepest = min(move.z for move in shelf.moves)
    assert deepest == pytest.approx(
        -(parameters.blank_thickness - floyd.locking_nut.shelf_height)
    )
    assert any("1.73 mm shelf" in note for note in plan.outline.notes)


def test_the_neck_cam_says_how_to_fit_the_nut(floyd) -> None:  # type: ignore[no-untyped-def]
    notes = " ".join(plan_neck_machining(floyd, NeckMachiningParameters()).top.notes)

    assert "Floyd Rose R2 locking nut" in notes
    assert "13.59 mm apart" in notes
    assert "16 mm flat seat" in notes


def test_the_web_form_offers_the_nut() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }

    nut = fields["locking_nut"]
    assert nut["type"] == "choice" and not nut["advanced"]
    assert nut["options"] == ["auto", "none", "r2", "r3"]
    assert nut["default"] == "auto"

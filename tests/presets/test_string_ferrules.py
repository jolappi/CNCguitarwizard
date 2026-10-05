"""Tests for the string ferrules' counterbores and the bridge's notes."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters
from cncguitarwizard.cam.body import plan_body_machining
from cncguitarwizard.geometry.body import (
    BodySolid,
    DrilledHole,
    FloydRoseSpec,
    HardtailSpec,
    SingleStringBridgeSpec,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.presets import Prototype001Parameters

HARDTAIL = replace(Prototype001Parameters(), body_bridge=HardtailSpec())


def _ferrules(body: BodySolid) -> list[DrilledHole]:
    return [hole for hole in body.rear_holes if hole.name.startswith("String")]


def test_every_string_through_hole_gets_a_ferrule_counterbore() -> None:
    geometry = HARDTAIL.build()
    body = geometry.body
    through = [hole for hole in body.holes if "through hole" in hole.name]
    ferrules = _ferrules(body)
    assert len(ferrules) == len(through) == 6
    for hole, ferrule in zip(through, ferrules, strict=True):
        # Right under the string's hole, from the back, hidden by the
        # ferrule.
        assert ferrule.center == hole.center
        assert ferrule.diameter == 8.0 and ferrule.depth == 6.0
        assert ferrule.name == hole.name.replace("through hole", "ferrule")
    plan = plan_body_machining(body, MachiningParameters())
    (back,) = [setup for setup in plan.setups if setup.name == "Body_back"]
    cut = {path.name: path for path in back.toolpaths}
    assert "String 1 ferrule" in cut
    assert min(move.z for move in cut["String 1 ferrule"].moves) == pytest.approx(-6.0)
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert "'string 1 ferrule cut'" in source


def test_a_bass_takes_wider_ferrules_and_single_string_bridges_too() -> None:
    bass = Prototype001Parameters.for_instrument("bass_guitar").build().body
    assert {(f.diameter, f.depth) for f in _ferrules(bass)} == {(9.5, 6.5)}
    assert len(_ferrules(bass)) == 4
    singles = (
        replace(
            Prototype001Parameters.for_instrument("five_string_bass"),
            body_bridge=SingleStringBridgeSpec(string_count=5),
        )
        .build()
        .body
    )
    assert len(_ferrules(singles)) == 5


def test_no_ferrules_without_strings_through_or_with_no_depth() -> None:
    top_loaded = replace(
        HARDTAIL, body_bridge=HardtailSpec(string_through=False)
    ).build()
    assert _ferrules(top_loaded.body) == []
    none = replace(HARDTAIL, body_string_ferrule_depth=0.0).build()
    assert _ferrules(none.body) == []
    # The default Kahler has no string holes.
    assert _ferrules(Prototype001Parameters().build().body) == []


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"body_string_ferrule_diameter": 3.0}, "wider than the string holes"),
        ({"body_string_ferrule_depth": 30.0}, "under half"),
        ({"body_string_ferrule_depth": -1.0}, "under half"),
    ],
)
def test_ferrules_that_cannot_be_cut_are_refused(
    overrides: dict[str, float], match: str
) -> None:
    with pytest.raises(BodyGeometryError, match=match):
        replace(HARDTAIL, **overrides).build()  # type: ignore[arg-type]


def test_the_bridge_notes_reach_the_top_program() -> None:
    seven = replace(
        Prototype001Parameters.for_instrument("seven_string_guitar"),
        body_bridge=FloydRoseSpec(string_count=7),
    )
    body = seven.build().body
    plan = plan_body_machining(body, MachiningParameters())
    (top,) = [setup for setup in plan.setups if setup.name == "Body_top"]
    bridge = [note for note in top.notes if note.startswith("Bridge: ")]
    assert any("7-String Routing sheet" in note for note in bridge)
    assert any("block_pocket_depth to 28.19" in note for note in bridge)
    # Set, the deeper pocket is cut under the spring cover.
    pocket = replace(
        seven, body_bridge=FloydRoseSpec(string_count=7, block_pocket_depth=28.19)
    ).build()
    plan = plan_body_machining(pocket.body, MachiningParameters())
    (back,) = [setup for setup in plan.setups if setup.name == "Body_back"]
    assert any("block clearance pocket" in path.name for path in back.toolpaths)

"""Tests for the Fender vintage six-screw tremolo, set flat on the top."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.geometry.body import VintageTremoloSpec
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.controls import rear_cover
from cncguitarwizard.webapp import load_design, parameter_schema, style_design

SCALE = 647.7
SCREWS = SCALE - 6.35
"""StewMac: the pivot screws 25-1/4 in from the nut on a 25-1/2 in scale."""


def test_the_routes_follow_stewmac_and_the_strat_drawing() -> None:
    hardware = VintageTremoloSpec().hardware(SCALE, 44.45)

    # Six Ø 3 pilots, 2-7/32 in from the outer one to the other.
    screws = [hole for hole in hardware.holes if hole.name.startswith("Bridge screw")]
    assert len(screws) == 6
    assert all(hole.center_x == pytest.approx(SCREWS) for hole in screws)
    ys = sorted(hole.center_y for hole in screws)
    assert ys[-1] - ys[0] == pytest.approx(2.21875 * 25.4, abs=0.01)
    assert {(hole.diameter, hole.depth) for hole in screws} == {(3.0, 22.0)}
    # Nothing routed for the plate: it sits on the top, a footprint kept
    # clear, from 4 mm ahead of the screws.
    assert hardware.top_cavities == ()
    xs = [p.x for p in hardware.footprint]
    assert (min(xs), max(xs)) == (pytest.approx(SCREWS - 4.0), SCREWS + 38.0)
    assert max(p.y for p in hardware.footprint) == 36.5
    # The block route: 1/2 in behind the screws, 11/16 in long, 3-1/8 in
    # wide and 3/16 in toward the arm (+Y), 1-1/8 in deep.
    (block,) = hardware.through_cavities
    assert block.name == "Vintage tremolo block route"
    assert (block.min_x, block.max_x) == (
        pytest.approx(SCREWS + 12.7),
        pytest.approx(SCREWS + 30.15),
    )
    assert (block.min_y, block.max_y) == (pytest.approx(-34.925), 44.45)
    assert block.depth == 28.575
    # From the back: the 5/8 in spring cavity ahead of the block and the
    # 1 in block cavity, one outline, the block cavity on to 3/16 in under
    # the top.
    (rear,) = hardware.rear_cavities
    assert rear.cavity.name == "Vintage tremolo spring cavity"
    assert rear.cavity.depth == 15.875
    assert rear.cavity.min_x == pytest.approx(SCREWS + 12.7 - 99.314)
    assert rear.cavity.max_x == pytest.approx(SCREWS + 38.1)
    spring = [p for p in rear.cavity.outline if p.x < SCREWS]
    assert max(abs(p.y) for p in spring) == pytest.approx(28.194)
    (pocket,) = rear.steps
    assert pocket.name == "Vintage tremolo block cavity"
    assert pocket.depth == pytest.approx(44.45 - 4.7625)
    assert (pocket.min_y, pocket.max_y) == (pytest.approx(-34.925), 44.45)
    # The cover is a stock one on the back: nothing routed for it.
    assert rear.cover_on_back
    assert rear.routes == rear.pockets
    assert all(
        point_in_polygon(p, rear.cover_recess.outline) for p in rear.cavity.outline
    )
    # The claw's screws 7/16 in up from the back, into the nut-ward wall.
    claw = hardware.side_holes
    assert [hole.start.x for hole in claw] == [rear.cavity.min_x] * 2
    assert {hole.start.z for hole in claw} == {11.1125}
    assert sorted(hole.start.y for hole in claw) == [-17.0, 17.0]


def test_the_block_route_follows_the_arm_to_the_other_side() -> None:
    lefty = VintageTremoloSpec(treble_side="-y").hardware(SCALE, 44.45)
    (block,) = lefty.through_cavities
    assert (block.min_y, block.max_y) == (-44.45, pytest.approx(34.925))
    (pocket,) = lefty.rear_cavities[0].steps
    assert (pocket.min_y, pocket.max_y) == (-44.45, pytest.approx(34.925))
    # The screws and the plate stay centred.
    right = VintageTremoloSpec().hardware(SCALE, 44.45)
    assert lefty.holes == right.holes and lefty.footprint == right.footprint


@pytest.mark.parametrize("thickness", [44.0, 44.45, 50.8])
def test_a_thicker_body_deepens_the_spring_cavity(thickness: float) -> None:
    # The block hangs from the top: past the 1.75 in body its springs are
    # that much further from the back.
    hardware = VintageTremoloSpec().hardware(SCALE, thickness)
    (rear,) = hardware.rear_cavities
    extra = max(0.0, thickness - 44.45)
    assert rear.cavity.depth == pytest.approx(15.875 + extra)
    assert rear.steps[0].depth == pytest.approx(thickness - 4.7625)
    assert [hole.start.z for hole in hardware.side_holes] == [
        pytest.approx(11.1125 + extra)
    ] * 2


@pytest.mark.parametrize(
    ("changes", "thickness", "match"),
    [
        ({"screw_spacing": 15.0}, 44.0, "on its plate"),
        ({"block_route_lead": 1.0}, 44.0, "start behind its screws"),
        ({"block_route_length": 30.0}, 44.0, "at least as long"),
        ({"block_route_width": 60.0}, 44.0, "wider than the spring cavity"),
        ({}, 28.0, "pass through the body"),
        ({"block_cavity_top_wood": 30.0}, 44.0, "not open into the block"),
        ({}, 36.0, "break into the spring cavity"),
        ({"claw_screw_spacing": 60.0}, 44.0, "inside the spring cavity"),
        ({"claw_screw_height": 16.0}, 44.0, "spring cavity's wall"),
        ({"plate_width": -1.0}, 44.0, "plate_width must be finite"),
    ],
)
def test_a_route_that_cannot_be_laid_out_is_refused(
    changes: dict[str, float], thickness: float, match: str
) -> None:
    with pytest.raises(BodyGeometryError, match=match):
        VintageTremoloSpec(**changes).hardware(SCALE, thickness)  # type: ignore[arg-type]


def strat(**changes: object) -> Prototype001Parameters:
    parameters = load_design(style_design("electric_guitar", "stratocaster")).parameters
    return replace(parameters, **changes)  # type: ignore[arg-type]


def test_the_stratocaster_style_carries_it() -> None:
    parameters = strat()
    assert parameters.body_bridge == VintageTremoloSpec()
    geometry = parameters.build()
    body = geometry.body
    # Its bridge pickup stays where the drawing has it, clear of the plate.
    pickup = body.bridge_pickup
    assert pickup is not None
    front = min(p.x for p in body.bridge_footprint)
    assert front - max(p.x for p in pickup.outline) >= 3.0
    # No cover is cut for it, and none of it is a recess.
    assert not any("tremolo" in cover.name for cover in geometry.covers)
    plan = plan_body_machining(body, MachiningParameters())
    names = {path.name for setup in plan.setups for path in setup.toolpaths}
    assert {"Vintage tremolo spring cavity", "Vintage tremolo block cavity"} <= names
    assert "Vintage tremolo cover" not in names
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert "# vintage tremolo spring cavity cut" in source
    assert "vintage tremolo spring cavity cover recess cut" not in source


def test_a_left_handed_strat_moves_the_block_route_with_the_arm() -> None:
    right = strat().build().body
    left = strat(handedness="left").build().body

    def block(body: object) -> tuple[float, float]:
        (route,) = body.through_cavities  # type: ignore[attr-defined]
        return route.min_y, route.max_y

    assert block(left) == pytest.approx((-block(right)[1], -block(right)[0]))


def test_a_cover_on_the_back_is_neither_cut_nor_spotted() -> None:
    (rear,) = VintageTremoloSpec().hardware(SCALE, 44.45).rear_cavities
    features = rear_cover(rear, 6)
    assert features.covers == () and features.back_marks == ()


def test_the_form_offers_it() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    variant = fields["body_bridge"]["variants"]["vintage_tremolo"]
    assert variant["label"] == (
        "Fender vintage tremolo (6 screws, springs from the back)"
    )
    assert (variant["min_strings"], variant["max_strings"]) == (6, 6)
    assert "only dives" in variant["note"]
    basic = {field["name"] for field in variant["fields"] if not field["advanced"]}
    assert basic == {"treble_side", "screw_offset", "screw_spacing", "plate_width"}

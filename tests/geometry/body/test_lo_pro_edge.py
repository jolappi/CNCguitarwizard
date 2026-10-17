"""Tests for the Ibanez Lo-Pro Edge with a JEM777's Lion's Claw route."""

import ast
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.geometry.body import LoProEdgeSpec, ScoopedGrooves
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import parameter_schema

SCALE = 647.7
STUDS = SCALE - 11.9


def test_the_route_follows_the_jem777_blueprint() -> None:
    """Dimensions read off a JEM777 body blueprint (mm), from the studs."""
    hardware = LoProEdgeSpec().hardware(SCALE, 44.0)

    studs = hardware.mounting.pivot_holes
    assert [(p.x, p.y) for p in studs] == [
        (pytest.approx(STUDS), -37.0),
        (pytest.approx(STUDS), 37.0),
    ]
    assert hardware.mounting.pivot_hole_diameter == 11.0
    # 32 deep below the 6 mm shelf.
    assert hardware.mounting.pivot_hole_depth == 38.0
    recess, floor, claw = hardware.top_cavities
    # 95 wide, 7 ahead of the studs, 6 deep, to 67 behind them.
    assert recess.name == "Lo-Pro Edge recess" and recess.depth == 6.0
    assert recess.min_x == pytest.approx(STUDS - 7.0)
    assert recess.max_x == pytest.approx(STUDS + 67.0)
    assert (recess.min_y, recess.max_y) == (pytest.approx(-47.5), 47.5)
    # Deepened to 12 from 11 behind the studs; full width to 36 behind
    # them, then 74 wide to 67 behind them, past which the grooves lift
    # out.
    assert floor.name == "Lo-Pro Edge fine-tuner recess" and floor.depth == 12.0
    assert floor.min_x == pytest.approx(STUDS + 11.0)
    assert max(p.y for p in floor.outline if p.x < STUDS + 34.0) == 47.5
    # (Its walls between the step's R6 and the back's R3.)
    walls = [p for p in floor.outline if STUDS + 41.0 < p.x < STUDS + 65.0]
    assert max(abs(p.y) for p in walls) == pytest.approx(37.0)
    # The Lion's Claw: six 10.8 grooves, 16 deep, from halfway along the
    # block route; lifting out in a 16 mm quarter circle from 67 behind
    # the studs (less the blueprint's rounding), each ending in a half
    # circle on the top 88 behind them.
    assert isinstance(claw, ScoopedGrooves)
    assert claw.name == "Lo-Pro Edge Lion's Claw" and claw.depth == 16.0
    assert claw.min_x == pytest.approx(STUDS + 23.5)
    assert claw.scoop_start == pytest.approx(STUDS + 66.6)
    assert claw.max_x == pytest.approx(STUDS + 88.0)
    assert (claw.min_y, claw.max_y) == (pytest.approx(-32.4), pytest.approx(32.4))
    tips = sorted(p.y for p in claw.outline if p.x == pytest.approx(claw.max_x))
    assert tips == pytest.approx([-27.0, -16.2, -5.4, 5.4, 16.2, 27.0])
    # Between two grooves' ends a point of wood, a groove's radius back.
    cusps = [p for p in claw.outline if p.x == pytest.approx(STUDS + 88.0 - 5.4)]
    assert sorted(p.y for p in cusps) == pytest.approx(
        [-32.4, -21.6, -10.8, 0.0, 10.8, 21.6, 32.4]
    )

    # Full depth under the fine tuners; where they lift out, a groove is
    # deepest along its middle and a ridge rises between two, to the top
    # at their ends.
    def depth(x: float, y: float) -> float:
        return claw.floor_depth(Point2D(STUDS + x, y))

    assert depth(50.0, -27.0) == depth(50.0, -21.6) == 16.0
    assert depth(80.0, -27.0) == pytest.approx(13.86, abs=0.01)
    assert depth(80.0, -21.6) == pytest.approx(8.74, abs=0.01)
    assert depth(82.6, -21.6) == pytest.approx(0.0, abs=0.01)
    assert depth(82.6, -27.0) == pytest.approx(11.98, abs=0.01)
    assert depth(88.0, -27.0) == 0.0 and depth(20.0, 0.0) == 0.0
    # The block route: 25 long, 30 deep, 33 to the bass and 45 to the
    # treble (+Y) side, through into the spring cavity.
    (block,) = hardware.through_cavities
    assert block.name == "Lo-Pro Edge block route" and block.depth == 30.0
    assert block.min_x == pytest.approx(STUDS + 11.0)
    assert block.max_x == pytest.approx(STUDS + 36.0)
    assert (block.min_y, block.max_y) == (pytest.approx(-33.0), pytest.approx(45.0))
    (spring,) = hardware.rear_cavities
    assert spring.cavity.name == "Lo-Pro Edge spring cavity"
    assert spring.cavity.depth == 21.0 and spring.cover_recess.depth == 3.0
    assert spring.cavity.max_x == pytest.approx(STUDS + 43.5)
    assert spring.steps == ()
    assert block.depth + spring.cavity.depth > 44.0
    assert [hole.name for hole in hardware.side_holes] == [
        "Trem claw screw 1 hole",
        "Trem claw screw 2 hole",
    ]


def test_the_block_route_follows_the_arm_to_the_other_side() -> None:
    lefty = LoProEdgeSpec(treble_side="-y").hardware(SCALE, 44.0)
    (block,) = lefty.through_cavities
    assert (block.min_y, block.max_y) == (pytest.approx(-45.0), pytest.approx(33.0))
    # The recess and the grooves are symmetric.
    assert lefty.top_cavities == LoProEdgeSpec().hardware(SCALE, 44.0).top_cavities


@pytest.mark.parametrize("thickness", [44.0, 44.45, 50.8])
def test_a_thicker_body_deepens_the_spring_cavity(thickness: float) -> None:
    # The block hangs a fixed depth below the top: past the 1.75 in body
    # the depths are set for, the spring cavity reaches deeper by as much.
    hardware = LoProEdgeSpec().hardware(SCALE, thickness)
    (rear,) = hardware.rear_cavities
    assert rear.cavity.depth == pytest.approx(21.0 + max(0.0, thickness - 44.45))
    (block,) = hardware.through_cavities
    assert block.depth + rear.cavity.depth - thickness >= 6.5


@pytest.mark.parametrize(
    ("changes", "thickness", "match"),
    [
        ({"lions_claw_groove_width": 13.0}, 44.0, "fit the fine-tuner"),
        ({"block_route_width": 66.0}, 44.0, "no wider than the block route"),
        ({"lions_claw_depth": 11.0}, 44.0, "deeper than the fine-tuner"),
        ({"lions_claw_length": 10.0}, 44.0, "past the recess's end"),
        ({"recess_length": 50.0, "lions_claw_length": 8.0}, 44.0, "too short"),
        ({"block_route_length": 30.0}, 44.0, "full-width part"),
        ({"pivot_stud_spacing": 90.0}, 44.0, "inside the recess width"),
        ({}, 36.0, "too thin for the Lion's Claw"),
        ({"block_route_depth": 20.0}, 44.0, "too thick"),
    ],
)
def test_a_route_that_cannot_be_laid_out_is_refused(
    changes: dict[str, float], thickness: float, match: str
) -> None:
    with pytest.raises(BodyGeometryError, match=match):
        LoProEdgeSpec(**changes).hardware(SCALE, thickness)  # type: ignore[arg-type]


def guitar(**changes: object) -> Prototype001Parameters:
    return replace(
        Prototype001Parameters.for_instrument("electric_guitar"),
        body_bridge=LoProEdgeSpec(),
        **changes,  # type: ignore[arg-type]
    )


def test_a_guitar_carries_it_with_a_locking_nut() -> None:
    parameters = guitar()
    body = parameters.build().body
    names = [cavity.name for cavity in body.top_cavities]
    recess, floor, claw = (
        body.top_cavities[names.index(name)]
        for name in (
            "Lo-Pro Edge recess",
            "Lo-Pro Edge fine-tuner recess",
            "Lo-Pro Edge Lion's Claw",
        )
    )
    # The floor a step inside the recess; the grooves open out of both,
    # deeper than either wherever they overlap.
    assert body.is_step(floor, recess)
    assert body.opens_out_of(claw, floor) and body.opens_out_of(claw, recess)
    assert not body.opens_out_of(floor, claw)
    assert parameters.locking_nut_kind == "r2"


def test_a_left_handed_guitar_moves_the_block_route_with_the_arm() -> None:
    right = guitar().build().body
    left = guitar(handedness="left").build().body

    def block(body: object) -> tuple[float, float]:
        (route,) = [
            cavity
            for cavity in body.through_cavities  # type: ignore[attr-defined]
            if cavity.name == "Lo-Pro Edge block route"
        ]
        return route.min_y, route.max_y

    assert block(left) == pytest.approx((-block(right)[1], -block(right)[0]))


def test_it_is_made_for_six_strings() -> None:
    seven = replace(
        Prototype001Parameters.for_instrument("seven_string_guitar"),
        body_bridge=LoProEdgeSpec(),
    )
    with pytest.raises(BodyGeometryError, match="made for 6 strings"):
        seven.build()


def test_the_lions_claw_is_pocketed_then_scooped_with_the_ball_nose() -> None:
    geometry = guitar().build()
    (claw,) = [
        cavity
        for cavity in geometry.body.top_cavities
        if cavity.name == "Lo-Pro Edge Lion's Claw"
    ]
    assert isinstance(claw, ScoopedGrooves)
    plan = plan_body_machining(geometry.body, MachiningParameters())
    radius = MachiningParameters().tool_radius

    def cuts(setup_name: str, path_name: str) -> list[tuple[float, float]]:
        (setup,) = [setup for setup in plan.setups if setup.name == setup_name]
        (path,) = [path for path in setup.toolpaths if path.name == path_name]
        return [
            (move.x + plan.origin_x, move.z) for move in path.moves if not move.rapid
        ]

    # Its full-depth part with the end mill, to where the bit starts
    # lifting out and a groove's radius on (the round ends there).
    flat = cuts("Body_top", "Lo-Pro Edge Lion's Claw")
    assert min(z for _, z in flat) == pytest.approx(-16.0)
    assert max(x for x, _ in flat) == pytest.approx(
        claw.scoop_start + claw.radius - radius, abs=0.05
    )
    # The scoops with the ball nose, from where the bit starts lifting
    # out to the grooves' round ends on the top.
    for name in ("roughing", "finishing"):
        scooped = cuts("Body_top_edges", f"Lo-Pro Edge Lion's Claw {name}")
        assert min(z for _, z in scooped) == pytest.approx(-16.0, abs=0.05)
        assert min(x for x, _ in scooped) < claw.scoop_start
        assert max(x for x, z in scooped if z < -0.5) > claw.max_x - 2.0 * radius
    (edges,) = [setup for setup in plan.setups if setup.name == "Body_top_edges"]
    assert "Lion's Claw's scoops" in edges.description


def test_the_model_lofts_each_groove_along_its_bit() -> None:
    source = FreeCADScriptExporter().render_prototype001(guitar().build())
    ast.parse(source)
    assert "for groove_centre in [-27.0, -16.2, -5.4, 5.4, 16.2, 27.0]" in source
    # Each reaching a hair into the next (two that only touched shared a
    # face, and FreeCAD left every other groove uncut), all in one boolean.
    assert "across = 5.41 * math.sin(angle)" in source
    assert "body_shape.cut(groove_lofts)" in source


def test_the_form_offers_it() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    variant = fields["body_bridge"]["variants"]["lo_pro_edge"]
    assert variant["label"] == (
        "Ibanez Lo-Pro Edge + Lion's Claw (recessed, as on a JEM777)"
    )
    assert (variant["min_strings"], variant["max_strings"]) == (6, 6)
    basic = {field["name"] for field in variant["fields"] if not field["advanced"]}
    assert basic == {"treble_side", "pivot_offset"}
    help_text = {field["name"]: field.get("help", "") for field in variant["fields"]}
    assert "rounded end" in help_text["lions_claw_groove_width"]

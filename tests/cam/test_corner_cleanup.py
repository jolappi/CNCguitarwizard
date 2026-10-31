"""Tests for the pockets' corners cut with the small end mill
(``corner_cleanup``): the main tool leaves its own radius in each."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.cam import (
    MachiningParameters,
    plan_body_machining,
    plan_feature_machining,
)
from cncguitarwizard.cam.body import BodyMachiningPlan
from cncguitarwizard.cam.exceptions import ToolpathError
from cncguitarwizard.cam.operations import clean_corners
from cncguitarwizard.cam.planar import disc_fits
from cncguitarwizard.cam.toolpath import Toolpath
from cncguitarwizard.geometry.body import BodySolid, TracedCavity
from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.styles import STYLES
from cncguitarwizard.webapp import parameter_schema

WIDE = MachiningParameters(tool_diameter=12.0)
"""A 12 mm end mill: it leaves 6 mm in every inside corner."""

SQUARE = (
    Point2D(0.0, 0.0),
    Point2D(40.0, 0.0),
    Point2D(40.0, 30.0),
    Point2D(0.0, 30.0),
)


def _style(name: str) -> Prototype001Parameters:
    style = STYLES[name]
    return Prototype001Parameters(**style.prototype_values(style.instruments[0]))


def _corner_paths(plan: BodyMachiningPlan) -> list[str]:
    return [
        path.name
        for setup in plan.setups
        for path in setup.toolpaths
        if path.name.endswith(" corners")
    ]


def _path(paths: tuple[Toolpath, ...], name: str) -> Toolpath:
    return next(path for path in paths if path.name == name)


def _cuts(path: Toolpath) -> list[Point2D]:
    return [Point2D(move.x, move.y) for move in path.moves if not move.rapid]


def _nearest(path: Toolpath, corner: Point2D, z: float) -> float:
    """Return how near ``path``'s centre comes to ``corner`` at depth ``z``."""
    return min(
        math.hypot(move.x - corner.x, move.y - corner.y)
        for move in path.moves
        if not move.rapid and move.z == pytest.approx(z)
    )


@pytest.fixture(scope="module")
def body() -> BodySolid:
    return Prototype001Parameters().build().body


def test_a_square_pocket_s_corners_are_cut_down_to_the_small_radius() -> None:
    small = WIDE.small_cutter
    path = clean_corners("Square corners", SQUARE, 10.0, WIDE, small)

    assert path is not None
    for corner in SQUARE:
        # 1.5 mm off both walls, where the 12 mm end mill stays 6 mm off.
        assert _nearest(path, corner, -10.0) == pytest.approx(1.5 * math.sqrt(2.0))
    assert all(disc_fits(point, SQUARE, 1.5 - 1e-6) for point in _cuts(path))
    assert path.deepest_z() == pytest.approx(-10.0)
    # Only round the corners (the 12 mm end mill's arc meets the walls
    # 6 mm from each), not along the walls between them.
    assert all(
        min(math.hypot(point.x - c.x, point.y - c.y) for c in SQUARE) < 8.0
        for point in _cuts(path)
    )


def test_it_never_lifts_in_a_corner() -> None:
    path = clean_corners("Square corners", SQUARE, 10.0, WIDE, WIDE.small_cutter)

    assert path is not None
    # Down once at each corner's clean end, then back and forth, a pass
    # deeper each way.
    descents = [
        index
        for index, move in enumerate(path.moves)
        if move.rapid and 0.0 < move.z < WIDE.safe_height
    ]
    assert len(descents) == 4
    passes = math.ceil(10.0 / WIDE.small_cutter.step_down)
    plunges = [move for move in path.moves if not move.rapid and move.feed == 150.0]
    assert len(plunges) == 4 * passes


def test_nothing_to_cut_without_a_corner() -> None:
    small = WIDE.small_cutter
    circle = tuple(
        Point2D(30.0 * math.cos(angle), 30.0 * math.sin(angle))
        for angle in (2.0 * math.pi * k / 120 for k in range(120))
    )

    assert clean_corners("Circle corners", circle, 10.0, WIDE, small) is None
    # Nor when the small end mill is no smaller than the pocket's.
    assert clean_corners("Square corners", SQUARE, 10.0, small, small) is None


def test_a_floor_not_level_is_never_cut_below() -> None:
    def floor(point: Point2D) -> float:
        return 10.0 + point.x / 10.0

    path = clean_corners(
        "Square corners", SQUARE, 10.0, WIDE, WIDE.small_cutter, floor=floor
    )

    assert path is not None
    for move in path.moves:
        assert move.z >= -floor(Point2D(move.x, move.y)) - 1e-9
    # The corners at the deep end go deeper than the shallow end's.
    assert path.deepest_z() < -13.0


def test_corner_cleanup_is_off_by_default(body: BodySolid) -> None:
    assert MachiningParameters().corner_cleanup == "none"
    assert _corner_paths(plan_body_machining(body, WIDE)) == []


def test_the_neck_pocket_s_corners_go_to_the_small_end_mill(body: BodySolid) -> None:
    plan = plan_body_machining(body, replace(WIDE, corner_cleanup="neck_pocket"))

    assert _corner_paths(plan) == ["Neck pocket corners"]
    small = plan.top_small_holes
    assert small is not None
    names = [path.name for path in small.toolpaths]
    # After the narrow routes, before the holes.
    assert names[:2] == ["Truss rod access", "Neck pocket corners"]
    assert small.description == (
        "Body top face - narrow routes, pocket corners and holes for the 3 mm end mill"
    )
    assert (
        "The 12 mm end mill leaves its radius in the corners; Body_top_small_holes "
        "cuts them down to the 3 mm one's: Neck pocket corners." in plan.top.notes
    )
    pocket = body.neck_pocket
    assert pocket is not None
    corners = _path(small.toolpaths, "Neck pocket corners")
    assert corners.deepest_z() == pytest.approx(-pocket.depth)
    model = [
        Point2D(point.x + plan.origin_x, point.y + plan.origin_y)
        for point in _cuts(corners)
    ]
    assert all(disc_fits(point, pocket.outline, 1.5 - 1e-6) for point in model)
    # The square heel's two corners, 1.5 mm off both walls.
    for y in (-28.15, 28.15):
        corner = Point2D(461.2 - plan.origin_x, y - plan.origin_y)
        assert _nearest(corners, corner, -pocket.depth) < 2.2


def test_the_neck_pocket_alone_leaves_the_pickups_as_they_are(
    body: BodySolid,
) -> None:
    alone = plan_body_machining(body, replace(WIDE, corner_cleanup="neck_pocket"))
    every = plan_body_machining(body, replace(WIDE, corner_cleanup="all"))

    assert "Neck pickup route corners" not in _corner_paths(alone)
    assert {
        "Neck pocket corners",
        "Neck pickup route corners",
        "Bridge pickup route corners",
        "Control cavity corners",
    } <= set(_corner_paths(every))
    back = every.back_small_holes
    assert back is not None
    assert "Control cavity corners" in [path.name for path in back.toolpaths]
    assert back.description.startswith("Body back face - pocket corners")
    assert any("Control cavity corners" in note for note in every.back.notes)


def test_an_angled_neck_s_corners_stay_above_its_tilted_floor() -> None:
    body = _style("les_paul").build().body
    pocket = body.neck_pocket
    assert isinstance(pocket, TracedCavity) and pocket.floor_slope > 0.0
    plan = plan_body_machining(body, replace(WIDE, corner_cleanup="neck_pocket"))

    assert plan.top_small_holes is not None
    corners = _path(plan.top_small_holes.toolpaths, "Neck pocket corners")
    for move in corners.moves:
        # Where the 1.5 mm end mill's shallowest edge is, the slope's depth.
        x = move.x + plan.origin_x + 1.5
        floor = pocket.depth + max(0.0, pocket.max_x - x) * pocket.floor_slope
        assert move.z >= -floor - 1e-9
    # The corners at the deep end, toward the neck, follow the tilt down.
    assert corners.deepest_z() < -pocket.depth - 1.0


def test_a_core_s_corners_are_cut_before_the_top_goes_on() -> None:
    les_paul = replace(_style("les_paul"), body_chambers=True)
    plan = plan_body_machining(
        les_paul.build().body, MachiningParameters(corner_cleanup="all")
    )

    assert plan.core_top is not None
    small = plan.core_small_routes
    assert small is not None
    assert all(path.name.endswith(" corners") for path in small.toolpaths)
    assert small.description == ("Body core top - pocket corners for the 3 mm end mill")
    assert any("glue" in note for note in small.notes)
    assert not any("glue" in note for note in plan.core_top.notes)
    assert any("Body_core_small_routes" in note for note in plan.core_top.notes)


def test_a_feature_s_corners_go_to_its_small_program() -> None:
    geometry = Prototype001Parameters().build()
    setups = plan_feature_machining(
        geometry.body,
        geometry.covers,
        lambda name: name.startswith("Bridge baseplate"),
        "bridge",
        MachiningParameters(corner_cleanup="all"),
    )

    small = {setup.name: setup for setup in setups}["Feature_bridge_top_small_holes"]
    assert [path.name for path in small.toolpaths] == [
        "Bridge baseplate cutout corners"
    ]
    assert small.description.endswith("top face, pocket corners")
    assert "change to the small end mill" in small.notes[0]


def test_an_unknown_corner_cleanup_is_refused() -> None:
    with pytest.raises(ToolpathError, match="corner_cleanup"):
        MachiningParameters(corner_cleanup="some")  # type: ignore[arg-type]


def test_corner_cleanup_is_a_basic_machining_choice() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["machining"]
        for field in group["fields"]
    }

    field = fields["corner_cleanup"]
    assert field["default"] == "none"
    assert field["options"] == ["none", "neck_pocket", "all"]
    assert set(field["labels"]) == {"none", "neck_pocket", "all"}
    assert not field["advanced"]

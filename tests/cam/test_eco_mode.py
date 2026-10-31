"""Tests for eco mode: programs built to cut as little air as they can."""

import math
from dataclasses import replace
from functools import cache

import pytest

from cncguitarwizard.cam import (
    FretboardMachiningParameters,
    GRBLWriter,
    MachiningParameters,
    NeckMachiningParameters,
    drill,
    plan_body_machining,
    plan_neck_machining,
    pocket,
)
from cncguitarwizard.cam.gcode import ECO_MODE_NOTE, Setup
from cncguitarwizard.cam.neck import NeckMachiningPlan
from cncguitarwizard.cam.parameters import ECO_LINK_DIAMETERS
from cncguitarwizard.cam.toolpath import Move, Toolpath
from cncguitarwizard.geometry.body import TuneOMaticSpec
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.webapp import parameter_schema

PLAIN = MachiningParameters()
ECO = MachiningParameters(eco_mode=True)

# A U: its two prongs' rows split in two, the tool lifted over the gap
# between them.
U_SHAPE = (
    Point2D(0.0, 0.0),
    Point2D(60.0, 0.0),
    Point2D(60.0, 40.0),
    Point2D(40.0, 40.0),
    Point2D(40.0, 15.0),
    Point2D(20.0, 15.0),
    Point2D(20.0, 40.0),
    Point2D(0.0, 40.0),
)


def fast_descents(path: Toolpath) -> list[tuple[Move, float | None]]:
    """Return every rapid straight down, each with the lowest Z the path fed
    to at its X/Y before it (``None`` where it never fed there)."""
    lowest: dict[tuple[float, float], float] = {}
    found = []
    previous: Move | None = None
    for move in path.moves:
        here = (move.x, move.y)
        if (
            previous is not None
            and move.rapid
            and (previous.x, previous.y) == here
            and move.z < previous.z
        ):
            found.append((move, lowest.get(here)))
        if not move.rapid:
            lowest[here] = min(move.z, lowest.get(here, math.inf))
        previous = move
    return found


def plunged(path: Toolpath) -> float:
    """Return how far a path feeds straight down, in mm."""
    moves = path.moves
    return sum(
        a.z - b.z
        for a, b in zip(moves, moves[1:], strict=False)
        if not b.rapid and (a.x, a.y) == (b.x, b.y) and b.z < a.z
    )


def fed_points(path: Toolpath) -> dict[float, set[tuple[float, float]]]:
    """Return the X/Y points each depth's feed moves reach."""
    points: dict[float, set[tuple[float, float]]] = {}
    for move in path.moves:
        if not move.rapid and move.z < 0.0:
            points.setdefault(round(move.z, 6), set()).add(
                (round(move.x, 6), round(move.y, 6))
            )
    return points


def test_eco_mode_is_off_by_default() -> None:
    assert not PLAIN.eco_mode
    assert PLAIN.eco_link_distance == 0.0
    assert ECO.eco_link_distance == ECO_LINK_DIAMETERS * ECO.tool_diameter


def test_a_pockets_passes_come_down_fast_over_the_floor_they_cut() -> None:
    plain = pocket("U", U_SHAPE, 9.0, PLAIN)
    eco = pocket("U", U_SHAPE, 9.0, ECO)

    # Plain, every plunge starts over the stock top; in eco mode the tool
    # comes down fast to 1 mm over the floor its own last pass cut there,
    # never lower, and never below the stock top over wood it has not cut.
    descents = [(move, floor) for move, floor in fast_descents(eco) if move.z < 0.0]
    assert descents
    for move, floor in descents:
        assert floor is not None
        assert move.z == pytest.approx(floor + 1.0)
    assert all(move.z >= 0.0 for move, _ in fast_descents(plain))
    assert plunged(eco) < 0.6 * plunged(plain)
    # The same wood cut: every pass reaches the same points.
    assert fed_points(eco) == fed_points(plain)


def test_a_pockets_passes_and_wall_start_where_the_last_cut_ended() -> None:
    # A long slot, the truss rod's: plain, the tool feeds back down its
    # length at depth to start the wall, and again to start the next pass.
    slot = (
        Point2D(0.0, 0.0),
        Point2D(300.0, 0.0),
        Point2D(300.0, 10.0),
        Point2D(0.0, 10.0),
    )
    plain = pocket("Slot", slot, 9.0, PLAIN)
    eco = pocket("Slot", slot, 9.0, ECO)

    def longest_link(path: Toolpath) -> float:
        """Return the longest feed at depth across the slot's rows."""
        moves = path.moves
        return max(
            math.dist((a.x, a.y), (b.x, b.y))
            for a, b in zip(moves, moves[1:], strict=False)
            if not b.rapid and b.z < 0.0 and abs(b.y - a.y) > 1e-6
        )

    assert longest_link(plain) > 250.0
    assert longest_link(eco) < 10.0
    assert eco.cutting_length() < plain.cutting_length() - 3 * 250.0
    assert fed_points(eco) == fed_points(plain)


def test_a_holes_pecks_come_back_down_fast_over_the_last_one() -> None:
    plain = drill("Hole", Point2D(0.0, 0.0), 6.0, 15.0, PLAIN)
    eco = drill("Hole", Point2D(0.0, 0.0), 6.0, 15.0, ECO)

    # Five 3 mm pecks: plain, each from the top (4 + 6 + 9 + 12 + 15 mm
    # fed down); in eco mode each from 1 mm over the last one's floor.
    assert plunged(plain) == pytest.approx(46.0)
    assert plunged(eco) == pytest.approx(5 * 4.0)
    for move, floor in fast_descents(eco):
        if move.z < 0.0:
            assert floor is not None and move.z == pytest.approx(floor + 1.0)
    assert eco.deepest_z() == pytest.approx(-15.0)


def test_a_stepped_tops_bands_come_down_fast_over_the_floor_they_cut() -> None:
    stepped = replace(
        Prototype001Parameters(),
        body_shape=YOUR_DESIGN_TEMPLATES["stratocaster"][1],
        body_stepped_top=True,
        body_top_step_insets=(8.0, 18.0),
    )
    body = stepped.build().body
    # A 1 mm step-down: each 1.5 mm band in two passes.
    shallow = replace(PLAIN, step_down=1.0)
    plain = plan_body_machining(body, shallow).top_steps
    eco = plan_body_machining(body, replace(shallow, eco_mode=True)).top_steps
    assert plain is not None and eco is not None

    descents = [
        (move, floor)
        for band in eco.toolpaths
        for move, floor in fast_descents(band)
        if move.z < 0.0
    ]
    assert descents
    for move, floor in descents:
        assert floor is not None and move.z == pytest.approx(floor + 1.0)
    for plain_band, eco_band in zip(plain.toolpaths, eco.toolpaths, strict=True):
        assert plunged(eco_band) <= plunged(plain_band)
        assert fed_points(eco_band) == fed_points(plain_band)
    assert sum(map(plunged, eco.toolpaths)) < sum(map(plunged, plain.toolpaths))


def test_a_program_in_eco_mode_says_so() -> None:
    path = pocket("U", U_SHAPE, 3.0, ECO)
    setup = Setup("Eco", "An eco pocket", (path,))

    assert f"({ECO_MODE_NOTE})" in GRBLWriter().render(setup, ECO).splitlines()
    assert ECO_MODE_NOTE not in GRBLWriter().render(setup, PLAIN)


def test_eco_mode_reaches_the_necks_and_the_fretboards_cutters() -> None:
    neck = NeckMachiningParameters().with_form_settings(ECO)
    fretboard = FretboardMachiningParameters().with_form_settings(ECO)

    assert neck.flat.eco_mode and neck.ball.eco_mode
    assert fretboard.flat.eco_mode and fretboard.ball.eco_mode
    assert fretboard.slot.eco_mode and fretboard.inlay.eco_mode
    assert not FretboardMachiningParameters().with_form_settings(PLAIN).inlay.eco_mode


@cache
def neck_plan(eco: bool, back_cut: str = "rough_and_finish") -> NeckMachiningPlan:
    """Return Prototype001's neck plan, in eco mode or not."""
    machining = ECO if eco else PLAIN
    parameters = replace(
        NeckMachiningParameters().with_form_settings(machining), back_cut=back_cut
    )
    return plan_neck_machining(Prototype001Parameters().build(), parameters)


def test_the_necks_back_is_finished_only_where_the_end_mill_left_wood() -> None:
    plain = neck_plan(False).back_finish
    eco = neck_plan(True).back_finish
    assert plain is not None and eco is not None
    plain_path, eco_path = plain.toolpaths[0], eco.toolpaths[0]

    # The waste beside the neck, cut flat to the skin by the end mill, and
    # the flats of the back are left as it cut them; the runs taken
    # nearest first, no lifting between them.
    assert eco_path.cutting_length() < 0.8 * plain_path.cutting_length()
    assert eco_path.rapid_length() < plain_path.rapid_length() / 2.0
    assert eco.estimated_minutes(PLAIN) < plain.estimated_minutes(PLAIN) - 10.0
    assert any(note.startswith("Eco mode:") for note in eco.notes)
    # Never deeper than the plain finish anywhere it cuts.
    assert eco_path.deepest_z() == pytest.approx(plain_path.deepest_z())


def test_the_necks_back_in_eco_mode_never_cuts_below_the_back() -> None:
    plan = neck_plan(True)
    geometry = Prototype001Parameters().build()
    finish = plan.back_finish
    assert finish is not None and finish.tool is not None
    r = finish.tool.tool_radius
    origin_x, origin_y = plan.index_pin_positions[0]
    vertices = [
        (point.x - origin_x, -(point.y - origin_y), -(plan.stock_thickness + point.z))
        for row in geometry.neck_surface.mesh.rows[::6]
        for point in row[::2]
    ]
    moves = [move for move in finish.toolpaths[0].moves if not move.rapid]
    checked = 0
    for vx, vy, vz in vertices:
        for move in moves:
            d = math.hypot(move.x - vx, move.y - vy)
            if d > r:
                continue
            checked += 1
            # 0.1 mm covers the grid sampling of the steep edge zone, as for
            # the plain finish.
            assert move.z + r >= vz + math.sqrt(r * r - d * d) - 0.1
    assert checked > 1000


def test_the_ball_nose_alone_hops_between_its_runs_in_eco_mode() -> None:
    plain = neck_plan(False, "ball").setups
    eco = neck_plan(True, "ball").setups
    (plain_back,) = [setup for setup in plain if setup.name == "Neck_back"]
    (eco_back,) = [setup for setup in eco if setup.name == "Neck_back"]

    # The heel and the flat headstock left as planed in both; in eco mode
    # the finishing runs are linked in the cut, not over the safe height.
    plain_finish, eco_finish = plain_back.toolpaths[1], eco_back.toolpaths[1]
    assert eco_finish.rapid_length() < plain_finish.rapid_length() / 2.0
    assert eco_back.estimated_minutes(PLAIN) < plain_back.estimated_minutes(PLAIN)


def test_a_carved_tops_ball_nose_runs_only_over_the_fall() -> None:
    les_paul = replace(
        Prototype001Parameters(),
        body_carved_top=True,
        body_shape=YOUR_DESIGN_TEMPLATES["les_paul"][1],
        body_bridge=TuneOMaticSpec(),
        body_thickness=50.8,
    )
    body = les_paul.build().body
    carve = body.carved_top
    assert carve is not None
    finished = replace(PLAIN, carve_finish=True)
    plain = plan_body_machining(body, finished)
    eco = plan_body_machining(body, replace(finished, eco_mode=True))
    assert plain.top_carve is not None and eco.top_carve is not None
    _, plain_finish = plain.top_carve.toolpaths
    _, eco_finish = eco.top_carve.toolpaths

    # The plateau and the rim, flat as the end mill left them, are not
    # traced again; the fall is, never below the arch.
    assert eco_finish.cutting_length() < 0.8 * plain_finish.cutting_length()
    assert any("runs only over the fall" in note for note in eco.top_carve.notes)
    outline = body.outline.points
    for move in eco_finish.moves:
        model = Point2D(move.x + eco.origin_x, move.y + eco.origin_y)
        if not move.rapid and point_in_polygon(model, outline):
            assert move.z >= -carve.drop_at(model.x, model.y) - 0.05


def test_eco_mode_is_a_basic_machining_setting() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["machining"]
        for field in group["fields"]
    }

    assert fields["eco_mode"]["default"] is False
    assert not fields["eco_mode"]["advanced"]
    assert "air" in fields["eco_mode"]["help"]

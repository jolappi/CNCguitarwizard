"""Tests for the pocket, drill, and profile operations."""

import math

import pytest

from cncguitarwizard.cam import (
    MachiningParameters,
    ToolpathError,
    depth_levels,
    drill,
    pocket,
    profile,
)
from cncguitarwizard.cam.planar import disc_fits, signed_area
from cncguitarwizard.cam.toolpath import Move
from cncguitarwizard.geometry.primitives import Point2D


def rectangle(width: float, height: float) -> tuple[Point2D, ...]:
    return (
        Point2D(0.0, 0.0),
        Point2D(width, 0.0),
        Point2D(width, height),
        Point2D(0.0, height),
    )


def cuts(moves: tuple[Move, ...]) -> list[Move]:
    return [move for move in moves if not move.rapid and move.z < 0.0]


def test_depth_levels_are_equal_and_end_on_the_floor() -> None:
    assert depth_levels(0.0, 9.0, 3.0) == pytest.approx([-3.0, -6.0, -9.0])
    assert depth_levels(0.0, 7.0, 3.0) == pytest.approx([-7 / 3, -14 / 3, -7.0])
    assert depth_levels(2.0, 5.0, 3.0) == pytest.approx([-5.0])


def test_depth_levels_reject_a_depth_above_the_start() -> None:
    with pytest.raises(ToolpathError):
        depth_levels(5.0, 5.0, 3.0)


def test_pocket_keeps_every_cut_inside_the_polygon() -> None:
    parameters = MachiningParameters()
    polygon = rectangle(40.0, 25.0)

    path = pocket("Test pocket", polygon, 10.0, parameters)

    assert path.deepest_z() == pytest.approx(-10.0)
    for move in cuts(path.moves):
        assert disc_fits(Point2D(move.x, move.y), polygon, parameters.tool_radius)


def test_pocket_reaches_the_walls_with_its_finishing_contour() -> None:
    parameters = MachiningParameters()
    polygon = rectangle(40.0, 25.0)

    path = pocket("Test pocket", polygon, 3.0, parameters)
    xs = [move.x for move in cuts(path.moves)]
    ys = [move.y for move in cuts(path.moves)]

    assert min(xs) == pytest.approx(parameters.tool_radius)
    assert max(xs) == pytest.approx(40.0 - parameters.tool_radius)
    assert min(ys) == pytest.approx(parameters.tool_radius)
    assert max(ys) == pytest.approx(25.0 - parameters.tool_radius)


def test_pocket_covers_the_floor_between_raster_rows() -> None:
    parameters = MachiningParameters(step_over=0.5)
    polygon = rectangle(40.0, 25.0)
    path = pocket("Test pocket", polygon, 3.0, parameters)
    cut_moves = cuts(path.moves)
    swept = [
        (cut_moves[index - 1], cut_moves[index])
        for index in range(1, len(cut_moves))
        if cut_moves[index - 1].z == cut_moves[index].z
    ]

    def swept_by_tool(x: float, y: float) -> bool:
        for start, end in swept:
            dx, dy = end.x - start.x, end.y - start.y
            length_sq = dx * dx + dy * dy
            t = 0.0 if length_sq == 0.0 else max(
                0.0, min(1.0, ((x - start.x) * dx + (y - start.y) * dy) / length_sq)
            )
            if math.hypot(x - (start.x + t * dx), y - (start.y + t * dy)) <= (
                parameters.tool_radius + 1e-6
            ):
                return True
        return False

    # Every floor point is swept except the inside corners, which an end
    # mill necessarily leaves rounded to its own radius.
    corners = polygon
    for x in range(1, 40):
        for y in range(1, 25):
            point = (x + 0.5, y + 0.5)
            if any(
                math.hypot(point[0] - corner.x, point[1] - corner.y)
                < parameters.tool_radius
                for corner in corners
            ):
                continue
            assert swept_by_tool(*point), point


def test_pocket_uses_the_full_step_down_count() -> None:
    parameters = MachiningParameters(step_down=3.0)
    path = pocket("Test pocket", rectangle(40.0, 25.0), 10.0, parameters)
    depths = sorted({move.z for move in cuts(path.moves)}, reverse=True)

    assert depths == pytest.approx([-2.5, -5.0, -7.5, -10.0])


def test_pocket_rejects_a_slot_narrower_than_the_tool() -> None:
    with pytest.raises(ToolpathError, match="too narrow"):
        pocket("Slot", rectangle(40.0, 5.0), 3.0, MachiningParameters())


def test_pocket_can_start_below_the_surface() -> None:
    path = pocket(
        "Deep", rectangle(40.0, 25.0), 8.0, MachiningParameters(), start_depth=2.0
    )
    depths = sorted({move.z for move in cuts(path.moves)}, reverse=True)

    assert depths == pytest.approx([-5.0, -8.0])


def test_drill_pecks_a_tool_sized_hole() -> None:
    parameters = MachiningParameters(step_down=3.0)
    path = drill("Pin", Point2D(10.0, 5.0), 6.0, 7.0, parameters)

    assert path.deepest_z() == pytest.approx(-7.0)
    assert all(move.x == 10.0 and move.y == 5.0 for move in path.moves)
    lifts = [move for move in path.moves if move.rapid and move.z == 0.0]
    assert len(lifts) == 2


def test_drill_bores_a_larger_hole_with_a_helix_after_a_centre_peck() -> None:
    parameters = MachiningParameters(step_down=3.0)
    centre = Point2D(10.0, 5.0)
    path = drill("Pot", centre, 10.0, 6.0, parameters)
    helix = [
        move
        for move in cuts(path.moves)
        if math.hypot(move.x - centre.x, move.y - centre.y) > 1e-6
    ]

    assert helix
    assert all(
        math.hypot(move.x - centre.x, move.y - centre.y) == pytest.approx(2.0)
        for move in helix
    )
    assert path.deepest_z() == pytest.approx(-6.0)
    assert helix[-1].z == pytest.approx(-6.0)


def test_drill_rejects_a_hole_smaller_than_the_tool() -> None:
    with pytest.raises(ToolpathError, match="smaller"):
        drill("Tiny", Point2D(0.0, 0.0), 4.0, 5.0, MachiningParameters())


def test_profile_runs_counter_clockwise_outside_the_polygon() -> None:
    parameters = MachiningParameters()
    polygon = rectangle(50.0, 30.0)
    path = profile("Outline", polygon, 6.0, parameters)
    loop = [
        Point2D(move.x, move.y) for move in cuts(path.moves) if move.z == -6.0
    ]

    assert signed_area(loop) > 0.0
    for point in loop:
        assert disc_fits(point, polygon, parameters.tool_radius, inside=False)
    assert min(point.x for point in loop) == pytest.approx(-parameters.tool_radius)


def test_profile_lifts_over_tabs_on_the_final_passes() -> None:
    parameters = MachiningParameters(tab_count=4, tab_height=4.0, tab_length=8.0)
    path = profile("Outline", rectangle(50.0, 30.0), 12.0, parameters, with_tabs=True)
    cut_moves = cuts(path.moves)
    first_floor = next(index for index, move in enumerate(cut_moves) if move.z == -12.0)
    final = cut_moves[first_floor:]

    # The last pass alternates between the floor and the tab top.
    assert {round(move.z, 3) for move in final} == {-12.0, -8.0}
    tab_moves = [move for move in final if move.z == -8.0]
    assert len(tab_moves) >= 4
    # Every pass below the tab top lifts over the tabs; those above never do.
    earlier = {round(move.z, 3) for move in cut_moves[:first_floor]}
    assert earlier == {-3.0, -6.0, -9.0, -8.0}
    assert all(
        move.z != -8.0
        for move in cut_moves[:first_floor]
        if move.z > -6.0 - 1e-9
    )


def test_profile_without_tabs_stays_at_full_depth() -> None:
    path = profile("Outline", rectangle(50.0, 30.0), 6.0, MachiningParameters())

    assert {round(move.z, 3) for move in cuts(path.moves)} == {-3.0, -6.0}

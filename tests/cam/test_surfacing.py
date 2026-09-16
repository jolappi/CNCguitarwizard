"""Tests for the drop-cutter offset grid and raster surfacing passes."""

import math

import pytest

from cncguitarwizard.cam import (
    MachiningParameters,
    build_offset_grid,
    raster_finish,
    raster_rough,
)
from cncguitarwizard.cam.surfacing import interpolate_rows
from cncguitarwizard.cam.toolpath import Move


def cylinder(radius: float, crown: float):  # type: ignore[no-untyped-def]
    def surface(x: float, y: float) -> float:
        return crown - (radius - math.sqrt(max(0.0, radius * radius - y * y)))

    return surface


def cuts(moves: tuple[Move, ...]) -> list[Move]:
    return [move for move in moves if not move.rapid and move.z < 0.0]


def test_flat_tool_tip_is_the_highest_surface_point_under_the_disc() -> None:
    slope = lambda x, y: min(0.0, -0.1 * x)  # noqa: E731
    grid = build_offset_grid(slope, (0.0, 40.0), (-5.0, 5.0), MachiningParameters())

    # Descending slope: the trailing edge of the 6 mm disc sits 3 mm uphill
    # (plus half a cell of conservative sampling).
    assert grid.tip_at(20.0, 0.0) == pytest.approx(-0.1 * 16.5)
    assert grid.tip_at(0.0, 0.0) == pytest.approx(0.0)
    assert grid.floor() == pytest.approx(-0.1 * 36.5)


def test_ball_tool_never_gouges_a_cylinder() -> None:
    radius, crown = 430.0, -1.0
    surface = cylinder(radius, crown)
    ball = MachiningParameters(tool_tip="ball")
    grid = build_offset_grid(surface, (0.0, 10.0), (-30.0, 30.0), ball, spacing_y=0.5)

    # Exact drop cutter on a convex cylinder: the ball touches the surface
    # directly below its centre, so the tip sits on the surface.
    for y in (-28.0, -10.0, 0.0, 15.0, 27.5):
        assert grid.tip_at(5.0, y) >= surface(5.0, y) - 1e-9
        # Conservative cell sampling lets the tip hover a few hundredths.
        assert grid.tip_at(5.0, y) == pytest.approx(surface(5.0, y), abs=0.03)
    # And the sphere clears every finely sampled surface point.
    r = ball.tool_radius
    for y in (-27.0, 0.0, 20.0):
        centre_z = grid.tip_at(5.0, y) + r
        for dy in [step * 0.05 for step in range(-60, 61)]:
            if abs(dy) <= r:
                clearance = surface(5.0, y + dy) + math.sqrt(r * r - dy * dy)
                assert centre_z >= clearance - 0.01


def test_raster_finish_follows_the_offset_surface() -> None:
    surface = cylinder(430.0, -1.0)
    ball = MachiningParameters(tool_tip="ball")
    grid = build_offset_grid(surface, (0.0, 50.0), (-20.0, 20.0), ball)
    path = raster_finish(
        "Finish", grid, ball, x_range=(0.0, 50.0), y_range=(-20.0, 20.0), step_over=2.0
    )
    cut_moves = cuts(path.moves)

    ys = sorted({round(move.y, 3) for move in cut_moves})
    assert ys[0] == -20.0 and ys[-1] == 20.0 and len(ys) == 21
    for move in cut_moves:
        assert move.z >= grid.tip_at(move.x, move.y) - 0.003
        assert move.z <= grid.tip_at(move.x, move.y) + 0.05 or move.x in (0.0, 50.0)


def test_raster_rough_layers_never_exceed_the_step_down_or_the_surface() -> None:
    slope = lambda x, y: -0.2 * x  # noqa: E731  (0 to -10 over 50 mm)
    flat = MachiningParameters(step_down=3.0)
    grid = build_offset_grid(slope, (0.0, 50.0), (-6.0, 6.0), flat)
    path = raster_rough(
        "Rough", grid, flat, x_range=(0.0, 50.0), y_range=(-6.0, 6.0), step_over=3.0
    )
    cut_moves = cuts(path.moves)
    levels = sorted({round(move.z, 3) for move in cut_moves if move.z < -1e-6})

    assert min(levels) == pytest.approx(grid.floor(), abs=1e-6)
    for move in cut_moves:
        assert move.z >= grid.tip_at(move.x, move.y) - 1e-6
    # The first layer is a full flat pass, deeper layers only where material
    # remained below the previous one.
    first_layer = [move for move in cut_moves if abs(move.z - levels[-1]) < 1e-6]
    assert first_layer
    plunges = [
        move
        for move in path.moves
        if not move.rapid and move.feed == flat.plunge_rate
    ]
    assert all(abs(move.z) <= grid.floor() * -1 + 1e-6 for move in plunges)


def test_interpolate_rows_blends_between_stations_and_across_a_row() -> None:
    stations = [0.0, 10.0]
    rows = [([-1.0, 0.0, 1.0], [0.0, -2.0, 0.0]), ([-1.0, 0.0, 1.0], [0.0, -4.0, 0.0])]

    assert interpolate_rows(stations, rows, 5.0, 0.0) == pytest.approx(-3.0)
    assert interpolate_rows(stations, rows, 0.0, 0.5) == pytest.approx(-1.0)
    assert interpolate_rows(stations, rows, 11.0, 0.0) is None
    assert interpolate_rows(stations, rows, 5.0, 2.0) is None

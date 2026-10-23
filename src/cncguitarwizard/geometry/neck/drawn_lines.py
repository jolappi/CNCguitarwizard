"""Lines drawn across the neck's back, seen from behind.

A volute's crest and ends, and where the heel or a flat headstock's back
turns into the neck's, are drawn as lines across the back: half of each,
from the centre line out to one side, mirrored; or, its two sides
differing, the whole line from one side to the other. These are the
helpers they share: the whole line from its drawn points, how far a point
is from one, and which side of it a point is on.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..exceptions import NeckGeometryError
from ..primitives import DrawnPoint, Point2D, drawn_points, moved, open_catmull_rom


def drawn_whole(points: Sequence[DrawnPoint]) -> bool:
    """Return whether a line is drawn whole, from one side to the other
    (its sides differing), rather than half and mirrored: whether a point
    of it lies across on the -Y side."""
    return any(point[1] < 0.0 for point in points)


def drawn_back_line(
    points: Sequence[DrawnPoint], origin: float = 0.0
) -> tuple[Point2D, ...]:
    """Return a line drawn across the back, in the model frame.

    Args:
        points: Half of it seen from behind, ``(toward the headstock from
            origin, across)`` from the centre line out to one side (a point
            marked ``"corner"`` a sharp bend), the other half mirroring it;
            or, its sides differing (``drawn_whole``), the whole of it,
            from the -Y side across to the +Y side.
        origin: Where along the neck (the model's ``x``) its points are
            measured from: the nut (0) or, for the heel, its block.

    Returns:
        A smooth line through them (and their mirror), from one side to
        the other; empty for none.

    Raises:
        NeckGeometryError: For fewer than two points, mirrored.
    """
    if not points:
        return ()
    drawn, corners = drawn_points(points)
    model = [Point2D(origin - point.x, point.y) for point in drawn]
    if drawn_whole(points):
        whole, marks = tuple(model), tuple(corners)
    else:
        mirror = [
            (Point2D(point.x, -point.y), corner)
            for point, corner in zip(reversed(model), reversed(corners), strict=True)
            if abs(point.y) > 1e-9
        ]
        whole = (*(point for point, _ in mirror), *model)
        marks = (*(corner for _, corner in mirror), *corners)
    if len(whole) < 2:
        raise NeckGeometryError("A line drawn on the neck's back needs two points.")
    return open_catmull_rom(whole, 8, marks)


def mirrored_line(points: Sequence[DrawnPoint]) -> tuple[DrawnPoint, ...]:
    """Return a line's points as a left-handed neck has them.

    A whole line (``drawn_whole``) mirrored across the centre line, still
    from the -Y side to the +Y side; a half one as it is (its mirror is
    itself).
    """
    if not drawn_whole(points):
        return tuple(points)
    return tuple(moved(point, point[0], -point[1]) for point in reversed(points))


def nearest(point: Point2D, line: Sequence[Point2D]) -> tuple[float, float]:
    """Return how far ``point`` is from the open ``line``, and which side
    of it it is on (the sign of the turn from the line's way to it)."""
    best, side = math.inf, 0.0
    for start, end in zip(line, line[1:], strict=False):
        dx, dy = end.x - start.x, end.y - start.y
        length_squared = dx * dx + dy * dy
        along = (
            0.0
            if length_squared == 0.0
            else max(
                0.0,
                min(
                    1.0,
                    ((point.x - start.x) * dx + (point.y - start.y) * dy)
                    / length_squared,
                ),
            )
        )
        off_x = point.x - start.x - along * dx
        off_y = point.y - start.y - along * dy
        distance = math.hypot(off_x, off_y)
        if distance < best:
            best, side = distance, dx * off_y - dy * off_x
    return best, side


def side_toward(line: Sequence[Point2D], toward: float) -> float:
    """Return which side of ``line`` lies ``toward`` along the neck (-1 the
    headstock, 1 the body), as ``nearest``'s side sign: tried a millimetre
    that way from the line's middle."""
    if not line:
        return 1.0
    middle = line[len(line) // 2]
    _, side = nearest(Point2D(middle.x + toward, middle.y), line)
    return 1.0 if side >= 0.0 else -1.0


def smootherstep(fraction: float) -> float:
    """Return the quintic ease from 0 to 1, flat at both ends."""
    return fraction**3 * (fraction * (fraction * 6.0 - 15.0) + 10.0)

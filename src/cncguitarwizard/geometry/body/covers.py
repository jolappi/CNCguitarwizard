"""Cover plates for the electronics cavities, and where their screws go."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from ..exceptions import BodyGeometryError
from ..primitives import Point2D
from .hardware import Cavity, DrilledHole


@dataclass(frozen=True, slots=True)
class CoverPlate:
    """A flat plate that closes a cavity, cut from sheet (plexiglass, plastic).

    The plate sits flush in its cavity's cover recess, so its outline is
    that recess's outline and its thickness the recess depth — or, not
    ``recessed``, on the face itself (a truss-rod cover on the headstock).

    Args:
        name: Plate name, e.g. ``"Control cavity cover"``.
        face: The body face the plate sits on: ``"back"`` for a rear
            cavity, ``"top"`` for a top-routed control plate.
        outline: The plate's outline in the model frame.
        thickness: Sheet thickness.
        holes: Holes through the plate — screw clearance holes, and pot
            shaft holes for a control plate.
        slots: Openings through the plate that are not round (a blade
            switch's slot).
        recessed: Whether it sits in a recess (cut a little smaller to
            fit it) rather than on the face.

    Raises:
        BodyGeometryError: For a non-positive thickness or an outline of
            fewer than three points.
    """

    name: str
    face: Literal["top", "back"]
    outline: tuple[Point2D, ...]
    thickness: float
    holes: tuple[DrilledHole, ...] = ()
    slots: tuple[Cavity, ...] = ()
    recessed: bool = True

    def __post_init__(self) -> None:
        """Reject a plate that cannot be cut."""
        if len(self.outline) < 3:
            raise BodyGeometryError(f"{self.name} needs an outline.")
        if not math.isfinite(self.thickness) or self.thickness <= 0.0:
            raise BodyGeometryError(f"{self.name} thickness must be positive.")


def cover_screw_points(
    cavity: Sequence[Point2D],
    cover: Sequence[Point2D],
    count: int,
    minimum_ledge: float,
) -> tuple[Point2D, ...]:
    """Return up to ``count`` screw centres spread round a cover's ledge.

    The ledge is the band between the cavity's outline and its cover
    recess's. Rays leave the cover's bounding-box centre at even angles,
    stretched to the box's proportions so four screws land toward the
    corners of a rectangular cover (and an odd count starts straight
    along +Y). Each screw sits halfway between where its ray leaves the
    cavity and where it leaves the cover. Where the ledge is narrower
    than ``minimum_ledge`` the ray is turned up to 30 degrees either
    way; a screw with no wide enough ledge in that range is skipped.
    """
    xs = [point.x for point in cover]
    ys = [point.y for point in cover]
    centre = Point2D((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)
    half_x = (max(xs) - min(xs)) / 2.0
    half_y = (max(ys) - min(ys)) / 2.0
    start = math.pi / 4.0 if count % 2 == 0 else math.pi / 2.0
    points: list[Point2D] = []
    for step in range(count):
        angle = start + 2.0 * math.pi * step / count
        # Where the ledge is too narrow, try turning the ray a little.
        for nudge in (0.0, 10.0, -10.0, 20.0, -20.0, 30.0, -30.0):
            screw = _ledge_point(
                centre,
                (half_x, half_y),
                angle + math.radians(nudge),
                cavity,
                cover,
                minimum_ledge,
            )
            if screw is not None:
                points.append(screw)
                break
    return tuple(points)


def _ledge_point(
    centre: Point2D,
    half_size: tuple[float, float],
    angle: float,
    cavity: Sequence[Point2D],
    cover: Sequence[Point2D],
    minimum_ledge: float,
) -> Point2D | None:
    """Return the mid-ledge point on one ray, or ``None`` if too narrow."""
    direction = (half_size[0] * math.cos(angle), half_size[1] * math.sin(angle))
    outer = _ray_exit(centre, direction, cover)
    inner = _ray_exit(centre, direction, cavity)
    if outer is None or inner is None or inner >= outer:
        return None
    middle = (inner + outer) / 2.0
    screw = Point2D(centre.x + direction[0] * middle, centre.y + direction[1] * middle)
    ledge = _distance_to_outline(screw, cavity) + _distance_to_outline(screw, cover)
    return screw if ledge >= minimum_ledge else None


def _ray_exit(
    origin: Point2D, direction: tuple[float, float], outline: Sequence[Point2D]
) -> float | None:
    """Return the ray parameter where it last crosses ``outline``, if any."""
    dx, dy = direction
    best: float | None = None
    for a, b in zip(outline, (*outline[1:], outline[0]), strict=True):
        ex, ey = b.x - a.x, b.y - a.y
        denominator = dx * ey - dy * ex
        if abs(denominator) < 1e-12:
            continue
        ax, ay = a.x - origin.x, a.y - origin.y
        t = (ax * ey - ay * ex) / denominator
        u = (ax * dy - ay * dx) / denominator
        if t > 0.0 and -1e-9 <= u <= 1.0 + 1e-9 and (best is None or t > best):
            best = t
    return best


def _distance_to_outline(point: Point2D, outline: Sequence[Point2D]) -> float:
    """Return the distance from ``point`` to the closed polyline ``outline``."""
    best = math.inf
    for a, b in zip(outline, (*outline[1:], outline[0]), strict=True):
        ex, ey = b.x - a.x, b.y - a.y
        length_squared = ex * ex + ey * ey
        t = 0.0
        if length_squared > 0.0:
            t = ((point.x - a.x) * ex + (point.y - a.y) * ey) / length_squared
            t = min(1.0, max(0.0, t))
        best = min(best, math.hypot(a.x + ex * t - point.x, a.y + ey * t - point.y))
    return best

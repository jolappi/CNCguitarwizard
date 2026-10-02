"""Edge finishes: roundovers, binding channels and arm / belly contours.

Everything here is optional; a body with none of it keeps the square
edges and flat faces of the slab.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

from ..exceptions import BodyGeometryError
from ..primitives import Point2D


@dataclass(frozen=True, slots=True)
class EdgeProfile:
    """How the outline edge of one face is finished.

    Args:
        radius: Roundover radius; ``0`` leaves the edge square.
        binding_width: Width of a binding channel (a rabbet) cut into
            the edge; ``0`` for no binding.
        binding_depth: Depth of that channel from the face.

    Raises:
        BodyGeometryError: For a negative or non-finite value, or a
            roundover and a binding on the same edge.
    """

    radius: float = 0.0
    binding_width: float = 0.0
    binding_depth: float = 0.0

    def __post_init__(self) -> None:
        """Reject a finish that cannot be cut."""
        for name in ("radius", "binding_width", "binding_depth"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0.0:
                raise BodyGeometryError(f"Edge {name} must be zero or more.")
        if self.radius > 0.0 and self.has_binding:
            raise BodyGeometryError(
                "An edge takes either a roundover or a binding channel, not both."
            )
        if self.binding_width > 0.0 and self.binding_depth <= 0.0:
            raise BodyGeometryError("A binding channel needs a depth.")

    @property
    def has_binding(self) -> bool:
        """Return whether a binding channel is cut into this edge."""
        return self.binding_width > 0.0

    @property
    def reach(self) -> float:
        """Return how far the finish reaches into the face, in mm."""
        return max(self.radius, self.binding_depth if self.has_binding else 0.0)


CONTOUR_SAMPLE_SPACING = 4.0
"""Spacing of the edge samples a contour is described by, in mm."""


@dataclass(frozen=True, slots=True)
class ContourCut:
    """A bevel along one bout's edge: a Strat-style arm or belly contour.

    The bevel follows a stretch of the outline ``length`` long, centred
    on its deepest point. Across the edge it is a straight ramp from
    the face, ``width`` in from the edge, down to ``depth`` at the edge;
    along the edge both width and depth fade to nothing toward the ends
    (a ``cos²`` taper), so it blends into the square edge either side.
    Given ``reaches`` instead (a line drawn where the bevel starts, see
    ``along_line``), it reaches that far in at each edge sample, and its
    depth at the edge is ``depth`` scaled by the reach over ``width``.

    Args:
        name: E.g. ``"Arm contour"``.
        face: ``"top"`` for an arm contour, ``"back"`` for a belly cut.
        edge: The outline stretch, sampled every
            ``CONTOUR_SAMPLE_SPACING``, in order along the outline.
        normals: The inward unit normal at each edge sample.
        arc: Each sample's distance along the edge from the deepest
            point (negative before it).
        length: The stretch's full length.
        width: How far the bevel reaches in from the edge at its deepest.
        depth: How deep it is at the edge at its deepest.
        reaches: How far it reaches in at each edge sample, or empty for
            the ``cos²`` taper of ``width``.

    Raises:
        BodyGeometryError: For a non-positive size or mismatched samples.
    """

    name: str
    face: Literal["top", "back"]
    edge: tuple[Point2D, ...]
    normals: tuple[Point2D, ...]
    arc: tuple[float, ...]
    length: float
    width: float
    depth: float
    reaches: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        """Reject a contour that cannot be cut."""
        for label in ("length", "width", "depth"):
            value = getattr(self, label)
            if not math.isfinite(value) or value <= 0.0:
                raise BodyGeometryError(f"{self.name} {label} must be positive.")
        if not len(self.edge) == len(self.normals) == len(self.arc) >= 2:
            raise BodyGeometryError(f"{self.name} needs matching edge samples.")
        if self.reaches and len(self.reaches) != len(self.edge):
            raise BodyGeometryError(f"{self.name} needs a reach for every sample.")

    @classmethod
    def along_edge(
        cls,
        name: str,
        face: Literal["top", "back"],
        outline: Sequence[Point2D],
        apex_index: int,
        length: float,
        width: float,
        depth: float,
    ) -> ContourCut:
        """Return a contour centred on ``outline[apex_index]``.

        The outline is walked ``length / 2`` each way from that point and
        resampled evenly.
        """
        if length <= 0.0:
            raise BodyGeometryError(f"{name} length must be positive.")
        points = list(outline)
        count = len(points)
        area = sum(
            a.x * b.y - b.x * a.y
            for a, b in zip(points, (*points[1:], points[0]), strict=True)
        )
        # Arc length of every outline vertex, walking forward from the apex.
        forward = [0.0]
        for step in range(1, count):
            a = points[(apex_index + step - 1) % count]
            b = points[(apex_index + step) % count]
            forward.append(forward[-1] + math.dist((a.x, a.y), (b.x, b.y)))
        perimeter = forward[-1] + math.dist(
            (points[apex_index - 1].x, points[apex_index - 1].y),
            (points[apex_index].x, points[apex_index].y),
        )
        if length >= perimeter:
            raise BodyGeometryError(f"{name} is longer than the body's edge.")

        def at(s: float) -> Point2D:
            s %= perimeter
            for step in range(count):
                end = forward[step + 1] if step + 1 < count else perimeter
                if s <= end:
                    a = points[(apex_index + step) % count]
                    b = points[(apex_index + step + 1) % count]
                    span = end - forward[step]
                    t = (s - forward[step]) / span if span else 0.0
                    return Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)
            return points[apex_index]

        samples = max(2, math.ceil(length / CONTOUR_SAMPLE_SPACING))
        arc = tuple(-length / 2.0 + length * i / samples for i in range(samples + 1))
        edge = tuple(at(s) for s in arc)
        normals: list[Point2D] = []
        for s in arc:
            a, b = at(s - 12.0), at(s + 12.0)
            tx, ty = b.x - a.x, b.y - a.y
            size = math.hypot(tx, ty) or 1.0
            tx, ty = tx / size, ty / size
            normals.append(Point2D(-ty, tx) if area > 0.0 else Point2D(ty, -tx))
        return cls(name, face, edge, tuple(normals), arc, length, width, depth)

    @classmethod
    def along_line(
        cls,
        name: str,
        face: Literal["top", "back"],
        outline: Sequence[Point2D],
        line: Sequence[Point2D],
        depth: float,
    ) -> ContourCut:
        """Return a contour from the edge in to ``line``, where it starts.

        The line's ends are taken onto the outline; the bevel runs along
        the stretch of edge between them (the way round nearer the line's
        middle) and, at each edge sample, in along the inward normal to
        where it meets the line.

        Raises:
            BodyGeometryError: When the line does not run inside the body
                beside that stretch.
        """
        if len(line) < 2:
            raise BodyGeometryError(f"{name} line needs at least two points.")
        points = list(outline)
        count = len(points)

        def nearest(p: Point2D) -> int:
            return min(range(count), key=lambda i: math.dist(_xy(points[i]), _xy(p)))

        first, last = nearest(line[0]), nearest(line[-1])
        middle = line[len(line) // 2]
        forward, backward = (last - first) % count, (first - last) % count
        way_forward = points[(first + forward // 2) % count]
        way_back = points[(last + backward // 2) % count]
        if math.dist(_xy(way_forward), _xy(middle)) <= math.dist(
            _xy(way_back), _xy(middle)
        ):
            start, steps = first, forward
        else:
            start, steps = last, backward
        if steps < 2:
            raise BodyGeometryError(f"{name} line's ends are too close together.")
        stretch = [points[(start + k) % count] for k in range(steps + 1)]
        lengths = [0.0]
        for a, b in zip(stretch, stretch[1:], strict=False):
            lengths.append(lengths[-1] + math.dist(_xy(a), _xy(b)))
        length = lengths[-1]
        apex = (
            start + min(range(steps + 1), key=lambda k: abs(lengths[k] - length / 2.0))
        ) % count
        shape = cls.along_edge(name, face, outline, apex, length, 1.0, depth)
        reaches = tuple(
            _ray_to_line(p, n, line)
            for p, n in zip(shape.edge, shape.normals, strict=True)
        )
        widest = max(reaches)
        if widest <= 0.0:
            raise BodyGeometryError(
                f"{name} line must run inside the body, its ends on the edge."
            )
        return replace(shape, width=widest, reaches=reaches)

    def reach(self, s: float) -> float:
        """Return how far in from the edge the bevel reaches at arc ``s``."""
        if not self.reaches:
            return self.width * self.taper(s)
        if s <= self.arc[0] or s >= self.arc[-1]:
            return 0.0
        for index in range(len(self.arc) - 1):
            a, b = self.arc[index], self.arc[index + 1]
            if a <= s <= b:
                t = (s - a) / (b - a) if b > a else 0.0
                return (
                    self.reaches[index]
                    + (self.reaches[index + 1] - self.reaches[index]) * t
                )
        return 0.0

    def fade(self, s: float) -> float:
        """Return the depth at the edge at arc ``s`` over the deepest (0 to 1)."""
        return self.reach(s) / self.width

    def taper(self, s: float) -> float:
        """Return the fade (1 at the deepest point, 0 at the ends) at arc ``s``."""
        if abs(s) >= self.length / 2.0:
            return 0.0
        return math.cos(math.pi * s / self.length) ** 2

    def locate(self, point: Point2D) -> tuple[float, float]:
        """Return ``(arc, inward distance)`` of ``point`` from the edge.

        The inward distance is negative outside the body.
        """
        # The samples are evenly spaced, so the nearest segment is one of
        # the two either side of the nearest sample.
        px, py = point.x, point.y
        nearest = min(
            range(len(self.edge)),
            key=lambda i: (self.edge[i].x - px) ** 2 + (self.edge[i].y - py) ** 2,
        )
        best = (math.inf, 0.0, 0.0)
        for index in (nearest - 1, nearest):
            if index < 0 or index >= len(self.edge) - 1:
                continue
            a, b = self.edge[index], self.edge[index + 1]
            ex, ey = b.x - a.x, b.y - a.y
            size = ex * ex + ey * ey
            t = ((px - a.x) * ex + (py - a.y) * ey) / size if size else 0.0
            t = min(1.0, max(0.0, t))
            cx, cy = a.x + ex * t, a.y + ey * t
            distance = math.hypot(px - cx, py - cy)
            if distance < best[0]:
                na, nb = self.normals[index], self.normals[index + 1]
                nx, ny = na.x + (nb.x - na.x) * t, na.y + (nb.y - na.y) * t
                inward = (px - cx) * nx + (py - cy) * ny
                s = self.arc[index] + (self.arc[index + 1] - self.arc[index]) * t
                best = (distance, s, inward)
        return best[1], best[2]

    def depth_at(self, point: Point2D) -> float:
        """Return the bevel's depth below the face at ``point``.

        Past the edge (in the waste around the body) the ramp runs on,
        up to half as deep again, so a cutter can finish the edge.
        """
        return self.depth_from(*self.locate(point))

    def depth_from(self, s: float, inward: float) -> float:
        """Return the depth for an already located ``(arc, inward)`` pair."""
        reach = self.reach(s)
        if reach <= 0.0:
            return 0.0
        fade = reach / self.width
        if inward >= reach:
            return 0.0
        ramp = self.depth * fade * (1.0 - inward / reach)
        return min(ramp, self.depth * fade * 1.5)

    def max_depth(self, outline: Sequence[Point2D]) -> float:
        """Return the deepest the bevel goes on the body (at its edge)."""
        return self.depth

    def inner_edge(self) -> tuple[Point2D, ...]:
        """Return where the bevel meets the face, along the edge samples."""
        return tuple(
            Point2D(p.x + n.x * self.reach(s), p.y + n.y * self.reach(s))
            for p, n, s in zip(self.edge, self.normals, self.arc, strict=True)
        )

    def region(self, outline: Sequence[Point2D] = ()) -> tuple[Point2D, ...]:
        """Return the bevelled area: the edge stretch and the bevel's inner edge."""
        return (*self.edge, *reversed(self.inner_edge()))


def _xy(point: Point2D) -> tuple[float, float]:
    return (point.x, point.y)


def _ray_to_line(origin: Point2D, direction: Point2D, line: Sequence[Point2D]) -> float:
    """Return how far along ``direction`` from ``origin`` it meets ``line``.

    Zero when it does not meet it ahead.
    """
    best = math.inf
    for a, b in zip(line, line[1:], strict=False):
        ex, ey = b.x - a.x, b.y - a.y
        denominator = direction.x * ey - direction.y * ex
        if abs(denominator) < 1e-12:
            continue
        wx, wy = a.x - origin.x, a.y - origin.y
        t = (wx * ey - wy * ex) / denominator
        u = (wx * direction.y - wy * direction.x) / denominator
        if t > 0.0 and 0.0 <= u <= 1.0:
            best = min(best, t)
    return best if math.isfinite(best) else 0.0

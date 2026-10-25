"""Edge finishes: roundovers, binding channels, arm / belly contours and heel reliefs.

Everything here is optional; a body with none of it keeps the square
edges and flat faces of the slab.
"""

from __future__ import annotations

import bisect
import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

from ..exceptions import BodyGeometryError
from ..primitives import Point2D, point_in_polygon


@dataclass(frozen=True, slots=True)
class EdgeProfile:
    """How the outline edge of one face is finished.

    Args:
        radius: Roundover radius; ``0`` leaves the edge square.
        binding_width: Width of a binding channel (a rabbet) cut into
            the edge; ``0`` for no binding.
        binding_depth: Depth of that channel from the face.
        square: Regions of the face the roundover stops short of, the
            edge in them left square, to blend by hand: round a bolt-on
            neck's plate on the back where it sits too near the edge for
            the roundover (a Stratocaster's, 3 mm in), as builders stop
            the router short of it.

    Raises:
        BodyGeometryError: For a negative or non-finite value, or a
            roundover and a binding on the same edge.
    """

    radius: float = 0.0
    binding_width: float = 0.0
    binding_depth: float = 0.0
    square: tuple[tuple[Point2D, ...], ...] = ()

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

    def rounds_at(self, point: Point2D) -> bool:
        """Return whether the roundover is cut at ``point``: anywhere but
        in a ``square`` region."""
        return not any(point_in_polygon(point, region) for region in self.square)

    @property
    def reach(self) -> float:
        """Return how far the finish reaches into the face, in mm."""
        return max(self.radius, self.binding_depth if self.has_binding else 0.0)


CONTOUR_SAMPLE_SPACING = 4.0
"""Spacing of the edge samples a contour is described by, in mm."""

CONTOUR_WASTE = 10.0
"""How far past the edge (into the waste) a contour's layers reach, in mm."""

AROUND_SHARE = 0.45
"""The most of the body's width across at a point a bevel all round
(``ContourCut.around``) reaches in, so the bevels either side of a narrow
part (a horn's tip) never meet."""

AROUND_GAP = 2.0
"""How far, in mm, a bevel all round stops short of a route or hole."""

AROUND_FADE = 20.0
"""How far along the edge, in mm, a bevel all round fades in from either
end (where the neck joins)."""

AROUND_ROUND_FADE = 60.0
"""How far along the edge, in mm, a bevel all round fades out into a
stretch it leaves to the edge's roundover (``rounded``), so the two run
into each other rather than the bevel ending at a wall."""

AROUND_TAPER = 0.25
"""How fast a bevel all round narrows to keep clear of something, and
widens again past it: its reach changes by at most this many millimetres
per millimetre along the edge, so it eases into a waist, not a notch."""


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
        # A line meeting the edge at a slant (a Stratocaster's, turning
        # round onto the tail) is still far in along the last samples'
        # normals: run out over as far along the edge as it reaches in at
        # either end, so the bevel ends on the line's end at about the
        # angle it falls across, not as a wall that deep.
        reaches = tuple(
            reach * _run_out(s, shape.arc, reaches)
            for reach, s in zip(reaches, shape.arc, strict=True)
        )
        widest = max(reaches)
        if widest <= 0.0:
            raise BodyGeometryError(
                f"{name} line must run inside the body, its ends on the edge."
            )
        return replace(shape, width=widest, reaches=reaches)

    @classmethod
    def around(
        cls,
        name: str,
        face: Literal["top", "back"],
        outline: Sequence[Point2D],
        skip: Sequence[bool],
        width: float,
        depth: float,
        keep_clear: Sequence[Sequence[Point2D]] = (),
        rounded: Sequence[bool] = (),
    ) -> ContourCut:
        """Return a bevel all round the body but where ``skip`` marks it.

        ``skip`` marks the outline's points left square (where the neck
        joins, and any other stretch); the bevel runs round from the end of
        the longest such run to its start, square across the others,
        ``width`` in from the edge and ``depth`` deep there, but never
        further in than ``AROUND_SHARE`` of the body's width across at a
        point (a horn's tip), nor than ``AROUND_GAP`` short of anything in
        ``keep_clear`` (the routes and holes in its face, as outlines), its
        depth going with its reach so its angle stays the same, as an SG's
        does. Wherever it narrows so it eases in and out over the edge
        beside, by ``AROUND_TAPER`` (a waist rather than a notch), and it
        fades in over ``AROUND_FADE`` from either end of every stretch left
        square, over ``AROUND_ROUND_FADE`` from one ``rounded`` marks
        (left to the edge's roundover; skipped too).

        Raises:
            BodyGeometryError: When ``skip`` marks none of the outline or
                all of it.
        """
        points = list(outline)
        count = len(points)
        rounded = list(rounded) or [False] * count
        skip = [square or round_over for square, round_over in zip(skip, rounded)]
        if len(skip) != count or not any(skip) or all(skip):
            raise BodyGeometryError(
                f"{name} needs a stretch of the edge to leave square."
            )
        # The longest run of skipped points, round the outline.
        best_start, best_run = 0, 0
        for index in range(count):
            if not skip[index] or skip[index - 1]:
                continue
            run = 0
            while skip[(index + run) % count] and run < count:
                run += 1
            if run > best_run:
                best_start, best_run = index, run
        first = (best_start + best_run - 1) % count
        last = best_start
        steps = (last - first) % count
        stretch = [points[(first + k) % count] for k in range(steps + 1)]
        arcs = [0.0]
        for a, b in itertools.pairwise(stretch):
            arcs.append(arcs[-1] + math.dist(_xy(a), _xy(b)))
        length = arcs[-1]
        apex = (
            first + min(range(steps + 1), key=lambda k: abs(arcs[k] - length / 2.0))
        ) % count
        shape = cls.along_edge(name, face, outline, apex, length, width, depth)
        closed = [*points, points[0]]
        reaches = []
        for point, normal in zip(shape.edge, shape.normals, strict=True):
            origin = Point2D(point.x + normal.x * 0.01, point.y + normal.y * 0.01)
            across = _ray_to_line(origin, normal, closed)
            reaches.append(min(width, AROUND_SHARE * across) if across > 0.0 else 0.0)
        # Short of whatever it must keep clear of: every point of it caps
        # the reach of the edge either side of it; one breaking through
        # the edge (a neck pocket opening out of the side) stops it there.
        spacing = shape.length / (len(shape.arc) - 1)
        for polygon in keep_clear:
            for point in _densified(polygon, 2.0):
                s, inward = shape.locate(point)
                if inward < -CONTOUR_WASTE:
                    continue
                cap = max(0.0, inward - AROUND_GAP)
                position = (s - shape.arc[0]) / spacing
                for index in {math.floor(position), math.ceil(position)}:
                    if 0 <= index < len(reaches):
                        reaches[index] = min(reaches[index], cap)
        # Eased into and out of every narrowing, both ways along the edge.
        step = AROUND_TAPER * spacing
        for index in range(1, len(reaches)):
            reaches[index] = min(reaches[index], reaches[index - 1] + step)
        for index in range(len(reaches) - 2, -1, -1):
            reaches[index] = min(reaches[index], reaches[index + 1] + step)
        # Fading in from either end, and either side of every other
        # stretch left square (its points, along the edge as the samples).
        middle = arcs[(apex - first) % count]
        places = [arc - middle for arc in arcs]
        square = [
            (
                places[k],
                AROUND_ROUND_FADE if rounded[(first + k) % count] else AROUND_FADE,
            )
            for k in range(steps + 1)
            if skip[(first + k) % count]
        ]
        faded = []
        for reach, s in zip(reaches, shape.arc, strict=True):
            end = min(abs(s - place) / fade for place, fade in square)
            # Between two points left square: none of it.
            k = min(max(bisect.bisect_right(places, s) - 1, 0), steps - 1)
            if skip[(first + k) % count] and skip[(first + k + 1) % count]:
                end = 0.0
            end = min(1.0, max(0.0, end))
            faded.append(reach * end * end * (3.0 - 2.0 * end))
        return replace(shape, reaches=tuple(faded))

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

    def clear_of(self, point: Point2D, gap: float) -> Point2D:
        """Return ``point`` moved in off the bevel, ``gap`` past it.

        A point closer to the edge than the bevel reaches in beside it,
        and ``gap`` more, is moved in along the edge's normal to that far
        in; any other is returned as it is.
        """
        s, inward = self.locate(point)
        reach = self.reach(s)
        if reach <= 0.0 or inward >= reach + gap:
            return point
        normal = self._normal_at(s)
        shift = reach + gap - inward
        return Point2D(point.x + normal.x * shift, point.y + normal.y * shift)

    def _normal_at(self, s: float) -> Point2D:
        """Return the inward unit normal at arc ``s`` (between samples,
        their normals blended)."""
        index = min(
            len(self.arc) - 2,
            max(0, next((k for k, a in enumerate(self.arc) if a > s), 1) - 1),
        )
        a, b = self.arc[index], self.arc[index + 1]
        t = min(1.0, max(0.0, (s - a) / (b - a))) if b > a else 0.0
        na, nb = self.normals[index], self.normals[index + 1]
        nx, ny = na.x + (nb.x - na.x) * t, na.y + (nb.y - na.y) * t
        size = math.hypot(nx, ny) or 1.0
        return Point2D(nx / size, ny / size)

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
        if inward >= reach:
            return 0.0
        fade = reach / self.width
        ramp = self.depth * fade * (1.0 - inward / reach)
        return min(ramp, self.depth * fade * 1.5)

    def machining_depth(self, point: Point2D, slot: float) -> float:
        """Return the depth a cutter takes at ``point``.

        On the body, the bevel's; past the edge the ramp runs on through
        the outline's slot (``slot`` wide), where the cutter finishes the
        edge from, and no further.
        """
        s, inward = self.locate(point)
        if inward < -slot:
            return 0.0
        return self.depth_from(s, inward)

    def cuts(self, point: Point2D) -> bool:
        """Whether the bevel cuts at ``point``: on the body, or in the waste
        no more than ``CONTOUR_WASTE`` past the edge (the ramp runs on
        outside it for the cutter, but nothing further out is cut)."""
        s, inward = self.locate(point)
        return inward >= -CONTOUR_WASTE and self.depth_from(s, inward) > 0.0

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

    def level_regions(self, level: float) -> tuple[tuple[Point2D, ...], ...]:
        """Return the areas where the bevel is deeper than ``level``.

        Each bounded inside the body by where the ramp passes that depth
        and outside it by a line ``CONTOUR_WASTE`` past the edge, so a
        terrace cut down to ``level`` clears the edge too: one for each run
        of the edge it is that deep along (a bevel thinned to nothing round
        a horn's tip, or left square along a stretch, makes two, not one
        reaching across the gap).
        """
        regions: list[tuple[Point2D, ...]] = []
        inner: list[Point2D] = []
        outer: list[Point2D] = []

        def close() -> None:
            if len(inner) >= 2:
                regions.append((*inner, *reversed(outer)))
            inner.clear()
            outer.clear()

        for point, normal, arc in zip(self.edge, self.normals, self.arc, strict=True):
            edge_depth = self.depth * self.fade(arc)
            if edge_depth <= level:
                close()
                continue
            reach = self.reach(arc) * (1.0 - level / edge_depth)
            inner.append(
                Point2D(point.x + normal.x * reach, point.y + normal.y * reach)
            )
            outer.append(
                Point2D(
                    point.x - normal.x * CONTOUR_WASTE,
                    point.y - normal.y * CONTOUR_WASTE,
                )
            )
        close()
        return tuple(regions)


HEEL_RELIEF_RULINGS = 72
"""How many rulings (edge point to line point) a heel relief is drawn by."""

HEEL_RELIEF_FADE = 10.0
"""How far along its edge a contour heel relief fades in from nothing at
either end, in mm: where its line meets the edge it runs out smoothly,
not as a wall the relief's full depth."""


@dataclass(frozen=True, slots=True)
class HeelRelief:
    """A relief cut into the back where the neck's heel meets the body.

    It runs from ``edge`` (the body's edge at the neck end) in to ``line``
    (where it starts on the face). Its surface is ruled: both are sampled
    evenly along their lengths, the same number of points each, and the
    samples are joined in order, so a concave edge (between a body's
    horns) gives no crossing rulings. Along each ruling a ``"ramp"`` (a
    contour) rises from ``depth`` at the edge to the face at the line,
    fading in along the edge over ``HEEL_RELIEF_FADE`` from either end
    (where the line meets it) so it runs out there smoothly; a
    ``"flat"`` profile (a notch) is ``depth`` deep all the way in, a wall
    at the line; a ``"plane"`` (a bevel, for a neck plate to sit on) is a
    flat slope, ``depth`` deep at ``plane[0]`` along ``plane_axis`` (X: a
    slope across the neck) and at the face at ``plane[1]``, never deeper
    than ``depth``; with a ``side_run`` (no plate to sit on it) its sides
    slope too, up to the face at the line from that far in, so it has no
    wall there.

    Args:
        name: Its name, e.g. ``"Heel relief"``.
        edge: The edge stretch it runs from, ``HEEL_RELIEF_RULINGS`` evenly
            spaced points.
        line: Where it starts on the face, as many points, from the end
            nearer ``edge[0]``.
        depth: How deep it is at its deepest.
        profile: ``"ramp"``, ``"flat"`` or ``"plane"``.
        plane: For a ``"plane"``: where it is ``depth`` deep and where it
            meets the face, along ``plane_axis``.
        plane_axis: The unit direction ``plane`` is measured along: X for a
            bevel across the neck, slanting for one across a corner.
        carries: The holes drilled from its surface (their depths, from
            the face, take it in): they may start on it.
        face: Always the back.
        side_run: For a ``"plane"``: how far in from its line it reaches
            the plane's depth, rising straight to the face at the line
            (0: the plane right up to a wall at the line).

    Raises:
        BodyGeometryError: For a depth that is not finite and positive,
            mismatched samples, a plane whose two places are the same, a
            plane axis that is not a unit vector, or a negative side run.
    """

    name: str
    edge: tuple[Point2D, ...]
    line: tuple[Point2D, ...]
    depth: float
    profile: Literal["ramp", "flat", "plane"] = "ramp"
    plane: tuple[float, float] = (0.0, 0.0)
    plane_axis: tuple[float, float] = (1.0, 0.0)
    carries: tuple[str, ...] = ()
    face: Literal["back"] = "back"
    side_run: float = 0.0

    def __post_init__(self) -> None:
        """Reject a relief that cannot be cut."""
        if not math.isfinite(self.depth) or self.depth <= 0.0:
            raise BodyGeometryError(f"{self.name} depth must be positive.")
        if len(self.edge) != len(self.line) or len(self.edge) < 2:
            raise BodyGeometryError(
                f"{self.name} needs matching edge and line samples."
            )
        if self.profile == "plane" and math.isclose(self.plane[0], self.plane[1]):
            raise BodyGeometryError(f"{self.name}'s slope needs a length.")
        if not math.isclose(math.hypot(*self.plane_axis), 1.0):
            raise BodyGeometryError(f"{self.name}'s slope needs a unit direction.")
        if not math.isfinite(self.side_run) or self.side_run < 0.0:
            raise BodyGeometryError(f"{self.name}'s side run must not be negative.")

    @classmethod
    def between(
        cls,
        name: str,
        outline: Sequence[Point2D],
        line: Sequence[Point2D],
        depth: float,
        profile: Literal["ramp", "flat", "plane"] = "ramp",
        plane: tuple[float, float] = (0.0, 0.0),
        plane_axis: tuple[float, float] = (1.0, 0.0),
        side_run: float = 0.0,
    ) -> HeelRelief:
        """Return a relief from the edge in to ``line``.

        The line's ends are taken onto the outline; the relief runs from
        the stretch of edge between them (the way round nearer the line's
        middle).

        Raises:
            BodyGeometryError: For a line of fewer than two points or with
                its ends too close together on the edge.
        """
        if len(line) < 2:
            raise BodyGeometryError(f"{name} line needs at least two points.")
        stretch = _stretch_between(name, outline, line)
        return cls(
            name,
            _resample(stretch, HEEL_RELIEF_RULINGS),
            _resample(line, HEEL_RELIEF_RULINGS),
            depth,
            profile,
            plane,
            plane_axis,
            side_run=side_run,
        )

    def _profile_depth(self, t: float, point: Point2D, fade: float = 1.0) -> float:
        """Return the depth ``t`` of the way along a ruling, at ``point``.

        ``fade`` is the share of its full depth a ramp has at the edge
        there (``_fades``).
        """
        if self.profile == "flat":
            return self.depth
        if self.profile == "plane":
            deep, face = self.plane
            fraction = (self.along_plane(point) - face) / (deep - face)
            sloped = self.depth * min(1.0, max(0.0, fraction))
            if self.side_run:
                # Its sides rising to the face at the line.
                side = self.depth * _distance_to(self.line, point) / self.side_run
                return min(sloped, side)
            return sloped
        return self.depth * fade * (1.0 - t)

    def _fades(self) -> tuple[float, ...]:
        """Return the share of its full depth a ramp has at each ruling.

        Rising smoothly from nothing at either end of the edge to all of it
        ``HEEL_RELIEF_FADE`` along (the rulings are evenly spaced along
        it); a notch or a bevel keeps its depth to the ends.
        """
        count = len(self.edge)
        if self.profile != "ramp":
            return (1.0,) * count
        length = sum(
            math.dist(_xy(a), _xy(b))
            for a, b in zip(self.edge, self.edge[1:], strict=False)
        )
        spacing = length / (count - 1)
        shares = []
        for k in range(count):
            s = min(1.0, min(k, count - 1 - k) * spacing / HEEL_RELIEF_FADE)
            shares.append(s * s * (3.0 - 2.0 * s))
        return tuple(shares)

    def _side_reach(self, e: Point2D, start: Point2D, level: float) -> float:
        """Return how far along the ruling ``e``→``start`` a plane's sloping
        sides stay deeper than ``level`` (``side_run``)."""
        near = level * self.side_run / self.depth
        steps = 40
        for step in range(1, steps + 1):
            t = step / steps
            point = Point2D(e.x + (start.x - e.x) * t, e.y + (start.y - e.y) * t)
            if _distance_to(self.line, point) <= near:
                # Between the last sample still that far in and this one.
                return (step - 0.5) / steps
        return 1.0

    def along_plane(self, point: Point2D) -> float:
        """Return how far ``point`` lies along ``plane_axis``."""
        return point.x * self.plane_axis[0] + point.y * self.plane_axis[1]

    def _locate(self, point: Point2D) -> tuple[float, float] | None:
        """Return how far along the rulings ``point`` lies (0 at the edge,
        1 at the line) and the fade there (``_fades``, between the two
        rulings either side), or ``None`` outside the relief."""
        for k in range(len(self.edge) - 1):
            quad = (self.edge[k], self.edge[k + 1], self.line[k + 1], self.line[k])
            if not _in_box(point, quad) or not point_in_polygon(point, quad):
                continue
            fades = self._fades()
            t0, d0 = _along(self.edge[k], self.line[k], point)
            t1, d1 = _along(self.edge[k + 1], self.line[k + 1], point)
            if d0 + d1 <= 1e-12:
                return min(1.0, max(0.0, t0)), fades[k]
            t = (t0 * d1 + t1 * d0) / (d0 + d1)
            fade = (fades[k] * d1 + fades[k + 1] * d0) / (d0 + d1)
            return min(1.0, max(0.0, t)), fade
        return None

    def depth_at(self, point: Point2D) -> float:
        """Return the relief's depth below the back face at ``point``."""
        located = self._locate(point)
        if located is None:
            return 0.0
        t, fade = located
        return self._profile_depth(t, point, fade)

    def machining_depth(self, point: Point2D, slot: float) -> float:
        """Return the depth a cutter takes at ``point``.

        On the relief, its depth; past the edge, in the outline's slot
        (``slot`` wide, where the cutter finishes the edge from), the
        depth at the nearest edge point, and nothing further out.
        """
        located = self._locate(point)
        if located is not None:
            t, fade = located
            return self._profile_depth(t, point, fade)
        nearest, distance, outside = _nearest_on(self.edge, point, self._clockwise)
        if distance > slot or not outside:
            return 0.0
        # The fade of the edge's sample nearest there.
        k = min(
            range(len(self.edge)),
            key=lambda i: math.dist(_xy(self.edge[i]), _xy(nearest)),
        )
        return self._profile_depth(0.0, nearest, self._fades()[k])

    @property
    def _clockwise(self) -> bool:
        region = self.region()
        area = sum(
            a.x * b.y - b.x * a.y
            for a, b in zip(region, (*region[1:], region[0]), strict=True)
        )
        return area < 0.0

    def cuts(self, point: Point2D) -> bool:
        """Whether the relief cuts at ``point``."""
        return self.depth_at(point) > 0.0

    def max_depth(self, outline: Sequence[Point2D]) -> float:
        """Return the deepest the relief goes."""
        return self.depth

    def inner_edge(self) -> tuple[Point2D, ...]:
        """Return where the relief meets the face (its line)."""
        return self.line

    def region(self, outline: Sequence[Point2D] = ()) -> tuple[Point2D, ...]:
        """Return the relieved area: the edge stretch and the line."""
        return (*self.edge, *reversed(self.line))

    def level_regions(self, level: float) -> tuple[tuple[Point2D, ...], ...]:
        """Return the area where the relief is deeper than ``level``, as
        the one region (see ``level_region``)."""
        return (self.level_region(level),)

    def level_region(self, level: float) -> tuple[Point2D, ...]:
        """Return the area where the relief is deeper than ``level``.

        Along each ruling, from ``CONTOUR_WASTE`` past the edge (into the
        waste) in to where it passes that depth (the wall, for a flat
        profile); rulings no deeper than ``level`` at the edge are left
        out. Where the edge turns sharply in (a cutaway's corner by the
        neck) the points past it would cross: the loop they make is left
        out, so the area stays one simple outline.
        """
        inner: list[Point2D] = []
        outer: list[Point2D] = []
        clockwise = self._clockwise
        fades = self._fades()
        for k, (e, start) in enumerate(zip(self.edge, self.line, strict=True)):
            if self._profile_depth(0.0, e, fades[k]) <= level:
                continue
            if self.profile == "flat":
                t = 1.0
            elif self.profile == "plane":
                deep, face = self.plane
                there = face + (level / self.depth) * (deep - face)
                at_edge, at_line = self.along_plane(e), self.along_plane(start)
                t = (
                    1.0
                    if math.isclose(at_line, at_edge)
                    else (there - at_edge) / (at_line - at_edge)
                )
                t = min(1.0, max(0.0, t))
                if self.side_run:
                    t = min(t, self._side_reach(e, start, level))
            else:
                t = 1.0 - level / (self.depth * fades[k])
            inner.append(Point2D(e.x + (start.x - e.x) * t, e.y + (start.y - e.y) * t))
            out = _outward(self.edge, k, clockwise)
            outer.append(
                Point2D(e.x + out.x * CONTOUR_WASTE, e.y + out.y * CONTOUR_WASTE)
            )
        return (*inner, *reversed(_without_loops(outer)))


Contour = ContourCut | HeelRelief
"""A bevel or relief cut into a face: an arm contour, a belly cut, a heel relief."""


def _stretch_between(
    name: str, outline: Sequence[Point2D], line: Sequence[Point2D]
) -> list[Point2D]:
    """Return the outline stretch between ``line``'s ends, from the first.

    The ends are taken onto the outline where it passes nearest them (on
    a side, not only at a corner, so a line ending on the centreline has
    its relief end there too); of the two ways round between them, the
    one whose middle is nearer the line's middle.
    """
    points = list(outline)
    count = len(points)

    def nearest(p: Point2D) -> tuple[int, Point2D]:
        # The side from points[i] to the next that passes nearest, and the
        # point on it.
        best: tuple[float, int, Point2D] = (math.inf, 0, points[0])
        for i in range(count):
            a, b = points[i], points[(i + 1) % count]
            t, _ = _along(a, b, p)
            t = min(1.0, max(0.0, t))
            foot = Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)
            distance = math.dist(_xy(foot), _xy(p))
            if distance < best[0]:
                best = (distance, i, foot)
        return best[1], best[2]

    (first, start), (last, end) = nearest(line[0]), nearest(line[-1])
    middle = line[len(line) // 2]
    forward = [
        start,
        *(points[(first + k) % count] for k in range(1, (last - first) % count + 1)),
        end,
    ]
    backward = [
        start,
        *(points[(first - k) % count] for k in range((first - last) % count)),
        end,
    ]
    stretch = min(
        (forward, backward),
        key=lambda way: math.dist(_xy(way[len(way) // 2]), _xy(middle)),
    )
    if len(stretch) < 3:
        raise BodyGeometryError(f"{name} line's ends are too close together.")
    return stretch


def _resample(points: Sequence[Point2D], count: int) -> tuple[Point2D, ...]:
    """Return ``count`` points evenly spaced along the polyline ``points``."""
    lengths = [0.0]
    for a, b in zip(points, points[1:], strict=False):
        lengths.append(lengths[-1] + math.dist(_xy(a), _xy(b)))
    total = lengths[-1]
    out: list[Point2D] = []
    index = 0
    for k in range(count):
        target = total * k / (count - 1)
        while index < len(points) - 2 and lengths[index + 1] < target:
            index += 1
        a, b = points[index], points[index + 1]
        span = lengths[index + 1] - lengths[index]
        t = 0.0 if span <= 0.0 else (target - lengths[index]) / span
        out.append(Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t))
    return tuple(out)


def _distance_to(polyline: Sequence[Point2D], point: Point2D) -> float:
    """Return the distance from ``point`` to the open ``polyline``."""
    best = math.inf
    for a, b in zip(polyline, polyline[1:], strict=False):
        t, _ = _along(a, b, point)
        t = min(1.0, max(0.0, t))
        foot = (a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)
        best = min(best, math.dist(foot, _xy(point)))
    return best


def _densified(polygon: Sequence[Point2D], step: float) -> list[Point2D]:
    """Return the closed ``polygon`` with a point at least every ``step``."""
    points: list[Point2D] = []
    for a, b in zip(polygon, (*polygon[1:], polygon[0]), strict=True):
        count = max(1, math.ceil(math.dist(_xy(a), _xy(b)) / step))
        points += [
            Point2D(a.x + (b.x - a.x) * k / count, a.y + (b.y - a.y) * k / count)
            for k in range(count)
        ]
    return points


def _in_box(point: Point2D, polygon: Sequence[Point2D]) -> bool:
    xs = [p.x for p in polygon]
    ys = [p.y for p in polygon]
    return min(xs) <= point.x <= max(xs) and min(ys) <= point.y <= max(ys)


def _along(a: Point2D, b: Point2D, point: Point2D) -> tuple[float, float]:
    """Return how far along ``a``→``b`` ``point`` projects, and its distance off it."""
    ex, ey = b.x - a.x, b.y - a.y
    size = ex * ex + ey * ey
    if size <= 0.0:
        return 0.0, math.dist(_xy(a), _xy(point))
    wx, wy = point.x - a.x, point.y - a.y
    return (wx * ex + wy * ey) / size, abs(wx * ey - wy * ex) / math.sqrt(size)


def _without_loops(points: Sequence[Point2D]) -> list[Point2D]:
    """Return the open polyline ``points`` with every loop it makes cut out.

    Where two of its spans cross, the points between them go and the
    crossing takes their place.
    """
    kept = list(points)
    crossed = True
    while crossed:
        crossed = False
        for i in range(len(kept) - 3):
            for j in range(len(kept) - 2, i + 1, -1):
                meet = _crossing(kept[i], kept[i + 1], kept[j], kept[j + 1])
                if meet is not None:
                    kept[i + 1 : j + 1] = [meet]
                    crossed = True
                    break
            if crossed:
                break
    return kept


def _crossing(a: Point2D, b: Point2D, c: Point2D, d: Point2D) -> Point2D | None:
    """Return where the spans ``a``-``b`` and ``c``-``d`` cross, if they do."""
    rx, ry = b.x - a.x, b.y - a.y
    sx, sy = d.x - c.x, d.y - c.y
    denominator = rx * sy - ry * sx
    if abs(denominator) < 1e-12:
        return None
    qx, qy = c.x - a.x, c.y - a.y
    t = (qx * sy - qy * sx) / denominator
    u = (qx * ry - qy * rx) / denominator
    if 0.0 < t < 1.0 and 0.0 < u < 1.0:
        return Point2D(a.x + rx * t, a.y + ry * t)
    return None


def _outward(edge: Sequence[Point2D], k: int, clockwise: bool) -> Point2D:
    """Return the unit normal at ``edge[k]`` pointing away from the relief."""
    a = edge[max(0, k - 1)]
    b = edge[min(len(edge) - 1, k + 1)]
    tx, ty = b.x - a.x, b.y - a.y
    size = math.hypot(tx, ty) or 1.0
    # The relief lies left of the edge's direction when it runs counter-
    # clockwise round it (edge forward, line back).
    nx, ny = (ty / size, -tx / size) if not clockwise else (-ty / size, tx / size)
    return Point2D(nx, ny)


def _nearest_on(
    edge: Sequence[Point2D], point: Point2D, clockwise: bool
) -> tuple[Point2D, float, bool]:
    """Return the nearest point on the polyline ``edge``, its distance, and
    whether ``point`` lies on the side away from the relief."""
    best = (edge[0], math.inf, False)
    for k in range(len(edge) - 1):
        a, b = edge[k], edge[k + 1]
        t, _ = _along(a, b, point)
        t = min(1.0, max(0.0, t))
        c = Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)
        distance = math.dist(_xy(c), _xy(point))
        if distance < best[1]:
            cross = (b.x - a.x) * (point.y - a.y) - (b.y - a.y) * (point.x - a.x)
            outside = cross < 0.0 if not clockwise else cross > 0.0
            best = (c, distance, outside)
    return best


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


def _run_out(s: float, arc: Sequence[float], reaches: Sequence[float]) -> float:
    """Return the share of a drawn bevel's reach kept at arc ``s``.

    Eased (a smoothstep) from none at either end of its stretch to all of
    it as far along the edge from there as the bevel reaches in at that
    end; all of it near an end it reaches in by nothing at (where its line
    meets the edge square).
    """
    kept = 1.0
    for end, reach in ((arc[0], reaches[0]), (arc[-1], reaches[-1])):
        if reach <= 0.0:
            continue
        t = min(1.0, abs(s - end) / reach)
        kept *= t * t * (3.0 - 2.0 * t)
    return kept

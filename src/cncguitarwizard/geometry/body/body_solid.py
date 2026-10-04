"""Complete parametric solid-body assembly."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..exceptions import BodyGeometryError
from ..primitives import Point2D, nudge_inward, point_in_polygon
from .carve import CarvedTop
from .edges import ContourCut, EdgeProfile
from .engraving import Engraving
from .hardware import BridgeMounting, Cavity, DrilledHole, JackHole, RearCavity
from .outline import BodyOutline, TracedOutline

Outline = BodyOutline | TracedOutline

EDGE_RIM_TOLERANCE = 1.0
"""How far a roundover may lower a cavity's rim, in mm (a pickup ring or
cover hides it)."""


def rim_drop(radius: float, inset: float) -> float:
    """Return how far below the face a roundover of ``radius`` is at ``inset``.

    ``inset`` is measured in from the edge; past the radius the face is
    untouched.
    """
    if radius <= 0.0 or inset >= radius:
        return 0.0
    return radius - math.sqrt(radius**2 - (radius - inset) ** 2)


def max_radius_for(inset: float) -> float:
    """Return the largest roundover that lowers a rim at ``inset`` by the tolerance.

    Solving ``rim_drop(r, inset) = t`` for ``r`` gives
    ``r = t + inset + sqrt(2 t inset)``.
    """
    t = EDGE_RIM_TOLERANCE
    return t + inset + math.sqrt(2.0 * t * max(inset, 0.0))


CARVE_WALL = 3.0
"""Least wood a carved top leaves over a cavity routed from the back, in mm."""


@dataclass(frozen=True, slots=True)
class BodySolid:
    """A flat slab body with every routed cavity it needs to play.

    Combines the outline with the neck pocket, both pickup routes, the
    bridge mounting, the rear control and switch cavities, and the jack
    bore, and cross-checks that every cavity both fits within the
    body's thickness and falls inside the outline's own bounding box.
    The faces are flat unless ``contours`` bevel them, and the edges
    square unless ``top_edge`` / ``back_edge`` round them over or cut a
    binding channel.

    Args:
        outline: The body's plan-view silhouette.
        thickness: Overall slab thickness in millimetres.
        neck_pocket: Recess that receives the neck heel, or ``None`` on a
            neck-through body (the neck blank runs on through it).
        bridge_pickup: Route for the bridge-position pickup, or ``None``.
        neck_pickup: Route for the neck-position pickup, or ``None``.
        bridge_mounting: Kahler-style bridge cavity and pivot holes.
        control_cavity: Optional rear-routed cavity for the
            potentiometers, with its cover recess.
        jack_hole: Bore for the edge-mounted output jack.
        switch_cavity: Optional rear-routed cavity for the pickup
            selector, with its cover recess.
        battery_cavity: Optional rear-routed pocket for a 9 V battery,
            with its cover recess.
        extra_cavities: Any further top-routed pockets not covered by
            the named fields above — for example, a traced
            baseplate-clearance cutout that sits alongside the bridge
            mounting.
        holes: Vertical holes drilled from the top face — pot and
            switch shaft holes, pickup-screw clearance recesses.
        control_top_cavities: Electronics routed from the top — a
            control plate's recess and the deeper cavity inside it; cut
            in their own program with the top-face screw spots.
        control_back_marks: Cover-screw spots drilled from the back.
        control_top_marks: Cover-screw spots drilled from the top.
        rear_holes: Vertical holes drilled from the back face, their
            depth measured from the back — the neck-bolt ferrule
            counterbores and the bolt holes through to the neck pocket.
        through_cavities: Routes cut from the top that open into a rear
            cavity (a tremolo's sustain-block route into its spring
            cavity) or clean through the body; exempt from the floor and
            break-through checks by design, but each must actually reach
            the back face or a rear cavity it overlaps.
        extra_rear_cavities: Further rear-routed cavities with cover
            recesses beyond the named electronics cavities — a tremolo
            spring cavity, for example.
        top_edge: Roundover or binding channel on the top edge.
        back_edge: Roundover or binding channel on the back edge.
        contours: Planar bevels — an arm contour on the top, a belly cut
            on the back.
        truss_rod_access: A notch out of the neck pocket's tail wall so a
            heel-adjusted truss rod's spoke wheel can be turned; it starts
            inside the pocket, so its overlap with it is allowed.
        carved_top: The top arched from a flat plateau down to a flat rim
            (``CarvedTop``), or ``None`` for a flat top. Every rear cavity
            must leave ``CARVE_WALL`` of wood under it.
        engraving: Decorative lines engraved into the top, or ``None``;
            it must leave half the slab.
        edge_outline: The outline the edge finishes (roundover, binding)
            follow, if not ``outline``: on one part of a neck-through body,
            the body's outline carried on past its glue lines into the
            part's waste, so its glue faces stay square.
        checked: ``False`` for one part of a neck-through body, cut from
            its own blank: the whole body was checked, and the part carries
            every feature that reaches it, past its glue lines too.

    Raises:
        BodyGeometryError: If any cavity is deeper than the slab, falls
            outside the outline (the neck pocket may open onto the horn
            gap, but its tail-ward wall must lie in body wood), a rear
            cavity would break through into a top cavity above it, or
            a hole is deeper than the slab or centred outside the
            outline.
    """

    outline: Outline
    thickness: float
    neck_pocket: Cavity | None
    bridge_pickup: Cavity | None
    neck_pickup: Cavity | None
    bridge_mounting: BridgeMounting
    jack_hole: JackHole
    control_cavity: RearCavity | None = None
    switch_cavity: RearCavity | None = None
    battery_cavity: RearCavity | None = None
    extra_cavities: tuple[Cavity, ...] = ()
    holes: tuple[DrilledHole, ...] = ()
    through_cavities: tuple[Cavity, ...] = ()
    extra_rear_cavities: tuple[RearCavity, ...] = ()
    rear_holes: tuple[DrilledHole, ...] = ()
    control_top_cavities: tuple[Cavity, ...] = ()
    control_back_marks: tuple[DrilledHole, ...] = ()
    control_top_marks: tuple[DrilledHole, ...] = ()
    top_edge: EdgeProfile = field(default_factory=EdgeProfile)
    back_edge: EdgeProfile = field(default_factory=EdgeProfile)
    contours: tuple[ContourCut, ...] = ()
    truss_rod_access: Cavity | None = None
    engraving: Engraving | None = None
    carved_top: CarvedTop | None = None
    edge_outline: tuple[Point2D, ...] = ()
    checked: bool = True

    def __post_init__(self) -> None:
        """Cross-check every cavity against the slab and outline bounds."""
        if not math.isfinite(self.thickness) or self.thickness <= 0.0:
            raise BodyGeometryError("Body thickness must be finite and positive.")
        if not self.checked:
            return
        if self.carved_top is not None:
            self._check_carve()
        if self.engraving is not None and self.engraving.depth >= self.thickness / 2.0:
            raise BodyGeometryError(
                "The engraving must be shallower than half the body's thickness."
            )
        for hole in (
            *self.holes,
            *self.rear_holes,
            *self.control_back_marks,
            *self.control_top_marks,
        ):
            if hole.depth > self.thickness:
                raise BodyGeometryError(
                    f"{hole.name} must not be deeper than the body."
                )
            if not point_in_polygon(hole.center, self.outline.points):
                raise BodyGeometryError(f"{hole.name} falls outside the body outline.")

        for cavity in self._cavities():
            if cavity in self.through_cavities:
                continue
            if cavity.depth >= self.thickness:
                raise BodyGeometryError(
                    f"{cavity.name} depth must leave material beneath its floor."
                )
        for cavity in self.through_cavities:
            if cavity.depth < self.thickness and not self._reaches_rear_cavity(cavity):
                raise BodyGeometryError(
                    f"{cavity.name} is a through route and must reach the back "
                    "face or a rear cavity beneath it."
                )
        # Top cavities are separate features; two that overlap in plan
        # would merge into one unintended pocket (typically a bridge
        # feature that has been moved onto a body feature by a scale
        # or fret-count change). Two exceptions: a through route sits
        # inside its recess by design, and a *step* — a deeper cavity
        # whose outline lies entirely inside a shallower one — is how a
        # recess with two floor levels is described (a tremolo recess
        # cut over its whole footprint first, then deepened behind the
        # studs), so its walls stay continuous instead of two pockets
        # meeting at a wall.
        top_cavities = tuple(
            cavity
            for cavity in self.top_cavities
            if cavity not in self.through_cavities
        )
        for index, first in enumerate(top_cavities):
            for second in top_cavities[index + 1 :]:
                if not (
                    first.min_x < second.max_x
                    and second.min_x < first.max_x
                    and first.min_y < second.max_y
                    and second.min_y < first.max_y
                ) or not outlines_overlap(first.outline, second.outline):
                    continue
                if {id(first), id(second)} == {
                    id(self.neck_pocket),
                    id(self.truss_rod_access),
                }:
                    continue
                if self.is_step(second, first) or self.is_step(first, second):
                    continue
                if self.encloses(first, second) or self.encloses(second, first):
                    raise BodyGeometryError(
                        f"{first.name} overlaps {second.name}: nested, but the "
                        "inner one is not deeper, so not a step."
                    )
                raise BodyGeometryError(f"{first.name} overlaps {second.name}.")
        # Each rear cavity closes with its own plate, so two cover
        # recesses must not overlap: the plates would sit on each other.
        rears = self.rear_cavities
        for index, rear in enumerate(rears):
            for other in rears[index + 1 :]:
                a, b = rear.cover_recess, other.cover_recess
                if (
                    a.min_x < b.max_x
                    and b.min_x < a.max_x
                    and a.min_y < b.max_y
                    and b.min_y < a.max_y
                    and outlines_overlap(a.outline, b.outline)
                ):
                    raise BodyGeometryError(f"{a.name} overlaps {b.name}.")
        # No hole is meant to open into the battery box: a top hole must
        # stop short of its floor (string-through holes would run into
        # it), and a hole from the back must stay off its cover.
        if self.battery_cavity is not None:
            box = self.battery_cavity
            for hole in (*self.holes, *self.rear_holes):
                from_back = hole in self.rear_holes
                for pocket in (box.cavity, box.cover_recess):
                    reaches = from_back or hole.depth + pocket.depth >= self.thickness
                    if reaches and _circle_meets_outline(
                        hole.center_x, hole.center_y, hole.diameter / 2.0, pocket
                    ):
                        raise BodyGeometryError(
                            f"{hole.name} would break into {pocket.name}."
                        )
        # A rear cavity and a top cavity that overlap in plan must
        # together leave wood between their floors, or the two rout
        # into one another.
        for rear in self.rear_cavities:
            for pocket in rear.pockets:
                for top in self.top_cavities:
                    if top in self.through_cavities:
                        continue
                    overlaps = (
                        pocket.min_x < top.max_x
                        and top.min_x < pocket.max_x
                        and pocket.min_y < top.max_y
                        and top.min_y < pocket.max_y
                        and outlines_overlap(pocket.outline, top.outline)
                    )
                    if overlaps and pocket.depth + top.depth >= self.thickness:
                        raise BodyGeometryError(
                            f"{pocket.name} would break through into {top.name}."
                        )
        if self.bridge_mounting.pivot_hole_depth >= self.thickness:
            raise BodyGeometryError(
                "Bridge pivot holes must leave material beneath their floor."
            )
        if self.jack_hole.depth >= self._outline_half_span():
            raise BodyGeometryError("Jack bore must not reach clean through the body.")

        # Testing every one of a cavity's own outline points (not just its
        # bounding-box corners) catches a concave or irregular traced
        # shape poking past the body outline between those corners.
        # Insetting each one very slightly toward the cavity's own
        # centre keeps a cavity that legitimately runs flush against the
        # outline from being rejected by floating-point noise where the
        # ray-casting test's horizontal ray passes through a coincident
        # outline vertex — a real containment failure is never this
        # close.
        #
        # The neck pocket is the one deliberate exception: on a bolt-on
        # body its nut-ward end opens onto the horn gap, so part of its
        # footprint lies outside the wood by design. It only has to
        # reach the body at all — its tail-ward wall must be in wood.
        inset = 0.1
        for cavity in self._cavities():
            test_points = self._inset_outline(cavity, inset)
            if cavity is self.neck_pocket:
                tail_points = [
                    point
                    for point in test_points
                    if point.x >= cavity.max_x - inset * 2.0
                ]
                if not all(
                    point_in_polygon(point, self.outline.points)
                    for point in tail_points
                ):
                    raise BodyGeometryError(
                        f"{cavity.name} tail-ward wall falls outside the body outline."
                    )
                continue
            if not all(
                point_in_polygon(point, self.outline.points) for point in test_points
            ):
                raise BodyGeometryError(
                    f"{cavity.name} falls outside the body outline."
                )
        for pivot_hole in self.bridge_mounting.pivot_holes:
            if not point_in_polygon(pivot_hole, self.outline.points):
                raise BodyGeometryError(
                    "Bridge pivot hole falls outside the body outline."
                )
        self._validate_edges()

    def _check_carve(self) -> None:
        """Refuse a carve that would leave a rear cavity too thin a top."""
        carve = self.carved_top
        assert carve is not None
        if carve.height >= self.thickness / 2.0:
            raise BodyGeometryError(
                "The carved top's depth (body_carve_depth) must be under half the "
                "body's thickness."
            )
        rears = [
            (rear.cavity.name, part)
            for rear in (
                self.control_cavity,
                self.switch_cavity,
                self.battery_cavity,
                *self.extra_rear_cavities,
            )
            if rear is not None
            for part in (rear.cavity, *rear.steps)
        ]
        for name, part in rears:
            for point in part.outline:
                wood = self.thickness - carve.drop_at(point.x, point.y) - part.depth
                if wood < CARVE_WALL - 1e-6:
                    raise BodyGeometryError(
                        f"The carved top leaves {max(wood, 0.0):.1f} mm over the "
                        f"{name.lower()}; lower body_carve_depth or use a thicker "
                        "body."
                    )

    def _validate_edges(self) -> None:
        """Check the edge finishes and bevels against the cavities."""
        half = self.thickness / 2.0
        outline = self.outline.points
        for face, edge in (("Top", self.top_edge), ("Back", self.back_edge)):
            if edge.reach > half - 2.0:
                raise BodyGeometryError(
                    f"{face} edge finish reaches too deep for a "
                    f"{self.thickness:g} mm body."
                )
        # A roundover lowers the rim of a cavity near the edge by the
        # fillet's depth at that inset; up to EDGE_RIM_TOLERANCE is hidden
        # under a pickup ring or cover. A binding channel must leave a
        # wall of wood between itself and the cavity.
        faces: tuple[tuple[str, EdgeProfile, tuple[Cavity, ...]], ...] = (
            (
                "top",
                self.top_edge,
                tuple(c for c in self.top_cavities if c is not self.neck_pocket),
            ),
            (
                "back",
                self.back_edge,
                tuple(rear.cover_recess for rear in self.rear_cavities),
            ),
        )
        for face, edge, cavities in faces:
            if edge.radius <= 0.0 and not edge.has_binding:
                continue
            for cavity in cavities:
                gap = min(_distance_to_outline(p, outline) for p in cavity.outline)
                if edge.has_binding and gap < edge.binding_width + 1.0:
                    raise BodyGeometryError(
                        f"{cavity.name} is {gap:.1f} mm from the edge; the {face} "
                        f"binding channel ({edge.binding_width:g} mm) needs "
                        f"{edge.binding_width + 1.0:g} mm."
                    )
                drop = rim_drop(edge.radius, gap)
                if drop > EDGE_RIM_TOLERANCE:
                    raise BodyGeometryError(
                        f"{cavity.name} is {gap:.1f} mm from the edge, so the "
                        f"{edge.radius:g} mm {face} roundover would lower its rim "
                        f"by {drop:.1f} mm; use a radius under "
                        f"{max_radius_for(gap):.1f} mm or move the cavity."
                    )
        # A roundover runs on down from a contour's floor; each face can
        # only be machined to the body's middle.
        for contour in self.contours:
            edge = self.top_edge if contour.face == "top" else self.back_edge
            reach = contour.depth + edge.radius
            if edge.radius > 0.0 and reach > half:
                raise BodyGeometryError(
                    f"{contour.name} ({contour.depth:g} mm) and the "
                    f"{edge.radius:g} mm {contour.face} roundover reach "
                    f"{reach:g} mm into the {self.thickness:g} mm body; from the "
                    f"{contour.face} it can be machined to {half:g} mm, so keep "
                    "their sum at most that."
                )
        for contour in self.contours:
            deepest = contour.max_depth(outline)
            if deepest > half - 2.0:
                raise BodyGeometryError(
                    f"{contour.name} is {deepest:.1f} mm deep; keep it under "
                    f"{half - 2.0:g} mm."
                )
            same_face: tuple[Cavity, ...]
            if contour.face == "top":
                same_face = self.top_cavities
                other_face = tuple(
                    pocket for rear in self.rear_cavities for pocket in rear.pockets
                )
                holes = (*self.holes, *self.control_top_marks)
            else:
                same_face = tuple(
                    pocket for rear in self.rear_cavities for pocket in rear.pockets
                )
                other_face = self.top_cavities
                holes = (*self.rear_holes, *self.control_back_marks)
            for cavity in same_face:
                if any(contour.depth_at(p) > 0.0 for p in cavity.outline):
                    raise BodyGeometryError(f"{contour.name} cuts into {cavity.name}.")
            for hole in holes:
                if contour.depth_at(hole.center) > 0.0:
                    raise BodyGeometryError(f"{contour.name} cuts into {hole.name}.")
            # A cavity routed from the other face must keep 3 mm of wood
            # under the bevel.
            for cavity in other_face:
                if cavity in self.through_cavities:
                    continue
                bevel = max(contour.depth_at(p) for p in cavity.outline)
                if bevel > 0.0 and cavity.depth + bevel > self.thickness - 3.0:
                    raise BodyGeometryError(
                        f"{contour.name} leaves too little wood over {cavity.name}."
                    )

    @staticmethod
    def encloses(outer: Cavity, inner: Cavity) -> bool:
        """Return whether ``inner``'s outline lies inside ``outer``'s.

        Walls the two share are tolerated: each inner point is nudged
        very slightly into the inner cavity first.
        """
        return all(
            point_in_polygon(point, outer.outline)
            for point in nudge_inward(inner.outline, 0.05)
        )

    @staticmethod
    def is_step(inner: Cavity, outer: Cavity) -> bool:
        """Return whether ``inner`` is a deeper floor inside ``outer``."""
        return inner.depth > outer.depth and BodySolid.encloses(outer, inner)

    def step_start_depth(self, cavity: Cavity) -> float:
        """Return the depth already cleared above ``cavity`` by the cavities
        it steps down from, or 0 when it starts at the top face."""
        return max(
            (
                other.depth
                for other in self.top_cavities
                if other is not cavity and self.is_step(cavity, other)
            ),
            default=0.0,
        )

    def _reaches_rear_cavity(self, cavity: Cavity) -> bool:
        """Return whether a top route opens into some rear pocket under it."""
        for rear in self.rear_cavities:
            for pocket in rear.pockets:
                overlaps = (
                    pocket.min_x < cavity.max_x
                    and cavity.min_x < pocket.max_x
                    and pocket.min_y < cavity.max_y
                    and cavity.min_y < pocket.max_y
                )
                if overlaps and pocket.depth + cavity.depth >= self.thickness:
                    return True
        return False

    @staticmethod
    def _inset_outline(cavity: Cavity, inset: float) -> list[Point2D]:
        """Return the cavity outline with each point nudged toward its centre."""
        center_x = (cavity.min_x + cavity.max_x) / 2.0
        center_y = (cavity.min_y + cavity.max_y) / 2.0
        test_points: list[Point2D] = []
        for point in cavity.outline:
            dx, dy = center_x - point.x, center_y - point.y
            length = math.hypot(dx, dy)
            if length == 0.0:
                test_points.append(point)
                continue
            test_points.append(
                Point2D(
                    point.x + dx / length * inset,
                    point.y + dy / length * inset,
                )
            )
        return test_points

    @property
    def rear_cavities(self) -> tuple[RearCavity, ...]:
        """Return every rear-routed cavity actually present on this body."""
        return tuple(
            rear
            for rear in (
                self.control_cavity,
                self.switch_cavity,
                self.battery_cavity,
                *self.extra_rear_cavities,
            )
            if rear is not None
        )

    @property
    def edge_points(self) -> tuple[Point2D, ...]:
        """Return the outline the edge finishes follow (see ``edge_outline``)."""
        return self.edge_outline or self.outline.points

    @property
    def top_cavities(self) -> tuple[Cavity, ...]:
        """Return every cavity cut down from the top face, through routes last."""
        cavities: list[Cavity] = (
            [self.neck_pocket] if self.neck_pocket is not None else []
        )
        if self.truss_rod_access is not None:
            cavities.append(self.truss_rod_access)
        cavities.extend(
            pickup
            for pickup in (self.neck_pickup, self.bridge_pickup)
            if pickup is not None
        )
        if self.bridge_mounting.sustain_block_cavity is not None:
            cavities.append(self.bridge_mounting.sustain_block_cavity)
        cavities.extend(self.extra_cavities)
        cavities.extend(self.control_top_cavities)
        cavities.extend(self.through_cavities)
        return tuple(cavities)

    def _cavities(self) -> tuple[Cavity, ...]:
        """Return every plan-view cavity outline to depth- and bounds-check."""
        cavities = list(self.top_cavities)
        for rear in self.rear_cavities:
            cavities.extend(rear.pockets)
            cavities.append(rear.cover_recess)
        return tuple(cavities)

    def _outline_half_span(self) -> float:
        """Return half the outline's lateral span, as a jack-depth cap."""
        outline_min_y = min(point.y for point in self.outline.points)
        outline_max_y = max(point.y for point in self.outline.points)
        return (outline_max_y - outline_min_y) / 2.0


def _distance_to_outline(point: Point2D, outline: tuple[Point2D, ...]) -> float:
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


def outlines_overlap(first: tuple[Point2D, ...], second: tuple[Point2D, ...]) -> bool:
    """Return whether two closed outlines share any area.

    Their bounding boxes may overlap without the shapes doing so (two
    pickups turned for fanned frets), so this tests the edges themselves:
    two edges crossing, or one outline lying inside the other.
    """

    def cross(o: Point2D, a: Point2D, b: Point2D) -> float:
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)

    edges_first = list(zip(first, (*first[1:], first[0]), strict=True))
    edges_second = list(zip(second, (*second[1:], second[0]), strict=True))
    for a, b in edges_first:
        for c, d in edges_second:
            if (
                max(a.x, b.x) < min(c.x, d.x)
                or max(c.x, d.x) < min(a.x, b.x)
                or max(a.y, b.y) < min(c.y, d.y)
                or max(c.y, d.y) < min(a.y, b.y)
            ):
                continue
            d1, d2 = cross(c, d, a), cross(c, d, b)
            d3, d4 = cross(a, b, c), cross(a, b, d)
            if d1 * d2 <= 0.0 and d3 * d4 <= 0.0:
                return True
    return point_in_polygon(first[0], second) or point_in_polygon(second[0], first)


def _circle_meets_outline(x: float, y: float, radius: float, cavity: Cavity) -> bool:
    """Return whether a hole of ``radius`` at (x, y) opens into ``cavity``."""
    centre = Point2D(x, y)
    return (
        point_in_polygon(centre, cavity.outline)
        or _distance_to_outline(centre, cavity.outline) < radius
    )

"""Complete parametric solid-body assembly."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..exceptions import BodyGeometryError
from ..primitives import Point2D, nudge_inward, point_in_polygon
from .hardware import BridgeMounting, Cavity, DrilledHole, JackHole, RearCavity
from .outline import BodyOutline, TracedOutline

Outline = BodyOutline | TracedOutline


@dataclass(frozen=True, slots=True)
class BodySolid:
    """A flat slab body with every routed cavity it needs to play.

    Combines the outline with the neck pocket, both pickup routes, the
    bridge mounting, the rear control and switch cavities, and the jack
    bore, and cross-checks that every cavity both fits within the
    body's thickness and falls inside the outline's own bounding box.
    This is the first, un-contoured pass: arm and belly bevels are not
    modelled yet, so the top and back faces are both flat.

    Args:
        outline: The body's plan-view silhouette.
        thickness: Overall slab thickness in millimetres.
        neck_pocket: Recess that receives the neck heel.
        bridge_pickup: Route for the bridge-position humbucker.
        neck_pickup: Route for the neck-position humbucker.
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
        through_cavities: Routes cut from the top that open into a rear
            cavity (a tremolo's sustain-block route into its spring
            cavity) or clean through the body; exempt from the floor and
            break-through checks by design, but each must actually reach
            the back face or a rear cavity it overlaps.
        extra_rear_cavities: Further rear-routed cavities with cover
            recesses beyond the named electronics cavities — a tremolo
            spring cavity, for example.

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
    neck_pocket: Cavity
    bridge_pickup: Cavity
    neck_pickup: Cavity
    bridge_mounting: BridgeMounting
    jack_hole: JackHole
    control_cavity: RearCavity | None = None
    switch_cavity: RearCavity | None = None
    battery_cavity: RearCavity | None = None
    extra_cavities: tuple[Cavity, ...] = ()
    holes: tuple[DrilledHole, ...] = ()
    through_cavities: tuple[Cavity, ...] = ()
    extra_rear_cavities: tuple[RearCavity, ...] = ()

    def __post_init__(self) -> None:
        """Cross-check every cavity against the slab and outline bounds."""
        if not math.isfinite(self.thickness) or self.thickness <= 0.0:
            raise BodyGeometryError("Body thickness must be finite and positive.")
        for hole in self.holes:
            if hole.depth > self.thickness:
                raise BodyGeometryError(
                    f"{hole.name} must not be deeper than the body."
                )
            if not point_in_polygon(hole.center, self.outline.points):
                raise BodyGeometryError(
                    f"{hole.name} falls outside the body outline."
                )

        for cavity in self._cavities():
            if cavity in self.through_cavities:
                continue
            if cavity.depth >= self.thickness:
                raise BodyGeometryError(
                    f"{cavity.name} depth must leave material beneath its "
                    "floor."
                )
        for cavity in self.through_cavities:
            if cavity.depth < self.thickness and not self._reaches_rear_cavity(
                cavity
            ):
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
                ):
                    continue
                if self.is_step(second, first) or self.is_step(first, second):
                    continue
                if self.encloses(first, second) or self.encloses(second, first):
                    raise BodyGeometryError(
                        f"{first.name} overlaps {second.name}: nested, but the "
                        "inner one is not deeper, so not a step."
                    )
                raise BodyGeometryError(
                    f"{first.name} overlaps {second.name}."
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
            raise BodyGeometryError(
                "Jack bore must not reach clean through the body."
            )

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
                        f"{cavity.name} tail-ward wall falls outside the "
                        "body outline."
                    )
                continue
            if not all(
                point_in_polygon(point, self.outline.points)
                for point in test_points
            ):
                raise BodyGeometryError(
                    f"{cavity.name} falls outside the body outline."
                )
        for pivot_hole in self.bridge_mounting.pivot_holes:
            if not point_in_polygon(pivot_hole, self.outline.points):
                raise BodyGeometryError(
                    "Bridge pivot hole falls outside the body outline."
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
    def top_cavities(self) -> tuple[Cavity, ...]:
        """Return every cavity cut down from the top face, through routes last."""
        cavities = [self.neck_pocket, self.neck_pickup, self.bridge_pickup]
        if self.bridge_mounting.sustain_block_cavity is not None:
            cavities.append(self.bridge_mounting.sustain_block_cavity)
        cavities.extend(self.extra_cavities)
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

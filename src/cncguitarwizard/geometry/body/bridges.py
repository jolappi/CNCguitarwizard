"""Interchangeable bridge hardware: what each bridge needs cut into the body.

A bridge is described by a small frozen dataclass of dimensions (a
*spec*). Asking the spec for its ``hardware`` at a given scale length and
body thickness yields every body feature that bridge requires — pivot or
post holes, top routes, routes that pass clean through into a rear cavity,
rear cavities with their cover recesses — ready for ``BodySolid``.

The Floyd Rose routing follows the manufacturer's own routing diagrams
(six and seven strings; the eight-string's is derived from them) and the
Kahler's seven- and eight-string cutout widens as Kahler's installation
sheets do; the other bridges' dimensions are labelled, adjustable
starting values rather than verified templates — measure the real
hardware before cutting.
All longitudinal offsets are measured from the scale-length line (the
nominal saddle/intonation line) toward the tail, so a bridge stays on the
scale whatever the neck does.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields, replace
from typing import Any, Literal, NamedTuple

from ..exceptions import BodyGeometryError
from ..primitives import Point2D, Point3D, rounded_polygon_points
from .hardware import (
    BridgeMounting,
    Cavity,
    DrilledHole,
    RearCavity,
    RectangularCavity,
    TracedCavity,
)


@dataclass(frozen=True, slots=True)
class SideHole:
    """A hole drilled by hand at an angle, modelled.

    A router cannot drill sideways (a tremolo claw's screws into its
    cavity's wall) or slanting (a tilted neck plate's bolts, square to
    their bevel); the hole is in the model (FreeCAD, the plan view, the
    DXF) so its place is seen and checked. The bit meets the wood at
    ``start``, on the wall, and stops at ``end``; heights are above the
    back face.

    Args:
        name: ``"Trem claw screw 1 hole"``.
        start: Where the bit meets the wood.
        end: Where the hole ends.
        diameter: The bit's diameter.
        drilled_from: The cavity it is drilled from.
        opens_into: The cavity it opens into at ``end`` (a neck bolt's
            into the neck pocket), or empty when it ends in the wood.

    Raises:
        BodyGeometryError: For a non-positive diameter or a hole of no
            length.
    """

    name: str
    start: Point3D
    end: Point3D
    diameter: float
    drilled_from: str
    opens_into: str = ""

    def __post_init__(self) -> None:
        """Reject a hole of no size."""
        if not math.isfinite(self.diameter) or self.diameter <= 0.0:
            raise BodyGeometryError(f"{self.name} needs a positive diameter.")
        if self.length <= 0.0:
            raise BodyGeometryError(f"{self.name} needs a length.")

    @property
    def length(self) -> float:
        """The hole's length."""
        return math.dist(
            (self.start.x, self.start.y, self.start.z),
            (self.end.x, self.end.y, self.end.z),
        )

    def along(self, distance: float) -> Point3D:
        """Return the point ``distance`` along the hole from its start."""
        t = distance / self.length
        return Point3D(
            self.start.x + (self.end.x - self.start.x) * t,
            self.start.y + (self.end.y - self.start.y) * t,
            self.start.z + (self.end.z - self.start.z) * t,
        )


@dataclass(frozen=True, slots=True)
class BridgeHardware:
    """Everything a bridge adds to the body, in the model frame.

    Args:
        mounting: The bridge reference line and any pivot-stud holes.
        top_cavities: Routes cut down from the top face.
        through_cavities: Routes cut from the top clean through the body
            into a rear cavity (a tremolo's sustain-block route).
        rear_cavities: Rear-routed cavities with cover recesses (a spring
            cavity).
        holes: Vertical holes drilled from the top face.
        notes: Fitting notes for the operator or the FreeCAD reviewer.
        footprint: The outline the bridge itself covers on the top where
            that reaches past its routes (a Kahler's plate), or empty; a
            pickguard keeps clear of it.
        side_holes: Holes drilled sideways by hand into a cavity's wall
            (a tremolo claw's screws), modelled.
    """

    mounting: BridgeMounting
    top_cavities: tuple[Cavity, ...] = ()
    through_cavities: tuple[Cavity, ...] = ()
    rear_cavities: tuple[RearCavity, ...] = ()
    holes: tuple[DrilledHole, ...] = ()
    notes: tuple[str, ...] = ()
    footprint: tuple[Point2D, ...] = ()
    side_holes: tuple[SideHole, ...] = ()


def turned_hardware(
    hardware: BridgeHardware,
    centre: Point2D,
    lean: float,
    turns: Callable[[str], bool] | None = None,
) -> BridgeHardware:
    """Return ``hardware`` turned about ``centre`` to follow a leaning line.

    ``lean`` is the bridge line's ``dx/dy`` (a fanned-fret bridge); every
    cavity and hole turns with it, a cavity becoming a ``TracedCavity`` of
    its turned outline — or, given ``turns``, only the holes whose names it
    accepts (a Tune-o-matic's posts, leaving the stop-bar studs square).
    The mounting's pivot studs do not turn; only the hardtail and the
    Tune-o-matic, which have none, are turned.
    """
    if lean == 0.0:
        return hardware
    angle = -math.atan(lean)
    cosine, sine = math.cos(angle), math.sin(angle)

    def turn(point: Point2D) -> Point2D:
        dx, dy = point.x - centre.x, point.y - centre.y
        return Point2D(
            centre.x + dx * cosine - dy * sine, centre.y + dx * sine + dy * cosine
        )

    def turn_cavity(cavity: Cavity) -> TracedCavity:
        return TracedCavity(
            cavity.name, tuple(turn(point) for point in cavity.outline), cavity.depth
        )

    def turn_hole(hole: DrilledHole) -> DrilledHole:
        if turns is not None and not turns(hole.name):
            return hole
        moved = turn(hole.center)
        return replace(hole, center_x=moved.x, center_y=moved.y)

    return replace(
        hardware,
        top_cavities=tuple(turn_cavity(c) for c in hardware.top_cavities),
        through_cavities=tuple(turn_cavity(c) for c in hardware.through_cavities),
        rear_cavities=tuple(
            RearCavity(
                turn_cavity(rear.cavity),
                turn_cavity(rear.cover_recess),
                tuple(turn_cavity(step) for step in rear.steps),
            )
            for rear in hardware.rear_cavities
        ),
        holes=tuple(turn_hole(hole) for hole in hardware.holes),
        footprint=tuple(turn(point) for point in hardware.footprint),
        side_holes=tuple(
            replace(
                hole,
                start=_lifted(turn(Point2D(hole.start.x, hole.start.y)), hole.start.z),
                end=_lifted(turn(Point2D(hole.end.x, hole.end.y)), hole.end.z),
            )
            for hole in hardware.side_holes
        ),
    )


def _lifted(point: Point2D, z: float) -> Point3D:
    return Point3D(point.x, point.y, z)


def mirrored_hardware(hardware: BridgeHardware) -> BridgeHardware:
    """Return ``hardware`` mirrored across the centreline (Y to -Y).

    For a bridge drawn with its bass side on -Y, on a neck whose bass side
    is +Y.
    """

    def flip(point: Point2D) -> Point2D:
        return Point2D(point.x, -point.y)

    def flip_cavity(cavity: Cavity) -> TracedCavity:
        return TracedCavity(
            cavity.name,
            tuple(flip(point) for point in reversed(cavity.outline)),
            cavity.depth,
        )

    return replace(
        hardware,
        top_cavities=tuple(flip_cavity(c) for c in hardware.top_cavities),
        through_cavities=tuple(flip_cavity(c) for c in hardware.through_cavities),
        rear_cavities=tuple(
            RearCavity(
                flip_cavity(rear.cavity),
                flip_cavity(rear.cover_recess),
                tuple(flip_cavity(step) for step in rear.steps),
            )
            for rear in hardware.rear_cavities
        ),
        holes=tuple(replace(hole, center_y=-hole.center_y) for hole in hardware.holes),
        footprint=tuple(flip(point) for point in reversed(hardware.footprint)),
        side_holes=tuple(
            replace(
                hole,
                start=Point3D(hole.start.x, -hole.start.y, hole.start.z),
                end=Point3D(hole.end.x, -hole.end.y, hole.end.z),
            )
            for hole in hardware.side_holes
        ),
    )


KAHLER_BASEPLATE_WIDTHS: dict[int, float] = {6: 65.04, 7: 85.36, 8: 85.36}
"""The cutout's width per string count: the six-string's as drawn in the
Prototype001 DXF; the seven- and eight-string units share a route
0.800 in (20.32 mm) wider — 3.400 in against 2.600 in on Kahler's
2300/7300 installation sheets (6205RIMA against 6200RIMA), whose length,
depths and position are the six-string's."""

KAHLER_MODELS: dict[int, str] = {6: "7300", 7: "7327", 8: "7328"}
"""The Kahler 7300-series model per string count."""


@dataclass(frozen=True, slots=True)
class KahlerBridgeSpec:
    """Kahler 7300-style fixed bridge, screwed flat to the body.

    Only a rectangular baseplate-clearance cutout is routed; there are no
    studs, no springs and no rear cavity. The defaults are the cutout as
    drawn in the Prototype001 DXF; the seven- and eight-string units
    (7327, 7328) take a wider one (``KAHLER_BASEPLATE_WIDTHS``).

    Args:
        string_count: Strings the unit carries: 6, 7 or 8.
        baseplate_length: Cutout length along the neck.
        baseplate_width: Cutout width across the body; empty for the
            string count's (65.04 mm, 85.36 mm for seven or eight).
        baseplate_offset: Cutout centre behind the scale line.
        baseplate_depth: Cutout depth.
        plate_overhang: How far the bridge's plate, sitting on the top,
            reaches past the cutout all round (its footprint).
    """

    kind: Literal["kahler_7300"] = "kahler_7300"
    string_count: int = 6
    baseplate_length: float = 55.45
    baseplate_width: float | None = None
    baseplate_offset: float = 44.245
    baseplate_depth: float = 25.0
    plate_overhang: float = 5.0

    @property
    def cutout_width(self) -> float:
        """Return the cutout's width: as set, else the string count's.

        Raises:
            BodyGeometryError: For a string count Kahler makes no unit for.
        """
        if self.string_count not in KAHLER_BASEPLATE_WIDTHS:
            raise BodyGeometryError(
                f"The Kahler 7300 comes for 6, 7 or 8 strings, not {self.string_count}."
            )
        if self.baseplate_width is None:
            return KAHLER_BASEPLATE_WIDTHS[self.string_count]
        return self.baseplate_width

    def hardware(self, scale_length: float, body_thickness: float) -> BridgeHardware:
        width = self.cutout_width
        _positive(self, "baseplate_length", "baseplate_depth")
        if not math.isfinite(width) or width <= 0.0:
            raise BodyGeometryError(
                "Bridge baseplate_width must be finite and positive."
            )
        centre_x = scale_length + self.baseplate_offset
        half_length = self.baseplate_length / 2.0 + self.plate_overhang
        half_width = width / 2.0 + self.plate_overhang
        return BridgeHardware(
            BridgeMounting(
                scale_length, pivot_stud_spacing=None, has_sustain_block=False
            ),
            top_cavities=(
                RectangularCavity(
                    "Bridge baseplate cutout",
                    scale_length + self.baseplate_offset,
                    0.0,
                    self.baseplate_length,
                    width,
                    self.baseplate_depth,
                    corner_radius=0.0,
                ),
            ),
            notes=(
                (
                    "Kahler 7300: screw-mounted; verify the cutout against the unit."
                    if self.string_count == 6
                    else f"Kahler {KAHLER_MODELS[self.string_count]} "
                    f"({self.string_count} strings): screw-mounted; its cutout is "
                    "the six-string's widened as Kahler's installation sheets "
                    "do — verify it against the unit."
                ),
            ),
            footprint=(
                Point2D(centre_x - half_length, -half_width),
                Point2D(centre_x + half_length, -half_width),
                Point2D(centre_x + half_length, half_width),
                Point2D(centre_x - half_length, half_width),
            ),
        )


FLOYD_ROSE_DRAWN_THICKNESS = 44.45
"""The body thickness Floyd Rose's routing diagrams are drawn for (1.75 in)."""

FLOYD_ROSE_STUD_SPACINGS: dict[int, float] = {6: 73.91, 7: 84.58, 8: 95.5}
"""The pivot studs' centre distance per string count: the Original's
six- and seven-string routing sheets, and the eight-string FRT8's post
spacing (3.76 in; Floyd Rose publishes no eight-string routing)."""

FLOYD_ROSE_BASS_MARGIN = 8.89
"""From the bass-side stud's centre out to the recess wall, in mm."""

FLOYD_ROSE_TREBLE_MARGIN = 12.45
"""From the treble-side stud's centre out to the recess wall, in mm."""

FLOYD_ROSE_BLOCK_ROUTE_EXTRA = 8.94
"""How much wider the block route is than the studs are apart, in mm."""

FLOYD_ROSE_FINE_TUNER_INSET = 2.79
"""How much narrower the fine-tuner recess is than the studs are apart."""

FLOYD_ROSE_SIX_STRING_POCKET = 28.19
"""The six-string sheet's block clearance pocket depth from the back; the
seven-string sheet routes none deeper than the spring cavity."""


class FloydRoseWidths(NamedTuple):
    """A Floyd Rose's string-count dependent sizes, resolved (in mm).

    Args:
        stud_spacing: The pivot studs' centre distance.
        bass_half_width: Centreline to the recess's bass-side wall.
        treble_half_width: Centreline to its treble-side wall.
        fine_tuner_width: The narrower rear part's width.
        block_route_width: The block slot's width.
        block_pocket_depth: The block clearance pocket's depth from the
            back, as drawn (before a thicker body deepens it); the spring
            cavity's own depth when none is routed deeper.
    """

    stud_spacing: float
    bass_half_width: float
    treble_half_width: float
    fine_tuner_width: float
    block_route_width: float
    block_pocket_depth: float


@dataclass(frozen=True, slots=True)
class FloydRoseSpec:
    """Recessed Floyd Rose Original double-locking tremolo.

    For six, seven or eight strings (``string_count``). Every width across
    the body follows the studs' spacing by the same margins on Floyd
    Rose's six- and seven-string sheets — the recess's walls 8.89 mm
    (bass) and 12.45 mm (treble) outside the studs, the block slot
    8.94 mm wider than the studs are apart and the fine-tuner part
    2.79 mm narrower — so the widths left empty come from the string
    count's stud spacing (``FLOYD_ROSE_STUD_SPACINGS``); everything along
    the neck and every depth is the same on both sheets. The seven-string
    sheet routes no block pocket deeper than the spring cavity. Floyd Rose
    publishes no eight-string routing: the eight-string takes the FRT8's
    95.5 mm stud spacing with the seven-string sheet's margins and depths.

    The six-string routing follows the manufacturer's *Original Series Routing
    Diagrams* (floydrose.com, metric sheet): from the top a 95.25 mm wide
    recess, full width for 42.44 mm from the front wall and then
    71.12 mm wide, 79.38 mm long, cut 6.73 mm deep over its whole
    footprint; its front 15.88 mm stays at that depth as the shelf
    carrying the two Ø 10 pivot-stud holes, while everything behind is
    deepened to 11.18 mm for the baseplate's underside and the fine
    tuners, with a 20.96 × 82.85 mm slot 29.59 mm deep for the sustain
    block through that floor; from the back a 123.19 × 56.64 × 16.13 mm spring cavity
    with a 28.19 mm deep block clearance pocket at its tail end. The
    slot and the spring cavity meet only where they overlap, so the slot
    opens into the back solely inside the narrower spring cavity. The
    recess is not symmetric: the tremolo-arm side (treble) is 3.56 mm
    wider and the block slot sits 5.44 mm toward it. Floyd Rose puts the
    stud centre line 25.03 in from the nut on a 25.5 in scale, i.e.
    11.9 mm ahead of the scale line (StewMac's rule of thumb is 0.415 in
    / 10.5 mm) — ``pivot_offset``. The drawing is for a 1.75 in
    (``FLOYD_ROSE_DRAWN_THICKNESS``) body, where the slot runs 1.27 mm into
    the spring cavity; in a thicker body the spring cavity and the block
    pocket are that much deeper, so the slot still opens into the back.

    Args:
        treble_side: Which side of the centreline carries the treble
            strings and the tremolo arm: ``"+y"`` for the right-handed
            Prototype001 body (controls at +Y), ``"-y"`` otherwise.
        string_count: Strings the tremolo carries: 6, 7 or 8.
        pivot_offset: Stud centres relative to the scale line (negative =
            ahead of it, toward the nut).
        pivot_stud_spacing: Centre distance between the two stud inserts;
            empty for the string count's (73.91, 84.58 or 95.5 mm). The
            widths below left empty follow it.
        pivot_hole_diameter: Insert hole diameter.
        pivot_hole_depth: Insert hole depth from the top face (the
            6.73 mm shelf plus a 20.3 mm insert).
        stud_to_front_wall: Stud centres behind the recess front wall.
        stud_shelf_depth: Depth of the shelf the baseplate rests over.
        stud_shelf_length: Front wall to the block slot's front edge.
        recess_bass_half_width: Centreline to the bass-side wall; empty
            for the studs' half spacing + 8.89.
        recess_treble_half_width: Centreline to the treble-side wall;
            empty for the studs' half spacing + 12.45.
        recess_full_width_length: Length of the full-width part, from
            the front wall.
        recess_length: Total recess length from the front wall.
        fine_tuner_width: Width of the narrower rear part; empty for the
            stud spacing - 2.79.
        fine_tuner_depth: Depth of the clearance behind the stud shelf,
            around and behind the block slot.
        recess_corner_radius: Radius of the convex recess corners.
        recess_step_radius: Radius where the full width steps in.
        block_route_length: Block slot length along the neck.
        block_route_width: Block slot width across the body; empty for
            the stud spacing + 8.94.
        block_route_depth: Block slot depth from the top face; together
            with the spring cavity it must exceed the body thickness so
            the slot opens into the cavity.
        block_route_treble_shift: Slot centre toward the treble side.
        spring_cavity_length: Rear spring cavity length along the neck.
        spring_cavity_width: Rear spring cavity width across the body.
        spring_cavity_depth: Spring cavity depth from the back face.
        spring_cavity_tail_offset: Spring cavity tail end behind the
            recess front wall.
        block_pocket_length: Length of the deeper block clearance pocket
            at the spring cavity's tail end.
        block_pocket_depth: Its depth from the back face; empty for the
            six-string sheet's 28.19 mm, or none deeper than the spring
            cavity with seven or eight strings, as the seven-string sheet
            draws it (the spring cavity's depth: no pocket).
        cover_margin: Cover recess overhang around the spring cavity: room
            for the cover's six screws on the ledge (a Strat-style cover's
            overlap; the routing diagram leaves the cover to the builder).
        cover_depth: Cover recess depth.
        claw_screw_spacing: The tremolo claw's two screws apart, about the
            spring cavity's centre (34 mm on a Gotoh claw).
        claw_screw_height: The screws' height above the back face; empty
            for halfway up the spring cavity.
        claw_screw_diameter: Their pilot holes' diameter (for 4.2 mm
            screws).
        claw_screw_depth: How deep the pilots run into the spring
            cavity's nut-ward wall, along the neck.
    """

    kind: Literal["floyd_rose"] = "floyd_rose"
    treble_side: Literal["+y", "-y"] = "+y"
    string_count: int = 6
    pivot_offset: float = -11.9
    pivot_stud_spacing: float | None = None
    pivot_hole_diameter: float = 10.0
    pivot_hole_depth: float = 27.0
    stud_to_front_wall: float = 7.62
    stud_shelf_depth: float = 6.73
    stud_shelf_length: float = 15.88
    recess_bass_half_width: float | None = None
    recess_treble_half_width: float | None = None
    recess_full_width_length: float = 42.44
    recess_length: float = 79.38
    fine_tuner_width: float | None = None
    fine_tuner_depth: float = 11.18
    recess_corner_radius: float = 3.18
    recess_step_radius: float = 4.76
    block_route_length: float = 20.96
    block_route_width: float | None = None
    block_route_depth: float = 29.59
    block_route_treble_shift: float = 5.44
    spring_cavity_length: float = 123.19
    spring_cavity_width: float = 56.64
    spring_cavity_depth: float = 16.13
    spring_cavity_tail_offset: float = 48.27
    block_pocket_length: float = 11.43
    block_pocket_depth: float | None = None
    cover_margin: float = 8.0
    cover_depth: float = 2.0
    claw_screw_spacing: float = 34.0
    claw_screw_height: float | None = None
    claw_screw_diameter: float = 3.5
    claw_screw_depth: float = 30.0

    def widths(self) -> FloydRoseWidths:
        """Return the string-count dependent sizes, the empty ones filled.

        Raises:
            BodyGeometryError: For a string count Floyd Rose makes no
                Original for, or a size that is not finite and positive.
        """
        if self.string_count not in FLOYD_ROSE_STUD_SPACINGS:
            raise BodyGeometryError(
                "The Floyd Rose Original comes for 6, 7 or 8 strings, not "
                f"{self.string_count}."
            )

        def given(value: float | None, default: float) -> float:
            return default if value is None else value

        studs = given(
            self.pivot_stud_spacing, FLOYD_ROSE_STUD_SPACINGS[self.string_count]
        )
        widths = FloydRoseWidths(
            studs,
            given(self.recess_bass_half_width, studs / 2.0 + FLOYD_ROSE_BASS_MARGIN),
            given(
                self.recess_treble_half_width, studs / 2.0 + FLOYD_ROSE_TREBLE_MARGIN
            ),
            given(self.fine_tuner_width, studs - FLOYD_ROSE_FINE_TUNER_INSET),
            given(self.block_route_width, studs + FLOYD_ROSE_BLOCK_ROUTE_EXTRA),
            given(
                self.block_pocket_depth,
                FLOYD_ROSE_SIX_STRING_POCKET
                if self.string_count == 6
                else self.spring_cavity_depth,
            ),
        )
        names = (
            "pivot_stud_spacing",
            "recess_bass_half_width",
            "recess_treble_half_width",
            "fine_tuner_width",
            "block_route_width",
            "block_pocket_depth",
        )
        for name, value in zip(names, widths, strict=True):
            if not math.isfinite(value) or value <= 0.0:
                raise BodyGeometryError(f"Bridge {name} must be finite and positive.")
        return widths

    def hardware(self, scale_length: float, body_thickness: float) -> BridgeHardware:
        _positive(
            self,
            "pivot_hole_diameter",
            "pivot_hole_depth",
            "stud_shelf_depth",
            "stud_shelf_length",
            "recess_full_width_length",
            "recess_length",
            "fine_tuner_depth",
            "block_route_length",
            "block_route_depth",
            "spring_cavity_length",
            "spring_cavity_width",
            "spring_cavity_depth",
            "block_pocket_length",
            "cover_margin",
            "cover_depth",
            "claw_screw_spacing",
            "claw_screw_diameter",
            "claw_screw_depth",
        )
        if self.claw_screw_spacing >= self.spring_cavity_width:
            raise BodyGeometryError(
                "The trem claw's screws must lie inside the spring cavity's "
                "width: make claw_screw_spacing smaller."
            )
        if self.claw_screw_height is not None and not (
            0.0 < self.claw_screw_height < body_thickness
        ):
            raise BodyGeometryError(
                "claw_screw_height must lie between the back and the top."
            )
        widths = self.widths()
        self._check_layout(body_thickness, widths)
        sign = 1.0 if self.treble_side == "+y" else -1.0
        pivot_x = scale_length + self.pivot_offset
        front = pivot_x - self.stud_to_front_wall
        slot_front = front + self.stud_shelf_length
        slot_back = slot_front + self.block_route_length
        step_x = front + self.recess_full_width_length
        back = front + self.recess_length
        bass = -sign * widths.bass_half_width
        treble = sign * widths.treble_half_width
        narrow = widths.fine_tuner_width / 2.0
        corner = self.recess_corner_radius
        step = self.recess_step_radius

        mounting = BridgeMounting(
            pivot_x,
            pivot_stud_spacing=widths.stud_spacing,
            pivot_hole_diameter=self.pivot_hole_diameter,
            pivot_hole_depth=self.pivot_hole_depth,
            has_sustain_block=False,
        )
        # The whole footprint is one shallow pocket, so its walls are
        # continuous; the deeper floor behind the stud shelf is a step
        # inside it, starting where the slot starts so every pocket is
        # wider than a router bit (the drawing's 5.6 mm full-width strip
        # behind the slot would otherwise be a pocket no tool fits into).
        recess = TracedCavity(
            "Floyd Rose recess",
            rounded_polygon_points(
                [
                    Point2D(front, bass),
                    Point2D(step_x, bass),
                    Point2D(step_x, -sign * narrow),
                    Point2D(back, -sign * narrow),
                    Point2D(back, sign * narrow),
                    Point2D(step_x, sign * narrow),
                    Point2D(step_x, treble),
                    Point2D(front, treble),
                ],
                [corner, corner, step, corner, corner, step, corner, corner],
            ),
            self.stud_shelf_depth,
        )
        fine_tuners = TracedCavity(
            "Floyd Rose fine-tuner recess",
            rounded_polygon_points(
                [
                    Point2D(slot_front, bass),
                    Point2D(step_x, bass),
                    Point2D(step_x, -sign * narrow),
                    Point2D(back, -sign * narrow),
                    Point2D(back, sign * narrow),
                    Point2D(step_x, sign * narrow),
                    Point2D(step_x, treble),
                    Point2D(slot_front, treble),
                ],
                [0.0, corner, step, corner, corner, step, corner, 0.0],
            ),
            self.fine_tuner_depth,
        )
        block_route = RectangularCavity(
            "Floyd Rose block route",
            (slot_front + slot_back) / 2.0,
            sign * self.block_route_treble_shift,
            self.block_route_length,
            widths.block_route_width,
            min(self.block_route_depth, body_thickness),
            corner_radius=self.block_route_length / 2.0,
        )
        tail = front + self.spring_cavity_tail_offset
        rear_radius = min(5.0, self.block_pocket_length / 2.0)
        # The block hangs a fixed depth below the top; a body thicker than
        # the drawing's puts it further from the back, so the spring
        # cavity and the block pocket reach that much deeper.
        extra = max(0.0, body_thickness - FLOYD_ROSE_DRAWN_THICKNESS)
        spring_cavity = RearCavity(
            RectangularCavity(
                "Floyd Rose spring cavity",
                tail - self.spring_cavity_length / 2.0,
                0.0,
                self.spring_cavity_length,
                self.spring_cavity_width,
                self.spring_cavity_depth + extra,
                corner_radius=rear_radius,
            ),
            RectangularCavity(
                "Floyd Rose spring cavity cover recess",
                tail - self.spring_cavity_length / 2.0,
                0.0,
                self.spring_cavity_length + 2.0 * self.cover_margin,
                self.spring_cavity_width + 2.0 * self.cover_margin,
                self.cover_depth,
                corner_radius=rear_radius + self.cover_margin,
            ),
            # As drawn for seven strings, no pocket deeper than the cavity.
            steps=(
                (
                    RectangularCavity(
                        "Floyd Rose block clearance pocket",
                        tail - self.block_pocket_length / 2.0,
                        0.0,
                        self.block_pocket_length,
                        self.spring_cavity_width,
                        widths.block_pocket_depth + extra,
                        corner_radius=rear_radius,
                    ),
                )
                if widths.block_pocket_depth > self.spring_cavity_depth
                else ()
            ),
        )
        notes: tuple[str, ...] = {
            6: (
                "Floyd Rose Original: routing per the manufacturer's Original "
                "Series Routing Diagrams; studs 11.9 mm ahead of the scale line "
                "(25.03 in on a 25.5 in scale).",
            ),
            7: (
                "Floyd Rose Original 7-string: routing per the manufacturer's "
                "7-String Routing sheet; studs 11.9 mm ahead of the scale line.",
            ),
            8: (
                "Floyd Rose 8-string: Floyd Rose publishes no 8-string routing; "
                "this is the 7-string sheet widened to the FRT8's 95.5 mm stud "
                "spacing (every width keeps the 6- and 7-string sheets' margins "
                "from the studs). Check it against the unit before cutting.",
            ),
        }[self.string_count]
        if self.string_count != 6 and widths.block_pocket_depth <= (
            self.spring_cavity_depth
        ):
            notes += (
                "As the 7-string sheet draws it, the block has no pocket deeper "
                "than the spring cavity behind it; should it touch the wood on "
                "a deep dive, set the bridge's block_pocket_depth to "
                f"{FLOYD_ROSE_SIX_STRING_POCKET:g} (the 6-string sheet's, from "
                "the back) and the pocket is cut at the cavity's tail end, "
                "under the spring cover.",
            )
        # The tremolo claw's two screws go into the spring cavity's
        # nut-ward wall along the neck, drilled sideways by hand.
        wall = tail - self.spring_cavity_length
        height = (
            (self.spring_cavity_depth + extra) / 2.0
            if self.claw_screw_height is None
            else self.claw_screw_height
        )
        claw = tuple(
            SideHole(
                f"Trem claw screw {index} hole",
                Point3D(wall, y, height),
                Point3D(wall - self.claw_screw_depth, y, height),
                self.claw_screw_diameter,
                "Floyd Rose spring cavity",
            )
            for index, y in enumerate(
                (-self.claw_screw_spacing / 2.0, self.claw_screw_spacing / 2.0),
                start=1,
            )
        )
        return BridgeHardware(
            mounting,
            top_cavities=(recess, fine_tuners),
            through_cavities=(block_route,),
            rear_cavities=(spring_cavity,),
            notes=(
                *notes,
                f"Drill the trem claw's two screws' {self.claw_screw_diameter:g} "
                "mm pilots by hand into the spring cavity's nut-ward wall, "
                f"{self.claw_screw_depth:g} mm deep along the neck, "
                f"{self.claw_screw_spacing:g} mm apart about the centreline and "
                f"{height:g} mm up from the back (modelled: Trem claw screw "
                "holes; set the bridge's claw_screw_* to the claw's own).",
            ),
            side_holes=claw,
        )

    def _check_layout(self, body_thickness: float, widths: FloydRoseWidths) -> None:
        """Reject a recess whose parts cannot be laid out as drawn."""
        if self.stud_to_front_wall <= 0.0 or self.stud_to_front_wall >= (
            self.stud_shelf_length
        ):
            raise BodyGeometryError(
                "Floyd Rose studs must sit on the shelf ahead of the block route."
            )
        if self.stud_shelf_length + self.block_route_length > (
            self.recess_full_width_length
        ):
            raise BodyGeometryError(
                "Floyd Rose block route must end inside the full-width part of "
                "the recess."
            )
        if self.recess_full_width_length >= self.recess_length:
            raise BodyGeometryError(
                "Floyd Rose recess must be longer than its full-width part."
            )
        if widths.fine_tuner_width / 2.0 > min(
            widths.bass_half_width, widths.treble_half_width
        ):
            raise BodyGeometryError(
                "Floyd Rose fine-tuner recess must be narrower than the full width."
            )
        slot_half = widths.block_route_width / 2.0
        if (
            self.block_route_treble_shift + slot_half > widths.treble_half_width
            or slot_half - self.block_route_treble_shift > widths.bass_half_width
        ):
            raise BodyGeometryError(
                "Floyd Rose block route must lie inside the recess width."
            )
        if self.block_pocket_length > self.spring_cavity_length:
            raise BodyGeometryError(
                "Floyd Rose block clearance pocket must fit in the spring cavity."
            )
        if widths.block_pocket_depth < self.spring_cavity_depth:
            raise BodyGeometryError(
                "Floyd Rose block clearance pocket must be at least as deep as "
                "the spring cavity (as deep: none)."
            )
        if self.spring_cavity_depth <= self.cover_depth:
            raise BodyGeometryError(
                "Floyd Rose spring cavity must be deeper than its cover recess."
            )
        # The rear depths as routed in this body (see ``hardware``).
        extra = max(0.0, body_thickness - FLOYD_ROSE_DRAWN_THICKNESS)
        spring_depth = self.spring_cavity_depth + extra
        pocket_depth = widths.block_pocket_depth + extra
        if (
            pocket_depth + self.fine_tuner_depth >= body_thickness
            or spring_depth + self.fine_tuner_depth >= body_thickness
        ):
            raise BodyGeometryError(
                "Floyd Rose routes would meet: the body is too thin for the "
                "fine-tuner recess over the spring cavity."
            )
        if self.pivot_hole_depth >= body_thickness:
            raise BodyGeometryError(
                "Floyd Rose stud holes would pass through the body: too thin."
            )
        if self.block_route_depth + spring_depth <= body_thickness:
            raise BodyGeometryError(
                "Floyd Rose block route would not open into the spring cavity: "
                "the body is too thick for the routed depths."
            )


@dataclass(frozen=True, slots=True)
class TuneOMaticSpec:
    """Tune-o-matic bridge on two posts with a stop-bar tailpiece.

    Nothing is routed; four holes take the post and stud inserts. A
    Tune-o-matic on a flat-topped body wants a neck angle (or a recessed
    bridge): ``Prototype001Parameters.neck_angle`` gives one, 2 degrees by
    default with this bridge.

    The bass-side post sits ``bass_setback`` further back than the
    treble one, so the bridge leans as the strings' compensation does and
    every saddle starts near the middle of its short travel (the usual
    setting: treble post 1/16 in behind the scale, the bass post 1/16-1/8
    in further). The bass side is -Y; a neck with its bass side on +Y gets
    the bridge mirrored (``mirrored_hardware``).

    Args:
        post_spacing: Centre distance between the bridge posts.
        post_hole_diameter: Post insert hole diameter (Nashville-style
            inserts; ABR-1 wood-screw posts need about 4 mm).
        post_hole_depth: Post insert hole depth.
        compensation: The treble post's centre behind the scale line.
        bass_setback: How much further back the bass post sits.
        stud_spacing: Centre distance between the tailpiece studs.
        stud_hole_diameter: Tailpiece insert hole diameter.
        stud_hole_depth: Tailpiece insert hole depth.
        tailpiece_offset: Tailpiece stud centres behind the scale line.
    """

    kind: Literal["tune_o_matic"] = "tune_o_matic"
    post_spacing: float = 74.0
    post_hole_diameter: float = 11.2
    post_hole_depth: float = 20.0
    compensation: float = 1.6
    bass_setback: float = 3.2
    stud_spacing: float = 82.0
    stud_hole_diameter: float = 11.2
    stud_hole_depth: float = 20.0
    tailpiece_offset: float = 45.0

    def hardware(self, scale_length: float, body_thickness: float) -> BridgeHardware:
        _positive(
            self,
            "post_spacing",
            "post_hole_diameter",
            "post_hole_depth",
            "stud_spacing",
            "stud_hole_diameter",
            "stud_hole_depth",
        )
        if not math.isfinite(self.bass_setback) or self.bass_setback < 0.0:
            raise BodyGeometryError(
                "Tune-o-matic bass_setback must be finite and not negative."
            )
        post_x = scale_length + self.compensation
        stud_x = scale_length + self.tailpiece_offset
        holes: list[DrilledHole] = []
        for side, sign in (("bass", -1.0), ("treble", 1.0)):
            holes.append(
                DrilledHole(
                    f"Bridge post {side}",
                    post_x + (self.bass_setback if side == "bass" else 0.0),
                    sign * self.post_spacing / 2.0,
                    self.post_hole_diameter,
                    self.post_hole_depth,
                )
            )
            holes.append(
                DrilledHole(
                    f"Tailpiece stud {side}",
                    stud_x,
                    sign * self.stud_spacing / 2.0,
                    self.stud_hole_diameter,
                    self.stud_hole_depth,
                )
            )
        return BridgeHardware(
            BridgeMounting(post_x, pivot_stud_spacing=None, has_sustain_block=False),
            holes=tuple(holes),
            notes=(
                "Tune-o-matic: it reaches playing height on the flat top with "
                "the neck angled (neck_angle, 2 degrees by default).",
            ),
        )


@dataclass(frozen=True, slots=True)
class HardtailSpec:
    """Flat hardtail bridge, strung through the body or top-loaded.

    A string hole per string passes through the body behind the saddles;
    a top-loading bridge (``string_through`` off — most bass bridges can
    be strung either way) takes the strings through its own tail and
    needs none. The baseplate screws are pilot-drilled along its front
    edge.

    Args:
        string_count: Number of strings (and string-through holes).
        string_through: Whether the strings pass through the body; off,
            they load through the bridge's tail and no holes are drilled.
        string_spacing: Centre distance between neighbouring strings.
        string_hole_diameter: String-through hole diameter.
        string_hole_offset: String holes behind the scale line.
        screw_count: Baseplate mounting screws along the front edge.
        screw_spacing: Centre distance between neighbouring screws.
        screw_hole_diameter: Pilot hole diameter.
        screw_hole_depth: Pilot hole depth.
        screw_offset: Screw line behind the scale line (negative =
            ahead of it).
    """

    kind: Literal["hardtail"] = "hardtail"
    string_count: int = 6
    string_through: bool = True
    string_spacing: float = 10.5
    string_hole_diameter: float = 3.0
    string_hole_offset: float = 14.0
    screw_count: int = 5
    screw_spacing: float = 12.0
    screw_hole_diameter: float = 3.0
    screw_hole_depth: float = 12.0
    screw_offset: float = -10.0

    def hardware(self, scale_length: float, body_thickness: float) -> BridgeHardware:
        _positive(
            self,
            "string_spacing",
            "string_hole_diameter",
            "screw_spacing",
            "screw_hole_diameter",
            "screw_hole_depth",
        )
        if self.screw_count < 1:
            raise BodyGeometryError("Hardtail needs at least one mounting screw.")
        if self.string_count < 1:
            raise BodyGeometryError("Hardtail needs at least one string.")
        holes: list[DrilledHole] = []
        string_x = scale_length + self.string_hole_offset
        for index in range(self.string_count if self.string_through else 0):
            y = (index - (self.string_count - 1) / 2.0) * self.string_spacing
            holes.append(
                DrilledHole(
                    f"String {index + 1} through hole",
                    string_x,
                    y,
                    self.string_hole_diameter,
                    body_thickness,
                )
            )
        screw_x = scale_length + self.screw_offset
        for index in range(self.screw_count):
            y = (index - (self.screw_count - 1) / 2.0) * self.screw_spacing
            holes.append(
                DrilledHole(
                    f"Bridge screw {index + 1} pilot",
                    screw_x,
                    y,
                    self.screw_hole_diameter,
                    self.screw_hole_depth,
                )
            )
        return BridgeHardware(
            BridgeMounting(
                scale_length, pivot_stud_spacing=None, has_sustain_block=False
            ),
            holes=tuple(holes),
            notes=(
                (
                    "Hardtail, strung through the body: the string ferrules' "
                    "counterbores are drilled from the back (Body_back, "
                    "body_string_ferrule_diameter and _depth)."
                    if self.string_through
                    else "Hardtail, top-loaded: the strings load through the "
                    "bridge's tail; nothing passes through the body."
                ),
            ),
        )


@dataclass(frozen=True, slots=True)
class HeadlessBridgeSpec:
    """A headless bridge: saddles and the tuners in one unit on the top.

    The strings anchor at the headless neck's end and are tuned at the
    bridge, its tuner knobs at the unit's tail. The unit is screwed flat to
    the top: only its pilot holes are drilled, at the plate's four corners,
    and its plate is the bridge's footprint (kept clear of the pickguard
    and the engraving). The defaults are a typical six-string unit's
    (Hipshot / ABM style); check the screw pattern against the unit.

    Args:
        string_count: Number of strings.
        string_spacing: Centre distance between neighbouring strings.
        front_reach: How far the plate reaches ahead of the scale line.
        length: The unit's length along the neck, tuner knobs included.
        side_margin: Plate past the outer strings on each side.
        screw_inset: Pilot holes' distance in from the plate's edges.
        screw_hole_diameter: Pilot hole diameter.
        screw_hole_depth: Pilot hole depth.
    """

    kind: Literal["headless"] = "headless"
    string_count: int = 6
    string_spacing: float = 10.5
    front_reach: float = 12.0
    length: float = 90.0
    side_margin: float = 10.0
    screw_inset: float = 6.0
    screw_hole_diameter: float = 3.0
    screw_hole_depth: float = 12.0

    def hardware(self, scale_length: float, body_thickness: float) -> BridgeHardware:
        _positive(
            self,
            "string_spacing",
            "front_reach",
            "length",
            "side_margin",
            "screw_inset",
            "screw_hole_diameter",
            "screw_hole_depth",
        )
        if self.string_count < 1:
            raise BodyGeometryError("A headless bridge needs at least one string.")
        half = (self.string_count - 1) * self.string_spacing / 2.0 + self.side_margin
        front = scale_length - self.front_reach
        back = front + self.length
        if self.screw_inset * 2.0 >= min(self.length, 2.0 * half):
            raise BodyGeometryError(
                "The headless bridge's screws do not fit its plate."
            )
        holes = tuple(
            DrilledHole(
                f"Bridge screw {index + 1} pilot",
                x,
                y,
                self.screw_hole_diameter,
                self.screw_hole_depth,
            )
            for index, (x, y) in enumerate(
                (x, side * (half - self.screw_inset))
                for x in (front + self.screw_inset, back - self.screw_inset)
                for side in (-1.0, 1.0)
            )
        )
        return BridgeHardware(
            BridgeMounting(
                scale_length, pivot_stud_spacing=None, has_sustain_block=False
            ),
            holes=holes,
            notes=(
                "Headless bridge: tuners at the bridge; check its screw pattern "
                "against the unit before drilling.",
            ),
            footprint=(
                Point2D(front, -half),
                Point2D(back, -half),
                Point2D(back, half),
                Point2D(front, half),
            ),
        )


@dataclass(frozen=True, slots=True)
class SingleStringBridgeSpec:
    """Single-string bridges: a small bridge of its own for every string.

    Each unit sits on its own string, ``front_reach`` of it ahead of the
    string's scale point (its saddle there, mid-travel), and is screwed
    down through two holes on its centre line, ``screw_inset`` in from
    its ends; with ``string_through`` its string passes through the body
    ``string_hole_offset`` behind the scale point. On a multiscale every
    unit stands at its own string's scale on the fanned bridge line, still
    square to its string — the units follow the fan without turning,
    which is why fanned basses use them. The defaults are labelled
    starting values for a bass single (ABM 3710-style, 60 x 15 mm, 19 mm
    string spacing); check the screw and string holes against the units.

    Args:
        string_count: Number of strings, one unit each.
        string_spacing: Centre distance between neighbouring strings.
        unit_length: A unit's length along its string.
        unit_width: A unit's width; at most the string spacing.
        front_reach: How far a unit reaches ahead of its scale point.
        screw_inset: Its two screws in from its front and rear ends.
        screw_hole_diameter: Pilot hole diameter.
        screw_hole_depth: Pilot hole depth.
        string_through: Whether the strings pass through the body; off,
            they load through the units.
        string_hole_offset: String holes behind the scale point.
        string_hole_diameter: String-through hole diameter.
    """

    kind: Literal["single_string"] = "single_string"
    string_count: int = 4
    string_spacing: float = 19.0
    unit_length: float = 60.0
    unit_width: float = 15.0
    front_reach: float = 15.0
    screw_inset: float = 6.0
    screw_hole_diameter: float = 3.0
    screw_hole_depth: float = 12.0
    string_through: bool = True
    string_hole_offset: float = 30.0
    string_hole_diameter: float = 4.0

    def hardware(
        self, scale_length: float, body_thickness: float, lean: float = 0.0
    ) -> BridgeHardware:
        """Return the units' holes and footprint.

        ``lean`` is a multiscale's bridge line's ``dx/dy``: the unit on a
        string ``y`` from the centreline stands ``lean * y`` further back.
        """
        _positive(
            self,
            "string_spacing",
            "unit_length",
            "unit_width",
            "screw_inset",
            "screw_hole_diameter",
            "screw_hole_depth",
            "string_hole_diameter",
        )
        if self.string_count < 1:
            raise BodyGeometryError("Single-string bridges need at least one string.")
        if self.unit_width > self.string_spacing:
            raise BodyGeometryError(
                "The single-string bridges would overlap: unit_width must not "
                "exceed string_spacing."
            )
        front = -self.front_reach
        back = front + self.unit_length
        screws = (front + self.screw_inset, back - self.screw_inset)
        if not front < 0.0 < back or screws[0] >= screws[1]:
            raise BodyGeometryError(
                "A single-string bridge must reach over its scale point with "
                "room for its two screws."
            )
        if self.string_through and not screws[0] < self.string_hole_offset < screws[1]:
            raise BodyGeometryError(
                "A single-string bridge's string hole must lie between its screws."
            )
        holes: list[DrilledHole] = []
        centres: list[Point2D] = []
        for index in range(self.string_count):
            y = (index - (self.string_count - 1) / 2.0) * self.string_spacing
            x = scale_length + lean * y
            centres.append(Point2D(x, y))
            unit = f"String {index + 1} bridge"
            holes.extend(
                DrilledHole(
                    f"{unit} screw {end} pilot",
                    x + dx,
                    y,
                    self.screw_hole_diameter,
                    self.screw_hole_depth,
                )
                for end, dx in zip(("front", "rear"), screws, strict=True)
            )
            if self.string_through:
                holes.append(
                    DrilledHole(
                        f"{unit} string through hole",
                        x + self.string_hole_offset,
                        y,
                        self.string_hole_diameter,
                        body_thickness,
                    )
                )
        half = self.unit_width / 2.0
        first, last = centres[0], centres[-1]
        return BridgeHardware(
            BridgeMounting(
                scale_length, pivot_stud_spacing=None, has_sustain_block=False
            ),
            holes=tuple(holes),
            notes=(
                "Single-string bridges: a unit per string, its saddle on the "
                "string's scale"
                + (", each on the fanned bridge line" if lean else "")
                + "; check the screw"
                + (" and string" if self.string_through else "")
                + " holes against the units before drilling.",
            ),
            # Round all the units: one plate's worth of top kept clear.
            footprint=(
                Point2D(first.x + front, first.y - half),
                Point2D(first.x + back, first.y - half),
                Point2D(last.x + back, last.y + half),
                Point2D(last.x + front, last.y + half),
            ),
        )


BridgeSpec = (
    KahlerBridgeSpec
    | FloydRoseSpec
    | TuneOMaticSpec
    | HardtailSpec
    | HeadlessBridgeSpec
    | SingleStringBridgeSpec
)

BRIDGE_KINDS: dict[str, type[Any]] = {
    "kahler_7300": KahlerBridgeSpec,
    "floyd_rose": FloydRoseSpec,
    "tune_o_matic": TuneOMaticSpec,
    "hardtail": HardtailSpec,
    "headless": HeadlessBridgeSpec,
    "single_string": SingleStringBridgeSpec,
}

BRIDGE_LABELS: dict[str, str] = {
    "kahler_7300": "Kahler 7300 (fixed, flat mount)",
    "floyd_rose": "Floyd Rose (recessed tremolo)",
    "tune_o_matic": "Tune-o-matic + stop bar",
    "hardtail": "Hardtail (string-through or top-load)",
    "headless": "Headless (tuners at the bridge)",
    "single_string": "Single-string bridges (one per string)",
}

BRIDGE_MAX_STRINGS: dict[str, int] = {
    "kahler_7300": 8,
    "floyd_rose": 8,
    "tune_o_matic": 6,
}
"""The most strings a bridge kind is drawn for; unlisted kinds take any count.

The Kahler 7300 and the Floyd Rose come for six to eight strings, the
Tune-o-matic spec carries six-string dimensions; the hardtail and the
single-string bridges make a hole or a unit per string.
"""

BRIDGE_MIN_STRINGS: dict[str, int] = {
    "kahler_7300": 6,
    "floyd_rose": 6,
}
"""The fewest strings a bridge kind is made for; unlisted kinds take any."""


def bridge_spec_from_dict(data: Mapping[str, Any]) -> BridgeSpec:
    """Rebuild a bridge spec from its ``dataclasses.asdict`` form.

    The ``kind`` entry selects the spec class; every other entry must be
    one of its fields.

    Raises:
        BodyGeometryError: For an unknown kind or field.
    """
    kind = data.get("kind")
    spec_class = BRIDGE_KINDS.get(str(kind))
    if spec_class is None:
        raise BodyGeometryError(
            f"Unknown bridge kind {kind!r}; choose one of "
            + ", ".join(sorted(BRIDGE_KINDS))
            + "."
        )
    allowed = {field.name for field in fields(spec_class)}
    unknown = set(data) - allowed
    if unknown:
        raise BodyGeometryError(
            f"Unknown {kind} bridge field(s): {', '.join(sorted(unknown))}."
        )
    spec: BridgeSpec = spec_class(**data)
    return spec


def _positive(spec: object, *names: str) -> None:
    for name in names:
        value = getattr(spec, name)
        if not math.isfinite(value) or value <= 0.0:
            raise BodyGeometryError(f"Bridge {name} must be finite and positive.")

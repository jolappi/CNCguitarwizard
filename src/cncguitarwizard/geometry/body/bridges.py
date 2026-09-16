"""Interchangeable bridge hardware: what each bridge needs cut into the body.

A bridge is described by a small frozen dataclass of dimensions (a
*spec*). Asking the spec for its ``hardware`` at a given scale length and
body thickness yields every body feature that bridge requires — pivot or
post holes, top routes, routes that pass clean through into a rear cavity,
rear cavities with their cover recesses — ready for ``BodySolid``.

The Floyd Rose routing follows the manufacturer's own routing diagrams;
the other bridges' dimensions are labelled, adjustable starting values
rather than verified templates — measure the real hardware before cutting.
All longitudinal offsets are measured from the scale-length line (the
nominal saddle/intonation line) toward the tail, so a bridge stays on the
scale whatever the neck does.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any, Literal

from ..exceptions import BodyGeometryError
from ..primitives import Point2D, rounded_polygon_points
from .hardware import (
    BridgeMounting,
    Cavity,
    DrilledHole,
    RearCavity,
    RectangularCavity,
    TracedCavity,
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
    """

    mounting: BridgeMounting
    top_cavities: tuple[Cavity, ...] = ()
    through_cavities: tuple[Cavity, ...] = ()
    rear_cavities: tuple[RearCavity, ...] = ()
    holes: tuple[DrilledHole, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class KahlerBridgeSpec:
    """Kahler 7300-style fixed bridge, screwed flat to the body.

    Only a rectangular baseplate-clearance cutout is routed; there are no
    studs, no springs and no rear cavity. The defaults are the cutout as
    drawn in the Prototype001 DXF.

    Args:
        baseplate_length: Cutout length along the neck.
        baseplate_width: Cutout width across the body.
        baseplate_offset: Cutout centre behind the scale line.
        baseplate_depth: Cutout depth.
    """

    kind: Literal["kahler_7300"] = "kahler_7300"
    baseplate_length: float = 55.45
    baseplate_width: float = 65.04
    baseplate_offset: float = 44.245
    baseplate_depth: float = 25.0

    def hardware(self, scale_length: float, body_thickness: float) -> BridgeHardware:
        _positive(self, "baseplate_length", "baseplate_width", "baseplate_depth")
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
                    self.baseplate_width,
                    self.baseplate_depth,
                    corner_radius=0.0,
                ),
            ),
            notes=("Kahler 7300: screw-mounted; verify the cutout against the unit.",),
        )


@dataclass(frozen=True, slots=True)
class FloydRoseSpec:
    """Recessed Floyd Rose Original double-locking tremolo.

    The routing follows the manufacturer's *Original Series Routing
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
    / 10.5 mm) — ``pivot_offset``.

    Args:
        treble_side: Which side of the centreline carries the treble
            strings and the tremolo arm: ``"+y"`` for the left-handed
            Prototype001 body (controls at +Y), ``"-y"`` otherwise.
        pivot_offset: Stud centres relative to the scale line (negative =
            ahead of it, toward the nut).
        pivot_stud_spacing: Centre distance between the two stud inserts.
        pivot_hole_diameter: Insert hole diameter.
        pivot_hole_depth: Insert hole depth from the top face (the
            6.73 mm shelf plus a 20.3 mm insert).
        stud_to_front_wall: Stud centres behind the recess front wall.
        stud_shelf_depth: Depth of the shelf the baseplate rests over.
        stud_shelf_length: Front wall to the block slot's front edge.
        recess_bass_half_width: Centreline to the bass-side wall.
        recess_treble_half_width: Centreline to the treble-side wall.
        recess_full_width_length: Length of the full-width part, from
            the front wall.
        recess_length: Total recess length from the front wall.
        fine_tuner_width: Width of the narrower rear part.
        fine_tuner_depth: Depth of the clearance behind the stud shelf,
            around and behind the block slot.
        recess_corner_radius: Radius of the convex recess corners.
        recess_step_radius: Radius where the full width steps in.
        block_route_length: Block slot length along the neck.
        block_route_width: Block slot width across the body.
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
        block_pocket_depth: Its depth from the back face.
        cover_margin: Cover recess overhang around the spring cavity.
        cover_depth: Cover recess depth.
    """

    kind: Literal["floyd_rose"] = "floyd_rose"
    treble_side: Literal["+y", "-y"] = "+y"
    pivot_offset: float = -11.9
    pivot_stud_spacing: float = 73.91
    pivot_hole_diameter: float = 10.0
    pivot_hole_depth: float = 27.0
    stud_to_front_wall: float = 7.62
    stud_shelf_depth: float = 6.73
    stud_shelf_length: float = 15.88
    recess_bass_half_width: float = 45.85
    recess_treble_half_width: float = 49.4
    recess_full_width_length: float = 42.44
    recess_length: float = 79.38
    fine_tuner_width: float = 71.12
    fine_tuner_depth: float = 11.18
    recess_corner_radius: float = 3.18
    recess_step_radius: float = 4.76
    block_route_length: float = 20.96
    block_route_width: float = 82.85
    block_route_depth: float = 29.59
    block_route_treble_shift: float = 5.44
    spring_cavity_length: float = 123.19
    spring_cavity_width: float = 56.64
    spring_cavity_depth: float = 16.13
    spring_cavity_tail_offset: float = 48.27
    block_pocket_length: float = 11.43
    block_pocket_depth: float = 28.19
    cover_margin: float = 5.0
    cover_depth: float = 2.0

    def hardware(self, scale_length: float, body_thickness: float) -> BridgeHardware:
        _positive(
            self,
            "pivot_stud_spacing",
            "pivot_hole_diameter",
            "pivot_hole_depth",
            "stud_shelf_depth",
            "stud_shelf_length",
            "recess_bass_half_width",
            "recess_treble_half_width",
            "recess_full_width_length",
            "recess_length",
            "fine_tuner_width",
            "fine_tuner_depth",
            "block_route_length",
            "block_route_width",
            "block_route_depth",
            "spring_cavity_length",
            "spring_cavity_width",
            "spring_cavity_depth",
            "block_pocket_length",
            "block_pocket_depth",
            "cover_margin",
            "cover_depth",
        )
        self._check_layout(body_thickness)
        sign = 1.0 if self.treble_side == "+y" else -1.0
        pivot_x = scale_length + self.pivot_offset
        front = pivot_x - self.stud_to_front_wall
        slot_front = front + self.stud_shelf_length
        slot_back = slot_front + self.block_route_length
        step_x = front + self.recess_full_width_length
        back = front + self.recess_length
        bass = -sign * self.recess_bass_half_width
        treble = sign * self.recess_treble_half_width
        narrow = self.fine_tuner_width / 2.0
        corner = self.recess_corner_radius
        step = self.recess_step_radius

        mounting = BridgeMounting(
            pivot_x,
            pivot_stud_spacing=self.pivot_stud_spacing,
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
            self.block_route_width,
            min(self.block_route_depth, body_thickness),
            corner_radius=self.block_route_length / 2.0,
        )
        tail = front + self.spring_cavity_tail_offset
        rear_radius = min(5.0, self.block_pocket_length / 2.0)
        spring_cavity = RearCavity(
            RectangularCavity(
                "Floyd Rose spring cavity",
                tail - self.spring_cavity_length / 2.0,
                0.0,
                self.spring_cavity_length,
                self.spring_cavity_width,
                self.spring_cavity_depth,
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
            steps=(
                RectangularCavity(
                    "Floyd Rose block clearance pocket",
                    tail - self.block_pocket_length / 2.0,
                    0.0,
                    self.block_pocket_length,
                    self.spring_cavity_width,
                    self.block_pocket_depth,
                    corner_radius=rear_radius,
                ),
            ),
        )
        return BridgeHardware(
            mounting,
            top_cavities=(recess, fine_tuners),
            through_cavities=(block_route,),
            rear_cavities=(spring_cavity,),
            notes=(
                "Floyd Rose Original: routing per the manufacturer's Original "
                "Series Routing Diagrams; studs 11.9 mm ahead of the scale line "
                "(25.03 in on a 25.5 in scale).",
                "Drill the two trem-claw screw holes into the spring cavity's "
                "nut-ward wall by hand.",
            ),
        )

    def _check_layout(self, body_thickness: float) -> None:
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
        if self.fine_tuner_width / 2.0 > min(
            self.recess_bass_half_width, self.recess_treble_half_width
        ):
            raise BodyGeometryError(
                "Floyd Rose fine-tuner recess must be narrower than the full width."
            )
        slot_half = self.block_route_width / 2.0
        if (
            self.block_route_treble_shift + slot_half > self.recess_treble_half_width
            or slot_half - self.block_route_treble_shift > self.recess_bass_half_width
        ):
            raise BodyGeometryError(
                "Floyd Rose block route must lie inside the recess width."
            )
        if self.block_pocket_length > self.spring_cavity_length:
            raise BodyGeometryError(
                "Floyd Rose block clearance pocket must fit in the spring cavity."
            )
        if self.block_pocket_depth <= self.spring_cavity_depth:
            raise BodyGeometryError(
                "Floyd Rose block clearance pocket must be deeper than the "
                "spring cavity."
            )
        if self.spring_cavity_depth <= self.cover_depth:
            raise BodyGeometryError(
                "Floyd Rose spring cavity must be deeper than its cover recess."
            )
        if (
            self.block_pocket_depth + self.fine_tuner_depth >= body_thickness
            or self.spring_cavity_depth + self.fine_tuner_depth >= body_thickness
        ):
            raise BodyGeometryError(
                "Floyd Rose routes would meet: the body is too thin for the "
                "fine-tuner recess over the spring cavity."
            )
        if self.pivot_hole_depth >= body_thickness:
            raise BodyGeometryError(
                "Floyd Rose stud holes would pass through the body: too thin."
            )
        if self.block_route_depth + self.spring_cavity_depth <= body_thickness:
            raise BodyGeometryError(
                "Floyd Rose block route would not open into the spring cavity: "
                "the body is too thick for the routed depths."
            )


@dataclass(frozen=True, slots=True)
class TuneOMaticSpec:
    """Tune-o-matic bridge on two posts with a stop-bar tailpiece.

    Nothing is routed; four holes take the post and stud inserts. Note
    that a Tune-o-matic on a flat-topped body normally wants a neck angle
    or a recessed bridge — this model gives neither.

    Args:
        post_spacing: Centre distance between the bridge posts.
        post_hole_diameter: Post insert hole diameter (Nashville-style
            inserts; ABR-1 wood-screw posts need about 4 mm).
        post_hole_depth: Post insert hole depth.
        compensation: Post centres behind the scale line.
        stud_spacing: Centre distance between the tailpiece studs.
        stud_hole_diameter: Tailpiece insert hole diameter.
        stud_hole_depth: Tailpiece insert hole depth.
        tailpiece_offset: Tailpiece stud centres behind the scale line.
    """

    kind: Literal["tune_o_matic"] = "tune_o_matic"
    post_spacing: float = 74.0
    post_hole_diameter: float = 11.2
    post_hole_depth: float = 20.0
    compensation: float = 3.0
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
        post_x = scale_length + self.compensation
        stud_x = scale_length + self.tailpiece_offset
        holes: list[DrilledHole] = []
        for side, sign in (("bass", -1.0), ("treble", 1.0)):
            holes.append(
                DrilledHole(
                    f"Bridge post {side}",
                    post_x,
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
                "Tune-o-matic: a flat body needs a neck angle or a recessed bridge "
                "to reach playing height.",
            ),
        )


@dataclass(frozen=True, slots=True)
class HardtailSpec:
    """Flat string-through hardtail bridge.

    Six string holes pass through the body behind the saddles; the
    baseplate screws are pilot-drilled along its front edge.

    Args:
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
        holes: list[DrilledHole] = []
        string_x = scale_length + self.string_hole_offset
        for index in range(6):
            y = (index - 2.5) * self.string_spacing
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
            notes=("Hardtail: counterbore the string ferrules on the back by hand.",),
        )


BridgeSpec = KahlerBridgeSpec | FloydRoseSpec | TuneOMaticSpec | HardtailSpec

BRIDGE_KINDS: dict[str, type[Any]] = {
    "kahler_7300": KahlerBridgeSpec,
    "floyd_rose": FloydRoseSpec,
    "tune_o_matic": TuneOMaticSpec,
    "hardtail": HardtailSpec,
}

BRIDGE_LABELS: dict[str, str] = {
    "kahler_7300": "Kahler 7300 (fixed, flat mount)",
    "floyd_rose": "Floyd Rose (recessed tremolo)",
    "tune_o_matic": "Tune-o-matic + stop bar",
    "hardtail": "Hardtail (string-through)",
}


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
            raise BodyGeometryError(
                f"Bridge {name} must be finite and positive."
            )

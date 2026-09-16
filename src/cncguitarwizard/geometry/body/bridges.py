"""Interchangeable bridge hardware: what each bridge needs cut into the body.

A bridge is described by a small frozen dataclass of dimensions (a
*spec*). Asking the spec for its ``hardware`` at a given scale length and
body thickness yields every body feature that bridge requires — pivot or
post holes, top routes, routes that pass clean through into a rear cavity,
rear cavities with their cover recesses — ready for ``BodySolid``.

Every dimension here is a labelled, adjustable starting value, not a
verified manufacturer template: measure the real hardware before cutting.
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
from .hardware import (
    BridgeMounting,
    Cavity,
    DrilledHole,
    RearCavity,
    RectangularCavity,
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
    """Recessed Floyd Rose-style double-locking tremolo.

    Two pivot studs on the scale line, a recess so the baseplate sits
    flush with the top, a sustain-block route through the body, and a
    rear spring cavity with a cover recess. The trem-claw screws go into
    the spring cavity's nut-ward wall by hand.

    Args:
        pivot_stud_spacing: Centre distance between the two stud inserts.
        pivot_hole_diameter: Insert hole diameter.
        pivot_hole_depth: Insert hole depth.
        pivot_offset: Stud centres behind the scale line.
        recess_length: Baseplate/fine-tuner recess length along the neck.
        recess_width: Recess width across the body.
        recess_front_offset: Recess front edge behind the scale line
            (negative = ahead of it).
        recess_depth: Recess depth from the top.
        block_route_length: Sustain-block route length along the neck.
        block_route_width: Sustain-block route width across the body.
        block_route_offset: Route centre behind the scale line.
        spring_cavity_length: Rear spring cavity length along the neck.
        spring_cavity_width: Rear spring cavity width across the body.
        spring_cavity_offset: Cavity centre behind the scale line.
        spring_cavity_floor_wall: Wood left between the recess floor and
            the spring cavity.
        cover_margin: Cover recess overhang around the spring cavity.
        cover_depth: Cover recess depth.
    """

    kind: Literal["floyd_rose"] = "floyd_rose"
    pivot_stud_spacing: float = 74.0
    pivot_hole_diameter: float = 10.0
    pivot_hole_depth: float = 22.0
    pivot_offset: float = 0.0
    recess_length: float = 60.0
    recess_width: float = 84.0
    recess_front_offset: float = -6.0
    recess_depth: float = 16.0
    block_route_length: float = 24.0
    block_route_width: float = 40.0
    block_route_offset: float = 12.0
    spring_cavity_length: float = 45.0
    spring_cavity_width: float = 95.0
    spring_cavity_offset: float = 32.0
    spring_cavity_floor_wall: float = 6.0
    cover_margin: float = 5.0
    cover_depth: float = 2.0

    def hardware(self, scale_length: float, body_thickness: float) -> BridgeHardware:
        _positive(
            self,
            "pivot_stud_spacing",
            "pivot_hole_diameter",
            "pivot_hole_depth",
            "recess_length",
            "recess_width",
            "recess_depth",
            "block_route_length",
            "block_route_width",
            "spring_cavity_length",
            "spring_cavity_width",
            "spring_cavity_floor_wall",
            "cover_margin",
            "cover_depth",
        )
        pivot_x = scale_length + self.pivot_offset
        spring_depth = (
            body_thickness - self.recess_depth - self.spring_cavity_floor_wall
        )
        if spring_depth <= self.cover_depth:
            raise BodyGeometryError(
                "Floyd Rose spring cavity would have no depth: the body is too "
                "thin for the recess and floor wall."
            )
        mounting = BridgeMounting(
            pivot_x,
            pivot_stud_spacing=self.pivot_stud_spacing,
            pivot_hole_diameter=self.pivot_hole_diameter,
            pivot_hole_depth=self.pivot_hole_depth,
            has_sustain_block=False,
        )
        recess = RectangularCavity(
            "Tremolo recess",
            pivot_x + self.recess_front_offset + self.recess_length / 2.0,
            0.0,
            self.recess_length,
            self.recess_width,
            self.recess_depth,
            corner_radius=4.0,
        )
        block_route = RectangularCavity(
            "Sustain-block route",
            pivot_x + self.block_route_offset,
            0.0,
            self.block_route_length,
            self.block_route_width,
            body_thickness,
            corner_radius=3.0,
        )
        spring_x = pivot_x + self.spring_cavity_offset
        spring_cavity = RearCavity(
            RectangularCavity(
                "Tremolo spring cavity",
                spring_x,
                0.0,
                self.spring_cavity_length,
                self.spring_cavity_width,
                spring_depth,
                corner_radius=6.0,
            ),
            RectangularCavity(
                "Tremolo spring cavity cover recess",
                spring_x,
                0.0,
                self.spring_cavity_length + 2.0 * self.cover_margin,
                self.spring_cavity_width + 2.0 * self.cover_margin,
                self.cover_depth,
                corner_radius=6.0 + self.cover_margin,
            ),
        )
        return BridgeHardware(
            mounting,
            top_cavities=(recess,),
            through_cavities=(block_route,),
            rear_cavities=(spring_cavity,),
            notes=(
                "Floyd Rose: drill the two trem-claw screw holes into the spring "
                "cavity's nut-ward wall by hand.",
                "Dimensions are starting values; check them against the unit.",
            ),
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

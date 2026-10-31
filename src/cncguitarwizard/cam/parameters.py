"""Tool, feed, and fixturing parameters for the 2.5D toolpath planner."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal

from .exceptions import ToolpathError

PostProcessor = Literal["grbl", "linuxcnc", "mach3", "marlin", "fanuc", "kosy"]
"""The G-code dialect the programs are written in (see ``cam.gcode``)."""

POST_PROCESSOR_LABELS: dict[str, str] = {
    "grbl": "GRBL (grblHAL, FluidNC, Carbide Motion, UGS, Candle)",
    "linuxcnc": "LinuxCNC",
    "mach3": "Mach3 / Mach4 / UCCNC",
    "marlin": "Marlin",
    "fanuc": "Fanuc-style industrial control",
    "kosy": "KOSY / nccad (.KNC)",
}
"""A readable name for each post processor."""

INDEX_PIN_DIAMETER = 6.0
"""The index pins' diameter, in mm, where the tool is no wider."""

CUTTER_FIELDS = (
    "tool_diameter",
    "tool_tip",
    "step_down",
    "step_over",
    "spindle_speed",
    "feed_rate",
    "plunge_rate",
    "rapid_rate",
    "safe_height",
    "small_hole_tool_diameter",
    "small_hole_step_down",
    "eco_mode",
)
"""What a part's own tool takes from the machining form's cutter
(``with_cutter``): its size and how it is run (eco mode too), and the small
end mill's (for what it is too wide to cut); the part's blank and
fixturing stay its own."""

ECO_LINK_DIAMETERS = 2.0
"""How far, in tool diameters, a finishing pass in eco mode hops to its
next run fed across in the cut rather than lifted over
(``MachiningParameters.eco_link_distance``)."""


def depth_per_pass(step_down: float, diameter: float) -> float:
    """Return ``step_down``, or half ``diameter`` for ``0``."""
    return step_down if step_down > 0.0 else diameter / 2.0


@dataclass(frozen=True, slots=True)
class MachiningParameters:
    """One end mill and the feeds, depths, and fixturing it is run with.

    Every distance is in millimetres, every feed in millimetres per
    minute. The defaults describe the TwoTrees H40 / GRBL setup from the
    Prototype001 manufacturing specification: a single 6 mm end mill,
    at most 3 mm axial step-down, a 0.30 mm wall finishing allowance,
    and two 6 mm index pins on the centerline for two-sided machining.

    Args:
        tool_diameter: Cutting diameter of the end mill.
        tool_tip: ``"flat"`` for a square end mill, ``"ball"`` for a ball
            nose of the same diameter (only surfacing cares), ``"vee"`` for
            the engraving V-bit (its diameter the groove's width).
        spindle_speed: Spindle speed in rpm, emitted with ``M3``.
        feed_rate: Cutting feed for XY moves.
        plunge_rate: Feed for straight plunges and helical descents.
        rapid_rate: Nominal rapid speed, used only for time estimates.
        step_down: Maximum axial depth of cut per pass; ``0`` (the
            default) for half the tool's diameter.
        step_over: Radial engagement between raster rows, as a fraction
            of the tool diameter.
        finishing_allowance: Wall stock left by roughing and removed by
            the finishing contour.
        safe_height: Z height for rapid traverses above the stock top.
        through_overshoot: Extra depth below a through feature so the
            cutter clears the far face.
        tab_count: Holding tabs left on the final profile passes.
        tab_length: Length of each tab along the profile.
        tab_height: Height of each tab above the profile floor.
        index_pin_diameter: Diameter of the two-sided-machining dowels,
            or ``None`` (the default) for 6 mm, or the tool's own
            diameter where it is wider: the holes are drilled with the
            tool, so a dowel cannot be narrower than it (an 8 mm end mill
            takes 8 mm dowels).
        index_pin_positions: Dowel centres in the model frame, or ``None``
            to place them automatically on the centerline in the blank's
            waste — in the horn gap ahead of the neck pocket and in the
            tail notch behind the body — so the holes never end up in
            the finished part. The first one is the G-code work origin
            (X = 0, Y = 0).
        index_pin_wall: Wood left between a dowel hole and the nearest
            cut (outline profile or cavity), beyond the tool diameter.
        stock_margin: Waste around the body outline on every side; the
            blank is the outline's bounding box grown by this much.
        stock_edge_margin: Minimum distance from a dowel hole to the
            blank's edge.
        small_hole_tool_diameter: Diameter of the drill or end mill used
            in a separate program for holes smaller than the main tool
            (string-through and pilot holes), and for the cover plates
            cut from sheet.
        small_hole_step_down: How deep the small end mill cuts per pass;
            ``0`` (the default) for half its diameter (the cover plates,
            in sheet, at most 1 mm).
        ball_tool_diameter: The ball nose's diameter: the neck's back,
            the fretboard's radius and scallops, a body's edges; ``0``
            (the default) for the main tool's.
        ball_step_down: How deep the ball nose cuts per pass; ``0`` (the
            default) for half its diameter.
        profile_overlap: How far each side's outline profile cuts past
            the mid-plane so the two half-depth cuts meet.
        raster_link_spacing: Sample spacing when checking whether a link
            between raster rows can stay in the cut.
        post_processor: The G-code dialect: ``"grbl"`` (default; also
            grblHAL, FluidNC and similar senders), ``"linuxcnc"``,
            ``"mach3"`` (Mach3/4, UCCNC), ``"marlin"``, ``"fanuc"``
            (Fanuc-style industrial controls) or ``"kosy"`` (KOSY / nccad
            ``.KNC`` programs).
        spindle_dwell: Seconds to wait after starting the spindle, for a
            spindle that needs time to reach speed; ``0`` for none.
        z_lift_rate: How fast the cutter lifts and comes back down above
            the work, in mm/min: every Z move outside the cut written as a
            feed move at that speed (``G1``), so the Z axis is never driven
            at the machine's top speed. A heavy spindle's Z motor that
            stalls lifting loses steps, and every later cut goes deeper.
            ``0`` (the default): rapids (``G0``), at the machine's speed.
        eco_mode: Build the programs to cut as little air as they can.
            The cutter comes down fast (``G0``) to 1 mm over the floor its
            last pass left, not to the stock top, before it feeds down: a
            pocket's passes after its first, a hole's pecks after its
            first. A pocket's passes run from where the last one ended,
            every other one the other way round, and its finishing wall
            starts nearest where the clearing ended: no long feed across
            the cut pocket between them. A ball nose finishing a surface an
            end mill roughed (a neck's back, a carved top) runs only where
            the end mill left wood, its runs taken nearest first, fed
            across to the next where it is near. Off (the default) keeps
            the programs as they were.
        combine_programs: Join a part's programs that run one after
            another with the same tool, fixture and work zero into one
            program (``Body_back`` and ``Body_back_controls`` become
            ``Body_back_and_controls``), so nothing is loaded or started
            in between; off (the default) keeps one program per setup, to
            run or rerun apart.
        machine_x_travel: How far the machine reaches along X (its width),
            in mm; none (the default) limits nothing. Every part is cut
            lying along X, sideways; one that does not fit that way but
            fits along Y has all its programs turned a quarter to run
            along Y (``cam.fitted_to_machine``): on a 750 x 1000 mm
            machine, anything over 750 mm long.
        machine_y_travel: How far the machine reaches along Y (its
            length), in mm; none (the default) limits nothing.
        neck_blank: The neck blank the build plans for: ``"solid"``, one
            plank as thick as the headstock needs, or ``"laminated"``, the
            neck cut from its own plank first and the headstock after a
            block is glued under it (``NeckMachiningParameters.blank``).
        neck_back_cut: How the neck's back is carved: ``"rough_and_finish"``,
            the flat end mill roughing it and the ball nose finishing it in
            two programs, or ``"ball"``, the ball nose alone in one program,
            roughing in layers and then finishing, no tool change
            (``NeckMachiningParameters.back_cut``).
        engraving_tool_angle: The engraving V-bit's included angle, in
            degrees (its groove is ``2 * depth * tan(angle / 2)`` wide).
        engraving_step_down: Depth cut per engraving pass.
        engraving_feed_rate: Feed along the engraved lines.
        relief_tool_diameter: The flat end mill clearing a relief
            engraving's shapes (the camo pattern) to their levels.
        relief_step_down: How deep that end mill cuts per pass; ``0`` (the
            default) for half its diameter.
        fret_slot_spindle_speed: The 0.6 mm fret-slot cutter's spindle
            speed, rpm (30 000 by default: a cutter that thin wants it
            fast).
        fret_slot_tool_diameter: The fret-slot cutter's diameter, in mm
            (0.6 by default): the slots come out its width.
        fret_slot_step_down: The most the fret-slot cutter goes down per
            pass, in mm (0.2 by default, so it does not snap); the slot's
            depth is split into equal passes no deeper.
        inlay_spindle_speed: The 1 mm inlay cutter's spindle speed, rpm
            (30 000 by default), for the inlay pockets, a slotted nut's
            slot and the inlay pieces cut from sheet.
        inlay_tool_diameter: The inlay cutter's diameter, in mm (1 by
            default).
        inlay_step_down: The most the inlay cutter goes down per pass, in
            mm (0.2 by default, so it does not snap).
        nut_jig_tool_diameter: The cutter the nut-slot jig (nut_jig) is
            cut with, in mm: 0.6 by default, the fret-slot cutter's
            size, at the fret-slot speed and step-down. A slot narrower than
            it comes out its width; a cutter no wider than the thinnest
            string's slot (0.3 mm for a .010) cuts every slot its own width,
            in a sheet no thicker than it reaches through. Under 1.4 mm.
        carve_tool_diameter: The flat end mill roughing a carved top;
            ``0`` uses the main tool. A bigger one roughs the arch far
            quicker (the time goes with the wood over its width).
        carve_step_down: How deep the carve's roughing tool cuts per pass;
            ``0`` (the default) for half its diameter, or the main tool's
            step-down when it is the main tool.
        carve_finish: Finish a carved top with a ball nose as wide as its
            roughing tool, in fine passes; off (the default) leaves the
            roughing's rows, the flat tool following the arch, to sand
            smooth by hand, as a carve routed in steps is.
        carve_flat_tool_diameter: A big flat end mill (25.4 mm, an inch)
            that takes a carved top's flat parts first, in a program of
            its own: the rim along the edge cut flat to its level and the
            bulk of the wood off the fall; the roughing tool then cuts
            only what it left, and the ball nose only the fall, never the
            flat plateau and rim. ``0`` (the default) for none.
        carve_flat_step_down: How deep that big end mill cuts per pass;
            ``0`` (the default) for half its diameter.
        fretboard_blank_length: The fretboard blank's length, in mm, the
            board centred on it (a bought blank, 540 mm say); none (the
            default) cuts it from stock 35 mm longer at each end, longer
            still where the index pins need it.
        fretboard_blank_width: The fretboard blank's width, in mm, the
            board centred on it (70 mm say); none (the default) leaves
            35 mm of waste each side.
        fretboard_blank_thickness: The fretboard blank's thickness before
            the radius is cut, in mm (7 by default); at least the board's
            ``fretboard_thickness``. The radius takes the rest off the
            top, roughed in layers first where it is deeper than the ball
            nose's step-down.
        fretboard_carrier_thickness: A carrier board under the fretboard
            blank, in mm: the blank glued (or taped) on it, the index pins
            go through it past the blank's ends where the blank is too
            short to take them (the program's notes give how far). None
            (the default): no carrier, and the pins must fit in the blank.

    Raises:
        ToolpathError: If any value is non-finite or out of its range.
    """

    tool_diameter: float = 6.0
    tool_tip: str = "flat"
    spindle_speed: float = 10000.0
    feed_rate: float = 1000.0
    plunge_rate: float = 300.0
    rapid_rate: float = 3000.0
    step_down: float = 0.0
    step_over: float = 0.4
    finishing_allowance: float = 0.3
    safe_height: float = 5.0
    through_overshoot: float = 0.5
    tab_count: int = 6
    tab_length: float = 8.0
    tab_height: float = 4.0
    index_pin_diameter: float | None = None
    index_pin_positions: tuple[tuple[float, float], ...] | None = None
    index_pin_wall: float = 3.0
    stock_margin: float = 15.0
    stock_edge_margin: float = 8.0
    small_hole_tool_diameter: float = 3.0
    small_hole_step_down: float = 0.0
    ball_tool_diameter: float = 0.0
    ball_step_down: float = 0.0
    profile_overlap: float = 0.5
    raster_link_spacing: float = 1.0
    post_processor: PostProcessor = "grbl"
    spindle_dwell: float = 0.0
    z_lift_rate: float = 0.0
    eco_mode: bool = False
    combine_programs: bool = False
    machine_x_travel: float | None = None
    machine_y_travel: float | None = None
    neck_blank: Literal["solid", "laminated"] = "solid"
    neck_back_cut: Literal["rough_and_finish", "ball"] = "rough_and_finish"
    engraving_tool_angle: float = 60.0
    engraving_step_down: float = 1.0
    engraving_feed_rate: float = 600.0
    relief_tool_diameter: float = 3.0
    relief_step_down: float = 0.0
    fret_slot_spindle_speed: float = 30000.0
    fret_slot_tool_diameter: float = 0.6
    fret_slot_step_down: float = 0.2
    inlay_spindle_speed: float = 30000.0
    inlay_tool_diameter: float = 1.0
    inlay_step_down: float = 0.2
    nut_jig_tool_diameter: float = 0.6
    carve_tool_diameter: float = 0.0
    carve_step_down: float = 0.0
    carve_finish: bool = False
    carve_flat_tool_diameter: float = 0.0
    carve_flat_step_down: float = 0.0
    fretboard_blank_length: float | None = None
    fretboard_blank_width: float | None = None
    fretboard_blank_thickness: float = 7.0
    fretboard_carrier_thickness: float | None = None

    def __post_init__(self) -> None:
        """Reject parameters the planner cannot cut safely with; a
        ``step_down`` of ``0`` becomes half the tool's diameter."""
        if self.step_down == 0.0 and math.isfinite(self.tool_diameter):
            object.__setattr__(self, "step_down", self.tool_diameter / 2.0)
        positive = {
            "tool_diameter": self.tool_diameter,
            "spindle_speed": self.spindle_speed,
            "feed_rate": self.feed_rate,
            "plunge_rate": self.plunge_rate,
            "rapid_rate": self.rapid_rate,
            "step_down": self.step_down,
            "safe_height": self.safe_height,
            "tab_length": self.tab_length,
            "tab_height": self.tab_height,
            "stock_margin": self.stock_margin,
            "stock_edge_margin": self.stock_edge_margin,
            "small_hole_tool_diameter": self.small_hole_tool_diameter,
            "raster_link_spacing": self.raster_link_spacing,
            "engraving_step_down": self.engraving_step_down,
            "engraving_feed_rate": self.engraving_feed_rate,
            "relief_tool_diameter": self.relief_tool_diameter,
            "fret_slot_spindle_speed": self.fret_slot_spindle_speed,
            "fret_slot_step_down": self.fret_slot_step_down,
            "inlay_spindle_speed": self.inlay_spindle_speed,
            "inlay_step_down": self.inlay_step_down,
            "nut_jig_tool_diameter": self.nut_jig_tool_diameter,
            "fret_slot_tool_diameter": self.fret_slot_tool_diameter,
            "inlay_tool_diameter": self.inlay_tool_diameter,
            "fretboard_blank_thickness": self.fretboard_blank_thickness,
        }
        for name, value in (
            ("index_pin_diameter", self.index_pin_diameter),
            ("fretboard_blank_length", self.fretboard_blank_length),
            ("fretboard_blank_width", self.fretboard_blank_width),
            ("fretboard_carrier_thickness", self.fretboard_carrier_thickness),
            ("machine_x_travel", self.machine_x_travel),
            ("machine_y_travel", self.machine_y_travel),
        ):
            if value is not None:
                positive[name] = value
        for name, value in positive.items():
            if not math.isfinite(value) or value <= 0.0:
                raise ToolpathError(f"{name} must be finite and positive.")
        non_negative = {
            "finishing_allowance": self.finishing_allowance,
            "through_overshoot": self.through_overshoot,
            "profile_overlap": self.profile_overlap,
            "index_pin_wall": self.index_pin_wall,
            "spindle_dwell": self.spindle_dwell,
            "z_lift_rate": self.z_lift_rate,
            "carve_tool_diameter": self.carve_tool_diameter,
            "carve_flat_tool_diameter": self.carve_flat_tool_diameter,
            "small_hole_step_down": self.small_hole_step_down,
            "ball_tool_diameter": self.ball_tool_diameter,
            "ball_step_down": self.ball_step_down,
            "relief_step_down": self.relief_step_down,
            "carve_step_down": self.carve_step_down,
            "carve_flat_step_down": self.carve_flat_step_down,
        }
        for name, value in non_negative.items():
            if not math.isfinite(value) or value < 0.0:
                raise ToolpathError(f"{name} must be finite and non-negative.")
        if self.post_processor not in POST_PROCESSOR_LABELS:
            raise ToolpathError(
                "post_processor must be one of "
                f"{', '.join(POST_PROCESSOR_LABELS)}."
            )
        if self.neck_blank not in ("solid", "laminated"):
            raise ToolpathError('neck_blank must be "solid" or "laminated".')
        if self.neck_back_cut not in ("rough_and_finish", "ball"):
            raise ToolpathError(
                'neck_back_cut must be "rough_and_finish" or "ball".'
            )
        if self.tool_tip not in ("flat", "ball", "vee"):
            raise ToolpathError('tool_tip must be "flat", "ball" or "vee".')
        if not 0.0 < self.engraving_tool_angle < 180.0:
            raise ToolpathError("engraving_tool_angle must lie in (0, 180).")
        if not 0.0 < self.step_over <= 1.0:
            raise ToolpathError("step_over must lie in (0, 1].")
        if self.tab_count < 0:
            raise ToolpathError("tab_count must not be negative.")
        if self.index_pin_positions is not None:
            if len(self.index_pin_positions) != 2:
                raise ToolpathError("Exactly two index pins are required.")
            for x, y in self.index_pin_positions:
                if not math.isfinite(x) or not math.isfinite(y):
                    raise ToolpathError("Index pin positions must be finite.")

    @property
    def pin_diameter(self) -> float:
        """Return the index pins' diameter: ``index_pin_diameter``, else
        6 mm, or the tool's diameter where it is wider."""
        if self.index_pin_diameter is not None:
            return self.index_pin_diameter
        return max(INDEX_PIN_DIAMETER, self.tool_diameter)

    @property
    def tool_radius(self) -> float:
        """Return half the tool diameter."""
        return self.tool_diameter / 2.0

    @property
    def raster_spacing(self) -> float:
        """Return the distance between neighbouring raster rows."""
        return self.tool_diameter * self.step_over

    @property
    def eco_link_distance(self) -> float:
        """Return how far a finishing pass hops to its next run fed across
        in the cut: ``ECO_LINK_DIAMETERS`` tool diameters in eco mode,
        ``0`` (always lifted over) with it off."""
        return ECO_LINK_DIAMETERS * self.tool_diameter if self.eco_mode else 0.0

    @property
    def small_cutter(self) -> MachiningParameters:
        """Return the small end mill's settings: ``small_hole_tool_diameter``
        at ``small_hole_step_down`` a pass, plunging at most 150 mm/min."""
        diameter = self.small_hole_tool_diameter
        return replace(
            self,
            tool_diameter=diameter,
            step_down=depth_per_pass(self.small_hole_step_down, diameter),
            plunge_rate=min(self.plunge_rate, 150.0),
        )

    @property
    def ball_cutter(self) -> MachiningParameters:
        """Return the ball nose's settings: ``ball_tool_diameter`` (else
        the main tool's) at ``ball_step_down`` a pass."""
        diameter = self.ball_tool_diameter or self.tool_diameter
        return replace(
            self,
            tool_tip="ball",
            tool_diameter=diameter,
            step_down=depth_per_pass(self.ball_step_down, diameter),
        )

    @property
    def relief_cutter(self) -> MachiningParameters:
        """Return the relief end mill's settings: ``relief_tool_diameter``
        at ``relief_step_down`` a pass, plunging at most 150 mm/min."""
        diameter = self.relief_tool_diameter
        return replace(
            self,
            tool_diameter=diameter,
            step_down=depth_per_pass(self.relief_step_down, diameter),
            plunge_rate=min(self.plunge_rate, 150.0),
        )

    @property
    def carve_cutter(self) -> MachiningParameters:
        """Return the carve's roughing tool's settings: its own
        (``carve_tool_diameter``, ``carve_step_down``) or the main tool,
        at ``carve_step_down`` a pass when set."""
        if self.carve_tool_diameter <= 0.0:
            if self.carve_step_down <= 0.0:
                return self
            return replace(self, step_down=self.carve_step_down)
        diameter = self.carve_tool_diameter
        return replace(
            self,
            tool_diameter=diameter,
            step_down=depth_per_pass(self.carve_step_down, diameter),
        )

    @property
    def carve_flat_cutter(self) -> MachiningParameters | None:
        """Return the carve's big flat end mill's settings
        (``carve_flat_tool_diameter``, ``carve_flat_step_down``), or
        ``None`` for none."""
        diameter = self.carve_flat_tool_diameter
        if diameter <= 0.0:
            return None
        return replace(
            self,
            tool_diameter=diameter,
            step_down=depth_per_pass(self.carve_flat_step_down, diameter),
        )


def with_cutter(
    tool: MachiningParameters, cutter: MachiningParameters
) -> MachiningParameters:
    """Return a part's own ``tool`` cutting as the machining form's
    ``cutter`` does (``CUTTER_FIELDS``): its size, depth and speeds, and
    eco mode."""
    return replace(tool, **{name: getattr(cutter, name) for name in CUTTER_FIELDS})

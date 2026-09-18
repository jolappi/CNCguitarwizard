"""Locked but configurable parameters for the first complete neck."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from ..geometry.body import (
    BodySolid,
    BridgeSpec,
    CircularCavity,
    DrilledHole,
    JackHole,
    KahlerBridgeSpec,
    RearCavity,
    TracedCavity,
    TracedOutline,
)
from ..geometry.exceptions import NeckGeometryError
from ..geometry.fretboard import (
    Fretboard,
    FretboardSurface,
    FretLayout,
    InlayLayout,
    InlayStyle,
)
from ..geometry.neck import (
    Centerline,
    HeadstockAngleReference,
    HeadstockPlan,
    HeadstockSolid,
    NeckBackSurface,
    NeckOutline,
    Side,
    TrussRodChannel,
    TunerLayout,
)
from ..geometry.primitives import Point2D
from ._omarunko_outline import (
    OMARUNKO_CONTROL_CAVITY_POINTS,
    OMARUNKO_CONTROL_COVER_POINTS,
    OMARUNKO_HEEL_END_X,
    OMARUNKO_OUTLINE_POINTS,
    OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS,
)

HeadstockStyle = Literal["3+3", "6_inline", "6_inline_reverse", "4+2", "2+4"]
"""Tuner arrangements: bass+treble counts; "reverse" puts the row on the treble side."""

HEADSTOCK_STYLES: dict[str, tuple[int, int]] = {
    "3+3": (3, 3),
    "6_inline": (6, 0),
    "6_inline_reverse": (0, 6),
    "4+2": (4, 2),
    "2+4": (2, 4),
}
"""Tuner counts on the (bass, treble) side for every headstock style."""

HEADSTOCK_RESERVES: dict[
    str, tuple[tuple[float | None, float | None], tuple[float | None, float | None]]
] = {
    "6_inline": ((36.0, None), (35.0, 60.0)),
    "6_inline_reverse": ((36.0, None), (35.0, 60.0)),
    "4+2": ((36.0, 15.0), (40.0, 30.0)),
    "2+4": ((36.0, 15.0), (40.0, 30.0)),
}
"""Least (shoulder, tip) half-widths kept on the row side and the other side.

``None`` leaves that end to the edge fitted through the holes.

Wood left in the blank so a traditional outline can still be carved from
it: a Strat headstock's treble lobe beside a six-in-line row (the row's
own edge follows its posts, which sit on the strings' lines and so run
diagonally across the centreline), a Music Man's root lobe and narrow tip
around 4+2. A 3+3 has no reserve; its edges follow the holes exactly.
"""


@dataclass(frozen=True, slots=True)
class Prototype001Geometry:
    """Contain every backend-independent component of Prototype001."""

    neck_outline: NeckOutline
    neck_surface: NeckBackSurface
    fretboard_surface: FretboardSurface
    fret_layout: FretLayout
    truss_rod_channel: TrussRodChannel
    headstock: HeadstockSolid
    tuner_layout: TunerLayout
    inlay_layout: InlayLayout
    body: BodySolid
    fret_slot_width: float
    fret_slot_depth: float
    tuner_chamfer_depth: float
    joint_fillet_radius: float
    headstock_root_swell: float
    nut_end_u_trim_depth: float
    nut_end_u_side_fillet_radius: float
    headstock_outer_d_profile_guide_extension: float
    heel_nose_radius: float
    heel_block_start_offset: float


@dataclass(frozen=True, slots=True)
class _HeadstockLayout:
    """The resolved headstock plan settings and tuner stations of a style."""

    length: float
    shoulder_width: float
    shoulder_shift: float
    tip_width: float
    tip_shift: float
    bass_sign: float
    stations: tuple[float, ...]
    sides: tuple[Side, ...] | None
    offsets: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class Prototype001Parameters:
    """Define the complete first CNCguitarwizard neck in millimetres.

    First- and twelfth-fret thicknesses are total centerline dimensions from
    the playing surface to the neck back. Heel thickness describes neck wood
    below the separate fretboard, matching the specified 20 mm + fretboard.
    """

    scale_length: float = 609.6
    fret_count: int = 24
    nut_width: float = 42.0
    final_fret_width: float = 56.0
    heel_width: float = 56.0
    heel_mounting_length: float = 54.0
    heel_length: float = 4.0
    fretboard_end_extension: float = 4.0
    # Square nut-end corners: the board meets the nut with no rounding.
    fretboard_nut_corner_radius: float = 0.0
    first_fret_thickness: float = 17.0
    twelfth_fret_thickness: float = 19.0
    heel_thickness: float = 20.0
    fretboard_radius: float = 430.0
    fretboard_thickness: float = 6.0
    fret_slot_width: float = 0.6
    fret_slot_depth: float = 2.7
    # Position markers, cut as flat-bottomed pockets into the playing
    # surface: barbed wire (default), round dots, or Gibson-style blocks
    # that follow the taper. 12 and 24 get the traditional double layout
    # (blocks stay single); every other listed fret gets one marker.
    inlay_depth: float = 2.0
    inlay_single_marker_frets: tuple[int, ...] = (3, 5, 7, 9, 15, 17, 19, 21)
    inlay_double_marker_frets: tuple[int, ...] = (12, 24)
    inlay_style: InlayStyle = "barbed_wire"
    inlay_dot_diameter: float = 6.0
    inlay_block_length_fraction: float = 0.6
    inlay_block_edge_margin: float = 5.0
    # Solid body (left-handed): outline, pickup routes, bridge baseplate
    # cutout, and the rear control and switch cavities (each with its
    # cover recess) are all digitised directly from the user's own
    # assets/reference/omarunko.dxf (see _omarunko_outline.py) — the actual
    # shapes, not an approximation. The baseplate cutout depth remains a placeholder
    # (no Kahler 7300 manufacturer template was available).
    body_thickness: float = 44.0
    # The neck pocket is the neck's own tapered outline over the last
    # body_neck_pocket_length millimetres before the heel end, widened
    # by body_neck_pocket_clearance per side. It ends exactly where the
    # heel ends, opens onto the horn gap at its nut-ward end as in the
    # drawing, and follows any change of scale, fret count or neck
    # width by construction.
    body_neck_pocket_length: float = 79.48
    body_neck_pocket_clearance: float = 0.15
    # Longitudinal placements are offsets, not absolute positions. The
    # traced body — outline, neck pickup, control and switch cavities,
    # pots, jack — rides with the neck's heel end; the bridge features
    # — baseplate cutout, bridge pickup — ride with the scale length.
    # A different scale or fret count therefore keeps the neck in its
    # pocket and the bridge on the scale, and only the bridge's place
    # on the body changes. The defaults are the DXF's own distances.
    # Pickup routes use the drawing's own route shape
    # (OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS, a humbucker with mounting-ear
    # tabs).
    body_neck_pickup_offset: float = 30.5  # route centre past the heel end
    # The bridge pickup sits body_bridge_pickup_offset ahead of the scale
    # line, but moves further forward on its own when the chosen bridge's
    # routes reach ahead of the scale line (a recessed Floyd Rose), keeping
    # body_bridge_pickup_clearance of wood between route and recess.
    body_bridge_pickup_offset: float = 21.73  # route centre before the bridge
    body_bridge_pickup_clearance: float = 3.0
    body_pickup_route_depth: float = 22.0
    # Clearance recesses for the pickup height-adjustment screw tips,
    # drilled on down from the route floor at the centre of each of the
    # route's two mounting-ear tabs (the DXF ears are centred 39.95 mm
    # either side of the string line).
    body_pickup_screw_spacing: float = 79.9
    body_pickup_screw_recess_diameter: float = 6.0
    body_pickup_screw_recess_extra_depth: float = 8.0
    # The bridge is an interchangeable spec (see geometry.body.bridges):
    # KahlerBridgeSpec (default, the DXF's flat-mount 7300 cutout),
    # FloydRoseSpec, TuneOMaticSpec or HardtailSpec. Each places its own
    # routes, rear cavities and holes relative to the scale line. In the
    # web form it is edited as JSON with a "kind" entry.
    body_bridge: BridgeSpec = field(default_factory=KahlerBridgeSpec)
    # Rear-routed electronics cavities, both straight from the DXF. Each
    # is cut up from the back face to within body_rear_cavity_top_wall
    # of the top so the pot and switch bushings can pass through, and is
    # closed by a cover plate seated in a body_cover_recess_depth ledge
    # — the drawing's own outer ring/circle around each cavity.
    body_rear_cavity_top_wall: float = 8.0
    body_cover_recess_depth: float = 2.0
    # Pickup-selector cavity at the upper-horn root: the DXF's two
    # near-concentric circles (inner = cavity, outer = cover ledge,
    # exactly as drawn, slightly eccentric).
    body_switch_cavity_offset: float = -4.005  # centre X from the heel end
    body_switch_cavity_y: float = -70.565
    body_switch_cavity_diameter: float = 43.972
    body_switch_cover_offset: float = -3.211
    body_switch_cover_y: float = -70.3
    body_switch_cover_diameter: float = 59.452
    # Shaft holes through the top wall: a 1/2" toggle bushing at the
    # switch cavity's centre, and two 3/8" pot bushings side by side
    # along the almond control cavity's long axis.
    body_switch_shaft_hole_diameter: float = 12.7
    body_pot_shaft_hole_diameter: float = 10.0
    body_pot_offsets: tuple[tuple[float, float], ...] = (  # (X from heel end, Y)
        (180.8, 86.0),
        (220.8, 87.0),
    )
    # Output jack on the lower-bout edge, bored in toward the control
    # cavity's tail-ward end so the wiring lands inside it.
    body_jack_offset: float = 280.8  # X from the heel end
    body_jack_y: float = 107.5
    body_jack_direction_degrees: float = 202.5
    body_jack_diameter: float = 12.5
    body_jack_depth: float = 55.0
    truss_rod_start: float = 12.0
    truss_rod_length: float = 440.0
    truss_rod_width: float = 6.0
    truss_rod_depth: float = 9.0
    # Headstock style: "3+3" mirrors tuner_station_distances /
    # tuner_side_offsets onto both sides. The row styles (six in line on
    # the bass or, for "reverse", the treble edge; 4+2 with the pair at
    # the root) space tuner_inline_* stations along the row and put every
    # post on its own string's straight line past the nut
    # (nut_string_spacing / bridge_string_spacing, the post
    # tuner_post_diameter/2 outboard of the string), so no string bends
    # at the nut. Every edge with tuners follows them tuner_edge_offset
    # further out (a line fitted through the holes), but never inside
    # the style's wood reserve (HEADSTOCK_RESERVES): a six-in-line blank
    # keeps room for a Strat outline, a 4+2 blank for a Music Man one.
    # The headstock grows past headstock_length when the last tuner
    # needs it. headstock_bass_side says where the low E is: -Y on the
    # left-handed Prototype001 body (the long-horn side). The shoulder
    # and tip widths and shifts, when set, override the resolved ends
    # (shifts toward the bass side positive).
    headstock_style: HeadstockStyle = "3+3"
    headstock_bass_side: Literal["-y", "+y"] = "-y"
    headstock_length: float = 150.0
    headstock_root_length: float = 45.0
    headstock_shoulder_width: float | None = None
    headstock_tip_width: float | None = None
    headstock_shoulder_shift: float | None = None
    headstock_tip_shift: float | None = None
    headstock_angle: float = 8.0
    headstock_thickness: float = 16.0
    tuner_hole_diameter: float = 10.0
    tuner_station_distances: tuple[float, float, float] = (55.0, 85.0, 110.0)
    tuner_side_offsets: tuple[float, float, float] = (15.0, 12.0, 10.0)
    tuner_inline_first_distance: float = 50.0
    tuner_inline_spacing: float = 25.4
    tuner_edge_offset: float = 15.0
    tuner_tip_margin: float = 5.0
    tuner_post_diameter: float = 6.0
    nut_string_spacing: float = 7.0
    bridge_string_spacing: float = 10.5
    tuner_edge_clearance: float = 8.0
    tuner_hole_clearance: float = 10.0
    tuner_chamfer_depth: float = 0.2
    joint_fillet_radius: float = 3.0
    heel_nose_radius: float = 0.0
    heel_block_overlap: float = 0.0
    nut_shelf_length: float = 5.0
    # A real volute is compact and sits right behind the nut, not a long
    # gradual ramp that keeps the neck close to the raw headstock thickness
    # nearly out to fret 1 (which the previous 30 mm length did: fret 1
    # falls around X=34 mm). 12 mm keeps the whole taper well clear of the
    # fretted area while still being a smooth, tangent-continuous blend.
    headstock_volute_length: float = 12.0
    # Zero: any added swell here is, by definition, a local maximum that
    # must fall back down again to reconnect with its neighbours on both
    # sides — the depth rises toward the headstock, dips back down toward
    # the nut, rises a second time, then falls again into the neck. A
    # smooth monotonic taper (no added bump, using only the existing
    # smoothstep/smootherstep easing) still reads as a single round,
    # continuous curve from neck to headstock, it just never reverses.
    headstock_volute_depth: float = 0.0
    headstock_volute_peak_fraction: float = 0.25
    headstock_root_swell: float = 0.0
    # A real reference Stratocaster neck (measured from an actual STEP
    # model) has an instant depth step and a separately, gradually
    # tapering plan-view width. The depth step in our own model is now a
    # genuine boolean seam (see _headstock_transition_sections), not a
    # blend, so this length only controls how much room the width taper
    # gets — it no longer has to also fit a depth blend into the same
    # span. 15 mm keeps that narrowing visibly gradual rather than
    # cramming the headstock's whole plan width down to the nut width in
    # just a few mm.
    headstock_root_side_extension: float = 15.0
    nut_end_u_trim_depth: float = 12.0
    nut_end_u_side_fillet_radius: float = 2.0
    headstock_outer_d_profile_guide_extension: float = 0.0
    heel_root_length: float = 45.0
    heel_scoop_depth: float = 1.5
    heel_root_center_extension: float = 15.0
    neck_profile_exponent: float = 2.0
    profile_sample_count: int = 33
    segments_per_region: int = 12

    @property
    def heel_flat_start_offset(self) -> float:
        """Return the derived distance from fret 24 to the flat heel start.

        ``heel_mounting_length`` is the user-facing, total length of the
        bolt-on mounting block.  The small ``heel_length`` extension after
        fret 24 is part of that total, so the flat block begins this far
        before fret 24.
        """
        return self.heel_mounting_length - self.heel_length

    @property
    def headstock_shoulder_distance(self) -> float:
        """Return the plan-view distance used to form the headstock root.

        ``HeadstockPlan`` calls this a shoulder distance.  At the preset level
        it is deliberately named a root length: it controls how far the two
        sides run smoothly from the 42 mm neck into the full headstock width.
        It does not add a bulky volute below the player's thumb.
        """
        return self.headstock_root_length

    @property
    def heel_transition_length(self) -> float:
        """Return the longitudinal runout from playing neck into heel block.

        The separately configured ``heel_mounting_length`` remains fully flat
        for the bolt-on pocket.  This root length affects only the smooth
        lead-in immediately before that fixed mounting area.
        """
        return self.heel_root_length

    def _neck_pocket_outline(
        self, outline: NeckOutline, heel_end: float
    ) -> tuple[Point2D, ...]:
        """Return the pocket polygon: the neck's own outline plus clearance.

        The pocket runs from ``heel_end - body_neck_pocket_length`` to
        ``heel_end``; between those the neck is ``nut_width`` wide at
        the nut tapering to ``last_fret_width`` at the last fret, then
        ``heel_width`` to the heel end. Every wall sits
        ``body_neck_pocket_clearance`` outside the neck.
        """
        start = heel_end - self.body_neck_pocket_length
        if start < 0.0:
            raise NeckGeometryError(
                "Neck pocket must not reach past the nut."
            )
        clearance = self.body_neck_pocket_clearance
        last_fret = outline.last_fret_position

        def taper_half_width(x: float) -> float:
            fraction = x / last_fret
            return (
                outline.nut_width
                + (outline.last_fret_width - outline.nut_width) * fraction
            ) / 2.0

        stations: list[tuple[float, float]] = []
        if start < last_fret:
            stations.append((start, taper_half_width(start)))
            stations.append((last_fret, outline.last_fret_width / 2.0))
            if outline.heel_width != outline.last_fret_width:
                stations.append((last_fret, outline.heel_width / 2.0))
        else:
            stations.append((start, outline.heel_width / 2.0))
        stations.append((heel_end, outline.heel_width / 2.0))
        lower = [Point2D(x, -(half + clearance)) for x, half in stations]
        upper = [Point2D(x, half + clearance) for x, half in reversed(stations)]
        return tuple(lower + upper)

    def _headstock_layout(self) -> _HeadstockLayout:
        """Resolve the headstock plan and tuner stations for the style.

        Stations: "3+3" mirrors ``tuner_station_distances`` onto both
        sides with ``tuner_side_offsets``. A row of tuners runs
        ``max(bass, treble)`` stations ``tuner_inline_spacing`` apart along
        the fuller side from ``tuner_inline_first_distance``; a 4+2 pair
        sits at the root on the other side, staggered half a station
        opposite the row's first two.

        Posts: in the row styles every post sits on its own string's
        straight continuation past the nut (the bridge-to-nut line from
        ``bridge_string_spacing`` and ``nut_string_spacing``), the post
        radius outboard of the string, so no string bends at the nut. The
        row takes its side's strings nearest first (low E to the first
        bass post) and the pair the other side's outermost strings, so a
        six-in-line row runs diagonally across the centreline and a 4+2
        row converges toward it. A 3+3 keeps its given offsets: with both
        rows at the same stations, straight strings would put the D and G
        posts too close together.

        Outline: each edge with tuners on it is the straight line fitted
        through those holes ``tuner_edge_offset`` further out, from the
        shoulder to the tip, so every hole sits the same distance from
        its edge — but never inside the style's ``HEADSTOCK_RESERVES``,
        the wood kept for carving a Strat or Music Man outline. An edge
        with no tuners is the reserve alone. Explicit
        ``headstock_shoulder_width`` / ``headstock_shoulder_shift`` /
        ``headstock_tip_width`` / ``headstock_tip_shift`` override the
        resolved ends. The headstock grows past ``headstock_length`` when
        the last tuner needs it.
        """
        bass_sign = -1.0 if self.headstock_bass_side == "-y" else 1.0
        bass_count, treble_count = HEADSTOCK_STYLES[self.headstock_style]
        hole_edge = self.tuner_hole_diameter / 2.0 + self.tuner_edge_clearance
        # Bass-positive lateral position of string n (1 = low E) at a
        # distance past the nut, continuing its bridge-to-nut line.
        def string_u(string: int, distance: float) -> float:
            spacing = self.nut_string_spacing + (
                self.nut_string_spacing - self.bridge_string_spacing
            ) * distance / self.scale_length
            return (3.5 - string) * spacing

        stations: list[tuple[float, Side, float]] = []  # distance, side, u
        sides: tuple[Side, ...] | None
        distances: tuple[float, ...]
        offsets: tuple[float, ...]
        if self.headstock_style == "3+3":
            for distance, offset in zip(
                self.tuner_station_distances, self.tuner_side_offsets, strict=True
            ):
                stations.append((distance, "bass", offset))
                stations.append((distance, "treble", -offset))
            length = self.headstock_length
            sides = None
            distances = self.tuner_station_distances
            offsets = self.tuner_side_offsets
        else:
            row_side: Side
            pair_side: Side
            row_side, pair_side = (
                ("bass", "treble")
                if bass_count >= treble_count
                else ("treble", "bass")
            )
            row_count = max(bass_count, treble_count)
            pair_count = min(bass_count, treble_count)
            first, spacing = self.tuner_inline_first_distance, self.tuner_inline_spacing
            row_strings = (
                list(range(1, row_count + 1))
                if row_side == "bass"
                else list(range(6, 6 - row_count, -1))
            )
            pair_strings = (
                list(range(6, 6 - pair_count, -1))
                if pair_side == "treble"
                else list(range(1, pair_count + 1))
            )
            post_radius = self.tuner_post_diameter / 2.0
            row_distances = [first + index * spacing for index in range(row_count)]
            length = max(
                self.headstock_length,
                max(row_distances) + hole_edge + self.tuner_tip_margin,
            )
            for distance, string in zip(row_distances, row_strings, strict=True):
                sign = 1.0 if row_side == "bass" else -1.0
                post_u = string_u(string, distance) + sign * post_radius
                stations.append((distance, row_side, post_u))
            for step, string in enumerate(pair_strings):
                distance = first + (step + 0.5) * spacing
                sign = 1.0 if pair_side == "bass" else -1.0
                post_u = string_u(string, distance) + sign * post_radius
                stations.append((distance, pair_side, post_u))
            sides = tuple(side for _, side, _ in stations)
            distances = tuple(distance for distance, _, _ in stations)
            # Offsets are measured toward the hole's own side; a row post
            # past the centreline gets a negative one.
            offsets = tuple(
                u if side == "bass" else -u for _, side, u in stations
            )

        # Edges: fit each side's line through its holes, edge_offset out,
        # never inside the style's reserve; then, keeping the shoulder
        # end, push the tip end out until the line clears every hole (a
        # row that has crossed the centreline needs room on the far side
        # too) by tuner_edge_clearance.
        root = self.headstock_root_length
        reserve = HEADSTOCK_RESERVES.get(self.headstock_style)
        row_side_of_style: Side = (
            "bass" if bass_count >= treble_count else "treble"
        )
        halves: dict[Side, tuple[float, float]] = {}
        for side in ("bass", "treble"):
            sign = 1.0 if side == "bass" else -1.0
            reserve_shoulder, reserve_tip = (
                (None, None)
                if reserve is None
                else reserve[0 if side == row_side_of_style else 1]
            )
            points = [
                (distance, sign * u + self.tuner_edge_offset)
                for distance, hole_side, u in stations
                if hole_side == side
            ]
            if len(points) >= 2:
                mean_d = sum(d for d, _ in points) / len(points)
                mean_e = sum(e for _, e in points) / len(points)
                slope = sum((d - mean_d) * (e - mean_e) for d, e in points) / sum(
                    (d - mean_d) ** 2 for d, _ in points
                )
                shoulder_half = mean_e + slope * (root - mean_d)
                tip_half = mean_e + slope * (length - mean_d)
                if reserve_shoulder is not None:
                    shoulder_half = max(shoulder_half, reserve_shoulder)
                if reserve_tip is not None:
                    tip_half = max(tip_half, reserve_tip)
            else:
                shoulder_half = reserve_shoulder or 0.0
                tip_half = reserve_tip or 0.0
            for distance, _, u in stations:
                fraction = (distance - root) / (length - root)
                if fraction <= 0.0:
                    continue
                required = sign * u + hole_edge + 0.01
                tip_half = max(
                    tip_half, (required - shoulder_half * (1.0 - fraction)) / fraction
                )
            halves[side] = (shoulder_half, tip_half)
        shoulder_bass, tip_bass = halves["bass"]
        shoulder_treble, tip_treble = halves["treble"]
        shoulder_width = shoulder_bass + shoulder_treble
        shoulder_shift = (shoulder_bass - shoulder_treble) / 2.0
        tip_width_final = tip_bass + tip_treble
        tip_shift = (tip_bass - tip_treble) / 2.0
        if self.headstock_shoulder_width is not None:
            shoulder_width = self.headstock_shoulder_width
        if self.headstock_shoulder_shift is not None:
            shoulder_shift = self.headstock_shoulder_shift
        if self.headstock_tip_width is not None:
            tip_width_final = self.headstock_tip_width
        if self.headstock_tip_shift is not None:
            tip_shift = self.headstock_tip_shift
        return _HeadstockLayout(
            length,
            shoulder_width,
            shoulder_shift,
            tip_width_final,
            tip_shift,
            bass_sign,
            distances,
            sides,
            offsets,
        )

    def build(self) -> Prototype001Geometry:
        """Build and validate all geometry from this parameter set.

        Returns:
            Complete backend-independent Prototype001 geometry.
        """
        heel_flat_start_offset = self.heel_flat_start_offset
        if (
            not math.isfinite(self.heel_mounting_length)
            or self.heel_mounting_length < 40.0
        ):
            raise NeckGeometryError(
                "Heel mounting length must be at least 40 mm for a secure "
                "bolt-on joint."
            )
        if heel_flat_start_offset <= 0.0:
            raise NeckGeometryError(
                "Heel mounting length must exceed the heel extension after "
                "fret 24."
            )
        if not math.isclose(self.nut_shelf_length, 5.0):
            raise NeckGeometryError(
                "Prototype001 fixes the nut shelf at 5 mm; the scarf-root "
                "runout must not change the nut seat."
            )
        if (
            not math.isfinite(self.headstock_volute_length)
            or not 5.0 <= self.headstock_volute_length <= 30.0
        ):
            raise NeckGeometryError(
                "Headstock volute length must be between 5 and 30 mm."
            )
        if (
            not math.isfinite(self.headstock_root_length)
            or not 5.0 <= self.headstock_root_length < self.headstock_length
        ):
            raise NeckGeometryError(
                "Headstock root length must be at least 5 mm and shorter "
                "than the headstock."
            )
        if self.headstock_style not in HEADSTOCK_STYLES:
            raise NeckGeometryError(
                f"Unknown headstock style {self.headstock_style!r}; choose one "
                f"of {', '.join(HEADSTOCK_STYLES)}."
            )
        inline_values = (
            self.tuner_inline_first_distance,
            self.tuner_inline_spacing,
            self.tuner_edge_offset,
        )
        if not all(
            math.isfinite(value) and value > 0.0 for value in inline_values
        ):
            raise NeckGeometryError(
                "In-line tuner distance, spacing and edge offset must be positive."
            )
        if not math.isfinite(self.tuner_tip_margin) or (
            self.tuner_tip_margin < 0.0
        ):
            raise NeckGeometryError("Tuner tip margin must not be negative.")
        if self.headstock_bass_side not in ("-y", "+y"):
            raise NeckGeometryError('headstock_bass_side must be "-y" or "+y".')
        string_values = (
            self.tuner_post_diameter,
            self.nut_string_spacing,
            self.bridge_string_spacing,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in string_values):
            raise NeckGeometryError(
                "Tuner post diameter and string spacings must be positive."
            )
        if self.tuner_inline_first_distance < self.headstock_root_length:
            raise NeckGeometryError(
                "The first in-line tuner must sit beyond the headstock root, "
                "on the straight tapered edge."
            )
        if (
            not math.isfinite(self.headstock_root_swell)
            or not 0.0 <= self.headstock_root_swell <= 3.0
        ):
            raise NeckGeometryError(
                "Headstock root swell must be between 0 and 3 mm."
            )
        if (
            not math.isfinite(self.nut_end_u_trim_depth)
            or not 0.0 <= self.nut_end_u_trim_depth <= 30.0
        ):
            raise NeckGeometryError(
                "Nut-end U trim depth must be between 0 and 30 mm."
            )
        if (
            not math.isfinite(self.nut_end_u_side_fillet_radius)
            or not 0.0 <= self.nut_end_u_side_fillet_radius <= 2.0
        ):
            raise NeckGeometryError(
                "Nut-end U side fillet radius must be between 0 and 2 mm."
            )
        if (
            not math.isfinite(self.headstock_outer_d_profile_guide_extension)
            or not 0.0
            <= self.headstock_outer_d_profile_guide_extension
            <= 30.0
        ):
            raise NeckGeometryError(
                "Outer D-profile guide extension must be between 0 and 30 mm."
            )
        if (
            not math.isfinite(self.heel_root_length)
            or self.heel_root_length <= 0.0
        ):
            raise NeckGeometryError(
                "Heel root length must be finite and positive."
            )
        outline = NeckOutline(
            self.scale_length,
            self.fret_count,
            self.nut_width,
            self.final_fret_width,
            self.heel_width,
            self.heel_length,
        )
        first_fret_wood_thickness = (
            self.first_fret_thickness - self.fretboard_thickness
        )
        twelfth_fret_wood_thickness = (
            self.twelfth_fret_thickness - self.fretboard_thickness
        )
        neck_surface = NeckBackSurface(
            outline,
            first_fret_wood_thickness,
            twelfth_fret_wood_thickness,
            self.heel_thickness,
            nut_transition_thickness=self.headstock_thickness,
            nut_shelf_length=self.nut_shelf_length,
            nut_transition_length=self.headstock_volute_length,
            # Keep the underlying D-profile surface independent from the
            # inspection-only U-shaped end trim emitted by the FreeCAD
            # backend. That trim changes only the neck-end boundary.
            nut_volute_depth=max(
                self.headstock_volute_depth,
                self.headstock_root_swell,
            ),
            nut_volute_peak_fraction=self.headstock_volute_peak_fraction,
            nut_root_side_extension=self.headstock_root_side_extension,
            heel_transition_length=self.heel_root_length,
            heel_flat_start_offset=heel_flat_start_offset,
            heel_scoop_depth=self.heel_scoop_depth,
            heel_root_center_extension=self.heel_root_center_extension,
            preserve_d_profile_at_heel=False,
            exponent=self.neck_profile_exponent,
            profile_sample_count=self.profile_sample_count,
            segments_per_region=self.segments_per_region,
        )
        fretboard_surface = FretboardSurface(
            self.scale_length,
            self.fret_count,
            self.nut_width,
            self.final_fret_width,
            self.fretboard_radius,
            self.fretboard_thickness,
            end_extension=self.fretboard_end_extension,
            profile_sample_count=self.profile_sample_count,
        )
        final_fret_fraction = 1.0 - 2.0 ** (-self.fret_count / 12.0)
        width_at_scale_end = self.nut_width + (
            self.final_fret_width - self.nut_width
        ) / final_fret_fraction
        fretboard = Fretboard(
            self.scale_length,
            self.nut_width,
            width_at_scale_end,
            Centerline(self.scale_length),
            nut_corner_radius=self.fretboard_nut_corner_radius,
        )
        fret_layout = FretLayout(fretboard, self.fret_count)
        # Markers listed beyond the last fret (the 24th-fret pair on a
        # 22-fret neck, say) are simply not cut.
        inlay_layout = InlayLayout(
            fretboard_surface,
            self.inlay_depth,
            single_marker_frets=tuple(
                fret for fret in self.inlay_single_marker_frets
                if fret <= self.fret_count
            ),
            double_marker_frets=tuple(
                fret for fret in self.inlay_double_marker_frets
                if fret <= self.fret_count
            ),
            style=self.inlay_style,
            dot_diameter=self.inlay_dot_diameter,
            block_length_fraction=self.inlay_block_length_fraction,
            block_edge_margin=self.inlay_block_edge_margin,
        )
        truss_rod_channel = TrussRodChannel(
            outline,
            self.truss_rod_start,
            self.truss_rod_length,
            self.truss_rod_width,
            self.truss_rod_depth,
            adjustment_side="heel",
        )
        layout = self._headstock_layout()
        headstock_plan = HeadstockPlan(
            layout.length,
            self.nut_width,
            self.headstock_root_length,
            layout.shoulder_width,
            layout.tip_width,
            shoulder_shift=layout.shoulder_shift,
            tip_shift=layout.tip_shift,
            bass_sign=layout.bass_sign,
        )
        headstock = HeadstockSolid(
            headstock_plan,
            HeadstockAngleReference(
                layout.length,
                self.headstock_angle,
            ),
            self.headstock_thickness,
        )
        heel_end = outline.last_fret_position + self.heel_length
        # Traced body features ride with the heel end, bridge features
        # with the scale length (see the body_* parameter comments).
        body_shift = heel_end - OMARUNKO_HEEL_END_X

        def shifted(
            points: tuple[tuple[float, float], ...], dx: float
        ) -> tuple[Point2D, ...]:
            return tuple(Point2D(x + dx, y) for x, y in points)

        body_outline = TracedOutline(shifted(OMARUNKO_OUTLINE_POINTS, body_shift))
        neck_pocket = TracedCavity(
            "Neck pocket",
            self._neck_pocket_outline(outline, heel_end),
            self.heel_thickness,
        )

        def pickup_route(name: str, center_x: float) -> TracedCavity:
            return TracedCavity(
                name,
                tuple(
                    Point2D(center_x + local_x, local_y)
                    for local_x, local_y in OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS
                ),
                self.body_pickup_route_depth,
            )

        bridge = self.body_bridge.hardware(self.scale_length, self.body_thickness)
        bridge_mounting = bridge.mounting
        neck_pickup_x = heel_end + self.body_neck_pickup_offset
        route_half_length = max(x for x, _ in OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS)
        bridge_fronts = [
            cavity.min_x for cavity in (*bridge.top_cavities, *bridge.through_cavities)
        ]
        needed_offset = (
            self.scale_length
            - min(bridge_fronts)
            + route_half_length
            + self.body_bridge_pickup_clearance
            if bridge_fronts
            else -math.inf
        )
        bridge_pickup_x = self.scale_length - max(
            self.body_bridge_pickup_offset, needed_offset
        )
        neck_pickup = pickup_route("Neck pickup route", neck_pickup_x)
        bridge_pickup = pickup_route("Bridge pickup route", bridge_pickup_x)
        switch_x = heel_end + self.body_switch_cavity_offset
        switch_cover_x = heel_end + self.body_switch_cover_offset
        rear_cavity_depth = self.body_thickness - self.body_rear_cavity_top_wall
        control_cavity = RearCavity(
            TracedCavity(
                "Control cavity",
                shifted(OMARUNKO_CONTROL_CAVITY_POINTS, body_shift),
                rear_cavity_depth,
            ),
            TracedCavity(
                "Control cavity cover recess",
                shifted(OMARUNKO_CONTROL_COVER_POINTS, body_shift),
                self.body_cover_recess_depth,
            ),
        )
        switch_cavity = RearCavity(
            CircularCavity(
                "Switch cavity",
                switch_x,
                self.body_switch_cavity_y,
                self.body_switch_cavity_diameter,
                rear_cavity_depth,
            ),
            CircularCavity(
                "Switch cavity cover recess",
                switch_cover_x,
                self.body_switch_cover_y,
                self.body_switch_cover_diameter,
                self.body_cover_recess_depth,
            ),
        )
        jack_hole = JackHole(
            heel_end + self.body_jack_offset,
            self.body_jack_y,
            self.body_jack_direction_degrees,
            diameter=self.body_jack_diameter,
            depth=self.body_jack_depth,
        )
        holes: list[DrilledHole] = list(bridge.holes)
        holes.append(
            DrilledHole(
                "Switch shaft hole",
                switch_x,
                self.body_switch_cavity_y,
                self.body_switch_shaft_hole_diameter,
                self.body_thickness,
            )
        )
        for index, (pot_offset, pot_y) in enumerate(self.body_pot_offsets, start=1):
            holes.append(
                DrilledHole(
                    f"Pot {index} shaft hole",
                    heel_end + pot_offset,
                    pot_y,
                    self.body_pot_shaft_hole_diameter,
                    self.body_thickness,
                )
            )
        for label, pickup_x in (
            ("Neck", neck_pickup_x),
            ("Bridge", bridge_pickup_x),
        ):
            for side, sign in (("bass", -1.0), ("treble", 1.0)):
                holes.append(
                    DrilledHole(
                        f"{label} pickup {side} screw recess",
                        pickup_x,
                        sign * self.body_pickup_screw_spacing / 2.0,
                        self.body_pickup_screw_recess_diameter,
                        self.body_pickup_route_depth
                        + self.body_pickup_screw_recess_extra_depth,
                    )
                )
        body = BodySolid(
            body_outline,
            self.body_thickness,
            neck_pocket,
            bridge_pickup,
            neck_pickup,
            bridge_mounting,
            jack_hole,
            control_cavity=control_cavity,
            switch_cavity=switch_cavity,
            extra_cavities=bridge.top_cavities,
            holes=tuple(holes),
            through_cavities=bridge.through_cavities,
            extra_rear_cavities=bridge.rear_cavities,
        )
        tuner_layout = TunerLayout(
            headstock_plan,
            hole_diameter=self.tuner_hole_diameter,
            station_distances=layout.stations,
            side_offsets=layout.offsets,
            minimum_edge_clearance=self.tuner_edge_clearance,
            minimum_hole_clearance=self.tuner_hole_clearance,
            sides=layout.sides,
        )
        return Prototype001Geometry(
            outline,
            neck_surface,
            fretboard_surface,
            fret_layout,
            truss_rod_channel,
            headstock,
            tuner_layout,
            inlay_layout,
            body,
            self.fret_slot_width,
            self.fret_slot_depth,
            self.tuner_chamfer_depth,
            self.joint_fillet_radius,
            self.headstock_root_swell,
            self.nut_end_u_trim_depth,
            self.nut_end_u_side_fillet_radius,
            self.headstock_outer_d_profile_guide_extension,
            self.heel_nose_radius,
            heel_flat_start_offset + self.heel_block_overlap,
        )

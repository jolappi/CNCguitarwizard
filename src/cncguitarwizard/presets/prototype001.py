"""Locked but configurable parameters for the first complete neck."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..geometry.body import (
    BodySolid,
    BridgeMounting,
    CircularCavity,
    DrilledHole,
    JackHole,
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
)
from ..geometry.neck import (
    Centerline,
    HeadstockAngleReference,
    HeadstockPlan,
    HeadstockSolid,
    NeckBackSurface,
    NeckOutline,
    TrussRodChannel,
    TunerLayout,
)
from ..geometry.primitives import Point2D
from ._omarunko_outline import (
    OMARUNKO_BRIDGE_BASEPLATE_POINTS,
    OMARUNKO_CONTROL_CAVITY_POINTS,
    OMARUNKO_CONTROL_COVER_POINTS,
    OMARUNKO_HEEL_END_X,
    OMARUNKO_OUTLINE_POINTS,
    OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS,
    OMARUNKO_SCALE_LENGTH,
)


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
    first_fret_thickness: float = 17.0
    twelfth_fret_thickness: float = 19.0
    heel_thickness: float = 20.0
    fretboard_radius: float = 430.0
    fretboard_thickness: float = 6.0
    fret_slot_width: float = 0.6
    fret_slot_depth: float = 2.7
    # Barbed-wire position markers, cut as flat-bottomed pockets into the
    # playing surface. 12 and 24 get the traditional double-dot layout;
    # every other listed fret gets one marker centred on the fretboard.
    inlay_depth: float = 2.0
    inlay_single_marker_frets: tuple[int, ...] = (3, 5, 7, 9, 15, 17, 19, 21)
    inlay_double_marker_frets: tuple[int, ...] = (12, 24)
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
    body_bridge_pickup_offset: float = 21.73  # route centre before the bridge
    body_pickup_route_depth: float = 22.0
    # Clearance recesses for the pickup height-adjustment screw tips,
    # drilled on down from the route floor at the centre of each of the
    # route's two mounting-ear tabs (the DXF ears are centred 39.95 mm
    # either side of the string line).
    body_pickup_screw_spacing: float = 79.9
    body_pickup_screw_recess_diameter: float = 6.0
    body_pickup_screw_recess_extra_depth: float = 8.0
    # A Kahler 7300 is a fixed bridge screwed flat to the body: no pivot
    # stud holes (None) and no sustain block or springs, so no rear
    # cavity behind it either. The stud parameters stay parametrised
    # for a stud-mounted bridge in a future preset.
    body_bridge_pivot_stud_spacing: float | None = None
    body_bridge_pivot_hole_diameter: float = 8.0
    body_bridge_pivot_hole_depth: float = 12.0
    body_bridge_baseplate_depth: float = 25.0
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
    headstock_length: float = 150.0
    headstock_root_length: float = 45.0
    headstock_shoulder_width: float = 65.0
    headstock_tip_width: float = 40.0
    headstock_angle: float = 8.0
    headstock_thickness: float = 16.0
    tuner_hole_diameter: float = 10.0
    tuner_station_distances: tuple[float, float, float] = (55.0, 85.0, 110.0)
    tuner_side_offsets: tuple[float, float, float] = (15.0, 12.0, 10.0)
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
        )
        truss_rod_channel = TrussRodChannel(
            outline,
            self.truss_rod_start,
            self.truss_rod_length,
            self.truss_rod_width,
            self.truss_rod_depth,
            adjustment_side="heel",
        )
        headstock_plan = HeadstockPlan(
            self.headstock_length,
            self.nut_width,
            self.headstock_root_length,
            self.headstock_shoulder_width,
            self.headstock_tip_width,
        )
        headstock = HeadstockSolid(
            headstock_plan,
            HeadstockAngleReference(
                self.headstock_length,
                self.headstock_angle,
            ),
            self.headstock_thickness,
        )
        heel_end = outline.last_fret_position + self.heel_length
        # Traced body features ride with the heel end, bridge features
        # with the scale length (see the body_* parameter comments).
        body_shift = heel_end - OMARUNKO_HEEL_END_X
        bridge_shift = self.scale_length - OMARUNKO_SCALE_LENGTH

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

        neck_pickup_x = heel_end + self.body_neck_pickup_offset
        bridge_pickup_x = self.scale_length - self.body_bridge_pickup_offset
        neck_pickup = pickup_route("Neck pickup route", neck_pickup_x)
        bridge_pickup = pickup_route("Bridge pickup route", bridge_pickup_x)
        switch_x = heel_end + self.body_switch_cavity_offset
        switch_cover_x = heel_end + self.body_switch_cover_offset
        bridge_mounting = BridgeMounting(
            self.scale_length,
            pivot_stud_spacing=self.body_bridge_pivot_stud_spacing,
            pivot_hole_diameter=self.body_bridge_pivot_hole_diameter,
            pivot_hole_depth=self.body_bridge_pivot_hole_depth,
            has_sustain_block=False,
        )
        bridge_baseplate_cavity = TracedCavity(
            "Bridge baseplate cutout",
            shifted(OMARUNKO_BRIDGE_BASEPLATE_POINTS, bridge_shift),
            self.body_bridge_baseplate_depth,
        )
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
        holes = [
            DrilledHole(
                "Switch shaft hole",
                switch_x,
                self.body_switch_cavity_y,
                self.body_switch_shaft_hole_diameter,
                self.body_thickness,
            )
        ]
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
            extra_cavities=(bridge_baseplate_cavity,),
            holes=tuple(holes),
        )
        tuner_layout = TunerLayout(
            headstock_plan,
            hole_diameter=self.tuner_hole_diameter,
            station_distances=self.tuner_station_distances,
            side_offsets=self.tuner_side_offsets,
            minimum_edge_clearance=self.tuner_edge_clearance,
            minimum_hole_clearance=self.tuner_hole_clearance,
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

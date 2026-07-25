"""Locked but configurable parameters for the first complete neck."""

from __future__ import annotations

from dataclasses import dataclass

from ..geometry.fretboard import Fretboard, FretboardSurface, FretLayout
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
    fret_slot_width: float
    fret_slot_depth: float
    tuner_chamfer_depth: float


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
    heel_length: float = 4.0
    first_fret_thickness: float = 17.0
    twelfth_fret_thickness: float = 19.0
    heel_thickness: float = 20.0
    fretboard_radius: float = 430.0
    fretboard_thickness: float = 6.0
    fret_slot_width: float = 0.6
    fret_slot_depth: float = 2.7
    truss_rod_start: float = 12.0
    truss_rod_length: float = 440.0
    truss_rod_width: float = 6.0
    truss_rod_depth: float = 9.0
    headstock_length: float = 150.0
    headstock_shoulder_distance: float = 30.0
    headstock_shoulder_width: float = 65.0
    headstock_tip_width: float = 40.0
    headstock_angle: float = 8.0
    headstock_thickness: float = 16.0
    tuner_hole_diameter: float = 10.0
    tuner_station_distances: tuple[float, float, float] = (55.0, 85.0, 115.0)
    tuner_side_offsets: tuple[float, float, float] = (16.0, 13.0, 10.0)
    tuner_edge_clearance: float = 8.0
    tuner_hole_clearance: float = 10.0
    tuner_chamfer_depth: float = 0.2
    nut_shelf_length: float = 6.0
    headstock_transition_length: float = 30.0
    heel_transition_length: float = 35.0
    neck_profile_exponent: float = 2.0
    profile_sample_count: int = 33
    segments_per_region: int = 8

    def build(self) -> Prototype001Geometry:
        """Build and validate all geometry from this parameter set.

        Returns:
            Complete backend-independent Prototype001 geometry.
        """
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
            nut_transition_length=self.headstock_transition_length,
            heel_transition_length=self.heel_transition_length,
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
            end_extension=self.heel_length,
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
            self.headstock_shoulder_distance,
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
            self.fret_slot_width,
            self.fret_slot_depth,
            self.tuner_chamfer_depth,
        )

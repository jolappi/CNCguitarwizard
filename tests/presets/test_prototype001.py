"""Tests for the complete Prototype001 parameter preset."""

from dataclasses import FrozenInstanceError, replace

import pytest

from cncguitarwizard.geometry.exceptions import (
    HeadstockGeometryError,
    NeckGeometryError,
)
from cncguitarwizard.presets import Prototype001Parameters


def test_default_preset_builds_every_locked_component() -> None:
    parameters = Prototype001Parameters()
    geometry = parameters.build()

    assert geometry.neck_outline.scale_length == 609.6
    assert geometry.neck_outline.fret_count == 24
    assert geometry.neck_outline.nut_width == 42.0
    assert geometry.neck_outline.heel_width == 56.0
    assert geometry.neck_outline.heel_length == 63.0
    assert geometry.fretboard_surface.radius == 430.0
    assert geometry.fretboard_surface.center_thickness == 6.0
    assert geometry.neck_surface.first_fret_thickness == 11.0
    assert geometry.neck_surface.twelfth_fret_thickness == 13.0
    assert (
        geometry.neck_surface.first_fret_thickness
        + geometry.fretboard_surface.center_thickness
        == 17.0
    )
    assert (
        geometry.neck_surface.twelfth_fret_thickness
        + geometry.fretboard_surface.center_thickness
        == 19.0
    )
    assert geometry.neck_surface.final_fret_thickness == 20.0
    assert geometry.truss_rod_channel.length == 440.0
    assert geometry.headstock.thickness == 16.0
    assert len(geometry.tuner_layout.holes) == 6
    assert geometry.tuner_layout.station_distances == (55.0, 85.0, 115.0)
    assert geometry.tuner_layout.side_offsets == (16.0, 13.0, 10.0)
    assert geometry.tuner_layout.minimum_side_edge_clearance >= 8.0
    assert geometry.tuner_layout.minimum_side_edge_clearance == pytest.approx(
        8.645833,
        abs=0.000001,
    )
    assert len(geometry.fret_layout.slots) == 24
    assert geometry.fret_slot_width == 0.6
    assert geometry.fret_slot_depth == 2.7


def test_preset_headstock_thickness_is_configurable_in_supported_range() -> None:
    geometry = replace(
        Prototype001Parameters(),
        headstock_thickness=14.0,
    ).build()

    assert geometry.headstock.thickness == 14.0


def test_preset_rejects_unsupported_headstock_thickness() -> None:
    with pytest.raises(HeadstockGeometryError):
        replace(
            Prototype001Parameters(),
            headstock_thickness=13.9,
        ).build()


def test_preset_rejects_fretboard_thicker_than_neck_total() -> None:
    with pytest.raises(NeckGeometryError):
        replace(
            Prototype001Parameters(),
            first_fret_thickness=5.0,
        ).build()


def test_preset_parameters_are_immutable() -> None:
    parameters = Prototype001Parameters()

    with pytest.raises(FrozenInstanceError):
        parameters.scale_length = 647.7

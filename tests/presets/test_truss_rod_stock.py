"""Tests for fitting a stock-length truss rod to the neck."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.prototype001 import TRUSS_ROD_STOCK_LENGTHS

GUITAR = Prototype001Parameters()


def heel_end(parameters: Prototype001Parameters) -> float:
    outline = parameters.neck_outline()
    return outline.last_fret_position + outline.heel_length


def test_rods_are_stocked_every_20_mm() -> None:
    assert TRUSS_ROD_STOCK_LENGTHS[:3] == (300.0, 320.0, 340.0)
    assert 420.0 in TRUSS_ROD_STOCK_LENGTHS and 440.0 in TRUSS_ROD_STOCK_LENGTHS
    assert TRUSS_ROD_STOCK_LENGTHS[-1] == 600.0


@pytest.mark.parametrize(
    ("instrument", "rod"),
    [
        ("electric_guitar", 440.0),
        ("seven_string_guitar", 480.0),
        ("bass_guitar", 600.0),
    ],
)
def test_the_longest_stock_rod_that_fits_is_chosen(instrument: str, rod: float) -> None:
    parameters = Prototype001Parameters.for_instrument(instrument)
    fit = parameters.truss_rod_fit(parameters.neck_outline())

    assert fit.rod_length == fit.recommended == rod
    assert rod <= fit.longest < rod + 20.0
    # The route is the rod less its sleeve and head, outside the route.
    assert fit.route_length == pytest.approx(rod - 18.0)


def test_a_shorter_rod_keeps_its_adjuster_at_the_heel() -> None:
    long_rod = GUITAR.truss_rod(GUITAR.neck_outline())
    short = replace(GUITAR, truss_rod_rod_length=400.0)
    rod = short.truss_rod(short.neck_outline())

    # Only the thin part is shorter: the anchor end moves toward the heel.
    assert rod.end_position == long_rod.end_position == heel_end(GUITAR) - 12.0
    assert rod.start_position == pytest.approx(long_rod.start_position + 40.0)
    assert rod.channel_length == pytest.approx(long_rod.channel_length - 40.0)
    assert rod.pockets == long_rod.pockets


def test_a_shorter_rod_adjusted_at_the_headstock_ends_sooner() -> None:
    parameters = replace(GUITAR, truss_rod_adjustment="headstock")
    short = replace(parameters, truss_rod_rod_length=420.0)
    long_rod = parameters.truss_rod(parameters.neck_outline())
    rod = short.truss_rod(short.neck_outline())

    assert rod.start_position == long_rod.start_position
    assert rod.end_position == pytest.approx(long_rod.end_position - 40.0)


def test_a_rod_too_long_for_the_neck_is_rejected_with_advice() -> None:
    parameters = replace(GUITAR, truss_rod_rod_length=460.0)

    with pytest.raises(NeckGeometryError, match=r"460 mm .* 4\.8 mm too long.*440 mm"):
        parameters.build()


def test_no_fitting_stock_rod_asks_for_a_length() -> None:
    parameters = replace(GUITAR, truss_rod_stock_lengths=(700.0,))

    with pytest.raises(NeckGeometryError, match="No stock truss rod fits"):
        parameters.build()
    replace(parameters, truss_rod_rod_length=430.0).build()


def test_a_route_length_set_by_hand_skips_the_stock_lengths() -> None:
    parameters = replace(
        GUITAR, truss_rod_adjustment="headstock", truss_rod_length=300.0
    )
    fit = parameters.truss_rod_fit(parameters.neck_outline())

    assert fit.rod_length is None
    assert fit.route_length == 300.0
    assert parameters.truss_rod(parameters.neck_outline()).length == 300.0

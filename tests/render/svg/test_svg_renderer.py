"""Snapshot tests for SVG geometry rendering."""

from pathlib import Path
from xml.etree import ElementTree

import pytest

from cncguitarwizard.geometry.fretboard import (
    Fretboard,
    FretboardCrossSection,
    FretboardSideProfile,
    FretLayout,
)
from cncguitarwizard.geometry.neck import (
    Centerline,
    HeadstockAngleReference,
    HeadstockPlan,
    NeckOutline,
    NeckSideProfile,
    TrussRodChannel,
    TunerLayout,
)
from cncguitarwizard.geometry.primitives import Line2D, Point2D
from cncguitarwizard.render.svg import SVGRenderer

SNAPSHOT_DIRECTORY = Path(__file__).parent / "snapshots"


def make_fret_layout() -> FretLayout:
    """Return a compact fret layout used by renderer tests."""
    scale_length = 609.6
    fretboard = Fretboard(
        scale_length,
        42.0,
        63.0,
        Centerline(scale_length),
    )
    return FretLayout(fretboard, fret_count=3)


def make_neck_outline() -> NeckOutline:
    """Return the Prototype001 top-view neck outline."""
    return NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 63.0)


def make_neck_side_profile() -> NeckSideProfile:
    """Return the Prototype001 longitudinal neck wood profile."""
    return NeckSideProfile(609.6, 24, 17.0, 19.0, 20.0, 63.0)


def make_fretboard_side_profile() -> FretboardSideProfile:
    """Return the Prototype001 fretboard centerline side profile."""
    return FretboardSideProfile(609.6, 24, 6.0)


def make_fretboard_cross_section() -> FretboardCrossSection:
    """Return the Prototype001 widest fretboard cross-section."""
    return FretboardCrossSection(56.0, 430.0, 6.0, sample_count=5)


def make_headstock_plan() -> HeadstockPlan:
    """Return the Prototype001 tapered headstock plan."""
    return HeadstockPlan(150.0, 42.0, 30.0, 65.0, 40.0)


def make_tuner_layout() -> TunerLayout:
    """Return the Prototype001 symmetric tuner-hole layout."""
    return TunerLayout(make_headstock_plan())


def make_truss_rod_channel() -> TrussRodChannel:
    """Return the Prototype001 centered truss-rod channel."""
    return TrussRodChannel(
        make_neck_outline(),
        12.0,
        440.0,
        6.0,
        9.0,
        adjustment_side="heel",
    )


@pytest.mark.parametrize(
    ("geometry", "snapshot_name"),
    [
        (Point2D(10.0, 20.0), "point.svg"),
        (Line2D(Point2D(0.0, 0.0), Point2D(3.0, 4.0)), "line.svg"),
        (Centerline(609.6), "centerline.svg"),
        (Fretboard(609.6, 42.0, 63.0, Centerline(609.6)), "fretboard.svg"),
        (make_fret_layout(), "fret_layout.svg"),
        (make_neck_outline(), "neck_outline.svg"),
        (make_neck_side_profile(), "neck_side_profile.svg"),
        (make_fretboard_side_profile(), "fretboard_side_profile.svg"),
        (make_fretboard_cross_section(), "fretboard_cross_section.svg"),
        (make_headstock_plan(), "headstock_plan.svg"),
        (HeadstockAngleReference(150.0, 8.0), "headstock_angle.svg"),
        (make_tuner_layout(), "tuner_layout.svg"),
        (make_truss_rod_channel(), "truss_rod.svg"),
    ],
)
def test_svg_renderer_matches_geometry_snapshot(
    geometry: (
        Point2D
        | Line2D
        | Centerline
        | Fretboard
        | FretLayout
        | FretboardCrossSection
        | FretboardSideProfile
        | HeadstockAngleReference
        | HeadstockPlan
        | TunerLayout
        | TrussRodChannel
        | NeckOutline
        | NeckSideProfile
    ),
    snapshot_name: str,
) -> None:
    svg = SVGRenderer().render(geometry)

    assert svg == (SNAPSHOT_DIRECTORY / snapshot_name).read_text()


@pytest.mark.parametrize(
    "geometry",
    [
        Point2D(10.0, 20.0),
        Line2D(Point2D(0.0, 0.0), Point2D(3.0, 4.0)),
        Centerline(609.6),
        Fretboard(609.6, 42.0, 63.0, Centerline(609.6)),
        make_fret_layout(),
        make_neck_outline(),
        make_neck_side_profile(),
        make_fretboard_side_profile(),
        make_fretboard_cross_section(),
        make_headstock_plan(),
        HeadstockAngleReference(150.0, 8.0),
        make_tuner_layout(),
        make_truss_rod_channel(),
    ],
)
def test_svg_renderer_returns_well_formed_xml(
    geometry: (
        Point2D
        | Line2D
        | Centerline
        | Fretboard
        | FretLayout
        | FretboardCrossSection
        | FretboardSideProfile
        | HeadstockAngleReference
        | HeadstockPlan
        | TunerLayout
        | TrussRodChannel
        | NeckOutline
        | NeckSideProfile
    ),
) -> None:
    svg = SVGRenderer().render(geometry)

    assert ElementTree.fromstring(svg).tag == "{http://www.w3.org/2000/svg}svg"


def test_fret_layout_svg_contains_one_outline_and_every_slot() -> None:
    layout = make_fret_layout()
    root = ElementTree.fromstring(SVGRenderer().render(layout))
    namespace = {"svg": "http://www.w3.org/2000/svg"}

    assert len(root.findall(".//svg:polygon", namespace)) == 1
    assert len(root.findall(".//svg:line", namespace)) == len(layout.slots)


def test_view_box_fits_geometry_with_requested_padding() -> None:
    line = Line2D(Point2D(10.0, -5.0), Point2D(110.0, 15.0))

    root = ElementTree.fromstring(SVGRenderer(padding=5.0).render(line))

    assert root.attrib["viewBox"] == "5 -10 110 30"


def test_zero_padding_still_produces_a_valid_point_view_box() -> None:
    root = ElementTree.fromstring(
        SVGRenderer(padding=0.0).render(Point2D(10.0, 20.0))
    )

    assert root.attrib["viewBox"] == "10 20 1 1"


@pytest.mark.parametrize(
    "arguments",
    [
        {"width": 0.0},
        {"height": float("inf")},
        {"padding": -1.0},
    ],
)
def test_renderer_rejects_invalid_viewport_configuration(
    arguments: dict[str, float],
) -> None:
    with pytest.raises(ValueError):
        SVGRenderer(**arguments)

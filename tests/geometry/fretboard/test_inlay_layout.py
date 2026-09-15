"""Tests for barbed-wire fret position marker inlays."""

from dataclasses import FrozenInstanceError
from typing import Callable

import pytest

from cncguitarwizard.geometry.exceptions import FretboardGeometryError
from cncguitarwizard.geometry.fretboard import FretboardSurface, InlayLayout


def make_surface() -> FretboardSurface:
    """Return a compact Prototype001 fretboard test surface."""
    return FretboardSurface(
        scale_length=609.6,
        fret_count=24,
        nut_width=42.0,
        last_fret_width=56.0,
        radius=430.0,
        center_thickness=6.0,
        profile_sample_count=5,
    )


def test_layout_places_one_marker_per_single_fret_and_two_per_double_fret() -> (
    None
):
    layout = InlayLayout(make_surface(), depth=2.0)

    single_frets = {3, 5, 7, 9, 15, 17, 19, 21}
    double_frets = {12, 24}
    assert len(layout.markers) == len(single_frets) + 2 * len(double_frets)
    for fret_number in single_frets:
        assert sum(
            1 for marker in layout.markers if marker.fret_number == fret_number
        ) == 1
    for fret_number in double_frets:
        assert sum(
            1 for marker in layout.markers if marker.fret_number == fret_number
        ) == 2


def test_double_marker_pair_straddles_the_centerline_symmetrically() -> None:
    layout = InlayLayout(make_surface(), depth=2.0)

    twelfth_fret_markers = [
        marker for marker in layout.markers if marker.fret_number == 12
    ]
    assert len(twelfth_fret_markers) == 2
    first, second = twelfth_fret_markers
    first_center_y = sum(point.y for point in first.outline) / len(first.outline)
    second_center_y = sum(
        point.y for point in second.outline
    ) / len(second.outline)
    assert first_center_y == pytest.approx(-second_center_y)


def test_marker_outline_is_a_closed_simple_polygon() -> None:
    layout = InlayLayout(make_surface(), depth=2.0)

    def ccw(a, b, c) -> bool:
        return (c.y - a.y) * (b.x - a.x) > (b.y - a.y) * (c.x - a.x)

    def segments_intersect(p1, p2, p3, p4) -> bool:
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(
            p1, p2, p4
        )

    for marker in layout.markers:
        points = marker.outline
        count = len(points)
        assert count >= 4
        for i in range(count):
            a1, a2 = points[i], points[(i + 1) % count]
            for j in range(i + 1, count):
                b1, b2 = points[j], points[(j + 1) % count]
                if len({a1, a2, b1, b2}) < 4:
                    continue
                assert not segments_intersect(a1, a2, b1, b2)


def test_marker_positions_match_fret_midpoints() -> None:
    layout = InlayLayout(make_surface(), depth=2.0)

    third_fret_marker = next(
        marker for marker in layout.markers if marker.fret_number == 3
    )
    assert third_fret_marker.position == pytest.approx(81.746, abs=1e-2)


def test_layout_is_immutable() -> None:
    layout = InlayLayout(make_surface(), depth=2.0)

    with pytest.raises(FrozenInstanceError):
        layout.depth = 3.0  # type: ignore[misc]


@pytest.mark.parametrize(
    "make_invalid_layout",
    [
        lambda: InlayLayout(make_surface(), depth=0.0),
        lambda: InlayLayout(make_surface(), depth=-1.0),
        lambda: InlayLayout(make_surface(), depth=float("nan")),
        lambda: InlayLayout(make_surface(), depth=6.0),
        lambda: InlayLayout(make_surface(), depth=7.0),
        lambda: InlayLayout(
            make_surface(),
            depth=2.0,
            single_marker_frets=(12,),
            double_marker_frets=(12, 24),
        ),
        lambda: InlayLayout(make_surface(), depth=2.0, single_marker_frets=(25,)),
        lambda: InlayLayout(make_surface(), depth=2.0, double_marker_frets=(0,)),
    ],
)
def test_layout_rejects_invalid_parameters(
    make_invalid_layout: Callable[[], InlayLayout],
) -> None:
    with pytest.raises(FretboardGeometryError):
        make_invalid_layout()

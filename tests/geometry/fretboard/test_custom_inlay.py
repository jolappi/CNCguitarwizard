"""Tests for the drawn (custom) inlay and the web app's inlay editor.

The shape is drawn once, on the first marker's fret space, as ``(along,
across)`` points; every marker is that shape fitted to its own fret space
and the board's width there.
"""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import FretboardMachiningParameters
from cncguitarwizard.cam.inlays import plan_inlay_machining
from cncguitarwizard.geometry.exceptions import FretboardGeometryError
from cncguitarwizard.geometry.fret import FretCalculator
from cncguitarwizard.geometry.fretboard import FretboardSurface, InlayLayout
from cncguitarwizard.geometry.fretboard.inlay_layout import (
    CUSTOM_CLEARANCE,
    DEFAULT_CUSTOM_POINTS,
    INLAY_STYLES,
    custom_limits,
)
from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import inlay_editor_layout, parameter_schema

POSITIONS = {
    fret.number: fret.distance_from_nut for fret in FretCalculator.calculate(609.6, 24)
}
# A tooth, wide on the bass side.
TOOTH = ((0.25, 0.8), (0.75, 0.8), (0.75, -0.5))


def surface() -> FretboardSurface:
    return FretboardSurface(609.6, 24, 42.0, 56.0, 430.0, 6.0, 9)


def _half(x: float) -> float:
    return (42.0 + (56.0 - 42.0) * x / POSITIONS[24]) / 2.0


def _centroid_y(points: tuple[Point2D, ...]) -> float:
    pairs = list(zip(points, (*points[1:], points[0]), strict=True))
    cross = [a.x * b.y - b.x * a.y for a, b in pairs]
    return sum((a.y + b.y) * c for (a, b), c in zip(pairs, cross, strict=True)) / (
        3 * sum(cross)
    )


def test_every_marker_is_the_drawn_shape_fitted_to_its_fret() -> None:
    layout = InlayLayout(surface(), 2.0, style="custom")

    # One per listed fret, the octaves too.
    assert [m.fret_number for m in layout.markers] == [
        3,
        5,
        7,
        9,
        12,
        15,
        17,
        19,
        21,
        24,
    ]
    for marker in layout.markers:
        front = POSITIONS[marker.fret_number - 1]
        back = POSITIONS[marker.fret_number]
        xs = [p.x for p in marker.outline]
        # The default block: 0.2 to 0.8 of its fret space (corners rounded
        # 1 mm, which only takes them in).
        assert min(xs) == pytest.approx(front + 0.2 * (back - front), abs=1e-6)
        assert max(xs) == pytest.approx(back - 0.2 * (back - front), abs=1e-6)
        for p in marker.outline:
            assert abs(p.y) <= 0.7 * _half(p.x) + 1e-6


def test_the_drawn_shape_reaches_toward_the_bass_edge() -> None:
    for bass_sign in (-1.0, 1.0):
        layout = InlayLayout(
            surface(), 2.0, style="custom", custom_points=TOOTH, bass_sign=bass_sign
        )
        for marker in layout.markers:
            assert _centroid_y(marker.outline) * bass_sign > 1.0


def test_a_drawn_shape_keeps_clear_of_the_frets_and_edges() -> None:
    # Fine at the first marker, too near the fret where the spaces are
    # shorter.
    near = 1.0 - 1.5 / (POSITIONS[3] - POSITIONS[2])
    with pytest.raises(FretboardGeometryError, match=r"fret 1\d comes within 1 mm"):
        InlayLayout(
            surface(),
            2.0,
            style="custom",
            custom_points=((0.3, -0.5), (near, 0.0), (0.3, 0.5)),
        )
    with pytest.raises(FretboardGeometryError, match="within 1 mm"):
        InlayLayout(
            surface(),
            2.0,
            style="custom",
            custom_points=((0.3, -0.99), (0.7, -0.5), (0.3, 0.5)),
        )


@pytest.mark.parametrize(
    ("points", "match"),
    [
        (((0.2, 0.0), (0.8, 0.0)), "at least three"),
        (((0.0, 0.0), (0.8, 0.5), (0.8, -0.5)), "between its frets"),
        (((0.2, 0.0), (0.8, 1.2), (0.8, -0.5)), "between its frets"),
        (((0.2, float("nan")), (0.8, 0.5), (0.8, -0.5)), "between its frets"),
        (((0.2, -0.5), (0.8, 0.5), (0.8, -0.5), (0.2, 0.5)), "must not cross"),
    ],
)
def test_a_drawn_shape_that_cannot_be_cut_is_refused(
    points: tuple[tuple[float, float], ...], match: str
) -> None:
    with pytest.raises(FretboardGeometryError, match=match):
        InlayLayout(surface(), 2.0, style="custom", custom_points=points)


@pytest.mark.parametrize(
    # (The parallelogram leans out over its frets: held in, below.)
    "style",
    [style for style in INLAY_STYLES if style != "parallelogram"],
)
def test_every_style_starts_the_editor_with_its_own_marker(style: str) -> None:
    layout = InlayLayout(surface(), 2.0, style=style)  # type: ignore[arg-type]
    points = layout.editable_points()

    # Drawn, the style's first marker comes out as it was.
    drawn = InlayLayout(surface(), 2.0, style="custom", custom_points=points)
    first = layout.markers[0]
    redrawn = drawn.markers[0]
    for axis in "xy":
        for pick in (min, max):
            assert pick(getattr(p, axis) for p in redrawn.outline) == pytest.approx(
                pick(getattr(p, axis) for p in first.outline), abs=0.6
            )


def test_the_limits_keep_a_drawn_shape_inside_every_marker() -> None:
    frets = (3, 5, 7, 9, 12, 15, 17, 19, 21, 24)
    (low, high), across = custom_limits(surface(), frets)
    # The 24th's space is the shortest, the board narrowest at the 2nd fret.
    assert low == pytest.approx(1.0 / (POSITIONS[24] - POSITIONS[23]), abs=1e-4)
    assert low >= 1.0 / (POSITIONS[24] - POSITIONS[23])
    assert high == pytest.approx(1.0 - low, abs=2e-4)
    assert across <= 1.0 - 1.0 / _half(POSITIONS[2])
    corners = ((low, -across), (high, -across), (high, across), (low, across))
    layout = InlayLayout(surface(), 2.0, style="custom", custom_points=corners)
    assert len(layout.markers) == 10
    # A parallelogram leans out over its frets; the editor starts from it
    # held inside the limits.
    leaning = InlayLayout(surface(), 2.0, style="parallelogram").editable_points()
    assert all(low <= along <= high for along, _ in leaning)
    with pytest.raises(FretboardGeometryError, match="No fret"):
        custom_limits(surface(), ())
    with pytest.raises(FretboardGeometryError, match="off the fretboard"):
        custom_limits(surface(), (3, 30))


def test_the_editable_points_of_a_drawn_shape_are_its_own() -> None:
    assert InlayLayout(surface(), 2.0, style="custom").editable_points() == (
        DEFAULT_CUSTOM_POINTS
    )
    layout = InlayLayout(surface(), 2.0, style="custom", custom_points=TOOTH)
    assert layout.editable_points() == TOOTH


@pytest.mark.parametrize(
    ("instrument", "overrides"),
    [
        ("electric_guitar", {}),
        ("electric_guitar", {"fret_slant_angle": 5.0}),
        ("five_string_bass", {"bass_scale_length": 863.6 + 50.8}),
        ("electric_guitar", {"handedness": "left"}),
    ],
)
def test_a_drawn_inlay_builds_machines_and_exports(
    instrument: str, overrides: dict[str, object]
) -> None:
    parameters = replace(
        Prototype001Parameters.for_instrument(instrument),  # type: ignore[arg-type]
        inlay_style="custom",
        inlay_points=TOOTH,
        **overrides,  # type: ignore[arg-type]
    )
    geometry = parameters.build()
    layout = geometry.inlay_layout
    assert layout.style == "custom" and layout.custom_points == TOOTH
    assert layout.markers
    pieces = plan_inlay_machining(layout, FretboardMachiningParameters())
    assert pieces is not None and pieces.pieces.toolpaths
    assert "inlay" in FreeCADScriptExporter().render_prototype001(geometry).lower()


def test_the_editor_shows_the_first_marker_and_its_limits() -> None:
    layout = inlay_editor_layout({"prototype": {}})
    assert layout["problem"] is None
    assert layout["fret"] == 3
    assert layout["front"] == pytest.approx(POSITIONS[2], abs=1e-3)
    assert layout["back"] == pytest.approx(POSITIONS[3], abs=1e-3)
    # The barbed wire's own corners to start from, and the whole board.
    assert len(layout["points"]) > 12 and not layout["custom"]
    assert len(layout["markers"]) == 12
    assert len(layout["frets"]) == 25
    # A corner on the limits fits every marker (the 24th's short space,
    # the board's narrowest at the first)...
    (low, high), across = layout["limits"]["along"], layout["limits"]["across"]
    assert low == pytest.approx(
        CUSTOM_CLEARANCE / (POSITIONS[24] - POSITIONS[23]), abs=1e-4
    )
    assert high == pytest.approx(1.0 - low, abs=2e-4)
    corners = [[low, -across], [high, -across], [high, across], [low, across]]
    drawn = inlay_editor_layout(
        {"prototype": {"inlay_style": "custom", "inlay_points": corners}}
    )
    assert drawn["problem"] is None and drawn["custom"]
    assert drawn["points"] == corners
    assert len(drawn["markers"]) == 10
    # ...one past them does not, and says why.
    corners[1][0] = high + 0.01
    refused = inlay_editor_layout(
        {"prototype": {"inlay_style": "custom", "inlay_points": corners}}
    )
    assert "within 1 mm" in refused["problem"]
    assert refused["markers"] == [] and refused["points"] == corners


def test_the_editor_draws_a_left_handed_board_mirrored() -> None:
    right = inlay_editor_layout({"prototype": {}})
    left = inlay_editor_layout({"prototype": {"handedness": "left"}})
    assert left["mirrored"] and not right["mirrored"]
    # Drawn as built right-handed, the same points either way.
    assert left["bass_sign"] == right["bass_sign"]
    assert left["points"] == right["points"]


def test_the_editor_reports_what_it_cannot_show() -> None:
    no_markers: dict[str, list[int]] = {
        "inlay_single_marker_frets": [],
        "inlay_double_marker_frets": [],
    }
    assert "error" in inlay_editor_layout({"prototype": no_markers})
    assert "error" in inlay_editor_layout({"prototype": {"fret_count": "x"}})


def test_the_web_form_offers_a_drawn_inlay() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    assert "custom" in fields["inlay_style"]["options"]
    assert "Inlay design" in fields["inlay_style"]["labels"]["custom"]
    assert fields["inlay_points"]["type"] == "json"
    assert fields["inlay_points"]["default"] == []

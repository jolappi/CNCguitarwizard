"""Tests for the symbol inlay styles: runes, Latin crosses, iron crosses,
ankhs."""

import ast
import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.geometry.exceptions import FretboardGeometryError
from cncguitarwizard.geometry.fret import FretCalculator
from cncguitarwizard.geometry.fretboard import FretboardSurface, InlayLayout
from cncguitarwizard.geometry.fretboard.inlay_layout import (
    CUSTOM_CLEARANCE,
    SYMBOL_SPAN,
)
from cncguitarwizard.geometry.fretboard.runes import (
    DEFAULT_RUNES,
    RUNES,
    rune_outlines,
)
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import inlay_editor_layout, parameter_schema

FRETS = (3, 5, 7, 9, 12, 15, 17, 19, 21, 24)


def surface(scale: float = 609.6) -> FretboardSurface:
    return FretboardSurface(scale, 24, 42.0, 56.0, 430.0, 6.0, 9)


def area(points: tuple[Point2D, ...]) -> float:
    return 0.5 * sum(
        a.x * b.y - b.x * a.y
        for a, b in zip(points, (*points[1:], points[0]), strict=True)
    )


@pytest.mark.parametrize("name", list(RUNES))
def test_every_rune_is_drawn_as_solid_pieces(name: str) -> None:
    pieces = rune_outlines(name)

    assert len(pieces) == (2 if name == "jera" else 1)
    assert all(area(piece) > 0.0 for piece in pieces)
    # In its box, one unit tall, its round ends reaching past it.
    ys = [p.y for piece in pieces for p in piece]
    assert min(ys) >= -0.061 and max(ys) <= 1.061
    assert max(ys) - min(ys) > 0.75


@pytest.mark.parametrize("style", ["runes", "cross", "iron_cross", "ankh"])
def test_a_symbol_fits_every_marker_fret_space(style: str) -> None:
    layout = InlayLayout(surface(), 2.0, style=style)
    positions = {
        fret.number: fret.distance_from_nut
        for fret in FretCalculator.calculate(609.6, 24)
    }

    assert sorted({m.fret_number for m in layout.markers}) == list(FRETS)
    for marker in layout.markers:
        front = positions[marker.fret_number - 1]
        back = positions[marker.fret_number]
        xs = [p.x for p in marker.outline]
        ys = [p.y for p in marker.outline]
        assert area(marker.outline) > 0.0
        assert min(xs) >= front + CUSTOM_CLEARANCE - 1e-6
        assert max(xs) <= back - CUSTOM_CLEARANCE + 1e-6
        board = 42.0 + 14.0 * marker.position / positions[24]
        assert max(ys) - min(ys) <= board * SYMBOL_SPAN + 1e-6


def test_the_runes_go_in_order_and_start_over() -> None:
    layout = InlayLayout(surface(), 2.0, style="runes", runes=("algiz", "jera"))

    pieces = {fret: 0 for fret in FRETS}
    for marker in layout.markers:
        pieces[marker.fret_number] += 1
    # Algiz, Jera (two hooks), Algiz, Jera...
    assert [pieces[fret] for fret in FRETS] == [1, 2] * 5
    # The default set when none are chosen.
    assert len(DEFAULT_RUNES) == len(FRETS)
    assert all(name in RUNES for name in DEFAULT_RUNES)


@pytest.mark.parametrize("bass_sign", [-1.0, 1.0])
def test_a_rune_stands_with_its_top_toward_the_bass_edge(bass_sign: float) -> None:
    # Tiwaz, an arrow: its head is its top, its widest part.
    (marker,) = [
        m
        for m in InlayLayout(
            surface(), 2.0, style="runes", runes=("tiwaz",), bass_sign=bass_sign
        ).markers
        if m.fret_number == 3
    ]
    ys = [p.y * bass_sign for p in marker.outline]
    top, bottom = max(ys), min(ys)
    width_near = [
        p.x for p in marker.outline if p.y * bass_sign > top - (top - bottom) * 0.3
    ]
    width_far = [
        p.x for p in marker.outline if p.y * bass_sign < bottom + (top - bottom) * 0.3
    ]
    assert max(width_near) - min(width_near) > 2.0 * (max(width_far) - min(width_far))


@pytest.mark.parametrize("bass_sign", [-1.0, 1.0])
def test_a_cross_stands_upright_its_head_toward_the_bass_edge(
    bass_sign: float,
) -> None:
    # Upright as the guitar is played, as a rune stands: its long arm
    # across the board, its crossbar along the neck nearer the bass edge.
    marker = InlayLayout(surface(), 2.0, style="cross", bass_sign=bass_sign).markers[0]
    xs = [p.x for p in marker.outline]
    ys = [p.y * bass_sign for p in marker.outline]
    assert max(ys) - min(ys) > 1.5 * (max(xs) - min(xs))
    # The crossbar's ends (the furthest along the neck) on the bass side.
    middle = (max(xs) + min(xs)) / 2.0
    crossbar = max(marker.outline, key=lambda p: abs(p.x - middle))
    assert crossbar.y * bass_sign > (max(ys) + min(ys)) / 2.0


def test_an_iron_cross_is_square_and_symmetric() -> None:
    marker = InlayLayout(surface(), 2.0, style="iron_cross").markers[0]
    xs = [p.x for p in marker.outline]
    ys = [p.y for p in marker.outline]

    assert max(xs) - min(xs) == pytest.approx(max(ys) - min(ys), abs=0.05)
    assert sum(ys) / len(ys) == pytest.approx(0.0, abs=0.05)


def distance_to(point: Point2D, outline: tuple[Point2D, ...]) -> float:
    def segment(a: Point2D, b: Point2D) -> float:
        dx, dy = b.x - a.x, b.y - a.y
        t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy)
        t = min(1.0, max(0.0, t))
        return math.hypot(point.x - a.x - t * dx, point.y - a.y - t * dy)

    return min(segment(a, b) for a, b in zip(outline, (*outline[1:], outline[0])))


@pytest.mark.parametrize("bass_sign", [-1.0, 1.0])
def test_an_ankh_is_one_piece_round_the_wood_in_its_loop(bass_sign: float) -> None:
    layout = InlayLayout(surface(), 2.0, style="ankh", bass_sign=bass_sign)
    assert [m.fret_number for m in layout.markers] == list(FRETS)
    for marker in layout.markers:
        (hole,) = marker.holes
        # Upright as a cross: its loop, round the hole, toward the bass
        # edge; the hole inside the outline.
        ys = [p.y * bass_sign for p in marker.outline]
        middle = (max(ys) + min(ys)) / 2.0
        assert all(p.y * bass_sign > middle for p in hole)
        assert all(point_in_polygon(p, marker.outline) for p in hole)
        # Wood enough round the hole for the 1 mm inlay cutter.
        assert min(distance_to(p, marker.outline) for p in hole) >= 1.1 - 1e-6
    # As photographed where there is room; drawn smaller where the loop
    # would be too thin round it (the last frets).
    widths = {
        m.fret_number: max(p.x for p in m.holes[0]) - min(p.x for p in m.holes[0])
        for m in layout.markers
    }
    lengths = {
        m.fret_number: max(p.x for p in m.outline) - min(p.x for p in m.outline)
        for m in layout.markers
    }
    assert widths[3] / lengths[3] == pytest.approx(0.1654 / 0.6035, abs=0.01)
    assert widths[24] / lengths[24] < 0.9 * widths[3] / lengths[3]


def test_an_ankh_leans_whole_with_fanned_frets() -> None:
    from cncguitarwizard.geometry.fretboard import FretSkew

    fanned = FretboardSurface(
        609.6, 24, 42.0, 56.0, 430.0, 6.0, 9, skew=FretSkew(slant=0.1)
    )
    for marker in InlayLayout(fanned, 2.0, style="ankh").markers:
        (hole,) = marker.holes
        assert all(point_in_polygon(p, marker.outline) for p in hole)


def test_an_ankh_is_cut_round_its_hole_and_its_piece_round_the_wood() -> None:
    from cncguitarwizard.cam.fretboard import (
        FretboardMachiningParameters,
        plan_fretboard_machining,
    )
    from cncguitarwizard.cam.inlays import plan_inlay_machining

    geometry = replace(Prototype001Parameters(), inlay_style="ankh").build()
    layout = geometry.inlay_layout
    parameters = FretboardMachiningParameters()
    plan = plan_fretboard_machining(geometry, parameters)
    # The pocket's tool never goes inside the wood in the loop.
    marker = layout.markers[0]
    (hole,) = marker.holes
    inner = [
        Point2D(
            sum(p.x for p in hole) / len(hole) - plan.origin_x,
            sum(p.y for p in hole) / len(hole) - plan.origin_y,
        )
    ]
    (pocket,) = [
        path
        for path in plan.inlays.toolpaths
        if path.name.startswith(f"Inlay fret {marker.fret_number} ")
    ]
    cutting = [m for m in pocket.moves if not m.rapid and m.z < 0.0]
    assert all(math.hypot(m.x - inner[0].x, m.y - inner[0].y) > 0.5 for m in cutting)
    # Each piece's hole cut out before the piece itself.
    pieces = plan_inlay_machining(layout, parameters)
    assert pieces is not None
    names = [path.name for path in pieces.pieces.toolpaths]
    assert len(names) == 2 * len(layout.markers)
    assert all(
        hole_name == f"{piece_name}, hole"
        for hole_name, piece_name in zip(names[::2], names[1::2], strict=True)
    )
    source = FreeCADScriptExporter().render_prototype001(geometry)
    assert "INLAY_MARKER_HOLES = " in source
    assert "marker_shape = marker_shape.cut(" in source


def test_a_symbol_too_thin_for_the_cutter_is_refused() -> None:
    # A short scale's top frets are too close for a rune's 1.1 mm stroke.
    with pytest.raises(FretboardGeometryError, match="thinnest part"):
        InlayLayout(surface(scale=350.0), 2.0, style="runes")


def test_an_unknown_rune_is_refused() -> None:
    with pytest.raises(FretboardGeometryError, match="Unknown rune 'odin'"):
        InlayLayout(surface(), 2.0, style="runes", runes=("odin",))


def test_the_page_offers_the_runes_and_each_frets_choice() -> None:
    runes = parameter_schema()["runes"]
    assert [rune["name"] for rune in runes] == list(RUNES)
    assert runes[0] == {"name": "fehu", "glyph": "ᚠ", "meaning": "wealth, cattle"}

    layout = inlay_editor_layout(
        {"prototype": {"inlay_style": "runes", "inlay_runes": ["algiz", "tiwaz"]}}
    )
    assert layout["problem"] is None
    assert layout["runes"][:3] == [
        {"fret": 3, "rune": "algiz"},
        {"fret": 5, "rune": "tiwaz"},
        {"fret": 7, "rune": "algiz"},
    ]
    assert inlay_editor_layout({"prototype": {}})["runes"] == []


@pytest.mark.parametrize("style", ["runes", "cross", "iron_cross", "ankh"])
def test_the_symbols_are_cut_and_modelled(style: str) -> None:
    geometry = replace(Prototype001Parameters(), inlay_style=style).build()

    assert len(geometry.inlay_layout.markers) >= len(FRETS)
    ast.parse(FreeCADScriptExporter().render_prototype001(geometry))

"""Position marker inlays cut into the fretboard surface.

The styles share one layout: ``barbed_wire`` (the Prototype001 default)
and round ``dot`` markers, two at the double-marker frets; ``barbed_wire_2``,
a knot of barbed wire across the board traced from the builder's drawing
(``barbed_wire_2``), one piece at every marker fret; and the
shapes that span the board between the frets, one per fret, following
its taper (``BOARD_STYLES``): Gibson-style ``block``, Les Paul style
``trapezoid`` (long at the bass edge, short at the treble edge), Jackson
style ``sharktooth`` (a triangle, its point at the treble edge), a
leaning ``parallelogram``, a ``diamond``, and Gibson's ``split_block``
(a block split along its diagonal into two pieces) — or ``custom``, a
shape of the builder's own drawn once (``custom_points``) and fitted to
every marker's fret space and the board's taper there.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from ..exceptions import FretboardGeometryError
from ..fret import FretCalculator
from ..primitives import Point2D, rounded_polygon_points
from .barbed_wire_2 import (
    BARBED_WIRE_2_ALONG,
    BARBED_WIRE_2_EDITOR_OUTLINE,
    BARBED_WIRE_2_OUTLINE,
)
from .skew import FretSkew
from .surface import FretboardSurface

InlayStyle = Literal[
    "barbed_wire",
    "barbed_wire_2",
    "dot",
    "block",
    "trapezoid",
    "sharktooth",
    "parallelogram",
    "diamond",
    "split_block",
    "custom",
]

INLAY_STYLES: tuple[str, ...] = (
    "barbed_wire",
    "barbed_wire_2",
    "dot",
    "block",
    "trapezoid",
    "sharktooth",
    "parallelogram",
    "diamond",
    "split_block",
    "custom",
)
"""Every inlay style, in the order the form offers them."""

BOARD_STYLES: frozenset[str] = frozenset(INLAY_STYLES) - {
    "barbed_wire",
    "barbed_wire_2",
    "dot",
}
"""Styles that span the board between two frets, one per fret, leaning
point by point with slanted frets."""

TRAPEZOID_SHORT_SIDE = 0.55
"""A trapezoid's treble edge as a share of its bass edge."""

PARALLELOGRAM_LEAN = 0.35
"""How far a parallelogram's treble edge sits toward the nut, as a share
of its length."""

SPLIT_BLOCK_GAP = 1.5
"""The gap along a split block's diagonal, in mm."""

DEFAULT_CUSTOM_POINTS: tuple[tuple[float, float], ...] = (
    (0.2, -0.7),
    (0.8, -0.7),
    (0.8, 0.7),
    (0.2, 0.7),
)
"""A drawn marker before any is drawn: a block (see ``custom_points``)."""

CUSTOM_CLEARANCE = 1.0
"""Wood a drawn marker keeps from the fret slots either side of it and from
the board's edges, in mm."""

BARBED_WIRE_2_SPAN = 0.8
"""How much of the board's width a ``barbed_wire_2`` knot spans."""

BARBED_WIRE_2_FRET_CLEARANCE = 1.5
"""Wood a ``barbed_wire_2`` knot's barbs keep from the frets either side,
in mm: in a short fret space the knot is drawn smaller to keep it."""


@dataclass(frozen=True, slots=True)
class InlayMarker:
    """One marker outline at a single fretboard position.

    Args:
        fret_number: Fret the marker sits behind, counted from the nut.
        position: Longitudinal distance from the nut in millimetres.
        outline: Closed, non-self-intersecting polygon in board-plane
            coordinates (x = longitudinal, y = lateral from centerline).
    """

    fret_number: int
    position: float
    outline: tuple[Point2D, ...]


@dataclass(frozen=True, slots=True)
class InlayLayout:
    """Fret markers sized to a tapered fretboard surface.

    Each single-marker fret receives one marker centred on the fretboard.
    Each double-marker fret receives two shorter markers offset either
    side of the centerline, matching the traditional double-dot layout
    at the octave and double-octave — except in ``barbed_wire_2`` (one
    traced knot, ``BARBED_WIRE_2_SPAN`` of the board's width, smaller where
    the fret space is short) and the styles that span the board (blocks
    and the like, and a drawn ``custom`` shape), where every listed fret
    gets one, as on a Gibson.

    Args:
        fretboard_surface: Surface the markers are cut into. Its own
            nut-to-final-fret taper sizes each marker to the locally
            available width.
        depth: Pocket depth in millimetres, cut down from the playing
            surface centerline.
        single_marker_frets: Frets that receive one centered marker.
        double_marker_frets: Frets that receive two offset markers.
        style: One of ``INLAY_STYLES``.
        dot_diameter: Diameter of a ``dot`` marker.
        block_length_fraction: A ``block``'s length along the neck as a
            fraction of the fret spacing it sits in.
        block_edge_margin: Wood left between a ``block`` and each board
            edge.
        block_corner_radius: Corner rounding of the board-spanning shapes.
        bass_sign: Which side the bass strings are on (-1: -Y, +1: +Y),
            for the shapes that differ side to side.
        custom_points: The ``custom`` marker's corners, straight lines
            between them (rounded by ``block_corner_radius``), as
            ``(along, across)``: ``along`` 0 at the fret toward the nut and
            1 at the marker's own fret, ``across`` the share of the board's
            half-width there, toward the bass edge (-1 the treble edge, +1
            the bass edge). Each marker's fret space and the board's width
            along it scale the shape, so it is drawn once (on the first
            marker, in the web app's inlay editor) and fits every fret;
            empty for ``DEFAULT_CUSTOM_POINTS``.

    Raises:
        FretboardGeometryError: If the depth cannot fit the fretboard
            thickness, a fret number falls outside the fretboard's fret
            range, or a fret is listed in both marker sets.
    """

    fretboard_surface: FretboardSurface
    depth: float
    single_marker_frets: tuple[int, ...] = (3, 5, 7, 9, 15, 17, 19, 21)
    double_marker_frets: tuple[int, ...] = (12, 24)
    style: InlayStyle = "barbed_wire"
    dot_diameter: float = 6.0
    block_length_fraction: float = 0.6
    block_edge_margin: float = 5.0
    block_corner_radius: float = 1.0
    bass_sign: float = -1.0
    custom_points: tuple[tuple[float, float], ...] = ()
    markers: tuple[InlayMarker, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate parameters and build every marker outline."""
        self._validate()

        fret_positions = {
            fret.number: fret.distance_from_nut
            for fret in FretCalculator.calculate(
                self.fretboard_surface.scale_length,
                self.fretboard_surface.fret_count,
            )
        }
        final_fret_position = fret_positions[self.fretboard_surface.fret_count]

        def midpoint(fret_number: int) -> float:
            previous = 0.0 if fret_number == 1 else fret_positions[fret_number - 1]
            return (previous + fret_positions[fret_number]) / 2.0

        def half_width_at(position: float) -> float:
            fraction = position / final_fret_position
            surface = self.fretboard_surface
            width = (
                surface.nut_width
                + (surface.last_fret_width - surface.nut_width) * fraction
            )
            return width / 2.0

        markers: list[InlayMarker] = []
        if self.style == "custom":
            for fret_number in sorted(
                (*self.single_marker_frets, *self.double_marker_frets)
            ):
                previous = 0.0 if fret_number == 1 else fret_positions[fret_number - 1]
                markers.append(
                    InlayMarker(
                        fret_number,
                        midpoint(fret_number),
                        self._custom_marker(
                            fret_number,
                            previous,
                            fret_positions[fret_number],
                            half_width_at,
                        ),
                    )
                )
        elif self.style in BOARD_STYLES:
            for fret_number in sorted(
                (*self.single_marker_frets, *self.double_marker_frets)
            ):
                previous = 0.0 if fret_number == 1 else fret_positions[fret_number - 1]
                spacing = fret_positions[fret_number] - previous
                position = midpoint(fret_number)
                half_length = spacing * self.block_length_fraction / 2.0
                front, back = position - half_length, position + half_length
                for vertices in _board_shape(
                    self.style,
                    front,
                    back,
                    half_width_at(front) - self.block_edge_margin,
                    half_width_at(back) - self.block_edge_margin,
                    self.bass_sign,
                ):
                    markers.append(
                        InlayMarker(
                            fret_number,
                            position,
                            rounded_polygon_points(
                                vertices,
                                [self.block_corner_radius] * len(vertices),
                                samples_per_corner=6,
                            ),
                        )
                    )
        elif self.style == "barbed_wire_2":
            for fret_number in sorted(
                (*self.single_marker_frets, *self.double_marker_frets)
            ):
                previous = 0.0 if fret_number == 1 else fret_positions[fret_number - 1]
                position = midpoint(fret_number)
                half_span = _knot_half_span(
                    fret_number,
                    fret_positions[fret_number] - previous,
                    half_width_at(position),
                )
                markers.append(
                    InlayMarker(
                        fret_number,
                        position,
                        _knot_outline(position, half_span, self.bass_sign),
                    )
                )
        else:
            for fret_number in sorted(self.single_marker_frets):
                position = midpoint(fret_number)
                half_width = half_width_at(position)
                markers.append(
                    InlayMarker(
                        fret_number,
                        position,
                        self._marker(position, 0.0, half_width * 0.6),
                    )
                )
            for fret_number in sorted(self.double_marker_frets):
                position = midpoint(fret_number)
                half_width = half_width_at(position)
                offset = half_width * 0.55
                half_span = half_width * 0.22
                for sign in (-1.0, 1.0):
                    markers.append(
                        InlayMarker(
                            fret_number,
                            position,
                            self._marker(position, sign * offset, half_span),
                        )
                    )
        skew = self.fretboard_surface.skew
        if not skew.is_square:
            # Every marker follows the slanted or fanned frets around it:
            # a block leans point by point with them, barbed wire turns to
            # their angle at its centre, a dot moves onto their line.
            markers = [
                InlayMarker(
                    marker.fret_number,
                    marker.position,
                    _slanted(marker.outline, skew, self.style),
                )
                for marker in markers
            ]
        object.__setattr__(
            self,
            "markers",
            tuple(sorted(markers, key=lambda marker: marker.position)),
        )

    def _custom_marker(
        self,
        fret_number: int,
        front: float,
        back: float,
        half_width_at: Callable[[float], float],
    ) -> tuple[Point2D, ...]:
        """Return the drawn marker fitted to one fret space.

        Raises:
            FretboardGeometryError: If it reaches within
                ``CUSTOM_CLEARANCE`` of a fret slot or the board's edge.
        """
        points = self.custom_points or DEFAULT_CUSTOM_POINTS
        corners = [
            Point2D(
                front + along * (back - front),
                self.bass_sign * across * half_width_at(front + along * (back - front)),
            )
            for along, across in points
        ]
        if any(
            p.x - front < CUSTOM_CLEARANCE
            or back - p.x < CUSTOM_CLEARANCE
            or abs(p.y) > half_width_at(p.x) - CUSTOM_CLEARANCE
            for p in corners
        ):
            raise FretboardGeometryError(
                f"The drawn inlay at fret {fret_number} comes within "
                f"{CUSTOM_CLEARANCE:g} mm of a fret slot or the board's edge: "
                "draw it smaller in the inlay editor."
            )
        if _signed_area(corners) < 0.0:
            corners.reverse()
        return rounded_polygon_points(
            corners, [self.block_corner_radius] * len(corners), samples_per_corner=6
        )

    def editable_points(self) -> tuple[tuple[float, float], ...]:
        """Return the first marker's shape as ``custom_points`` would hold it.

        The drawn shape itself, or what this style makes at the first
        marker fret, its corners before rounding — barbed wire's, a dot as
        twelve points, the first of a split block's pieces — held inside
        ``custom_limits``, so an inlay editor can start from any style.
        """
        if self.style == "custom":
            return self.custom_points or DEFAULT_CUSTOM_POINTS
        frets = sorted((*self.single_marker_frets, *self.double_marker_frets))
        if not frets:
            return DEFAULT_CUSTOM_POINTS
        fret_number = frets[0]
        positions = {
            fret.number: fret.distance_from_nut
            for fret in FretCalculator.calculate(
                self.fretboard_surface.scale_length,
                self.fretboard_surface.fret_count,
            )
        }
        final = positions[self.fretboard_surface.fret_count]
        surface = self.fretboard_surface

        def half_width_at(position: float) -> float:
            fraction = position / final
            width = (
                surface.nut_width
                + (surface.last_fret_width - surface.nut_width) * fraction
            )
            return width / 2.0

        front = 0.0 if fret_number == 1 else positions[fret_number - 1]
        back = positions[fret_number]
        middle = (front + back) / 2.0
        (low, high), across = custom_limits(surface, frets)
        if self.style in BOARD_STYLES:
            half_length = (back - front) * self.block_length_fraction / 2.0
            start, end = middle - half_length, middle + half_length
            corners = _board_shape(
                self.style,
                start,
                end,
                half_width_at(start) - self.block_edge_margin,
                half_width_at(end) - self.block_edge_margin,
                self.bass_sign,
            )[0]
        elif self.style == "dot":
            corners = list(
                _dot_outline(middle, 0.0, self.dot_diameter / 2.0, samples=12)
            )
        elif self.style == "barbed_wire_2":
            corners = list(
                _knot_outline(
                    middle,
                    _knot_half_span(fret_number, back - front, half_width_at(middle)),
                    self.bass_sign,
                    BARBED_WIRE_2_EDITOR_OUTLINE,
                )
            )
        else:
            corners = list(
                _barbed_wire_outline(middle, 0.0, half_width_at(middle) * 0.6)
            )
        # Held where a drawn shape fits every marker (a parallelogram leans
        # out over its frets).
        return tuple(
            (
                min(high, max(low, round((p.x - front) / (back - front), 4))),
                min(
                    across,
                    max(-across, round(self.bass_sign * p.y / half_width_at(p.x), 4)),
                ),
            )
            for p in corners
        )

    def _marker(
        self, position: float, lateral_offset: float, half_span: float
    ) -> tuple[Point2D, ...]:
        """Return one barbed-wire or dot outline at a marker position."""
        if self.style == "dot":
            return _dot_outline(position, lateral_offset, self.dot_diameter / 2.0)
        return _barbed_wire_outline(position, lateral_offset, half_span)

    def _validate(self) -> None:
        """Reject an unsafe depth or an inconsistent marker-fret layout."""
        if self.style not in INLAY_STYLES:
            raise FretboardGeometryError(
                f"Unknown inlay style {self.style!r}; use one of "
                f"{', '.join(INLAY_STYLES)}."
            )
        if self.bass_sign not in (-1.0, 1.0):
            raise FretboardGeometryError("Inlay bass_sign must be -1 or +1.")
        if not math.isfinite(self.dot_diameter) or self.dot_diameter <= 0.0:
            raise FretboardGeometryError("Inlay dot diameter must be positive.")
        if self.dot_diameter >= self.fretboard_surface.nut_width:
            raise FretboardGeometryError("Inlay dots must fit inside the fretboard.")
        if not 0.0 < self.block_length_fraction <= 1.0:
            raise FretboardGeometryError(
                "Inlay block length fraction must lie in (0, 1]."
            )
        if (
            not math.isfinite(self.block_edge_margin)
            or self.block_edge_margin < 0.0
            or 2.0 * self.block_edge_margin >= self.fretboard_surface.nut_width
        ):
            raise FretboardGeometryError(
                "Inlay block edge margin must leave width for the block."
            )
        corner = self.block_corner_radius
        if not math.isfinite(corner) or corner < 0.0:
            raise FretboardGeometryError("Inlay block corner radius must be >= 0.")
        if self.style == "custom":
            _check_custom(self.custom_points or DEFAULT_CUSTOM_POINTS)
        if not math.isfinite(self.depth) or self.depth <= 0.0:
            raise FretboardGeometryError(
                "Inlay depth must be a finite, positive number."
            )
        if self.depth >= self.fretboard_surface.center_thickness:
            raise FretboardGeometryError(
                "Inlay depth must leave material above the fretboard's flat underside."
            )
        overlap = set(self.single_marker_frets) & set(self.double_marker_frets)
        if overlap:
            raise FretboardGeometryError(
                f"Frets {sorted(overlap)} cannot use both marker styles."
            )
        fret_count = self.fretboard_surface.fret_count
        for fret_number in (*self.single_marker_frets, *self.double_marker_frets):
            if not 1 <= fret_number <= fret_count:
                raise FretboardGeometryError(
                    "Inlay marker frets must fall within the fretboard's "
                    f"1-{fret_count} fret range."
                )


def _dot_outline(
    position: float,
    lateral_offset: float,
    radius: float,
    samples: int = 24,
) -> tuple[Point2D, ...]:
    """Return a sampled circle centred on one marker position."""
    return tuple(
        Point2D(
            position + radius * math.cos(2.0 * math.pi * index / samples),
            lateral_offset + radius * math.sin(2.0 * math.pi * index / samples),
        )
        for index in range(samples)
    )


def _barbed_wire_outline(
    position: float,
    lateral_offset: float,
    half_span: float,
    wire_half_thickness: float = 0.7,
    barb_reach: float = 1.6,
    barb_half_width: float = 0.9,
    barb_count: int = 3,
) -> tuple[Point2D, ...]:
    """Return a closed barbed-wire silhouette centred on one marker.

    The outline is a thin ribbon running laterally across the fretboard
    (the "wire"), with diamond-shaped barbs at even intervals along its
    length that reach forward and backward along the neck. It is built
    directly as one simple polygon: the two long edges are traced in
    order (each dipping in and back out at every barb position) and
    joined by two short end caps, so the result is always closed and
    non-self-intersecting so long as neighbouring barbs do not overlap.

    Args:
        position: Longitudinal centre of the marker in millimetres.
        lateral_offset: Lateral centre of the marker in millimetres.
        half_span: Half the wire's lateral length in millimetres.
        wire_half_thickness: Half the ribbon's resting thickness.
        barb_reach: Extra longitudinal reach of each barb tip beyond the
            ribbon's flat edge.
        barb_half_width: Half the lateral footprint of one barb's base.
        barb_count: Number of barbs distributed along the wire.

    Returns:
        Marker outline points ordered as one closed polygon loop, in
        board-plane (longitudinal, lateral) coordinates.
    """
    margin = barb_half_width * 1.5
    reachable_half_span = max(0.0, half_span - margin)
    if barb_count <= 1 or reachable_half_span == 0.0:
        barb_positions = [0.0]
    else:
        step = 2.0 * reachable_half_span / (barb_count - 1)
        barb_positions = [
            -reachable_half_span + index * step for index in range(barb_count)
        ]

    def edge(sign: float) -> list[tuple[float, float]]:
        """Return one long ribbon edge, spiking outward at every barb."""
        points = [(-half_span, sign * wire_half_thickness)]
        for lateral in barb_positions:
            points.append((lateral - barb_half_width, sign * wire_half_thickness))
            points.append((lateral, sign * (wire_half_thickness + barb_reach)))
            points.append((lateral + barb_half_width, sign * wire_half_thickness))
        points.append((half_span, sign * wire_half_thickness))
        return points

    top_edge = edge(1.0)
    bottom_edge = list(reversed(edge(-1.0)))
    loop = (*top_edge, *bottom_edge)
    return tuple(
        Point2D(position + longitudinal, lateral_offset + lateral)
        for lateral, longitudinal in loop
    )


def _knot_half_span(fret_number: int, spacing: float, half_width: float) -> float:
    """Return a ``barbed_wire_2`` knot's half-length across the board.

    ``BARBED_WIRE_2_SPAN`` of the board's width, less where the knot's
    barbs would come within ``BARBED_WIRE_2_FRET_CLEARANCE`` of the frets.

    Raises:
        FretboardGeometryError: If the fret space is too short for any.
    """
    half_span = min(
        BARBED_WIRE_2_SPAN * half_width,
        (spacing / 2.0 - BARBED_WIRE_2_FRET_CLEARANCE) / BARBED_WIRE_2_ALONG,
    )
    if half_span <= 0.0:
        raise FretboardGeometryError(
            f"Fret {fret_number}'s space is too short for a barbed_wire_2 marker."
        )
    return half_span


def _knot_outline(
    position: float,
    half_span: float,
    bass_sign: float,
    outline: tuple[tuple[float, float], ...] = BARBED_WIRE_2_OUTLINE,
) -> tuple[Point2D, ...]:
    """Return the traced barbed-wire knot centred on one marker.

    The wire runs across the board, ``half_span`` either side of the
    centreline, its barbs reaching along the neck; the knot is drawn as
    traced on a right-handed board and mirrored on a left-handed one,
    counter-clockwise either way.

    Args:
        position: Longitudinal centre of the marker in millimetres.
        half_span: Half the wire's length across the board, in mm.
        bass_sign: Which side the bass strings are on (-1: -Y).
        outline: The traced outline (``BARBED_WIRE_2_OUTLINE``) or the
            editor's coarser one, in its own unit.

    Returns:
        Marker outline points ordered as one closed polygon loop, in
        board-plane (longitudinal, lateral) coordinates.
    """
    points = [
        Point2D(position + along * half_span, -bass_sign * across * half_span)
        for along, across in outline
    ]
    return tuple(points if bass_sign < 0.0 else reversed(points))


def _slanted(
    outline: tuple[Point2D, ...], skew: FretSkew, style: str
) -> tuple[Point2D, ...]:
    """Return a marker moved with slanted or fanned frets.

    A board-spanning shape (a block, a trapezoid...) leans every point
    with the frets there, so its front and back stay parallel to the frets
    either side. Barbed wire turns about its
    own centre to the frets' angle there, keeping its shape. A dot keeps
    its shape and moves by the lean at its centre, onto the line between
    the two frets.
    """
    if style in BOARD_STYLES:
        return tuple(Point2D(p.x + skew.at(p.x) * p.y, p.y) for p in outline)
    centre_x = sum(p.x for p in outline) / len(outline)
    centre_y = sum(p.y for p in outline) / len(outline)
    lean = skew.at(centre_x)
    moved_x = centre_x + lean * centre_y
    if style == "dot":
        return tuple(Point2D(p.x - centre_x + moved_x, p.y) for p in outline)
    # Turn so the marker's across-the-board axis (0, 1) runs along the
    # fret direction (lean, 1).
    angle = -math.atan(lean)
    cosine, sine = math.cos(angle), math.sin(angle)
    return tuple(
        Point2D(
            moved_x + (p.x - centre_x) * cosine - (p.y - centre_y) * sine,
            centre_y + (p.x - centre_x) * sine + (p.y - centre_y) * cosine,
        )
        for p in outline
    )


def _board_shape(
    style: str,
    front: float,
    back: float,
    front_half: float,
    back_half: float,
    bass_sign: float,
) -> list[list[Point2D]]:
    """Return the corners of one board-spanning marker's pieces.

    ``front``/``back`` bound it along the neck, ``front_half``/``back_half``
    are the board's half-width less the edge margin there; ``bass_sign``
    says which side is the bass side.
    """
    bass, treble = bass_sign, -bass_sign
    length = back - front
    block = [
        Point2D(front, treble * front_half),
        Point2D(back, treble * back_half),
        Point2D(back, bass * back_half),
        Point2D(front, bass * front_half),
    ]
    if style == "block":
        shapes = [block]
    elif style == "trapezoid":
        # Long at the bass edge, short at the treble edge.
        inset = length * (1.0 - TRAPEZOID_SHORT_SIDE) / 2.0
        shapes = [
            [
                Point2D(front + inset, treble * front_half),
                Point2D(back - inset, treble * back_half),
                Point2D(back, bass * back_half),
                Point2D(front, bass * front_half),
            ]
        ]
    elif style == "sharktooth":
        # Across the board at the bridge side, along the bass edge, its
        # point at the treble edge by the bridge-side fret.
        shapes = [
            [
                Point2D(back, treble * back_half),
                Point2D(back, bass * back_half),
                Point2D(front, bass * front_half),
            ]
        ]
    elif style == "parallelogram":
        lean = length * PARALLELOGRAM_LEAN
        shapes = [
            [
                Point2D(front - lean, treble * front_half),
                Point2D(back - lean, treble * back_half),
                Point2D(back, bass * back_half),
                Point2D(front, bass * front_half),
            ]
        ]
    elif style == "diamond":
        middle = (front + back) / 2.0
        half = (front_half + back_half) / 2.0
        shapes = [
            [
                Point2D(front, 0.0),
                Point2D(middle, treble * half),
                Point2D(back, 0.0),
                Point2D(middle, bass * half),
            ]
        ]
    else:  # split_block
        # Split along the diagonal from the treble front corner to the
        # bass back corner, SPLIT_BLOCK_GAP apart.
        start, end = block[0], block[2]
        shapes = [
            _clip_beside(block, start, end, SPLIT_BLOCK_GAP / 2.0, side)
            for side in (1.0, -1.0)
        ]
    # Every outline counter-clockwise, as the rest of the layout's are.
    return [
        shape if _signed_area(shape) > 0.0 else list(reversed(shape))
        for shape in shapes
    ]


def _clip_beside(
    polygon: list[Point2D],
    start: Point2D,
    end: Point2D,
    gap: float,
    side: float,
) -> list[Point2D]:
    """Return the part of ``polygon`` more than ``gap`` to one ``side`` of a line."""
    dx, dy = end.x - start.x, end.y - start.y
    length = math.hypot(dx, dy)

    def distance(point: Point2D) -> float:
        return (
            side * ((point.x - start.x) * dy - (point.y - start.y) * dx) / length - gap
        )

    clipped: list[Point2D] = []
    for index, current in enumerate(polygon):
        following = polygon[(index + 1) % len(polygon)]
        here, there = distance(current), distance(following)
        if here >= 0.0:
            clipped.append(current)
        if (here >= 0.0) != (there >= 0.0):
            fraction = here / (here - there)
            clipped.append(
                Point2D(
                    current.x + (following.x - current.x) * fraction,
                    current.y + (following.y - current.y) * fraction,
                )
            )
    return clipped


def _signed_area(points: list[Point2D]) -> float:
    """Return a polygon's signed area (positive counter-clockwise)."""
    return 0.5 * sum(
        a.x * b.y - b.x * a.y for a, b in zip(points, points[1:] + points[:1])
    )


def custom_limits(
    surface: FretboardSurface, marker_frets: Sequence[int]
) -> tuple[tuple[float, float], float]:
    """Return where a drawn marker's corners fit every marker.

    ``((low, high), across)``: ``along`` from ``low`` to ``high`` keeps
    ``CUSTOM_CLEARANCE`` from the frets in the shortest of the markers'
    fret spaces, ``across`` within ``±across`` keeps it from the edges
    where the board is narrowest (the first marker's fret toward the nut);
    rounded inward to the four decimals an inlay editor writes.

    Raises:
        FretboardGeometryError: For no marker fret, or one off the board.
    """
    if not marker_frets:
        raise FretboardGeometryError("No fret has a marker.")
    positions = {
        fret.number: fret.distance_from_nut
        for fret in FretCalculator.calculate(surface.scale_length, surface.fret_count)
    }
    if not all(1 <= fret <= surface.fret_count for fret in marker_frets):
        raise FretboardGeometryError("A marker fret lies off the fretboard.")
    shortest = min(
        positions[fret] - (0.0 if fret == 1 else positions[fret - 1])
        for fret in marker_frets
    )
    first = min(marker_frets)
    front = 0.0 if first == 1 else positions[first - 1]
    half = (
        surface.nut_width
        + (surface.last_fret_width - surface.nut_width)
        * front
        / positions[surface.fret_count]
    ) / 2.0
    margin = CUSTOM_CLEARANCE / shortest
    return (
        (math.ceil(margin * 1e4) / 1e4, math.floor((1.0 - margin) * 1e4) / 1e4),
        math.floor((1.0 - CUSTOM_CLEARANCE / half) * 1e4) / 1e4,
    )


def _check_custom(points: tuple[tuple[float, float], ...]) -> None:
    """Refuse a drawn marker that cannot be cut: too few points, numbers
    outside its fret space or the board, or sides that cross."""
    if len(points) < 3:
        raise FretboardGeometryError("A drawn inlay needs at least three points.")
    if not all(
        len(point) == 2
        and all(isinstance(v, (int, float)) and math.isfinite(v) for v in point)
        and 0.0 < point[0] < 1.0
        and -1.0 < point[1] < 1.0
        for point in points
    ):
        raise FretboardGeometryError(
            "A drawn inlay's points must lie between its frets (along 0 to 1) "
            "and inside the board (across -1 to 1)."
        )
    corners = [Point2D(along, across) for along, across in points]
    count = len(corners)

    def turn(a: Point2D, b: Point2D, c: Point2D) -> float:
        return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)

    for i in range(count):
        a, b = corners[i], corners[(i + 1) % count]
        for j in range(i + 2, count):
            if i == 0 and j == count - 1:
                continue  # the side that closes the loop meets the first
            c, d = corners[j], corners[(j + 1) % count]
            if (turn(a, b, c) > 0.0) != (turn(a, b, d) > 0.0) and (
                turn(c, d, a) > 0.0
            ) != (turn(c, d, b) > 0.0):
                raise FretboardGeometryError("A drawn inlay's sides must not cross.")

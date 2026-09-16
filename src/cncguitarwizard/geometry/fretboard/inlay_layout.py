"""Position marker inlays cut into the fretboard surface.

Three styles share one layout: ``barbed_wire`` (the Prototype001 default),
round ``dot`` markers, and Gibson-style ``block`` inlays that follow the
board's taper.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from ..exceptions import FretboardGeometryError
from ..fret import FretCalculator
from ..primitives import Point2D, rounded_polygon_points
from .surface import FretboardSurface

InlayStyle = Literal["barbed_wire", "dot", "block"]


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
    at the octave and double-octave — except in the ``block`` style,
    where every listed fret gets one block, as on a Gibson.

    Args:
        fretboard_surface: Surface the markers are cut into. Its own
            nut-to-final-fret taper sizes each marker to the locally
            available width.
        depth: Pocket depth in millimetres, cut down from the playing
            surface centerline.
        single_marker_frets: Frets that receive one centered marker.
        double_marker_frets: Frets that receive two offset markers.
        style: ``barbed_wire``, ``dot`` or ``block``.
        dot_diameter: Diameter of a ``dot`` marker.
        block_length_fraction: A ``block``'s length along the neck as a
            fraction of the fret spacing it sits in.
        block_edge_margin: Wood left between a ``block`` and each board
            edge.
        block_corner_radius: Corner rounding of a ``block``.

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
            previous = (
                0.0 if fret_number == 1 else fret_positions[fret_number - 1]
            )
            return (previous + fret_positions[fret_number]) / 2.0

        def half_width_at(position: float) -> float:
            fraction = position / final_fret_position
            surface = self.fretboard_surface
            width = surface.nut_width + (
                surface.last_fret_width - surface.nut_width
            ) * fraction
            return width / 2.0

        markers: list[InlayMarker] = []
        if self.style == "block":
            for fret_number in sorted(
                (*self.single_marker_frets, *self.double_marker_frets)
            ):
                previous = 0.0 if fret_number == 1 else fret_positions[fret_number - 1]
                spacing = fret_positions[fret_number] - previous
                position = midpoint(fret_number)
                half_length = spacing * self.block_length_fraction / 2.0
                front, back = position - half_length, position + half_length
                vertices = [
                    Point2D(front, -(half_width_at(front) - self.block_edge_margin)),
                    Point2D(back, -(half_width_at(back) - self.block_edge_margin)),
                    Point2D(back, half_width_at(back) - self.block_edge_margin),
                    Point2D(front, half_width_at(front) - self.block_edge_margin),
                ]
                markers.append(
                    InlayMarker(
                        fret_number,
                        position,
                        rounded_polygon_points(
                            vertices,
                            [self.block_corner_radius] * 4,
                            samples_per_corner=6,
                        ),
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
        object.__setattr__(
            self,
            "markers",
            tuple(sorted(markers, key=lambda marker: marker.position)),
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
        if self.style not in ("barbed_wire", "dot", "block"):
            raise FretboardGeometryError(
                f"Unknown inlay style {self.style!r}; use barbed_wire, dot or block."
            )
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
        if not math.isfinite(self.depth) or self.depth <= 0.0:
            raise FretboardGeometryError(
                "Inlay depth must be a finite, positive number."
            )
        if self.depth >= self.fretboard_surface.center_thickness:
            raise FretboardGeometryError(
                "Inlay depth must leave material above the fretboard's "
                "flat underside."
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
            points.append(
                (lateral, sign * (wire_half_thickness + barb_reach))
            )
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

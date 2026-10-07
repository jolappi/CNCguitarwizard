"""Truss-rod covers: the plates screwed over a headstock adjuster's trough.

Each style is drawn in the cover's own frame: ``u`` from its nut end (0)
toward the headstock tip, ``v`` across, both in millimetres, positive
toward the treble side of a right-handed neck. Its corners are joined by
straight lines and rounded with their radii. The styles are mockups of
the familiar shapes, not the makers' own plates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

TrussRodCoverStyle = Literal["bell", "ibanez", "prs", "rectangle", "custom"]

TRUSS_ROD_COVER_STYLES: tuple[str, ...] = (
    "bell",
    "ibanez",
    "prs",
    "rectangle",
    "custom",
)
"""Every truss-rod cover style, in the order the form offers them."""

TRUSS_ROD_COVER_SIZES: dict[str, tuple[float, float]] = {
    "bell": (41.0, 28.5),
    "ibanez": (26.0, 26.0),
    "prs": (30.0, 22.0),
    "custom": (30.0, 24.0),
}
"""Each style's own length and width, in mm (``rectangle`` is sized round
the trough instead)."""

CUSTOM_COVER_RADIUS = 1.5
"""A drawn cover's corner rounding, in mm."""

BELL_TOP = 0.55
"""A bell's round top's width, as a share of its foot's."""

BELL_FLARE = 2.5
"""How fast a bell's sides narrow from its foot: its width above the
waist's goes as ``(1 - t) ** BELL_FLARE`` from the foot (0) to the top (1)."""

BELL_SIDE_SAMPLES = 10
"""Points along each side of a bell, foot to top."""

BELL_TOP_SAMPLES = 8
"""Points round a bell's top."""


@dataclass(frozen=True, slots=True)
class TrussRodCoverShape:
    """A truss-rod cover's corners and screws in its own frame (mm).

    Args:
        corners: The outline's corners, ``(u, v)``, in order round it.
        radii: Each corner's rounding.
        screws: The screw holes' centres, ``(u, v)``.
    """

    corners: tuple[tuple[float, float], ...]
    radii: tuple[float, ...]
    screws: tuple[tuple[float, float], ...]


def _mirrored(
    half: list[tuple[float, float, float]],
) -> tuple[tuple[tuple[float, float], ...], tuple[float, ...]]:
    """Return corners and radii from one side's ``(u, v, radius)``, nut end
    first, mirrored to the other side back to the nut end."""
    corners = [(u, v) for u, v, _ in half] + [(u, -v) for u, v, _ in reversed(half)]
    radii = [r for _, _, r in half] + [r for _, _, r in reversed(half)]
    return tuple(corners), tuple(radii)


def truss_rod_cover_shape(
    style: str,
    length: float,
    width: float,
    points: tuple[tuple[float, float], ...] = (),
    screws: tuple[tuple[float, float], ...] = (),
) -> TrussRodCoverShape:
    """Return a cover style's shape at a size.

    Args:
        style: One of ``TRUSS_ROD_COVER_STYLES``.
        length: The cover's length along the neck, in mm.
        width: Its width across the neck, in mm.
        points: A ``custom`` cover's corners as ``(along, across)``:
            ``along`` 0 at its nut end and 1 at its far end, ``across``
            the share of its half-width (-1 to 1).
        screws: A ``custom`` cover's screw centres, likewise.

    Returns:
        The shape, in mm.
    """
    half = width / 2.0
    corners: tuple[tuple[float, float], ...]
    radii: tuple[float, ...]
    screw_points: tuple[tuple[float, float], ...]
    if style == "bell":
        # Gibson's bell: wide at the nut over the trough, its sides flaring
        # in a hollow curve from its foot (narrowing fast there, then
        # slowly) into a narrow waist and a round top toward the
        # headstock's tip; a screw in each of the foot's corners either
        # side of the trough, and one in the top.
        waist = BELL_TOP * half
        dome = length - waist
        side = [
            (dome * t, waist + (half - waist) * (1.0 - t) ** BELL_FLARE)
            for t in (step / BELL_SIDE_SAMPLES for step in range(1, BELL_SIDE_SAMPLES))
        ]
        top = [
            (dome + waist * math.sin(angle), waist * math.cos(angle))
            for angle in (
                math.pi * step / BELL_TOP_SAMPLES
                for step in range(BELL_TOP_SAMPLES + 1)
            )
        ]
        corners = (
            (0.0, half),
            *side,
            *top,
            *((u, -v) for u, v in reversed(side)),
            (0.0, -half),
        )
        radii = (2.5, *(0.0,) * (len(corners) - 2), 2.5)
        screw_points = (
            (0.08 * length, 0.66 * half),
            (0.08 * length, -0.66 * half),
            (dome, 0.0),
        )
    elif style == "ibanez":
        # A rounded triangle, wide at the nut, two screws at its corners.
        corners, radii = (
            ((0.0, half), (length, 0.0), (0.0, -half)),
            (3.0, 6.0, 3.0),
        )
        screw_points = ((0.12 * length, 0.62 * half), (0.12 * length, -0.62 * half))
    elif style == "prs":
        # A teardrop, round at the far end, two screws past the trough.
        corners, radii = _mirrored(
            [
                (0.0, 0.55 * half, 3.0),
                (0.5 * length, half, 12.0),
                (length, 0.45 * half, 8.0),
            ]
        )
        screw_points = ((0.66 * length, 0.5 * half), (0.66 * length, -0.5 * half))
    elif style == "rectangle":
        # Round at the far end, two screws at the nut end, one at the far.
        corners, radii = (
            ((0.0, half), (length, half), (length, -half), (0.0, -half)),
            (2.0, 0.9 * half, 0.9 * half, 2.0),
        )
        screw_points = (
            (3.5, half - 3.0),
            (3.5, -(half - 3.0)),
            (length - 4.0, 0.0),
        )
    else:
        corners = tuple((u * length, v * half) for u, v in points)
        radii = (CUSTOM_COVER_RADIUS,) * len(corners)
        screw_points = tuple((u * length, v * half) for u, v in screws)
    return TrussRodCoverShape(corners, radii, screw_points)


def editable_cover_points(
    shape: TrussRodCoverShape, length: float, width: float
) -> tuple[tuple[tuple[float, float], ...], tuple[tuple[float, float], ...]]:
    """Return a shape's corners and screws as a ``custom`` cover holds them.

    So an editor can start a drawn cover from any style.
    """
    half = width / 2.0

    def unit(point: tuple[float, float]) -> tuple[float, float]:
        return (round(point[0] / length, 4), round(point[1] / half, 4))

    return (
        tuple(unit(point) for point in shape.corners),
        tuple(unit(point) for point in shape.screws),
    )


def check_custom_cover(
    points: tuple[tuple[float, float], ...],
    screws: tuple[tuple[float, float], ...],
) -> str | None:
    """Return why a drawn cover cannot be cut, or ``None`` if it can."""
    if len(points) < 3:
        return "a drawn truss-rod cover needs at least three corners"
    if not screws:
        return "a drawn truss-rod cover needs at least one screw"
    for u, v in (*points, *screws):
        if not (math.isfinite(u) and math.isfinite(v)):
            return "a drawn truss-rod cover's points must be finite"
    return None

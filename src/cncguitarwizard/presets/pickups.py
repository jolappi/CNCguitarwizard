"""Pickup routes: the pocket each pickup type needs and its screw spots.

Every route is described in a local frame centred on the pickup — X along
the neck, Y across it — and placed by adding the pickup's centre. The
humbucker is the Design by Jone drawing's own route; the bass routes are
labelled starting values for the common pickup families, to be checked
against the pickups in hand before cutting.
"""

from __future__ import annotations

from typing import Literal

from ..geometry.body import TracedCavity
from ..geometry.primitives import Point2D, rounded_polygon_points
from ._omarunko_outline import OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS

PickupType = Literal["humbucker", "jazz_bass", "precision_bass", "bass_soapbar", "none"]
"""A pickup family, or ``"none"`` for no pickup in that position."""

PICKUP_LABELS: dict[str, str] = {
    "humbucker": "Humbucker (guitar)",
    "jazz_bass": "Jazz Bass single coil",
    "precision_bass": "Precision Bass split coil",
    "bass_soapbar": "Bass humbucker (MM-style soapbar)",
    "none": "None",
}

# Jazz Bass: a narrow bar with mounting ears at both ends, screwed
# through the ears. Bass soapbar: a wide rounded bar, screwed at both
# ends. Precision Bass: two offset coils, each screwed at both ends.
_JAZZ_LENGTH, _JAZZ_WIDTH, _JAZZ_SCREW = 100.0, 21.0, 47.0
_SOAPBAR_LENGTH, _SOAPBAR_WIDTH, _SOAPBAR_SCREW = 102.0, 44.0, 45.0
_P_COIL_LENGTH, _P_COIL_WIDTH, _P_COIL_OFFSET, _P_COIL_SHIFT = 58.0, 21.0, 19.0, 10.5


def _bar(length: float, width: float, radius: float) -> tuple[tuple[float, float], ...]:
    half_x, half_y = width / 2.0, length / 2.0
    corners = [
        Point2D(-half_x, -half_y),
        Point2D(half_x, -half_y),
        Point2D(half_x, half_y),
        Point2D(-half_x, half_y),
    ]
    return tuple(
        (point.x, point.y)
        for point in rounded_polygon_points(corners, [radius] * 4, samples_per_corner=6)
    )


def _precision(bass_sign: float) -> tuple[tuple[float, float], ...]:
    """Return the split-coil route: the bass coil nut-ward, the treble one
    tail-ward, overlapping across the centreline."""
    shift, width = _P_COIL_SHIFT, _P_COIL_WIDTH
    reach = _P_COIL_OFFSET + _P_COIL_LENGTH / 2.0
    inner = _P_COIL_LENGTH / 2.0 - _P_COIL_OFFSET
    corners = [
        (-shift - width / 2.0, -reach),
        (-shift + width / 2.0, -reach),
        (-shift + width / 2.0, -inner),
        (shift + width / 2.0, -inner),
        (shift + width / 2.0, reach),
        (shift - width / 2.0, reach),
        (shift - width / 2.0, inner),
        (-shift - width / 2.0, inner),
    ]
    # Bass (low strings) coil lies on the bass side of the centreline.
    return tuple((x, -bass_sign * y) for x, y in corners)


def pickup_half_length(kind: PickupType) -> float:
    """Return how far the route reaches along the neck from its centre."""
    if kind == "humbucker":
        return max(x for x, _ in OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS)
    if kind == "precision_bass":
        return _P_COIL_SHIFT + _P_COIL_WIDTH / 2.0
    if kind == "jazz_bass":
        return _JAZZ_WIDTH / 2.0
    if kind == "bass_soapbar":
        return _SOAPBAR_WIDTH / 2.0
    return 0.0


def pickup_route(
    kind: PickupType, name: str, center_x: float, depth: float, bass_sign: float
) -> TracedCavity | None:
    """Return the route for a pickup centred at ``center_x``, or ``None``.

    Args:
        kind: The pickup family.
        name: Route name, e.g. ``"Neck pickup route"``.
        center_x: Route centre along the neck, on the centreline.
        depth: Route depth from the top face.
        bass_sign: +1 when the bass side is +Y, -1 when it is -Y.
    """
    local: tuple[tuple[float, float], ...]
    if kind == "none":
        return None
    if kind == "humbucker":
        local = OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS
    elif kind == "jazz_bass":
        local = _bar(_JAZZ_LENGTH, _JAZZ_WIDTH, 6.0)
    elif kind == "bass_soapbar":
        local = _bar(_SOAPBAR_LENGTH, _SOAPBAR_WIDTH, 12.0)
    else:
        local = _precision(bass_sign)
    return TracedCavity(name, tuple(Point2D(center_x + x, y) for x, y in local), depth)


def pickup_screws(
    kind: PickupType,
    center_x: float,
    bass_sign: float,
    humbucker_screw_spacing: float,
) -> tuple[tuple[str, float, float], ...]:
    """Return ``(label, x, y)`` for each height-screw recess of a pickup.

    ``label`` is ``bass`` / ``treble`` (with a coil prefix for a split
    pickup); the humbucker's spacing is ``humbucker_screw_spacing``.
    """

    def pair(
        x: float, spacing: float, prefix: str = ""
    ) -> list[tuple[str, float, float]]:
        return [
            (f"{prefix}bass", x, bass_sign * spacing / 2.0),
            (f"{prefix}treble", x, -bass_sign * spacing / 2.0),
        ]

    if kind == "none":
        return ()
    if kind == "humbucker":
        return tuple(pair(center_x, humbucker_screw_spacing))
    if kind == "jazz_bass":
        return tuple(pair(center_x, 2.0 * _JAZZ_SCREW))
    if kind == "bass_soapbar":
        return tuple(pair(center_x, 2.0 * _SOAPBAR_SCREW))
    # Each coil is screwed 4 mm in from both of its ends; local Y has the
    # bass side negative, as in _precision.
    reach = _P_COIL_OFFSET + _P_COIL_LENGTH / 2.0 - 4.0
    inner = _P_COIL_LENGTH / 2.0 - _P_COIL_OFFSET - 4.0
    x_bass, x_treble = center_x - _P_COIL_SHIFT, center_x + _P_COIL_SHIFT
    local = (
        ("bass coil bass", x_bass, -reach),
        ("bass coil treble", x_bass, inner),
        ("treble coil bass", x_treble, -inner),
        ("treble coil treble", x_treble, reach),
    )
    return tuple((label, x, -bass_sign * y) for label, x, y in local)

"""Pickup routes: the pocket each pickup type needs and its screw spots.

Every route is described in a local frame centred on the pickup — X along
the neck, Y across it — and placed by adding the pickup's centre. The
humbucker is the Design by Jone drawing's own route; the bass routes are
labelled starting values for the common pickup families, to be checked
against the pickups in hand before cutting.
"""

from __future__ import annotations

import math
from typing import Literal

from ..geometry.body import TracedCavity
from ..geometry.primitives import Point2D, rounded_polygon_points
from ._omarunko_outline import OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS

PickupType = Literal[
    "humbucker", "single_coil", "jazz_bass", "precision_bass", "bass_soapbar", "none"
]
"""A pickup family, or ``"none"`` for no pickup in that position."""

PICKUP_LABELS: dict[str, str] = {
    "humbucker": "Humbucker (guitar)",
    "single_coil": "Single coil (guitar)",
    "jazz_bass": "Jazz Bass single coil",
    "precision_bass": "Precision Bass split coil",
    "bass_soapbar": "Bass humbucker (MM-style soapbar)",
    "none": "None",
}

PickupConfiguration = Literal[
    "HH", "HSH", "HSS", "H", "SSS", "SS", "PJ", "JJ", "P", "MM", "custom"
]
"""A pickup layout: H humbucker, S single coil, P/J/MM the bass types."""

PICKUP_CONFIGURATIONS: dict[str, tuple[PickupType, PickupType, PickupType]] = {
    "HH": ("humbucker", "none", "humbucker"),
    "HSH": ("humbucker", "single_coil", "humbucker"),
    "HSS": ("single_coil", "single_coil", "humbucker"),
    "H": ("none", "none", "humbucker"),
    "SSS": ("single_coil", "single_coil", "single_coil"),
    "SS": ("single_coil", "none", "single_coil"),
    "PJ": ("precision_bass", "none", "jazz_bass"),
    "JJ": ("jazz_bass", "none", "jazz_bass"),
    "P": ("precision_bass", "none", "none"),
    "MM": ("none", "none", "bass_soapbar"),
}
"""The (neck, middle, bridge) pickup types of each named configuration.

HSS reads from the neck: single coils at the neck and middle, a
humbucker at the bridge. ``"custom"`` is not listed: it takes the three
types from their own parameters.
"""

# Guitar single coil: a narrow bar with round ends, screwed at both ends.
# Jazz Bass: a narrow bar with mounting ears at both ends, screwed
# through the ears. Bass soapbar: a wide rounded bar, screwed at both
# ends. Precision Bass: two offset coils, each screwed at both ends.
_SINGLE_LENGTH, _SINGLE_WIDTH, _SINGLE_SCREW = 88.0, 20.0, 38.0
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


def _local_outline(
    kind: PickupType, bass_sign: float
) -> tuple[tuple[float, float], ...]:
    """Return the route outline centred on the origin, unrotated."""
    if kind == "humbucker":
        return OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS
    if kind == "single_coil":
        return _bar(_SINGLE_LENGTH, _SINGLE_WIDTH, _SINGLE_WIDTH / 2.0 - 0.01)
    if kind == "jazz_bass":
        return _bar(_JAZZ_LENGTH, _JAZZ_WIDTH, 6.0)
    if kind == "bass_soapbar":
        return _bar(_SOAPBAR_LENGTH, _SOAPBAR_WIDTH, 12.0)
    return _precision(bass_sign)


def _rotated(
    points: tuple[tuple[float, float], ...], angle_degrees: float, bass_sign: float
) -> tuple[tuple[float, float], ...]:
    """Turn points about the origin so the treble end swings toward the tail.

    A slanted bridge single coil (a Strat's) sits with its treble end
    nearer the bridge; with the bass side at ``bass_sign`` the treble end
    is at -bass_sign·Y, and a positive angle moves it toward +X.
    """
    if angle_degrees == 0.0:
        return points
    angle = math.radians(angle_degrees) * bass_sign
    cosine, sine = math.cos(angle), math.sin(angle)
    return tuple((x * cosine - y * sine, x * sine + y * cosine) for x, y in points)


def pickup_half_length(
    kind: PickupType, angle_degrees: float = 0.0, bass_sign: float = -1.0
) -> float:
    """Return how far the route reaches along the neck from its centre."""
    if kind == "none":
        return 0.0
    return max(
        abs(x)
        for x, _ in _rotated(_local_outline(kind, bass_sign), angle_degrees, bass_sign)
    )


def pickup_route(
    kind: PickupType,
    name: str,
    center_x: float,
    depth: float,
    bass_sign: float,
    angle_degrees: float = 0.0,
) -> TracedCavity | None:
    """Return the route for a pickup centred at ``center_x``, or ``None``.

    Args:
        kind: The pickup family.
        name: Route name, e.g. ``"Neck pickup route"``.
        center_x: Route centre along the neck, on the centreline.
        depth: Route depth from the top face.
        bass_sign: +1 when the bass side is +Y, -1 when it is -Y.
        angle_degrees: Slant, the treble end toward the tail (see
            ``_rotated``).
    """
    if kind == "none":
        return None
    local = _rotated(_local_outline(kind, bass_sign), angle_degrees, bass_sign)
    return TracedCavity(name, tuple(Point2D(center_x + x, y) for x, y in local), depth)


def pickup_screws(
    kind: PickupType,
    center_x: float,
    bass_sign: float,
    humbucker_screw_spacing: float,
    angle_degrees: float = 0.0,
) -> tuple[tuple[str, float, float], ...]:
    """Return ``(label, x, y)`` for each height-screw recess of a pickup.

    ``label`` is ``bass`` / ``treble`` (with a coil prefix for a split
    pickup); the humbucker's spacing is ``humbucker_screw_spacing``. The
    screws turn with the route by ``angle_degrees``.
    """

    def pair(spacing: float) -> list[tuple[str, float, float]]:
        return [
            ("bass", 0.0, bass_sign * spacing / 2.0),
            ("treble", 0.0, -bass_sign * spacing / 2.0),
        ]

    local: list[tuple[str, float, float]]
    if kind == "none":
        return ()
    if kind == "humbucker":
        local = pair(humbucker_screw_spacing)
    elif kind == "single_coil":
        local = pair(2.0 * _SINGLE_SCREW)
    elif kind == "jazz_bass":
        local = pair(2.0 * _JAZZ_SCREW)
    elif kind == "bass_soapbar":
        local = pair(2.0 * _SOAPBAR_SCREW)
    else:
        # Each coil is screwed 4 mm in from both of its ends; local Y has
        # the bass side negative, as in _precision.
        reach = _P_COIL_OFFSET + _P_COIL_LENGTH / 2.0 - 4.0
        inner = _P_COIL_LENGTH / 2.0 - _P_COIL_OFFSET - 4.0
        local = [
            (label, x, -bass_sign * y)
            for label, x, y in (
                ("bass coil bass", -_P_COIL_SHIFT, -reach),
                ("bass coil treble", -_P_COIL_SHIFT, inner),
                ("treble coil bass", _P_COIL_SHIFT, -inner),
                ("treble coil treble", _P_COIL_SHIFT, reach),
            )
        ]
    turned = _rotated(tuple((x, y) for _, x, y in local), angle_degrees, bass_sign)
    return tuple(
        (label, center_x + x, y)
        for (label, _, _), (x, y) in zip(local, turned, strict=True)
    )

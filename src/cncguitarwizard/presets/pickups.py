"""Pickup routes: the pocket each pickup type needs and its screw spots.

Every route is described in a local frame centred on the pickup — X along
the neck, Y across it — and placed by adding the pickup's centre. The
humbucker is the Design by Jone drawing's own route; the bass routes are
labelled starting values for the common pickup families, to be checked
against the pickups in hand before cutting. Guitar pickups for seven and
eight strings are the six-string routes stretched across the strings by
``PICKUP_STRETCH_PER_STRING`` per extra string.
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
# Bass soapbar: a wide rounded bar, screwed at both ends. The bass routes
# follow Warmoth's rout diagrams (warmoth.com/bass-pickup-routs): the
# Jazz Bass a 96 x 20 mm bar (3.75 x 0.79 in, the bridge rout; the neck
# pickup is 3-5/8 in) with two round recesses in each long side, a screw
# in each; the Precision Bass two 58 x 28.5 mm coils
# (2.28 in along the neck over both), 23 mm over each other across the
# strings (3.678 in over both), each with a round ear at both ends that
# its screws go through.
_SINGLE_LENGTH, _SINGLE_WIDTH, _SINGLE_SCREW = 88.0, 20.0, 38.0
_JAZZ_LENGTH, _JAZZ_WIDTH = 96.0, 20.0
_JAZZ_SIDE_RECESS, _JAZZ_SIDE_RADIUS, _JAZZ_SIDE_INSET = 19.6, 8.0, 3.0
_JAZZ_PICKUP_WIDTH = 18.2
"""The Jazz Bass pickup itself across the neck (a Seymour Duncan SJB-1b
bridge pickup is 94.4 x 18.2 mm)."""
_JAZZ_SCREW_ACROSS = _JAZZ_PICKUP_WIDTH / 2.0 + 2.9
"""How far out from the route's middle its screws sit (12 mm): through the
ears on the pickup's sides, 2.9 mm clear of them, in the side recesses."""
_SOAPBAR_LENGTH, _SOAPBAR_WIDTH, _SOAPBAR_SCREW = 102.0, 44.0, 45.0
_P_COIL_LENGTH, _P_COIL_WIDTH, _P_COIL_OFFSET, _P_COIL_SHIFT = 58.0, 28.5, 17.5, 14.25
_P_EAR_RADIUS, _P_EAR_INSET = 7.0, 1.2
"""A Precision coil's ear: its radius, and how far inside the coil's end
its centre (the screw) sits, in mm."""

PICKUP_STRETCH_PER_STRING = 12.0
"""How much longer (across the strings) a guitar pickup is per string past six.

A seven-string humbucker is about 82.5 mm long against a six-string's
70 mm, an eight-string's about 94 mm; the route and its screw spacing
grow by the same amount.
"""


def pickup_stretch(kind: PickupType, string_count: int) -> float:
    """Return how much a pickup's route is lengthened for ``string_count``.

    Only the guitar humbucker and single coil grow; the bass routes and
    guitars of six strings or fewer keep their size.
    """
    if kind not in ("humbucker", "single_coil") or string_count <= 6:
        return 0.0
    return (string_count - 6) * PICKUP_STRETCH_PER_STRING


def _stretched(
    points: tuple[tuple[float, float], ...], stretch: float
) -> tuple[tuple[float, float], ...]:
    """Move each half of a route outward across the strings by ``stretch / 2``.

    The ends (and a humbucker's ears) keep their shape; the straight sides
    between them get longer.
    """
    if stretch == 0.0:
        return points
    half = stretch / 2.0
    return tuple(
        (x, y + half if y > 0.0 else y - half if y < 0.0 else y) for x, y in points
    )


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


def _bump(
    start: tuple[float, float],
    end: tuple[float, float],
    centre: tuple[float, float],
    radius: float,
) -> tuple[tuple[float, float], ...]:
    """Return a round bulge out of a straight side of a route.

    ``start`` and ``end`` are the side's corners in the route's own order,
    counter-clockwise, so the outside lies to the side's right. The
    outline leaves the side where the circle about ``centre`` crosses it,
    runs round the circle's outer part and rejoins the side; ``centre``
    may lie on either side of it, nearer than ``radius``.
    """
    (x0, y0), (x1, y1) = start, end
    length = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    nx, ny = uy, -ux
    cx, cy = centre
    across = (cx - x0) * nx + (cy - y0) * ny
    along = (cx - x0) * ux + (cy - y0) * uy
    half_chord = math.sqrt(radius**2 - across**2)
    leave = (x0 + ux * (along - half_chord), y0 + uy * (along - half_chord))
    rejoin = (x0 + ux * (along + half_chord), y0 + uy * (along + half_chord))
    first = math.atan2(leave[1] - cy, leave[0] - cx)
    last = math.atan2(rejoin[1] - cy, rejoin[0] - cx)
    outward = math.atan2(ny, nx)
    sweep = (last - first) % (2.0 * math.pi)
    if (outward - first) % (2.0 * math.pi) > sweep:
        sweep -= 2.0 * math.pi  # the other way round, through the outside
    steps = 12
    return tuple(
        (
            cx + radius * math.cos(first + sweep * index / steps),
            cy + radius * math.sin(first + sweep * index / steps),
        )
        for index in range(steps + 1)
    )


def _jazz() -> tuple[tuple[float, float], ...]:
    """Return the Jazz Bass route: a bar with two round recesses in each
    long side, ``_JAZZ_SIDE_RECESS`` either side of its middle."""
    half_x, half_y = _JAZZ_WIDTH / 2.0, _JAZZ_LENGTH / 2.0
    a, b = (-half_x, -half_y), (half_x, -half_y)
    c, d = (half_x, half_y), (-half_x, half_y)
    inset, along = half_x - _JAZZ_SIDE_INSET, _JAZZ_SIDE_RECESS
    radius = _JAZZ_SIDE_RADIUS
    return (
        a,
        b,
        *_bump(b, c, (inset, -along), radius),
        *_bump(b, c, (inset, along), radius),
        c,
        d,
        *_bump(d, a, (-inset, along), radius),
        *_bump(d, a, (-inset, -along), radius),
    )


def _precision(bass_sign: float) -> tuple[tuple[float, float], ...]:
    """Return the split-coil route: the bass coil nut-ward, the treble one
    tail-ward, overlapping across the centreline, each with a round ear at
    both ends (see ``_precision_ears``)."""
    shift, width = _P_COIL_SHIFT, _P_COIL_WIDTH
    reach = _P_COIL_OFFSET + _P_COIL_LENGTH / 2.0
    inner = _P_COIL_LENGTH / 2.0 - _P_COIL_OFFSET
    outer_bass, inner_bass, inner_treble, outer_treble = _precision_ears()
    # Each coil's two long sides across the neck (they meet at X = 0 when
    # the coils just touch along the centreline).
    bass_out, bass_in = -shift - width / 2.0, -shift + width / 2.0
    treble_in, treble_out = shift - width / 2.0, shift + width / 2.0
    ear = _P_EAR_RADIUS
    corners = [
        (bass_out, -reach),
        *_bump((bass_out, -reach), (bass_in, -reach), outer_bass, ear),
        (bass_in, -reach),
        (bass_in, -inner),
        *_bump((treble_in, -inner), (treble_out, -inner), inner_treble, ear),
        (treble_out, -inner),
        (treble_out, reach),
        *_bump((treble_out, reach), (treble_in, reach), outer_treble, ear),
        (treble_in, reach),
        (treble_in, inner),
        *_bump((bass_in, inner), (bass_out, inner), inner_bass, ear),
        (bass_out, inner),
    ]
    # Bass (low strings) coil lies on the bass side of the centreline.
    return tuple((x, -bass_sign * y) for x, y in corners)


def _precision_ears() -> tuple[tuple[float, float], ...]:
    """Return the four ears' screws, local Y with the bass side negative.

    In order: the bass coil's outer and inner ends, the treble coil's
    inner and outer ends; each ``_P_EAR_INSET`` inside its coil's end.
    """
    reach = _P_COIL_OFFSET + _P_COIL_LENGTH / 2.0 - _P_EAR_INSET
    inner = _P_COIL_LENGTH / 2.0 - _P_COIL_OFFSET - _P_EAR_INSET
    return (
        (-_P_COIL_SHIFT, -reach),
        (-_P_COIL_SHIFT, inner),
        (_P_COIL_SHIFT, -inner),
        (_P_COIL_SHIFT, reach),
    )


def _local_outline(
    kind: PickupType, bass_sign: float
) -> tuple[tuple[float, float], ...]:
    """Return the route outline centred on the origin, unrotated."""
    if kind == "humbucker":
        return OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS
    if kind == "single_coil":
        return _bar(_SINGLE_LENGTH, _SINGLE_WIDTH, _SINGLE_WIDTH / 2.0 - 0.01)
    if kind == "jazz_bass":
        return _jazz()
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
    kind: PickupType,
    angle_degrees: float = 0.0,
    bass_sign: float = -1.0,
    string_count: int = 6,
) -> float:
    """Return how far the route reaches along the neck from its centre."""
    if kind == "none":
        return 0.0
    local = _stretched(
        _local_outline(kind, bass_sign), pickup_stretch(kind, string_count)
    )
    return max(abs(x) for x, _ in _rotated(local, angle_degrees, bass_sign))


def pickup_route(
    kind: PickupType,
    name: str,
    center_x: float,
    depth: float,
    bass_sign: float,
    angle_degrees: float = 0.0,
    string_count: int = 6,
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
        string_count: The instrument's strings; a guitar pickup for more
            than six is stretched (see ``pickup_stretch``).
    """
    if kind == "none":
        return None
    local = _rotated(
        _stretched(_local_outline(kind, bass_sign), pickup_stretch(kind, string_count)),
        angle_degrees,
        bass_sign,
    )
    return TracedCavity(name, tuple(Point2D(center_x + x, y) for x, y in local), depth)


def pickup_screws(
    kind: PickupType,
    center_x: float,
    bass_sign: float,
    humbucker_screw_spacing: float,
    angle_degrees: float = 0.0,
    string_count: int = 6,
) -> tuple[tuple[str, float, float], ...]:
    """Return ``(label, x, y)`` for each height-screw recess of a pickup.

    ``label`` is ``bass`` / ``treble`` (with a coil prefix for a split
    pickup); the humbucker's spacing is ``humbucker_screw_spacing``. The
    screws turn with the route by ``angle_degrees`` and spread with its
    stretch for more than six strings.
    """
    stretch = pickup_stretch(kind, string_count)

    def pair(spacing: float) -> list[tuple[str, float, float]]:
        spacing += stretch
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
        # One in each of the four side recesses, outside the pickup's own
        # sides (its ears are there); local Y has the bass side negative.
        across = _JAZZ_SCREW_ACROSS
        local = [
            (f"{end} {edge}", x, -bass_sign * y)
            for end, y in (("bass", -_JAZZ_SIDE_RECESS), ("treble", _JAZZ_SIDE_RECESS))
            for edge, x in (("front", -across), ("back", across))
        ]
    elif kind == "bass_soapbar":
        local = pair(2.0 * _SOAPBAR_SCREW)
    else:
        # Each coil is screwed through the ears at both of its ends; local
        # Y has the bass side negative, as in _precision.
        labels = (
            "bass coil bass",
            "bass coil treble",
            "treble coil bass",
            "treble coil treble",
        )
        local = [
            (label, x, -bass_sign * y)
            for label, (x, y) in zip(labels, _precision_ears(), strict=True)
        ]
    turned = _rotated(tuple((x, y) for _, x, y in local), angle_degrees, bass_sign)
    return tuple(
        (label, center_x + x, y)
        for (label, _, _), (x, y) in zip(local, turned, strict=True)
    )

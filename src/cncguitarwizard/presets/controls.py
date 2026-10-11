"""Electronics layouts: the cavities, shaft holes and cover plates of each.

A layout is chosen with ``Prototype001Parameters.body_controls``. Every
layout is placed from the body shape's own control area — the mean of its
``pot_offsets`` (the traced almond uses the drawing's own cavity) and its
round switch cavity — so it rides with the shape and the heel end. Rear
cavities close with a plate seated flush in a cover recess; a Telecaster
style control plate sits flush in a recess in the top instead, with the
pots and the blade switch mounted through the plate itself. Every plate
is a ``CoverPlate`` to cut from sheet, and the body gets a shallow spot
for each of its screws. An optional 9 V battery box (``battery_features``)
is one more rear cavity with its own cover, placed by the shape's
``battery_offset``, ``battery_y`` and ``battery_angle_degrees``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal

from ..geometry.body import (
    Cavity,
    CircularCavity,
    CoverPlate,
    DrilledHole,
    RearCavity,
    RectangularCavity,
    TracedCavity,
    cover_screw_points,
)
from ..geometry.exceptions import BodyGeometryError
from ..geometry.primitives import Point2D, point_in_polygon
from .body_shapes import BodyShapeSpec

ControlLayout = Literal[
    "almond_2",
    "gibson_4",
    "rear_3",
    "superstrat",
    "volume_1",
    "active_4",
    "tele",
    "jazz_bass",
    "pickguard",
    "none",
]
"""An electronics layout (see ``CONTROL_LABELS``)."""

CONTROL_LABELS: dict[str, str] = {
    "almond_2": "Design by Jone almond, 2 pots + round switch cavity",
    "gibson_4": "Gibson style, 4 pots + round switch cavity",
    "rear_3": "Rear cavity, 3 pots in a row + round switch cavity",
    "superstrat": "Superstrat rear cavity, 2 pots + 5-way blade switch in it",
    "volume_1": "One volume pot (+ round switch cavity with two or more pickups)",
    "active_4": "Active bass rear cavity, 4 pots in a row",
    "tele": "Telecaster style control plate on the top (2 pots + blade switch)",
    "jazz_bass": "Jazz Bass style control plate on the top (3 pots, jack on it)",
    "pickguard": "Stratocaster style, in the pickguard (3 pots + 5-way blade switch)",
    "none": "No control cavities",
}

GENERATED_REAR_LAYOUTS = frozenset(
    {"gibson_4", "rear_3", "superstrat", "volume_1", "active_4"}
)
"""The layouts whose rear cavity is generated (not drawn): they may move
clear of the top routes."""

SWITCHLESS_LAYOUTS = frozenset(
    {"superstrat", "active_4", "tele", "jazz_bass", "pickguard"}
)
"""The layouts with no round switch cavity of their own: their selector is
in the cavity or on the plate, or (a bass) there is none."""

BLADE_SWITCH_SCREW_SPACING = 41.28
"""A 5-way blade switch's mounting screws apart, in mm (1-5/8 in: Oak
Grigsby / CRL)."""

BLADE_SWITCH_SCREW_HOLE = 3.6
"""The clearance hole for its #6-32 screws, in mm."""

BLADE_SWITCH_SLOT = (27.0, 6.5)
"""The lever's slot through the top (length, width), in mm: its travel
(1-1/16 in), wide enough for the main end mill."""

BLADE_SWITCH_TOP_WALL = 4.0
"""The top left over a rear-mounted blade switch, in mm, so its lever
stands far enough out."""

BLADE_SWITCH_POCKET = (54.0, 16.0)
"""The deeper pocket the switch sits in (length, width), in mm."""

JAZZ_PLATE_SCREW_SPACING = 124.5
"""A Jazz Bass control plate's two mounting screws apart, in mm (4.9 in)."""

JACK_PLATE_HOLE = 9.6
"""The output jack's hole in a control plate, in mm (a 3/8 in bushing)."""

SCREW_SPOT_DIAMETER = 3.0
SCREW_SPOT_DEPTH = 1.0
SCREW_CLEARANCE = 3.2

POT_ROOM = 13.0
"""The radius routed round a drawn pot's shaft, in mm: a 24 mm pot and a
millimetre."""

JACK_ROOM = 12.0
"""The radius routed round a jack mounted in the top, in mm."""

SWITCH_ROOM = 11.0
"""The radius routed round each end of a drawn blade switch, in mm."""

SWITCH_REACH = 20.0
"""How far a drawn blade switch's body runs each way along its slot from
the slot's centre, in mm."""

COVER_MARGIN = 6.0
"""How far a cover routed round drawn pots reaches past their cavity, in
mm."""

TOGGLE_ROOM = 13.0
"""The radius routed round a toggle switch sharing a drawn control
cavity, in mm."""

COVER_SCREW_SPACING = 25.0
"""The closest two screws of a cover routed round drawn pots may be, in
mm: a corner nearer than this to a screw already placed goes without."""

COVER_SCREW_TAB = 5.0
"""The radius of wood left round each screw of a cover routed round drawn
pots, in mm: a small tab reaching into the cavity under the screw, as on a
Gibson's control cavity (2 mm in from a 6 mm ledge)."""

ROOM_PLAY = 1.0
"""How much of a room routed round a drawn part is play, in mm (a 24 mm
pot in ``POT_ROOM``): a cover screw's tab may reach into it."""

REAR_POT_COUNTS = {"gibson_4": 4, "rear_3": 3, "volume_1": 1, "active_4": 4}
"""How many pots each generated rear layout has: a shape's ``rear_pots``
of that many place them."""


@dataclass(frozen=True, slots=True)
class TelePlate:
    """A Telecaster control plate's sizes, along it from its centre.

    Args:
        length: The plate's length, in mm.
        width: Its width.
        cavity_length: The cavity's under it.
        cavity_width: The cavity's width: room for 24 mm pots.
        switch: The blade switch slot's centre.
        pots: The volume and the tone pot.
        screws: The two mounting screws.
    """

    length: float
    width: float
    cavity_length: float
    cavity_width: float
    switch: float
    pots: tuple[float, float]
    screws: tuple[float, float]


TELE_PLATE = TelePlate(155.0, 32.0, 142.0, 25.4, -50.0, (-2.0, 57.0), (-74.5, 74.5))
"""A '52 Telecaster's control plate, measured from a straight-on photo
(Wikimedia Commons, "Fender Telecaster American Vintage 1952
transparent.png", scaled from its frets): about 6 1/8 x 1 1/4 in, the
switch some 1 15/16 in ahead of the volume pot and the tone pot 2 3/8 in
behind it."""


@dataclass(frozen=True, slots=True)
class ControlFeatures:
    """Everything an electronics layout cuts into the body, plus its plates.

    Args:
        control_cavity: The rear control cavity, or ``None``.
        switch_cavity: The rear switch cavity, or ``None``.
        top_cavities: Top-routed electronics: a control plate's recess and
            the deeper cavity inside it.
        holes: Shaft holes drilled from the top into a rear cavity.
        back_marks: Cover-screw spots drilled from the back.
        top_marks: Cover-screw spots drilled from the top.
        covers: The plates to cut from sheet.
        battery_cavity: The rear 9 V battery box, or ``None``.
        through_cavities: Routes from the top through into the rear
            control cavity (a rear-mounted blade switch's slot); cut in
            ``Body_top``.
        plate_jack: Whether the output jack is on the control plate
            (``body_jack`` "plate"), so no bore runs in from the edge.
        control_centre: The control cavity's (or Tele plate's) centre: it
            turns about this point and stretches from it.
        control_axis: Its long axis, a unit vector (turned with it); the
            cavity's width runs square to it.
        guard_holes: Pot holes through the pickguard (the ``pickguard``
            layout's pots are mounted in it).
        guard_slots: Openings through the pickguard (its blade switch).
    """

    control_cavity: RearCavity | None = None
    switch_cavity: RearCavity | None = None
    top_cavities: tuple[Cavity, ...] = ()
    holes: tuple[DrilledHole, ...] = ()
    back_marks: tuple[DrilledHole, ...] = ()
    top_marks: tuple[DrilledHole, ...] = ()
    covers: tuple[CoverPlate, ...] = ()
    battery_cavity: RearCavity | None = None
    through_cavities: tuple[Cavity, ...] = ()
    plate_jack: bool = False
    control_centre: Point2D | None = None
    control_axis: Point2D | None = None
    guard_holes: tuple[DrilledHole, ...] = ()
    guard_slots: tuple[Cavity, ...] = ()

    def with_covers(self, other: ControlFeatures) -> ControlFeatures:
        """Return these features with another's screw spots and covers added."""
        return replace(
            self,
            back_marks=(*self.back_marks, *other.back_marks),
            top_marks=(*self.top_marks, *other.top_marks),
            covers=(*self.covers, *other.covers),
        )

    def with_battery(self, battery: ControlFeatures) -> ControlFeatures:
        """Return these features with a battery box's cavity, spots and cover."""
        return replace(self.with_covers(battery), battery_cavity=battery.battery_cavity)


def rear_cover(
    rear: RearCavity, count: int, at: tuple[Point2D, ...] = ()
) -> ControlFeatures:
    """Return the sheet cover for a rear cavity and its screw spots.

    ``count`` screws are spread round the ledge between the cavity and
    its cover recess (``cover_screw_points``), or go where ``at`` puts
    them (a drawn cover's corners); each gets a clearance hole in the
    plate and a shallow spot 1 mm into the ledge's floor. The plate is the
    recess's outline, as thick as the recess is deep.
    """
    depth = rear.cover_recess.depth
    screws = at or cover_screw_points(
        rear.cavity.outline,
        rear.cover_recess.outline,
        count,
        SCREW_CLEARANCE + 2.0,
    )
    marks = tuple(
        DrilledHole(
            f"{rear.cavity.name} cover screw {index}",
            point.x,
            point.y,
            SCREW_SPOT_DIAMETER,
            depth + SCREW_SPOT_DEPTH,
        )
        for index, point in enumerate(screws, start=1)
    )
    plate = CoverPlate(
        f"{rear.cavity.name} cover",
        "back",
        rear.cover_recess.outline,
        depth,
        holes=tuple(
            DrilledHole(f"Screw {index}", point.x, point.y, SCREW_CLEARANCE, depth)
            for index, point in enumerate(screws, start=1)
        ),
    )
    return ControlFeatures(back_marks=marks, covers=(plate,))


BATTERY_CAVITY_CORNER_RADIUS = 5.0
"""Corner radius of the battery box, in mm (a 9 V battery still fits the
default 56 × 30 mm box with it)."""

BATTERY_PITCH = 28.0
"""How much wider a box for two 9 V batteries is, in mm: one battery's
26.5 mm plus 1.5 mm between them."""


def battery_features(
    shape: BodyShapeSpec,
    heel_end: float,
    *,
    length: float,
    width: float,
    depth: float,
    cover_margin: float,
    cover_depth: float,
    count: int = 1,
) -> ControlFeatures:
    """Return a rear 9 V battery box: its cavity, cover, and screw spots.

    The box is ``length`` along its own axis by ``width`` and ``depth``
    deep from the back, centred ``shape.battery_offset`` behind the heel
    end at ``shape.battery_y`` and turned ``shape.battery_angle_degrees``
    from the neck's axis. A box for two batteries (``count`` 2) holds
    them side by side, ``BATTERY_PITCH`` wider. Its cover recess is
    ``cover_margin`` wider all round; the plate is held by two screws in
    the ledge at the box's ends.

    Raises:
        BodyGeometryError: For a ``count`` other than 1 or 2.
    """
    if count not in (1, 2):
        raise BodyGeometryError(
            f"A battery box holds one or two 9 V batteries, not {count}."
        )
    width += (count - 1) * BATTERY_PITCH
    centre = Point2D(heel_end + shape.battery_offset, shape.battery_y)
    angle = math.radians(shape.battery_angle_degrees)
    cos, sin = math.cos(angle), math.sin(angle)

    def placed(
        name: str, along: float, across: float, radius: float, deep: float
    ) -> TracedCavity:
        box = RectangularCavity(name, 0.0, 0.0, along, across, deep, radius)
        return TracedCavity(
            name,
            tuple(
                Point2D(
                    centre.x + p.x * cos - p.y * sin, centre.y + p.x * sin + p.y * cos
                )
                for p in box.outline
            ),
            deep,
        )

    cavity = placed(
        "Battery cavity", length, width, BATTERY_CAVITY_CORNER_RADIUS, depth
    )
    recess = placed(
        "Battery cavity cover recess",
        length + 2.0 * cover_margin,
        width + 2.0 * cover_margin,
        BATTERY_CAVITY_CORNER_RADIUS + cover_margin,
        cover_depth,
    )
    reach = length / 2.0 + cover_margin / 2.0
    screws = [
        Point2D(centre.x + side * reach * cos, centre.y + side * reach * sin)
        for side in (-1.0, 1.0)
    ]
    marks = tuple(
        DrilledHole(
            f"Battery cavity cover screw {index}",
            point.x,
            point.y,
            SCREW_SPOT_DIAMETER,
            cover_depth + SCREW_SPOT_DEPTH,
        )
        for index, point in enumerate(screws, start=1)
    )
    cover = CoverPlate(
        "Battery cavity cover",
        "back",
        recess.outline,
        cover_depth,
        holes=tuple(
            DrilledHole(f"Screw {index}", p.x, p.y, SCREW_CLEARANCE, cover_depth)
            for index, p in enumerate(screws, start=1)
        ),
    )
    return ControlFeatures(
        back_marks=marks, covers=(cover,), battery_cavity=RearCavity(cavity, recess)
    )


def _turned(
    points: tuple[Point2D, ...], centre: Point2D, degrees: float
) -> tuple[Point2D, ...]:
    """Return ``points`` turned ``degrees`` counter-clockwise about ``centre``."""
    if not degrees:
        return points
    angle = math.radians(degrees)
    cos, sin = math.cos(angle), math.sin(angle)
    return tuple(
        Point2D(
            centre.x + (p.x - centre.x) * cos - (p.y - centre.y) * sin,
            centre.y + (p.x - centre.x) * sin + (p.y - centre.y) * cos,
        )
        for p in points
    )


def _round_hull(
    rooms: list[tuple[Point2D, float]], samples: int = 32
) -> tuple[Point2D, ...]:
    """Return the convex hull round circles (centre, radius), counter-
    clockwise: a cavity routed round its pots."""
    points = sorted(
        {
            (
                round(centre.x + radius * math.cos(2.0 * math.pi * k / samples), 9),
                round(centre.y + radius * math.sin(2.0 * math.pi * k / samples), 9),
            )
            for centre, radius in rooms
            for k in range(samples)
        }
    )

    def cross(
        o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]
    ) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0.0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0.0:
            upper.pop()
        upper.append(point)
    return tuple(Point2D(x, y) for x, y in lower[:-1] + upper[:-1])


def _corner_screws(
    rooms: list[tuple[Point2D, float]], margin: float, steps: int = 360
) -> tuple[Point2D, ...]:
    """Return a screw by each corner of a cover routed round ``rooms``.

    Every circle (centre, radius) the hull runs round is a corner, as on
    a Gibson's cover. Its screw sits halfway across the ``margin`` wide
    ledge between the cavity and its cover, as near the middle of the
    corner's arc as its tab (``COVER_SCREW_TAB`` of wood round it, reaching
    into the cavity) stays clear of every part the rooms hold (each room's
    radius less ``ROOM_PLAY``): just along the side beside a pot. The
    widest corners go first: a corner nearer than ``COVER_SCREW_SPACING``
    to a screw already placed gets none. The screws are numbered
    counter-clockwise round the circles' middle.
    """
    # Which circle the hull runs round in each direction: the one
    # reaching furthest that way.
    arcs: dict[int, list[float]] = {}
    for step in range(steps):
        angle = 2.0 * math.pi * step / steps
        ux, uy = math.cos(angle), math.sin(angle)
        widest = max(
            range(len(rooms)),
            key=lambda i: rooms[i][0].x * ux + rooms[i][0].y * uy + rooms[i][1],
        )
        arcs.setdefault(widest, []).append(angle)
    # Where a screw's tab is clear of the parts, along the ledge's middle.
    ledge = _resampled(_round_hull([(p, r + margin / 2.0) for p, r in rooms]), 1.0)
    clear = [
        point
        for point in ledge
        if all(
            math.hypot(point.x - centre.x, point.y - centre.y)
            >= radius - ROOM_PLAY + COVER_SCREW_TAB
            for centre, radius in rooms
        )
    ]
    if not clear:
        return ()
    corners: list[tuple[int, Point2D]] = []
    for index, angles in arcs.items():
        centre, radius = rooms[index]
        # The arc's middle direction (its angles averaged as unit vectors).
        middle = math.atan2(
            sum(math.sin(a) for a in angles), sum(math.cos(a) for a in angles)
        )
        reach = radius + margin / 2.0
        corner = Point2D(
            centre.x + reach * math.cos(middle), centre.y + reach * math.sin(middle)
        )
        nearest = min(
            clear, key=lambda point: math.hypot(point.x - corner.x, point.y - corner.y)
        )
        corners.append((len(angles), nearest))
    screws: list[Point2D] = []
    for _, point in sorted(corners, key=lambda corner: -corner[0]):
        if all(
            math.hypot(point.x - s.x, point.y - s.y) >= COVER_SCREW_SPACING
            for s in screws
        ):
            screws.append(point)
    mx = sum(centre.x for centre, _ in rooms) / len(rooms)
    my = sum(centre.y for centre, _ in rooms) / len(rooms)
    return tuple(sorted(screws, key=lambda s: math.atan2(s.y - my, s.x - mx)))


def _resampled(outline: tuple[Point2D, ...], step: float) -> tuple[Point2D, ...]:
    """Return a closed ``outline`` with a point at least every ``step`` mm."""
    points: list[Point2D] = []
    for a, b in zip(outline, (*outline[1:], outline[0]), strict=True):
        count = max(1, math.ceil(math.hypot(b.x - a.x, b.y - a.y) / step))
        points += [
            Point2D(a.x + (b.x - a.x) * k / count, a.y + (b.y - a.y) * k / count)
            for k in range(count)
        ]
    return tuple(points)


def _with_tabs(
    outline: tuple[Point2D, ...], screws: tuple[Point2D, ...], samples: int = 12
) -> tuple[Point2D, ...]:
    """Return a cavity's ``outline`` with a tab left at each cover screw.

    The disc of ``COVER_SCREW_TAB`` about each screw (on the ledge outside
    the cavity) is taken out of the cavity where it reaches in: the
    outline runs round it on an arc, the tab a small bump of wood into the
    cavity under the screw, as on a Gibson's control cavity.
    """
    points = outline
    for screw in screws:
        points = _notched(points, screw, COVER_SCREW_TAB, samples)
    return points


def _notched(
    outline: tuple[Point2D, ...], centre: Point2D, radius: float, samples: int
) -> tuple[Point2D, ...]:
    """Return ``outline`` with the disc (``centre``, ``radius``) taken out.

    The outline must enter the disc once and leave it once; otherwise it
    is returned as it is.
    """
    count = len(outline)
    entry: tuple[int, Point2D] | None = None
    exit_: tuple[int, Point2D] | None = None
    for index in range(count):
        a, b = outline[index], outline[(index + 1) % count]
        dx, dy = b.x - a.x, b.y - a.y
        fx, fy = a.x - centre.x, a.y - centre.y
        aa = dx * dx + dy * dy
        bb = 2.0 * (fx * dx + fy * dy)
        cc = fx * fx + fy * fy - radius * radius
        discriminant = bb * bb - 4.0 * aa * cc
        if aa == 0.0 or discriminant <= 0.0:
            continue
        root = math.sqrt(discriminant)
        for t in sorted(((-bb - root) / (2.0 * aa), (-bb + root) / (2.0 * aa))):
            if not 0.0 <= t < 1.0:
                continue
            crossing = (index, Point2D(a.x + t * dx, a.y + t * dy))
            # Heading toward the centre there: entering the disc.
            if (fx + t * dx) * dx + (fy + t * dy) * dy < 0.0:
                if entry is not None:
                    return outline
                entry = crossing
            else:
                if exit_ is not None:
                    return outline
                exit_ = crossing
    if entry is None or exit_ is None:
        return outline
    (entry_edge, entry_point), (exit_edge, exit_point) = entry, exit_
    # From where the outline leaves the disc on round to where it enters.
    kept = [exit_point]
    index = (exit_edge + 1) % count
    while True:
        kept.append(outline[index])
        if index == entry_edge:
            break
        index = (index + 1) % count
    kept.append(entry_point)
    # Then round the disc back, on the side inside the outline.
    start = math.atan2(entry_point.y - centre.y, entry_point.x - centre.x)
    end = math.atan2(exit_point.y - centre.y, exit_point.x - centre.x)
    sweep = (end - start) % (2.0 * math.pi)
    middle = start + sweep / 2.0
    if not point_in_polygon(
        Point2D(
            centre.x + radius * math.cos(middle), centre.y + radius * math.sin(middle)
        ),
        outline,
    ):
        sweep -= 2.0 * math.pi
    kept += [
        Point2D(
            centre.x + radius * math.cos(start + sweep * k / samples),
            centre.y + radius * math.sin(start + sweep * k / samples),
        )
        for k in range(1, samples)
    ]
    return tuple(kept)


def _principal_axis(points: tuple[Point2D, ...]) -> Point2D:
    """Return the long axis of ``points`` (a unit vector, X never negative)."""
    n = len(points)
    mx = sum(p.x for p in points) / n
    my = sum(p.y for p in points) / n
    sxx = sum((p.x - mx) ** 2 for p in points)
    syy = sum((p.y - my) ** 2 for p in points)
    sxy = sum((p.x - mx) * (p.y - my) for p in points)
    angle = 0.5 * math.atan2(2.0 * sxy, sxx - syy)
    ux, uy = math.cos(angle), math.sin(angle)
    return Point2D(ux, uy) if ux >= 0.0 else Point2D(-ux, -uy)


def _stretched(
    points: tuple[Point2D, ...], centre: Point2D, axis: Point2D, amount: float
) -> tuple[Point2D, ...]:
    """Return ``points`` stretched ``amount`` along ``axis`` from ``centre``.

    Each half moves half the amount outward along the axis (inward for a
    negative amount, never past the centre), so the ends keep their shape
    and only the middle grows or shrinks.
    """
    if not amount:
        return points
    stretched = []
    for p in points:
        along = (p.x - centre.x) * axis.x + (p.y - centre.y) * axis.y
        moved = math.copysign(max(abs(along) + amount / 2.0, 0.0), along)
        shift = moved - along if along else 0.0
        stretched.append(Point2D(p.x + axis.x * shift, p.y + axis.y * shift))
    return tuple(stretched)


def _box(
    name: str,
    centre: Point2D,
    length_x: float,
    length_y: float,
    depth: float,
    corner_radius: float,
    degrees: float,
) -> Cavity:
    """Return a rounded rectangle about ``centre``, turned ``degrees``."""
    box = RectangularCavity(
        name, centre.x, centre.y, length_x, length_y, depth, corner_radius=corner_radius
    )
    if not degrees:
        return box
    return TracedCavity(name, _turned(box.outline, centre, degrees), depth)


def control_features(
    layout: ControlLayout,
    shape: BodyShapeSpec,
    heel_end: float,
    *,
    thickness: float,
    top_wall: float,
    cover_depth: float,
    pot_hole_diameter: float,
    switch_hole_diameter: float,
    switch: bool = True,
    plate_jack: bool = False,
    top_jack: Point2D | None = None,
) -> ControlFeatures:
    """Return the cavities, holes and plates of one electronics layout.

    ``switch`` off leaves out the round switch cavity of a ``volume_1``
    layout (a single pickup needs no selector); ``plate_jack`` puts the
    output jack on a ``jazz_bass`` plate. ``top_jack`` mounts the jack in
    the top there, as an SG's or an Explorer's: its hole is drilled
    through into the rear control cavity, which a shape's ``rear_pots``
    route round it too; a cavity laid out otherwise must lie under it.

    Raises:
        BodyGeometryError: When ``thickness`` leaves no room under
            ``top_wall`` for the control cavity, ``shape.control_stretch``
            shortens the control cavity or its cover past its rounded ends,
            ``shape.control_stretch_across`` leaves the cavity narrower
            than ``MIN_CONTROL_CAVITY_WIDTH``, or the jack is asked onto a
            layout with no plate for it, or into the top with no rear
            control cavity under it.
    """
    if plate_jack and layout != "jazz_bass":
        raise BodyGeometryError(
            'Only the Jazz Bass plate (body_controls "jazz_bass") carries the '
            "jack: choose side, cup or strat for body_jack."
        )
    if layout == "none":
        return ControlFeatures()
    depth = thickness - top_wall
    if depth <= 0.0:
        raise BodyGeometryError(
            f"Body thickness ({thickness:g} mm) must exceed the {top_wall:g} mm "
            "wall the control cavity leaves (body_rear_cavity_top_wall)."
        )
    pots = [(heel_end + x, y) for x, y in shape.pot_offsets]
    anchor_x = sum(x for x, _ in pots) / len(pots)
    anchor_y = sum(y for _, y in pots) / len(pots)
    inward = -1.0 if anchor_y > 0.0 else 1.0

    # The whole layout turns about its cavity's centre (the shape's
    # control_angle_degrees); round cavities are left as they are.
    turn = shape.control_angle_degrees
    # The cavity and its cover grow (or shrink) by control_stretch along
    # their long axis, from their centre; whatever sits off the centre
    # along that axis moves out with its end.
    stretch = shape.control_stretch
    # control_stretch_across does the same square to that axis.
    widen = shape.control_stretch_across

    def spread(dx: float) -> float:
        return dx + math.copysign(stretch / 2.0, dx) if dx else 0.0

    def spread_across(dy: float) -> float:
        return dy + math.copysign(widen / 2.0, dy) if dy else 0.0

    if top_jack is not None and layout not in (*REAR_POT_COUNTS, "almond_2"):
        raise BodyGeometryError(
            "A jack in the top (body_jack top) goes through into a rear control "
            f"cavity: the {layout} layout has none (choose almond_2, gibson_4, "
            "rear_3, volume_1 or active_4)."
        )

    if layout == "pickguard":
        return _pickguard_controls(
            Point2D(anchor_x, anchor_y),
            depth,
            pot_hole_diameter,
            turn,
            stretch,
            widen,
            tuple(Point2D(heel_end + x, y) for x, y in shape.pickguard_controls),
            shape.pickguard_switch_degrees,
            tuple(Point2D(heel_end + x, y) for x, y in shape.pickguard_cavity_points),
        )

    if layout == "tele":
        # The long plate sits 10 mm in from the pots' line, toward the
        # centreline, so its ends stay clear of the body edge.
        return _tele(
            Point2D(anchor_x, anchor_y + inward * 10.0),
            depth,
            cover_depth,
            pot_hole_diameter,
            turn,
            stretch,
            widen,
        )

    if layout == "jazz_bass":
        # Along the pots' line, like the bass's own drawn cavity.
        return _jazz_bass(
            Point2D(anchor_x, anchor_y),
            depth,
            cover_depth,
            pot_hole_diameter,
            plate_jack,
            turn,
            stretch,
            widen,
        )

    through: tuple[Cavity, ...] = ()
    steps: tuple[Cavity, ...] = ()
    extra_holes: list[DrilledHole] = []
    screws = 4
    drawn_rear = (
        layout in REAR_POT_COUNTS and len(shape.rear_pots) == REAR_POT_COUNTS[layout]
    )
    switch_at = Point2D(heel_end + shape.switch_cavity_offset, shape.switch_cavity_y)
    wants_switch = layout not in SWITCHLESS_LAYOUTS and (switch or layout != "volume_1")
    # A switch among drawn pots (a Jackson Rhoads') shares their cavity:
    # its own round cavity and cover would run into theirs. An SG's
    # shares it however far it is (switch_in_control_cavity).
    shared_switch = (
        drawn_rear
        and wants_switch
        and (
            shape.switch_in_control_cavity
            or min(
                math.hypot(heel_end + x - switch_at.x, y - switch_at.y)
                for x, y in shape.rear_pots
            )
            < POT_ROOM + shape.switch_cover_diameter / 2.0 + COVER_MARGIN
        )
    )
    # A drawn cover's screws go at its corners (_corner_screws).
    corner_screws: tuple[Point2D, ...] = ()
    if drawn_rear:
        # Where the shape draws them, as on the original: the cavity and
        # its cover routed round the pots (and a jack in the top), turned
        # about their middle.
        drawn_pots = tuple(Point2D(heel_end + x, y) for x, y in shape.rear_pots)
        middle = Point2D(
            sum(p.x for p in drawn_pots) / len(drawn_pots),
            sum(p.y for p in drawn_pots) / len(drawn_pots),
        )
        centre = middle
        turned_pots = _turned(drawn_pots, middle, turn)
        pots = [(p.x, p.y) for p in turned_pots]
        axis = Point2D(1.0, 0.0)
        rooms = [(p, POT_ROOM) for p in turned_pots]
        if top_jack is not None:
            rooms.append((top_jack, JACK_ROOM))
        if shared_switch:
            rooms.append((switch_at, TOGGLE_ROOM))
        screws = {"volume_1": 3, "active_4": 6}.get(layout, 4)
        corner_screws = _corner_screws(rooms, COVER_MARGIN)
        # Too few corners (a lone pot's round cavity): spread them round
        # the ledge instead, with no tabs.
        if len(corner_screws) < 3:
            corner_screws = ()
        cavity: Cavity = TracedCavity(
            "Control cavity", _with_tabs(_round_hull(rooms), corner_screws), depth
        )
        cover: Cavity = TracedCavity(
            "Control cavity cover recess",
            _round_hull([(p, r + COVER_MARGIN) for p, r in rooms]),
            cover_depth,
        )
    elif layout == "almond_2":
        # The drawn almond turns about its own centre; its pots are the
        # shape's own pot_offsets, placed (and turned) by the editor.
        drawn = shape.control_cavity_points(heel_end)
        centre = Point2D(
            sum(p.x for p in drawn) / len(drawn), sum(p.y for p in drawn) / len(drawn)
        )
        axis = _principal_axis(drawn)
        across = Point2D(-axis.y, axis.x)
        drawn_cover = shape.control_cover_points(heel_end)
        if stretch < 0.0:
            _check_shortening("almond control cavity", drawn, centre, axis, stretch)
            _check_shortening("almond cover", drawn_cover, centre, axis, stretch)
        _check_width(_extent(drawn, across) + widen)

        def reshaped(points: tuple[Point2D, ...]) -> tuple[Point2D, ...]:
            longer = _stretched(points, centre, axis, stretch)
            return _turned(_stretched(longer, centre, across, widen), centre, turn)

        cavity = TracedCavity("Control cavity", reshaped(drawn), depth)
        cover = TracedCavity(
            "Control cavity cover recess", reshaped(drawn_cover), cover_depth
        )
    elif layout == "gibson_4":
        centre = Point2D(anchor_x, anchor_y + inward * 6.0)
        pots = [
            (p.x, p.y)
            for p in _turned(
                tuple(
                    Point2D(centre.x + spread(dx), centre.y + spread_across(dy))
                    for dx, dy in (
                        (-21.0, -17.0),
                        (21.0, -17.0),
                        (-21.0, 17.0),
                        (21.0, 17.0),
                    )
                ),
                centre,
                turn,
            )
        ]
        axis = Point2D(1.0, 0.0)
        _check_width(70.0 + widen)
        cavity = _box(
            "Control cavity", centre, 78.0 + stretch, 70.0 + widen, depth, 16.0, turn
        )
        cover = _box(
            "Control cavity cover recess",
            centre,
            90.0 + stretch,
            82.0 + widen,
            cover_depth,
            22.0,
            turn,
        )
    elif layout == "superstrat":
        # A 5-way blade switch ahead of the volume and tone pots, all in
        # one rear cavity: the switch in a deeper pocket leaving
        # BLADE_SWITCH_TOP_WALL, its lever through a slot in the top, its
        # two screws through the top into its tabs.
        centre = Point2D(anchor_x, anchor_y)
        width = 40.0 + widen
        _check_width(width)

        def on_axis(dx: float) -> Point2D:
            (point,) = _turned(
                (Point2D(centre.x + spread(dx), centre.y),), centre, turn
            )
            return point

        pots = [(p.x, p.y) for p in (on_axis(16.0), on_axis(42.0))]
        axis = Point2D(1.0, 0.0)
        cavity = _box(
            "Control cavity", centre, 112.0 + stretch, width, depth, 12.0, turn
        )
        cover = _box(
            "Control cavity cover recess",
            centre,
            124.0 + stretch,
            width + 12.0,
            cover_depth,
            18.0,
            turn,
        )
        switch_at = on_axis(-28.0)
        pocket_length, pocket_width = BLADE_SWITCH_POCKET
        pocket_depth = thickness - BLADE_SWITCH_TOP_WALL
        steps = (
            _box(
                "Control switch pocket",
                switch_at,
                pocket_length,
                pocket_width,
                pocket_depth,
                3.0,
                turn,
            ),
        )
        slot_length, slot_width = BLADE_SWITCH_SLOT
        through = (
            _box(
                "Control switch slot",
                switch_at,
                slot_length,
                slot_width,
                thickness - pocket_depth + 1.0,
                slot_width / 2.0 - 0.01,
                turn,
            ),
        )
        half = BLADE_SWITCH_SCREW_SPACING / 2.0
        extra_holes = [
            DrilledHole(
                f"Control switch screw {index}",
                point.x,
                point.y,
                BLADE_SWITCH_SCREW_HOLE,
                thickness,
            )
            for index, point in enumerate(
                _turned(
                    (
                        Point2D(switch_at.x - half, switch_at.y),
                        Point2D(switch_at.x + half, switch_at.y),
                    ),
                    switch_at,
                    turn,
                ),
                start=1,
            )
        ]
    elif layout in ("volume_1", "active_4", "rear_3"):
        # Round-ended cavities with their pots in a row along them: one
        # volume pot; four for an active bass (volume, blend, bass,
        # treble), in a wider cavity with room for the preamp; three.
        offsets, length, base_width, screws = {
            "volume_1": ((0.0,), 56.0, 34.0, 3),
            "active_4": ((-42.0, -14.0, 14.0, 42.0), 130.0, 44.0, 6),
            "rear_3": ((-30.0, 0.0, 30.0), 94.0, 34.0, 4),
        }[layout]
        centre = Point2D(anchor_x, anchor_y)
        pots = [
            (p.x, p.y)
            for p in _turned(
                tuple(Point2D(anchor_x + spread(dx), anchor_y) for dx in offsets),
                centre,
                turn,
            )
        ]
        axis = Point2D(1.0, 0.0)
        # Round-ended: the ends stay half circles at any width.
        width = base_width + widen
        _check_width(width)
        cavity = _box(
            "Control cavity",
            centre,
            length + stretch,
            width,
            depth,
            width / 2.0 - 0.1,
            turn,
        )
        cover = _box(
            "Control cavity cover recess",
            centre,
            length + 12.0 + stretch,
            width + 12.0,
            cover_depth,
            width / 2.0 + 5.9,
            turn,
        )
    else:
        raise BodyGeometryError(f"Unknown control layout {layout!r}.")
    control = RearCavity(cavity, cover, steps)
    switch_cavity: RearCavity | None = None
    holes: list[DrilledHole] = []
    if shared_switch:
        holes.append(
            DrilledHole(
                "Switch shaft hole",
                switch_at.x,
                switch_at.y,
                switch_hole_diameter,
                thickness,
            )
        )
    elif wants_switch:
        switch_x = heel_end + shape.switch_cavity_offset
        switch_cavity = RearCavity(
            CircularCavity(
                "Switch cavity",
                switch_x,
                shape.switch_cavity_y,
                shape.switch_cavity_diameter,
                depth,
            ),
            CircularCavity(
                "Switch cavity cover recess",
                heel_end + shape.switch_cover_offset,
                shape.switch_cover_y,
                shape.switch_cover_diameter,
                cover_depth,
            ),
        )
        holes.append(
            DrilledHole(
                "Switch shaft hole",
                switch_x,
                shape.switch_cavity_y,
                switch_hole_diameter,
                thickness,
            )
        )
    # Generated layouts drag as one piece in the body editor, so their
    # pots are named after the cavity; the almond keeps its own pots.
    prefix = "Pot" if layout == "almond_2" else "Control pot"
    holes += [
        DrilledHole(f"{prefix} {index} shaft hole", x, y, pot_hole_diameter, thickness)
        for index, (x, y) in enumerate(pots, start=1)
    ]
    holes += extra_holes
    if top_jack is not None:
        if not point_in_polygon(top_jack, control.cavity.outline):
            raise BodyGeometryError(
                "A jack in the top (body_jack top) goes through into the control "
                "cavity, but the cavity is not under it: move the jack (the "
                "shape's jack_offset / jack_y) over it, or draw the pots round it "
                "(rear_pots)."
            )
        holes.append(
            DrilledHole("Jack hole", top_jack.x, top_jack.y, JACK_PLATE_HOLE, thickness)
        )
    marks: list[DrilledHole] = []
    covers: list[CoverPlate] = []
    for rear, count, at in (
        (control, screws, corner_screws),
        (switch_cavity, 3, ()),
    ):
        if rear is None:
            continue
        plate = rear_cover(rear, count, at)
        marks += plate.back_marks
        covers += plate.covers
    return ControlFeatures(
        control_cavity=control,
        switch_cavity=switch_cavity,
        holes=tuple(holes),
        back_marks=tuple(marks),
        covers=tuple(covers),
        through_cavities=through,
        control_centre=centre,
        control_axis=_turned((axis,), Point2D(0.0, 0.0), turn)[0],
    )


MIN_CONTROL_CAVITY_WIDTH = 16.0
"""The narrowest a control cavity may be made, in mm: a mini pot's body."""


def _extent(points: tuple[Point2D, ...], direction: Point2D) -> float:
    """Return how far ``points`` reach along ``direction``, end to end."""
    along = [p.x * direction.x + p.y * direction.y for p in points]
    return max(along) - min(along)


def _check_width(width: float) -> None:
    """Refuse a control cavity narrower than ``MIN_CONTROL_CAVITY_WIDTH``."""
    if width < MIN_CONTROL_CAVITY_WIDTH:
        raise BodyGeometryError(
            f"control_stretch_across leaves the control cavity {width:.1f} mm "
            f"wide; it needs at least {MIN_CONTROL_CAVITY_WIDTH:g} mm for a pot."
        )


def _check_shortening(
    name: str,
    points: tuple[Point2D, ...],
    centre: Point2D,
    axis: Point2D,
    stretch: float,
) -> None:
    """Refuse shortening a drawn outline by half its length or more.

    Past that its rounded ends would fold onto the centre.
    """
    half_length = max(
        abs((p.x - centre.x) * axis.x + (p.y - centre.y) * axis.y) for p in points
    )
    if -stretch >= half_length:
        raise BodyGeometryError(
            f"control_stretch {stretch:g} mm shortens the {name} too much: "
            f"less than {half_length:.1f} mm shorter, please."
        )


def _pickguard_controls(
    centre: Point2D,
    depth: float,
    pot_hole_diameter: float,
    turn: float = 0.0,
    stretch: float = 0.0,
    widen: float = 0.0,
    drawn: tuple[Point2D, ...] = (),
    switch_degrees: float = 0.0,
    drawn_cavity: tuple[Point2D, ...] = (),
) -> ControlFeatures:
    """Stratocaster style controls, mounted in the pickguard.

    Three pots 30 mm apart in a row along the neck through ``centre`` and
    a 5-way blade switch's 5 x 22 mm slot 60 mm ahead of the middle one
    go through the guard; under them a 127 x 50 mm cavity is routed from
    the top. ``stretch`` / ``widen`` make the cavity longer / wider, the
    end pots and the switch moving out with its ends; all of it turns
    ``turn`` degrees about the cavity's centre.

    ``drawn`` (the switch's slot centre, then the three pots) places them
    as on the original instead, the slot along ``switch_degrees``, the
    cavity ``drawn_cavity`` or else routed round the pots and the
    switch's body, all of it turned ``turn`` about the pots' middle;
    ``centre``, ``stretch`` and ``widen`` do not apply.
    """
    if drawn:
        drawn_pots = drawn[1:]
        middle = Point2D(
            sum(p.x for p in drawn_pots) / len(drawn_pots),
            sum(p.y for p in drawn_pots) / len(drawn_pots),
        )
        switch_at, *pots = _turned(drawn, middle, turn)
        outline = _turned(drawn_cavity, middle, turn)
        slot_turn = switch_degrees + turn
        along = Point2D(
            math.cos(math.radians(slot_turn)), math.sin(math.radians(slot_turn))
        )
        ends = [
            Point2D(switch_at.x + s * along.x, switch_at.y + s * along.y)
            for s in (-SWITCH_REACH, SWITCH_REACH)
        ]
        cavity: Cavity = TracedCavity(
            "Control cavity",
            outline
            or _round_hull(
                [(p, POT_ROOM) for p in pots] + [(p, SWITCH_ROOM) for p in ends]
            ),
            depth,
        )
        switch = _box("Control switch slot", switch_at, 22.0, 5.0, 1.0, 2.49, slot_turn)
        control_middle = middle
    else:

        def spread(dx: float) -> float:
            return dx + math.copysign(stretch / 2.0, dx) if dx else 0.0

        # The cavity's middle sits between the switch and the last pot.
        control_middle = Point2D(centre.x - 17.5, centre.y)

        def at(dx: float) -> Point2D:
            (point,) = _turned(
                (Point2D(control_middle.x + spread(dx), control_middle.y),),
                control_middle,
                turn,
            )
            return point

        cavity = _box(
            "Control cavity",
            control_middle,
            127.0 + stretch,
            50.0 + widen,
            depth,
            12.0,
            turn,
        )
        pots = [at(dx + 17.5) for dx in (-30.0, 0.0, 30.0)]
        switch = _box(
            "Control switch slot", at(-60.0 + 17.5), 22.0, 5.0, 1.0, 2.49, turn
        )
    holes = tuple(
        DrilledHole(
            f"Control pot {index} shaft hole", p.x, p.y, pot_hole_diameter, depth
        )
        for index, p in enumerate(pots, start=1)
    )
    return ControlFeatures(
        top_cavities=(cavity,),
        guard_holes=holes,
        guard_slots=(switch,),
        control_centre=control_middle,
        control_axis=_turned((Point2D(1.0, 0.0),), Point2D(0.0, 0.0), turn)[0],
    )


def _tele(
    centre: Point2D,
    depth: float,
    cover_depth: float,
    pot_hole_diameter: float,
    turn: float = 0.0,
    stretch: float = 0.0,
    widen: float = 0.0,
) -> ControlFeatures:
    """A Telecaster-style plate: flush in the top, parallel to the neck.

    As on a '52 Telecaster (``TELE_PLATE``): the 155 × 32 mm round-ended
    plate carries the blade switch's slot at its front, the volume pot
    about its middle and the tone pot behind; the 142 × 25.4 mm cavity
    under it takes 24 mm pots; two screws hold it near its ends.
    ``stretch`` makes the plate and cavity that much longer, moving the
    screws, the slot and the pots off the middle out with the ends, and
    ``widen`` that much wider, their ends staying half circles. All of it
    turns ``turn`` degrees about the plate's centre.
    """

    def at(dx: float) -> Point2D:
        if dx:
            dx += math.copysign(stretch / 2.0, dx)
        (point,) = _turned((Point2D(centre.x + dx, centre.y),), centre, turn)
        return point

    width = TELE_PLATE.cavity_width + widen
    _check_width(width)
    plate_width = width + TELE_PLATE.width - TELE_PLATE.cavity_width
    recess = _box(
        "Control plate recess",
        centre,
        TELE_PLATE.length + stretch,
        plate_width,
        cover_depth,
        plate_width / 2.0 - 0.01,
        turn,
    )
    cavity = _box(
        "Control cavity",
        centre,
        TELE_PLATE.cavity_length + stretch,
        width,
        depth,
        width / 2.0 - 0.01,
        turn,
    )
    screws = [at(dx) for dx in TELE_PLATE.screws]
    pots = [at(dx) for dx in TELE_PLATE.pots]
    plate = CoverPlate(
        "Control plate",
        "top",
        recess.outline,
        cover_depth,
        holes=(
            *(
                DrilledHole(
                    f"Pot {index} shaft hole", p.x, p.y, pot_hole_diameter, cover_depth
                )
                for index, p in enumerate(pots, start=1)
            ),
            *(
                DrilledHole(f"Screw {index}", p.x, p.y, SCREW_CLEARANCE, cover_depth)
                for index, p in enumerate(screws, start=1)
            ),
        ),
        slots=(
            _box(
                "Blade switch slot",
                at(TELE_PLATE.switch),
                20.0,
                7.0,
                cover_depth,
                3.49,
                turn,
            ),
        ),
    )
    marks = tuple(
        DrilledHole(
            f"Control plate screw {index}",
            p.x,
            p.y,
            SCREW_SPOT_DIAMETER,
            cover_depth + SCREW_SPOT_DEPTH,
        )
        for index, p in enumerate(screws, start=1)
    )
    return ControlFeatures(
        top_cavities=(recess, cavity),
        top_marks=marks,
        covers=(plate,),
        control_centre=centre,
        control_axis=_turned((Point2D(1.0, 0.0),), Point2D(0.0, 0.0), turn)[0],
    )


def _jazz_bass(
    centre: Point2D,
    depth: float,
    cover_depth: float,
    pot_hole_diameter: float,
    jack: bool,
    turn: float = 0.0,
    stretch: float = 0.0,
    widen: float = 0.0,
) -> ControlFeatures:
    """A Jazz Bass style control plate, flush in the top along the pots.

    The 150 × 36 mm round-ended plate (a real one is as long, gently
    curved) carries three pots 32 mm apart — volume, volume, tone — and,
    with ``jack``, the output jack behind them; two screws
    ``JAZZ_PLATE_SCREW_SPACING`` apart hold it. The cavity under it is
    112 × 26 mm. ``stretch`` makes the plate and cavity that much longer,
    moving the screws and the outer holes out with the ends, and
    ``widen`` that much wider. All of it turns ``turn`` degrees about the
    plate's centre.
    """

    def at(dx: float) -> Point2D:
        if dx:
            dx += math.copysign(stretch / 2.0, dx)
        (point,) = _turned((Point2D(centre.x + dx, centre.y),), centre, turn)
        return point

    width = 26.0 + widen
    _check_width(width)
    recess = _box(
        "Control plate recess",
        centre,
        150.0 + stretch,
        width + 10.0,
        cover_depth,
        width / 2.0 + 4.99,
        turn,
    )
    cavity = _box(
        "Control cavity",
        centre,
        112.0 + stretch,
        width,
        depth,
        width / 2.0 - 0.01,
        turn,
    )
    half = JAZZ_PLATE_SCREW_SPACING / 2.0
    screws = [at(-half), at(half)]
    pots = [at(-42.0), at(-10.0), at(22.0)]
    jack_at = at(48.0)
    jack_holes = (
        (DrilledHole("Jack hole", jack_at.x, jack_at.y, JACK_PLATE_HOLE, cover_depth),)
        if jack
        else ()
    )
    plate = CoverPlate(
        "Control plate",
        "top",
        recess.outline,
        cover_depth,
        holes=(
            *(
                DrilledHole(
                    f"Pot {index} shaft hole", p.x, p.y, pot_hole_diameter, cover_depth
                )
                for index, p in enumerate(pots, start=1)
            ),
            *jack_holes,
            *(
                DrilledHole(f"Screw {index}", p.x, p.y, SCREW_CLEARANCE, cover_depth)
                for index, p in enumerate(screws, start=1)
            ),
        ),
    )
    marks = tuple(
        DrilledHole(
            f"Control plate screw {index}",
            p.x,
            p.y,
            SCREW_SPOT_DIAMETER,
            cover_depth + SCREW_SPOT_DEPTH,
        )
        for index, p in enumerate(screws, start=1)
    )
    return ControlFeatures(
        top_cavities=(recess, cavity),
        top_marks=marks,
        covers=(plate,),
        plate_jack=jack,
        control_centre=centre,
        control_axis=_turned((Point2D(1.0, 0.0),), Point2D(0.0, 0.0), turn)[0],
    )

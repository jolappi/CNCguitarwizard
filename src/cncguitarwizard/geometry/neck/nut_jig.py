"""A jig for filing the nut's string slots: a comb against the nut.

The jig is a plate cut from sheet, as thick as it is long along the
neck. It stands on the fretboard with one face flat against the nut's
front face; seen from the bridge, its underside follows the fretboard's
radius between the board's edges, and a leg at each end reaches down
past an edge and hugs it, so the jig sits on the neck's centre. Its top
runs round the radius ``height`` above the board.

From the top a slot comes down at every string's place on the nut, as
wide as that string plus a little play, so the file for it slides
through without wandering sideways and starts the nut's slot exactly
where the string goes. The slots stop at ``floor`` above the board (the
frets' height): a nut slot is never filed lower than the frets' tops,
and the file, sloping up from the nut toward the bridge, is higher
still where it passes through the jig. Its slope down toward the
headstock, and its turn toward each tuner post once the slot is
started, are the filer's.

Every point here is in the jig's own frame, seen from the bridge: X
along the nut's face from the neck's centerline, the bass side positive
(on a left-handed neck too), Y up from the fretboard's crown.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ..exceptions import NeckGeometryError
from ..primitives import Point2D

NUT_JIG_LEG_WIDTH = 4.0
"""Each leg's width outside the fretboard's edge, in mm."""

NUT_JIG_LEG_DEPTH = 3.0
"""How far each leg reaches down past the fretboard's edge, in mm."""

NUT_JIG_EDGE_CLEARANCE = 0.05
"""The gap between each leg and the fretboard's edge, in mm."""

NUT_JIG_CORNER_RELIEF = 1.5
"""The square cut away where each leg meets the underside, in mm, so the
board's edge sits in it rather than on the round a cutter leaves there."""

NUT_JIG_MIN_FLOOR = 0.5
"""The least wood left under the slots, in mm above the board."""

NUT_JIG_MIN_SLOT_DEPTH = 1.0
"""The shallowest a slot may be, in mm, to guide a file at all."""

NUT_JIG_EDGE_ROOM = 0.5
"""The least wood between the outermost slots and the board's edges, mm."""

INCH = 25.4

GUITAR_GAUGES = (0.074, 0.059, 0.046, 0.036, 0.026, 0.017, 0.013, 0.010)
"""A usual eight-string guitar set, bass first, in inches (.010-.074); a
six- or seven-string takes its trebles (.010-.046, .010-.059)."""

BASS_GAUGES = (0.130, 0.105, 0.085, 0.065, 0.045, 0.032)
"""A usual six-string bass set, B to C, in inches (.032-.130); a five
takes B to G (.045-.130), a four E to G (.045-.105)."""

BASS_SCALE = 740.0
"""Scales from this long (mm) take bass strings by default."""

ARC_STEP = 1.0
"""The longest straight step along the jig's round underside and top."""


def default_gauges(string_count: int, scale_length: float) -> tuple[float, ...]:
    """Return a usual string set for the strings, bass first, in inches.

    Raises:
        NeckGeometryError: For a string count no usual set is listed for.
    """
    if scale_length >= BASS_SCALE:
        sets = {4: BASS_GAUGES[1:5], 5: BASS_GAUGES[:5], 6: BASS_GAUGES}
    else:
        sets = {count: GUITAR_GAUGES[-count:] for count in (6, 7, 8)}
    if string_count not in sets:
        raise NeckGeometryError(
            f"No usual string set is listed for {string_count} strings: give "
            "nut_jig_gauges, one per string."
        )
    return sets[string_count]


def resolved_gauges(given: Sequence[float], string_count: int) -> tuple[float, ...]:
    """Return given gauges bass first, in inches.

    They may come in any order, in inches (0.010) or thousandths (10):
    the thickest goes to the bass-most string.

    Raises:
        NeckGeometryError: Unless there is one positive gauge per string,
            each thinner than a quarter inch.
    """
    if len(given) != string_count:
        raise NeckGeometryError(
            f"nut_jig_gauges lists {len(given)} gauges for {string_count} "
            "strings: give one per string."
        )
    gauges = []
    for gauge in given:
        value = float(gauge)
        if not math.isfinite(value) or value <= 0.0:
            raise NeckGeometryError("Each of nut_jig_gauges must be positive.")
        if value >= 1.0:
            value /= 1000.0
        if value >= 0.25:
            raise NeckGeometryError(
                f"A {value:g} in string is too thick for a nut: give "
                "nut_jig_gauges in inches (0.010) or thousandths (10)."
            )
        gauges.append(value)
    return tuple(sorted(gauges, reverse=True))


@dataclass(frozen=True, slots=True)
class NutJigSlot:
    """One string's guide slot in the jig.

    Args:
        string: The string, 1 the bass-most.
        gauge: The string's gauge, in inches.
        centre: The slot's centre along the nut's face (X).
        width: The slot's width: the string's and the play.
        floor: Y of the slot's bottom.
        top: Y of the jig's top over the slot (its highest side).
    """

    string: int
    gauge: float
    centre: float
    width: float
    floor: float
    top: float

    def outline(self) -> tuple[Point2D, ...]:
        """Return the slot as a rectangle from its floor up to the top."""
        half = self.width / 2.0
        return (
            Point2D(self.centre - half, self.floor),
            Point2D(self.centre + half, self.floor),
            Point2D(self.centre + half, self.top),
            Point2D(self.centre - half, self.top),
        )


@dataclass(frozen=True, slots=True)
class NutSlotJig:
    """The nut-slot filing jig, seen from the bridge (see the module).

    Args:
        thickness: The sheet's thickness: the jig's length along the neck.
        body: The plate without its slots, counter-clockwise.
        slots: The strings' slots, bass first.
        edges: X of the fretboard's treble and bass edges at the jig.
        radius: The fretboard's radius its underside follows.
        height: The top's height above the board.
        lean: The nut face's lean: X along the neck gained per mm toward
            the bass side.
        bass_sign: ``+1`` when the bass side is at the model's +Y.
        crown: The fretboard crown's height above the board's glue face.
    """

    thickness: float
    body: tuple[Point2D, ...]
    slots: tuple[NutJigSlot, ...]
    edges: tuple[float, float]
    radius: float
    height: float
    lean: float = 0.0
    bass_sign: float = 1.0
    crown: float = 0.0

    def placed(self, point: Point2D) -> tuple[float, float, float]:
        """Return a point of the jig's nut-side face where it stands on the
        neck: X along the neck from the nut line, Y across, Z up from the
        fretboard's glue face."""
        k = math.hypot(1.0, self.lean)
        return (
            point.x * self.lean / k,
            point.x * self.bass_sign / k,
            self.crown + point.y,
        )

    @property
    def toward_bridge(self) -> tuple[float, float]:
        """Return the jig's thickness direction in plan: square to the
        nut's face, toward the bridge."""
        k = math.hypot(1.0, self.lean)
        return (1.0 / k, 0.0 - self.lean * self.bass_sign / k)

    @property
    def outline(self) -> tuple[Point2D, ...]:
        """Return the plate with its slots cut down from the top."""
        points: list[Point2D] = []
        slots = list(self.slots)
        # The top runs from the bass end's top corner back to the treble
        # end: each slot's notch goes in where the top crosses it.
        start = max(
            range(len(self.body)), key=lambda i: (self.body[i].x, self.body[i].y)
        )
        for index, point in enumerate(self.body):
            top = index >= start
            while top and slots and point.x <= slots[0].centre + slots[0].width / 2.0:
                slot = slots.pop(0)
                half = slot.width / 2.0
                points += [
                    Point2D(slot.centre + half, self._top(slot.centre + half)),
                    Point2D(slot.centre + half, slot.floor),
                    Point2D(slot.centre - half, slot.floor),
                    Point2D(slot.centre - half, self._top(slot.centre - half)),
                ]
            if not (top and self._in_slot(point.x)):
                points.append(point)
        return tuple(points)

    def _top(self, x: float) -> float:
        return self.height + board_surface(self.radius, x)

    def _in_slot(self, x: float) -> bool:
        return any(
            abs(x - slot.centre) <= slot.width / 2.0 + 1e-9 for slot in self.slots
        )


def board_surface(radius: float, x: float) -> float:
    """Return the fretboard's height at ``x`` off the crown (0 there)."""
    return math.sqrt(max(0.0, radius * radius - x * x)) - radius


def nut_slot_jig(
    *,
    radius: float,
    edges: tuple[float, float],
    strings: Sequence[float],
    gauges: Sequence[float],
    play: float,
    thickness: float,
    height: float,
    floor: float,
    lean: float = 0.0,
    bass_sign: float = 1.0,
    crown: float = 0.0,
) -> NutSlotJig:
    """Lay out the jig.

    Args:
        radius: The fretboard's radius.
        edges: X of the board's treble (negative) and bass edges along
            the nut's face, where the legs go.
        strings: Each string's X on the nut's face, bass first.
        gauges: Each string's gauge in inches, bass first.
        play: How much wider than its string each slot is.
        thickness: The sheet's thickness (the jig's length along the neck).
        height: The top's height above the board.
        floor: The slots' bottoms' height above the board (the frets').
        lean: The nut face's lean, ``bass_sign`` and the crown's height,
            which place the jig on the neck (see ``NutSlotJig``).

    Raises:
        NeckGeometryError: For sizes the jig cannot be made with, or a
            slot reaching the board's edge.
    """
    for name, value in (
        ("nut_jig_thickness", thickness),
        ("nut_jig_height", height),
        ("fretboard_radius", radius),
    ):
        if not math.isfinite(value) or value <= 0.0:
            raise NeckGeometryError(f"{name} must be finite and positive.")
    if not math.isfinite(play) or not 0.0 <= play <= 1.0:
        raise NeckGeometryError("nut_jig_slot_play must lie between 0 and 1 mm.")
    floor = max(floor, NUT_JIG_MIN_FLOOR)
    if height - floor < NUT_JIG_MIN_SLOT_DEPTH:
        raise NeckGeometryError(
            f"nut_jig_height must be at least {floor + NUT_JIG_MIN_SLOT_DEPTH:g} "
            f"mm: the slots stop {floor:g} mm above the board (the frets' "
            f"height) and need {NUT_JIG_MIN_SLOT_DEPTH:g} mm to guide the file."
        )
    treble, bass = edges
    slots = []
    for number, (centre, gauge) in enumerate(zip(strings, gauges, strict=True), 1):
        width = gauge * INCH + play
        if not (
            treble + NUT_JIG_EDGE_ROOM < centre - width / 2.0
            and centre + width / 2.0 < bass - NUT_JIG_EDGE_ROOM
        ):
            raise NeckGeometryError(
                f"String {number}'s slot in the nut-slot jig reaches the "
                "fretboard's edge: widen nut_width or narrow nut_string_spacing."
            )
        sides = (
            board_surface(radius, centre - width / 2.0),
            board_surface(radius, centre + width / 2.0),
        )
        slots.append(
            NutJigSlot(
                number,
                gauge,
                centre,
                width,
                board_surface(radius, centre) + floor,
                height + max(sides),
            )
        )
    inner_treble = treble - NUT_JIG_EDGE_CLEARANCE
    inner_bass = bass + NUT_JIG_EDGE_CLEARANCE
    outer_treble = inner_treble - NUT_JIG_LEG_WIDTH
    outer_bass = inner_bass + NUT_JIG_LEG_WIDTH
    treble_edge = board_surface(radius, treble)
    bass_edge = board_surface(radius, bass)
    relief = NUT_JIG_CORNER_RELIEF
    body = [
        Point2D(outer_treble, treble_edge - NUT_JIG_LEG_DEPTH),
        Point2D(inner_treble, treble_edge - NUT_JIG_LEG_DEPTH),
        # The treble leg's inner face, up past the board's edge into the
        # corner relief, then the underside along the radius.
        Point2D(inner_treble, treble_edge + relief),
        Point2D(treble + relief, treble_edge + relief),
        *(
            Point2D(x, board_surface(radius, x))
            for x in _steps(treble + relief, bass - relief)
        ),
        Point2D(bass - relief, bass_edge + relief),
        Point2D(inner_bass, bass_edge + relief),
        Point2D(inner_bass, bass_edge - NUT_JIG_LEG_DEPTH),
        Point2D(outer_bass, bass_edge - NUT_JIG_LEG_DEPTH),
        # Up the bass end and back along the top to the treble end.
        *(
            Point2D(x, height + board_surface(radius, x))
            for x in _steps(outer_bass, outer_treble)
        ),
    ]
    if relief >= height - NUT_JIG_MIN_FLOOR:
        raise NeckGeometryError(
            f"nut_jig_height must exceed {relief + NUT_JIG_MIN_FLOOR:g} mm, to "
            "keep wood over the corners cut away for the board's edges."
        )
    return NutSlotJig(
        thickness,
        tuple(body),
        tuple(slots),
        (treble, bass),
        radius,
        height,
        lean,
        bass_sign,
        crown,
    )


def _steps(start: float, end: float) -> list[float]:
    """Return ``start`` to ``end`` in equal steps no longer than ``ARC_STEP``."""
    count = max(1, math.ceil(abs(end - start) / ARC_STEP))
    return [start + (end - start) * index / count for index in range(count + 1)]

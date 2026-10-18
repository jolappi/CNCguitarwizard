"""A flame strap guide: a plate on the back the strap runs under.

The strap runs over the back through the guide instead of hanging from a
strap button on the edge, so it pulls from further in and the guitar
leans toward the player instead of away. As on the Design by Jone guitar
(photographed): a slim plate, a bar whose ends taper to a flame's
tongue, screwed over two spacers, each a flame reaching out past the
bar's end — a long tongue, a short one flicking up and one down — the
strap running under the bar between them. All three parts are cut from
sheet (plastic or wood), the spacers as thick as the strap needs room;
the guide is the same either side of the strap, mirrored.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..exceptions import BodyGeometryError
from ..primitives import DrawnPoint, Point2D, closed_catmull_rom, drawn_points
from .covers import CoverPlate
from .hardware import DrilledHole

STRAP_GUIDE_PLAY = 2.0
"""Room either side of the strap between the spacers, in mm."""

STRAP_GUIDE_SCREW_INSET = 3.5
"""Each screw's centre past the strap's channel, on the bar's middle
line, in mm: close by the strap, as on the photographed guide."""

STRAP_GUIDE_SCREW_CLEARANCE = 3.5
"""The screws' clearance holes through the plate and the spacers, in mm."""

STRAP_GUIDE_SAMPLES = 8
"""Points along each span of the outlines between drawn points."""

FLAME_END: tuple[DrawnPoint, ...] = (
    (0.0, 5.5, "corner"),
    (4.1, 7.5),
    (7.1, 9.3),
    (11.2, 10.3),
    (14.9, 10.5),
    (17.4, 10.0),
    (20.2, 9.0, "corner"),
    (18.2, 7.5, "corner"),
    (20.6, 6.5),
    (25.2, 4.9),
    (29.8, 3.6),
    (34.4, 2.1),
    (39.4, 0.9, "corner"),
    (34.4, -0.3),
    (29.8, -1.8),
    (25.2, -3.4),
    (20.6, -4.5),
    (17.9, -6.7, "corner"),
    (20.6, -8.0, "corner"),
    (17.4, -9.2),
    (13.3, -9.9),
    (9.2, -10.1),
    (5.1, -9.2),
    (2.5, -7.5),
    (0.0, -6.5, "corner"),
)
"""One spacer, a flame: ``(along, across)`` in mm, ``along`` from the
strap's channel outward, ``across`` square to the bar. From under the
bar's upper edge at the channel round a short tongue flicking up and
out, the long tongue reaching out 39 mm past the channel, a short
tongue flicking down and out, back under the bar's lower edge; traced
from a photograph of the guide on the Design by Jone guitar. The other
spacer is this one mirrored across the strap."""

PLATE_END: tuple[DrawnPoint, ...] = (
    (0.0, 5.0, "corner"),
    (4.0, 4.7),
    (8.0, 3.6),
    (12.5, 2.4),
    (17.4, 1.0),
    (20.6, 0.0, "corner"),
    (16.4, -1.8),
    (11.0, -3.2),
    (6.0, -4.5),
    (2.5, -5.0),
    (0.0, -5.0, "corner"),
)
"""The plate's end past the strap's channel, as ``FLAME_END``: the
10 mm bar over the screw, tapering to a flame's tongue 21 mm past the
channel (over the spacer's long tongue), its lower edge swelling as a
flame's does."""


@dataclass(frozen=True, slots=True)
class FlameStrapGuide:
    """A flame strap guide on the back of the body.

    Args:
        centre: The middle of the strap's channel, in the model frame.
        angle_degrees: The bar's direction, counter-clockwise from the
            neck's axis; the strap runs square to it.
        strap_width: The strap's width.
        gap: The spacers' thickness: the room the strap has under the
            bar.
        thickness: The plate's thickness.
        screw_diameter: The pilot holes' diameter in the body.
        screw_depth: The pilot holes' depth in the body.

    Raises:
        BodyGeometryError: For a size that is not finite and positive.
    """

    centre: Point2D
    angle_degrees: float
    strap_width: float = 25.0
    gap: float = 3.0
    thickness: float = 3.0
    screw_diameter: float = 3.0
    screw_depth: float = 12.0

    def __post_init__(self) -> None:
        """Reject a guide that cannot be cut."""
        for name in (
            "strap_width",
            "gap",
            "thickness",
            "screw_diameter",
            "screw_depth",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0.0:
                raise BodyGeometryError(
                    f"The strap guide's {name} must be finite and positive."
                )
        if self.screw_diameter >= STRAP_GUIDE_SCREW_CLEARANCE:
            raise BodyGeometryError(
                "The strap guide's screw pilots must be narrower than the "
                f"{STRAP_GUIDE_SCREW_CLEARANCE:g} mm holes through its parts."
            )

    @property
    def channel_half(self) -> float:
        """Return half the room between the spacers."""
        return self.strap_width / 2.0 + STRAP_GUIDE_PLAY

    @property
    def outline(self) -> tuple[Point2D, ...]:
        """Return the guide's footprint on the back: both spacers and the
        bar across the channel between them."""
        return self._placed(
            self._loop([*self._end(FLAME_END, 1.0), *self._end(FLAME_END, -1.0)])
        )

    @property
    def plate(self) -> tuple[Point2D, ...]:
        """Return the plate's outline: the bar and its two tongues."""
        return self._placed(
            self._loop([*self._end(PLATE_END, 1.0), *self._end(PLATE_END, -1.0)])
        )

    @property
    def spacers(self) -> tuple[tuple[Point2D, ...], tuple[Point2D, ...]]:
        """Return the two spacers' outlines: the flames past the channel."""
        return (
            self._placed(self._loop(self._end(FLAME_END, 1.0))),
            self._placed(self._loop(self._end(FLAME_END, -1.0))),
        )

    @property
    def screws(self) -> tuple[Point2D, Point2D]:
        """Return the two screws' centres, one through each spacer."""
        reach = self.channel_half + STRAP_GUIDE_SCREW_INSET
        first, second = self._placed(((reach, 0.0), (-reach, 0.0)))
        return first, second

    def covers(self) -> tuple[CoverPlate, ...]:
        """Return the parts cut from sheet: the plate and its spacers.

        Each with the screws' clearance holes; they sit on the back's
        face, not in a recess.
        """

        def holes(part: str) -> tuple[DrilledHole, ...]:
            return tuple(
                DrilledHole(
                    f"{part} screw {index}",
                    point.x,
                    point.y,
                    STRAP_GUIDE_SCREW_CLEARANCE,
                    self.thickness if part == "Strap guide plate" else self.gap,
                )
                for index, point in enumerate(self.screws, start=1)
            )

        first, second = self.spacers
        return (
            CoverPlate(
                "Strap guide plate",
                "back",
                self.plate,
                self.thickness,
                holes=holes("Strap guide plate"),
                recessed=False,
            ),
            CoverPlate(
                "Strap guide spacer 1",
                "back",
                first,
                self.gap,
                holes=holes("Strap guide spacer")[:1],
                recessed=False,
            ),
            CoverPlate(
                "Strap guide spacer 2",
                "back",
                second,
                self.gap,
                holes=holes("Strap guide spacer")[1:],
                recessed=False,
            ),
        )

    def pilot_holes(self) -> tuple[DrilledHole, ...]:
        """Return the screws' pilot holes, drilled up into the back."""
        return tuple(
            DrilledHole(
                f"Strap guide screw {index} pilot",
                point.x,
                point.y,
                self.screw_diameter,
                self.screw_depth,
            )
            for index, point in enumerate(self.screws, start=1)
        )

    def _end(self, drawn: tuple[DrawnPoint, ...], side: float) -> list[DrawnPoint]:
        """Return one end of a part from the guide's middle: ``side`` 1 the
        end past the channel's +along side, -1 the other, mirrored across
        the strap (and run backwards, so a loop through both ends goes one
        way round)."""
        moved: list[DrawnPoint] = []
        for point in drawn:
            u = side * (self.channel_half + point[0])
            moved.append((u, point[1], "corner") if len(point) == 3 else (u, point[1]))
        return moved if side > 0.0 else moved[::-1]

    @staticmethod
    def _loop(drawn: list[DrawnPoint]) -> tuple[tuple[float, float], ...]:
        """Return the closed outline through drawn points, its marked
        points sharp."""
        points, corners = drawn_points(tuple(drawn))
        return tuple(
            (p.x, p.y) for p in closed_catmull_rom(points, STRAP_GUIDE_SAMPLES, corners)
        )

    def _placed(self, points: tuple[tuple[float, float], ...]) -> tuple[Point2D, ...]:
        """Return points from the guide's own frame in the model frame."""
        angle = math.radians(self.angle_degrees)
        cosine, sine = math.cos(angle), math.sin(angle)
        return tuple(
            Point2D(
                self.centre.x + u * cosine - v * sine,
                self.centre.y + u * sine + v * cosine,
            )
            for u, v in points
        )

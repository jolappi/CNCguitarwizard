"""A flame strap guide: a plate on the back the strap runs under.

The strap runs over the back through the guide instead of hanging from a
strap button on the edge, so it pulls from further in and the guitar
leans toward the player instead of away. The guide is a plate shaped as
a bar with a flame at either end, screwed to the back over two spacers,
one under each flame: the strap runs under the bar between them. All
three parts are cut from sheet (plastic or wood), the spacers as thick
as the strap needs room.
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

STRAP_GUIDE_SCREW_INSET = 8.0
"""Each screw's centre past the strap's channel, on the bar's middle
line, in mm."""

STRAP_GUIDE_SCREW_CLEARANCE = 3.5
"""The screws' clearance holes through the plate and the spacers, in mm."""

STRAP_GUIDE_SAMPLES = 8
"""Points along each span of the flames' outline."""

FLAME_END: tuple[DrawnPoint, ...] = (
    (0.0, -11.0, "corner"),
    (6.8, -12.0),
    (12.8, -14.5),
    (17.8, -19.0),
    (21.2, -25.0),
    (26.3, -29.0, "corner"),
    (22.9, -21.0),
    (23.8, -15.0),
    (29.8, -12.0),
    (36.5, -10.0),
    (43.4, -9.0, "corner"),
    (37.4, -5.0),
    (31.4, -2.0),
    (31.4, 3.0),
    (34.9, 7.0),
    (39.9, 9.0, "corner"),
    (33.1, 11.5),
    (26.3, 13.0),
    (18.7, 13.0),
    (10.2, 12.0),
    (4.2, 11.2),
    (0.0, 11.0, "corner"),
)
"""One flame at the end of the guide's bar: ``(along, across)``, ``along``
from the strap's channel outward, ``across`` the strap's direction; from
the bar's lower edge round three tongues sweeping out and down (their
tips sharp, the lowest the broadest, the middle one reaching furthest:
43 mm past the channel) to its upper edge. The bar is 22 mm wide; the
other end's flame is this one turned half round."""


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
    strap_width: float = 50.0
    gap: float = 5.0
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
        """Return the plate's outline: the bar and its two flames."""
        return self._placed(self._loop([*self._end(1.0), *self._end(-1.0)]))

    @property
    def spacers(self) -> tuple[tuple[Point2D, ...], tuple[Point2D, ...]]:
        """Return the two spacers' outlines: the flames past the channel."""
        return (
            self._placed(self._loop(self._end(1.0))),
            self._placed(self._loop(self._end(-1.0))),
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
                self.outline,
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

    def _end(self, side: float) -> list[DrawnPoint]:
        """Return one flame, from the guide's middle: ``side`` 1 the
        flame past the channel's +along side, -1 the other, turned half
        round."""
        moved: list[DrawnPoint] = []
        for point in FLAME_END:
            u = side * (self.channel_half + point[0])
            v = side * point[1]
            moved.append((u, v, "corner") if len(point) == 3 else (u, v))
        return moved

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

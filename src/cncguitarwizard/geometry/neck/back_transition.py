"""Where the neck's rounded back turns into a flat block, drawn.

The heel's mounting block and a flat (0 degree) headstock are flat-backed
blocks the neck's rounded back runs into. Seen from behind, two lines
across the back say how: where the block's flat begins (the heel's or the
headstock's rounding, its shape) and where the neck's own profile does
(how far the rounding runs out onto the neck). Between them the back
turns evenly from the one into the other. It is never proud of either, so
two lines are enough; a volute, standing proud, needs its crest too.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..exceptions import NeckGeometryError
from ..primitives import DrawnPoint, Point2D
from .drawn_lines import nearest, side_toward, smootherstep

DEFAULT_HEEL_LINES: dict[str, tuple[tuple[float, float], ...]] = {
    "flat": ((0.0, 0.0), (0.0, 1.1)),
    "neck": ((60.0, 0.0), (57.0, 0.4), (51.0, 0.7), (45.0, 1.1)),
}
"""Where drawing a heel's lines starts: half of each seen from behind,
``(ahead of the heel's block, across as a share of the heel's
half-width)`` from the centre line out, much as the smooth heel is (its
``heel_root_length`` and ``heel_root_center_extension``): the block flat
from its start straight across, the neck's profile running into it 45 mm
ahead at the sides and 60 mm down the middle."""

DEFAULT_ROOT_LINES: dict[str, tuple[tuple[float, float], ...]] = {
    "flat": ((20.0, 0.0), (20.0, 1.1)),
    "neck": ((-14.0, 0.0), (-14.0, 1.1)),
}
"""Where drawing the headstock's root starts: half of each line seen from
behind, ``(behind the nut, across as a share of the neck's half-width at
the nut)``, where the smooth root runs: the headstock's back from 20 mm
behind the nut, the neck's own profile from 14 mm onto the neck, straight
across."""


@dataclass(frozen=True, slots=True)
class BackTransition:
    """Where the neck's back turns into a flat block, drawn as two lines.

    The model's ``x`` runs from the nut toward the body; ``toward_block``
    says which way along it the block is. On the block's side of ``flat``
    the back is the block's, ``depth_at`` below the glue face, square at
    its sides; on the neck's side of ``neck`` it is the neck's own rounded
    profile; between, the back turns from the one into the other by
    ``share``, evenly, meeting each with no edge.

    Args:
        flat: Where the block's flat begins, seen from behind, across the
            back from one side to the other, in the model frame.
        neck: Where the neck's own profile begins, likewise.
        depth: The block's back's depth below the glue face at the nut
            (``x`` 0), in mm.
        toward_block: 1.0 for a block toward the body (the heel), -1.0 for
            one toward the headstock.
        slope: How much deeper its back lies for each mm toward the body:
            0 for a back level with the glue face (the heel's, a flat
            headstock's); an angled headstock's back falls away behind
            the nut, so less deep toward the body (negative).

    Raises:
        NeckGeometryError: For a line of fewer than two points, a back
            not below the glue face all along the lines, or
            ``toward_block`` neither 1 nor -1.
    """

    flat: tuple[Point2D, ...]
    neck: tuple[Point2D, ...]
    depth: float
    toward_block: float
    slope: float = 0.0
    block_sides: tuple[float, float] = field(init=False, repr=False, compare=False)
    """Which side of each line (flat, neck) the block is: the sign of
    ``nearest``'s side there."""

    def __post_init__(self) -> None:
        """Reject a transition that cannot be shaped; find which side of
        each line the block is."""
        if len(self.flat) < 2 or len(self.neck) < 2:
            raise NeckGeometryError(
                "A drawn transition needs both its lines, two points each."
            )
        if not math.isfinite(self.depth) or not math.isfinite(self.slope):
            raise NeckGeometryError("A drawn transition's depth must be finite.")
        if self.toward_block not in (-1.0, 1.0):
            raise NeckGeometryError("A drawn transition's block is at 1 or -1.")
        object.__setattr__(
            self,
            "block_sides",
            (
                side_toward(self.flat, self.toward_block),
                side_toward(self.neck, self.toward_block),
            ),
        )
        if any(self.depth_at(x) <= 0.0 for x in self.span):
            raise NeckGeometryError(
                "A drawn transition's block must lie below the glue face: its "
                "depth must be positive along its lines."
            )

    def depth_at(self, x: float) -> float:
        """Return the block's back's depth below the glue face at ``x``."""
        return self.depth + self.slope * x

    @property
    def span(self) -> tuple[float, float]:
        """Return where along the neck its lines reach, ``(least x, most
        x)``."""
        xs = [point.x for point in (*self.flat, *self.neck)]
        return min(xs), max(xs)

    def share(self, x: float, y: float) -> float:
        """Return how far the back at ``(x, y)`` has turned into the block.

        1 on the block's side of the flat line, 0 on the neck's side of the
        neck line; between them the way from the neck line to the flat
        one, eased so the back meets each with no edge.
        """
        point = Point2D(x, y)
        flat_side, neck_side = self.block_sides
        to_flat, side = nearest(point, self.flat)
        if side * flat_side >= 0.0:
            return 1.0
        to_neck, side = nearest(point, self.neck)
        if side * neck_side <= 0.0:
            return 0.0
        return smootherstep(to_neck / (to_neck + to_flat))


def default_transition_lines(
    lines: dict[str, tuple[tuple[float, float], ...]], half_width: float
) -> dict[str, tuple[DrawnPoint, ...]]:
    """Return a drawn transition's two lines where drawing them starts.

    Args:
        lines: ``DEFAULT_HEEL_LINES`` or ``DEFAULT_ROOT_LINES``.
        half_width: The half-width their across shares are of.

    Returns:
        ``{"flat", "neck"}``, each half its line seen from behind, as
        ``drawn_back_line`` takes them, across in mm.
    """
    return {
        name: tuple((along, round(share * half_width, 1)) for along, share in line)
        for name, line in lines.items()
    }

"""How each fret leans: slanted frets and multiscale (fanned) frets."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..exceptions import FretboardGeometryError


@dataclass(frozen=True, slots=True)
class FretSkew:
    """The lean of every fret line, as X gained per millimetre of Y.

    A fret sits at its equal-temperament position ``x`` on the centerline
    and runs straight across the board; ``at(x)`` is the tangent of its
    lean (``dx/dy``). Two effects add up:

    * ``slant`` — every fret, and the nut and board ends, lean the same.
    * a fan — the bass side's scale is ``fan`` longer than the treble
      side's. Each fret is the straight line through its exact positions
      on the two outer strings; the fret at ``perpendicular_fraction`` of
      the scale is square to the neck. The outer strings run from
      ``outer_nut`` off the centerline at the nut to ``outer_bridge`` at
      the bridge, and the centerline scale ``scale_length`` is the mean of
      the two.

    Args:
        slant: Constant lean, the tangent of the slant angle.
        fan: Bass scale minus treble scale, in mm (0 for no fan).
        perpendicular_fraction: Fraction of the scale where the fret is
            square (``1 - 2^(-n/12)`` for fret ``n``; 0 at the nut).
        scale_length: The centerline scale.
        outer_nut: The outermost strings' distance from the centerline at
            the nut.
        outer_bridge: Their distance from it at the bridge.
        bass_sign: ``+1`` when the bass strings are at +Y, ``-1`` at -Y.

    Raises:
        FretboardGeometryError: For non-finite values or a fan without a
            positive scale and string spread.
    """

    slant: float = 0.0
    fan: float = 0.0
    perpendicular_fraction: float = 0.0
    scale_length: float = 1.0
    outer_nut: float = 1.0
    outer_bridge: float = 1.0
    bass_sign: float = -1.0

    def __post_init__(self) -> None:
        """Reject values the frets cannot be laid out from."""
        values = (
            self.slant,
            self.fan,
            self.perpendicular_fraction,
            self.scale_length,
            self.outer_nut,
            self.outer_bridge,
        )
        if not all(math.isfinite(value) for value in values):
            raise FretboardGeometryError("Fret skew values must be finite.")
        if self.fan and (
            self.scale_length <= 0.0
            or self.outer_nut <= 0.0
            or self.outer_bridge <= 0.0
        ):
            raise FretboardGeometryError(
                "A fanned fret layout needs a scale and a string spread."
            )

    @property
    def is_square(self) -> bool:
        """Return whether every fret is square to the neck."""
        return self.slant == 0.0 and self.fan == 0.0

    def at(self, x: float) -> float:
        """Return the lean (``dx/dy``) of the fret line through centerline ``x``."""
        if not self.fan:
            return self.slant
        fraction = x / self.scale_length
        half_span = self.outer_nut + (self.outer_bridge - self.outer_nut) * fraction
        return self.slant + self.bass_sign * (
            fraction - self.perpendicular_fraction
        ) * self.fan / (2.0 * half_span)

    def fan_only(self) -> FretSkew:
        """Return this skew without its slant (what the bridge and pickups follow)."""
        return FretSkew(
            0.0,
            self.fan,
            self.perpendicular_fraction,
            self.scale_length,
            self.outer_nut,
            self.outer_bridge,
            self.bass_sign,
        )

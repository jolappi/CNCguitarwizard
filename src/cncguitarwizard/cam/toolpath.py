"""Toolpaths as ordered tool-centre moves in the machine frame."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .exceptions import ToolpathError


@dataclass(frozen=True, slots=True)
class Move:
    """One straight tool-centre move to an absolute position.

    Args:
        x: Target X in millimetres.
        y: Target Y in millimetres.
        z: Target Z in millimetres; zero is the stock top, cuts are
            negative.
        rapid: ``True`` for a non-cutting traverse (``G0``), ``False``
            for a feed move (``G1``).
        feed: Feed rate in millimetres per minute for a feed move.
    """

    x: float
    y: float
    z: float
    rapid: bool
    feed: float | None = None


@dataclass(frozen=True, slots=True)
class Toolpath:
    """A named, ordered sequence of moves cut with one tool."""

    name: str
    moves: tuple[Move, ...]

    def cutting_length(self) -> float:
        """Return the total length of feed moves in millimetres."""
        return self._length(rapid=False)

    def rapid_length(self) -> float:
        """Return the total length of rapid moves in millimetres."""
        return self._length(rapid=True)

    def deepest_z(self) -> float:
        """Return the lowest Z reached, or zero for an empty path."""
        return min((move.z for move in self.moves), default=0.0)

    def _length(self, *, rapid: bool) -> float:
        total = 0.0
        previous: Move | None = None
        for move in self.moves:
            if previous is not None and move.rapid == rapid:
                total += math.dist(
                    (previous.x, previous.y, previous.z),
                    (move.x, move.y, move.z),
                )
            previous = move
        return total


class PathBuilder:
    """Accumulate moves while keeping rapids at the safe height.

    The builder tracks the tool position so callers can say "rapid
    there", "plunge to this depth", or "cut to that point" without
    repeating heights and feeds. It refuses to produce a rapid move
    below the safe height: ``rapid_to`` retracts first if necessary.
    """

    def __init__(
        self,
        name: str,
        *,
        safe_height: float,
        feed_rate: float,
        plunge_rate: float,
    ) -> None:
        if safe_height <= 0.0:
            raise ToolpathError("Safe height must be positive.")
        self._name = name
        self._safe_height = safe_height
        self._feed_rate = feed_rate
        self._plunge_rate = plunge_rate
        self._moves: list[Move] = []
        self._x: float | None = None
        self._y: float | None = None
        self._z = safe_height

    @property
    def x(self) -> float:
        """Return the current X, or raise if no move has been made."""
        if self._x is None:
            raise ToolpathError("Tool position is undefined before the first move.")
        return self._x

    @property
    def y(self) -> float:
        """Return the current Y, or raise if no move has been made."""
        if self._y is None:
            raise ToolpathError("Tool position is undefined before the first move.")
        return self._y

    @property
    def z(self) -> float:
        """Return the current Z."""
        return self._z

    @property
    def positioned(self) -> bool:
        """Return whether an XY position has been established."""
        return self._x is not None

    def retract(self) -> None:
        """Rapid straight up to the safe height if not already there."""
        if self._z >= self._safe_height or self._x is None or self._y is None:
            self._z = max(self._z, self._safe_height)
            return
        self._z = self._safe_height
        self._moves.append(Move(self._x, self._y, self._z, True))

    def rapid_to(self, x: float, y: float) -> None:
        """Traverse to an XY position at the safe height."""
        self.retract()
        self._x, self._y = x, y
        self._moves.append(Move(x, y, self._z, True))

    def rapid_down_to(self, z: float, clearance: float = 1.0) -> None:
        """Rapid down to ``clearance`` above a depth already cut."""
        target = z + clearance
        if target < self._z:
            self._z = target
            self._moves.append(Move(self.x, self.y, self._z, True))

    def lift_to(self, z: float) -> None:
        """Rapid straight up to ``z`` (no higher than the safe height)."""
        target = min(z, self._safe_height)
        if target > self._z:
            self._z = target
            self._moves.append(Move(self.x, self.y, self._z, True))

    def plunge_to(self, z: float) -> None:
        """Feed straight down (or up) to ``z`` at the plunge rate."""
        if z == self._z:
            return
        self._z = z
        self._moves.append(Move(self.x, self.y, z, False, self._plunge_rate))

    def cut_to(self, x: float, y: float, z: float | None = None) -> None:
        """Feed to a position at the cutting rate, keeping Z by default."""
        if z is None:
            z = self._z
        self._x, self._y, self._z = x, y, z
        self._moves.append(Move(x, y, z, False, self._feed_rate))

    def build(self) -> Toolpath:
        """Return the accumulated moves, ending at the safe height."""
        self.retract()
        return Toolpath(self._name, tuple(self._moves))

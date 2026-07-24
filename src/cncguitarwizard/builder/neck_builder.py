"""Fluent builder for immutable neck models."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Self

from .exceptions import BuilderError
from .neck import Neck


@dataclass(frozen=True, slots=True)
class NeckBuilder:
    """Build an immutable neck model from required dimensions."""

    _scale_length: float | None = None
    _nut_width: float | None = None
    _bridge_width: float | None = None

    def scale_length(self, value: float) -> Self:
        """Set the nut-to-bridge distance.

        Args:
            value: Scale length in millimetres.

        Returns:
            A builder with the specified scale length.
        """
        return replace(self, _scale_length=value)

    def nut_width(self, value: float) -> Self:
        """Set the fretboard width at the nut.

        Args:
            value: Nut width in millimetres.

        Returns:
            A builder with the specified nut width.
        """
        return replace(self, _nut_width=value)

    def bridge_width(self, value: float) -> Self:
        """Set the fretboard width at the bridge.

        Args:
            value: Bridge width in millimetres.

        Returns:
            A builder with the specified bridge width.
        """
        return replace(self, _bridge_width=value)

    def build(self) -> Neck:
        """Build an immutable neck model.

        Raises:
            BuilderError: If a required dimension is missing or not positive.

        Returns:
            The completed neck model.
        """
        if self._scale_length is None:
            raise BuilderError("Scale length is required.")
        if self._nut_width is None:
            raise BuilderError("Nut width is required.")
        if self._bridge_width is None:
            raise BuilderError("Bridge width is required.")
        if self._scale_length <= 0.0:
            raise BuilderError("Scale length must be greater than zero.")
        if self._nut_width <= 0.0:
            raise BuilderError("Nut width must be greater than zero.")
        if self._bridge_width <= 0.0:
            raise BuilderError("Bridge width must be greater than zero.")

        return Neck(self._scale_length, self._nut_width, self._bridge_width)

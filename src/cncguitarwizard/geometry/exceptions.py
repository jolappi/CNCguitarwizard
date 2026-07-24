"""Exceptions raised by the geometry package."""

from __future__ import annotations

from ..exceptions import CNCGuitarWizardError


class GeometryException(CNCGuitarWizardError):
    """Base exception for all geometry package errors."""


class ZeroLengthVectorError(GeometryException):
    """Raised when normalizing a vector with zero length."""


class FretboardGeometryError(GeometryException):
    """Raised when fretboard geometry cannot be constructed safely."""


class NeckGeometryError(GeometryException):
    """Raised when neck geometry cannot be constructed safely."""

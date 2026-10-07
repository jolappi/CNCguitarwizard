"""Errors raised reading a drawing back from another program."""

from __future__ import annotations

from ..exceptions import CNCGuitarWizardError


class DrawingError(CNCGuitarWizardError):
    """Raised when a drawing cannot be read or does not fit the design."""

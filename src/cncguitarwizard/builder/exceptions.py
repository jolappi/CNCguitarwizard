"""Exceptions raised by model builders."""

from __future__ import annotations

from ..exceptions import CNCGuitarWizardError


class BuilderError(CNCGuitarWizardError):
    """Raised when a builder cannot create a valid model."""

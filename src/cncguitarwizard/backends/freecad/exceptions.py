"""Exceptions raised by the FreeCAD backend."""

from __future__ import annotations

from ...exceptions import CNCGuitarWizardError


class FreeCADBackendError(CNCGuitarWizardError):
    """Raised when FreeCAD output cannot be generated safely."""

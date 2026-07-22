"""
Custom exceptions used by CNCguitarwizard.
"""


class CNCGuitarWizardError(Exception):
    """Base exception for all project-specific exceptions."""


class ValidationError(CNCGuitarWizardError):
    """Raised when validation fails."""


class GeometryError(CNCGuitarWizardError):
    """Raised when geometry generation fails."""


class BackendError(CNCGuitarWizardError):
    """Raised when a CAD backend fails."""


class CAMError(CNCGuitarWizardError):
    """Raised when CAM generation fails."""

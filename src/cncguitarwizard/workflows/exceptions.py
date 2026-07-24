"""Exceptions raised by user-facing build workflows."""


class BuildWorkflowError(RuntimeError):
    """Base exception for a failed CNCguitarwizard build workflow."""


class FreeCADExecutionError(BuildWorkflowError):
    """Raised when FreeCAD cannot produce the requested build artifacts."""

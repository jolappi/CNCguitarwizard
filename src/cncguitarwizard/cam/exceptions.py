"""Exceptions raised while planning toolpaths."""

from ..exceptions import CAMError


class ToolpathError(CAMError):
    """Raised when a feature cannot be machined with the given tool."""


__all__ = ["CAMError", "ToolpathError"]

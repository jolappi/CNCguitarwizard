"""
Project metadata.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from cncguitarwizard.version import __version__


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC value."""
    return datetime.now(UTC)


@dataclass(slots=True)
class ProjectMetadata:
    """General project metadata."""

    name: str = "Untitled"

    author: str = ""

    description: str = ""

    project_id: str = field(default_factory=lambda: str(uuid4()))

    created: datetime = field(default_factory=utc_now)

    modified: datetime = field(default_factory=utc_now)

    version: str = __version__

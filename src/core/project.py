"""
cncguitarwizard.core.project

Project root object for CNCguitarwizard.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from cncguitarwizard.version import __version__


@dataclass(slots=True)
class ProjectMetadata:
    """Metadata describing a CNCguitarwizard project."""

    name: str = "Untitled"
    author: str = ""
    description: str = ""

    created: datetime = field(default_factory=datetime.utcnow)
    modified: datetime = field(default_factory=datetime.utcnow)

    project_id: str = field(default_factory=lambda: str(uuid4()))

    version: str = __version__


@dataclass(slots=True)
class Project:
    """Root object for every CNCguitarwizard project."""

    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)

    def touch(self) -> None:
        """Update modification timestamp."""
        self.metadata.modified = datetime.utcnow()

"""
Project metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from cncguitarwizard.version import __version__


@dataclass(slots=True)
class ProjectMetadata:
    """General project metadata."""

    name: str = "Untitled"

    author: str = ""

    description: str = ""

    project_id: str = field(default_factory=lambda: str(uuid4()))

    created: datetime = field(default_factory=datetime.utcnow)

    modified: datetime = field(default_factory=datetime.utcnow)

    version: str = __version__

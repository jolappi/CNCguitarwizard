"""
Root project object.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .metadata import ProjectMetadata
from .neck import NeckParameters


@dataclass(slots=True)
class Project:
    """
    Root object for CNCguitarwizard.

    Every future module hangs under this object.
    """

    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    neck: NeckParameters = field(default_factory=NeckParameters)

    # Added in future commits
    # parameters
    # materials
    # machine
    # tools
    # validation

    def touch(self) -> None:
        """Update modification timestamp."""
        self.metadata.modified = datetime.now(UTC)

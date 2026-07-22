"""
Root project object.
"""

from dataclasses import dataclass, field

from .metadata import ProjectMetadata


@dataclass(slots=True)
class Project:
    """
    Root object for CNCguitarwizard.

    Every future module hangs under this object.
    """

    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)

    # Added in future commits
    # parameters
    # materials
    # machine
    # tools
    # validation

    def touch(self) -> None:
        """Update modification timestamp."""

        from datetime import datetime

        self.metadata.modified = datetime.utcnow()

from datetime import UTC

from cncguitarwizard.core.project import Project


def test_project_defaults() -> None:
    project = Project()

    assert project.metadata.name == "Untitled"
    assert project.metadata.project_id != ""
    assert project.metadata.version != ""
    assert project.metadata.created.tzinfo is UTC
    assert project.metadata.modified.tzinfo is UTC

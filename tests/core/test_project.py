from cncguitarwizard.core.project import Project


def test_project_defaults():

    project = Project()

    assert project.metadata.name == "Untitled"

    assert project.metadata.project_id != ""

    assert project.metadata.version != ""

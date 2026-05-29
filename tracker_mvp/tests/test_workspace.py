from app.workspace import get_active_workspace, get_database_path, open_workspace

from tests.conftest import assert_workspace_structure


def test_workspace_created_with_required_project_structure(isolated_workspace):
    assert_workspace_structure(isolated_workspace)
    assert get_active_workspace() == isolated_workspace
    assert get_database_path() == isolated_workspace / "tracker.sqlite"


def test_existing_workspace_can_be_opened(isolated_workspace):
    opened = open_workspace(isolated_workspace)

    assert opened == isolated_workspace
    assert get_active_workspace() == isolated_workspace

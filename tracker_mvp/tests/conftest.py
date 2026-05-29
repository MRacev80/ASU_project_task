from pathlib import Path

import pytest


@pytest.fixture()
def isolated_workspace(tmp_path, monkeypatch):
    from app import db as db_module
    from app import workspace as workspace_module

    data_dir = tmp_path / "app_data"
    state_file = data_dir / "app_state.json"
    workspace_dir = tmp_path / "project_workspace"

    # Тесты не должны трогать реальный app_state.json и реальный tracker.sqlite пользователя.
    monkeypatch.setattr(workspace_module, "DATA_DIR", data_dir)
    monkeypatch.setattr(workspace_module, "STATE_FILE", state_file)
    monkeypatch.setattr(db_module, "DATA_DIR", data_dir)

    # SQLAlchemy engine кэшируется глобально, поэтому каждый тест начинает с чистого подключения.
    db_module._engine = None
    db_module._session_local = None
    db_module._database_path = None

    workspace_module.create_workspace(
        workspace_dir,
        project_name="QA Котельная",
        customer="Тестовый заказчик",
        automation_object="Котельная HCFA",
    )
    db_module.init_db()

    yield workspace_dir

    db_module._engine = None
    db_module._session_local = None
    db_module._database_path = None


@pytest.fixture()
def db_session(isolated_workspace):
    from app.db import get_session_local

    session = get_session_local()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def project(db_session):
    from app.models import Project

    project = Project(
        name="QA Котельная",
        project_code="QA-001",
        customer="Тестовый заказчик",
        automation_object="Котельная HCFA",
        contract_number="QA-2026-001",
        project_manager="QA РП",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def assert_workspace_structure(workspace_dir: Path) -> None:
    expected = [
        "project_config.json",
        "project_context.md",
        "agent_rules.md",
        "tracker.sqlite",
        "documents",
        "archive",
        "backup",
        "exports",
        "agents/inbox",
        "agents/work",
        "agents/outbox",
        "agents/logs",
    ]
    for relative in expected:
        assert (workspace_dir / relative).exists(), relative


@pytest.fixture()
def client(isolated_workspace):
    """HTTP-клиент TestClient для интеграционных тестов UI-маршрутов."""
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)

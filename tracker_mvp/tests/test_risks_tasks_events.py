from datetime import date

from sqlalchemy import select

from app.models import Event, Risk, Task
from app.routes.risks import create_risk, delete_risk, update_risk
from app.routes.tasks import change_task_status, create_task


def test_task_creation_and_status_change_are_logged(db_session, project):
    create_response = create_task(
        project.id,
        title="Проверить шкаф управления",
        description="Проверить состав шкафа",
        type="работа",
        priority="Высокий",
        due_date=date(2026, 6, 1),
        assignee="QA Инженер",
        db=db_session,
    )
    assert create_response.headers["location"] == f"/projects/{project.id}/tasks"

    task = db_session.scalars(select(Task).where(Task.project_id == project.id)).one()
    assert task.title == "Проверить шкаф управления"
    assert task.status == "Бэклог"

    status_response = change_task_status(task.id, status="В работе", db=db_session)
    db_session.refresh(task)
    assert task.status == "В работе"
    assert status_response.headers["location"] == f"/projects/{project.id}/tasks"

    events = db_session.scalars(select(Event).where(Event.project_id == project.id)).all()
    assert {event.event_type for event in events} >= {"task.created", "task.status_changed"}


def test_task_can_be_created_without_due_date(db_session, project):
    response = create_task(
        project.id,
        title="Задача без срока",
        due_date="",
        db=db_session,
    )

    task = db_session.scalars(select(Task).where(Task.project_id == project.id, Task.title == "Задача без срока")).one()

    assert response.headers["location"] == f"/projects/{project.id}/tasks"
    assert task.due_date is None


def test_risk_can_be_created_updated_and_deleted(db_session, project):
    create_risk(
        project.id,
        title="Задержка поставки шкафа",
        description="Поставка может уйти за плановый срок",
        probability="Высокая",
        impact="Высокое",
        mitigation="Заранее согласовать аналоги",
        owner="QA РП",
        status="Открыт",
        linked_entity_type="procurement",
        linked_entity_id="",
        db=db_session,
    )

    risk = db_session.scalars(select(Risk).where(Risk.project_id == project.id)).one()
    assert risk.title == "Задержка поставки шкафа"
    assert risk.status == "Открыт"
    assert risk.risk_score == "9"
    assert risk.risk_level == "Критичный"

    update_risk(
        risk.id,
        title="Задержка поставки шкафа управления",
        description=risk.description,
        probability="Средняя",
        impact="Высокое",
        mitigation="Проверить складские остатки",
        owner="QA Снабжение",
        status="В работе",
        linked_entity_type="procurement",
        linked_entity_id="PR-1",
        db=db_session,
    )
    db_session.refresh(risk)
    assert risk.title == "Задержка поставки шкафа управления"
    assert risk.status == "В работе"
    assert risk.risk_score == "6"
    assert risk.risk_level == "Критичный"
    assert risk.linked_entity_id == "PR-1"

    delete_risk(risk.id, db=db_session)
    assert db_session.get(Risk, risk.id) is None

    events = db_session.scalars(select(Event).where(Event.project_id == project.id)).all()
    assert {event.event_type for event in events} >= {"risk.created", "risk.updated", "risk.deleted"}
    assert any(event.before_state for event in events if event.event_type == "risk.updated")
    assert any(event.after_state for event in events if event.event_type == "risk.updated")

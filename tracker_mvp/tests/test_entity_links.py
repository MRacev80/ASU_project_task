from sqlalchemy import select

from app.models import Document, EntityLink, Event, ProcurementItem, Risk, Task
from app.routes.links import create_entity_link, delete_entity_link
from app.routes.pages import build_entity_labels, build_link_targets, build_link_views_by_source


def test_entity_link_can_be_created_and_deleted(db_session, project):
    create_entity_link(
        project.id,
        source_type="task",
        source_id="task-1",
        target_type="document",
        target_id="document-1",
        relation_type="основание",
        note="Документ является основанием задачи",
        return_tab="tasks",
        db=db_session,
    )

    link = db_session.scalars(select(EntityLink).where(EntityLink.project_id == project.id)).one()
    assert link.source_type == "task"
    assert link.target_type == "document"
    assert link.relation_type == "основание"

    delete_entity_link(link.id, return_tab="tasks", db=db_session)

    assert db_session.get(EntityLink, link.id) is None
    events = db_session.scalars(select(Event).where(Event.project_id == project.id)).all()
    assert {event.event_type for event in events} >= {"entity_link.created", "entity_link.deleted"}


def test_entity_link_can_be_created_from_combined_target_ref(db_session, project):
    create_entity_link(
        project.id,
        source_type="procurement",
        source_id="procurement-1",
        target_ref="risk:risk-1",
        relation_type="снижает риск",
        return_tab="procurement",
        db=db_session,
    )

    link = db_session.scalars(select(EntityLink).where(EntityLink.project_id == project.id)).one()

    assert link.source_type == "procurement"
    assert link.source_id == "procurement-1"
    assert link.target_type == "risk"
    assert link.target_id == "risk-1"
    assert link.relation_type == "снижает риск"


def test_entity_link_view_uses_readable_labels(project):
    task = Task(project_id=project.id, id="task-1", title="Подготовить ТЗ")
    document = Document(project_id=project.id, id="doc-1", title="Расчет КП", type="расчет КП/СС")
    procurement = ProcurementItem(project_id=project.id, id="proc-1", name="Шкаф управления")
    risk = Risk(project_id=project.id, id="risk-1", title="Задержка поставки")
    link = EntityLink(
        project_id=project.id,
        source_type="task",
        source_id=task.id,
        target_type="procurement",
        target_id=procurement.id,
        relation_type="ожидает",
        note="Нужна комплектация",
    )

    targets = build_link_targets([task], [document], [procurement], [risk], [])
    labels = build_entity_labels(targets)
    views = build_link_views_by_source([link], labels)

    assert labels["task:task-1"] == "Задача: Подготовить ТЗ"
    assert labels["procurement:proc-1"] == "Закупка: Шкаф управления"
    assert views["task:task-1"][0]["other_label"] == "Закупка: Шкаф управления"
    assert views["procurement:proc-1"][0]["other_label"] == "Задача: Подготовить ТЗ"
    assert views["task:task-1"][0]["note"] == "Нужна комплектация"

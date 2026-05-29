from datetime import date, timedelta

from app.models import EntityLink, Event, P3Activity, P3Cycle
from app.routes.pages import build_graph_edges, build_graph_nodes, build_entity_labels, filter_events
from app.services.p3_service import get_p3_cycles, get_p3_groups, is_overdue


def test_graph_nodes_and_edges_are_filtered_by_entity_and_relation(project):
    targets = [
        {"type": "task", "id": "task-1", "label": "Задача: Проверить шкаф"},
        {"type": "risk", "id": "risk-1", "label": "Риск: задержка поставки"},
        {"type": "document", "id": "doc-1", "label": "Документ: расчет КП"},
    ]
    links = [
        EntityLink(project_id=project.id, source_type="task", source_id="task-1", target_type="risk", target_id="risk-1", relation_type="снижает"),
        EntityLink(project_id=project.id, source_type="document", source_id="doc-1", target_type="task", target_id="task-1", relation_type="основание"),
    ]

    labels = build_entity_labels(targets)
    nodes = build_graph_nodes(targets, links, selected_key="task:task-1")
    edges = build_graph_edges(links, labels, nodes, relation="основание")

    assert {node["key"] for node in nodes} == {"task:task-1", "risk:risk-1", "document:doc-1"}
    assert len(edges) == 1
    assert edges[0]["source_label"] == "Документ: расчет КП"
    assert edges[0]["target_label"] == "Задача: Проверить шкаф"


def test_event_filters_by_type_entity_and_source(project):
    events = [
        Event(project_id=project.id, event_type="task.created", entity_type="task", entity_id="1", source="ui"),
        Event(project_id=project.id, event_type="p3_cycle.updated", entity_type="p3_cycle", entity_id="2", source="ui"),
        Event(project_id=project.id, event_type="agent.proposed", entity_type="agent_proposal", entity_id="3", source="agent"),
    ]

    filtered = filter_events(events, event_type="", entity_type="p3_cycle", source="ui")

    assert [event.event_type for event in filtered] == ["p3_cycle.updated"]


def test_p3_overdue_flags_for_activities_and_cycles(db_session, project):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    db_session.add(P3Activity(project_id=project.id, code="A01", group_code="A", group_title="Запуск проекта", title="Назначить спонсора", next_due_at=yesterday))
    db_session.add(P3Activity(project_id=project.id, code="A02", group_code="A", group_title="Запуск проекта", title="Назначить РП", next_due_at=tomorrow))
    db_session.add(P3Cycle(project_id=project.id, title="Старый цикл", end_date=yesterday, status="Активен"))
    db_session.commit()

    groups = get_p3_groups(db_session, project.id)
    cycles = get_p3_cycles(db_session, project.id)

    overdue_activity = next(activity for group in groups for activity in group["activities"] if activity.code == "A01")
    active_activity = next(activity for group in groups for activity in group["activities"] if activity.code == "A02")
    assert overdue_activity.is_overdue is True
    assert active_activity.is_overdue is False
    assert cycles[0].is_overdue is True
    assert is_overdue(yesterday, "Выполнено") is False

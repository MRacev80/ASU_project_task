from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AgentProposal, CompanyPerson, Document, EntityLink, Event, P3Activity, ProcurementItem, Project, ProjectPhase, ProjectSite, ProjectSpecification, Risk, SpecificationItem, Task, WorkItem
from app.services.p3_service import get_p3_cycles, get_p3_groups, get_p3_summary
from app.services.phase_service import phase_view_model
from app.templates import templates
from app.workspace import get_active_workspace


router = APIRouter()


@router.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    if get_active_workspace() is None:
        return templates.TemplateResponse(
            "workspace.html",
            {"request": request, "active_workspace": None, "error": ""},
        )
    projects = db.scalars(select(Project).order_by(Project.created_at.desc())).all()
    project = projects[0] if projects else None
    return render_project_page(request, db, projects, project)


@router.get("/projects/{project_id}")
def project_page(project_id: str, request: Request, db: Session = Depends(get_db)):
    return project_tab_page(project_id, "main", request, db)


@router.get("/projects/{project_id}/{tab}")
def project_tab_page(project_id: str, tab: str, request: Request, db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).order_by(Project.created_at.desc())).all()
    project = db.get(Project, project_id)
    return render_project_page(request, db, projects, project, tab)


def render_project_page(request: Request, db: Session, projects: list[Project], project: Project | None, active_tab: str = "main"):
    valid_tabs = {"main", "phases", "sites", "tasks", "budget", "procurement", "documents", "risks", "p3", "graph", "events", "agents"}
    if active_tab not in valid_tabs:
        active_tab = "main"

    context = build_empty_context(request, projects, project, active_tab)
    people = db.scalars(select(CompanyPerson).where(CompanyPerson.is_active == "1").order_by(CompanyPerson.full_name)).all()
    context["company_people"] = people
    context["company_people_names"] = [person.full_name for person in people]
    workspace = get_active_workspace()
    context["active_workspace"] = workspace
    context["documents_dir"] = workspace / "documents" if workspace else None

    if project:
        tasks = db.scalars(select(Task).where(Task.project_id == project.id).order_by(Task.created_at.desc())).all()
        documents = db.scalars(select(Document).where(Document.project_id == project.id).order_by(Document.created_at.desc())).all()
        all_events = db.scalars(select(Event).where(Event.project_id == project.id).order_by(Event.created_at.desc()).limit(300)).all()
        work_items = db.scalars(select(WorkItem).where(WorkItem.project_id == project.id).order_by(WorkItem.created_at.desc())).all()
        procurement_items = db.scalars(
            select(ProcurementItem).where(ProcurementItem.project_id == project.id).order_by(ProcurementItem.created_at.desc())
        ).all()
        risks = db.scalars(select(Risk).where(Risk.project_id == project.id).order_by(Risk.created_at.desc())).all()
        # Площадки и спецификации — основа управленческого контроля многоплощадочного проекта.
        sites = db.scalars(
            select(ProjectSite).where(ProjectSite.project_id == project.id).order_by(ProjectSite.order_index, ProjectSite.created_at)
        ).all()
        specifications = db.scalars(
            select(ProjectSpecification).where(ProjectSpecification.project_id == project.id).order_by(ProjectSpecification.created_at)
        ).all()
        # Позиции спецификаций — ручные записи оборудования/работ внутри каждой спецификации.
        spec_items = db.scalars(
            select(SpecificationItem).where(SpecificationItem.project_id == project.id).order_by(SpecificationItem.created_at)
        ).all()
        p3_cycles = get_p3_cycles(db, project.id)
        p3_summary = get_p3_summary(db, project.id)
        links = db.scalars(select(EntityLink).where(EntityLink.project_id == project.id).order_by(EntityLink.created_at.desc())).all()
        p3_activities = db.scalars(select(P3Activity).where(P3Activity.project_id == project.id).order_by(P3Activity.code)).all()
        agent_proposals = db.scalars(
            select(AgentProposal).where(AgentProposal.project_id == project.id).order_by(AgentProposal.created_at.desc())
        ).all()
        phases = db.scalars(select(ProjectPhase).where(ProjectPhase.project_id == project.id).order_by(ProjectPhase.order_index)).all()
        phase_model = phase_view_model(db, project.id, request.query_params.get("phase", ""))
        db.commit()
        phases = phase_model["phases"]

        budget_section = request.query_params.get("budget_section", "")
        budget_search = request.query_params.get("budget_search", "").strip()
        filtered_work_items = filter_work_items(work_items, budget_section, budget_search)

        procurement_status = request.query_params.get("status", "")
        procurement_group = request.query_params.get("group", "")
        procurement_manufacturer = request.query_params.get("manufacturer", "")
        procurement_sort = request.query_params.get("sort", "status")
        procurement_direction = request.query_params.get("direction", "asc")
        filtered_procurement = filter_procurement_items(procurement_items, procurement_status, procurement_group, procurement_manufacturer)

        risk_status = request.query_params.get("risk_status", "")
        risk_level = request.query_params.get("risk_level", "")
        risk_owner = request.query_params.get("risk_owner", "")
        filtered_risks = filter_risks(risks, risk_status, risk_level, risk_owner)

        event_type = request.query_params.get("event_type", "")
        event_entity = request.query_params.get("event_entity", "")
        event_source = request.query_params.get("event_source", "")
        events = filter_events(all_events, event_type, event_entity, event_source)[:50]

        link_entity = request.query_params.get("link_entity", "")
        link_relation = request.query_params.get("link_relation", "")

        p3_groups = []
        if active_tab == "p3":
            p3_groups = get_p3_groups(db, project.id)
            db.commit()

        link_targets = build_link_targets(tasks, documents, procurement_items, risks, p3_activities, phases)
        entity_labels = build_entity_labels(link_targets)
        graph_nodes = build_graph_nodes(link_targets, links, link_entity)
        graph_edges = build_graph_edges(links, entity_labels, graph_nodes, link_relation)

        context.update(
            {
                "tasks": tasks,
                "documents": documents,
                "documents_by_id": {item.id: item for item in documents},
                "events": events,
                "event_type": event_type,
                "event_entity": event_entity,
                "event_source": event_source,
                "event_types": sorted({item.event_type for item in all_events if item.event_type}),
                "event_entities": sorted({item.entity_type for item in all_events if item.entity_type}),
                "event_sources": sorted({item.source for item in all_events if item.source}),
                "work_items": filtered_work_items,
                "work_sections": sorted({item.section for item in work_items if item.section}),
                "work_totals": calculate_work_totals(filtered_work_items),
                "work_section_groups": group_work_items_by_section(filtered_work_items),
                "budget_section": budget_section,
                "budget_search": budget_search,
                "procurement_items": sort_procurement_items(filtered_procurement, procurement_sort, procurement_direction),
                "procurement_groups": sorted({item.group_name for item in procurement_items if item.group_name}),
                "procurement_manufacturers": sorted({item.manufacturer for item in procurement_items if item.manufacturer}),
                "procurement_sort": procurement_sort,
                "procurement_direction": procurement_direction,
                "procurement_status": procurement_status,
                "procurement_group": procurement_group,
                "procurement_manufacturer": procurement_manufacturer,
                "risks": filtered_risks,
                "risk_status": risk_status,
                "risk_level": risk_level,
                "risk_owner": risk_owner,
                "risk_statuses": sorted({item.status for item in risks if item.status}),
                "risk_levels": sorted({item.risk_level for item in risks if item.risk_level}),
                "risk_owners": sorted({item.owner for item in risks if item.owner}),
                "p3_groups": p3_groups,
                "p3_activities": p3_activities,
                "p3_cycles": p3_cycles,
                "p3_summary": p3_summary,
                "entity_links": links,
                "links_by_source": group_links_by_source(links),
                "link_targets": link_targets,
                "entity_labels": entity_labels,
                "link_views_by_source": build_link_views_by_source(links, entity_labels),
                "graph_nodes": graph_nodes,
                "graph_edges": graph_edges,
                "link_entity": link_entity,
                "link_relation": link_relation,
                "link_relations": sorted({item.relation_type for item in links if item.relation_type}),
                "p3_cycle_events": [event for event in all_events if event.entity_type == "p3_cycle"][:20],
                "agent_proposals": agent_proposals,
                "phases": phases,
                "phase_cards": phase_model["phase_cards"],
                "selected_phase": phase_model["selected_phase"],
                "selected_phase_inputs": phase_model["selected_phase_inputs"],
                "selected_phase_outputs": phase_model["selected_phase_outputs"],
                "selected_phase_dod": phase_model["selected_phase_dod"],
                "selected_phase_inputs_text": phase_model["selected_phase_inputs_text"],
                "selected_phase_outputs_text": phase_model["selected_phase_outputs_text"],
                "selected_phase_dod_text": phase_model["selected_phase_dod_text"],
                "selected_phase_audit": phase_model["selected_phase_audit"],
                "project_health": phase_model["project_health"],
                "phase_risks": phase_model["phase_risks"],
                # Площадки и спецификации
                "sites": sites,
                "specifications": specifications,
                "specs_by_site": _group_specs_by_site(specifications),
                "spec_items": spec_items,
                "items_by_spec": _group_items_by_spec(spec_items),
            }
        )

    return templates.TemplateResponse("project.html", context)


def build_empty_context(request: Request, projects: list[Project], project: Project | None, active_tab: str) -> dict:
    return {
        "request": request,
        "projects": projects,
        "project": project,
        "active_tab": active_tab,
        "active_workspace": None,
        "documents_dir": None,
        "tasks": [],
        "documents": [],
        "documents_by_id": {},
        "events": [],
        "event_type": "",
        "event_entity": "",
        "event_source": "",
        "event_types": [],
        "event_entities": [],
        "event_sources": [],
        "work_items": [],
        "work_sections": [],
        "work_totals": {"quantity": "0", "sum_no_vat": "0", "sum_with_vat": "0"},
        "work_section_groups": [],
        "budget_section": "",
        "budget_search": "",
        "procurement_items": [],
        "procurement_groups": [],
        "procurement_manufacturers": [],
        "procurement_sort": "status",
        "procurement_direction": "asc",
        "procurement_status": "",
        "procurement_group": "",
        "procurement_manufacturer": "",
        "risks": [],
        "risk_status": "",
        "risk_level": "",
        "risk_owner": "",
        "risk_statuses": [],
        "risk_levels": [],
        "risk_owners": [],
        "p3_groups": [],
        "p3_activities": [],
        "p3_cycles": [],
        "p3_summary": {"current_phase": "Не указана", "current_phase_code": "", "readiness_percent": "0", "cycle_title": "", "cycle_dates": ""},
        "entity_links": [],
        "links_by_source": {},
        "link_targets": [],
        "entity_labels": {},
        "link_views_by_source": {},
        "graph_nodes": [],
        "graph_edges": [],
        "link_entity": "",
        "link_relation": "",
        "link_relations": [],
        "p3_cycle_events": [],
        "agent_proposals": [],
        "phases": [],
        "phase_cards": [],
        "selected_phase": None,
        "selected_phase_inputs": [],
        "selected_phase_outputs": [],
        "selected_phase_dod": [],
        "selected_phase_inputs_text": "",
        "selected_phase_outputs_text": "",
        "selected_phase_dod_text": "",
        "selected_phase_audit": None,
        "project_health": [],
        "phase_risks": [],
        "health_options": [],
        "company_people": [],
        "company_people_names": [],
        "sites": [],
        "specifications": [],
        "specs_by_site": {},
        "spec_items": [],
        "items_by_spec": {},
    }


@router.get("/db-diagram")
def db_diagram(request: Request):
    return templates.TemplateResponse("db_diagram.html", {"request": request})


def sort_procurement_items(items: list[ProcurementItem], sort: str, direction: str) -> list[ProcurementItem]:
    # Сортировка закупок нужна для снабжения: статус показывает процесс, а группа сохраняет структуру шкафа/SCADA из Excel.
    status_order = {"В проработке": 0, "Оформлено": 1, "Поставляется": 2, "На складе": 3}
    reverse = direction == "desc"
    if sort == "name":
        key = lambda item: (item.name or "").lower()
    elif sort == "section":
        key = lambda item: (item.group_name or item.section or "", item.row_order or "", item.name or "")
    elif sort == "manufacturer":
        key = lambda item: (item.manufacturer or "", item.name or "")
    else:
        key = lambda item: (status_order.get(item.status, 99), item.name or "")
    return sorted(items, key=key, reverse=reverse)


def _to_float(value: str) -> float:
    cleaned = str(value or "").replace("\u00a0", "").replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _format_total(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def filter_work_items(items: list[WorkItem], section: str, search: str) -> list[WorkItem]:
    result = items
    if section:
        result = [item for item in result if item.section == section]
    if search:
        needle = search.lower()
        result = [
            item
            for item in result
            if needle in (item.name or "").lower()
            or needle in (item.group_name or "").lower()
            or needle in (item.source_file or "").lower()
        ]
    return result


def calculate_work_totals(items: list[WorkItem]) -> dict[str, str]:
    quantity = sum(_to_float(item.quantity) for item in items)
    sum_no_vat = sum(_to_float(item.sum_no_vat) for item in items)
    sum_with_vat = sum(_to_float(item.sum_with_vat) for item in items)
    return {
        "quantity": _format_total(quantity),
        "sum_no_vat": _format_total(sum_no_vat),
        "sum_with_vat": _format_total(sum_with_vat),
    }


def group_work_items_by_section(items: list[WorkItem]) -> list[dict]:
    grouped: dict[str, list[WorkItem]] = defaultdict(list)
    for item in items:
        grouped[item.section or "Без раздела"].append(item)
    return [
        {"section": section, "items": section_items, "totals": calculate_work_totals(section_items)}
        for section, section_items in sorted(grouped.items())
    ]


def filter_procurement_items(items: list[ProcurementItem], status: str, group: str, manufacturer: str) -> list[ProcurementItem]:
    result = items
    if status:
        result = [item for item in result if item.is_group_header or item.status == status]
    if group:
        result = [item for item in result if item.group_name == group]
    if manufacturer:
        result = [item for item in result if item.is_group_header or item.manufacturer == manufacturer]
    return result


def filter_risks(items: list[Risk], status: str, level: str, owner: str) -> list[Risk]:
    result = items
    if status:
        result = [item for item in result if item.status == status]
    if level:
        result = [item for item in result if item.risk_level == level]
    if owner:
        result = [item for item in result if item.owner == owner]
    return result


def filter_events(items: list[Event], event_type: str, entity_type: str, source: str) -> list[Event]:
    result = items
    if event_type:
        result = [item for item in result if item.event_type == event_type]
    if entity_type:
        result = [item for item in result if item.entity_type == entity_type]
    if source:
        result = [item for item in result if item.source == source]
    return result


def group_links_by_source(links: list[EntityLink]) -> dict[str, list[EntityLink]]:
    grouped: dict[str, list[EntityLink]] = defaultdict(list)
    for link in links:
        grouped[f"{link.source_type}:{link.source_id}"].append(link)
        grouped[f"{link.target_type}:{link.target_id}"].append(link)
    return grouped


def build_link_targets(
    tasks: list[Task],
    documents: list[Document],
    procurement_items: list[ProcurementItem],
    risks: list[Risk],
    p3_activities: list[P3Activity],
    phases: list[ProjectPhase] | None = None,
) -> list[dict[str, str]]:
    targets = []
    targets.extend({"type": "task", "id": item.id, "label": f"Задача: {item.title}"} for item in tasks)
    targets.extend({"type": "document", "id": item.id, "label": f"Документ: {item.title}"} for item in documents)
    targets.extend(
        {"type": "procurement", "id": item.id, "label": f"Закупка: {item.name}"}
        for item in procurement_items
        if not item.is_group_header
    )
    targets.extend({"type": "risk", "id": item.id, "label": f"Риск: {item.title}"} for item in risks)
    targets.extend({"type": "p3", "id": item.id, "label": f"P3: {item.code} {item.title}"} for item in p3_activities)
    targets.extend({"type": "phase", "id": item.id, "label": f"Фаза: {item.name}"} for item in phases or [])
    return targets


def build_entity_labels(targets: list[dict[str, str]]) -> dict[str, str]:
    # Карта человекочитаемых названий нужна UI и будущим агентам, чтобы связи не выглядели как сырые type/id.
    return {f"{target['type']}:{target['id']}": target["label"] for target in targets}


def build_link_views_by_source(links: list[EntityLink], entity_labels: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for link in links:
        source_key = f"{link.source_type}:{link.source_id}"
        target_key = f"{link.target_type}:{link.target_id}"
        grouped[source_key].append(
            {
                "id": link.id,
                "relation_type": link.relation_type,
                "other_label": entity_labels.get(target_key, target_key),
                "note": link.note,
            }
        )
        grouped[target_key].append(
            {
                "id": link.id,
                "relation_type": link.relation_type,
                "other_label": entity_labels.get(source_key, source_key),
                "note": link.note,
            }
        )
    return grouped


def build_graph_nodes(targets: list[dict[str, str]], links: list[EntityLink], selected_key: str = "") -> list[dict[str, str]]:
    connected_keys = set()
    for link in links:
        source_key = f"{link.source_type}:{link.source_id}"
        target_key = f"{link.target_type}:{link.target_id}"
        if selected_key and selected_key not in {source_key, target_key}:
            continue
        connected_keys.update({source_key, target_key})
    return [
        {**target, "key": f"{target['type']}:{target['id']}", "connected": f"{target['type']}:{target['id']}" in connected_keys}
        for target in targets
        if not selected_key or f"{target['type']}:{target['id']}" in connected_keys or f"{target['type']}:{target['id']}" == selected_key
    ]


def build_graph_edges(
    links: list[EntityLink],
    entity_labels: dict[str, str],
    nodes: list[dict[str, str]],
    relation: str = "",
) -> list[dict[str, str]]:
    node_keys = {node["key"] for node in nodes}
    edges = []
    for link in links:
        if relation and link.relation_type != relation:
            continue
        source_key = f"{link.source_type}:{link.source_id}"
        target_key = f"{link.target_type}:{link.target_id}"
        if source_key not in node_keys or target_key not in node_keys:
            continue
        edges.append(
            {
                "id": link.id,
                "source_key": source_key,
                "target_key": target_key,
                "source_label": entity_labels.get(source_key, source_key),
                "target_label": entity_labels.get(target_key, target_key),
                "relation_type": link.relation_type,
                "note": link.note,
            }
        )
    return edges


def _group_specs_by_site(specifications: list[ProjectSpecification]) -> dict[str, list[ProjectSpecification]]:
    """Группировка спецификаций по site_id для быстрого доступа из шаблона."""
    grouped: dict[str, list[ProjectSpecification]] = defaultdict(list)
    for spec in specifications:
        grouped[spec.site_id].append(spec)
    return grouped


def _group_items_by_spec(items: list[SpecificationItem]) -> dict[str, list[SpecificationItem]]:
    """Группировка позиций по specification_id для быстрого доступа из шаблона."""
    grouped: dict[str, list[SpecificationItem]] = defaultdict(list)
    for item in items:
        grouped[item.specification_id].append(item)
    return grouped

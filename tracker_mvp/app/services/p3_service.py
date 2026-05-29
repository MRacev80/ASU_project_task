from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import P3Activity, P3Cycle
from app.services.event_log import record_event
from app.services.p3_catalog import P3_GROUPS, flat_p3_items, project_links_for


P3_DONE_STATUS = "Выполнено"
P3_CYCLE_GROUPS = {"B", "C", "D", "E"}
P3_CYCLE_STATUSES = {"Планируется", "Активен", "Завершен"}


def ensure_p3_activities(db: Session, project_id: str) -> None:
    # P3.express хранит методическую часть в каталоге, а в БД проекта лежит только состояние выполнения.
    existing_codes = set(db.scalars(select(P3Activity.code).where(P3Activity.project_id == project_id)).all())
    for item in flat_p3_items():
        if item["code"] in existing_codes:
            continue
        db.add(
            P3Activity(
                project_id=project_id,
                code=item["code"],
                group_code=item["group_code"],
                group_title=item["group_title"],
                title=item["title"],
                purpose=item["purpose"],
                project_links=project_links_for(item["code"]),
            )
        )
    db.flush()


def get_p3_groups(db: Session, project_id: str) -> list[dict]:
    ensure_p3_activities(db, project_id)
    activities = db.scalars(select(P3Activity).where(P3Activity.project_id == project_id).order_by(P3Activity.code)).all()
    by_group = {group["code"]: {**group, "activities": []} for group in P3_GROUPS}
    for activity in activities:
        activity.is_overdue = is_overdue(activity.next_due_at, activity.status)
        by_group[activity.group_code]["activities"].append(activity)

    groups = []
    for group in by_group.values():
        activities = group["activities"]
        done_count = sum(1 for activity in activities if activity.status == P3_DONE_STATUS)
        group["done_count"] = done_count
        group["total_count"] = len(activities)
        group["is_done"] = bool(activities) and done_count == len(activities)
        group["is_cycle"] = group["code"] in P3_CYCLE_GROUPS
        groups.append(group)
    return groups


def get_p3_cycles(db: Session, project_id: str) -> list[P3Cycle]:
    cycles = db.scalars(select(P3Cycle).where(P3Cycle.project_id == project_id).order_by(P3Cycle.start_date, P3Cycle.cycle_number)).all()
    for cycle in cycles:
        cycle.is_overdue = is_overdue(cycle.end_date, cycle.status)
    return cycles


def get_p3_summary(db: Session, project_id: str) -> dict[str, str]:
    groups = get_p3_groups(db, project_id)
    current_group = next((group for group in groups if not group["is_done"]), groups[-1] if groups else None)
    active_cycle = get_active_cycle(db, project_id)
    done = sum(group["done_count"] for group in groups)
    total = sum(group["total_count"] for group in groups)
    readiness = round(done * 100 / total) if total else 0
    return {
        "current_phase": current_group["title"] if current_group else "Не указана",
        "current_phase_code": current_group["code"] if current_group else "",
        "readiness_percent": str(readiness),
        "cycle_title": active_cycle.title if active_cycle else "",
        "cycle_dates": format_cycle_dates(active_cycle) if active_cycle else "",
    }


def get_active_cycle(db: Session, project_id: str) -> P3Cycle | None:
    cycles = get_p3_cycles(db, project_id)
    if not cycles:
        return None
    today = date.today().isoformat()
    active = [cycle for cycle in cycles if cycle.status == "Активен"]
    if active:
        return active[0]
    by_date = [cycle for cycle in cycles if cycle.start_date and cycle.end_date and cycle.start_date <= today <= cycle.end_date]
    if by_date:
        return by_date[0]
    planned = [cycle for cycle in cycles if cycle.status != "Завершен"]
    return planned[0] if planned else cycles[-1]


def format_cycle_dates(cycle: P3Cycle) -> str:
    if cycle.start_date and cycle.end_date:
        return f"{cycle.start_date} - {cycle.end_date}"
    if cycle.start_date and cycle.duration_days:
        return f"{cycle.start_date}, {cycle.duration_days} дн."
    return cycle.start_date or cycle.end_date or ""


def calculate_end_date(start_date: str, duration_days: str) -> str:
    if not start_date or not duration_days:
        return ""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        duration = int(duration_days)
    except ValueError:
        return ""
    return (start + timedelta(days=max(duration - 1, 0))).isoformat()


def is_overdue(value: str, status: str) -> bool:
    # Просрочка нужна как управленческий сигнал: завершенные элементы не подсвечиваются, даже если дата уже прошла.
    if not value or status in {P3_DONE_STATUS, "Завершен", "Пропущено"}:
        return False
    try:
        due_date = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return False
    return due_date < date.today()


def update_p3_activity(
    db: Session,
    *,
    activity_id: str,
    status: str,
    owner: str,
    last_done_at: str,
    next_due_at: str,
    notes: str,
) -> P3Activity | None:
    activity = db.get(P3Activity, activity_id)
    if not activity:
        return None

    before = {
        "status": activity.status,
        "owner": activity.owner,
        "last_done_at": activity.last_done_at,
        "next_due_at": activity.next_due_at,
    }
    activity.status = status
    activity.owner = owner
    activity.last_done_at = last_done_at
    activity.next_due_at = next_due_at
    activity.notes = notes
    record_event(
        db,
        project_id=activity.project_id,
        event_type="p3.updated",
        entity_type="p3_activity",
        entity_id=activity.id,
        description=f"Обновлено действие P3.express {activity.code}: {activity.status}",
        before_state=before,
        after_state={
            "status": activity.status,
            "owner": activity.owner,
            "last_done_at": activity.last_done_at,
            "next_due_at": activity.next_due_at,
        },
    )
    return activity


def create_or_update_cycle(
    db: Session,
    *,
    project_id: str,
    title: str,
    cycle_number: str,
    start_date: str,
    end_date: str,
    duration_days: str,
    status: str,
    notes: str,
    cycle_id: str = "",
) -> P3Cycle:
    cycle = db.get(P3Cycle, cycle_id) if cycle_id else None
    if not end_date:
        end_date = calculate_end_date(start_date, duration_days)
    if not duration_days and start_date and end_date:
        duration_days = calculate_duration_days(start_date, end_date)

    if cycle is None:
        cycle = P3Cycle(project_id=project_id, title=title)
        db.add(cycle)
        event_type = "p3_cycle.created"
    else:
        event_type = "p3_cycle.updated"

    before = cycle_state(cycle)
    cycle.title = title
    cycle.cycle_number = cycle_number
    cycle.start_date = start_date
    cycle.end_date = end_date
    cycle.duration_days = duration_days
    cycle.status = status if status in P3_CYCLE_STATUSES else "Планируется"
    cycle.notes = notes
    db.flush()
    record_event(
        db,
        project_id=project_id,
        event_type=event_type,
        entity_type="p3_cycle",
        entity_id=cycle.id,
        description=f"Обновлен цикл P3.express: {cycle.title}",
        before_state=before,
        after_state=cycle_state(cycle),
    )
    return cycle


def calculate_duration_days(start_date: str, end_date: str) -> str:
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return ""
    return str((end - start).days + 1)


def cycle_state(cycle: P3Cycle | None) -> dict[str, str]:
    if cycle is None:
        return {}
    return {
        "title": cycle.title,
        "cycle_number": cycle.cycle_number,
        "start_date": cycle.start_date,
        "end_date": cycle.end_date,
        "duration_days": cycle.duration_days,
        "status": cycle.status,
    }

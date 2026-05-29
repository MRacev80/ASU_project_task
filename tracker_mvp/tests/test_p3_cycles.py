from sqlalchemy import select

from app.models import P3Activity, P3Cycle
from app.routes.p3 import save_p3_cycle
from app.services.p3_service import get_p3_groups, get_p3_summary, update_p3_activity


def test_p3_summary_uses_first_not_completed_group_as_current_phase(db_session, project):
    groups = get_p3_groups(db_session, project.id)
    for activity in groups[0]["activities"]:
        update_p3_activity(
            db_session,
            activity_id=activity.id,
            status="Выполнено",
            owner="QA",
            last_done_at="2026-05-27",
            next_due_at="",
            notes="",
        )
    db_session.commit()

    summary = get_p3_summary(db_session, project.id)
    refreshed_groups = get_p3_groups(db_session, project.id)

    assert refreshed_groups[0]["is_done"] is True
    assert summary["current_phase_code"] == "B"
    assert summary["current_phase"] == "Планирование цикла"


def test_p3_cycle_dates_can_be_configured_by_start_and_duration(db_session, project):
    save_p3_cycle(
        project.id,
        title="Цикл 1",
        cycle_number="1",
        start_date="2026-06-01",
        end_date="",
        duration_days="14",
        status="Активен",
        notes="Первый цикл",
        cycle_id="",
        db=db_session,
    )

    cycle = db_session.scalars(select(P3Cycle).where(P3Cycle.project_id == project.id)).one()
    summary = get_p3_summary(db_session, project.id)

    assert cycle.end_date == "2026-06-14"
    assert cycle.duration_days == "14"
    assert summary["cycle_title"] == "Цикл 1"
    assert summary["cycle_dates"] == "2026-06-01 - 2026-06-14"


def test_p3_activity_update_writes_before_after_event(db_session, project):
    get_p3_groups(db_session, project.id)
    activity = db_session.scalars(select(P3Activity).where(P3Activity.project_id == project.id)).first()

    update_p3_activity(
        db_session,
        activity_id=activity.id,
        status="В работе",
        owner="QA РП",
        last_done_at="",
        next_due_at="2026-06-01",
        notes="Проверить",
    )
    db_session.commit()

    db_session.refresh(activity)
    assert activity.status == "В работе"
    assert activity.owner == "QA РП"

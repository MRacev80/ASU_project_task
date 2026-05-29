from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.p3_service import create_or_update_cycle, update_p3_activity


router = APIRouter()


@router.post("/p3/{activity_id}")
def update_p3_activity_route(
    activity_id: str,
    status: str = Form("Не начато"),
    owner: str = Form(""),
    last_done_at: str = Form(""),
    next_due_at: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    activity = update_p3_activity(
        db,
        activity_id=activity_id,
        status=status,
        owner=owner,
        last_done_at=last_done_at,
        next_due_at=next_due_at,
        notes=notes,
    )
    db.commit()
    if not activity:
        return RedirectResponse(url="/", status_code=303)
    return RedirectResponse(url=f"/projects/{activity.project_id}/p3", status_code=303)


@router.post("/projects/{project_id}/p3/cycles")
def save_p3_cycle(
    project_id: str,
    title: str = Form(...),
    cycle_number: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    duration_days: str = Form(""),
    status: str = Form("Планируется"),
    notes: str = Form(""),
    cycle_id: str = Form(""),
    db: Session = Depends(get_db),
):
    # Циклы P3 задаются отдельно от чек-листа: чек-лист описывает управленческие действия, цикл задает временные рамки.
    create_or_update_cycle(
        db,
        project_id=project_id,
        title=title,
        cycle_number=cycle_number,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration_days,
        status=status,
        notes=notes,
        cycle_id=cycle_id,
    )
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}/p3", status_code=303)

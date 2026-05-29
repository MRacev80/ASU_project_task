from datetime import date, datetime

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Task
from app.services.event_log import record_event


router = APIRouter()

TASK_STATUSES = ["Бэклог", "В работе", "Тестируется", "Готово", "Заблокировано"]


@router.get("/api/projects/{project_id}/tasks")
def list_tasks(project_id: str, db: Session = Depends(get_db)):
    tasks = db.scalars(select(Task).where(Task.project_id == project_id).order_by(Task.created_at.desc())).all()
    return [
        {
            "id": task.id,
            "title": task.title,
            "type": task.type,
            "status": task.status,
            "priority": task.priority,
            "assignee": task.assignee,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        }
        for task in tasks
    ]


@router.get("/api/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        return {"error": "task not found"}
    return {
        "id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "description": task.description,
        "type": task.type,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "assignee": task.assignee,
        "result": task.result,
        "blocked_reason": task.blocked_reason,
    }


@router.post("/projects/{project_id}/tasks")
def create_task(
    project_id: str,
    title: str = Form(...),
    description: str = Form(""),
    type: str = Form("работа"),
    priority: str = Form("Средний"),
    due_date: str = Form(""),
    assignee: str = Form(""),
    db: Session = Depends(get_db),
):
    description = description if isinstance(description, str) else ""
    type = type if isinstance(type, str) else "работа"
    priority = priority if isinstance(priority, str) else "Средний"
    assignee = assignee if isinstance(assignee, str) else ""
    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        type=type,
        status="Бэклог",
        priority=priority,
        due_date=parse_due_date(due_date),
        assignee=assignee,
    )
    db.add(task)
    db.flush()
    record_event(
        db,
        project_id=project_id,
        event_type="task.created",
        entity_type="task",
        entity_id=task.id,
        description=f"Создана задача: {task.title}",
        after_state={"title": task.title, "status": task.status, "assignee": task.assignee},
    )
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}/tasks", status_code=303)


@router.post("/tasks/{task_id}/status")
def change_task_status(task_id: str, status: str = Form(...), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        return RedirectResponse(url="/", status_code=303)
    old_status = task.status
    task.status = status if status in TASK_STATUSES else task.status
    record_event(
        db,
        project_id=task.project_id,
        event_type="task.status_changed",
        entity_type="task",
        entity_id=task.id,
        description=f"Статус задачи изменен: {old_status} -> {task.status}",
        before_state={"status": old_status},
        after_state={"status": task.status},
    )
    db.commit()
    return RedirectResponse(url=f"/projects/{task.project_id}/tasks", status_code=303)


def parse_due_date(value: str | date) -> date | None:
    # HTML date input отправляет пустую строку, если срок не выбран; ее нельзя отдавать FastAPI как date напрямую.
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None

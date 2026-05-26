from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, Event, Project, Task
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
    valid_tabs = {"main", "tasks", "budget", "procurement", "documents", "risks", "p3", "events", "agents"}
    if active_tab not in valid_tabs:
        active_tab = "main"

    tasks = []
    documents = []
    events = []
    workspace = get_active_workspace()
    if project:
        tasks = db.scalars(select(Task).where(Task.project_id == project.id).order_by(Task.created_at.desc())).all()
        documents = db.scalars(
            select(Document).where(Document.project_id == project.id).order_by(Document.created_at.desc())
        ).all()
        events = db.scalars(select(Event).where(Event.project_id == project.id).order_by(Event.created_at.desc()).limit(20)).all()

    return templates.TemplateResponse(
        "project.html",
        {
            "request": request,
            "projects": projects,
            "project": project,
            "active_tab": active_tab,
            "active_workspace": workspace,
            "tasks": tasks,
            "documents": documents,
            "events": events,
        },
    )


@router.get("/db-diagram")
def db_diagram(request: Request):
    return templates.TemplateResponse("db_diagram.html", {"request": request})

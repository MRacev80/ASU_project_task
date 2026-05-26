from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Project
from app.services.event_log import record_event


router = APIRouter()


@router.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).order_by(Project.created_at.desc())).all()
    return [
        {
            "id": project.id,
            "name": project.name,
            "customer": project.customer,
            "status": project.status,
            "stage": project.stage,
        }
        for project in projects
    ]


@router.get("/api/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        return {"error": "project not found"}
    return {
        "id": project.id,
        "name": project.name,
        "customer": project.customer,
        "automation_object": project.automation_object,
        "stage": project.stage,
        "status": project.status,
        "project_manager": project.project_manager,
        "documents_path": project.documents_path,
        "description": project.description,
    }


@router.post("/projects")
def create_project(
    name: str = Form(...),
    customer: str = Form(""),
    automation_object: str = Form(""),
    project_manager: str = Form(""),
    documents_path: str = Form(""),
    db: Session = Depends(get_db),
):
    project = Project(
        name=name,
        customer=customer,
        automation_object=automation_object,
        project_manager=project_manager,
        documents_path=documents_path,
    )
    db.add(project)
    db.flush()
    record_event(
        db,
        project_id=project.id,
        event_type="project.created",
        entity_type="project",
        entity_id=project.id,
        description=f"Создан проект: {project.name}",
    )
    db.commit()
    return RedirectResponse(url=f"/projects/{project.id}", status_code=303)


@router.post("/projects/{project_id}")
def update_project(
    project_id: str,
    name: str = Form(...),
    customer: str = Form(""),
    automation_object: str = Form(""),
    stage: str = Form(""),
    status: str = Form("В работе"),
    project_manager: str = Form(""),
    documents_path: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        return RedirectResponse(url="/", status_code=303)

    project.name = name
    project.customer = customer
    project.automation_object = automation_object
    project.stage = stage
    project.status = status
    project.project_manager = project_manager
    project.documents_path = documents_path
    project.description = description
    record_event(
        db,
        project_id=project.id,
        event_type="project.updated",
        entity_type="project",
        entity_id=project.id,
        description=f"Обновлен проект: {project.name}",
    )
    db.commit()
    return RedirectResponse(url=f"/projects/{project.id}", status_code=303)

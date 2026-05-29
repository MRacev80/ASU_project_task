from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, EntityLink, Event, P3Activity, P3Cycle, ProcurementItem, Project, Risk, Task, WorkItem
from app.services.event_log import record_event
from app.workspace import get_active_workspace


router = APIRouter()


def get_workspace_documents_path() -> str:
    workspace = get_active_workspace()
    if not workspace:
        return ""
    return str(workspace / "documents")


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
        "project_code": project.project_code,
        "name": project.name,
        "customer": project.customer,
        "automation_object": project.automation_object,
        "contract_number": project.contract_number,
        "stage": project.stage,
        "current_milestone": project.current_milestone,
        "start_plan": project.start_plan,
        "finish_plan": project.finish_plan,
        "start_fact": project.start_fact,
        "finish_fact": project.finish_fact,
        "readiness_percent": project.readiness_percent,
        "contract_amount": project.contract_amount,
        "budget_plan": project.budget_plan,
        "budget_actual": project.budget_actual,
        "status": project.status,
        "project_manager": project.project_manager,
        "designer": project.designer,
        "programmer": project.programmer,
        "kip_master": project.kip_master,
        "documents_path": project.documents_path,
        "description": project.description,
    }


@router.post("/projects")
def create_project(
    name: str = Form(...),
    project_code: str = Form(""),
    customer: str = Form(""),
    automation_object: str = Form(""),
    contract_number: str = Form(""),
    project_manager: str = Form(""),
    db: Session = Depends(get_db),
):
    project = Project(
        project_code=project_code,
        name=name,
        customer=customer,
        automation_object=automation_object,
        contract_number=contract_number,
        project_manager=project_manager,
        documents_path=get_workspace_documents_path(),
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
    project_code: str = Form(""),
    customer: str = Form(""),
    automation_object: str = Form(""),
    contract_number: str = Form(""),
    stage: str = Form(""),
    status: str = Form("В работе"),
    current_milestone: str = Form(""),
    start_plan: str = Form(""),
    finish_plan: str = Form(""),
    start_fact: str = Form(""),
    finish_fact: str = Form(""),
    readiness_percent: str = Form(""),
    contract_amount: str = Form(""),
    budget_plan: str = Form(""),
    budget_actual: str = Form(""),
    project_manager: str = Form(""),
    designer: str = Form(""),
    programmer: str = Form(""),
    kip_master: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        return RedirectResponse(url="/", status_code=303)

    project.project_code = project_code
    project.name = name
    project.customer = customer
    project.automation_object = automation_object
    project.contract_number = contract_number
    project.stage = stage
    project.status = status
    project.current_milestone = current_milestone
    project.start_plan = start_plan
    project.finish_plan = finish_plan
    project.start_fact = start_fact
    project.finish_fact = finish_fact
    project.readiness_percent = readiness_percent
    project.contract_amount = contract_amount
    project.budget_plan = budget_plan
    project.budget_actual = budget_actual
    project.project_manager = project_manager
    project.designer = designer
    project.programmer = programmer
    project.kip_master = kip_master
    project.documents_path = get_workspace_documents_path()
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


@router.post("/projects/{project_id}/delete")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        return RedirectResponse(url="/", status_code=303)

    db.execute(delete(Task).where(Task.project_id == project_id))
    db.execute(delete(Document).where(Document.project_id == project_id))
    db.execute(delete(WorkItem).where(WorkItem.project_id == project_id))
    db.execute(delete(ProcurementItem).where(ProcurementItem.project_id == project_id))
    db.execute(delete(P3Activity).where(P3Activity.project_id == project_id))
    db.execute(delete(P3Cycle).where(P3Cycle.project_id == project_id))
    db.execute(delete(Risk).where(Risk.project_id == project_id))
    db.execute(delete(EntityLink).where(EntityLink.project_id == project_id))
    db.execute(delete(Event).where(Event.project_id == project_id))
    db.delete(project)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

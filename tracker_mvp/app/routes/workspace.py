from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from sqlalchemy import select

from app.db import get_session_local, init_db
from app.models import Project
from app.templates import templates
from app.workspace import create_workspace, get_active_workspace, open_workspace


router = APIRouter()


@router.get("/workspace")
def workspace_page(request: Request, error: str = ""):
    return templates.TemplateResponse(
        "workspace.html",
        {
            "request": request,
            "active_workspace": get_active_workspace(),
            "error": error,
        },
    )


@router.post("/workspace/create")
def create_workspace_route(
    path: str = Form(...),
    project_name: str = Form(...),
    customer: str = Form(""),
    automation_object: str = Form(""),
):
    try:
        workspace = create_workspace(path, project_name=project_name, customer=customer, automation_object=automation_object)
        init_db()
        session = get_session_local()()
        try:
            existing_project = session.scalars(select(Project)).first()
            if not existing_project:
                project = Project(
                    name=project_name,
                    customer=customer,
                    automation_object=automation_object,
                    documents_path=str(workspace / "documents"),
                )
                session.add(project)
                session.commit()
        finally:
            session.close()
        return RedirectResponse(url="/", status_code=303)
    except Exception as exc:
        return RedirectResponse(url=f"/workspace?error={exc}", status_code=303)


@router.post("/workspace/open")
def open_workspace_route(path: str = Form(...)):
    try:
        open_workspace(path)
        init_db()
        return RedirectResponse(url="/", status_code=303)
    except Exception as exc:
        return RedirectResponse(url=f"/workspace?error={exc}", status_code=303)

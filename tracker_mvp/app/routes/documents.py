from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document
from app.services.event_log import record_event


router = APIRouter()


@router.get("/api/projects/{project_id}/documents")
def list_documents(project_id: str, db: Session = Depends(get_db)):
    documents = db.scalars(select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())).all()
    return [
        {
            "id": document.id,
            "title": document.title,
            "type": document.type,
            "file_path": document.file_path,
            "status": document.status,
            "summary": document.summary,
        }
        for document in documents
    ]


@router.post("/projects/{project_id}/documents")
def create_document(
    project_id: str,
    title: str = Form(...),
    type: str = Form("прочий документ"),
    file_path: str = Form(""),
    summary: str = Form(""),
    db: Session = Depends(get_db),
):
    document = Document(
        project_id=project_id,
        title=title,
        type=type,
        file_path=file_path,
        summary=summary,
    )
    db.add(document)
    db.flush()
    record_event(
        db,
        project_id=project_id,
        event_type="document.created",
        entity_type="document",
        entity_id=document.id,
        description=f"Добавлен документ: {document.title}",
    )
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

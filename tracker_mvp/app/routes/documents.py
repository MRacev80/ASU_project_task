from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, ProcurementItem, ProjectSpecification, WorkItem
from app.services.calculation_import import parse_calculation
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
    exists = Path(file_path).expanduser().exists() if file_path else True
    document = Document(
        project_id=project_id,
        title=title,
        type=type,
        file_path=file_path,
        status="Активный" if exists else "Отсутствует",
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
        after_state={"title": document.title, "status": document.status, "file_path": document.file_path},
    )
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}/documents", status_code=303)


@router.post("/projects/{project_id}/calculation-import")
def import_calculation(
    project_id: str,
    file_path: str = Form(...),
    site_id: str = Form(""),
    work_specification_id: str = Form(""),
    equipment_specification_id: str = Form(""),
    db: Session = Depends(get_db),
):
    # Расчёт КП/СС является источником для производных строк работ и закупок.
    # При повторном импорте строки пересоздаются из исходного Excel-файла.
    # Если указана площадка / спецификация, строки привязываются к ней,
    # что позволяет отслеживать состояние по каждой площадке отдельно.
    try:
        imported = parse_calculation(file_path)
    except (FileNotFoundError, ValueError) as exc:
        # Ошибка импорта должна быть пользовательской и не должна портить уже импортированные строки.
        message = quote(str(exc))
        return RedirectResponse(url=f"/projects/{project_id}/documents?error={message}", status_code=303)

    source_file = str(Path(file_path).expanduser().resolve())
    existing_statuses = {
        (item.name, item.catalog_number): item.status
        for item in db.scalars(
            select(ProcurementItem).where(ProcurementItem.project_id == project_id, ProcurementItem.source_file == source_file)
        ).all()
    }

    db.execute(delete(WorkItem).where(WorkItem.project_id == project_id, WorkItem.source_file == source_file))
    db.execute(delete(ProcurementItem).where(ProcurementItem.project_id == project_id, ProcurementItem.source_file == source_file))

    # Привязываем строки работ к спецификации работ, если она указана.
    for item in imported["works"]:
        db.add(WorkItem(
            project_id=project_id,
            site_id=site_id,
            specification_id=work_specification_id,
            **item,
        ))

    # Привязываем закупки к спецификации оборудования, если она указана.
    for item in imported["procurement"]:
        item["status"] = existing_statuses.get((item["name"], item["catalog_number"]), "В проработке")
        db.add(ProcurementItem(
            project_id=project_id,
            site_id=site_id,
            specification_id=equipment_specification_id,
            **item,
        ))

    # Обновляем source_file в спецификациях, если переданы их ID.
    for spec_id in [work_specification_id, equipment_specification_id]:
        if spec_id:
            spec = db.get(ProjectSpecification, spec_id)
            if spec:
                spec.source_file = source_file

    record_event(
        db,
        project_id=project_id,
        event_type="calculation.imported",
        entity_type="document",
        entity_id=project_id,
        description=f"Импортирован расчет: {len(imported['works'])} работ, {len(imported['procurement'])} позиций закупок",
        after_state={
            "source_file": source_file,
            "site_id": site_id,
            "works": len(imported["works"]),
            "procurement": len(imported["procurement"]),
        },
    )
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}/documents", status_code=303)

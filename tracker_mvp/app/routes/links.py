from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import EntityLink
from app.services.event_log import record_event


router = APIRouter()


@router.post("/projects/{project_id}/links")
def create_entity_link(
    project_id: str,
    source_type: str = Form(...),
    source_id: str = Form(...),
    target_type: str = Form(""),
    target_id: str = Form(""),
    target_ref: str = Form(""),
    relation_type: str = Form("связано"),
    note: str = Form(""),
    return_tab: str = Form("tasks"),
    db: Session = Depends(get_db),
):
    target_type = target_type if isinstance(target_type, str) else ""
    target_id = target_id if isinstance(target_id, str) else ""
    target_ref = target_ref if isinstance(target_ref, str) else ""
    relation_type = relation_type if isinstance(relation_type, str) else "связано"
    note = note if isinstance(note, str) else ""
    return_tab = return_tab if isinstance(return_tab, str) else "tasks"

    if target_ref and ":" in target_ref:
        target_type, target_id = target_ref.split(":", 1)
    if not target_type or not target_id or (source_type == target_type and source_id == target_id):
        return RedirectResponse(url=f"/projects/{project_id}/{return_tab}", status_code=303)

    # Универсальная связь не навязывает бизнес-правила: она только фиксирует граф проекта для UI и будущего агента.
    link = EntityLink(
        project_id=project_id,
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        relation_type=relation_type,
        note=note,
    )
    db.add(link)
    db.flush()
    record_event(
        db,
        project_id=project_id,
        event_type="entity_link.created",
        entity_type="entity_link",
        entity_id=link.id,
        description=f"Создана связь: {source_type}:{source_id} -> {target_type}:{target_id}",
        after_state={
            "source_type": source_type,
            "source_id": source_id,
            "target_type": target_type,
            "target_id": target_id,
            "relation_type": relation_type,
        },
    )
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}/{return_tab}", status_code=303)


@router.post("/links/{link_id}/delete")
def delete_entity_link(link_id: str, return_tab: str = Form("tasks"), db: Session = Depends(get_db)):
    link = db.get(EntityLink, link_id)
    if not link:
        return RedirectResponse(url="/", status_code=303)

    project_id = link.project_id
    before_state = {
        "source_type": link.source_type,
        "source_id": link.source_id,
        "target_type": link.target_type,
        "target_id": link.target_id,
        "relation_type": link.relation_type,
    }
    db.delete(link)
    record_event(
        db,
        project_id=project_id,
        event_type="entity_link.deleted",
        entity_type="entity_link",
        entity_id=link_id,
        description="Удалена связь сущностей",
        before_state=before_state,
    )
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}/{return_tab}", status_code=303)

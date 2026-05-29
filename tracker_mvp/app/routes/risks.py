from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Risk
from app.services.event_log import record_event
from app.services.risk_service import calculate_risk_score


router = APIRouter()

RISK_STATUSES = {"Открыт", "В работе", "Снижен", "Закрыт"}


def _redirect_to_risks(project_id: str) -> RedirectResponse:
    return RedirectResponse(url=f"/projects/{project_id}/risks", status_code=303)


def _risk_state(risk: Risk) -> dict[str, str]:
    return {
        "title": risk.title,
        "probability": risk.probability,
        "impact": risk.impact,
        "risk_score": risk.risk_score,
        "risk_level": risk.risk_level,
        "status": risk.status,
        "owner": risk.owner,
    }


@router.post("/projects/{project_id}/risks")
def create_risk(
    project_id: str,
    title: str = Form(...),
    description: str = Form(""),
    probability: str = Form(""),
    impact: str = Form(""),
    mitigation: str = Form(""),
    owner: str = Form(""),
    status: str = Form("Открыт"),
    linked_entity_type: str = Form(""),
    linked_entity_id: str = Form(""),
    db: Session = Depends(get_db),
):
    risk_score, risk_level = calculate_risk_score(probability, impact)
    risk = Risk(
        project_id=project_id,
        title=title,
        description=description,
        probability=probability,
        impact=impact,
        risk_score=risk_score,
        risk_level=risk_level,
        mitigation=mitigation,
        owner=owner,
        status=status if status in RISK_STATUSES else "Открыт",
        linked_entity_type=linked_entity_type,
        linked_entity_id=linked_entity_id,
    )
    db.add(risk)
    db.flush()
    record_event(
        db,
        project_id=project_id,
        event_type="risk.created",
        entity_type="risk",
        entity_id=risk.id,
        description=f"Добавлен риск: {risk.title}",
        after_state=_risk_state(risk),
    )
    db.commit()
    return _redirect_to_risks(project_id)


@router.post("/risks/{risk_id}/update")
def update_risk(
    risk_id: str,
    title: str = Form(...),
    description: str = Form(""),
    probability: str = Form(""),
    impact: str = Form(""),
    mitigation: str = Form(""),
    owner: str = Form(""),
    status: str = Form("Открыт"),
    linked_entity_type: str = Form(""),
    linked_entity_id: str = Form(""),
    db: Session = Depends(get_db),
):
    risk = db.get(Risk, risk_id)
    if not risk:
        return RedirectResponse(url="/", status_code=303)

    before = _risk_state(risk)
    risk_score, risk_level = calculate_risk_score(probability, impact)
    risk.title = title
    risk.description = description
    risk.probability = probability
    risk.impact = impact
    risk.risk_score = risk_score
    risk.risk_level = risk_level
    risk.mitigation = mitigation
    risk.owner = owner
    risk.status = status if status in RISK_STATUSES else "Открыт"
    risk.linked_entity_type = linked_entity_type
    risk.linked_entity_id = linked_entity_id
    record_event(
        db,
        project_id=risk.project_id,
        event_type="risk.updated",
        entity_type="risk",
        entity_id=risk.id,
        description=f"Обновлен риск: {risk.title}",
        before_state=before,
        after_state=_risk_state(risk),
    )
    db.commit()
    return _redirect_to_risks(risk.project_id)


@router.post("/risks/{risk_id}/delete")
def delete_risk(risk_id: str, db: Session = Depends(get_db)):
    risk = db.get(Risk, risk_id)
    if not risk:
        return RedirectResponse(url="/", status_code=303)

    project_id = risk.project_id
    title = risk.title
    before = _risk_state(risk)
    db.delete(risk)
    record_event(
        db,
        project_id=project_id,
        event_type="risk.deleted",
        entity_type="risk",
        entity_id=risk_id,
        description=f"Удален риск: {title}",
        before_state=before,
    )
    db.commit()
    return _redirect_to_risks(project_id)

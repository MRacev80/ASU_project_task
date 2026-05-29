import json

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ProjectPhase, TechnicalAudit
from app.services.event_log import record_event
from app.services.phase_service import (
    GATE_STATUSES,
    HEALTH_VALUES,
    PHASE_STATUSES,
    clamp_percent,
    normalize_choice,
    parse_items_text,
    phase_state,
    today_string,
)


router = APIRouter()


def _redirect_to_phase(project_id: str, phase_id: str) -> RedirectResponse:
    return RedirectResponse(url=f"/projects/{project_id}/phases?phase={phase_id}", status_code=303)


@router.post("/phases/{phase_id}")
def update_phase(
    phase_id: str,
    status: str = Form("Не начато"),
    health: str = Form("gray"),
    schedule_health: str = Form("gray"),
    technical_health: str = Form("gray"),
    risk_health: str = Form("gray"),
    procurement_health: str = Form("gray"),
    documentation_health: str = Form("gray"),
    testing_health: str = Form("gray"),
    progress_percent: str = Form("0"),
    start_plan: str = Form(""),
    finish_plan: str = Form(""),
    start_fact: str = Form(""),
    finish_fact: str = Form(""),
    project_manager: str = Form(""),
    technical_lead: str = Form(""),
    summary: str = Form(""),
    inputs_text: str = Form(""),
    outputs_text: str = Form(""),
    dod_text: str = Form(""),
    gate_status: str = Form("Не готов"),
    gate_comment: str = Form(""),
    db: Session = Depends(get_db),
):
    phase = db.get(ProjectPhase, phase_id)
    if not phase:
        return RedirectResponse(url="/", status_code=303)

    before = phase_state(phase)
    phase.status = normalize_choice(status, PHASE_STATUSES, "Не начато")
    phase.health = normalize_choice(health, HEALTH_VALUES, "gray")
    phase.schedule_health = normalize_choice(schedule_health, HEALTH_VALUES, "gray")
    phase.technical_health = normalize_choice(technical_health, HEALTH_VALUES, "gray")
    phase.risk_health = normalize_choice(risk_health, HEALTH_VALUES, "gray")
    phase.procurement_health = normalize_choice(procurement_health, HEALTH_VALUES, "gray")
    phase.documentation_health = normalize_choice(documentation_health, HEALTH_VALUES, "gray")
    phase.testing_health = normalize_choice(testing_health, HEALTH_VALUES, "gray")
    phase.progress_percent = clamp_percent(progress_percent)
    phase.start_plan = start_plan
    phase.finish_plan = finish_plan
    phase.start_fact = start_fact
    phase.finish_fact = finish_fact
    phase.project_manager = project_manager
    phase.technical_lead = technical_lead
    phase.summary = summary
    # В первой версии входы/выходы/DoD храним JSON-списками: это быстрее для MVP и не ломает будущую нормализацию.
    phase.inputs = json.dumps(parse_items_text(inputs_text), ensure_ascii=False)
    phase.outputs = json.dumps(parse_items_text(outputs_text), ensure_ascii=False)
    phase.definition_of_done = json.dumps(parse_items_text(dod_text, checklist=True), ensure_ascii=False)
    phase.gate_status = normalize_choice(gate_status, GATE_STATUSES, "Не готов")
    phase.gate_comment = gate_comment
    record_event(
        db,
        project_id=phase.project_id,
        event_type="phase.updated",
        entity_type="phase",
        entity_id=phase.id,
        description=f"Обновлена фаза: {phase.name}",
        before_state=before,
        after_state=phase_state(phase),
    )
    db.commit()
    return _redirect_to_phase(phase.project_id, phase.id)


@router.post("/phases/{phase_id}/gate")
def update_gate(
    phase_id: str,
    gate_status: str = Form("Не готов"),
    gate_comment: str = Form(""),
    gate_decision_by: str = Form(""),
    db: Session = Depends(get_db),
):
    phase = db.get(ProjectPhase, phase_id)
    if not phase:
        return RedirectResponse(url="/", status_code=303)

    before = phase_state(phase)
    phase.gate_status = normalize_choice(gate_status, GATE_STATUSES, "Не готов")
    phase.gate_comment = gate_comment
    phase.gate_decision_by = gate_decision_by
    phase.gate_decision_at = today_string()
    if phase.gate_status in {"Разрешен", "GO"}:
        phase.health = "green"
    elif phase.gate_status in {"Разрешен с рисками", "GO WITH RISKS"}:
        phase.health = "yellow"
    elif phase.gate_status in {"Стоп", "STOP"}:
        phase.health = "red"
    elif phase.gate_status == "На аудите":
        phase.health = "blue"

    record_event(
        db,
        project_id=phase.project_id,
        event_type="phase.gate_updated",
        entity_type="phase",
        entity_id=phase.id,
        description=f"Gate-решение по фазе {phase.name}: {phase.gate_status}",
        before_state=before,
        after_state=phase_state(phase),
    )
    db.commit()
    return _redirect_to_phase(phase.project_id, phase.id)


@router.post("/phases/{phase_id}/audits")
def create_technical_audit(
    phase_id: str,
    auditor: str = Form(""),
    status: str = Form("В работе"),
    audit_date: str = Form(""),
    findings: str = Form(""),
    open_findings_count: str = Form("0"),
    critical_findings_count: str = Form("0"),
    decision: str = Form(""),
    decision_comment: str = Form(""),
    db: Session = Depends(get_db),
):
    phase = db.get(ProjectPhase, phase_id)
    if not phase:
        return RedirectResponse(url="/", status_code=303)

    audit = TechnicalAudit(
        project_id=phase.project_id,
        phase_id=phase.id,
        auditor=auditor,
        status=status,
        audit_date=audit_date or today_string(),
        findings=findings,
        open_findings_count=open_findings_count or "0",
        critical_findings_count=critical_findings_count or "0",
        decision=decision,
        decision_comment=decision_comment,
    )
    db.add(audit)
    db.flush()
    record_event(
        db,
        project_id=phase.project_id,
        event_type="technical_audit.created",
        entity_type="technical_audit",
        entity_id=audit.id,
        description=f"Создан техаудит фазы: {phase.name}",
        after_state={
            "phase_id": phase.id,
            "auditor": audit.auditor,
            "status": audit.status,
            "decision": audit.decision,
        },
    )
    db.commit()
    return _redirect_to_phase(phase.project_id, phase.id)

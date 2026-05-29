from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AgentProposal, P3Activity, ProcurementItem, Risk, Task
from app.services.event_log import record_event


router = APIRouter()


@router.post("/projects/{project_id}/agent-proposals")
def create_agent_proposal(
    project_id: str,
    agent_name: str = Form("local-agent"),
    proposal_type: str = Form("create_task"),
    title: str = Form(...),
    description: str = Form(""),
    target_ref: str = Form(""),
    suggested_status: str = Form(""),
    source_file: str = Form(""),
    db: Session = Depends(get_db),
):
    agent_name = agent_name if isinstance(agent_name, str) else "local-agent"
    proposal_type = proposal_type if isinstance(proposal_type, str) else "create_task"
    description = description if isinstance(description, str) else ""
    target_ref = target_ref if isinstance(target_ref, str) else ""
    suggested_status = suggested_status if isinstance(suggested_status, str) else ""
    source_file = source_file if isinstance(source_file, str) else ""
    target_type, target_id = split_target_ref(target_ref)
    proposal = AgentProposal(
        project_id=project_id,
        agent_name=agent_name,
        source_file=source_file,
        proposal_type=proposal_type,
        title=title,
        description=description,
        target_type=target_type,
        target_id=target_id,
        suggested_status=suggested_status,
    )
    db.add(proposal)
    db.flush()
    record_event(
        db,
        project_id=project_id,
        event_type="agent_proposal.created",
        entity_type="agent_proposal",
        entity_id=proposal.id,
        actor_type="агент",
        actor_id=agent_name,
        source="agent",
        description=f"Создано предложение агента: {proposal.title}",
        after_state=proposal_state(proposal),
    )
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}/agents", status_code=303)


@router.post("/agent-proposals/{proposal_id}/decision")
def decide_agent_proposal(
    proposal_id: str,
    decision: str = Form(...),
    decision_comment: str = Form(""),
    db: Session = Depends(get_db),
):
    decision_comment = decision_comment if isinstance(decision_comment, str) else ""
    proposal = db.get(AgentProposal, proposal_id)
    if not proposal:
        return RedirectResponse(url="/", status_code=303)

    before = proposal_state(proposal)
    if decision == "accept":
        apply_agent_proposal(db, proposal)
        proposal.status = "Принято"
        event_type = "agent_proposal.accepted"
    else:
        proposal.status = "Отклонено"
        event_type = "agent_proposal.rejected"
    proposal.decision_comment = decision_comment
    db.flush()
    record_event(
        db,
        project_id=proposal.project_id,
        event_type=event_type,
        entity_type="agent_proposal",
        entity_id=proposal.id,
        description=f"Решение по предложению агента: {proposal.status}",
        before_state=before,
        after_state=proposal_state(proposal),
    )
    db.commit()
    return RedirectResponse(url=f"/projects/{proposal.project_id}/agents", status_code=303)


def split_target_ref(target_ref: str) -> tuple[str, str]:
    if target_ref and ":" in target_ref:
        return target_ref.split(":", 1)
    return "", ""


def proposal_state(proposal: AgentProposal) -> dict[str, str]:
    return {
        "proposal_type": proposal.proposal_type,
        "title": proposal.title,
        "target_type": proposal.target_type,
        "target_id": proposal.target_id,
        "suggested_status": proposal.suggested_status,
        "status": proposal.status,
    }


def apply_agent_proposal(db: Session, proposal: AgentProposal) -> None:
    # Агент не меняет проект напрямую: изменение применяется только после явного принятия человеком.
    if proposal.proposal_type == "create_task":
        task = Task(
            project_id=proposal.project_id,
            title=proposal.title,
            description=proposal.description,
            type="предложение агента",
            source_type="агент",
        )
        db.add(task)
        db.flush()
        record_event(
            db,
            project_id=proposal.project_id,
            event_type="task.created_from_agent_proposal",
            entity_type="task",
            entity_id=task.id,
            actor_type="агент",
            actor_id=proposal.agent_name,
            source="agent",
            description=f"Создана задача из предложения агента: {task.title}",
            after_state={"title": task.title, "status": task.status, "proposal_id": proposal.id},
        )
        return

    if proposal.proposal_type == "update_status" and proposal.target_type and proposal.target_id:
        target = get_status_target(db, proposal.target_type, proposal.target_id)
        if not target:
            return
        before = {"status": target.status}
        target.status = proposal.suggested_status or target.status
        record_event(
            db,
            project_id=proposal.project_id,
            event_type="status.updated_from_agent_proposal",
            entity_type=proposal.target_type,
            entity_id=proposal.target_id,
            actor_type="агент",
            actor_id=proposal.agent_name,
            source="agent",
            description=f"Обновлен статус из предложения агента: {proposal.title}",
            before_state=before,
            after_state={"status": target.status, "proposal_id": proposal.id},
        )


def get_status_target(db: Session, target_type: str, target_id: str):
    models = {
        "task": Task,
        "procurement": ProcurementItem,
        "risk": Risk,
        "p3": P3Activity,
    }
    model = models.get(target_type)
    return db.get(model, target_id) if model else None

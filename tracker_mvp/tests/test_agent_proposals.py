from sqlalchemy import select

from app.models import AgentProposal, Event, Task
from app.routes.agents import create_agent_proposal, decide_agent_proposal


def test_agent_proposal_acceptance_creates_task(db_session, project):
    create_agent_proposal(
        project.id,
        agent_name="qa-agent",
        proposal_type="create_task",
        title="Проверить ведомость закупок",
        description="Агент нашел незаполненные позиции.",
        db=db_session,
    )
    proposal = db_session.scalars(select(AgentProposal).where(AgentProposal.project_id == project.id)).one()

    decide_agent_proposal(proposal.id, decision="accept", decision_comment="Берем в работу", db=db_session)

    task = db_session.scalars(select(Task).where(Task.project_id == project.id, Task.title == "Проверить ведомость закупок")).one()
    db_session.refresh(proposal)
    events = db_session.scalars(select(Event).where(Event.project_id == project.id)).all()

    assert task.source_type == "агент"
    assert proposal.status == "Принято"
    assert {event.event_type for event in events} >= {"agent_proposal.created", "agent_proposal.accepted", "task.created_from_agent_proposal"}


def test_agent_proposal_rejection_does_not_apply_change(db_session, project):
    create_agent_proposal(
        project.id,
        proposal_type="create_task",
        title="Лишняя задача",
        db=db_session,
    )
    proposal = db_session.scalars(select(AgentProposal).where(AgentProposal.project_id == project.id)).one()

    decide_agent_proposal(proposal.id, decision="reject", decision_comment="Не нужно", db=db_session)

    db_session.refresh(proposal)
    tasks = db_session.scalars(select(Task).where(Task.project_id == project.id, Task.title == "Лишняя задача")).all()

    assert proposal.status == "Отклонено"
    assert tasks == []

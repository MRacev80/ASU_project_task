from sqlalchemy.orm import Session

from app.models import Event


def record_event(
    db: Session,
    *,
    project_id: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    description: str,
    actor_type: str = "человек",
    actor_id: str = "local",
) -> Event:
    event = Event(
        project_id=project_id,
        actor_type=actor_type,
        actor_id=actor_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    db.add(event)
    return event

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import Event


def serialize_state(state: dict[str, Any] | None) -> str:
    if not state:
        return ""
    return json.dumps(state, ensure_ascii=False, sort_keys=True)


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
    source: str = "ui",
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
) -> Event:
    # Журнал хранит не только текст события, но и легкий before/after-снимок:
    # это будущая основа для агентского анализа и восстановления хода изменений.
    event = Event(
        project_id=project_id,
        actor_type=actor_type,
        actor_id=actor_id,
        source=source,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        before_state=serialize_state(before_state),
        after_state=serialize_state(after_state),
    )
    db.add(event)
    return event

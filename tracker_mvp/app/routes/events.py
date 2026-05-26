from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Event


router = APIRouter()


@router.get("/api/projects/{project_id}/events")
def list_events(project_id: str, db: Session = Depends(get_db)):
    events = db.scalars(select(Event).where(Event.project_id == project_id).order_by(Event.created_at.desc()).limit(100)).all()
    return [
        {
            "id": event.id,
            "actor_type": event.actor_type,
            "event_type": event.event_type,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "description": event.description,
            "created_at": event.created_at.isoformat(),
        }
        for event in events
    ]

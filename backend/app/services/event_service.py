from sqlalchemy.orm import Session, joinedload
from ..models import Event
from ..schemas import EventCreate
from .canonical_analysis_service import ensure_legacy_writes_allowed


class EventService:
    @staticmethod
    def get_by_match(db: Session, match_id: int):
        return (
            db.query(Event)
            .options(
                joinedload(Event.player),
                joinedload(Event.assist_player),
                joinedload(Event.goalkeeper),
                joinedload(Event.sub_in_player),
                joinedload(Event.sub_out_player),
            )
            .filter(Event.match_id == match_id)
            .order_by(Event.game_timestamp.asc())
            .all()
        )

    @staticmethod
    def create(db: Session, data: EventCreate):
        ensure_legacy_writes_allowed(db, data.match_id)
        obj = Event(**data.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, event_id: int) -> bool:
        obj = db.query(Event).filter(Event.id == event_id).first()
        if not obj:
            return False
        ensure_legacy_writes_allowed(db, obj.match_id)
        db.delete(obj)
        db.commit()
        return True

    @staticmethod
    def get_last_by_match(db: Session, match_id: int):
        return (
            db.query(Event)
            .filter(Event.match_id == match_id)
            .order_by(Event.id.desc())
            .first()
        )

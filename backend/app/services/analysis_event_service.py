from sqlalchemy.orm import Session, joinedload

from ..models import AnalysisCodebookEntry, AnalysisEvent, AnalysisEventRevision, User
from ..schemas import AnalysisEventCreate, AnalysisEventUpdate
from .canonical_analysis_service import ensure_legacy_writes_allowed


class AnalysisEventService:
    @staticmethod
    def _payload(event):
        return {
            "codebook_version": event.codebook_entry.version,
            "code": event.codebook_entry.code,
            "period": event.period,
            "regulation_seconds": event.regulation_seconds,
            "video_timestamp": event.video_timestamp,
            "clock_unverified": event.clock_unverified,
            "team_action": event.team_action,
            "player_id": event.player_id,
            "turnover_cause": event.turnover_cause,
            "outcome": event.outcome,
            "evidence_state": event.evidence_state,
            "source": event.source,
            "angle": event.angle,
            "note": event.note,
            "included": event.included,
            "active": event.active,
        }

    @staticmethod
    def _entry(db, version, code):
        return db.query(AnalysisCodebookEntry).filter_by(version=version, code=code).one_or_none()

    @staticmethod
    def get_by_match(db: Session, match_id: int):
        return db.query(AnalysisEvent).options(joinedload(AnalysisEvent.codebook_entry)).filter_by(match_id=match_id).order_by(AnalysisEvent.id).all()

    @staticmethod
    def get(db: Session, event_id: int):
        return db.query(AnalysisEvent).options(joinedload(AnalysisEvent.codebook_entry)).filter_by(id=event_id).one_or_none()

    @classmethod
    def create(cls, db: Session, match_id: int, data: AnalysisEventCreate, actor: User):
        ensure_legacy_writes_allowed(db, match_id)
        entry = cls._entry(db, data.codebook_version, data.code)
        if entry is None:
            raise ValueError("unsupported codebook entry")
        event = AnalysisEvent(match_id=match_id, codebook_entry=entry, analyst_id=actor.id, **data.model_dump(exclude={"codebook_version", "code"}))
        db.add(event)
        db.flush()
        db.add(AnalysisEventRevision(event=event, actor_id=actor.id, after_payload=cls._payload(event), reason="created"))
        db.commit()
        return cls.get(db, event.id)

    @classmethod
    def update(cls, db: Session, event: AnalysisEvent, data: AnalysisEventUpdate, actor: User):
        ensure_legacy_writes_allowed(db, event.match_id)
        before = cls._payload(event)
        changes = data.model_dump(exclude_unset=True, exclude={"reason"})
        code = changes.pop("code", event.codebook_entry.code)
        version = changes.pop("codebook_version", event.codebook_entry.version)
        entry = cls._entry(db, version, code)
        if entry is None:
            raise ValueError("unsupported codebook entry")
        turnover_cause = changes.get("turnover_cause", event.turnover_cause)
        if code == "turnover" and turnover_cause is None:
            raise ValueError("turnover_cause is required for turnover events")
        if code != "turnover" and turnover_cause is not None:
            raise ValueError("turnover_cause is only valid for turnover events")
        event.codebook_entry = entry
        for field, value in changes.items():
            setattr(event, field, value)
        db.flush()
        db.add(AnalysisEventRevision(event=event, actor_id=actor.id, before_payload=before, after_payload=cls._payload(event), reason=data.reason))
        db.commit()
        return cls.get(db, event.id)

    @classmethod
    def set_active(cls, db: Session, event: AnalysisEvent, active: bool, reason: str, actor: User):
        ensure_legacy_writes_allowed(db, event.match_id)
        before = cls._payload(event)
        event.active = active
        db.flush()
        db.add(AnalysisEventRevision(event=event, actor_id=actor.id, before_payload=before, after_payload=cls._payload(event), reason=reason))
        db.commit()
        return cls.get(db, event.id)

    @staticmethod
    def revisions(db: Session, event_id: int):
        return db.query(AnalysisEventRevision).filter_by(event_id=event_id).order_by(AnalysisEventRevision.id).all()

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import AnalysisCodebookEntry, Match, User
from app.schemas import AnalysisEventCreate, AnalysisEventUpdate
from app.services.analysis_event_service import AnalysisEventService


def test_analytical_event_revisions_preserve_selected_event_history():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([
        User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst"),
        Match(id=1),
        AnalysisCodebookEntry(version="mvp-1", code="turnover", category="possession"),
        AnalysisCodebookEntry(version="mvp-1", code="recovery", category="defense"),
    ])
    session.commit()

    event = AnalysisEventService.create(session, 1, AnalysisEventCreate(code="turnover", evidence_state="confirmed", turnover_cause="interception"), session.get(User, 1))
    event = AnalysisEventService.update(session, event, AnalysisEventUpdate(code="recovery", turnover_cause=None, reason="reviewed footage"), session.get(User, 1))
    with pytest.raises(ValueError, match="turnover_cause"):
        AnalysisEventService.update(session, event, AnalysisEventUpdate(code="turnover", reason="incomplete correction"), session.get(User, 1))
    AnalysisEventService.set_active(session, event, False, "duplicate observation", session.get(User, 1))
    restored = AnalysisEventService.set_active(session, event, True, "selected correction", session.get(User, 1))

    revisions = AnalysisEventService.revisions(session, event.id)
    assert restored.active is True
    assert [(revision.reason, revision.actor_id) for revision in revisions] == [("created", 1), ("reviewed footage", 1), ("duplicate observation", 1), ("selected correction", 1)]
    assert revisions[1].before_payload["code"] == "turnover"
    assert revisions[1].after_payload["code"] == "recovery"
    assert revisions[2].after_payload["active"] is False
    engine.dispose()


def test_codebook_accepts_observable_events_and_preserves_evidence_revisions():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    session.add_all([
        analyst,
        Match(id=1),
        AnalysisCodebookEntry(version="mvp-1", code="shot", category="attack"),
        AnalysisCodebookEntry(version="mvp-1", code="seven_meter", category="attack"),
    ])
    session.commit()

    event = AnalysisEventService.create(
        session, 1, AnalysisEventCreate(code="shot", outcome="goal", evidence_state="confirmed"), analyst
    )
    with pytest.raises(ValueError, match="unsupported codebook entry"):
        AnalysisEventService.create(
            session, 1, AnalysisEventCreate(code="confirmed_assist", evidence_state="confirmed"), analyst
        )
    event = AnalysisEventService.update(
        session, event, AnalysisEventUpdate(evidence_state="ambiguous", reason="angle obscures outcome"), analyst
    )
    AnalysisEventService.set_active(session, event, False, "selected event is duplicate", analyst)
    restored = AnalysisEventService.set_active(session, event, True, "selected event restored", analyst)

    revisions = AnalysisEventService.revisions(session, event.id)
    assert restored.codebook_entry.code == "shot"
    assert restored.evidence_state == "ambiguous"
    assert restored.active is True
    assert revisions[1].before_payload["evidence_state"] == "confirmed"
    assert revisions[1].after_payload["evidence_state"] == "ambiguous"
    assert [revision.reason for revision in revisions[2:]] == ["selected event is duplicate", "selected event restored"]
    engine.dispose()


def test_capture_rejects_passing_accuracy_and_audits_no_visible_and_replay():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    session.add_all([
        analyst,
        Match(id=1),
        AnalysisCodebookEntry(version="mvp-1", code="shot", category="attack"),
    ])
    session.commit()

    with pytest.raises(ValidationError, match="passing_accuracy"):
        AnalysisEventCreate(code="passing_accuracy", evidence_state="confirmed")

    no_visible = AnalysisEventService.create(
        session, 1, AnalysisEventCreate(code="shot", evidence_state="no_visible", note="action obscured"), analyst
    )
    replay = AnalysisEventService.create(
        session, 1, AnalysisEventCreate(code="shot", evidence_state="replay", note="repeated footage"), analyst
    )

    assert no_visible.id != replay.id
    assert AnalysisEventService.revisions(session, no_visible.id)[0].after_payload["evidence_state"] == "no_visible"
    assert AnalysisEventService.revisions(session, replay.id)[0].after_payload["evidence_state"] == "replay"
    engine.dispose()

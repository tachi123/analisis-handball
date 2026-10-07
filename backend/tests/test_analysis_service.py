"""Canonical-only read facade contract.

Legacy ``AnalysisEvent`` rows are unreviewed provenance: they must never feed
metrics or reconciliation, and every mutation on them leaves the canonical
read model untouched.
"""
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import AnalysisCodebookEntry, AnalysisEvent, Match, OfficialSnapshot, User
from app.schemas import AnalysisEventCreate, AnalysisEventUpdate
from app.services.analysis_event_service import AnalysisEventService
from app.services.analysis_service import AnalysisService


def make_event(entry, **values):
    defaults = {
        "match_id": 1,
        "analyst_id": 1,
        "codebook_entry": entry,
        "evidence_state": "confirmed",
        "active": True,
        "included": True,
    }
    defaults.update(values)
    return AnalysisEvent(**defaults)


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    return engine, session


def test_legacy_analysis_events_are_never_a_metric_source():
    engine, session = _session()
    shot = AnalysisCodebookEntry(version="mvp-1", code="shot", category="attack")
    turnover = AnalysisCodebookEntry(version="mvp-1", code="turnover", category="possession")
    session.add_all([User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst"), Match(id=1), shot, turnover])
    session.flush()
    session.add_all([
        make_event(shot, outcome="goal", clock_unverified=True),
        make_event(shot, outcome="saved"),
        make_event(shot, outcome="goal", evidence_state="no_visible"),
        make_event(shot, outcome="goal", evidence_state="replay"),
        make_event(shot, outcome="goal", included=False),
        make_event(shot, outcome="goal", active=False),
        make_event(turnover, turnover_cause="interception"),
    ])
    session.commit()

    result = AnalysisService.reviewed_metrics(session, 1)

    assert result["metrics"] == {}
    assert result["eligibility"] == {"eligible": 0, "excluded": 0, "unknown": 0,
                                     "clock_unverified": 0, "unresolved": 0}
    assert result["reconciliation"] == []
    assert session.query(AnalysisEvent).count() == 7
    engine.dispose()


def test_passing_accuracy_is_never_claimed_from_any_source():
    engine, session = _session()
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    session.add_all([analyst, Match(id=1),
                     AnalysisCodebookEntry(version="mvp-1", code="shot", category="attack")])
    session.commit()
    for state in ("confirmed", "no_visible", "replay"):
        AnalysisEventService.create(
            session, 1, AnalysisEventCreate(code="shot", outcome="goal", evidence_state=state), analyst
        )

    metrics = AnalysisService.reviewed_metrics(session, 1)["metrics"]

    assert "passing_accuracy" not in metrics
    assert "shot_conversion" not in metrics
    engine.dispose()


def test_reconciliation_reads_official_snapshot_without_mutating_it():
    engine, session = _session()
    shot = AnalysisCodebookEntry(version="mvp-1", code="shot", category="attack")
    match = Match(id=1, date=date(2026, 8, 22), home_score=99, away_score=88)
    snapshot = OfficialSnapshot(
        id="official-1", match=match, source_filename="sheet.pdf", source_content_type="application/pdf",
        source_size_bytes=1, source_sha256="hash", source_page_count=1, source_path="sheet.pdf",
        confirmed_date=date(2026, 8, 22), home_team_name="SAPA", away_team_name="Banfield", home_score=28, away_score=24,
    )
    session.add_all([User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst"), shot, snapshot])
    session.flush()
    session.add_all([make_event(shot, outcome="goal", team_action="SAPA"), make_event(shot, outcome="goal", team_action="Banfield")])
    session.commit()

    result = AnalysisService.reviewed_metrics(session, 1)

    assert result["official"] == {"snapshot_id": "official-1", "home_score": 28, "away_score": 24}
    assert result["reconciliation"] == [
        {"side": "home", "official": 28, "analytical": 0, "discrepancy": -28},
        {"side": "away", "official": 24, "analytical": 0, "discrepancy": -24},
    ]
    assert (session.get(Match, 1).home_score, session.get(Match, 1).away_score) == (99, 88)
    assert (session.get(OfficialSnapshot, "official-1").home_score, session.get(OfficialSnapshot, "official-1").away_score) == (28, 24)
    engine.dispose()


def test_legacy_event_lifecycle_leaves_canonical_reads_untouched():
    engine, session = _session()
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    session.add_all([analyst, Match(id=1, date=date(2026, 8, 22)),
                     AnalysisCodebookEntry(version="mvp-1", code="shot", category="attack")])
    session.commit()
    baseline = AnalysisService.reviewed_metrics(session, 1)

    event = AnalysisEventService.create(
        session, 1, AnalysisEventCreate(code="shot", outcome="goal", team_action="SAPA", evidence_state="confirmed"), analyst
    )
    event = AnalysisEventService.update(
        session, event, AnalysisEventUpdate(evidence_state="no_visible", reason="outcome not visible"), analyst
    )
    AnalysisEventService.set_active(session, event, False, "selected event excluded", analyst)
    AnalysisEventService.set_active(session, event, True, "selected event restored", analyst)

    refreshed = AnalysisService.reviewed_metrics(session, 1)
    assert refreshed == baseline
    assert session.query(AnalysisEvent).count() == 1
    engine.dispose()

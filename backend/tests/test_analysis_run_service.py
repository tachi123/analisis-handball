import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import AnalysisRun, Match, OfficialSnapshot, User
from app.services.analysis_run_service import create_draft, promote, require_writable_run


def test_promoting_a_draft_supersedes_the_previous_active_run_atomically():
    engine = create_engine("sqlite://")
    db = sessionmaker(bind=engine)()
    Base.metadata.create_all(engine)
    user = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    official_snapshot = OfficialSnapshot(id="snap-1", match_id=1, source_filename="test.pdf", source_content_type="application/pdf", source_size_bytes=100, source_sha256="abc", source_page_count=1, source_path="/tmp/test.pdf", confirmed_date=date(2026, 1, 1), home_team_name="A", away_team_name="B", home_score=0, away_score=0, is_confirmed=True)
    db.add_all([user, Match(id=1, canonical_analysis_enabled=True), official_snapshot, AnalysisRun(id=10, match_id=1, mode="legacy", status="active")])
    db.commit()

    draft = create_draft(db, 1, "video", user)
    promoted = promote(db, 1, draft.id, user)

    assert promoted.status == "active"
    assert db.get(AnalysisRun, 10).status == "superseded"
    assert db.query(AnalysisRun).filter_by(match_id=1, status="active").count() == 1
    with pytest.raises(ValueError, match="only draft"):
        require_writable_run(db, db.get(Match, 1), 10, user)
    engine.dispose()


def test_run_creator_can_write_to_active_run():
    engine = create_engine("sqlite://")
    db = sessionmaker(bind=engine)()
    Base.metadata.create_all(engine)
    user = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    official_snapshot = OfficialSnapshot(id="snap-1", match_id=1, source_filename="test.pdf", source_content_type="application/pdf", source_size_bytes=100, source_sha256="abc", source_page_count=1, source_path="/tmp/test.pdf", confirmed_date=date(2026, 1, 1), home_team_name="A", away_team_name="B", home_score=0, away_score=0, is_confirmed=True)
    db.add_all([user, Match(id=1, canonical_analysis_enabled=True), official_snapshot, AnalysisRun(id=20, match_id=1, mode="video", status="active", created_by_user_id=user.id)])
    db.commit()

    assert require_writable_run(db, db.get(Match, 1), 20, user).status == "active"
    engine.dispose()

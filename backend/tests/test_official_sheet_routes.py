from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Match, OfficialSnapshot, OfficialSnapshotPlayer, User
from app.security import create_access_token


def test_official_sheet_returns_latest_confirmed_facts_without_source_path(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'official-sheet.db'}", connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = factory()
    match = Match(date=date.today())
    db.add_all([User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst"), match])
    db.flush()
    old = OfficialSnapshot(id="old", match_id=match.id, source_path="/private/old.pdf", source_filename="old.pdf", source_content_type="application/pdf", source_size_bytes=1, source_sha256="old", source_page_count=1, confirmed_date=date.today(), home_team_name="Old", away_team_name="Old Away", home_score=1, away_score=1, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    latest = OfficialSnapshot(id="latest", match_id=match.id, source_path="/private/latest.pdf", source_filename="latest.pdf", source_content_type="application/pdf", source_size_bytes=2, source_sha256="latest", source_page_count=1, confirmed_date=date.today(), home_team_name="Local", away_team_name="Visitante", home_score=20, away_score=18, created_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    db.add_all([old, latest, OfficialSnapshotPlayer(snapshot=latest, side="home", player_id=None, name="Jugadora", jersey_number=7, official_goals=3, official_yellow=1, official_2min=0, official_red=0, official_blue=0)])
    db.commit()

    def override_db():
        current = factory()
        try:
            yield current
        finally:
            current.close()

    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        assert TestClient(app).get(f"/api/v1/matches/{match.id}/official-sheet").status_code == 403
        response = TestClient(app).get(f"/api/v1/matches/{match.id}/official-sheet", headers=headers)
        assert response.status_code == 200
        assert response.json() == {
            "snapshot_id": "latest", "confirmed_date": str(date.today()),
            "home": {"name": "Local", "score": 20, "players": [{"player_id": None, "name": "Jugadora", "jersey_number": 7, "official_goals": 3, "official_yellow": 1, "official_2min": 0, "official_red": 0, "official_blue": 0}]},
            "away": {"name": "Visitante", "score": 18, "players": []},
            "provenance": {"filename": "latest.pdf", "content_type": "application/pdf", "size_bytes": 2, "sha256": "latest", "page_count": 1},
            "pdf_available": False,
        }
        assert "source_path" not in response.text
        assert TestClient(app).get(f"/api/v1/matches/{match.id}/official-sheet/pdf", headers=headers).status_code == 409
        assert TestClient(app).get(f"/api/v1/matches/{match.id + 1}/official-sheet", headers=headers).status_code == 404
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def test_official_sheet_streams_only_a_pdf_inside_an_approved_root(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'official-sheet-pdf.db'}", connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = factory()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    source = evidence / "official.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    match = Match(date=date.today())
    db.add_all([User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst"), match])
    db.flush()
    db.add(OfficialSnapshot(id="approved", match_id=match.id, source_path=str(source), source_filename="official.pdf", source_content_type="application/pdf", source_size_bytes=source.stat().st_size, source_sha256="approved", source_page_count=1, confirmed_date=date.today(), home_team_name="Local", away_team_name="Visitante", home_score=1, away_score=0))
    db.commit()
    monkeypatch.setenv("OFFICIAL_EVIDENCE_ROOTS", str(evidence))

    def override_db():
        current = factory()
        try:
            yield current
        finally:
            current.close()

    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        response = TestClient(app).get(f"/api/v1/matches/{match.id}/official-sheet/pdf", headers=headers)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/pdf")
        assert response.headers["content-disposition"] == 'inline; filename="official.pdf"'
        assert response.content == b"%PDF-1.4\n"
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Club, CompetitionTeam, FixtureImport, FixtureImportEntry, Match, OfficialSnapshot, OfficialSnapshotPlayer, Round, ScheduledMatch, Season, TeamRegistration, TournamentStage, User
from app.security import create_access_token


def _client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'stage-performance.db'}", connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = factory()
    season = Season(year=2026); stage = TournamentStage(season=season, name="Stage", category="Senior", division="A", gender="M")
    db.add_all([User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst"), season, stage])
    registrations = []
    for name in ("Alpha", "Beta"):
        registrations.append(TeamRegistration(competition_team=CompetitionTeam(club=Club(name=name), stage=stage, variant_key=""), stage=stage))
    db.add_all(registrations); db.flush()
    fixture = ScheduledMatch(stage=stage, round=Round(stage=stage, round_number=1), home_registration=registrations[0], away_registration=registrations[1], fixture_key="fixture", match_number_label="1", scheduled_date=date.today())
    match = Match(date=date.today(), scheduled_match=fixture)
    snapshot = OfficialSnapshot(id="confirmed", match=match, is_confirmed=True, source_filename="sheet.pdf", source_content_type="application/pdf", source_size_bytes=1, source_sha256="a", source_page_count=1, source_path="sheet.pdf", confirmed_date=date.today(), home_team_name="Alpha", away_team_name="Beta", home_score=21, away_score=20)
    audit = FixtureImport(stage=stage, source_label="test", captured_at=datetime.now(timezone.utc), source_sha256="fixture-import", payload={})
    db.add_all([
        snapshot,
        FixtureImportEntry(fixture_import=audit, entry_key="fixture", kind="match", raw_entry={}, scheduled_match=fixture),
        OfficialSnapshotPlayer(snapshot=snapshot, side="home", name="Ana", jersey_number=9, official_goals=7, official_yellow=1, official_2min=0, official_red=0, official_blue=0),
    ])
    db.commit()
    stage_id = stage.id
    db.close()

    def override_db():
        current = factory()
        try:
            yield current
        finally:
            current.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), engine, stage_id


def test_stage_routes_return_confirmed_aggregates_and_no_data_conflict(tmp_path):
    client, engine, stage_id = _client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    try:
        standings = client.get(f"/api/v1/stages/{stage_id}/standings?win_points=3", headers=headers)
        assert standings.status_code == 200
        assert standings.json()[0]["team_name"] == "Alpha" and standings.json()[0]["points"] == 3
        assert client.get(f"/api/v1/stages/{stage_id}/scorers", headers=headers).json()[0]["goals"] == 7
        assert client.get(f"/api/v1/stages/{stage_id}/player-averages", headers=headers).json()[0]["goals_per_match"] == 7
        empty = client.get("/api/v1/stages/999/player-averages", headers=headers)
        assert empty.status_code == 409 and empty.json()["detail"] == "no_confirmed_official_data"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

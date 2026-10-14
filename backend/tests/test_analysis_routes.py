from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import AnalysisCodebookEntry, Match, OfficialSnapshot, User
from app.security import create_access_token


def analysis_client(tmp_path, confirmed_sheet=False, manual_match=False):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'analysis-routes.db'}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    session = session_factory()
    records = [
        User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst"),
        User(id=2, email="other@example.com", hashed_password="x", full_name="Other analyst"),
        Match(id=1, origin="manual" if manual_match else "legacy", created_by_user_id=1 if manual_match else None),
        AnalysisCodebookEntry(version="mvp-1", code="shot", category="attack"),
    ]
    if confirmed_sheet:
        records.append(OfficialSnapshot(
            id="sheet-1", match_id=1, source_filename="sheet.pdf", source_content_type="application/pdf",
            source_size_bytes=1, source_sha256="sha", source_page_count=1, source_path="/tmp/sheet.pdf",
            confirmed_date=date(2026, 1, 1), home_team_name="Home", away_team_name="Away",
            home_score=0, away_score=0, is_confirmed=True,
        ))
    session.add_all(records)
    session.commit()
    session.close()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), engine


def test_authenticated_source_session_is_saved_and_retrieved(tmp_path):
    client, engine = analysis_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    payload = {
        "mode": "video",
        "profile": "goalkeepers",
        "source": {"url": "https://youtu.be/abcdefghijk", "availability_state": "ready"},
        "video_position_seconds": 94.5,
        "clock_start_video_seconds": 12.5,
    }

    try:
        saved = client.put("/api/v1/matches/1/analysis-session", json=payload, headers=headers)
        recovered = client.get("/api/v1/matches/1/analysis-session", headers=headers)

        assert saved.status_code == 200
        assert saved.json()["source"]["provider_video_id"] == "abcdefghijk"
        assert recovered.status_code == 200
        assert recovered.json()["video_position_seconds"] == 94.5
        assert recovered.json()["profile"] == "goalkeepers"
        assert recovered.json()["clock_start_video_seconds"] == 12.5
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_confirmed_match_creates_a_draft_and_scopes_its_initial_session(tmp_path):
    client, engine = analysis_client(tmp_path, confirmed_sheet=True)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}

    try:
        created = client.post("/api/v1/matches/1/analysis-runs", json={"mode": "video"}, headers=headers)
        run_id = created.json()["id"]
        saved = client.put(
            f"/api/v1/matches/1/analysis-session?run_id={run_id}",
            json={"mode": "video", "source": None},
            headers=headers,
        )

        assert created.status_code == 201
        assert created.json()["status"] == "draft"
        assert saved.status_code == 200
        assert saved.json()["run_id"] == run_id
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_manual_match_draft_and_writes_are_limited_to_its_owner(tmp_path):
    client, engine = analysis_client(tmp_path, confirmed_sheet=True, manual_match=True)
    owner_headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    other_headers = {"Authorization": f"Bearer {create_access_token({'sub': '2'})}"}

    try:
        denied_creation = client.post("/api/v1/matches/1/analysis-runs", json={"mode": "video"}, headers=other_headers)
        created = client.post("/api/v1/matches/1/analysis-runs", json={"mode": "video"}, headers=owner_headers)
        denied_write = client.put(
            f"/api/v1/matches/1/analysis-session?run_id={created.json()['id']}",
            json={"mode": "video", "source": None},
            headers=other_headers,
        )

        assert denied_creation.status_code == 403
        assert created.status_code == 201
        assert denied_write.status_code == 403
        assert "run creator" in denied_write.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_unique_implicit_draft_session_write_is_limited_to_its_owner(tmp_path):
    client, engine = analysis_client(tmp_path, confirmed_sheet=True)
    owner_headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    other_headers = {"Authorization": f"Bearer {create_access_token({'sub': '2'})}"}

    try:
        created = client.post("/api/v1/matches/1/analysis-runs", json={"mode": "video"}, headers=owner_headers)
        denied_write = client.put(
            "/api/v1/matches/1/analysis-session",
            json={"mode": "video", "source": None},
            headers=other_headers,
        )

        assert created.status_code == 201
        assert denied_write.status_code == 403
        assert "run creator" in denied_write.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_source_replacement_request_discards_stale_video_calibration(tmp_path):
    client, engine = analysis_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    original = {
        "mode": "video",
        "source": {"url": "https://youtu.be/abcdefghijk", "availability_state": "ready"},
        "video_position_seconds": 12,
        "clock_start_video_seconds": 10,
        "anchors": [{"period": 1, "video_seconds": 10, "regulation_seconds": 0}],
        "time_segments": [{"period": 1, "video_start_seconds": 10, "video_end_seconds": 70, "regulation_start_seconds": 0, "regulation_end_seconds": 60, "coverage": "playable"}],
    }
    stale_replacement = {
        **original,
        "source": {"url": "https://youtu.be/zyxwvutsrq", "availability_state": "ready"},
        "video_position_seconds": 99,
        "clock_start_video_seconds": 99,
        "anchors": [{"period": 1, "video_seconds": 99, "regulation_seconds": 0}],
        "time_segments": [{"period": 1, "video_start_seconds": 99, "video_end_seconds": 159, "regulation_start_seconds": 0, "regulation_end_seconds": 60, "coverage": "playable"}],
    }

    try:
        saved = client.put("/api/v1/matches/1/analysis-session", json=original, headers=headers)
        replaced = client.put("/api/v1/matches/1/analysis-session", json=stale_replacement, headers=headers)

        assert saved.status_code == replaced.status_code == 200
        assert replaced.json()["source"]["id"] != saved.json()["source"]["id"]
        assert replaced.json()["video_position_seconds"] is None
        assert replaced.json()["clock_start_video_seconds"] is None
        assert replaced.json()["anchors"] == []
        assert replaced.json()["time_segments"] == []
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_source_session_routes_reject_requests_without_a_bearer_token(tmp_path):
    client, engine = analysis_client(tmp_path)

    try:
        saved = client.put(
            "/api/v1/matches/1/analysis-session",
            json={"source": {"url": "https://youtu.be/abcdefghijk"}},
        )
        recovered = client.get("/api/v1/matches/1/analysis-session")

        assert saved.status_code == 403
        assert recovered.status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_event_route_persists_ambiguous_and_period_aware_clock_evidence(tmp_path):
    client, engine = analysis_client(tmp_path)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}
    payloads = [
        {"evidence_state": "ambiguous", "video_timestamp": 12, "regulation_seconds": None, "clock_unverified": True},
        {"evidence_state": "confirmed", "video_timestamp": 40, "regulation_seconds": 30, "clock_unverified": False},
        {"evidence_state": "no_visible", "video_timestamp": 75, "regulation_seconds": None, "clock_unverified": True},
        {"evidence_state": "replay", "video_timestamp": 94.5, "regulation_seconds": 84.5, "clock_unverified": False},
    ]

    try:
        saved = [client.post(
            "/api/v1/matches/1/analysis-events",
            json={"code": "shot", "period": 1, "source": "youtube", **payload},
            headers=headers,
        ) for payload in payloads]

        assert [response.status_code for response in saved] == [201, 201, 201, 201]
        events = client.get("/api/v1/matches/1/analysis-events", headers=headers)
        assert events.status_code == 200
        assert [(item["evidence_state"], item["video_timestamp"], item["regulation_seconds"], item["clock_unverified"]) for item in events.json()] == [
            ("ambiguous", 12, None, True),
            ("confirmed", 40, 30, False),
            ("no_visible", 75, None, True),
            ("replay", 94.5, 84.5, False),
        ]
        revisions = [client.get(f"/api/v1/analysis-events/{response.json()['id']}/revisions", headers=headers) for response in saved]
        assert [[revision["reason"] for revision in response.json()] for response in revisions] == [["created"]] * 4
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

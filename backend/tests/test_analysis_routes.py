from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import AnalysisCodebookEntry, Match, User
from app.security import create_access_token


def analysis_client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'analysis-routes.db'}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    session = session_factory()
    session.add_all([
        User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst"),
        Match(id=1),
        AnalysisCodebookEntry(version="mvp-1", code="shot", category="attack"),
    ])
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

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import GoalkeeperShot, Match, User
from app.security import create_access_token


def goalkeeper_client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'goalkeeper-shots.db'}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    session = session_factory()
    session.add_all([
        User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst"),
        Match(id=1),
        Match(id=2),
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


def auth_headers():
    return {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}


def test_create_goalkeeper_shot_with_minimal_payload(tmp_path):
    client, engine = goalkeeper_client(tmp_path)

    try:
        response = client.post("/api/v1/matches/1/goalkeeper-shots", json={}, headers=auth_headers())

        assert response.status_code == 201
        body = response.json()
        assert body["match_id"] == 1
        assert body["shooter_player_id"] is None
        assert body["origin_zone"] is None
        assert body["outcome"] is None
        assert body["created_at"] is not None
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_create_goalkeeper_shot_persists_full_payload_and_rejects_bad_enum(tmp_path):
    client, engine = goalkeeper_client(tmp_path)
    headers = auth_headers()
    payload = {
        "shooter_label": "7",
        "period": 1,
        "video_timestamp": 12.5,
        "origin_zone": "9m_left",
        "target_zone": "high_right",
        "shot_type": "spin",
        "outcome": "saved",
        "note": "Rosca al palo largo",
    }

    try:
        saved = client.post("/api/v1/matches/1/goalkeeper-shots", json=payload, headers=headers)
        assert saved.status_code == 201
        assert saved.json()["origin_zone"] == "9m_left"
        assert saved.json()["outcome"] == "saved"

        rejected = client.post(
            "/api/v1/matches/1/goalkeeper-shots",
            json={**payload, "origin_zone": "media_distancia"},
            headers=headers,
        )
        assert rejected.status_code == 422

        unknown_match = client.post("/api/v1/matches/999/goalkeeper-shots", json={}, headers=headers)
        assert unknown_match.status_code == 404
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_list_goalkeeper_shots_is_ordered_by_id_asc(tmp_path):
    client, engine = goalkeeper_client(tmp_path)
    headers = auth_headers()

    try:
        created = [
            client.post(
                "/api/v1/matches/1/goalkeeper-shots",
                json={"origin_zone": zone},
                headers=headers,
            ).json()["id"]
            for zone in ("6m_center", "wing_right", "seven_meter")
        ]

        listed = client.get("/api/v1/matches/1/goalkeeper-shots", headers=headers)
        other_match = client.get("/api/v1/matches/2/goalkeeper-shots", headers=headers)

        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == sorted(created)
        assert [item["origin_zone"] for item in listed.json()] == ["6m_center", "wing_right", "seven_meter"]
        assert other_match.json() == []
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_delete_goalkeeper_shot_is_scoped_by_match(tmp_path):
    client, engine = goalkeeper_client(tmp_path)
    headers = auth_headers()
    shot_id = client.post(
        "/api/v1/matches/1/goalkeeper-shots",
        json={"outcome": "goal"},
        headers=headers,
    ).json()["id"]

    try:
        wrong_match = client.delete(f"/api/v1/matches/2/goalkeeper-shots/{shot_id}", headers=headers)
        assert wrong_match.status_code == 404

        deleted = client.delete(f"/api/v1/matches/1/goalkeeper-shots/{shot_id}", headers=headers)
        assert deleted.status_code == 204

        missing = client.delete(f"/api/v1/matches/1/goalkeeper-shots/{shot_id}", headers=headers)
        assert missing.status_code == 404

        listed = client.get("/api/v1/matches/1/goalkeeper-shots", headers=headers)
        assert listed.json() == []
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_goalkeeper_shot_routes_require_authentication(tmp_path):
    client, engine = goalkeeper_client(tmp_path)

    try:
        listed = client.get("/api/v1/matches/1/goalkeeper-shots")
        created = client.post("/api/v1/matches/1/goalkeeper-shots", json={})
        deleted = client.delete("/api/v1/matches/1/goalkeeper-shots/1")

        assert listed.status_code == 403
        assert created.status_code == 403
        assert deleted.status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

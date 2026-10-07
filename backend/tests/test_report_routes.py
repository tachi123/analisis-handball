from datetime import date, datetime, timezone
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import reports
from app.database import Base, get_db
from app.main import app
from app.models import Match, RecoveryArtifact, ReportPackage, ReportPackageEvidence, ReportPublication, Team, User
from app.security import create_access_token


class FakeAdapter:
    def __init__(self):
        self.projections = []

    def upsert(self, projection):
        self.projections.append(projection)


@pytest.fixture
def report_client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'report-routes.db'}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    with session_factory() as session:
        package = ReportPackage(
            id=1,
            match=Match(id=1, date=date(2026, 8, 22), home_team=Team(name="SAPA"), away_team=Team(name="Banfield")),
            analyst_id=1,
            coaching_question="How do we defend the pivot?",
            pattern_statement="The pivot lane remained open.",
            action_kind="change",
            action_text="Close the pivot lane.",
            uncertainty_disclosure="One sequence was outside camera view.",
        )
        package.evidence = [
            ReportPackageEvidence(reference=f"Sequence {index}", period=1, public_approved=True)
            for index in range(3)
        ]
        session.add_all([User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst"), package])
        session.commit()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, session_factory
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def headers():
    return {"Authorization": f"Bearer {create_access_token({'sub': '1'})}"}


def test_publication_control_routes_require_authentication(report_client):
    client, _ = report_client
    responses = [
        client.get("/api/v1/report-packages/1/publication-status"),
        client.put("/api/v1/report-packages/1/recovery-artifacts/postgres_dump", json={"location": "dump"}),
        client.post("/api/v1/report-packages/1/publish"),
    ]
    assert [response.status_code for response in responses] == [403, 403, 403]


def test_recovery_status_identifies_missing_artifacts_and_exposes_only_safe_fields(report_client):
    client, _ = report_client
    response = client.get("/api/v1/report-packages/1/publication-status", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "package_id": 1, "report_version": 1, "status": "not_ready",
        "missing_recovery_artifacts": ["imported_pdf_export", "postgres_dump"],
        "recovery_artifacts": [], "published_at": None, "failure_message": None, "public_url": None,
    }

    artifact = client.put(
        "/api/v1/report-packages/1/recovery-artifacts/postgres_dump",
        json={"location": "C:/recovery/dump"}, headers=headers(),
    )
    status = client.get("/api/v1/report-packages/1/publication-status", headers=headers())
    assert artifact.status_code == 200
    assert artifact.json()["attested_at"] is not None
    assert status.json()["missing_recovery_artifacts"] == ["imported_pdf_export"]
    assert "attested_by_user_id" not in str(status.json())


def test_publish_retry_and_another_ready_package_overwrite_current_projection(report_client, monkeypatch):
    client, session_factory = report_client
    adapter = FakeAdapter()
    monkeypatch.setattr(reports, "report_adapter_factory", lambda: adapter)
    missing = client.post("/api/v1/report-packages/1/publish", headers=headers())
    assert missing.status_code == 409
    assert "postgres_dump" in missing.json()["detail"]

    for artifact_type in ("postgres_dump", "imported_pdf_export"):
        response = client.put(
            f"/api/v1/report-packages/1/recovery-artifacts/{artifact_type}",
            json={"location": f"C:/recovery/{artifact_type}"}, headers=headers(),
        )
        assert response.status_code == 200
    with session_factory() as db:
        db.get(ReportPackage, 1).approved_at = datetime.now(timezone.utc)
        db.commit()

    first = client.post("/api/v1/report-packages/1/publish", headers=headers())
    retry = client.post("/api/v1/report-packages/1/publish", headers=headers())
    assert first.status_code == retry.status_code == 200
    assert first.json()["status"] == retry.json()["status"] == "published"

    with session_factory() as db:
        replacement = ReportPackage(
            match_id=1, analyst_id=1, coaching_question="How do we stop wing shots?",
            pattern_statement="The wing remained open.", action_kind="change",
            action_text="Close the wing.", uncertainty_disclosure="None.", approved_at=datetime.now(timezone.utc),
        )
        replacement.evidence = [ReportPackageEvidence(reference=f"Wing {index}", period=1, public_approved=True) for index in range(3)]
        db.add(replacement)
        db.flush()
        db.add_all([
            RecoveryArtifact(package_id=replacement.id, artifact_type="postgres_dump", location="dump", attested_at=datetime.now(timezone.utc)),
            RecoveryArtifact(package_id=replacement.id, artifact_type="imported_pdf_export", location="pdf", attested_at=datetime.now(timezone.utc)),
        ])
        db.commit()
        replacement_id = replacement.id

    overwrite = client.post(f"/api/v1/report-packages/{replacement_id}/publish", headers=headers())
    with session_factory() as db:
        assert overwrite.status_code == 200
        assert db.query(ReportPublication).filter_by(package_id=1).count() == 1
        assert db.query(ReportPublication).filter_by(package_id=replacement_id).count() == 1
    assert [item["coaching"]["question"] for item in adapter.projections] == [
        "How do we defend the pivot?", "How do we defend the pivot?", "How do we stop wing shots?"
    ]


def test_anonymous_local_reader_returns_only_file_mode_projection(report_client, tmp_path, monkeypatch):
    client, _ = report_client
    target = tmp_path / "current-report.json"
    projection = {"schema_version": "public-report-v1", "report_version": 1, "metrics": {}}
    target.write_text(json.dumps(projection), encoding="utf-8")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("REPORT_PUBLISHER", "file")
    monkeypatch.setenv("LOCAL_PUBLIC_REPORT_FILE", str(target))
    response = client.get("/api/v1/public/reports/current")
    assert response.status_code == 200
    assert response.json() == projection


def test_anonymous_reader_is_unavailable_outside_file_mode(report_client, monkeypatch):
    client, _ = report_client
    monkeypatch.setenv("REPORT_PUBLISHER", "google")
    assert client.get("/api/v1/public/reports/current").status_code == 404

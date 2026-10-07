from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.api.routes import reports
from app.deps import get_current_user
from app.models import AnalysisCodebookEntry, Match, RecoveryArtifact, ReportPackage, ReportPackageEvidence, ReportPublication, Team, User
from app.models import CanonicalEvent, CanonicalEventRevision
from app.schemas import AnalysisEventCreate, ReportPackageCreate, ReportPackageUpdate, ReviewedReportPackage
from app.services.analysis_event_service import AnalysisEventService
from app.services.analysis_service import AnalysisService
from app.services.report_service import ReportService
from app.services.sheets_service import (
    FileReportAdapter,
    GoogleSheetsAdapter,
    SheetsConfigurationError,
    get_report_adapter,
    validate_report_publisher_configuration,
)


def package_with_evidence(session):
    home = Team(name="SAPA")
    away = Team(name="Banfield")
    match = Match(date=date(2026, 8, 22), home_team=home, away_team=away)
    analyst = User(email="analyst@example.com", hashed_password="x", full_name="Analyst")
    package = ReportPackage(match=match, analyst_id=1, coaching_question="How do we defend the pivot?", pattern_statement="Three visible actions need adjustment.", action_kind="change", action_text="Close the pivot lane.", uncertainty_disclosure="One observation was outside the camera view.", metrics={"defensive_action": {"count": 3, "denominator": "not_applicable", "private": "omit"}, "unsupported": {"count": 9}}, reconciliation=[{"side": "home", "official": 28, "analytical": 27}], source_label="Match broadcast", source_status="public_reference")
    package.evidence = [
        ReportPackageEvidence(reference="Defensive sequence", period=1, regulation_seconds=120.0, public_observation="Pivot lane remained open.", private_note="Discuss player positioning privately.", public_media_url="https://example.test/private", public_approved=True, media_public_approved=False),
        ReportPackageEvidence(reference="Recovery sequence", period=2, regulation_seconds=None, clock_unverified=True, public_observation="Recovery followed the turnover.", public_media_url="https://example.test/approved", public_approved=True, media_public_approved=True),
        ReportPackageEvidence(reference="Transition sequence", period=2, regulation_seconds=130.0, public_observation="Transition recovered shape.", public_approved=True),
        ReportPackageEvidence(reference="Private sequence", period=2, regulation_seconds=140.0, private_note="Do not publish.", public_approved=False),
    ]
    session.add_all([home, away, match, analyst, package])
    session.commit()
    return package


def test_projection_contains_only_public_report_fields():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    package = package_with_evidence(session)

    projection = ReportService.public_projection(package)

    assert projection["schema_version"] == "public-report-v1"
    assert projection["report_version"] == 1
    assert projection["match"] == {"date": "2026-08-22", "home_team": "SAPA", "away_team": "Banfield"}
    assert projection["evidence"][0]["media_available"] is False
    assert "media_url" not in projection["evidence"][0]
    assert projection["evidence"][1]["media_url"] == "https://example.test/approved"
    assert len(projection["evidence"]) == 3
    assert projection["metrics"] == {"defensive_action": {"count": 3, "denominator": "not_applicable"}}
    assert "private_note" not in str(projection)
    assert "analysis_event_id" not in str(projection)
    engine.dispose()


def test_recovery_readiness_requires_attested_dump_and_pdf_export():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    package = package_with_evidence(session)

    session.add(RecoveryArtifact(package=package, artifact_type="postgres_dump", location="C:/recovery/dump", attested_at=datetime.now(timezone.utc)))
    session.commit()
    assert ReportService.publication_readiness(package) == {"approved": False, "missing_recovery_artifacts": ["imported_pdf_export"], "ready": False}

    package.approved_at = datetime.now(timezone.utc)
    session.add(RecoveryArtifact(package=package, artifact_type="imported_pdf_export", location="C:/recovery/pdfs", attested_at=datetime.now(timezone.utc)))
    session.commit()
    assert ReportService.publication_readiness(package) == {"approved": True, "missing_recovery_artifacts": [], "ready": True}
    engine.dispose()


class FakeSheetsService:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = []

    def spreadsheets(self):
        return self

    def values(self):
        return self

    def batchUpdate(self, **kwargs):
        self.calls.append(kwargs)
        return self

    def execute(self):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeAdapter:
    def __init__(self):
        self.projections = []

    def upsert(self, projection):
        self.projections.append(projection)


def test_publish_retries_one_batch_upsert_and_omits_restricted_fields(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    package = package_with_evidence(session)
    package.approved_at = datetime.now(timezone.utc)
    session.add_all([
        RecoveryArtifact(package=package, artifact_type="postgres_dump", location="dump", attested_at=datetime.now(timezone.utc)),
        RecoveryArtifact(package=package, artifact_type="imported_pdf_export", location="pdf", attested_at=datetime.now(timezone.utc)),
    ])
    session.commit()
    fake = FakeSheetsService([TimeoutError(), {"updatedCells": 2}, {"updatedCells": 2}])
    adapter = GoogleSheetsAdapter(spreadsheet_id="sheet-id", service=fake, sleep=lambda _: None)
    monkeypatch.setattr(reports, "report_adapter_factory", lambda: adapter)

    first = reports.publish_report(package.id, db=session, _user=None)
    second = reports.publish_report(package.id, db=session, _user=None)

    assert first["status"] == second["status"] == "published"
    assert session.query(ReportPublication).filter_by(package_id=package.id, report_version=1).count() == 1
    assert len(fake.calls) == 3
    call = fake.calls[0]
    assert call["spreadsheetId"] == "sheet-id"
    assert call["body"]["valueInputOption"] == "RAW"
    assert [item["range"] for item in call["body"]["data"]] == ["PublicReports!A1", "PublicReports!A2"]
    payload = call["body"]["data"][0]["values"][0][0]
    assert "private_note" not in payload
    assert "https://example.test/private" not in payload
    engine.dispose()


def test_publish_another_ready_package_directly_replaces_current_projection():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    package = package_with_evidence(session)
    package.approved_at = datetime.now(timezone.utc)
    session.add_all([
        RecoveryArtifact(package=package, artifact_type="postgres_dump", location="dump", attested_at=datetime.now(timezone.utc)),
        RecoveryArtifact(package=package, artifact_type="imported_pdf_export", location="pdf", attested_at=datetime.now(timezone.utc)),
    ])
    session.commit()
    adapter = FakeAdapter()

    replacement = ReportPackage(
        match=package.match,
        analyst_id=package.analyst_id,
        coaching_question="How do we stop wing shots?",
        pattern_statement=package.pattern_statement,
        action_kind=package.action_kind,
        action_text=package.action_text,
        uncertainty_disclosure=package.uncertainty_disclosure,
    )
    replacement.evidence = [
        ReportPackageEvidence(reference="Wing sequence", period=1, public_approved=True)
    ]
    replacement.approved_at = datetime.now(timezone.utc)
    session.add(replacement)
    session.flush()
    session.add_all([
        RecoveryArtifact(package=replacement, artifact_type="postgres_dump", location="dump-2", attested_at=datetime.now(timezone.utc)),
        RecoveryArtifact(package=replacement, artifact_type="imported_pdf_export", location="pdf-2", attested_at=datetime.now(timezone.utc)),
    ])
    session.commit()

    first = ReportService.publish(session, package, lambda: adapter)
    second = ReportService.publish(session, replacement, lambda: adapter)
    repeated = ReportService.publish(session, replacement, lambda: adapter)

    assert first.report_version == 1
    assert second.id == repeated.id
    assert session.query(ReportPublication).filter_by(package_id=replacement.id).count() == 1
    assert [projection["coaching"]["question"] for projection in adapter.projections] == [
        package.coaching_question,
        replacement.coaching_question,
        replacement.coaching_question,
    ]
    engine.dispose()


def test_sheets_adapter_requires_environment_configuration(monkeypatch):
    monkeypatch.delenv("GOOGLE_SHEETS_ID", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS_JSON", raising=False)
    monkeypatch.delenv("REPORT_PUBLISHER", raising=False)
    with pytest.raises(SheetsConfigurationError, match="GOOGLE_SHEETS_ID"):
        GoogleSheetsAdapter()
    with pytest.raises(SheetsConfigurationError, match="credentials"):
        GoogleSheetsAdapter(spreadsheet_id="sheet-id").upsert({"schema_version": "public-report-v1", "report_version": 1})
    with pytest.raises(SheetsConfigurationError, match="GOOGLE_SHEETS_ID"):
        get_report_adapter()


def test_file_adapter_atomically_replaces_and_reads_exact_projection(tmp_path, monkeypatch):
    target = tmp_path / "current-report.json"
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("REPORT_PUBLISHER", "file")
    monkeypatch.setenv("LOCAL_PUBLIC_REPORT_FILE", str(target))
    first = {"schema_version": "public-report-v1", "report_version": 1, "metrics": {"count": 1}}
    replacement = {"schema_version": "public-report-v1", "report_version": 2, "metrics": {"count": 2}}

    validate_report_publisher_configuration()
    adapter = get_report_adapter()
    assert isinstance(adapter, FileReportAdapter)
    adapter.upsert(first)
    adapter.upsert(replacement)

    assert adapter.read() == replacement
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize(
    ("environment", "match"),
    [
        ({"REPORT_PUBLISHER": "file", "APP_ENV": "production", "LOCAL_PUBLIC_REPORT_FILE": "C:/report.json"}, "APP_ENV"),
        ({"REPORT_PUBLISHER": "file", "APP_ENV": "development"}, "LOCAL_PUBLIC_REPORT_FILE"),
        ({"REPORT_PUBLISHER": "unsafe"}, "REPORT_PUBLISHER"),
    ],
)
def test_report_publisher_configuration_rejects_unsafe_modes(monkeypatch, environment, match):
    for name in ("APP_ENV", "REPORT_PUBLISHER", "LOCAL_PUBLIC_REPORT_FILE"):
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(SheetsConfigurationError, match=match):
        validate_report_publisher_configuration()


def test_publish_route_reports_missing_recovery_artifacts():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    package = package_with_evidence(session)

    with pytest.raises(HTTPException) as error:
        reports.publish_report(package.id, db=session, _user=None)

    assert error.value.status_code == 409
    assert "imported_pdf_export" in error.value.detail
    engine.dispose()


def package_input(approved_evidence=0, action_kind="change"):
    return {
        "coaching_question": "How do we defend the pivot?",
        "pattern_statement": "The pivot lane stayed open.",
        "action_kind": action_kind,
        "action_text": "Close the pivot lane.",
        "uncertainty_disclosure": "One sequence was outside camera view.",
        "evidence": [
            {
                "reference": f"Sequence {index}",
                "period": 1,
                "public_observation": "The pivot lane remained open.",
                "public_approved": index < approved_evidence,
            }
            for index in range(max(approved_evidence, 1))
        ],
    }


def test_reviewed_package_routes_create_retrieve_edit_and_approve():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    home = Team(name="SAPA")
    away = Team(name="Banfield")
    analyst = User(email="analyst@example.com", hashed_password="x", full_name="Analyst")
    match = Match(date=date(2026, 8, 22), home_team=home, away_team=away)
    session.add_all([home, away, analyst, match])
    session.commit()

    created = reports.create_report_package(
        match.id, ReportPackageCreate(**package_input()), db=session, user=analyst
    )
    retrieved = reports.get_report_package(created.id, db=session, _user=analyst)
    updated = reports.update_report_package(
        created.id, ReportPackageUpdate(**package_input(approved_evidence=3)), db=session, _user=analyst
    )
    approved = reports.approve_report_package(created.id, db=session, _user=analyst)

    assert retrieved.id == created.id
    assert updated.evidence[0].public_approved is True
    assert approved.approved_at is not None
    engine.dispose()


def test_prepared_package_keeps_no_visible_observation_unknown():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    match = Match(id=1, date=date(2026, 8, 22), home_team=Team(name="SAPA"), away_team=Team(name="Banfield"))
    session.add_all([analyst, match, AnalysisCodebookEntry(version="mvp-1", code="shot", category="attack")])
    session.commit()

    confirmed = AnalysisEventService.create(
        session, match.id, AnalysisEventCreate(code="shot", outcome="goal", evidence_state="confirmed"), analyst
    )
    no_visible = AnalysisEventService.create(
        session, match.id, AnalysisEventCreate(code="shot", outcome="goal", evidence_state="no_visible"), analyst
    )
    reviewed = AnalysisService.reviewed_metrics(session, match.id)
    package = ReportService.create(session, match.id, ReportPackageCreate(
        coaching_question="What should we change in shot selection?",
        pattern_statement="The confirmed goal is actionable; one outcome was not visible.",
        action_kind="change",
        action_text="Create a clearer shooting lane.",
        uncertainty_disclosure="One reviewed observation had no visible outcome.",
        metrics=reviewed["metrics"],
        reconciliation=reviewed["reconciliation"],
        evidence=[
            {"reference": f"Confirmed event {confirmed.id}", "period": 1, "public_observation": "Goal confirmed.", "public_approved": True},
            {"reference": "Shot sequence 2", "period": 1, "public_observation": "Lane was available.", "public_approved": True},
            {"reference": "Shot sequence 3", "period": 2, "public_observation": "Support arrived late.", "public_approved": True},
        ],
    ), analyst)
    projection = ReportService.public_projection(package)

    assert reviewed["metrics"] == {}
    assert reviewed["eligibility"] == {"eligible": 0, "excluded": 0, "unknown": 0, "clock_unverified": 0, "unresolved": 0}
    assert no_visible.id not in [item.analysis_event_id for item in package.evidence]
    assert [item["reference"] for item in projection["evidence"]] == [
        f"Confirmed event {confirmed.id}", "Shot sequence 2", "Shot sequence 3",
    ]
    assert projection["metrics"] == {}
    assert projection["coaching"]["action"] == {"kind": "change", "text": "Create a clearer shooting lane."}
    assert "private_note" not in str(projection)
    assert "media_url" not in str(projection)
    engine.dispose()


def test_canonical_report_rejects_ineligible_evidence_and_derives_its_metrics():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    home, away = Team(id=1, name="Home"), Team(id=2, name="Away")
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    match = Match(id=1, home_team=home, away_team=away)
    event = CanonicalEvent(id=1, match=match, sequence=1)
    event.revisions = [CanonicalEventRevision(revision=1, actor_id=1, reason="created", payload={"kind": "shot", "period": 1, "team_id": 1, "player_id": None, "outcome": "goal", "clock_unverified": False, "fact_kind": "observed", "evidence_state": "confirmed", "uncertainty": []})]
    session.add_all([home, away, analyst, match, event])
    session.commit()
    data = package_input(approved_evidence=1)
    data.update({"source_status": "canonical", "canonical_event_ids": [1], "metrics": {"forged": {"count": 9}}})
    package = ReportService.create(session, 1, ReportPackageCreate(**data), analyst)
    assert package.metrics["shots"]["count"] == 1
    with pytest.raises(ValueError, match="must be recreated"):
        ReportService.update(session, package, ReportPackageUpdate(**data))
    data["canonical_event_ids"] = [99]
    with pytest.raises(ValueError, match="unsupported or ineligible"):
        ReportService.create(session, 1, ReportPackageCreate(**data), analyst)
    engine.dispose()


def test_cutover_match_rejects_free_form_reports_and_derives_selected_evidence():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    home, away = Team(id=1, name="Home"), Team(id=2, name="Away")
    analyst = User(id=1, email="analyst@example.com", hashed_password="x", full_name="Analyst")
    match = Match(id=1, home_team=home, away_team=away, canonical_analysis_enabled=True)
    event = CanonicalEvent(id=7, match=match, sequence=1)
    event.revisions = [CanonicalEventRevision(revision=3, actor_id=1, reason="created", payload={"kind": "shot",
                       "period": 2, "team_id": 1, "player_id": None, "outcome": "goal", "regulation_seconds": 300.0,
                       "clock_unverified": True, "fact_kind": "observed", "evidence_state": "confirmed", "uncertainty": []})]
    session.add_all([home, away, analyst, match, event])
    session.commit()
    data = package_input(approved_evidence=1)
    data.update({"metrics": {"forged": {"count": 9}}, "reconciliation": [{"side": "home", "official": 0, "analytical": 99}],
                 "source_status": None})
    with pytest.raises(ValueError, match="requires selected eligible event evidence"):
        ReportService.create(session, 1, ReportPackageCreate(**data), analyst)
    data.update({"canonical_event_ids": [7]})
    package = ReportService.create(session, 1, ReportPackageCreate(**data), analyst)
    assert package.source_status == "canonical-eligible"
    assert package.metrics["shots"]["count"] == 1
    assert "forged" not in package.metrics
    assert len(package.evidence) == 1
    assert package.evidence[0].reference == "canonical:7:rev:3"
    assert package.evidence[0].period == 2 and package.evidence[0].clock_unverified is True
    engine.dispose()


def test_package_approval_returns_clear_validation_errors():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    package = package_with_evidence(session)
    package.evidence[2].public_approved = False
    session.commit()

    with pytest.raises(HTTPException, match="3 to 8 approved evidence") as error:
        reports.approve_report_package(package.id, db=session, _user=None)

    assert error.value.status_code == 422
    package.evidence[0].public_approved = True
    package.evidence[1].public_approved = True
    package.evidence[2].public_approved = True
    package.action_kind = "unsupported"
    session.commit()
    with pytest.raises(HTTPException, match="exactly one keep, do, or change action") as error:
        reports.approve_report_package(package.id, db=session, _user=None)

    assert error.value.status_code == 422
    engine.dispose()


def test_approved_package_cannot_be_edited_after_validation():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    package = package_with_evidence(session)
    package.evidence[2].public_approved = True
    ReportService.approve(session, package)

    with pytest.raises(ValueError, match="cannot be edited"):
        ReportService.update(session, package, ReportPackageUpdate(**package_input(approved_evidence=3)))

    engine.dispose()


def test_reviewed_package_response_omits_restricted_evidence_fields():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    package = package_with_evidence(session)

    response = ReviewedReportPackage.model_validate(package).model_dump()

    assert "private_note" not in str(response)
    assert "public_media_url" not in str(response)
    engine.dispose()


def test_reviewed_package_routes_require_authentication():
    package_routes = [route for route in reports.router.routes if "report-packages" in route.path]

    assert package_routes
    assert all(
        any(dependency.call is get_current_user for dependency in route.dependant.dependencies)
        for route in package_routes
    )

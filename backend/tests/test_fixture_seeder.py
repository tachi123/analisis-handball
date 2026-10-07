import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic import command
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Club, CompetitionTeam, FixtureImport, FixtureImportEntry, Round, ScheduledMatch, TeamRegistration
from app.services.fixture_seeder import import_fixture, load_fixture


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data/fixtures/clausura-permanencia-rounds-1-3.json"


def migrated_session(migrated_db):
    return sessionmaker(bind=migrated_db)()


@pytest.fixture
def fixture_database(alembic_config):
    config, database_url = alembic_config
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    yield engine
    engine.dispose()


def test_curated_fixture_imports_source_facts_after_real_migration(fixture_database):
    payload, raw_payload = load_fixture(str(FIXTURE_PATH))
    session = migrated_session(fixture_database)
    try:
        summary = import_fixture(session, payload, raw_payload)
        audit = session.query(FixtureImport).one()
        scheduled = session.query(ScheduledMatch).filter_by(match_number_label="r2-8").one()
        played = session.query(ScheduledMatch).filter_by(match_number_label="r1-1").one()
        round_three = session.query(ScheduledMatch).filter_by(match_number_label="r3-5").one()
        assert summary.created == 19 and summary.byes == 5
        assert audit.source_label == "analyst-copied fixture text"
        assert audit.source_sha256 == hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
        assert audit.payload["source"]["fixture_title"] == "Torneo Metropolitano Clausura Permanencia | Mayores - 4º División - Masculino"
        assert audit.payload["source"]["organizer"] == "Federación Metropolitana de Balonmano (FEMEBAL)"
        assert audit.payload["source"]["updated_at"] == "2026-08-24 15:31"
        assert session.query(Round).count() == 3
        assert (played.status, played.source_home_score, played.source_away_score, played.result_status) == ("played", 27, 23, "reported")
        assert (round_three.status, round_three.source_home_score, round_three.source_away_score) == ("played", 28, 20)
        assert (scheduled.status, scheduled.scheduled_date.isoformat(), scheduled.match_time, scheduled.source_home_score, scheduled.source_away_score, scheduled.result_status) == ("scheduled", "2026-08-25", "21:00", None, None, "unreported")
        assert (scheduled.home_registration.competition_team.club.name, scheduled.home_registration.competition_team.variant) == ("Municipalidad de Escobar", "B")
        assert (scheduled.away_registration.competition_team.club.name, scheduled.away_registration.competition_team.variant) == ("Municipalidad de Almirante Brown", "B")
        assert {team.variant for team in session.query(CompetitionTeam)} >= {None, "B", "C", "D"}
        byes = session.query(FixtureImportEntry).filter_by(kind="bye").all()
        assert len(byes) == 5 and all(entry.scheduled_match_id is None for entry in byes)
        assert any(entry.raw_entry["source_text"] == "Circulo General Belgrano 2–0 Fe.Me.Bal. Libre 2" for entry in byes)
        assert session.query(Club).filter(Club.name.like("%Libre%")).count() == 0
        assert session.query(TeamRegistration).count() == 14
    finally:
        session.close()


def test_corrected_schedule_reimport_preserves_imported_fixture_key(fixture_database):
    payload, raw_payload = load_fixture(str(FIXTURE_PATH))
    session = migrated_session(fixture_database)
    try:
        import_fixture(session, payload, raw_payload)
        match = session.query(ScheduledMatch).filter_by(match_number_label="r2-8").one()
        fixture_key = match.fixture_key
        session.commit()

        corrected = copy.deepcopy(payload)
        corrected["source"]["updated_at"] = "2026-08-24 15:34"
        entry = next(entry for entry in corrected["rounds"][1]["entries"] if entry["entry_key"] == "r2-8")
        entry["date"], entry["time"] = "2026-08-26", "20:30"
        import_fixture(session, corrected, json.dumps(corrected))

        corrected_match = session.query(ScheduledMatch).filter_by(match_number_label="r2-8").one()
        assert corrected_match.fixture_key == fixture_key
        assert (corrected_match.scheduled_date.isoformat(), corrected_match.match_time) == ("2026-08-26", "20:30")
    finally:
        session.close()


def test_local_fixture_import_never_calls_network_or_pdf_services(fixture_database):
    from app.services.pdf_service import PDFService

    payload, raw_payload = load_fixture(str(FIXTURE_PATH))
    session = migrated_session(fixture_database)
    try:
        with (
            patch("socket.create_connection", side_effect=AssertionError("network access is forbidden")),
            patch("urllib.request.urlopen", side_effect=AssertionError("network access is forbidden")),
            patch.object(PDFService, "preview_femebal_sheet", side_effect=AssertionError("PDF access is forbidden")),
            patch.object(PDFService, "save_pdf", side_effect=AssertionError("PDF access is forbidden")),
            patch.object(PDFService, "confirm_import", side_effect=AssertionError("PDF access is forbidden")),
        ):
            assert import_fixture(session, payload, raw_payload).created == 19
    finally:
        session.close()


def test_curated_fixture_rerun_extension_and_approved_results_are_safe(fixture_database):
    payload, raw_payload = load_fixture(str(FIXTURE_PATH))
    session = migrated_session(fixture_database)
    try:
        initial = copy.deepcopy(payload)
        initial["rounds"] = initial["rounds"][:1]
        assert import_fixture(session, initial, json.dumps(initial)).created == 7
        extension = copy.deepcopy(payload)
        extension["source"]["updated_at"] = "2026-08-24 15:32"
        extension["rounds"] = extension["rounds"][:2]
        assert import_fixture(session, extension, json.dumps(extension)).created == 6
        assert session.query(ScheduledMatch).count() == 13
        session.commit()
        assert import_fixture(session, payload, raw_payload).created == 6
        assert import_fixture(session, payload, raw_payload).skipped == 1
        protected = session.query(ScheduledMatch).filter_by(match_number_label="r1-1").one()
        omitted = session.query(ScheduledMatch).filter_by(match_number_label="r1-2").one()
        protected.result_status = omitted.result_status = "approved"
        session.commit()
        corrected = copy.deepcopy(payload)
        corrected["source"]["updated_at"] = "2026-08-24 15:33"
        corrected["rounds"][0]["entries"][0]["result"] = {"home": 1, "away": 2, "status": "reported"}
        corrected["rounds"][0]["entries"][1].pop("result")
        import_fixture(session, corrected, json.dumps(corrected))
        assert (protected.source_home_score, protected.source_away_score, protected.result_status) == (27, 23, "approved")
        assert (omitted.source_home_score, omitted.source_away_score, omitted.result_status) == (28, 13, "approved")
    finally:
        session.close()

import pytest

from app.models import Club, FixtureImport, FixtureImportEntry, ScheduledMatch
from app.services.fixture_seeder import FixtureValidationError, import_fixture, validate_fixture


def fixture(result=None):
    entry = {"entry_key": "r1-1", "kind": "match", "home": {"club": "SAPA", "variant": None}, "away": {"club": "Banfield", "variant": "B"}, "date": "2026-08-22", "time": "20:00"}
    if result:
        entry["result"] = result
    return {"source": {"label": "analyst copy", "captured_at": "2026-08-24"}, "stage": {"season": 2026, "name": "Clausura Permanencia", "category": "Mayores", "division": "4º División", "gender": "Masculino"}, "rounds": [{"number": 1, "entries": [entry, {"entry_key": "r1-bye", "kind": "bye", "team": {"club": "Libre side", "variant": None}, "source_text": "Libre"}]}]}


def test_validation_rejects_duplicate_keys_and_same_registration():
    payload = fixture()
    payload["rounds"][0]["entries"].append(payload["rounds"][0]["entries"][0].copy())
    with pytest.raises(FixtureValidationError):
        validate_fixture(payload)
    payload = fixture()
    payload["rounds"][0]["entries"][0]["away"] = {"club": "SAPA", "variant": None}
    with pytest.raises(FixtureValidationError):
        validate_fixture(payload)


def test_import_audits_bye_without_creating_bye_entities(session):
    summary = import_fixture(session, fixture({"home": 28, "away": 24, "status": "reported"}))
    assert summary.created == 1 and summary.byes == 1
    assert session.query(FixtureImport).count() == 1
    assert session.query(FixtureImportEntry).filter_by(kind="bye").count() == 1
    assert session.query(ScheduledMatch).one().fixture_key
    assert session.query(Club).filter_by(name="Libre side").count() == 0


def test_reimport_uses_hash_noop_and_preserves_approved_result(session):
    payload = fixture({"home": 28, "away": 24, "status": "reported"})
    import_fixture(session, payload)
    assert import_fixture(session, payload).skipped == 1
    match = session.query(ScheduledMatch).one()
    match.result_status, match.source_home_score, match.source_away_score = "approved", 28, 24
    session.commit()
    corrected = fixture({"home": 1, "away": 2, "status": "reported"})
    corrected["source"]["captured_at"] = "2026-08-25"
    import_fixture(session, corrected)
    assert (match.source_home_score, match.source_away_score, match.result_status) == (28, 24, "approved")


def test_import_honors_explicit_deterministic_fixture_key(session):
    payload = fixture()
    payload["rounds"][0]["entries"][0]["fixture_key"] = "planilla:deadbeef:1"

    import_fixture(session, payload)

    assert session.query(ScheduledMatch).one().fixture_key == "planilla:deadbeef:1"

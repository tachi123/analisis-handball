from datetime import date

import pytest
from sqlalchemy.orm import Query

from app.models import Match, OfficialSnapshot, ScheduledMatch, StageRoster, Team, Tournament, User
from app.schemas import MatchCreate, MatchPDFConfirmation, MatchUpdate
from app.services.match_service import MatchService
from app.services.pdf_service import PDFService


def parsed_sheet(*, parsed_date="2026-10-04", home_score=2, away_score=1, warnings=None):
    return {
        "match_info": {"date": parsed_date, "home_score": home_score, "away_score": away_score},
        "home_team": {"name": "Home", "players": []},
        "away_team": {"name": "Away", "players": []},
        "fields": {}, "warnings": warnings or [],
        "provenance": {"filename": "sheet.pdf", "content_type": "application/pdf", "size_bytes": 1, "sha256": "a", "page_count": 1},
    }


def manual_context(session, *, match_date=date(2026, 10, 4)):
    owner = User(email="owner@example.com", hashed_password="x", full_name="Owner")
    other = User(email="other@example.com", hashed_password="x", full_name="Other")
    admin = User(email="admin@example.com", hashed_password="x", full_name="Admin", role="admin")
    home, away = Team(name="Home"), Team(name="Away")
    session.add_all([owner, other, admin, home, away])
    session.flush()
    match = Match(date=match_date, home_team_id=home.id, away_team_id=away.id, home_score=2, away_score=1, origin="manual", created_by_user_id=owner.id)
    imported = Match(date=match_date, home_team_id=home.id, away_team_id=away.id, home_score=2, away_score=1, origin="fixture")
    session.add_all([match, imported])
    session.commit()
    return owner, other, admin, match, imported, home, away


def confirmation():
    return MatchPDFConfirmation(home_players=[], away_players=[])


def test_manual_creation_allows_optional_date_and_tournament_without_fixture_writes(session):
    user = User(email="analyst@example.com", hashed_password="x", full_name="Analyst")
    home, away = Team(name="Home"), Team(name="Away")
    session.add_all([user, home, away]); session.commit()

    created = MatchService.create(session, MatchCreate(home_team_id=home.id, away_team_id=away.id), user)

    assert (created.origin, created.created_by_user_id, created.date, created.tournament_id) == ("manual", user.id, None, None)
    assert session.query(ScheduledMatch).count() == session.query(StageRoster).count() == 0


def test_manual_ownership_checks_origin_before_admin_or_owner_authorization(session):
    owner, other, admin, match, imported, _, _ = manual_context(session)

    with pytest.raises(PermissionError):
        MatchService.require_manual_owner(session, match.id, other)
    assert MatchService.require_manual_owner(session, match.id, admin).id == match.id
    with pytest.raises(ValueError, match="solo está disponible para partidos manuales"):
        MatchService.require_manual_owner(session, imported.id, admin)
    with pytest.raises(ValueError, match="Solo los partidos manuales"):
        MatchService.update(session, imported.id, MatchUpdate(venue="x"), admin)
    assert MatchService.update(session, match.id, MatchUpdate(venue="x"), owner).venue == "x"


def test_manual_preview_is_read_only_and_rejects_imported_matches(session, monkeypatch):
    _, _, admin, match, imported, _, _ = manual_context(session)
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: parsed_sheet(warnings=["parser warning"])))

    preview = PDFService.match_preview(session, match.id, b"x", "sheet.pdf", "application/pdf")

    assert preview["warnings"] == ["parser warning"]
    assert session.query(OfficialSnapshot).count() == session.query(ScheduledMatch).count() == session.query(StageRoster).count() == 0
    with pytest.raises(ValueError, match="solo está disponible para partidos manuales"):
        PDFService.match_preview(session, imported.id, b"x", "sheet.pdf", "application/pdf")
    assert MatchService.require_manual_owner(session, match.id, admin).id == match.id


def test_manual_confirmation_is_idempotent_locks_match_and_never_writes_fixture_data(session, tmp_path, monkeypatch):
    _, _, _, match, _, _, _ = manual_context(session)
    monkeypatch.setattr(PDFService, "PDF_DIR", str(tmp_path))
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: parsed_sheet()))
    calls = []
    original = Query.with_for_update
    monkeypatch.setattr(Query, "with_for_update", lambda query, *args, **kwargs: (calls.append((args, kwargs)) or original(query, *args, **kwargs)))

    first = PDFService.confirm_match_pdf(session, match.id, b"x", "sheet.pdf", "application/pdf", confirmation())
    second = PDFService.confirm_match_pdf(session, match.id, b"x", "sheet.pdf", "application/pdf", confirmation())

    assert calls
    assert first["reused"] is False
    assert second == {**first, "reused": True}
    assert session.query(OfficialSnapshot).filter_by(match_id=match.id, is_confirmed=True).count() == 1
    assert session.query(ScheduledMatch).count() == session.query(StageRoster).count() == 0


def test_manual_confirmation_requires_date_when_neither_match_nor_pdf_provides_one(session, monkeypatch):
    _, _, _, match, _, _, _ = manual_context(session, match_date=None)
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: parsed_sheet(parsed_date=None)))

    with pytest.raises(ValueError, match="no informan una fecha"):
        PDFService.confirm_match_pdf(session, match.id, b"x", "sheet.pdf", "application/pdf", confirmation())
    assert session.query(OfficialSnapshot).count() == 0


def test_manual_confirmation_requires_explicit_reconciliation_acknowledgement(session, monkeypatch):
    _, _, _, match, _, _, _ = manual_context(session)
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: parsed_sheet(home_score=3)))

    with pytest.raises(ValueError, match="reconocer explícitamente"):
        PDFService.confirm_match_pdf(session, match.id, b"x", "sheet.pdf", "application/pdf", confirmation())
    accepted = PDFService.confirm_match_pdf(session, match.id, b"x", "sheet.pdf", "application/pdf", MatchPDFConfirmation(home_players=[], away_players=[], acknowledge_mismatches=True))
    assert accepted["reused"] is False

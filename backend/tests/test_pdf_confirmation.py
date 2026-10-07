from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Club, CompetitionTeam, FixtureImport, FixtureImportEntry, Match, MatchSquad, OfficialSnapshot, OfficialSnapshotPlayer, Player, Round, ScheduledMatch, Season, StageRoster, Team, TeamRegistration, TournamentStage
from app.schemas import FixtureConfirmation, FixtureRosterResolution, PDFImportConfirmation
from app.services.pdf_service import PDFService


SAMPLE_SHEET = (
    Path(__file__).resolve().parents[1]
    / "resources"
    / "planillas"
    / "planilla_banfield_b_vs_sapa.pdf"
)


def fixture_context(session, *, key="fixture:1", source_scores=(31, 31)):
    season = Season(year=2026)
    stage = TournamentStage(season=season, name="Stage", category="Senior", division="A", gender="F")
    home_club, away_club = Club(name="Banfield"), Club(name="SAPA")
    home_ct = CompetitionTeam(club=home_club, stage=stage, suffix="B")
    away_ct = CompetitionTeam(club=away_club, stage=stage)
    round_ = Round(stage=stage, round_number=1)
    home_reg = TeamRegistration(competition_team=home_ct, stage=stage)
    away_reg = TeamRegistration(competition_team=away_ct, stage=stage)
    fixture = ScheduledMatch(stage=stage, round=round_, home_registration=home_reg, away_registration=away_reg,
        match_number_label="1", fixture_key=key, scheduled_date=date(2026, 5, 31),
        source_home_score=source_scores[0], source_away_score=source_scores[1], result_status="reported")
    audit = FixtureImport(stage=stage, source_label="test", captured_at=datetime.now(timezone.utc), source_sha256=key, payload={})
    session.add_all([fixture, FixtureImportEntry(fixture_import=audit, entry_key="1", kind="match", raw_entry={}, scheduled_match=fixture)])
    home, away = Team(name="Banfield B"), Team(name="SAPA")
    session.add_all([home, away]); session.commit()
    return fixture, home, away


def parsed_sheet(home_score=31, away_score=31):
    return {"match_info": {"date": "2026-05-31", "home_score": home_score, "away_score": away_score},
            "home_team": {"name": "C.A. Banfield B", "players": []}, "away_team": {"name": "S.A.P.A.", "players": []},
            "fields": {}, "warnings": [], "provenance": {"filename": "sheet.pdf", "content_type": "application/pdf", "size_bytes": 1, "sha256": "a", "page_count": 1}}


def fixture_confirmation(home, away, **extra):
    return FixtureConfirmation(home_team_id=home.id, away_team_id=away.id, **extra)


def test_fixture_preview_rejects_unknown_or_bye_keys_and_writes_nothing(session, monkeypatch):
    fixture, _, _ = fixture_context(session)
    entry = fixture.fixture_import_entries[0]
    entry.kind = "bye"; session.commit()
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: parsed_sheet()))
    with pytest.raises(ValueError, match="no existe o es un bye"):
        PDFService.fixture_preview(session, fixture.fixture_key, b"x", "sheet.pdf", "application/pdf")
    assert session.query(Match).count() == session.query(OfficialSnapshot).count() == 0


def test_fixture_preview_is_read_only_and_checks_variant(session, monkeypatch):
    fixture, _, _ = fixture_context(session)
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: parsed_sheet()))
    result = PDFService.fixture_preview(session, fixture.fixture_key, b"x", "sheet.pdf", "application/pdf")
    assert result["home_compatibility"]["status"] == result["away_compatibility"]["status"] == "compatible"
    assert result["score_reconciliation"] == "match"
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: parsed_sheet(None, None)))
    assert PDFService.fixture_preview(session, fixture.fixture_key, b"x", "sheet.pdf", "application/pdf")["score_reconciliation"] == "unknown"
    assert session.query(Match).count() == session.query(OfficialSnapshot).count() == 0


def test_fixture_list_includes_imported_matches_and_excludes_byes(session):
    eligible, _, _ = fixture_context(session, key="fixture:eligible")
    bye = ScheduledMatch(
        stage_id=eligible.stage_id, round_id=eligible.round_id,
        home_registration_id=eligible.home_registration_id, away_registration_id=eligible.away_registration_id,
        match_number_label="bye", fixture_key="fixture:bye", scheduled_date=eligible.scheduled_date,
        result_status="unreported",
    )
    session.add_all([bye, FixtureImportEntry(
        fixture_import=eligible.fixture_import_entries[0].fixture_import,
        entry_key="bye", kind="bye", raw_entry={}, scheduled_match=bye,
    )])
    session.commit()

    assert [item.fixture_key for item in PDFService.list_fixtures(session)] == [eligible.fixture_key]
    assert PDFService.fixture_read(PDFService.list_fixtures(session)[0])["roster_status"] == "not_confirmed"
    match = Match(date=eligible.scheduled_date, scheduled_match=eligible, youtube_link=None)
    snapshot = OfficialSnapshot(id="confirmed", match=match, is_confirmed=True, source_filename="sheet.pdf", source_content_type="application/pdf", source_size_bytes=1, source_sha256="a", source_page_count=1, source_path="sheet.pdf", confirmed_date=eligible.scheduled_date, home_team_name="Banfield B", away_team_name="SAPA", home_score=31, away_score=31)
    session.add(snapshot); session.commit()

    fixtures = PDFService.list_fixtures(session)
    assert [fixture.fixture_key for fixture in fixtures] == [eligible.fixture_key]
    row = PDFService.fixture_read(fixtures[0])
    assert row["home_registration"] == {
        "id": eligible.home_registration_id, "display_name": "Banfield B", "variant": "B"
    }
    assert row["stage"] == {
        "id": eligible.stage_id, "season_year": 2026, "name": "Stage", "category": "Senior", "division": "A", "gender": "F",
    }
    assert (row["official_snapshot_id"], row["is_preloaded"], row["youtube_link"]) == ("confirmed", True, "")
    assert PDFService.preloaded_fixture(session, eligible.fixture_key).id == eligible.id
    with pytest.raises(ValueError, match="confirmada"):
        PDFService.preloaded_fixture(session, bye.fixture_key)


def test_confirmed_preload_requires_explicit_roster_resolution_then_populates_match_and_stage_rosters(session):
    fixture, home, _ = fixture_context(session)
    match = Match(date=fixture.scheduled_date, scheduled_match=fixture, home_team=home)
    snapshot = OfficialSnapshot(id="confirmed-roster", match=match, is_confirmed=True, source_filename="sheet.pdf", source_content_type="application/pdf", source_size_bytes=1, source_sha256="a", source_page_count=1, source_path="sheet.pdf", confirmed_date=fixture.scheduled_date, home_team_name="Banfield B", away_team_name="SAPA", home_score=31, away_score=31)
    row = OfficialSnapshotPlayer(snapshot=snapshot, side="home", name="Ana Gómez", jersey_number=7, official_goals=3, official_yellow=0, official_2min=0, official_red=0, official_blue=0)
    session.add(row); session.commit()

    before = PDFService.fixture_roster(session, fixture.fixture_key)
    assert before["fixture"]["roster_status"] == "needs_identity_resolution"
    assert before["players"][0]["candidates"] == []

    result = PDFService.resolve_fixture_roster(session, fixture.fixture_key, [FixtureRosterResolution(snapshot_player_id=row.id, create_player=True)])

    assert result == {"match_id": match.id, "roster_status": "ready", "unresolved_roster_players": 0}
    persisted = session.get(OfficialSnapshotPlayer, row.id)
    assert persisted.player_id is not None
    assert session.query(MatchSquad).filter_by(match_id=match.id, player_id=persisted.player_id).one().jersey_number == 7
    assert session.query(StageRoster).filter_by(registration_id=fixture.home_registration_id, player_id=persisted.player_id).one().jersey_number == 7


def test_roster_resolution_rejects_assigning_one_player_to_multiple_official_rows(session):
    fixture, home, _ = fixture_context(session)
    match = Match(date=fixture.scheduled_date, scheduled_match=fixture, home_team=home)
    snapshot = OfficialSnapshot(id="duplicate-roster", match=match, is_confirmed=True, source_filename="sheet.pdf", source_content_type="application/pdf", source_size_bytes=1, source_sha256="a", source_page_count=1, source_path="sheet.pdf", confirmed_date=fixture.scheduled_date, home_team_name="Banfield B", away_team_name="SAPA", home_score=31, away_score=31)
    first = OfficialSnapshotPlayer(snapshot=snapshot, side="home", name="Ana Gómez", jersey_number=7, official_goals=3, official_yellow=0, official_2min=0, official_red=0, official_blue=0)
    second = OfficialSnapshotPlayer(snapshot=snapshot, side="home", name="Ana Gómez", jersey_number=8, official_goals=0, official_yellow=0, official_2min=0, official_red=0, official_blue=0)
    player = Player(name="Ana Gómez", team_id=home.id, default_jersey_number=7)
    session.add_all([match, snapshot, first, second, player]); session.commit()

    with pytest.raises(ValueError, match="one player cannot resolve multiple official roster rows"):
        PDFService.resolve_fixture_roster(session, fixture.fixture_key, [
            FixtureRosterResolution(snapshot_player_id=first.id, existing_player_id=player.id),
            FixtureRosterResolution(snapshot_player_id=second.id, existing_player_id=player.id),
        ])

    assert [row.player_id for row in session.query(OfficialSnapshotPlayer).filter_by(snapshot_id=snapshot.id).order_by(OfficialSnapshotPlayer.id)] == [None, None]
    assert session.query(MatchSquad).filter_by(match_id=match.id).count() == 0


def test_roster_readiness_rejects_a_malformed_duplicate_player_projection(session):
    fixture, home, _ = fixture_context(session)
    match = Match(date=fixture.scheduled_date, scheduled_match=fixture, home_team=home)
    snapshot = OfficialSnapshot(id="malformed-roster", match=match, is_confirmed=True, source_filename="sheet.pdf", source_content_type="application/pdf", source_size_bytes=1, source_sha256="a", source_page_count=1, source_path="sheet.pdf", confirmed_date=fixture.scheduled_date, home_team_name="Banfield B", away_team_name="SAPA", home_score=31, away_score=31)
    player = Player(name="Ana Gómez", team_id=home.id, default_jersey_number=7)
    session.add_all([match, snapshot, player])
    session.flush()
    session.add_all([
        OfficialSnapshotPlayer(snapshot=snapshot, side="home", player_id=player.id, name="Ana Gómez", jersey_number=7, official_goals=3, official_yellow=0, official_2min=0, official_red=0, official_blue=0),
        OfficialSnapshotPlayer(snapshot=snapshot, side="home", player_id=player.id, name="Ana Gómez", jersey_number=8, official_goals=0, official_yellow=0, official_2min=0, official_red=0, official_blue=0),
        MatchSquad(match_id=match.id, player_id=player.id, jersey_number=7),
        StageRoster(registration_id=fixture.home_registration_id, player_id=player.id, jersey_number=7),
        StageRoster(registration_id=fixture.home_registration_id, player_id=player.id, jersey_number=8),
    ])
    session.commit()

    assert PDFService.fixture_read(PDFService.preloaded_fixture(session, fixture.fixture_key))["roster_status"] == "needs_identity_resolution"


def test_confirmed_fixture_never_reparses_or_reconfirms_uploaded_pdf(session, monkeypatch):
    fixture, _, _ = fixture_context(session)
    snapshot = OfficialSnapshot(id="confirmed-no-reconfirm", match=Match(date=fixture.scheduled_date, scheduled_match=fixture), is_confirmed=True, source_filename="sheet.pdf", source_content_type="application/pdf", source_size_bytes=1, source_sha256="a", source_page_count=1, source_path="sheet.pdf", confirmed_date=fixture.scheduled_date, home_team_name="Banfield B", away_team_name="SAPA", home_score=31, away_score=31)
    session.add(snapshot); session.commit()
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: (_ for _ in ()).throw(AssertionError("must not parse"))))

    result = PDFService.confirm_fixture(session, fixture.fixture_key, b"ignored", "ignored.pdf", "application/pdf", fixture_confirmation(*session.query(Team).order_by(Team.id).all()))

    assert result == {"match_id": snapshot.match_id, "snapshot_id": snapshot.id, "reused": True}


@pytest.mark.parametrize("home_name", ["C.A. Lanús B", "C.A. Banfield A"])
def test_fixture_confirmation_rejects_incompatible_parsed_side_or_variant(session, monkeypatch, home_name):
    fixture, home, away = fixture_context(session)
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(
        lambda *_: {**parsed_sheet(), "home_team": {"name": home_name, "players": []}}
    ))

    with pytest.raises(ValueError, match="no coincide"):
        PDFService.confirm_fixture(session, fixture.fixture_key, b"x", "sheet.pdf", "application/pdf", fixture_confirmation(home, away))

    assert session.query(Match).count() == session.query(OfficialSnapshot).count() == 0


def test_fixture_confirmation_rejects_identity_creation_and_unresolved_ids(session, monkeypatch):
    fixture, home, away = fixture_context(session)
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: parsed_sheet()))

    with pytest.raises(ValidationError):
        FixtureConfirmation.model_validate({
            "home_team_id": home.id, "away_team_id": away.id,
            "home_team": {"name": "New legacy team"},
        })
    with pytest.raises(ValidationError):
        FixtureConfirmation.model_validate({
            "home_team_id": home.id, "away_team_id": away.id,
            "home_players": [{"name": "New legacy player", "jersey_number": 7, "existing_player_id": 0}],
        })
    with pytest.raises(ValueError, match="equipo confirmado no existe"):
        PDFService.confirm_fixture(session, fixture.fixture_key, b"x", "sheet.pdf", "application/pdf",
            FixtureConfirmation(home_team_id=9999, away_team_id=away.id))

    assert session.query(Team).count() == 2
    assert session.query(Player).count() == session.query(Match).count() == session.query(OfficialSnapshot).count() == 0


def test_fixture_confirmation_persists_unresolved_parsed_players_and_requires_resolution(session, tmp_path, monkeypatch):
    fixture, home, away = fixture_context(session)
    parsed = parsed_sheet()
    parsed["home_team"]["players"] = [{"number": 7, "name": "Ana Gómez", "goals": 3, "yellow": 1, "two_min": 0, "red": 0, "blue": 0}]
    parsed["away_team"]["players"] = [{"number": 10, "name": "Bea Pérez", "goals": 1, "yellow": 0, "two_min": 1, "red": 0, "blue": 0}]
    monkeypatch.setattr(PDFService, "PDF_DIR", str(tmp_path))
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: parsed))

    result = PDFService.confirm_fixture(session, fixture.fixture_key, b"x", "sheet.pdf", "application/pdf", fixture_confirmation(home, away,
        home_players=[{"name": "Ana Gómez", "jersey_number": 7, "official_goals": 3, "official_yellow": 1, "official_2min": 0, "official_red": 0, "official_blue": 0}],
        away_players=[{"name": "Bea Pérez", "jersey_number": 10, "official_goals": 1, "official_yellow": 0, "official_2min": 1, "official_red": 0, "official_blue": 0}],
    ))

    snapshot_players = session.query(OfficialSnapshotPlayer).filter_by(snapshot_id=result["snapshot_id"]).order_by(OfficialSnapshotPlayer.side).all()
    assert [(player.side, player.name, player.player_id) for player in snapshot_players] == [("away", "Bea Pérez", None), ("home", "Ana Gómez", None)]
    assert session.get(Match, result["match_id"]).origin == "fixture"
    assert session.query(MatchSquad).filter_by(match_id=result["match_id"]).count() == 0
    assert PDFService.fixture_read(PDFService.preloaded_fixture(session, fixture.fixture_key))["roster_status"] == "needs_identity_resolution"


def test_fixture_confirmation_rejects_dropping_parsed_players(session, monkeypatch):
    fixture, home, away = fixture_context(session)
    parsed = parsed_sheet()
    parsed["home_team"]["players"] = [{"number": 7, "name": "Ana Gómez", "goals": 3, "yellow": 0, "two_min": 0, "red": 0, "blue": 0}]
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: parsed))

    with pytest.raises(ValueError, match="deben coincidir"):
        PDFService.confirm_fixture(session, fixture.fixture_key, b"x", "sheet.pdf", "application/pdf", fixture_confirmation(home, away))

    assert session.query(Match).count() == session.query(OfficialSnapshot).count() == 0


def test_fixture_confirmation_requires_acknowledgement_preserves_fixture_and_retries(session, tmp_path, monkeypatch):
    fixture, home, away = fixture_context(session, source_scores=(27, 23))
    monkeypatch.setattr(PDFService, "PDF_DIR", str(tmp_path))
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: parsed_sheet()))
    confirmation = fixture_confirmation(home, away)
    with pytest.raises(ValueError, match="discrepancia"):
        PDFService.confirm_fixture(session, fixture.fixture_key, b"x", "sheet.pdf", "application/pdf", confirmation)
    assert (fixture.source_home_score, fixture.source_away_score, fixture.result_status) == (27, 23, "reported")
    result = PDFService.confirm_fixture(session, fixture.fixture_key, b"x", "sheet.pdf", "application/pdf", fixture_confirmation(home, away, acknowledge_score_mismatch=True))
    retry = PDFService.confirm_fixture(session, fixture.fixture_key, b"x", "sheet.pdf", "application/pdf", fixture_confirmation(home, away, acknowledge_score_mismatch=True))
    assert retry == {**result, "reused": True}
    assert session.query(Match).count() == session.query(OfficialSnapshot).count() == 1
    assert (session.get(ScheduledMatch, fixture.id).source_home_score, session.get(ScheduledMatch, fixture.id).source_away_score) == (27, 23)


def test_fixture_confirmation_rejects_cross_team_identity_and_cleans_failed_upload(session, tmp_path, monkeypatch):
    fixture, home, away = fixture_context(session)
    wrong_player = Player(name="Wrong", team_id=away.id); session.add(wrong_player); session.commit()
    monkeypatch.setattr(PDFService, "PDF_DIR", str(tmp_path))
    parsed = parsed_sheet()
    parsed["home_team"]["players"] = [{"number": 1, "name": "Wrong", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0}]
    monkeypatch.setattr(PDFService, "preview_femebal_sheet", staticmethod(lambda *_: parsed))
    with pytest.raises(ValueError, match="no pertenece"):
        PDFService.confirm_fixture(session, fixture.fixture_key, b"x", "sheet.pdf", "application/pdf",
            fixture_confirmation(home, away, home_players=[{"name": "Wrong", "existing_player_id": wrong_player.id, "jersey_number": 1}]))
    monkeypatch.setattr(PDFService, "_fixture_snapshot_players", staticmethod(lambda *_: (_ for _ in ()).throw(RuntimeError("write failure"))))
    with pytest.raises(RuntimeError, match="write failure"):
        PDFService.confirm_fixture(session, fixture.fixture_key, b"x", "sheet.pdf", "application/pdf",
            fixture_confirmation(home, away, home_players=[{"name": "Wrong", "jersey_number": 1}]))
    assert not list(tmp_path.iterdir()) and session.query(Match).count() == 0


def test_confirmation_persists_manual_official_snapshot_without_parser_fallback(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    monkeypatch.setattr(PDFService, "PDF_DIR", str(tmp_path))
    confirmation = PDFImportConfirmation.model_validate({
        "date": date(2026, 8, 22),
        "home_team": {"name": "SAPA"},
        "away_team": {"name": "Banfield B"},
        "home_score": 28,
        "away_score": 24,
        "home_players": [{"name": "Ana Manual", "jersey_number": 7, "official_goals": 3}],
        "away_players": [],
    })

    snapshot = PDFService.confirm_import(
        session, SAMPLE_SHEET.read_bytes(), SAMPLE_SHEET.name, "application/pdf", confirmation
    )

    persisted = session.get(OfficialSnapshot, snapshot.id)
    player = session.query(OfficialSnapshotPlayer).filter_by(snapshot_id=snapshot.id).one()
    assert (persisted.home_team_name, persisted.away_team_name) == ("SAPA", "Banfield B")
    assert (persisted.home_score, persisted.away_score) == (28, 24)
    assert session.get(Match, persisted.match_id).origin == "fixture"
    assert player.name == "Ana Manual"
    assert Path(persisted.source_path).read_bytes() == SAMPLE_SHEET.read_bytes()
    session.get(Match, persisted.match_id).home_score = 99
    session.commit()
    assert session.get(OfficialSnapshot, snapshot.id).home_score == 28
    engine.dispose()


def test_context_supported_confirmation_reuses_identity_and_preserves_official_provenance(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    monkeypatch.setattr(PDFService, "PDF_DIR", str(tmp_path))
    home, away = Team(name="SAPA"), Team(name="Banfield B")
    session.add_all([home, away])
    session.flush()
    existing = Player(name="Ana Gomez", team_id=home.id, default_jersey_number=7)
    session.add(existing)
    session.commit()
    confirmation = PDFImportConfirmation.model_validate({
        "date": date(2026, 8, 22), "home_team": {"name": "SAPA", "existing_team_id": home.id},
        "away_team": {"name": "Banfield B", "existing_team_id": away.id}, "home_score": 28, "away_score": 24,
        "home_players": [{"name": "Ana Gomez", "existing_player_id": existing.id, "jersey_number": 7, "official_goals": 3}],
    })

    snapshot = PDFService.confirm_import(session, SAMPLE_SHEET.read_bytes(), SAMPLE_SHEET.name, "application/pdf", confirmation)
    persisted = session.get(OfficialSnapshot, snapshot.id)
    player = session.query(OfficialSnapshotPlayer).filter_by(snapshot_id=snapshot.id).one()

    assert (persisted.source_filename, persisted.source_content_type, persisted.source_size_bytes, persisted.source_page_count) == (SAMPLE_SHEET.name, "application/pdf", len(SAMPLE_SHEET.read_bytes()), 1)
    assert persisted.source_sha256 == PDFService.preview_femebal_sheet(SAMPLE_SHEET.read_bytes(), SAMPLE_SHEET.name, "application/pdf")["provenance"]["sha256"]
    assert (persisted.home_team_name, persisted.away_team_name, persisted.home_score, persisted.away_score) == ("SAPA", "Banfield B", 28, 24)
    assert player.player_id == existing.id
    assert (session.get(Player, existing.id).name, session.get(Player, existing.id).team_id) == ("Ana Gomez", home.id)
    engine.dispose()


def test_declined_ambiguous_identity_creates_selected_player_without_mutating_candidates(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    monkeypatch.setattr(PDFService, "PDF_DIR", str(tmp_path))
    home, away = Team(name="SAPA"), Team(name="Banfield B")
    session.add_all([home, away])
    session.flush()
    candidates = [Player(name="Ana Gomez", team_id=home.id, default_jersey_number=7), Player(name="Ana Gomez", team_id=home.id, default_jersey_number=7)]
    session.add_all(candidates)
    session.commit()
    confirmation = PDFImportConfirmation.model_validate({
        "date": date(2026, 8, 22), "home_team": {"name": "SAPA", "existing_team_id": home.id},
        "away_team": {"name": "Banfield B", "existing_team_id": away.id}, "home_score": 28, "away_score": 24,
        "home_players": [{"name": "Ana Gomez", "jersey_number": 7, "official_goals": 3}],
    })

    snapshot = PDFService.confirm_import(session, SAMPLE_SHEET.read_bytes(), SAMPLE_SHEET.name, "application/pdf", confirmation)
    snapshot_player = session.query(OfficialSnapshotPlayer).filter_by(snapshot_id=snapshot.id).one()
    created = session.get(Player, snapshot_player.player_id)

    assert snapshot_player.player_id not in {candidate.id for candidate in candidates}
    assert (created.name, created.team_id, created.default_jersey_number) == ("Ana Gomez", home.id, 7)
    assert [(candidate.name, candidate.team_id, candidate.default_jersey_number) for candidate in session.query(Player).filter(Player.id.in_([candidate.id for candidate in candidates])).all()] == [("Ana Gomez", home.id, 7), ("Ana Gomez", home.id, 7)]
    assert session.get(OfficialSnapshot, snapshot.id).home_score == 28
    engine.dispose()

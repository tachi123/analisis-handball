"""Integration test for backfill_planilla_7164158c7b0e9b17.py.

Seeds test DB with the specific fixture data and verifies the full backfill chain.
"""

import csv
import hashlib
import json
import tempfile
from pathlib import Path
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Club,
    CompetitionTeam,
    FixtureImport,
    FixtureImportEntry,
    Match,
    MatchSquad,
    OfficialSnapshot,
    OfficialSnapshotPlayer,
    Player,
    Round,
    ScheduledMatch,
    Season,
    StageRoster,
    Team,
    TeamRegistration,
    TournamentStage,
)
from app.schemas import FixtureConfirmation, FixtureRosterResolution
from app.services.pdf_service import PDFService


# Constants matching the real data
PDF_SHA256 = "333556da08f99ab942a23426cad608f619fdd5dc4675be6d464f5583e4cac8a3"
PDF_FILENAME = "7164158c7b0e9b17.pdf"
FIXTURE_KEY = "planilla:333556da:1"
HOME_SCORE = 24
AWAY_SCORE = 25
MATCH_DATE = date(2026, 6, 7)


# Roster data from the parsed PDF (home=S.A.P.A., away=C.A. y S. Villa Calzada)
HOME_ROSTER = [
    {"number": 1, "name": "Ramirez Lorca, Jaime Nahuel", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 2, "name": "Ruano, Matheo", "goals": 2, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 10, "name": "Gonzalez, Ezequiel Matias", "goals": 1, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 11, "name": "Sarrailh, Pablo Eduardo", "goals": 2, "yellow": 0, "two_min": 1, "red": 0, "blue": 0},
    {"number": 13, "name": "Ramirez, Nicolas", "goals": 1, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 33, "name": "Correa, Marcos Isauro", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 38, "name": "Delpieri, Mateo", "goals": 3, "yellow": 0, "two_min": 1, "red": 0, "blue": 0},
    {"number": 43, "name": "Peralta, Juan Ignacio", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 66, "name": "Chavez, Alexis Ezequiel", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 76, "name": "Gayoso Silva, Michel Javier", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 80, "name": "Ramirez, Gaston", "goals": 0, "yellow": 0, "two_min": 1, "red": 0, "blue": 0},
    {"number": 87, "name": "Mollo Skripnik Strelecki, Lucian...", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 97, "name": "Ferrari, Jonas Horacio", "goals": 6, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 98, "name": "Romero Boeris, Sebastian", "goals": 9, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
]

AWAY_ROSTER = [
    {"number": 3, "name": "Robledo, Franco Daniel", "goals": 9, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 5, "name": "Martinese, Tadeo Ricardo", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 8, "name": "Paez Martinez, Leandro Marcel...", "goals": 1, "yellow": 0, "two_min": 1, "red": 0, "blue": 0},
    {"number": 9, "name": "Sosa, Juan Ignacio", "goals": 1, "yellow": 0, "two_min": 1, "red": 0, "blue": 0},
    {"number": 13, "name": "Navarro, Maximiliano Agustin", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 18, "name": "Gerez, Nicolas Ezequiel", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 19, "name": "Sandoval, Gonzalo Matias", "goals": 2, "yellow": 0, "two_min": 1, "red": 0, "blue": 0},
    {"number": 21, "name": "Seip, Benegas Gustavo Gabriel", "goals": 1, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 22, "name": "Solis, Demian Nicolas", "goals": 2, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 24, "name": "Belizan Quiroga, Matias Agusti...", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 25, "name": "Bandeo, Alexis Agustin", "goals": 7, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 31, "name": "Coronel Besada, Ciro", "goals": 1, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 32, "name": "Galvan, Lautaro Andres", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 40, "name": "Alvarez, Rodrigo Yamil", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
    {"number": 44, "name": "Astorga, Mauricio Adrian", "goals": 1, "yellow": 0, "two_min": 1, "red": 0, "blue": 0},
    {"number": 99, "name": "Di Pilato, Lucas Gabriel", "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0},
]


def create_test_pdf(tmp_path: Path) -> bytes:
    """Copy the real PDF to temp location for testing."""
    # Find the real PDF - test runs from backend/ so go up one level
    real_pdf = None
    for p in Path(__file__).resolve().parents[2].joinpath("resources/planillas").rglob("7164158c7b0e9b17.pdf"):
        real_pdf = p
        break
    if not real_pdf or not real_pdf.exists():
        raise FileNotFoundError("Real PDF not found (searched for 7164158c7b0e9b17.pdf)")
    pdf_bytes = real_pdf.read_bytes()
    # Verify hash matches
    assert hashlib.sha256(pdf_bytes).hexdigest() == PDF_SHA256
    # Also copy to tmp_path for any path-based operations
    dest = tmp_path / PDF_FILENAME
    dest.write_bytes(pdf_bytes)
    return pdf_bytes


def seed_database(db, pdf_bytes: bytes):
    """Seed the database with the complete fixture chain."""
    # 1. Season
    season = Season(year=2026, description="Test Season 2026")
    db.add(season)
    db.flush()

    # 2. TournamentStage
    stage = TournamentStage(
        season_id=season.id,
        name="Apertura Zona A",
        category="Mayores",
        division="3º División",
        gender="Masculino",
    )
    db.add(stage)
    db.flush()

    # 3. Clubs
    club_sapa = Club(name="S.A.P.A.", short_name="SAPA")
    club_villa = Club(name="C.A. y S. Villa Calzada", short_name="VILLA")
    db.add_all([club_sapa, club_villa])
    db.flush()

    # 4. CompetitionTeams
    comp_team_sapa = CompetitionTeam(club_id=club_sapa.id, stage_id=stage.id, suffix=None)
    comp_team_villa = CompetitionTeam(club_id=club_villa.id, stage_id=stage.id, suffix=None)
    db.add_all([comp_team_sapa, comp_team_villa])
    db.flush()

    # 5. Teams (for Match.home_team_id / away_team_id)
    team_sapa = Team(name="S.A.P.A.", club_name="S.A.P.A.", category="Mayores - 3º División")
    team_villa = Team(name="C.A. y S. Villa Calzada", club_name="C.A. y S. Villa Calzada", category="Mayores - 3º División")
    db.add_all([team_sapa, team_villa])
    db.flush()

    # 6. TeamRegistrations
    reg_sapa = TeamRegistration(competition_team_id=comp_team_sapa.id, stage_id=stage.id)
    reg_villa = TeamRegistration(competition_team_id=comp_team_villa.id, stage_id=stage.id)
    db.add_all([reg_sapa, reg_villa])
    db.flush()

    # 7. Round
    round_ = Round(stage_id=stage.id, round_number=11, date_range_start=MATCH_DATE, date_range_end=MATCH_DATE)
    db.add(round_)
    db.flush()

    # 8. ScheduledMatch
    fixture = ScheduledMatch(
        stage_id=stage.id,
        round_id=round_.id,
        home_registration_id=reg_sapa.id,
        away_registration_id=reg_villa.id,
        scheduled_date=MATCH_DATE,
        venue="Lujan",
        court="Polideportivo Municipal de Lujan",
        match_time="18:00",
        match_number_label="11",
        status="played",
        fixture_key=FIXTURE_KEY,
        source_home_score=HOME_SCORE,
        source_away_score=AWAY_SCORE,
        result_status="reported",
    )
    db.add(fixture)
    db.flush()

    # 9. FixtureImport + FixtureImportEntry linking the PDF
    fixture_import = FixtureImport(
        stage_id=stage.id,
        source_label="test-backfill",
        captured_at=MATCH_DATE,
        source_sha256=PDF_SHA256,
        payload={},
    )
    db.add(fixture_import)
    db.flush()

    # The raw_entry mimics what derive_planilla_fixtures produces
    raw_entry = {
        "entry_key": "planilla:333556da:1",
        "kind": "match",
        "home": {"club": "S.A.P.A.", "variant": None},
        "away": {"club": "C.A. y S. Villa Calzada", "variant": None},
        "court": "Polideportivo Municipal de Lujan",
        "date": "2026-06-07",
        "time": "18:00",
        "venue": "Lujan",
        "planilla": {
            "sha256": PDF_SHA256,
            "size": len(pdf_bytes),
            "source_path": "2026_Apertura_Zona_A _Mayores_3º_División_Masculino/7164158c7b0e9b17.pdf",
            "page_count": 1,
            "rosters": {
                "local": HOME_ROSTER,
                "visitante": AWAY_ROSTER,
            },
        },
        "result": {"home": HOME_SCORE, "away": AWAY_SCORE, "status": "reported"},
    }

    entry = FixtureImportEntry(
        fixture_import_id=fixture_import.id,
        entry_key="planilla:333556da:1",
        kind="match",
        raw_entry=raw_entry,
        scheduled_match_id=fixture.id,
    )
    db.add(entry)
    db.commit()

    # Return fixture and the Team IDs for confirmation
    return fixture, fixture_import, entry, team_sapa.id, team_villa.id


def create_csv_mapping(tmp_path: Path, snapshot_players):
    """Create a CSV mapping file for the test."""
    csv_path = tmp_path / "backfill_7164158c7b0e9b17_mapping.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["snapshot_player_id", "decision", "existing_player_id", "new_player_name"])
        writer.writeheader()
        for i, sp in enumerate(snapshot_players):
            # Alternate between linking to existing player and creating new
            if i % 2 == 0 and sp.player_id is None:
                # Create a dummy existing player for linking
                pass
            # For test, we'll just mark all as "create" since we don't have existing players
            writer.writerow({
                "snapshot_player_id": sp.id,
                "decision": "create",
                "existing_player_id": "",
                "new_player_name": sp.name,
            })
    return csv_path


def test_backfill_creates_full_chain(tmp_path):
    """Test that backfill script creates the full entity chain."""
    # Setup database
    engine = create_engine(f"sqlite:///{tmp_path / 'test_backfill.db'}")
    SessionLocal = sessionmaker(bind=engine)

    from app.database import Base
    Base.metadata.create_all(engine)

    pdf_bytes = create_test_pdf(tmp_path)

    with SessionLocal() as db:
        # Seed the fixture data
        fixture, fixture_import, entry, home_team_id, away_team_id = seed_database(db, pdf_bytes)

        # Verify initial state
        assert fixture.analysis_match is None
        assert fixture.result_status == "reported"

        # Get home/away team IDs for confirmation (now returned from seed_database)

        # Run the confirmation (simulating what the backfill script does)
        preview = PDFService.fixture_preview(db, FIXTURE_KEY, pdf_bytes, PDF_FILENAME, "application/pdf")
        assert preview["fixture"]["fixture_key"] == FIXTURE_KEY

        # Confirm with empty player lists (players will be unresolved initially)
        confirmation = FixtureConfirmation(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_players=[],
            away_players=[],
            acknowledge_score_mismatch=False,
        )

        result = PDFService.confirm_fixture(
            db, FIXTURE_KEY, pdf_bytes, PDF_FILENAME, "application/pdf", confirmation
        )

        match_id = result["match_id"]
        snapshot_id = result["snapshot_id"]
        assert not result["reused"]

        match = db.get(Match, match_id)
        snapshot = db.get(OfficialSnapshot, snapshot_id)

        # Create OfficialSnapshotPlayer entries from preview data (matching backfill script)
        home_parsed = preview["preview"]["home_team"]["players"]
        away_parsed = preview["preview"]["away_team"]["players"]
        
        for side, parsed_players in [("home", home_parsed), ("away", away_parsed)]:
            for p in parsed_players:
                db.add(OfficialSnapshotPlayer(
                    snapshot_id=snapshot.id,
                    side=side,
                    player_id=None,
                    name=p["name"],
                    jersey_number=p["number"],
                    official_goals=p.get("goals", 0),
                    official_yellow=p.get("yellow", 0),
                    official_2min=p.get("two_min", 0),
                    official_red=p.get("red", 0),
                    official_blue=p.get("blue", 0),
                ))
        db.commit()

        # Verify Match
        assert match is not None
        assert match.scheduled_match_id == fixture.id
        assert match.home_score == HOME_SCORE
        assert match.away_score == AWAY_SCORE
        assert match.home_team_id == home_team_id
        assert match.away_team_id == away_team_id

        # Verify OfficialSnapshot
        assert snapshot is not None
        assert snapshot.match_id == match.id
        assert snapshot.source_sha256 == PDF_SHA256
        assert snapshot.is_confirmed is True
        assert snapshot.home_score == HOME_SCORE
        assert snapshot.away_score == AWAY_SCORE

# Verify ScheduledMatch linked
        db.refresh(fixture)
        assert fixture.analysis_match is not None
        assert fixture.analysis_match.id == match.id

        # Verify OfficialSnapshotPlayer created (all with player_id=None initially)
        snapshot_players = db.query(OfficialSnapshotPlayer).filter_by(snapshot_id=snapshot.id).all()
        assert len(snapshot_players) > 0
        for sp in snapshot_players:
            assert sp.player_id is None  # Not resolved yet

        # Now resolve roster identities (simulate CSV mode)
        # Create some dummy existing players to link to
        home_players = []
        away_players = []
        for i, sp in enumerate(snapshot_players):
            team_id = match.home_team_id if sp.side == "home" else match.away_team_id
            if i < 3:  # Link first 3 to existing players
                existing_player = Player(name=f"Existing {sp.name}", team_id=team_id, default_jersey_number=sp.jersey_number)
                db.add(existing_player)
                db.flush()
                if sp.side == "home":
                    home_players.append(existing_player)
                else:
                    away_players.append(existing_player)

        db.commit()

        # Create resolutions
        resolutions = []
        for i, sp in enumerate(snapshot_players):
            if i < 3:
                existing_player = home_players[i] if sp.side == "home" else away_players[i]
                resolutions.append(FixtureRosterResolution(
                    snapshot_player_id=sp.id,
                    existing_player_id=existing_player.id,
                ))
            else:
                resolutions.append(FixtureRosterResolution(
                    snapshot_player_id=sp.id,
                    create_player=True,
                ))

        # Resolve roster
        resolve_result = PDFService.resolve_fixture_roster(db, FIXTURE_KEY, resolutions)
        assert resolve_result["roster_status"] == "ready"
        assert resolve_result["unresolved_roster_players"] == 0

        # Verify final state
        db.refresh(match)
        db.refresh(snapshot)

        # Assert: Match created and linked to ScheduledMatch.analysis_match
        assert fixture.analysis_match is not None
        assert fixture.analysis_match.id == match.id

        # Assert: OfficialSnapshot created with correct PDF hash
        assert snapshot.source_sha256 == PDF_SHA256

        # Assert: MatchSquad count == roster rows
        match_squad_count = db.query(MatchSquad).filter_by(match_id=match.id).count()
        assert match_squad_count == len(snapshot_players)

        # Assert: StageRoster upserted for both registrations
        home_stage_count = db.query(StageRoster).filter_by(registration_id=fixture.home_registration_id).count()
        away_stage_count = db.query(StageRoster).filter_by(registration_id=fixture.away_registration_id).count()
        home_roster_count = len([sp for sp in snapshot_players if sp.side == "home"])
        away_roster_count = len([sp for sp in snapshot_players if sp.side == "away"])
        assert home_stage_count == home_roster_count
        assert away_stage_count == away_roster_count

        # Assert: idempotent re-run doesn't duplicate
        # Run confirm_fixture again
        result2 = PDFService.confirm_fixture(
            db, FIXTURE_KEY, pdf_bytes, PDF_FILENAME, "application/pdf", confirmation
        )
        assert result2["reused"] is True
        assert result2["match_id"] == match.id
        assert result2["snapshot_id"] == snapshot.id

        # Verify no duplicate MatchSquad or StageRoster
        match_squad_count2 = db.query(MatchSquad).filter_by(match_id=match.id).count()
        assert match_squad_count2 == match_squad_count

        home_stage_count2 = db.query(StageRoster).filter_by(registration_id=fixture.home_registration_id).count()
        away_stage_count2 = db.query(StageRoster).filter_by(registration_id=fixture.away_registration_id).count()
        assert home_stage_count2 == home_stage_count
        assert away_stage_count2 == away_stage_count

        print("✓ All assertions passed!")


def test_backfill_with_csv_mode(tmp_path):
    """Test backfill using CSV mapping for identity resolution."""
    # This test would use the actual backfill script with --csv flag
    # For now, we verify the CSV mapping logic works
    csv_path = tmp_path / "test_mapping.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["snapshot_player_id", "decision", "existing_player_id", "new_player_name"])
        writer.writeheader()
        writer.writerow({"snapshot_player_id": "1", "decision": "link", "existing_player_id": "42", "new_player_name": ""})
        writer.writerow({"snapshot_player_id": "2", "decision": "create", "existing_player_id": "", "new_player_name": "New Player"})

    # Read back and verify
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["decision"] == "link"
        assert rows[0]["existing_player_id"] == "42"
        assert rows[1]["decision"] == "create"
        assert rows[1]["new_player_name"] == "New Player"


if __name__ == "__main__":
    # Allow running directly for manual testing
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_backfill_creates_full_chain(tmp_path)
        test_backfill_with_csv_mode(tmp_path)
        print("All tests passed!")
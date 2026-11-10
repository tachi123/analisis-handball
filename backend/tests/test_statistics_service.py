"""Focused tests for the FEMEBAL Permanencia 2026 statistics service."""
import pytest

from app.models import (
    Club,
    CompetitionTeam,
    Match,
    OfficialSnapshot,
    OfficialSnapshotPlayer,
    Player,
    Round,
    ScheduledMatch,
    Season,
    StageRoster,
    TeamRegistration,
    TournamentStage,
)
from app.services.statistics_service import club_statistics, player_statistics
from sqlalchemy.orm import Session


def test_player_statistics_schema(session: Session):
    """player_statistics returns the expected JSON shape."""
    from datetime import date

    season = Season(year=2026, description="Test Permanencia")
    session.add(season)
    session.flush()

    stage = TournamentStage(
        season_id=season.id,
        name="Torneo Permanencia 2026 3ªM",
        category="Mayores",
        division="3ª División",
        gender="Masculino",
    )
    session.add(stage)
    session.flush()

    # Create two clubs/competition_teams/registrations
    clubs = []
    for name, suffix in [("Club A", ""), ("Club", "B")]:
        club = Club(name=name)
        session.add(club)
        session.flush()
        clubs.append(club)

    competition_teams = []
    registrations = []
    for i, (club, suffix) in enumerate(zip(clubs, ["", "B"])):
        ct = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix=suffix, variant_key=suffix)
        session.add(ct)
        session.flush()
        competition_teams.append(ct)

        reg = TeamRegistration(competition_team_id=ct.id, stage_id=stage.id)
        session.add(reg)
        session.flush()
        registrations.append(reg)

    reg_a = registrations[0]
    reg_b = registrations[1]

    # Add a round and scheduled matches
    round1 = Round(stage_id=stage.id, round_number=1)
    session.add(round1)
    session.flush()

    scheduled1 = ScheduledMatch(
        stage_id=stage.id,
        round_id=round1.id,
        home_registration_id=reg_a.id,
        away_registration_id=reg_b.id,
        fixture_key="fm-001",
        match_number_label="1",
        scheduled_date=date(2026, 1, 1),
        status="played",
    )
    session.add(scheduled1)
    session.flush()

    # Create the match with an official snapshot (confirmed)
    from app.database import Base as _Base
    # Create the match with an official snapshot (confirmed)
    match1 = Match(
        date=scheduled1.scheduled_date,
        scheduled_match_id=scheduled1.id,
        home_team_id=clubs[0].id,
        away_team_id=clubs[1].id,
        home_score=2,
        away_score=1,
    )
    session.add(match1)
    session.flush()

    snapshot1 = OfficialSnapshot(
        id="snap-1",
        match_id=match1.id,
        source_filename="sheet.pdf",
        source_content_type="application/pdf",
        source_size_bytes=1,
        source_sha256="a",
        source_page_count=1,
        source_path="sheet.pdf",
        confirmed_date=date(2026, 1, 1),
        home_team_name="Club A",
        away_team_name="Club B",
        home_score=2,
        away_score=1,
        is_confirmed=True,
    )
    session.add(snapshot1)
    session.flush()

    # Official snapshot players (home team)
    # Player 1: Juan Perez, goals=1, yellow=0, 2min=0, red=0, blue=0
    # Player 2: None player_id, fall back to name
    sp1 = OfficialSnapshotPlayer(
        snapshot_id=snapshot1.id,
        side="home",
        player_id=1,
        name="Juan Perez",
        jersey_number=10,
        official_goals=1,
        official_yellow=0,
        official_2min=0,
        official_red=0,
        official_blue=0,
    )
    session.add(sp1)

    # Away player with no player_id (fallback to name)
    sp2 = OfficialSnapshotPlayer(
        snapshot_id=snapshot1.id,
        side="away",
        player_id=None,
        name="Carlos Ruiz",
        jersey_number=7,
        official_goals=0,
        official_yellow=1,
        official_2min=0,
        official_red=0,
        official_blue=0,
    )
    session.add(sp2)
    session.flush()

    # Create a second match/snapshot for the same stage
    scheduled2 = ScheduledMatch(
        stage_id=stage.id,
        round_id=round1.id,
        home_registration_id=reg_b.id,
        away_registration_id=reg_a.id,
        fixture_key="fm-002",
        match_number_label="2",
        scheduled_date=date(2026, 1, 2),
        status="played",
    )
    session.add(scheduled2)
    session.flush()

    match2 = Match(
        date=scheduled2.scheduled_date,
        scheduled_match_id=scheduled2.id,
        home_team_id=clubs[1].id,
        away_team_id=clubs[0].id,
        home_score=1,
        away_score=1,
    )
    session.add(match2)
    session.flush()

    snapshot2 = OfficialSnapshot(
        id="snap-2",
        match_id=match2.id,
        source_filename="sheet.pdf",
        source_content_type="application/pdf",
        source_size_bytes=1,
        source_sha256="b",
        source_page_count=1,
        source_path="sheet.pdf",
        confirmed_date=date(2026, 1, 2),
        home_team_name="Club B",
        away_team_name="Club A",
        home_score=1,
        away_score=1,
        is_confirmed=True,
    )
    session.add(snapshot2)
    session.flush()

    # Second snapshot players
    sp3 = OfficialSnapshotPlayer(
        snapshot_id=snapshot2.id,
        side="home",
        player_id=1,
        name="Juan Perez",
        jersey_number=10,
        official_goals=2,
        official_yellow=1,
        official_2min=1,
        official_red=0,
        official_blue=0,
    )
    session.add(sp3)

    sp4 = OfficialSnapshotPlayer(
        snapshot_id=snapshot2.id,
        side="away",
        player_id=None,
        name="Carlos Ruiz",
        jersey_number=7,
        official_goals=1,
        official_yellow=0,
        official_2min=0,
        official_red=0,
        official_blue=0,
    )
    session.add(sp4)
    session.flush()

    # Now call the service
    result = player_statistics(session, stage.id)

    # Validate shape
    assert "schema_version" in result
    assert "stage_id" in result
    assert "stage_name" in result
    assert "rows" in result
    assert "note" in result
    assert result["stage_id"] == stage.id  # use the actual stage id from test setup

    # We have 2 players: Juan Perez (appearances=2, goals=3) and Carlos Ruiz (appearances=2, goals=1)
    rows = result["rows"]
    assert len(rows) == 2

    # Juan Perez should be first (more goals)
    assert rows[0]["name"] == "Juan Perez"
    assert rows[0]["goals"] == 3
    assert rows[0]["appearances"] == 2
    assert rows[0]["goals_per_game"] == 1.5  # round(3/2, 2)
    assert rows[0]["club"] == "Club A"  # home registration for side "home"

    # Carlos Ruiz should be second (fallback to name since player_id=None)
    assert rows[1]["name"] == "Carlos Ruiz"
    assert rows[1]["goals"] == 1
    assert rows[1]["appearances"] == 2
    # goals_per_game = round(1/2, 2) = 0.5
    assert rows[1]["goals_per_game"] == 0.5
    # Club derivation: away side for first match, away side for second match
    # Both times Carlos was away, so club should be "Club B"
    assert rows[1]["club"] == "Club B"

    # Note about confirmed planillas
    assert "Only confirmed planillas are counted." in result["note"]


def test_club_statistics_schema(session: Session):
    """club_statistics returns the expected JSON shape."""
    from datetime import date

    season = Season(year=2026, description="Test Permanencia")
    session.add(season)
    session.flush()

    stage = TournamentStage(
        season_id=season.id,
        name="Torneo Permanencia 2026 3ªM",
        category="Mayores",
        division="3ª División",
        gender="Masculino",
    )
    session.add(stage)
    session.flush()

    # Create one club
    club = Club(name="Club A")
    session.add(club)
    session.flush()

    competition_team = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="", variant_key="")
    session.add(competition_team)
    session.flush()

    registration = TeamRegistration(competition_team_id=competition_team.id, stage_id=stage.id)
    session.add(registration)
    session.flush()

    # Add a round and scheduled matches
    round1 = Round(stage_id=stage.id, round_number=1)
    session.add(round1)
    session.flush()

    scheduled1 = ScheduledMatch(
        stage_id=stage.id,
        round_id=round1.id,
        home_registration_id=registration.id,
        away_registration_id=registration.id,
        fixture_key="fm-001",
        match_number_label="1",
        scheduled_date=date(2026, 1, 1),
        status="played",
    )
    session.add(scheduled1)
    session.flush()

    # Create the match with an official snapshot (confirmed)
    match1 = Match(
        date=scheduled1.scheduled_date,
        scheduled_match_id=scheduled1.id,
        home_team_id=club.id,
        away_team_id=club.id,
        home_score=2,
        away_score=1,
    )
    session.add(match1)
    session.flush()

    snapshot1 = OfficialSnapshot(
        id="snap-1",
        match_id=match1.id,
        source_filename="sheet.pdf",
        source_content_type="application/pdf",
        source_size_bytes=1,
        source_sha256="a",
        source_page_count=1,
        source_path="sheet.pdf",
        confirmed_date=date(2026, 1, 1),
        home_team_name="Club A",
        away_team_name="Club A",
        home_score=2,
        away_score=1,
        is_confirmed=True,
    )
    session.add(snapshot1)
    session.flush()

    # Snapshot players: 3 home players, 2 away players
    sp1 = OfficialSnapshotPlayer(
        snapshot_id=snapshot1.id,
        side="home",
        player_id=1,
        name="Juan Perez",
        jersey_number=10,
        official_goals=1,
        official_yellow=0,
        official_2min=0,
        official_red=0,
        official_blue=0,
    )
    session.add(sp1)

    sp2 = OfficialSnapshotPlayer(
        snapshot_id=snapshot1.id,
        side="home",
        player_id=2,
        name="Mario Gonzalez",
        jersey_number=9,
        official_goals=0,
        official_yellow=1,
        official_2min=0,
        official_red=0,
        official_blue=0,
    )
    session.add(sp2)

    sp3 = OfficialSnapshotPlayer(
        snapshot_id=snapshot1.id,
        side="home",
        player_id=None,
        name="Unknown Player",
        jersey_number=14,
        official_goals=2,
        official_yellow=0,
        official_2min=1,
        official_red=0,
        official_blue=0,
    )
    session.add(sp3)

    sp4 = OfficialSnapshotPlayer(
        snapshot_id=snapshot1.id,
        side="away",
        player_id=3,
        name="Luis Fernandez",
        jersey_number=5,
        official_goals=1,
        official_yellow=0,
        official_2min=0,
        official_red=0,
        official_blue=0,
    )
    session.add(sp4)

    sp5 = OfficialSnapshotPlayer(
        snapshot_id=snapshot1.id,
        side="away",
        player_id=None,
        name="Unknown Player 2",
        jersey_number=6,
        official_goals=0,
        official_yellow=1,
        official_2min=0,
        official_red=0,
        official_blue=0,
    )
    session.add(sp5)
    session.flush()

    # Call the service
    result = club_statistics(session, stage.id)

    # Validate shape
    assert "schema_version" in result
    assert "stage_id" in result
    assert "stage_name" in result
    assert "rows" in result
    assert "note" in result

    rows = result["rows"]
    assert len(rows) == 1
    assert rows[0]["club"] == "Club A"
    assert rows[0]["appearances"] == 5  # 3 home + 2 away
    assert rows[0]["goals"] == 4  # 1+0+2+1+0
    assert rows[0]["yellow"] == 2  # 0+1+0+0+1
    assert rows[0]["two_min"] == 1
    assert rows[0]["red"] == 0
    assert rows[0]["blue"] == 0
    assert rows[0]["distinct_players"] == 3  # Juan, Mario, Unknown, Luis = 4 but Unknown Player appears twice with different jersey numbers
    # Actually: player_ids = {1, 2, None, 3, None} -> non-None = {1, 2, 3} = 3 distinct

    # Note about confirmed planillas
    assert "Only confirmed planillas are counted." in result["note"]


def test_player_statistics_confirmed_only_filter(session: Session):
    """player_statistics should exclude snapshots with is_confirmed=False."""
    from datetime import date

    season = Season(year=2026, description="Test Permanencia")
    session.add(season)
    session.flush()

    stage = TournamentStage(
        season_id=season.id,
        name="Torneo Permanencia 2026 3ªM",
        category="Mayores",
        division="3ª División",
        gender="Masculino",
    )
    session.add(stage)
    session.flush()

    club = Club(name="Club A")
    session.add(club)
    session.flush()

    competition_team = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="", variant_key="")
    session.add(competition_team)
    session.flush()

    registration = TeamRegistration(competition_team_id=competition_team.id, stage_id=stage.id)
    session.add(registration)
    session.flush()

    round1 = Round(stage_id=stage.id, round_number=1)
    session.add(round1)
    session.flush()

    scheduled1 = ScheduledMatch(
        stage_id=stage.id,
        round_id=round1.id,
        home_registration_id=registration.id,
        away_registration_id=registration.id,
        fixture_key="fm-001",
        match_number_label="1",
        scheduled_date=date(2026, 1, 1),
        status="played",
    )
    session.add(scheduled1)
    session.flush()

    # Match with TWO snapshots: one confirmed, one not
    match1 = Match(
        date=scheduled1.scheduled_date,
        scheduled_match_id=scheduled1.id,
        home_team_id=club.id,
        away_team_id=club.id,
        home_score=2,
        away_score=1,
    )
    session.add(match1)
    session.flush()

    # Confirmed snapshot
    snap_confirmed = OfficialSnapshot(
        id="snap-conf",
        match_id=match1.id,
        source_filename="sheet-conf.pdf",
        source_content_type="application/pdf",
        source_size_bytes=1,
        source_sha256="c",
        source_page_count=1,
        source_path="sheet-conf.pdf",
        confirmed_date=date(2026, 1, 1),
        home_team_name="Club A",
        away_team_name="Club A",
        home_score=2,
        away_score=1,
        is_confirmed=True,
    )
    session.add(snap_confirmed)
    session.flush()

    # Unconfirmed snapshot
    snap_unconfirmed = OfficialSnapshot(
        id="snap-unconf",
        match_id=match1.id,
        source_filename="sheet-unconf.pdf",
        source_content_type="application/pdf",
        source_size_bytes=1,
        source_sha256="d",
        source_page_count=1,
        source_path="sheet-unconf.pdf",
        confirmed_date=date(2026, 1, 1),
        home_team_name="Club A",
        away_team_name="Club A",
        home_score=3,
        away_score=0,
        is_confirmed=False,
    )
    session.add(snap_unconfirmed)
    session.flush()

    # Players in confirmed snapshot
    sp1 = OfficialSnapshotPlayer(
        snapshot_id=snap_confirmed.id,
        side="home",
        player_id=1,
        name="Juan Perez",
        jersey_number=10,
        official_goals=1,
        official_yellow=0,
        official_2min=0,
        official_red=0,
        official_blue=0,
    )
    session.add(sp1)

    # Players in unconfirmed snapshot should NOT be counted
    sp2 = OfficialSnapshotPlayer(
        snapshot_id=snap_unconfirmed.id,
        side="home",
        player_id=2,
        name="Pedro Sanchez",
        jersey_number=8,
        official_goals=2,
        official_yellow=0,
        official_2min=0,
        official_red=0,
        official_blue=0,
    )
    session.add(sp2)
    session.flush()

    result = player_statistics(session, stage.id)

    # Only Juan Perez should appear (from confirmed snapshot)
    rows = result["rows"]
    assert len(rows) == 1
    assert rows[0]["name"] == "Juan Perez"
    assert rows[0]["goals"] == 1

    # Note should mention confirmed planillas
    assert "Only confirmed planillas are counted." in result["note"]
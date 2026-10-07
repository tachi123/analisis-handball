from datetime import date, datetime, timezone

import pytest

from app.models import (
    Club, CompetitionTeam, FixtureImport, FixtureImportEntry, Match, OfficialSnapshot, OfficialSnapshotPlayer,
    Round, ScheduledMatch, Season, TeamRegistration, TournamentStage,
)
from app.services.stage_performance_service import (
    NoConfirmedOfficialDataError, StandingsRules, player_averages, standings,
    top_scorers,
)


def _stage(session):
    season = Season(year=2026)
    stage = TournamentStage(season=season, name="Stage", category="Senior", division="A", gender="M")
    session.add_all([season, stage]); session.flush()
    registrations = []
    for name in ("Alpha", "Beta", "Gamma"):
        club = Club(name=name)
        team = CompetitionTeam(club=club, stage=stage, variant_key="")
        registrations.append(TeamRegistration(competition_team=team, stage=stage))
    session.add_all(registrations); session.flush()
    return stage, registrations


def _snapshot(session, stage, home, away, number, score, *, confirmed=True, players=(), fixture_kind="match"):
    round_ = Round(stage=stage, round_number=number)
    fixture = ScheduledMatch(stage=stage, round=round_, home_registration=home, away_registration=away,
                             fixture_key=f"fixture-{number}", match_number_label=str(number), scheduled_date=date(2026, 1, number))
    match = Match(date=fixture.scheduled_date, scheduled_match=fixture)
    snapshot = OfficialSnapshot(id=f"snapshot-{number}", match=match, is_confirmed=confirmed,
        source_filename="sheet.pdf", source_content_type="application/pdf", source_size_bytes=1,
        source_sha256=str(number), source_page_count=1, source_path="sheet.pdf", confirmed_date=date(2026, 1, number),
        home_team_name=home.competition_team.display_name, away_team_name=away.competition_team.display_name,
        home_score=score[0], away_score=score[1])
    audit = FixtureImport(
        stage=stage,
        source_label="test",
        captured_at=datetime.now(timezone.utc),
        source_sha256=f"fixture-import-{number}",
        payload={},
    )
    session.add_all([
        snapshot,
        FixtureImportEntry(
            fixture_import=audit,
            entry_key=f"fixture-{number}",
            kind=fixture_kind,
            raw_entry={},
            scheduled_match=fixture,
        ),
    ])
    session.flush()
    for side, name, goals, yellow, two_min, red, blue in players:
        session.add(OfficialSnapshotPlayer(snapshot=snapshot, side=side, name=name, jersey_number=7,
            official_goals=goals, official_yellow=yellow, official_2min=two_min, official_red=red, official_blue=blue))
    session.flush()
    return snapshot


def test_confirmed_snapshots_produce_configurable_standings_and_player_aggregates(session):
    stage, (alpha, beta, gamma) = _stage(session)
    _snapshot(session, stage, alpha, beta, 1, (20, 18), players=[
        ("home", "Alex", 4, 1, 0, 0, 0), ("away", "Bea", 3, 0, 1, 0, 0),
    ])
    _snapshot(session, stage, gamma, alpha, 2, (15, 15), players=[
        ("away", "Alex", 2, 0, 1, 0, 0), ("home", "Gus", 5, 0, 0, 0, 0),
    ])
    _snapshot(session, stage, beta, gamma, 3, (22, 20), confirmed=False, players=[("home", "Bea", 9, 0, 0, 0, 0)])

    table = standings(session, stage.id, StandingsRules(win_points=3, draw_points=1, loss_points=0))
    assert [(row["team_name"], row["points"], row["rank"]) for row in table] == [("Alpha", 4, 1), ("Gamma", 1, 2), ("Beta", 0, 3)]
    assert top_scorers(session, stage.id)[0] == {"name": "Alex", "registration_id": alpha.id, "team_name": "Alpha", "goals": 6, "yellow": 1, "two_min": 1, "red": 0, "blue": 0, "appearances": 2}
    alex = next(row for row in player_averages(session, stage.id) if row["name"] == "Alex")
    assert (alex["goals"], alex["appearances"], alex["goals_per_match"], alex["yellow"], alex["two_min"]) == (6, 2, 3, 1, 1)


def test_unlinked_or_unconfirmed_evidence_is_not_stage_data(session):
    stage, (alpha, beta, _) = _stage(session)
    _snapshot(session, stage, alpha, beta, 1, (20, 18), confirmed=False)
    session.add(OfficialSnapshot(id="unlinked", match=Match(date=date.today()), is_confirmed=True,
        source_filename="sheet.pdf", source_content_type="application/pdf", source_size_bytes=1,
        source_sha256="unlinked", source_page_count=1, source_path="sheet.pdf", confirmed_date=date.today(),
        home_team_name="Alpha", away_team_name="Beta", home_score=99, away_score=0))
    session.commit()

    with pytest.raises(NoConfirmedOfficialDataError, match="no_confirmed_official_data"):
        standings(session, stage.id)
    with pytest.raises(NoConfirmedOfficialDataError):
        player_averages(session, stage.id)


def test_confirmed_snapshot_linked_to_bye_is_excluded_from_all_aggregates(session):
    stage, (alpha, beta, _) = _stage(session)
    _snapshot(session, stage, alpha, beta, 1, (20, 18), players=[
        ("home", "Alex", 4, 1, 0, 0, 0), ("away", "Bea", 3, 0, 1, 0, 0),
    ])
    _snapshot(session, stage, alpha, beta, 2, (99, 0), fixture_kind="bye", players=[
        ("home", "Alex", 99, 9, 9, 9, 9), ("away", "Bye Player", 88, 8, 8, 8, 8),
    ])

    assert [(row["team_name"], row["played"], row["points"]) for row in standings(session, stage.id)] == [
        ("Alpha", 1, 2), ("Beta", 1, 0),
    ]
    assert top_scorers(session, stage.id) == [
        {"name": "Alex", "registration_id": alpha.id, "team_name": "Alpha", "goals": 4, "yellow": 1, "two_min": 0, "red": 0, "blue": 0, "appearances": 1},
        {"name": "Bea", "registration_id": beta.id, "team_name": "Beta", "goals": 3, "yellow": 0, "two_min": 1, "red": 0, "blue": 0, "appearances": 1},
    ]
    assert player_averages(session, stage.id) == [
        {"name": "Alex", "registration_id": alpha.id, "team_name": "Alpha", "goals": 4, "yellow": 1, "two_min": 0, "red": 0, "blue": 0, "appearances": 1, "goals_per_match": 4, "yellow_per_match": 1, "two_min_per_match": 0, "red_per_match": 0, "blue_per_match": 0},
        {"name": "Bea", "registration_id": beta.id, "team_name": "Beta", "goals": 3, "yellow": 0, "two_min": 1, "red": 0, "blue": 0, "appearances": 1, "goals_per_match": 3, "yellow_per_match": 0, "two_min_per_match": 1, "red_per_match": 0, "blue_per_match": 0},
    ]

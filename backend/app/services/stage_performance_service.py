"""Read-only stage performance aggregates backed by confirmed official evidence."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session, joinedload

from ..models import (
    CompetitionTeam,
    FixtureImportEntry,
    Match,
    OfficialSnapshot,
    OfficialSnapshotPlayer,
    ScheduledMatch,
    TeamRegistration,
)


class NoConfirmedOfficialDataError(ValueError):
    """Raised when a stage has no confirmed fixture-linked official evidence."""


@dataclass(frozen=True)
class StandingsRules:
    win_points: int = 2
    draw_points: int = 1
    loss_points: int = 0
    tiebreak_order: tuple[str, ...] = ("points", "goal_difference", "goals_for", "team_name")

    def __post_init__(self) -> None:
        valid = {"points", "goal_difference", "goals_for", "goals_against", "team_name"}
        if not self.tiebreak_order or any(value not in valid for value in self.tiebreak_order):
            raise ValueError("tiebreak_order contains an unsupported criterion")


def standings(db: Session, stage_id: int, rules: StandingsRules | None = None) -> list[dict]:
    rules = rules or StandingsRules()
    rows = _confirmed_rows(db, stage_id)
    table: dict[int, dict] = {}
    for snapshot, fixture in rows:
        home = _team_row(table, fixture.home_registration)
        away = _team_row(table, fixture.away_registration)
        _apply_result(home, away, snapshot.home_score, snapshot.away_score, rules)
    return _rank(table.values(), rules)


def top_scorers(db: Session, stage_id: int) -> list[dict]:
    players = _player_totals(db, stage_id)
    return sorted(players.values(), key=lambda item: (-item["goals"], item["name"], item["team_name"]))


def player_averages(db: Session, stage_id: int) -> list[dict]:
    players = _player_totals(db, stage_id)
    for item in players.values():
        appearances = item["appearances"]
        item["goals_per_match"] = item["goals"] / appearances
        item["yellow_per_match"] = item["yellow"] / appearances
        item["two_min_per_match"] = item["two_min"] / appearances
        item["red_per_match"] = item["red"] / appearances
        item["blue_per_match"] = item["blue"] / appearances
    return sorted(players.values(), key=lambda item: (item["name"], item["team_name"]))


def _confirmed_rows(db: Session, stage_id: int) -> list[tuple[OfficialSnapshot, ScheduledMatch]]:
    rows = db.query(OfficialSnapshot, ScheduledMatch).join(
        Match, OfficialSnapshot.match_id == Match.id
    ).join(
        ScheduledMatch, Match.scheduled_match_id == ScheduledMatch.id
    ).join(
        FixtureImportEntry, FixtureImportEntry.scheduled_match_id == ScheduledMatch.id
    ).filter(
        ScheduledMatch.stage_id == stage_id,
        FixtureImportEntry.kind == "match",
        OfficialSnapshot.is_confirmed.is_(True),
    ).options(
        joinedload(ScheduledMatch.home_registration).joinedload(TeamRegistration.competition_team).joinedload(CompetitionTeam.club),
        joinedload(ScheduledMatch.away_registration).joinedload(TeamRegistration.competition_team).joinedload(CompetitionTeam.club),
    ).all()
    if not rows:
        raise NoConfirmedOfficialDataError("no_confirmed_official_data")
    return rows


def _team_name(registration: TeamRegistration) -> str:
    return registration.competition_team.display_name


def _team_row(table: dict[int, dict], registration: TeamRegistration) -> dict:
    return table.setdefault(registration.id, {
        "registration_id": registration.id, "team_name": _team_name(registration),
        "played": 0, "won": 0, "drawn": 0, "lost": 0, "goals_for": 0,
        "goals_against": 0, "goal_difference": 0, "points": 0,
    })


def _apply_result(home: dict, away: dict, home_score: int, away_score: int, rules: StandingsRules) -> None:
    for team, scored, conceded in ((home, home_score, away_score), (away, away_score, home_score)):
        team["played"] += 1
        team["goals_for"] += scored
        team["goals_against"] += conceded
        team["goal_difference"] = team["goals_for"] - team["goals_against"]
    if home_score > away_score:
        home["won"] += 1; away["lost"] += 1
        home["points"] += rules.win_points; away["points"] += rules.loss_points
    elif away_score > home_score:
        away["won"] += 1; home["lost"] += 1
        away["points"] += rules.win_points; home["points"] += rules.loss_points
    else:
        home["drawn"] += 1; away["drawn"] += 1
        home["points"] += rules.draw_points; away["points"] += rules.draw_points


def _rank(rows: Iterable[dict], rules: StandingsRules) -> list[dict]:
    def sort_key(row: dict) -> tuple:
        values = []
        for criterion in rules.tiebreak_order:
            value = row[criterion]
            values.append(value if criterion == "team_name" else -value)
        return tuple(values)

    return [dict(row, rank=index) for index, row in enumerate(sorted(rows, key=sort_key), start=1)]


def _player_totals(db: Session, stage_id: int) -> dict[tuple[str, int], dict]:
    rows = _confirmed_rows(db, stage_id)
    snapshot_ids = [snapshot.id for snapshot, _ in rows]
    fixtures = {snapshot.id: fixture for snapshot, fixture in rows}
    players = db.query(OfficialSnapshotPlayer).filter(OfficialSnapshotPlayer.snapshot_id.in_(snapshot_ids)).all()
    totals: dict[tuple[str, int], dict] = {}
    appearances: dict[tuple[str, int], set[str]] = {}
    for player in players:
        registration = fixtures[player.snapshot_id].home_registration if player.side == "home" else fixtures[player.snapshot_id].away_registration
        key = (player.name, registration.id)
        item = totals.setdefault(key, {
            "name": player.name, "registration_id": registration.id, "team_name": _team_name(registration),
            "goals": 0, "yellow": 0, "two_min": 0, "red": 0, "blue": 0,
        })
        item["goals"] += player.official_goals
        item["yellow"] += player.official_yellow
        item["two_min"] += player.official_2min
        item["red"] += player.official_red
        item["blue"] += player.official_blue
        appearances.setdefault(key, set()).add(player.snapshot_id)
    for key, item in totals.items():
        item["appearances"] = len(appearances[key])
    return totals

"""Shared competition ranking rules for standings, forecasts, and insights.

Handball ranks clubs by the **Olympic tiebreak**: when two or more clubs are
level on points, the matches played between them decide first. Points, goal
difference, and goals scored in that mini-table are applied in order. If the
mini-table separates only some clubs, the same procedure is repeated among the
clubs that remain level; only when it cannot separate them are overall goal
difference and overall goals scored used. A residual exact tie is returned as a
group so callers can decide whether to display it as a tie or split a simulated
position.

Keeping this rule in one pure module is deliberate: the standings table, the
Monte Carlo forecast, and the public insights must never drift into a parallel
rule (for example, ranking by overall goal difference when head-to-head applies).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Hashable, Protocol, Sequence, TypeVar


WIN, DRAW, LOSS = "win", "draw", "loss"

K = TypeVar("K", bound=Hashable)


class PointRule(Protocol):
    """Structural contract satisfied by ``StandingsPointRules``."""

    win_points: int
    draw_points: int
    loss_points: int
    suspended_winner_points: int
    suspended_loser_points: int


@dataclass(frozen=True)
class RankedResult(Generic[K]):
    """One counted fixture. Suspended results use the award rule, not the score."""

    home: K
    away: K
    home_goals: int
    away_goals: int
    suspended: bool = False


@dataclass
class TeamRecord(Generic[K]):
    team: K
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    penalized: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


def match_points(result: RankedResult[K], rules: PointRule) -> tuple[int, int, str, str]:
    """Return home/away points and results under the official rule."""
    if result.home_goals > result.away_goals:
        home_result, away_result = WIN, LOSS
    elif result.away_goals > result.home_goals:
        home_result, away_result = LOSS, WIN
    else:
        home_result = away_result = DRAW

    if result.suspended:
        home_points = rules.suspended_winner_points if home_result == WIN else rules.suspended_loser_points
        away_points = rules.suspended_winner_points if away_result == WIN else rules.suspended_loser_points
    else:
        home_points = rules.win_points if home_result == WIN else rules.draw_points if home_result == DRAW else rules.loss_points
        away_points = rules.win_points if away_result == WIN else rules.draw_points if away_result == DRAW else rules.loss_points
    return home_points, away_points, home_result, away_result


def apply_result(records: dict[K, TeamRecord[K]], result: RankedResult[K], rules: PointRule) -> None:
    """Update records in place, mirroring the standings service semantics."""
    home, away = records[result.home], records[result.away]
    home_points, away_points, home_result, away_result = match_points(result, rules)

    home.played += 1
    away.played += 1
    home.points += home_points
    away.points += away_points
    home.goals_for += result.home_goals
    home.goals_against += result.away_goals
    away.goals_for += result.away_goals
    away.goals_against += result.home_goals

    if result.suspended:
        # The suspended award replaces the normal result counters: the loser is
        # penalized (CP) instead of accumulating a defeat, and a tied award
        # leaves both sides penalized without a draw.
        if home_result == WIN:
            home.won += 1
            away.penalized += 1
        elif away_result == WIN:
            away.won += 1
            home.penalized += 1
        else:
            home.penalized += 1
            away.penalized += 1
        return

    if home_result == WIN:
        home.won += 1
        away.lost += 1
    elif away_result == WIN:
        away.won += 1
        home.lost += 1
    else:
        home.drawn += 1
        away.drawn += 1


def build_records(
    results: Sequence[RankedResult[K]],
    rules: PointRule,
    teams: Sequence[K] = (),
) -> dict[K, TeamRecord[K]]:
    """Build overall records for every team, including teams without results."""
    records = {team: TeamRecord(team) for team in teams}
    for result in results:
        records.setdefault(result.home, TeamRecord(result.home))
        records.setdefault(result.away, TeamRecord(result.away))
        apply_result(records, result, rules)
    return records


def mini_records(
    group: Sequence[K],
    results: Sequence[RankedResult[K]],
    rules: PointRule,
) -> dict[K, TeamRecord[K]]:
    """Records from the matches played only between the tied teams."""
    members = set(group)
    return build_records(
        [result for result in results if result.home in members and result.away in members],
        rules,
        teams=group,
    )


def rank_groups(
    records: dict[K, TeamRecord[K]],
    results: Sequence[RankedResult[K]],
    rules: PointRule,
) -> list[list[K]]:
    """Rank teams, returning residual exact ties as ordered groups.

    Each inner group contains teams that remain level after points, the Olympic
    mini-table, overall goal difference, and overall goals scored. Position
    consumers decide how to display that residual tie.
    """
    by_points: dict[int, list[K]] = {}
    for team, record in records.items():
        by_points.setdefault(record.points, []).append(team)
    ordered_groups: list[list[K]] = []
    for points in sorted(by_points, reverse=True):
        ordered_groups.extend(_break_tie(sorted(by_points[points], key=str), records, results, rules))
    return ordered_groups


def flatten(groups: Sequence[Sequence[K]]) -> list[K]:
    return [team for group in groups for team in group]


def _break_tie(
    group: list[K],
    records: dict[K, TeamRecord[K]],
    results: Sequence[RankedResult[K]],
    rules: PointRule,
) -> list[list[K]]:
    if len(group) <= 1:
        return [group]

    mini = mini_records(group, results, rules)
    ordered = sorted(
        group,
        key=lambda team: (-mini[team].points, -mini[team].goal_difference, -mini[team].goals_for, str(team)),
    )
    buckets = _buckets(ordered, lambda team: (mini[team].points, mini[team].goal_difference, mini[team].goals_for))
    if len(buckets) > 1:
        separated: list[list[K]] = []
        for bucket in buckets:
            separated.extend(_break_tie(bucket, records, results, rules))
        return separated

    # The mini-table did not separate anyone. The official procedure then uses
    # the overall record; if that still ties, the group is returned as a tie.
    ordered = sorted(
        group,
        key=lambda team: (-records[team].goal_difference, -records[team].goals_for, str(team)),
    )
    return _buckets(ordered, lambda team: (records[team].goal_difference, records[team].goals_for))


def _buckets(ordered: Sequence[K], key) -> list[list[K]]:
    buckets: list[list[K]] = []
    for team in ordered:
        if buckets and key(buckets[-1][0]) == key(team):
            buckets[-1].append(team)
        else:
            buckets.append([team])
    return buckets

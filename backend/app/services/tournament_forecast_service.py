"""Deterministic, explainable tournament forecast primitives.

This is deliberately a statistical estimate, not betting advice.  It uses only
scoreline history and the published remaining fixture, then applies the same
points and tiebreak rules as the standings service in Monte Carlo simulations.
"""
from __future__ import annotations

from bisect import bisect_left
from copy import copy
from dataclasses import dataclass
from math import exp, log
from random import Random
from typing import Any

from app.services.competition_ranking import RankedResult, TeamRecord, apply_result, rank_groups
from app.services.standings_service import StandingsPointRules, load_point_rules


SIMULATIONS = 20_000
MAX_GOALS = 60
RECENCY_HALF_LIFE_ROUNDS = 8.0
RIDGE_PENALTY = 4.0
FIT_ITERATIONS = 900


@dataclass(frozen=True)
class HistoricalResult:
    home: str
    away: str
    home_goals: int
    away_goals: int
    round_number: int = 0
    suspended: bool = False


@dataclass(frozen=True)
class RemainingFixture:
    round_number: int
    date: str | None
    home: str
    away: str
    status: str = "scheduled"

    @property
    def playable(self) -> bool:
        """Only fixtures that can still award points belong in a projection."""
        return self.status not in {"suspended", "cancelled"}


@dataclass(frozen=True)
class PlayerMatchObservation:
    """Confirmed-sheet contribution for a selected player in one match."""

    name: str
    round_number: int
    goals: int
    two_minute: bool
    ejected: bool
    expected_team_goals: float


def _poisson_at_least(mean: float, threshold: int) -> float:
    """Return P(X >= threshold) for a Poisson scoring count."""
    cumulative = 0.0
    probability = exp(-mean)
    for goals in range(threshold):
        if goals:
            probability *= mean / goals
        cumulative += probability
    return 1 - cumulative


def build_player_match_forecast(
    squad: list[str],
    observations: list[PlayerMatchObservation],
    expected_team_goals: float,
) -> list[dict[str, Any]]:
    """Project selected players from confirmed sheets and opponent-adjusted context.

    Each player's scoring share is estimated from his goals relative to SAPA's
    expected team goals in the opponents already faced.  Exponential recency
    weights and a small shared prior prevent a short run from becoming a false
    certainty; selected-player shares are then reconciled to the team goal
    forecast for the upcoming fixture.
    """
    if not squad or expected_team_goals <= 0:
        return []

    latest_round = max((item.round_number for item in observations), default=0)
    weighted: dict[str, dict[str, float]] = {
        name: {"goals": 0.0, "exposure": 0.0, "appearances": 0.0, "actual_appearances": 0.0, "two_minute": 0.0, "ejected": 0.0}
        for name in squad
    }
    for item in observations:
        if item.name not in weighted or item.expected_team_goals <= 0:
            continue
        weight = exp(-log(2) * max(0, latest_round - item.round_number) / RECENCY_HALF_LIFE_ROUNDS)
        row = weighted[item.name]
        row["goals"] += weight * item.goals
        row["exposure"] += weight * item.expected_team_goals
        row["appearances"] += weight
        row["actual_appearances"] += 1
        row["two_minute"] += weight * int(item.two_minute)
        row["ejected"] += weight * int(item.ejected)

    total_appearances = sum(row["appearances"] for row in weighted.values())
    two_minute_baseline = sum(row["two_minute"] for row in weighted.values()) / total_appearances if total_appearances else 0.0
    ejection_baseline = sum(row["ejected"] for row in weighted.values()) / total_appearances if total_appearances else 0.0

    # A prior of 1.5 goals over eight contextual expected team goals smooths
    # sparse scorers while preserving the relative confirmed-sheet evidence.
    shares = {
        name: (row["goals"] + 1.5) / (row["exposure"] + 8.0)
        for name, row in weighted.items()
    }
    share_total = sum(shares.values())
    rows = []
    for name in squad:
        row = weighted[name]
        mean = expected_team_goals * shares[name] / share_total
        appearances = int(row["actual_appearances"])
        # Eight weighted appearances of shared team discipline is deliberately
        # conservative for rare cards and prevents zero-history certainty.
        two_minute_probability = (row["two_minute"] + 8 * two_minute_baseline) / (row["appearances"] + 8)
        ejection_probability = (row["ejected"] + 16 * ejection_baseline) / (row["appearances"] + 16)
        rows.append(
            {
                "name": name,
                "appearances": appearances,
                "expected_goals": round(mean, 2),
                "one_or_more_goals_probability": round(_poisson_at_least(mean, 1), 4),
                "three_or_more_goals_probability": round(_poisson_at_least(mean, 3), 4),
                "two_minute_probability": round(two_minute_probability, 4),
                "ejection_probability": round(ejection_probability, 4),
                "confidence": "strong" if appearances >= 10 else "moderate" if appearances >= 5 else "exploratory",
            }
        )
    return sorted(rows, key=lambda row: (-row["expected_goals"], row["name"]))


def _poisson_cdf(mean: float) -> list[float]:
    probability = exp(-mean)
    total = probability
    cdf = [total]
    for goals in range(1, MAX_GOALS + 1):
        probability *= mean / goals
        total += probability
        cdf.append(total)
    return [value / total for value in cdf]


def _sample_score(cdf: list[float], rng: Random) -> int:
    return bisect_left(cdf, rng.random())


def _value(row: dict[str, Any], public_key: str, internal_key: str) -> Any:
    return row[public_key] if public_key in row else row[internal_key]


def _outcome_probabilities(home_mean: float, away_mean: float) -> dict[str, float]:
    home = _poisson_cdf(home_mean)
    away = _poisson_cdf(away_mean)
    home_win = draw = away_win = 0.0
    previous_home = 0.0
    for home_goals, home_cumulative in enumerate(home):
        home_probability = home_cumulative - previous_home
        previous_home = home_cumulative
        previous_away = 0.0
        for away_goals, away_cumulative in enumerate(away):
            away_probability = away_cumulative - previous_away
            previous_away = away_cumulative
            if home_goals > away_goals:
                home_win += home_probability * away_probability
            elif home_goals == away_goals:
                draw += home_probability * away_probability
            else:
                away_win += home_probability * away_probability
    return {"home_win": home_win, "draw": draw, "away_win": away_win}


@dataclass(frozen=True)
class FittedGoalModel:
    intercept: float
    home_advantage: float
    attack: dict[str, float]
    defense: dict[str, float]


def _fit_goal_model(teams: list[str], history: list[HistoricalResult]) -> FittedGoalModel:
    """Fit a regularized attack/defense Poisson model with recency weighting.

    The ridge penalty and zero-centering prevent a single high-scoring match or
    a short schedule from producing bookmaker-like false certainty.
    """
    observed_mean = sum(match.home_goals + match.away_goals for match in history) / max(1, len(history) * 2)
    intercept, home_advantage = log(observed_mean or 26.0), 0.0
    attack = {team: 0.0 for team in teams}
    defense = {team: 0.0 for team in teams}
    latest_round = max((match.round_number for match in history), default=0)
    weights = [exp(-log(2) * max(0, latest_round - match.round_number) / RECENCY_HALF_LIFE_ROUNDS) for match in history]
    weight_total = max(1.0, sum(weights) * 2)

    for _ in range(FIT_ITERATIONS):
        gradient_attack = {team: -RIDGE_PENALTY * value for team, value in attack.items()}
        gradient_defense = {team: -RIDGE_PENALTY * value for team, value in defense.items()}
        gradient_intercept = -RIDGE_PENALTY * (intercept - log(26.0))
        gradient_home = -RIDGE_PENALTY * home_advantage
        for match, weight in zip(history, weights):
            home_mean = exp(intercept + home_advantage + attack[match.home] - defense[match.away])
            away_mean = exp(intercept + attack[match.away] - defense[match.home])
            home_residual, away_residual = weight * (match.home_goals - home_mean), weight * (match.away_goals - away_mean)
            gradient_intercept += home_residual + away_residual
            gradient_home += home_residual
            gradient_attack[match.home] += home_residual
            gradient_defense[match.away] -= home_residual
            gradient_attack[match.away] += away_residual
            gradient_defense[match.home] -= away_residual
        step = 0.01 / weight_total
        intercept += step * gradient_intercept
        home_advantage += step * gradient_home
        for team in teams:
            attack[team] += step * gradient_attack[team]
            defense[team] += step * gradient_defense[team]
        attack_mean = sum(attack.values()) / len(teams)
        defense_mean = sum(defense.values()) / len(teams)
        for team in teams:
            attack[team] -= attack_mean
            defense[team] -= defense_mean
    return FittedGoalModel(intercept, home_advantage, attack, defense)


def _expected_goals(home: str, away: str, model: FittedGoalModel) -> tuple[float, float]:
    return (
        exp(model.intercept + model.home_advantage + model.attack[home] - model.defense[away]),
        exp(model.intercept + model.attack[away] - model.defense[home]),
    )


def build_forecast(
    standings: list[dict[str, Any]],
    history: list[HistoricalResult],
    fixtures: list[RemainingFixture],
    *,
    simulations: int = SIMULATIONS,
    seed: int = 20261110,
    rules: StandingsPointRules | None = None,
) -> dict[str, Any]:
    """Return public-safe probabilities for a league's unplayed fixtures.

    The table is rebuilt and fully ranked in every simulation, so the result
    includes first/second/third and podium probabilities, not just the champion.
    Points always come from the versioned competition rule.

    ``standings`` supplies the starting points/goals and ``history`` must cover
    the same counted matches, because the Olympic tiebreak is resolved from the
    results between level clubs. The exporter builds both from one fixture read,
    so they cannot drift.
    """
    rules = rules or load_point_rules()
    playable = [fixture for fixture in fixtures if fixture.playable]
    if not standings or not playable:
        return {
            "simulations": simulations,
            "methodology": "Sin fixture pendiente para proyectar.",
            "points_rule": _points_rule_payload(rules),
            "teams": [],
            "fixtures": [],
        }

    teams = [_value(row, "club", "name") for row in standings]
    if len(set(teams)) != len(teams):
        raise ValueError("A forecast needs unique public club names within the stage.")
    model = _fit_goal_model(teams, history)
    fixture_models = []
    for fixture in playable:
        home_mean, away_mean = _expected_goals(fixture.home, fixture.away, model)
        fixture_models.append(
            (
                fixture,
                _poisson_cdf(home_mean),
                _poisson_cdf(away_mean),
                _outcome_probabilities(home_mean, away_mean),
            )
        )

    position_totals = {club: [0.0] * len(teams) for club in teams}
    base_results = [
        RankedResult(item.home, item.away, item.home_goals, item.away_goals, item.suspended)
        for item in history
    ]
    # The standings passed by the exporter already reflect every counted result,
    # including reported-only matches; use them as the starting table. History is
    # still needed because the Olympic tiebreak is resolved from the matches
    # between level clubs.
    base_records = {}
    for row in standings:
        club = _value(row, "club", "name")
        goals_for = int(_value(row, "goals_for", "gf"))
        goals_against = int(row["goals_against"]) if "goals_against" in row else goals_for - int(_value(row, "goal_difference", "gd"))
        base_records[club] = TeamRecord(
            team=club,
            points=int(_value(row, "points", "pts")),
            goals_for=goals_for,
            goals_against=goals_against,
        )
    rng = Random(seed)
    for _ in range(simulations):
        records = {club: copy(record) for club, record in base_records.items()}
        simulated_results = list(base_results)
        for fixture, home_cdf, away_cdf, _ in fixture_models:
            home_goals, away_goals = _sample_score(home_cdf, rng), _sample_score(away_cdf, rng)
            result = RankedResult(fixture.home, fixture.away, home_goals, away_goals)
            simulated_results.append(result)
            apply_result(records, result, rules)
        position = 0
        for group in rank_groups(records, simulated_results, rules):
            share = 1.0 / len(group)
            for club in group:
                totals = position_totals[club]
                for occupied in range(position, position + len(group)):
                    totals[occupied] += share
            position += len(group)

    rows: list[dict[str, Any]] = []
    for club, totals in position_totals.items():
        probabilities = [total / simulations for total in totals]
        first = probabilities[0] if len(probabilities) > 0 else 0.0
        second = probabilities[1] if len(probabilities) > 1 else 0.0
        third = probabilities[2] if len(probabilities) > 2 else 0.0
        rows.append(
            {
                "club": club,
                "champion_probability": round(first, 4),
                "finish_probabilities": {
                    "first": round(first, 4),
                    "second": round(second, 4),
                    "third": round(third, 4),
                },
                # Summed from the simulation counts, never from the rounded parts.
                "podium_probability": round(first + second + third, 4),
                "expected_position": round(
                    sum(position * probability for position, probability in enumerate(probabilities, start=1)),
                    2,
                ),
            }
        )
    rows.sort(
        key=lambda row: (
            -row["podium_probability"],
            -row["champion_probability"],
            row["expected_position"],
            row["club"],
        )
    )

    return {
        "simulations": simulations,
        "methodology": (
            "Modelo Poisson regularizado de ataque/defensa, ponderado por recencia y localía, "
            "ajustado sobre los resultados del torneo. Cada simulación reconstruye y ordena la "
            "tabla completa con la regla vigente de puntos (configuración del torneo) y el "
            "desempate olímpico: primero los partidos entre los equipos igualados, luego la "
            "diferencia de gol y los goles a favor generales. Si después de todo persiste una "
            "igualdad exacta, la probabilidad de puesto se reparte entre los equipos igualados. "
            "Es una estimación estadística, no una cuota ni una garantía."
        ),
        "points_rule": _points_rule_payload(rules),
        "teams": rows,
        "fixtures": [
            {
                "round": item.round_number,
                "date": item.date,
                "home": item.home,
                "away": item.away,
                "home_win_probability": round(probabilities["home_win"], 4),
                "draw_probability": round(probabilities["draw"], 4),
                "away_win_probability": round(probabilities["away_win"], 4),
            }
            for item, _, _, probabilities in fixture_models
        ],
    }


def _points_rule_payload(rules: StandingsPointRules) -> dict[str, int]:
    return {
        "win": rules.win_points,
        "draw": rules.draw_points,
        "loss": rules.loss_points,
        "suspended_win": rules.suspended_winner_points,
        "suspended_loss": rules.suspended_loser_points,
    }

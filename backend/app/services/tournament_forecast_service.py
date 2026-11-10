"""Deterministic, explainable tournament forecast primitives.

This is deliberately a statistical estimate, not betting advice.  It uses only
scoreline history and the published remaining fixture, then applies the same
points and tiebreak rules as the standings service in Monte Carlo simulations.
"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from math import exp, log
from random import Random
from typing import Any


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


@dataclass(frozen=True)
class RemainingFixture:
    round_number: int
    date: str | None
    home: str
    away: str


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
) -> dict[str, Any]:
    """Return public-safe probabilities for a league's unplayed fixtures."""
    if not standings or not fixtures:
        return {"simulations": simulations, "methodology": "Sin fixture pendiente para proyectar.", "teams": [], "fixtures": []}

    teams = [_value(row, "club", "name") for row in standings]
    model = _fit_goal_model(teams, history)
    fixture_models = []
    for fixture in fixtures:
        home_mean, away_mean = _expected_goals(fixture.home, fixture.away, model)
        fixture_models.append((fixture, _poisson_cdf(home_mean), _poisson_cdf(away_mean), _outcome_probabilities(home_mean, away_mean)))

    champions = {_value(row, "club", "name"): 0 for row in standings}
    rng = Random(seed)
    for _ in range(simulations):
        table = {
            _value(row, "club", "name"): {
                "points": _value(row, "points", "pts"),
                "gd": _value(row, "goal_difference", "gd"),
                "gf": _value(row, "goals_for", "gf"),
            }
            for row in standings
        }
        for fixture, home_cdf, away_cdf, _ in fixture_models:
            home_goals, away_goals = _sample_score(home_cdf, rng), _sample_score(away_cdf, rng)
            home, away = table[fixture.home], table[fixture.away]
            home["gf"] += home_goals; home["gd"] += home_goals - away_goals
            away["gf"] += away_goals; away["gd"] += away_goals - home_goals
            if home_goals > away_goals:
                home["points"] += 3; away["points"] += 1
            elif away_goals > home_goals:
                away["points"] += 3; home["points"] += 1
            else:
                home["points"] += 2; away["points"] += 2
        champion = max(table, key=lambda club: (table[club]["points"], table[club]["gd"], table[club]["gf"]))
        champions[champion] += 1

    return {
        "simulations": simulations,
        "methodology": "Modelo Poisson regularizado de ataque/defensa, ponderado por recencia y localía, ajustado sobre resultados del torneo; simula marcadores, fixture y desempates reales. Es una estimación estadística, no una cuota ni una garantía.",
        "teams": [{"club": club, "champion_probability": round(wins / simulations, 4)} for club, wins in sorted(champions.items(), key=lambda item: (-item[1], item[0]))],
        "fixtures": [
            {"round": item.round_number, "date": item.date, "home": item.home, "away": item.away, "home_win_probability": round(probabilities["home_win"], 4), "draw_probability": round(probabilities["draw"], 4), "away_win_probability": round(probabilities["away_win"], 4)}
            for item, _, _, probabilities in fixture_models
        ],
    }

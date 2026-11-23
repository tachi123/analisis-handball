from app.services.competition_ranking import RankedResult, TeamRecord, apply_result
from app.services.standings_service import load_point_rules
from app.services.tournament_forecast_service import (
    HistoricalResult,
    PlayerMatchObservation,
    RemainingFixture,
    _expected_goals,
    _fit_goal_model,
    build_player_match_forecast,
    build_forecast,
)


def test_forecast_is_deterministic_and_respects_probability_bounds():
    standings = [
        {"name": "S.A.P.A.", "pts": 32, "gd": 19, "gf": 347},
        {"name": "Lanús C", "pts": 34, "gd": 62, "gf": 394},
    ]
    history = [
        HistoricalResult("S.A.P.A.", "Lanús C", 30, 28),
        HistoricalResult("Lanús C", "S.A.P.A.", 31, 27),
    ]
    fixtures = [RemainingFixture(14, "2026-11-14", "S.A.P.A.", "Lanús C")]

    first = build_forecast(standings, history, fixtures, simulations=500, seed=7)
    second = build_forecast(standings, history, fixtures, simulations=500, seed=7)

    assert first == second
    probabilities = first["fixtures"][0]
    assert 0.99 <= probabilities["home_win_probability"] + probabilities["draw_probability"] + probabilities["away_win_probability"] <= 1.01
    assert sum(row["champion_probability"] for row in first["teams"]) == 1


def test_regularized_goal_model_separates_attack_and_defense_without_extreme_means():
    history = [
        HistoricalResult("Attack", "Defense", 35, 22, 1),
        HistoricalResult("Defense", "Attack", 20, 33, 2),
        HistoricalResult("Attack", "Defense", 34, 21, 3),
        HistoricalResult("Defense", "Attack", 23, 32, 4),
    ]

    model = _fit_goal_model(["Attack", "Defense"], history)
    attack_goals, defense_goals = _expected_goals("Attack", "Defense", model)

    assert attack_goals > defense_goals
    assert 10 < attack_goals < 50
    assert 10 < defense_goals < 50


def test_forecast_ranks_the_full_table_and_counts_every_position():
    standings = [
        {"name": "Alpha", "pts": 10, "gd": 0, "gf": 100},
        {"name": "Beta", "pts": 10, "gd": 0, "gf": 100},
        {"name": "Gamma", "pts": 1, "gd": -10, "gf": 90},
        {"name": "Delta", "pts": 0, "gd": -20, "gf": 80},
    ]
    fixtures = [RemainingFixture(2, None, "Gamma", "Delta")]

    result = build_forecast(standings, [], fixtures, simulations=400, seed=3)

    assert result["points_rule"] == {"win": 3, "draw": 2, "loss": 1, "suspended_win": 3, "suspended_loss": 0}
    assert abs(sum(row["champion_probability"] for row in result["teams"]) - 1.0) <= 0.0002
    for row in result["teams"]:
        finish = row["finish_probabilities"]
        assert row["podium_probability"] == round(finish["first"] + finish["second"] + finish["third"], 4)
        assert 1 <= row["expected_position"] <= len(standings)
        assert 0 <= finish["first"] <= 1 and 0 <= finish["second"] <= 1 and 0 <= finish["third"] <= 1


def test_residual_exact_ties_share_positions():
    standings = [
        {"name": "Alpha", "pts": 10, "gd": 0, "gf": 100},
        {"name": "Beta", "pts": 10, "gd": 0, "gf": 100},
        {"name": "Gamma", "pts": 1, "gd": -10, "gf": 90},
        {"name": "Delta", "pts": 0, "gd": -20, "gf": 80},
    ]
    result = build_forecast(standings, [], [RemainingFixture(2, None, "Gamma", "Delta")], simulations=200, seed=5)
    alpha = next(row for row in result["teams"] if row["club"] == "Alpha")

    assert alpha["finish_probabilities"]["first"] == 0.5
    assert alpha["finish_probabilities"]["second"] == 0.5
    assert alpha["podium_probability"] == 1.0
    assert alpha["expected_position"] == 1.5


def test_forecast_applies_the_olympic_tiebreak():
    standings = [
        {"name": "Alpha", "pts": 10, "gd": 10, "gf": 100},
        {"name": "Beta", "pts": 10, "gd": 10, "gf": 100},
        {"name": "Gamma", "pts": 1, "gd": -10, "gf": 90},
        {"name": "Delta", "pts": 0, "gd": -20, "gf": 80},
    ]
    history = [HistoricalResult("Alpha", "Beta", 30, 20, 1)]
    fixtures = [RemainingFixture(2, None, "Gamma", "Delta")]

    result = build_forecast(standings, history, fixtures, simulations=100, seed=1)
    alpha = next(row for row in result["teams"] if row["club"] == "Alpha")
    beta = next(row for row in result["teams"] if row["club"] == "Beta")

    assert alpha["champion_probability"] == 1.0
    assert beta["champion_probability"] == 0.0
    assert alpha["expected_position"] == 1.0


def test_suspended_pending_fixture_is_not_projected():
    standings = [
        {"name": "Alpha", "pts": 10, "gd": 0, "gf": 100},
        {"name": "Beta", "pts": 8, "gd": -4, "gf": 95},
    ]
    result = build_forecast(standings, [], [RemainingFixture(2, None, "Alpha", "Beta", status="suspended")], simulations=50)

    assert result["teams"] == []
    assert result["fixtures"] == []


def test_apply_result_uses_the_versioned_points_rule():
    records = {
        "Alpha": TeamRecord(team="Alpha", points=10),
        "Beta": TeamRecord(team="Beta", points=10),
    }

    apply_result(records, RankedResult("Alpha", "Beta", 30, 26), load_point_rules())

    assert records["Alpha"].points == 13
    assert records["Beta"].points == 11
    assert records["Alpha"].goal_difference == 4
    assert records["Beta"].goals_for == 26


def test_player_forecast_is_selected_squad_only_and_reconciles_to_team_goals():
    observations = [
        PlayerMatchObservation("Top scorer", 1, 6, True, False, 30),
        PlayerMatchObservation("Top scorer", 2, 5, False, False, 28),
        PlayerMatchObservation("Contributor", 1, 2, False, False, 30),
        PlayerMatchObservation("Contributor", 2, 3, True, True, 28),
        # A non-selected player must not receive any upcoming probability.
        PlayerMatchObservation("Absent", 2, 9, False, False, 28),
    ]

    projected = build_player_match_forecast(["Top scorer", "Contributor"], observations, 24)

    assert [row["name"] for row in projected] == ["Top scorer", "Contributor"]
    assert round(sum(row["expected_goals"] for row in projected), 1) == 24.0
    top = projected[0]
    contributor = projected[1]
    assert top["one_or_more_goals_probability"] > contributor["one_or_more_goals_probability"]
    assert contributor["ejection_probability"] > 0
    assert top["appearances"] == 2
    assert top["confidence"] == "exploratory"

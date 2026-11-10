from app.services.tournament_forecast_service import HistoricalResult, RemainingFixture, _expected_goals, _fit_goal_model, build_forecast


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

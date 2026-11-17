"""Focused tests for descriptive tournament insights."""

from app.services.standings_service import load_point_rules
from app.services.tournament_insights_service import (
    ObservedMatch,
    annual_profile,
    club_insights,
    roster_continuity,
)


ROUND_ROBIN = [
    ObservedMatch(1, "2026-01-01", "A", "B", 30, 20),
    ObservedMatch(1, "2026-01-01", "C", "D", 25, 25),
    ObservedMatch(2, "2026-01-08", "C", "A", 26, 27),
    ObservedMatch(2, "2026-01-08", "B", "D", 28, 27),
    ObservedMatch(3, "2026-01-15", "A", "D", 31, 29),
    ObservedMatch(3, "2026-01-15", "B", "C", 26, 24),
]


def test_effectiveness_splits_and_streaks():
    insights = club_insights(ROUND_ROBIN)
    club = next(row for row in insights["clubs"] if row["club"] == "A")

    assert (club["played"], club["won"], club["drawn"], club["lost"]) == (3, 3, 0, 0)
    assert club["points"] == 9 and club["max_points"] == 9
    assert club["points_effectiveness"] == 1.0
    assert club["win_rate"] == 1.0
    assert (club["goals_for"], club["goals_against"], club["goal_difference"]) == (88, 75, 13)
    assert club["goals_for_per_game"] == 29.33
    assert club["goals_against_per_game"] == 25.0
    assert (club["home"]["played"], club["home"]["points"]) == (2, 6)
    assert (club["away"]["played"], club["away"]["points"]) == (1, 3)
    assert club["streaks"]["longest_win"] == {"length": 3, "from_round": 1, "to_round": 3}
    assert club["streaks"]["current_unbeaten"]["length"] == 3
    assert club["form_last_5"]["sequence"] == ["G", "G", "G"]
    assert club["biggest_win"]["margin"] == 10
    assert club["biggest_loss"] is None


def test_opponent_tiers_stay_disjoint_and_use_recorded_results():
    insights = club_insights(ROUND_ROBIN)
    club = next(row for row in insights["clubs"] if row["club"] == "A")

    assert club["opponent_tiers"]["top_five"]["played"] == 1
    assert club["opponent_tiers"]["bottom_five"]["played"] == 2
    assert club["opponent_tiers"]["bottom_five"]["points"] == 6
    assert club["opponent_tiers"]["bottom_five"]["max_points"] == 6
    assert club["opponent_tiers"]["middle"]["played"] == 0


def test_league_records_are_derived_from_the_same_dataset():
    insights = club_insights(ROUND_ROBIN)
    records = {record["key"]: record for record in insights["records"]}

    assert records["longest_unbeaten"]["club"] == "A"
    assert records["longest_unbeaten"]["value"] == 3
    assert records["longest_win"]["club"] == "A"
    assert records["best_attack"]["club"] == "A"
    assert records["best_defense"]["club"] == "A"
    assert records["best_form"]["value"] == 9
    assert set(records["perfect_vs_bottom_five"]["clubs"]) == {"A", "B"}


def test_suspended_match_uses_the_official_rule_and_is_disclosed():
    matches = [
        ObservedMatch(1, "2026-01-01", "A", "B", 3, 0, status="suspended"),
        ObservedMatch(2, "2026-01-08", "A", "B", 26, 26),
    ]
    insights = club_insights(matches, rules=load_point_rules())
    club = next(row for row in insights["clubs"] if row["club"] == "A")

    assert insights["suspended_matches"] == 1
    assert club["suspended_matches"] == 1
    assert club["points"] == 5  # 3 for the suspended win, 2 for the draw
    assert club["won"] == 1 and club["drawn"] == 1
    assert club["biggest_win"] is None  # suspended results never look like a rout


def test_annual_profile_sums_labelled_competitions_without_merging_tables():
    profile = annual_profile(
        "Lanús C",
        [
            {"key": "apertura", "label": "Apertura 2026 · Zona B", "position": 13, "played": 15, "won": 4, "drawn": 0, "lost": 11, "points": 23, "goals_for": 380, "goals_against": 410},
            {"key": "permanencia", "label": "Permanencia 2026", "position": 1, "played": 14, "won": 11, "drawn": 1, "lost": 2, "points": 37, "goals_for": 420, "goals_against": 356},
        ],
    )

    assert profile["club"] == "Lanús C"
    assert [block["position"] for block in profile["competitions"]] == [13, 1]
    assert profile["combined"]["played"] == 29
    assert profile["combined"]["points"] == 60
    assert profile["combined"]["goals_for"] == 800
    assert profile["combined"]["points_effectiveness"] == 0.69
    assert "no es una tabla" in profile["combined"]["label"]


def test_roster_continuity_matches_normalized_names_only_within_the_club():
    continuity = roster_continuity(
        ["Pérez, Juan", "Gómez, Ana", "Viejo, Pedro"],
        ["Juan Perez", "Ana Gomez", "Nuevo, Leo"],
    )

    assert continuity["previous_players"] == 3
    assert continuity["current_players"] == 3
    assert continuity["shared_players"] == 2
    assert continuity["retained_share"] == 0.667
    assert "aproximación" in continuity["note"] or "no es un registro" in continuity["note"]

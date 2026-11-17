"""Tests for the shared handball Olympic tiebreak."""

from app.services.competition_ranking import (
    RankedResult,
    build_records,
    flatten,
    rank_groups,
)
from app.services.standings_service import load_point_rules


RULES = load_point_rules()


def order(results):
    records = build_records(results, RULES)
    return flatten(rank_groups(records, results, RULES))


def test_head_to_head_beats_a_better_overall_goal_difference():
    results = [
        RankedResult("A", "B", 30, 29),  # A wins the direct match
        RankedResult("A", "C", 20, 40),
        RankedResult("B", "D", 40, 20),
        RankedResult("C", "D", 30, 20),
    ]
    records = build_records(results, RULES)

    assert records["A"].points == 4 and records["B"].points == 4
    assert records["A"].goal_difference == -19
    assert records["B"].goal_difference == 19
    # The direct match outranks the much better overall difference.
    assert order(results) == ["C", "A", "B", "D"]


def test_three_way_tie_uses_the_mini_table():
    results = [
        RankedResult("A", "B", 30, 20),
        RankedResult("B", "C", 31, 20),
        RankedResult("C", "A", 32, 21),
        RankedResult("A", "D", 30, 20),
        RankedResult("B", "D", 30, 20),
        RankedResult("C", "D", 30, 20),
    ]

    # The mini-table goal differences are B +1, C 0, A -1.
    assert order(results) == ["B", "C", "A", "D"]


def test_overall_difference_is_the_fallback_when_the_mini_table_ties():
    results = [
        RankedResult("A", "B", 30, 20),
        RankedResult("B", "C", 30, 20),
        RankedResult("C", "A", 30, 20),
        RankedResult("A", "D", 40, 20),
        RankedResult("B", "D", 30, 20),
        RankedResult("C", "D", 21, 20),
    ]

    # All three beat each other by ten, so the mini-table is identical; the
    # overall difference against D separates them.
    assert order(results) == ["A", "B", "C", "D"]


def test_residual_tie_is_returned_as_a_group():
    results = [
        RankedResult("A", "C", 30, 20),
        RankedResult("B", "C", 30, 20),
    ]
    records = build_records(results, RULES)
    groups = rank_groups(records, results, RULES)

    assert groups[0] == ["A", "B"]
    assert groups[1] == ["C"]
    assert len(groups[0]) == 2


def test_suspended_award_uses_three_and_zero_and_marks_the_loser_penalized():
    results = [RankedResult("A", "B", 3, 0, suspended=True)]
    records = build_records(results, RULES)

    assert records["A"].points == 3 and records["A"].won == 1
    assert records["B"].points == 0 and records["B"].penalized == 1
    assert records["B"].lost == 0

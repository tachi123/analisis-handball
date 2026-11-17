"""Descriptive tournament insights derived from observed results.

These helpers answer «how is this club doing?» using only recorded scores,
fixtures, and planilla aggregates. They never infer tactical causes: a long
unbeaten run, a perfect record against the bottom five, or a heavy defeat are
observed facts, not explanations of why they happened.

Every function is pure so the exporter can compose artifacts without a live
database and the browser receives only numbers and public names.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from app.services.competition_ranking import (
    DRAW,
    LOSS,
    WIN,
    RankedResult,
    build_records,
    flatten,
    match_points,
    rank_groups,
)
from app.services.planilla_player_identity_service import normalize_name
from app.services.standings_service import StandingsPointRules, load_point_rules


SCHEMA_VERSION = "tournament-insights-v1"


@dataclass(frozen=True)
class ObservedMatch:
    """One scheduled fixture with a final score, from the public fixture."""

    round_number: int
    date: str | None
    home: str
    away: str
    home_goals: int
    away_goals: int
    status: str = "played"

    @property
    def counted(self) -> bool:
        """Cancelled fixtures never award points; suspended ones do (3/0)."""
        return self.status != "cancelled"

    @property
    def suspended(self) -> bool:
        return self.status == "suspended"


def _row(club: str) -> dict[str, Any]:
    return {
        "club": club,
        "played": 0,
        "won": 0,
        "drawn": 0,
        "lost": 0,
        "points": 0,
        "goals_for": 0,
        "goals_against": 0,
        "suspended_matches": 0,
        "home": {"played": 0, "points": 0, "won": 0, "drawn": 0, "lost": 0, "goals_for": 0, "goals_against": 0},
        "away": {"played": 0, "points": 0, "won": 0, "drawn": 0, "lost": 0, "goals_for": 0, "goals_against": 0},
    }


_COUNTER = {WIN: "won", DRAW: "drawn", LOSS: "lost"}


def _add(row: dict[str, Any], side: str, goals_for: int, goals_against: int, points: int, result: str, suspended: bool) -> None:
    row["played"] += 1
    row[_COUNTER[result]] += 1
    row["points"] += points
    row["goals_for"] += goals_for
    row["goals_against"] += goals_against
    row["suspended_matches"] += 1 if suspended else 0
    split = row[side]
    split["played"] += 1
    split["points"] += points
    split[_COUNTER[result]] += 1
    split["goals_for"] += goals_for
    split["goals_against"] += goals_against


def _ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def _per_game(total: float, played: int) -> float:
    return round(total / played, 2) if played else 0.0


def _longest(games: Sequence[dict[str, Any]], wanted: set[str]) -> dict[str, Any]:
    best = {"length": 0, "from_round": None, "to_round": None}
    current = {"length": 0, "from_round": None, "to_round": None}
    for game in games:
        if game["result"] in wanted:
            if current["length"] == 0:
                current["from_round"] = game["round"]
            current["length"] += 1
            current["to_round"] = game["round"]
            if current["length"] > best["length"]:
                best = dict(current)
        else:
            current = {"length": 0, "from_round": None, "to_round": None}
    return best


def _current(games: Sequence[dict[str, Any]], wanted: set[str]) -> dict[str, Any]:
    streak = {"length": 0, "from_round": None, "to_round": None}
    for game in reversed(games):
        if game["result"] not in wanted:
            break
        if streak["length"] == 0:
            streak["to_round"] = game["round"]
        streak["from_round"] = game["round"]
        streak["length"] += 1
    return streak


def _outcome(match: ObservedMatch, rules: StandingsPointRules) -> tuple[int, int, str, str]:
    """Return points and results for both sides under the official rule."""
    return match_points(
        RankedResult(match.home, match.away, match.home_goals, match.away_goals, match.suspended),
        rules,
    )


def _games_by_club(matches: Iterable[ObservedMatch], rules: StandingsPointRules) -> dict[str, list[dict[str, Any]]]:
    games: dict[str, list[dict[str, Any]]] = {}
    for match in sorted(matches, key=lambda item: item.round_number):
        if not match.counted:
            continue
        home_points, away_points, home_result, away_result = _outcome(match, rules)
        games.setdefault(match.home, []).append({
            "round": match.round_number, "date": match.date, "opponent": match.away,
            "location": "home", "goals_for": match.home_goals, "goals_against": match.away_goals,
            "result": home_result, "points": home_points, "suspended": match.suspended,
        })
        games.setdefault(match.away, []).append({
            "round": match.round_number, "date": match.date, "opponent": match.home,
            "location": "away", "goals_for": match.away_goals, "goals_against": match.home_goals,
            "result": away_result, "points": away_points, "suspended": match.suspended,
        })
    return games


def _tier_metrics(games: Sequence[dict[str, Any]], opponents: set[str], rules: StandingsPointRules) -> dict[str, Any]:
    selected = [game for game in games if game["opponent"] in opponents]
    points = sum(game["points"] for game in selected)
    return {
        "played": len(selected),
        "points": points,
        "max_points": len(selected) * rules.win_points,
        "points_effectiveness": _ratio(points, len(selected) * rules.win_points),
        "goals_for": sum(game["goals_for"] for game in selected),
        "goals_against": sum(game["goals_against"] for game in selected),
    }


def _biggest(games: Sequence[dict[str, Any]], result: str) -> dict[str, Any] | None:
    """Return the widest win or heaviest defeat; draws are not extremes."""
    candidates = [game for game in games if not game["suspended"] and game["result"] == result]
    if not candidates:
        return None
    chosen = max(candidates, key=lambda game: (abs(game["goals_for"] - game["goals_against"]), game["goals_for"]))
    return {
        "round": chosen["round"],
        "opponent": chosen["opponent"],
        "location": chosen["location"],
        "goals_for": chosen["goals_for"],
        "goals_against": chosen["goals_against"],
        "margin": chosen["goals_for"] - chosen["goals_against"],
    }


def club_insights(
    matches: Iterable[ObservedMatch],
    *,
    rules: StandingsPointRules | None = None,
) -> dict[str, Any]:
    """Return descriptive per-club metrics plus league records.

    Opponent tiers use the competition ranking of this same dataset, including
    the Olympic tiebreak. They describe the schedule a club actually played; they
    are not a prediction or a strength claim about rivals.
    """
    rules = rules or load_point_rules()
    matches = [match for match in matches if match.counted]
    games = _games_by_club(matches, rules)
    rows = {club: _row(club) for club in games}

    for match in matches:
        home_points, away_points, home_result, away_result = _outcome(match, rules)
        _add(rows[match.home], "home", match.home_goals, match.away_goals, home_points, home_result, match.suspended)
        _add(rows[match.away], "away", match.away_goals, match.home_goals, away_points, away_result, match.suspended)

    results = [
        RankedResult(match.home, match.away, match.home_goals, match.away_goals, match.suspended)
        for match in matches
    ]
    records = build_records(results, rules, teams=list(rows))
    ordered_clubs = flatten(rank_groups(records, results, rules))
    order = [rows[club] for club in ordered_clubs]

    # A tier only makes sense when both ends are disjoint: with 16 clubs this is
    # the classic top five / bottom five, with a smaller league it shrinks.
    tier_size = min(5, len(order) // 2)
    top_five = {row["club"] for row in order[:tier_size]}
    bottom_five = {row["club"] for row in order[-tier_size:]} if tier_size else set()
    middle = {row["club"] for row in order} - top_five - bottom_five

    clubs: list[dict[str, Any]] = []
    for row in order:
        club_games = games[row["club"]]
        maximum = row["played"] * rules.win_points
        last_five = club_games[-5:]
        clubs.append({
            "club": row["club"],
            "played": row["played"],
            "won": row["won"],
            "drawn": row["drawn"],
            "lost": row["lost"],
            "points": row["points"],
            "max_points": maximum,
            "points_effectiveness": _ratio(row["points"], maximum),
            "win_rate": _ratio(row["won"], row["played"]),
            "goals_for": row["goals_for"],
            "goals_against": row["goals_against"],
            "goal_difference": row["goals_for"] - row["goals_against"],
            "goals_for_per_game": _per_game(row["goals_for"], row["played"]),
            "goals_against_per_game": _per_game(row["goals_against"], row["played"]),
            "goal_difference_per_game": _per_game(row["goals_for"] - row["goals_against"], row["played"]),
            "suspended_matches": row["suspended_matches"],
            "home": {
                **row["home"],
                "max_points": row["home"]["played"] * rules.win_points,
                "points_effectiveness": _ratio(row["home"]["points"], row["home"]["played"] * rules.win_points),
                "goals_for_per_game": _per_game(row["home"]["goals_for"], row["home"]["played"]),
                "goals_against_per_game": _per_game(row["home"]["goals_against"], row["home"]["played"]),
            },
            "away": {
                **row["away"],
                "max_points": row["away"]["played"] * rules.win_points,
                "points_effectiveness": _ratio(row["away"]["points"], row["away"]["played"] * rules.win_points),
                "goals_for_per_game": _per_game(row["away"]["goals_for"], row["away"]["played"]),
                "goals_against_per_game": _per_game(row["away"]["goals_against"], row["away"]["played"]),
            },
            "streaks": {
                "longest_win": _longest(club_games, {WIN}),
                "longest_unbeaten": _longest(club_games, {WIN, DRAW}),
                "longest_loss": _longest(club_games, {LOSS}),
                "current_unbeaten": _current(club_games, {WIN, DRAW}),
                "current_without_win": _current(club_games, {DRAW, LOSS}),
            },
            "form_last_5": {
                "sequence": ["G" if game["result"] == WIN else "E" if game["result"] == DRAW else "P" for game in last_five],
                "points": sum(game["points"] for game in last_five),
                "max_points": len(last_five) * rules.win_points,
            },
            "opponent_tiers": {
                "top_five": _tier_metrics(club_games, top_five, rules),
                "middle": _tier_metrics(club_games, middle, rules),
                "bottom_five": _tier_metrics(club_games, bottom_five, rules),
            },
            "biggest_win": _biggest(club_games, WIN),
            "biggest_loss": _biggest(club_games, LOSS),
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "matches_counted": len(matches),
        "suspended_matches": sum(1 for match in matches if match.suspended),
        "clubs": clubs,
        "records": _records(clubs),
    }


def _records(clubs: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """League-wide marks a reader can compare at a glance."""

    def streak_record(key: str, label: str, field: str) -> dict[str, Any] | None:
        candidates = [club for club in clubs if club["streaks"][field]["length"] > 0]
        if not candidates:
            return None
        club = max(candidates, key=lambda item: (item["streaks"][field]["length"], item["club"]))
        streak = club["streaks"][field]
        span = (
            f"Fechas {streak['from_round']} a {streak['to_round']}"
            if streak["from_round"] != streak["to_round"]
            else f"Fecha {streak['from_round']}"
        )
        return {"key": key, "label": label, "club": club["club"], "value": streak["length"], "unit": "partidos", "detail": span}

    records: list[dict[str, Any]] = [
        record
        for record in (
            streak_record("longest_unbeaten", "Mayor racha sin perder", "longest_unbeaten"),
            streak_record("longest_win", "Mayor racha de victorias", "longest_win"),
            streak_record("longest_loss", "Mayor racha de derrotas", "longest_loss"),
        )
        if record
    ]
    if clubs:
        attack = max(clubs, key=lambda club: (club["goals_for_per_game"], club["played"], club["club"]))
        defense = min(clubs, key=lambda club: (club["goals_against_per_game"], -club["played"], club["club"]))
        home = max(clubs, key=lambda club: (club["home"]["points_effectiveness"], club["home"]["played"], club["club"]))
        away = max(clubs, key=lambda club: (club["away"]["points_effectiveness"], club["away"]["played"], club["club"]))
        form = max(clubs, key=lambda club: (club["form_last_5"]["points"], club["club"]))
        records.extend([
            {"key": "best_attack", "label": "Mayor promedio de goles a favor", "club": attack["club"], "value": attack["goals_for_per_game"], "unit": "goles por partido", "detail": f"{attack['goals_for']} goles en {attack['played']} partidos"},
            {"key": "best_defense", "label": "Menor promedio de goles en contra", "club": defense["club"], "value": defense["goals_against_per_game"], "unit": "goles por partido", "detail": f"{defense['goals_against']} goles en contra en {defense['played']} partidos"},
            {"key": "best_home", "label": "Mejor efectividad como local", "club": home["club"], "value": home["home"]["points_effectiveness"], "unit": "de los puntos", "detail": f"{home['home']['points']} de {home['home']['max_points']} puntos como local"},
            {"key": "best_away", "label": "Mejor efectividad como visitante", "club": away["club"], "value": away["away"]["points_effectiveness"], "unit": "de los puntos", "detail": f"{away['away']['points']} de {away['away']['max_points']} puntos como visitante"},
            {"key": "best_form", "label": "Mejor presente en los últimos 5", "club": form["club"], "value": form["form_last_5"]["points"], "unit": "puntos", "detail": "".join(form["form_last_5"]["sequence"])},
        ])
    perfect = [
        club["club"]
        for club in clubs
        if club["opponent_tiers"]["bottom_five"]["played"] > 0
        and club["opponent_tiers"]["bottom_five"]["points"] == club["opponent_tiers"]["bottom_five"]["max_points"]
    ]
    if perfect:
        records.append({"key": "perfect_vs_bottom_five", "label": "Sin ceder puntos con los cinco últimos", "clubs": perfect, "value": len(perfect), "unit": "equipos", "detail": "Puntaje ideal contra el grupo inferior de la tabla"})
    return records


def annual_profile(
    club: str,
    competitions: Sequence[dict[str, Any]],
    *,
    rules: StandingsPointRules | None = None,
) -> dict[str, Any]:
    """Compare the same club across competitions without merging tables.

    Each competition keeps its own position, coverage, and campaign. The
    combined block is a labelled sum of different competitions, never a table.
    """
    rules = rules or load_point_rules()
    blocks = [
        {
            "key": item["key"],
            "label": item["label"],
            "position": item.get("position"),
            "played": item["played"],
            "won": item["won"],
            "drawn": item["drawn"],
            "lost": item["lost"],
            "points": item["points"],
            "max_points": item["played"] * rules.win_points,
            "points_effectiveness": _ratio(item["points"], item["played"] * rules.win_points),
            "goals_for": item["goals_for"],
            "goals_against": item["goals_against"],
            "goals_for_per_game": _per_game(item["goals_for"], item["played"]),
            "goals_against_per_game": _per_game(item["goals_against"], item["played"]),
        }
        for item in competitions
    ]
    totals = {key: sum(block[key] for block in blocks) for key in ("played", "won", "drawn", "lost", "points", "max_points", "goals_for", "goals_against")}
    return {
        "club": club,
        "competitions": blocks,
        "combined": {
            **totals,
            "label": "Suma de competencias distintas; no es una tabla de posiciones.",
            "points_effectiveness": _ratio(totals["points"], totals["max_points"]),
            "goals_for_per_game": _per_game(totals["goals_for"], totals["played"]),
            "goals_against_per_game": _per_game(totals["goals_against"], totals["played"]),
        },
    }


def roster_continuity(previous_names: Iterable[str], current_names: Iterable[str]) -> dict[str, Any]:
    """Estimate squad continuity from normalized planilla names.

    Player identities are materialized per stage, so continuity across
    competitions is a name match within the same club. It is an approximation:
    two people with the same normalized name would be counted as one, and a
    changed spelling would be counted as a new player.
    """
    previous = {name for name in (normalize_name(value) for value in previous_names) if name}
    current = {name for name in (normalize_name(value) for value in current_names) if name}
    shared = previous & current
    return {
        "previous_players": len(previous),
        "current_players": len(current),
        "shared_players": len(shared),
        "retained_share": _ratio(len(shared), len(current)),
        "note": "Coincidencia de nombres normalizados dentro del mismo club; no es un registro de pases.",
    }

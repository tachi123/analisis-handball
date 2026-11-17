"""Export a privacy-safe public tournament projection for the static report.

Derives standings, top scorers, and club aggregates from confirmed official
planillas, then projects them to a public-only shape (names and numbers, no
database IDs, raw payloads, notes, URLs, or operational paths). The public UI
reads the resulting JSON directly and never calls the private API.
"""
from __future__ import annotations

import json
import os
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from app.database import SessionLocal
from app.models import Match, ScheduledMatch, TournamentStage
from app.services.standings_service import compute_standings, load_point_rules
from app.services.statistics_service import club_statistics, player_statistics
from app.services.tournament_forecast_service import HistoricalResult, RemainingFixture, build_forecast
from app.services.tournament_insights_service import ObservedMatch, club_insights

STAGE_ID = int(os.getenv("PUBLIC_TOURNAMENT_STAGE_ID", "9"))

PUBLIC_COMPETITIONS: tuple[dict[str, Any], ...] = (
    {"key": "permanencia-2026", "stage_id": 9, "label": "Permanencia 2026", "competition": "Permanencia 2026", "zone": None},
    {"key": "apertura-zona-a-2026", "stage_id": 8, "label": "Apertura 2026 · Zona A", "competition": "Apertura 2026", "zone": "A"},
    {"key": "apertura-zona-b-2026", "stage_id": 11, "label": "Apertura 2026 · Zona B", "competition": "Apertura 2026", "zone": "B"},
)
FORECAST_KEY = "permanencia-2026"


def _standings_rows(standings: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "pos": row["pos"],
            "club": row["name"],
            "played": row["pj"],
            "won": row["wins"],
            "drawn": row["draws"],
            "lost": row["losses"],
            "penalized": row["cp"],
            "goals_for": row["gf"],
            "goals_against": row["ga"],
            "goal_difference": row["gd"],
            "points": row["pts"],
        }
        for row in standings["teams"]
    ]


def _scorer_rows(players: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": row["name"],
            "club": row["club"],
            "appearances": row["appearances"],
            "goals": row["goals"],
            "yellow": row["yellow"],
            "two_min": row["two_min"],
            "red": row["red"],
            "blue": row["blue"],
            "goals_per_game": row["goals_per_game"],
        }
        for row in players["rows"]
    ]


def _club_rows(clubs: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "club": row["club"],
            "appearances": row["appearances"],
            "goals": row["goals"],
            "yellow": row["yellow"],
            "two_min": row["two_min"],
            "red": row["red"],
            "blue": row["blue"],
            "players": row["distinct_players"],
        }
        for row in clubs["rows"]
    ]


def _club_name(registration: Any) -> str:
    return registration.competition_team.display_name


def _forecast_rows(db: Any, stage_id: int, standings: dict[str, Any]) -> dict[str, Any]:
    scheduled = (
        db.query(ScheduledMatch)
        .filter(ScheduledMatch.stage_id == stage_id)
        .order_by(ScheduledMatch.round_id, ScheduledMatch.match_number_label)
        .all()
    )
    history: list[HistoricalResult] = []
    fixtures: list[RemainingFixture] = []
    campaign: dict[str, list[dict[str, Any]]] = {row["name"]: [] for row in standings["teams"]}
    for item in scheduled:
        match = db.query(Match).filter(Match.scheduled_match_id == item.id).first()
        snapshot = next((row for row in (match.official_snapshots if match else []) if row.is_confirmed), None)
        home_score = snapshot.home_score if snapshot else (match.home_score if match else None)
        away_score = snapshot.away_score if snapshot else (match.away_score if match else None)
        home, away = _club_name(item.home_registration), _club_name(item.away_registration)
        if home_score is not None and away_score is not None:
            history.append(HistoricalResult(home, away, home_score, away_score, item.round.round_number, item.status == "suspended"))
            for club, opponent, location, goals_for, goals_against in (
                (home, away, "home", home_score, away_score),
                (away, home, "away", away_score, home_score),
            ):
                campaign[club].append(
                    {
                        "round": item.round.round_number,
                        "date": item.scheduled_date.isoformat() if item.scheduled_date else None,
                        "opponent": opponent,
                        "location": location,
                        "goals_for": goals_for,
                        "goals_against": goals_against,
                        "result": "win" if goals_for > goals_against else "draw" if goals_for == goals_against else "loss",
                    }
                )
        else:
            fixtures.append(RemainingFixture(item.round.round_number, item.scheduled_date.isoformat() if item.scheduled_date else None, home, away, item.status))
    forecast = build_forecast(standings["teams"], history, fixtures)
    for team in forecast["teams"]:
        team["campaign"] = sorted(campaign[team["club"]], key=lambda match: match["round"])
    return forecast


def _fixture_state(db: Any, scheduled: ScheduledMatch) -> tuple[Any, Any, int | None, int | None]:
    match = db.query(Match).filter(Match.scheduled_match_id == scheduled.id).first()
    snapshot = next((row for row in (match.official_snapshots if match else []) if row.is_confirmed), None)
    home_score = snapshot.home_score if snapshot else (match.home_score if match else None)
    away_score = snapshot.away_score if snapshot else (match.away_score if match else None)
    return match, snapshot, home_score, away_score


def _observed_matches(db: Any, stage_id: int) -> list[ObservedMatch]:
    scheduled = (
        db.query(ScheduledMatch)
        .filter(ScheduledMatch.stage_id == stage_id)
        .order_by(ScheduledMatch.round_id, ScheduledMatch.match_number_label)
        .all()
    )
    rows: list[ObservedMatch] = []
    for item in scheduled:
        _, _, home_score, away_score = _fixture_state(db, item)
        if home_score is None or away_score is None:
            continue
        rows.append(
            ObservedMatch(
                round_number=item.round.round_number,
                date=item.scheduled_date.isoformat() if item.scheduled_date else None,
                home=_club_name(item.home_registration),
                away=_club_name(item.away_registration),
                home_goals=home_score,
                away_goals=away_score,
                status=item.status,
            )
        )
    return rows


def _rounds_rows(db: Any, stage_id: int) -> list[dict[str, Any]]:
    scheduled = (
        db.query(ScheduledMatch)
        .filter(ScheduledMatch.stage_id == stage_id)
        .order_by(ScheduledMatch.round_id, ScheduledMatch.match_number_label)
        .all()
    )
    rounds: dict[int, dict[str, Any]] = {}
    for item in scheduled:
        _, snapshot, home_score, away_score = _fixture_state(db, item)
        if item.status == "suspended":
            coverage = "suspended"
        elif item.status == "cancelled":
            coverage = "cancelled"
        elif snapshot is not None:
            coverage = "planilla"
        elif home_score is not None and away_score is not None:
            coverage = "reported"
        else:
            coverage = "pending"
        round_row = rounds.setdefault(
            item.round.round_number,
            {"round": item.round.round_number, "date": None, "matches": []},
        )
        match_date = item.scheduled_date.isoformat() if item.scheduled_date else None
        if match_date and (round_row["date"] is None or match_date < round_row["date"]):
            round_row["date"] = match_date
        round_row["matches"].append(
            {
                "home": _club_name(item.home_registration),
                "away": _club_name(item.away_registration),
                "home_goals": home_score,
                "away_goals": away_score,
                "coverage": coverage,
            }
        )
    return sorted(rounds.values(), key=lambda row: row["round"])


def _coverage_rows(db: Any, stage_id: int) -> dict[str, Any]:
    stage = db.get(TournamentStage, stage_id)
    if stage is None:
        raise ValueError(f"Stage {stage_id} not found")
    total = len(stage.scheduled_matches)
    counted = confirmed = reported = suspended = 0
    rounds_with_results: set[int] = set()
    for item in stage.scheduled_matches:
        _, snapshot, home_score, away_score = _fixture_state(db, item)
        has_result = home_score is not None and away_score is not None
        if item.status == "suspended":
            suspended += 1
        if snapshot is not None:
            confirmed += 1
        if has_result:
            counted += 1
            rounds_with_results.add(item.round_id)
            if snapshot is None and item.status != "suspended":
                reported += 1
    pending = total - counted
    label = f"{counted} de {total} partidos con resultado · {confirmed} planillas confirmadas"
    if suspended:
        label += f" · {suspended} suspendido{'s' if suspended != 1 else ''}"
    label += " · no reemplaza la tabla oficial de FEMEBAL."
    return {
        "matches_total": total,
        "matches_counted": counted,
        "planillas_confirmed": confirmed,
        "reported_only": reported,
        "suspended": suspended,
        "pending": pending,
        "rounds_played": len(rounds_with_results),
        "rounds_total": len({item.round_id for item in stage.scheduled_matches}),
        "status": "complete" if pending == 0 else "partial",
        "label": label,
    }


def _insight_rows(insights: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for club in insights["clubs"]:
        rows.append(
            {
                "club": club["club"],
                "played": club["played"],
                "won": club["won"],
                "drawn": club["drawn"],
                "lost": club["lost"],
                "points": club["points"],
                "max_points": club["max_points"],
                "points_effectiveness": club["points_effectiveness"],
                "win_rate": club["win_rate"],
                "goals_for": club["goals_for"],
                "goals_against": club["goals_against"],
                "goal_difference": club["goal_difference"],
                "goals_for_per_game": club["goals_for_per_game"],
                "goals_against_per_game": club["goals_against_per_game"],
                "home": {
                    key: club["home"][key]
                    for key in ("played", "points", "max_points", "points_effectiveness", "goals_for_per_game", "goals_against_per_game")
                },
                "away": {
                    key: club["away"][key]
                    for key in ("played", "points", "max_points", "points_effectiveness", "goals_for_per_game", "goals_against_per_game")
                },
                "streaks": {
                    key: club["streaks"][key]
                    for key in ("longest_win", "longest_unbeaten", "longest_loss", "current_unbeaten")
                },
                "form_last_5": club["form_last_5"],
                "opponent_tiers": {
                    tier: {
                        key: club["opponent_tiers"][tier][key]
                        for key in ("played", "points", "max_points", "points_effectiveness")
                    }
                    for tier in ("top_five", "middle", "bottom_five")
                },
                "biggest_win": club["biggest_win"],
                "biggest_loss": club["biggest_loss"],
            }
        )
    return rows


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(character for character in decomposed.casefold() if character.isalnum())


def _is_sapa(value: str) -> bool:
    return _normalize(value) == "sapa"


def build_competition(entry: dict[str, Any]) -> dict[str, Any]:
    stage_id = int(entry["stage_id"])
    with SessionLocal() as db:
        stage = db.get(TournamentStage, stage_id)
        if stage is None:
            raise ValueError(f"Stage {stage_id} not found")
        standings = compute_standings(db, stage_id)
        players = player_statistics(db, stage_id)
        clubs = club_statistics(db, stage_id)
        coverage = _coverage_rows(db, stage_id)
        rounds = _rounds_rows(db, stage_id)
        insights = club_insights(_observed_matches(db, stage_id))
        season = stage.season.year
        tournament = stage.name

    rules = load_point_rules()
    return {
        "schema_version": "tournament-v3",
        "public_key": entry["key"],
        "tournament": tournament,
        "competition": entry["competition"],
        "zone": entry["zone"],
        "season": season,
        "updated_at": date.today().isoformat(),
        "coverage": coverage,
        "points_rule": {
            "win": rules.win_points,
            "draw": rules.draw_points,
            "loss": rules.loss_points,
            "suspended_win": rules.suspended_winner_points,
            "suspended_loss": rules.suspended_loser_points,
        },
        "standings": _standings_rows(standings),
        "scorers": _scorer_rows(players),
        "clubs": _club_rows(clubs),
        "rounds": rounds,
        "insights": {
            "matches_counted": insights["matches_counted"],
            "suspended_matches": insights["suspended_matches"],
            "clubs": _insight_rows(insights),
            "records": insights["records"],
        },
    }


def build_forecast_document(stage_id: int = 9, key: str = FORECAST_KEY) -> dict[str, Any]:
    with SessionLocal() as db:
        stage = db.get(TournamentStage, stage_id)
        if stage is None:
            raise ValueError(f"Stage {stage_id} not found")
        standings = compute_standings(db, stage_id)
        forecast = _forecast_rows(db, stage_id, standings)
        coverage = _coverage_rows(db, stage_id)
        season = stage.season.year
        tournament = stage.name

    sapa_fixture = next(
        (fixture for fixture in forecast["fixtures"] if _is_sapa(fixture["home"]) or _is_sapa(fixture["away"])),
        None,
    )
    rival = None
    if sapa_fixture:
        rival = sapa_fixture["away"] if _is_sapa(sapa_fixture["home"]) else sapa_fixture["home"]

    return {
        "schema_version": "forecast-v1",
        "public_key": key,
        "competition": "Permanencia 2026",
        "tournament": tournament,
        "season": season,
        "updated_at": date.today().isoformat(),
        "coverage": coverage,
        "simulations": forecast["simulations"],
        "methodology": forecast["methodology"],
        "points_rule": forecast["points_rule"],
        "teams": forecast["teams"],
        "fixtures": forecast["fixtures"],
        "rival_profile": {
            "club": rival,
            "competitions": [
                {"key": entry["key"], "label": entry["label"]}
                for entry in PUBLIC_COMPETITIONS
            ],
        },
    }


def _sapa_summary(document: dict[str, Any]) -> dict[str, Any] | None:
    row = next((item for item in document["standings"] if _is_sapa(item["club"])), None)
    if row is None:
        return None
    return {"position": row["pos"], "points": row["points"], "played": row["played"]}


def _next_sapa_match(document: dict[str, Any]) -> dict[str, Any] | None:
    for round_row in document["rounds"]:
        for match in round_row["matches"]:
            if match["coverage"] != "pending":
                continue
            if _is_sapa(match["home"]):
                return {"round": round_row["round"], "date": round_row["date"], "opponent": match["away"], "location": "home"}
            if _is_sapa(match["away"]):
                return {"round": round_row["round"], "date": round_row["date"], "opponent": match["home"], "location": "away"}
    return None


def _catalog_entry(document: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    has_forecast = document["public_key"] == FORECAST_KEY
    return {
        "key": document["public_key"],
        "label": entry["label"],
        "competition": document["competition"],
        "zone": document["zone"],
        "season": document["season"],
        "status": "in_progress" if document["coverage"]["pending"] else "finished",
        "coverage": document["coverage"],
        "updated_at": document["updated_at"],
        "file": f"tournament_{document['public_key']}.json",
        "forecast_file": f"forecast_{document['public_key']}.json" if has_forecast else None,
        "summary": {"sapa": _sapa_summary(document)},
        "next_match": _next_sapa_match(document),
    }


def build_public_competitions() -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    """Build the 2026 catalog, every tournament artifact, and the forecast.

    The catalog is metadata only; each card still opens a static artifact that
    the browser decodes with its own allowlist.
    """
    documents = {entry["key"]: build_competition(entry) for entry in PUBLIC_COMPETITIONS}
    forecast = build_forecast_document()
    catalog = {
        "schema_version": "tournaments-v1",
        "generated_at": date.today().isoformat(),
        "tournaments": [
            _catalog_entry(documents[entry["key"]], entry)
            for entry in PUBLIC_COMPETITIONS
        ],
    }
    return catalog, documents, forecast


def build_public_tournament(stage_id: int | None = None) -> dict[str, Any]:
    stage_id = stage_id or STAGE_ID
    with SessionLocal() as db:
        stage = db.get(TournamentStage, stage_id)
        if stage is None:
            raise ValueError(f"Stage {stage_id} not found")
        standings = compute_standings(db, stage_id)
        players = player_statistics(db, stage_id)
        clubs = club_statistics(db, stage_id)
        forecast = _forecast_rows(db, stage_id, standings)
        season = stage.season.year
        rounds_total = len({match.round_id for match in stage.scheduled_matches})
        pending = sum(
            1
            for match in stage.scheduled_matches
            if match.status not in {"suspended", "cancelled"}
            and not _has_result(db, match)
        )

    rounds_played = max((row["pj"] for row in standings["teams"]), default=0)
    return {
        "schema_version": "tournament-v2",
        "tournament": standings["stage_name"],
        "season": season,
        "updated_at": date.today().isoformat(),
        "coverage": {
            "rounds_played": rounds_played,
            "rounds_total": rounds_total,
            "status": "complete" if pending == 0 else "partial",
            "label": f"Cubre las {rounds_played} fechas con resultados cargados; no reemplaza la tabla oficial de FEMEBAL.",
        },
        "standings": _standings_rows(standings),
        "scorers": _scorer_rows(players),
        "clubs": _club_rows(clubs),
        "forecast": forecast,
    }


def _has_result(db: Any, scheduled: ScheduledMatch) -> bool:
    match = db.query(Match).filter(Match.scheduled_match_id == scheduled.id).first()
    if match is None:
        return False
    snapshot = next((row for row in match.official_snapshots if row.is_confirmed), None)
    home_score = snapshot.home_score if snapshot else match.home_score
    away_score = snapshot.away_score if snapshot else match.away_score
    return home_score is not None and away_score is not None


def main() -> None:
    output = Path(os.getenv("PUBLIC_REPORT_OUTPUT", "reports/public/tournament.json"))
    document = build_public_tournament()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(document['standings'])} standings, {len(document['scorers'])} scorers, {len(document['clubs'])} clubs -> {output}")


if __name__ == "__main__":
    main()

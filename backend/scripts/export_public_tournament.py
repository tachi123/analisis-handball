"""Export a privacy-safe public tournament projection for the static report.

Derives standings, top scorers, and club aggregates from confirmed official
planillas, then projects them to a public-only shape (names and numbers, no
database IDs, raw payloads, notes, URLs, or operational paths). The public UI
reads the resulting JSON directly and never calls the private API.
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from app.database import SessionLocal
from app.models import Match, ScheduledMatch
from app.services.standings_service import compute_standings
from app.services.statistics_service import club_statistics, player_statistics
from app.services.tournament_forecast_service import HistoricalResult, RemainingFixture, build_forecast

STAGE_ID = 9


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
    for item in scheduled:
        match = db.query(Match).filter(Match.scheduled_match_id == item.id).first()
        snapshot = next((row for row in (match.official_snapshots if match else []) if row.is_confirmed), None)
        home_score = snapshot.home_score if snapshot else (match.home_score if match else None)
        away_score = snapshot.away_score if snapshot else (match.away_score if match else None)
        home, away = _club_name(item.home_registration), _club_name(item.away_registration)
        if home_score is not None and away_score is not None:
            history.append(HistoricalResult(home, away, home_score, away_score, item.round.round_number))
        else:
            fixtures.append(RemainingFixture(item.round.round_number, item.scheduled_date.isoformat() if item.scheduled_date else None, home, away))
    return build_forecast(standings["teams"], history, fixtures)


def build_public_tournament() -> dict[str, Any]:
    with SessionLocal() as db:
        standings = compute_standings(db, STAGE_ID)
        players = player_statistics(db, STAGE_ID)
        clubs = club_statistics(db, STAGE_ID)
        forecast = _forecast_rows(db, STAGE_ID, standings)

    rounds_played = max((row["pj"] for row in standings["teams"]), default=0)
    return {
        "schema_version": "tournament-v2",
        "tournament": standings["stage_name"],
        "season": 2026,
        "updated_at": date.today().isoformat(),
        "coverage": {
            "rounds_played": rounds_played,
            "rounds_total": 15,
            "status": "partial",
            "label": f"Cubre las {rounds_played} fechas con resultados cargados; no reemplaza la tabla oficial de FEMEBAL.",
        },
        "standings": _standings_rows(standings),
        "scorers": _scorer_rows(players),
        "clubs": _club_rows(clubs),
        "forecast": forecast,
    }


def main() -> None:
    output = Path(os.getenv("PUBLIC_REPORT_OUTPUT", "reports/public/tournament.json"))
    document = build_public_tournament()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(document['standings'])} standings, {len(document['scorers'])} scorers, {len(document['clubs'])} clubs -> {output}")


if __name__ == "__main__":
    main()

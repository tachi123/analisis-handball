"""Standings derivation service for FEMEBAL tournaments.

Pure, deterministic computation of league tables from match results.
Points rules are loaded from a versioned JSON config; the numbers are NOT hardcoded.
Ranking uses the handball Olympic tiebreak via :mod:`competition_ranking`.
"""

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models import Match, ScheduledMatch, TeamRegistration, TournamentStage
from app.services.competition_ranking import RankedResult, build_records, rank_groups


# ---------------------------------------------------------------------------
# Config path -----------------------------------------------------------------
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "points_rules.json"


def _load_rules(path: Path | None = None) -> dict[str, Any]:
    """Load points rules from the versioned JSON config."""
    rules_path = path or _CONFIG_PATH
    text = rules_path.read_text(encoding="utf-8")
    import json
    return json.loads(text)


# ---------------------------------------------------------------------------
# Public types -----------------------------------------------------------------
# ---------------------------------------------------------------------------


class StandingsPointRules:
    """Versioned points rule container — loaded from config at runtime."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.schema_version: str = data.get("schema_version", "unknown")
        self.win_points: int = int(data["win_points"])
        self.draw_points: int = int(data["draw_points"])
        self.loss_points: int = int(data["loss_points"])
        suspended_cfg = data.get("suspended", {})
        self.suspended_winner_points: int = int(
            suspended_cfg.get("winner_points", self.win_points)
        )
        self.suspended_loser_points: int = int(
            suspended_cfg.get("loser_points", self.loss_points)
        )


def load_point_rules() -> StandingsPointRules:
    """Return the versioned points rule without requiring a database session.

    The rule is competition-level configuration, not stage data, so callers that
    derive results from an already-loaded fixture (for example the forecast
    simulator) can reuse the exact same numbers as the standings table.
    """
    data = _load_rules()
    return StandingsPointRules(data)


def get_point_rules(db: Session, stage_id: int) -> StandingsPointRules:
    """Return a :class:`StandingsPointRules` instance loaded from config."""
    return load_point_rules()


# ---------------------------------------------------------------------------
# Standings row -----------------------------------------------------------------
# ---------------------------------------------------------------------------


class _TeamRow:
    """Mutable row for one team during standings computation."""

    __slots__ = (
        "team_id", "name", "pj", "wins", "draws", "losses", "cp", "gf", "ga", "gd", "pts", "coverage", "_pos"
    )

    def __init__(self, team_id: int, name: str) -> None:
        self.team_id = team_id
        self.name = name
        self.pj = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.cp = 0
        self.gf = 0
        self.ga = 0
        self.gd = 0
        self.pts = 0
        self.coverage = "unknown"
        self._pos = 0

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "pos": self._pos,
            "team_id": self.team_id,
            "name": self.name,
            "pj": self.pj,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "cp": self.cp,
            "gf": self.gf,
            "ga": self.ga,
            "gd": self.gd,
            "pts": self.pts,
            "coverage": self.coverage,
        }


# ---------------------------------------------------------------------------
# Core derivation -------------------------------------------------------------
# ---------------------------------------------------------------------------


def compute_standings(db: Session, stage_id: int) -> dict[str, Any]:
    """Compute tournament standings for *stage_id*.

    Only matches that have a result (both ``home_score`` and ``away_score`` are
    not ``None``) are counted.  Matches without a score (e.g. future fixtures or
    suspended matches without a recorded result) are skipped.

    Points rule:
      - Win = 3 points, Draw = 2 points, Loss (played) = 1 point.
      - Suspended match (``ScheduledMatch.status == "suspended"``):
          winner = 3 points, loser = 0 points.

    The rule numbers are read from the versioned config via
    :func:`get_point_rules`; they are NOT hardcoded in logic.

    Tiebreak: handball Olympic tiebreak. Clubs level on points are ranked by the
    matches played between them (points, goal difference, goals for); if that
    still ties, by overall goal difference and overall goals for. A residual
    exact tie keeps a stable order and is visible in the coverage note.

    Returns a dict with the stable JSON shape described in the deliverables.
    """

    rules = get_point_rules(db, stage_id)

    stage = db.get(TournamentStage, stage_id)
    if not stage:
        raise ValueError(f"Stage {stage_id} not found")

    # Map: registration_id -> row. We key by registration_id because a
    # competition_team may have multiple registrations, but for this tournament
    # each team registers once.
    row_by_reg: dict[int, _TeamRow] = {}
    for competition_team in stage.competition_teams:
        registration = (
            db.query(TeamRegistration)
            .filter(TeamRegistration.competition_team_id == competition_team.id)
            .first()
        )
        if registration:
            row_by_reg[registration.id] = _TeamRow(registration.id, competition_team.display_name)

    matches = (
        db.query(Match, ScheduledMatch)
        .join(ScheduledMatch, Match.scheduled_match_id == ScheduledMatch.id)
        .options(joinedload(Match.official_snapshots))
        .filter(ScheduledMatch.stage_id == stage_id)
        .all()
    )

    # Count the full scheduled slate (includes fixtures that still lack a result).
    total_fixtures_per_reg: dict[int, int] = {reg_id: 0 for reg_id in row_by_reg}
    for scheduled in stage.scheduled_matches:
        if scheduled.home_registration_id in total_fixtures_per_reg:
            total_fixtures_per_reg[scheduled.home_registration_id] += 1
        if scheduled.away_registration_id in total_fixtures_per_reg:
            total_fixtures_per_reg[scheduled.away_registration_id] += 1

    results: list[RankedResult[int]] = []
    resolved_fixtures: set[int] = set()
    for match, scheduled in matches:
        home_reg_id = scheduled.home_registration_id
        away_reg_id = scheduled.away_registration_id
        row_by_reg.setdefault(home_reg_id, _TeamRow(home_reg_id, ""))
        row_by_reg.setdefault(away_reg_id, _TeamRow(away_reg_id, ""))

        # The confirmed planilla snapshot is the authoritative official result;
        # a legacy Match may still carry a stale 0:0 default.
        snapshot = next((s for s in match.official_snapshots if s.is_confirmed), None)
        if snapshot is not None:
            home_score, away_score = snapshot.home_score, snapshot.away_score
        else:
            home_score, away_score = match.home_score, match.away_score

        if home_score is None or away_score is None:
            continue

        resolved_fixtures.add(scheduled.id)
        results.append(
            RankedResult(
                home=home_reg_id,
                away=away_reg_id,
                home_goals=home_score,
                away_goals=away_score,
                suspended=scheduled.status == "suspended",
            )
        )

    records = build_records(results, rules, teams=list(row_by_reg))
    groups = rank_groups(records, results, rules)

    team_list: list[dict[str, Any]] = []
    position = 0
    for group in groups:
        for reg_id in group:
            position += 1
            row = row_by_reg[reg_id]
            record = records[reg_id]
            row.pj = record.played
            row.wins = record.won
            row.draws = record.drawn
            row.losses = record.lost
            row.cp = record.penalized
            row.gf = record.goals_for
            row.ga = record.goals_against
            row.gd = record.goal_difference
            row.pts = record.points
            row._pos = position  # type: ignore[attr-assign]
            row.coverage = _coverage_label(
                total_fixtures_per_reg.get(reg_id, 0),
                record.played,
            )
            team_list.append(row.summary)

    # ------------------------------------------------------------------
    # Coverage note
    # ------------------------------------------------------------------
    scheduled_without_result = sum(
        1 for scheduled in stage.scheduled_matches if scheduled.id not in resolved_fixtures
    )

    if scheduled_without_result > 0:
        note = f"{scheduled_without_result} fixture(s) without reported results."
    elif stage.scheduled_matches:
        note = "All fixtures have reported results."
    else:
        note = "Cobertura parcial: algunas fechas aún sin resultados."

    return {
        "schema_version": rules.schema_version,
        "stage_id": stage_id,
        "stage_name": stage.name,
        "teams": team_list,
        "note": note,
    }


def _coverage_label(total: int, reported: int) -> str:
    """Return a coverage status label.

    - "confirmed"  — all fixtures have a reported result
    - "partial"    — some fixtures have results, some don't
    - "none"       — no fixtures have results
    """
    if total == 0:
        return "none"
    if reported >= total:
        return "confirmed"
    return "partial"

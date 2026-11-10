"""Standings derivation service for FEMEBAL tournaments.

Pure, deterministic computation of league tables from match results.
Points rules are loaded from a versioned JSON config; the numbers are NOT hardcoded.
"""

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models import Match, ScheduledMatch, Team, TournamentStage, TeamRegistration


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


def get_point_rules(db: Session, stage_id: int) -> StandingsPointRules:
    """Return a :class:`StandingsPointRules` instance loaded from config."""
    data = _load_rules()
    return StandingsPointRules(data)


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
            "pos": self._pos,  # set later
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

    Tiebreak: points DESC, then goal difference DESC, then goals-for DESC.

    Returns a dict with the stable JSON shape described in the deliverables.
    """

    rules = get_point_rules(db, stage_id)

    # ------------------------------------------------------------------
    # 1. Resolve competition teams for the stage and map team_id -> row
    # ------------------------------------------------------------------
    stage = db.get(TournamentStage, stage_id)
    if not stage:
        raise ValueError(f"Stage {stage_id} not found")

    competition_teams = stage.competition_teams

    # Map: registration_id -> _TeamRow
    # We key by registration_id because a competition_team may have multiple
    # registrations, but for this tournament each team registers once.
    row_by_reg: dict[int, _TeamRow] = {}

    for ct in competition_teams:
        reg = (
            db.query(TeamRegistration)
            .filter(TeamRegistration.competition_team_id == ct.id)
            .first()
        )
        if reg:
            row_by_reg[reg.id] = _TeamRow(reg.id, ct.display_name)

    # ------------------------------------------------------------------
    # 2. Collect matches that have a result and belong to the stage
    # ------------------------------------------------------------------
    matches = (
        db.query(Match, ScheduledMatch)
        .join(ScheduledMatch, Match.scheduled_match_id == ScheduledMatch.id)
        .options(joinedload(Match.official_snapshots))
        .filter(ScheduledMatch.stage_id == stage_id)
        .all()
    )

    # Track fixture coverage counts per registration_id
    total_fixtures_per_reg: dict[int, int] = {reg_id: 0 for reg_id in row_by_reg}
    reported_fixtures_per_reg: dict[int, int] = {reg_id: 0 for reg_id in row_by_reg}

    # Count the full scheduled slate (includes fixtures that still lack a result).
    for sm in stage.scheduled_matches:
        if sm.home_registration_id in total_fixtures_per_reg:
            total_fixtures_per_reg[sm.home_registration_id] += 1
        if sm.away_registration_id in total_fixtures_per_reg:
            total_fixtures_per_reg[sm.away_registration_id] += 1

    for match, scheduled in matches:
        # Determine registration ids for home/away
        home_reg = (
            db.query(TeamRegistration.id)
            .filter(TeamRegistration.id == scheduled.home_registration_id)
            .first()
        )
        away_reg = (
            db.query(TeamRegistration.id)
            .filter(TeamRegistration.id == scheduled.away_registration_id)
            .first()
        )

        if not home_reg or not away_reg:
            continue
        home_reg_id = home_reg[0]
        away_reg_id = away_reg[0]

        # Initialise rows if not already done
        if home_reg_id not in row_by_reg:
            row_by_reg[home_reg_id] = _TeamRow(home_reg_id, "")
        if away_reg_id not in row_by_reg:
            row_by_reg[away_reg_id] = _TeamRow(away_reg_id, "")

        # The confirmed planilla snapshot is the authoritative official result;
        # a legacy Match may still carry a stale 0:0 default.
        snapshot = next((s for s in match.official_snapshots if s.is_confirmed), None)
        if snapshot is not None:
            home_score, away_score = snapshot.home_score, snapshot.away_score
        else:
            home_score, away_score = match.home_score, match.away_score

        # Only count matches that HAVE a result (both scores not None)
        if home_score is None or away_score is None:
            continue

        # Count as reported fixture
        reported_fixtures_per_reg[home_reg_id] += 1
        reported_fixtures_per_reg[away_reg_id] += 1

        home = row_by_reg[home_reg_id]
        away = row_by_reg[away_reg_id]

        # Determine if this is a suspended fixture
        is_suspended = scheduled.status == "suspended"

        # ---- Apply points rule ----
        if is_suspended:
            # Suspended match: winner = 3 pts (counted as a win), loser = 0 pts
            # and counted as a penalized match (CP), not a normal loss.
            if home_score > away_score:
                # Home wins
                home.pts += rules.suspended_winner_points
                away.pts += rules.suspended_loser_points
                home.wins += 1
                away.cp += 1
            elif away_score > home_score:
                # Away wins
                away.pts += rules.suspended_winner_points
                home.pts += rules.suspended_loser_points
                away.wins += 1
                home.cp += 1
            else:
                # Tied suspended match — treat both as penalized (rare)
                home.pts += rules.suspended_loser_points
                away.pts += rules.suspended_loser_points
                home.cp += 1
                away.cp += 1
        else:
            # Played match: standard rule (loaded from config)
            if home_score > away_score:
                home.pts += rules.win_points
                away.pts += rules.loss_points
                home.wins += 1
                away.losses += 1
            elif away_score > home_score:
                away.pts += rules.win_points
                home.pts += rules.loss_points
                away.wins += 1
                home.losses += 1
            else:
                # Draw
                home.pts += rules.draw_points
                away.pts += rules.draw_points
                home.draws += 1
                away.draws += 1

        # ---- Update game stats ----
        home.pj += 1
        away.pj += 1
        home.gf += home_score
        home.ga += away_score
        away.gf += away_score
        away.ga += home_score
        home.gd = home.gf - home.ga
        away.gd = away.gf - away.ga

    # ------------------------------------------------------------------
    # 3. Rank teams (tiebreak: points DESC, goal difference DESC, goals-for DESC)
    # ------------------------------------------------------------------
    sorted_rows = sorted(
        row_by_reg.values(),
        key=lambda r: (-r.pts, -r.gd, -r.gf),
    )

    for idx, row in enumerate(sorted_rows, start=1):
        row._pos = idx  # type: ignore[attr-assign]
        row.coverage = _coverage_label(
            total_fixtures_per_reg.get(row.team_id, 0),
            reported_fixtures_per_reg.get(row.team_id, 0),
        )

    # Build ordered list by position
    team_list: list[dict[str, Any]] = []
    for idx, row in enumerate(sorted_rows, start=1):
        team_list.append(row.summary)

    # ------------------------------------------------------------------
    # 4. Build note about coverage
    # ------------------------------------------------------------------
    # Check if any scheduled matches lack results (fechas 14-15 typically)
    scheduled_without_result = 0
    for sm in stage.scheduled_matches:
        # Check if there's a match record with scores
        m = db.query(Match).filter(Match.scheduled_match_id == sm.id).first()
        if m is None or m.home_score is None or m.away_score is None:
            # Check if it's suspended (those have a result by definition)
            if sm.status != "suspended":
                scheduled_without_result += 1

    note = ""
    if scheduled_without_result > 0:
        note = f"{scheduled_without_result} fixture(s) without reported results (fechas 14‑15)."
    elif all(
        db.query(Match).filter(Match.scheduled_match_id == sm.id).first() is not None
        and db.query(Match).filter(Match.scheduled_match_id == sm.id).first().home_score is not None
        for sm in stage.scheduled_matches
    ):
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
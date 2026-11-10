"""On-the-fly aggregated statistics service for FEMEBAL tournaments.

Derives per-player and per-club statistics from confirmed official snapshots
(``OfficialSnapshot.is_confirmed == True``) for a given stage.  No data is
persisted; all computation happens at query time.
"""

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models import (
    CompetitionTeam,
    Match,
    OfficialSnapshot,
    OfficialSnapshotPlayer,
    Player,
    ScheduledMatch,
    TeamRegistration,
    TournamentStage,
)


# ---------------------------------------------------------------------------
# Stable JSON-shape helpers
# ---------------------------------------------------------------------------

def _player_key(row: OfficialSnapshotPlayer) -> Tuple[int | None, str]:
    """Group key for a player: (player_id, name).

    Falls back to ``name`` when ``player_id`` is ``None`` so that
    unnamed rows are still deduped.
    """
    return (row.player_id, row.name)


def _club_from_registration(
    db: Session,
    snapshot: OfficialSnapshot,
    side: str,
) -> str:
    """Derive the club name for a player on *side* of *snapshot*.

    The club is the `` CompetitionTeam.display_name `` of the
    `` TeamRegistration `` for that side (`` home_registration `` if
    `` side == "home"``, else `` away_registration ``).
    """
    # Find the scheduled match for this snapshot
    match = db.get(Match, snapshot.match_id)
    if match is None or match.scheduled_match is None:
        return ""

    sm: ScheduledMatch = match.scheduled_match

    # Pick the registration based on side
    reg_id = (
        sm.home_registration_id
        if side == "home"
        else sm.away_registration_id
    )

    reg = db.get(TeamRegistration, reg_id)
    if reg is None or reg.competition_team is None:
        return ""

    return reg.competition_team.display_name


# ---------------------------------------------------------------------------
# Player statistics
# ---------------------------------------------------------------------------

def player_statistics(db: Session, stage_id: int) -> dict[str, Any]:
    """Return per-player aggregated statistics for *stage_id*.

    Only ``OfficialSnapshot.is_confirmed == True`` snapshots for fixtures
    in *stage_id* are counted (suspended matches are excluded).

    Returns a dict matching the stable JSON shape:

    .. code-block:: json

        {
          "schema_version": "femebal-permanencia-statistics-v1",
          "stage_id": 9,
          "stage_name": "...",
          "rows": [
            {
              "name": "Player name",
              "club": "Club name",
              "appearances": 5,
              "goals": 12,
              "yellow": 2,
              "two_min": 1,
              "red": 0,
              "blue": 0,
              "goals_per_game": 2.4
            }
          ],
          "note": "Only confirmed planillas are counted."
        }
    """

    stage = db.get(TournamentStage, stage_id)
    if not stage:
        raise ValueError(f"Stage {stage_id} not found")

    stage_name = stage.name

    # ------------------------------------------------------------------
    # 1. Load all confirmed snapshots for matches belonging to the stage
    # ------------------------------------------------------------------
    snapshots = (
        db.query(OfficialSnapshot)
        .join(Match, OfficialSnapshot.match_id == Match.id)
        .join(ScheduledMatch, Match.scheduled_match_id == ScheduledMatch.id)
        .filter(
            OfficialSnapshot.is_confirmed == True,
            ScheduledMatch.stage_id == stage_id,
        )
        .options(
            joinedload(OfficialSnapshot.players),
        )
        .all()
    )

    # ------------------------------------------------------------------
    # 2. Accumulate per-player stats (key = player_id / name)
    # ------------------------------------------------------------------
    # player_acc[player_key] -> dict with running totals
    player_acc: Dict[Tuple[int | None, str], dict[str, Any]] = {}

    for snap in snapshots:
        for player in snap.players:
            key = _player_key(player)

            if key not in player_acc:
                player_acc[key] = {
                    "appearances": 0,
                    "goals": 0,
                    "yellow": 0,
                    "two_min": 0,
                    "red": 0,
                    "blue": 0,
                    "name": player.name,
                    "club": _club_from_registration(db, snap, player.side),
                }

            acc = player_acc[key]
            acc["appearances"] += 1
            acc["goals"] += player.official_goals
            acc["yellow"] += player.official_yellow
            acc["two_min"] += player.official_2min
            acc["red"] += player.official_red
            acc["blue"] += player.official_blue

    # ------------------------------------------------------------------
    # 3. Compute goals-per-game and build rows
    # ------------------------------------------------------------------
    rows: List[dict[str, Any]] = []
    for (player_id, name), acc in player_acc.items():
        appearances = acc["appearances"]
        goals = acc["goals"]
        goals_per_game = round(goals / appearances, 2) if appearances > 0 else 0.0

        rows.append(
            {
                "name": name,
                "club": acc["club"],
                "appearances": appearances,
                "goals": goals,
                "yellow": acc["yellow"],
                "two_min": acc["two_min"],
                "red": acc["red"],
                "blue": acc["blue"],
                "goals_per_game": goals_per_game,
            }
        )

    # Sort by goals DESC, then appearances DESC
    rows.sort(key=lambda r: (-r["goals"], -r["appearances"]))

    return {
        "schema_version": "femebal-permanencia-statistics-v1",
        "stage_id": stage_id,
        "stage_name": stage_name,
        "rows": rows,
        "note": "Only confirmed planillas are counted.",
    }


# ---------------------------------------------------------------------------
# Club statistics
# ---------------------------------------------------------------------------

def club_statistics(db: Session, stage_id: int) -> dict[str, Any]:
    """Return per-club aggregated statistics for *stage_id*.

    Only ``OfficialSnapshot.is_confirmed == True`` snapshots for fixtures
    in *stage_id* are counted (suspended matches are excluded).

    Returns a dict matching the stable JSON shape:

    .. code-block:: json

        {
          "schema_version": "femebal-permanencia-statistics-v1",
          "stage_id": 9,
          "stage_name": "...",
          "rows": [
            {
              "club": "Club name",
              "appearances": 20,
              "goals": 65,
              "yellow": 12,
              "two_min": 5,
              "red": 1,
              "blue": 0,
              "distinct_players": 8
            }
          ],
          "note": "Only confirmed planillas are counted."
        }
    """

    stage = db.get(TournamentStage, stage_id)
    if not stage:
        raise ValueError(f"Stage {stage_id} not found")

    stage_name = stage.name

    # ------------------------------------------------------------------
    # 1. Load all confirmed snapshots for matches belonging to the stage
    # ------------------------------------------------------------------
    snapshots = (
        db.query(OfficialSnapshot)
        .join(Match, OfficialSnapshot.match_id == Match.id)
        .join(ScheduledMatch, Match.scheduled_match_id == ScheduledMatch.id)
        .filter(
            OfficialSnapshot.is_confirmed == True,
            ScheduledMatch.stage_id == stage_id,
        )
        .options(
            joinedload(OfficialSnapshot.players),
        )
        .all()
    )

    # ------------------------------------------------------------------
    # 2. Accumulate per-club stats
    # ------------------------------------------------------------------
    # club_acc[club_name] -> dict with running totals + player set
    club_acc: Dict[str, dict[str, Any]] = {}

    for snap in snapshots:
        # For each player in the snapshot, determine the club per side
        for player in snap.players:
            club = _club_from_registration(db, snap, player.side)

            if club not in club_acc:
                club_acc[club] = {
                    "appearances": 0,
                    "goals": 0,
                    "yellow": 0,
                    "two_min": 0,
                    "red": 0,
                    "blue": 0,
                    "player_ids": set(),
                }

            acc = club_acc[club]
            acc["appearances"] += 1
            acc["goals"] += player.official_goals
            acc["yellow"] += player.official_yellow
            acc["two_min"] += player.official_2min
            acc["red"] += player.official_red
            acc["blue"] += player.official_blue
            acc["player_ids"].add(player.player_id)  # may be None

    # ------------------------------------------------------------------
    # 3. Build rows with distinct player count
    # ------------------------------------------------------------------
    rows: List[dict[str, Any]] = []
    for club, acc in club_acc.items():
        distinct_players = len(
            {pid for pid in acc["player_ids"] if pid is not None}
        )
        rows.append(
            {
                "club": club,
                "appearances": acc["appearances"],
                "goals": acc["goals"],
                "yellow": acc["yellow"],
                "two_min": acc["two_min"],
                "red": acc["red"],
                "blue": acc["blue"],
                "distinct_players": distinct_players,
            }
        )

    # Sort by goals DESC
    rows.sort(key=lambda r: -r["goals"])

    return {
        "schema_version": "femebal-permanencia-statistics-v1",
        "stage_id": stage_id,
        "stage_name": stage_name,
        "rows": rows,
        "note": "Only confirmed planillas are counted.",
    }
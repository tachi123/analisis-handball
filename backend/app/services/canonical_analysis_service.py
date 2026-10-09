from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import (AnalysisEvent, AnalysisSession, CanonicalEvent, CanonicalEventRevision, CanonicalEvidence,
                          Event, GoalkeeperShot, Match, MatchSquad, OfficialSnapshot,
                          OfficialSnapshotPlayer, Player, ScheduledMatch, StageRoster, VideoSource)
from app.schemas import CanonicalEventCommand, CanonicalEventRevisionInput


class CanonicalValidationError(ValueError):
    """A command contradicts a fact already known for the match."""


class CanonicalStateConflictError(CanonicalValidationError):
    """A valid command conflicts with the projected canonical match state."""


class CanonicalWriteConflictError(CanonicalStateConflictError):
    """A concurrent canonical write invalidated this command's projection."""


class LegacyWriteBlockedError(RuntimeError):
    """A cutover match rejects legacy analytical writes; reads stay available."""


def ensure_legacy_writes_allowed(db: Session, match_id: int) -> None:
    """One shared cutover boundary applied by every legacy analytical writer."""
    match = db.get(Match, match_id)
    if match is not None and match.canonical_analysis_enabled:
        raise LegacyWriteBlockedError("match uses canonical analysis; legacy writes are blocked")


def order_key(command: CanonicalEventCommand, sequence: int) -> tuple[int, float, int]:
    """Server sequence orders an unverified clock without claiming a precise time."""
    if sequence < 1:
        raise CanonicalValidationError("sequence must be positive")
    return command.period, command.regulation_seconds if command.regulation_seconds is not None else float("inf"), sequence


def validate_command(
    command: CanonicalEventCommand,
    *,
    actor_id: int,
    match_team_ids: set[int],
    roster_sources: Mapping[int, str],
    player_team_ids: Mapping[int, int | None] | None = None,
) -> None:
    """Validate match and roster facts; replayed lineup state never blocks capture."""
    if actor_id <= 0:
        raise CanonicalValidationError("authenticated actor is required")
    if command.team_id is not None and command.team_id not in match_team_ids:
        raise CanonicalValidationError("team does not belong to the match")
    player_ids = (player_id for player_id in (command.player_id, command.related_player_id, command.goalkeeper_id) if player_id is not None)
    for player_id in player_ids:
        if player_id not in roster_sources:
            raise CanonicalValidationError("player is not listed on the match roster or official planilla")
    if command.goalkeeper_id is not None:
        goalkeeper_team_id = (player_team_ids or {}).get(command.goalkeeper_id)
        if command.team_id is None or goalkeeper_team_id not in match_team_ids or goalkeeper_team_id == command.team_id:
            raise CanonicalValidationError("shot goalkeeper must belong to the opposing match team")
    if command.kind == "goalkeeper_change" and command.outcome == "active" and command.player_id is not None:
        player_team_id = (player_team_ids or {}).get(command.player_id)
        if command.team_id is None or player_team_id != command.team_id:
            raise CanonicalValidationError("active goalkeeper must belong to the selected match team")
    if command.kind == "other" and command.outcome == "kickoff":
        if command.team_id is None:
            raise CanonicalValidationError("kickoff requires a match home or away team")
        if not any(item.kind == "video" and isinstance(item.reference, str) and item.reference.strip()
                   and item.video_source_id is not None and item.video_anchor_seconds is not None
                   for item in command.evidence):
            raise CanonicalValidationError("kickoff requires usable video evidence with a source and anchor")


def revision_payload(revision: CanonicalEventRevisionInput) -> dict:
    """Keep correction rationale and evidence rows outside the immutable observed payload."""
    return revision.model_dump(exclude={"reason", "evidence"})


def _persist_evidence(db: Session, revision: CanonicalEventRevision, command: CanonicalEventCommand, match: Match) -> None:
    """Validate and attach revision-owned provenance atomically with the revision."""
    for item in command.evidence:
        if item.kind != "unavailable" and not item.reference:
            raise CanonicalValidationError(f"{item.kind} evidence requires a reference")
        if item.scheduled_match_id is not None and item.scheduled_match_id != match.scheduled_match_id:
            raise CanonicalValidationError("evidence fixture does not belong to this match")
        if item.official_snapshot_id is not None:
            snapshot = db.get(OfficialSnapshot, item.official_snapshot_id)
            if snapshot is None or snapshot.match_id != match.id:
                raise CanonicalValidationError("evidence planilla does not belong to this match")
        if item.video_source_id is not None:
            source = db.get(VideoSource, item.video_source_id)
            if source is None or source.match_id != match.id:
                raise CanonicalValidationError("evidence video does not belong to this match")
        db.add(CanonicalEvidence(revision_id=revision.id, kind=item.kind, reference=item.reference,
                                 scheduled_match_id=item.scheduled_match_id,
                                 official_snapshot_id=item.official_snapshot_id,
                                 video_source_id=item.video_source_id,
                                 video_anchor_seconds=item.video_anchor_seconds,
                                 uncertainty=item.uncertainty))


@dataclass
class Possession:
    team_id: int
    start_basis: str
    terminal_basis: str | None = None
    unresolved: bool = False


@dataclass
class ShotTerminal:
    event_id: int
    result: str
    team_id: int | None
    player_id: int | None
    goalkeeper_id: int | None


@dataclass
class CanonicalMatchState:
    possession: Possession | None = None
    completed_possessions: list[Possession] = field(default_factory=list)
    player_states: dict[int, str] = field(default_factory=dict)
    active_goalkeepers: dict[int, int | None] = field(default_factory=dict)
    analytical_score: dict[int, int] = field(default_factory=dict)
    shots: list[ShotTerminal] = field(default_factory=list)
    discipline: list[dict] = field(default_factory=list)


def apply_transition(state: CanonicalMatchState, command: CanonicalEventCommand, event_id: int) -> CanonicalMatchState:
    """Apply only an explicit observation; unknowns never manufacture state."""
    if event_id <= 0:
        raise CanonicalValidationError("event id must be positive")
    _validate_transition_outcome(command)

    if command.kind == "other" and command.outcome == "kickoff":
        _open_possession(state, command.team_id, f"kickoff:{event_id}")
    elif command.kind == "turnover":
        _turnover(state, command, event_id)
    elif command.kind == "recovery":
        _recovery(state, command, event_id)
    elif command.kind == "shot":
        _shot(state, command, event_id)
    elif command.kind == "lineup_change":
        _lineup_change(state, command)
    elif command.kind == "goalkeeper_change":
        _goalkeeper_change(state, command)
    elif command.kind == "foul_sanction":
        _discipline(state, command, event_id)
    return state


def _open_possession(state: CanonicalMatchState, team_id: int | None, basis: str) -> None:
    if team_id is None:
        return
    if state.possession is not None and state.possession.terminal_basis is None:
        raise CanonicalStateConflictError("a possession is already open")
    if state.possession is not None:
        state.completed_possessions.append(state.possession)
    state.possession = Possession(team_id=team_id, start_basis=basis)


def _turnover(state: CanonicalMatchState, command: CanonicalEventCommand, event_id: int) -> None:
    if state.possession is None or state.possession.terminal_basis is not None:
        return
    if command.team_id is not None and state.possession.team_id != command.team_id:
        raise CanonicalStateConflictError("turnover team does not own the open possession")
    state.possession.terminal_basis = f"turnover:{event_id}"
    state.possession.unresolved = command.outcome == "unresolved_loss"


def _recovery(state: CanonicalMatchState, command: CanonicalEventCommand, event_id: int) -> None:
    if command.team_id is None:
        return
    if state.possession is not None and state.possession.terminal_basis is None:
        if state.possession.team_id == command.team_id:
            raise CanonicalStateConflictError("recovery team already owns the open possession")
        state.possession.terminal_basis = f"recovery:{event_id}"
    _open_possession(state, command.team_id, f"recovery:{event_id}")


def _shot(state: CanonicalMatchState, command: CanonicalEventCommand, event_id: int) -> None:
    if command.outcome not in {"goal", "save", "miss", "woodwork", "blocked"}:
        raise CanonicalValidationError("shot requires one terminal result: goal, save, miss, woodwork, or blocked")
    keeper = command.goalkeeper_id if command.goalkeeper_id is not None else _opposing_goalkeeper(state, command.team_id)
    state.shots.append(ShotTerminal(event_id, command.outcome, command.team_id, command.player_id, keeper))
    if command.outcome == "goal" and command.team_id is not None:
        state.analytical_score[command.team_id] = state.analytical_score.get(command.team_id, 0) + 1
    if state.possession is not None and state.possession.terminal_basis is None and state.possession.team_id == command.team_id:
        state.possession.terminal_basis = f"shot:{event_id}"


def _opposing_goalkeeper(state: CanonicalMatchState, attacking_team_id: int | None) -> int | None:
    if attacking_team_id is None:
        return None
    opponents = [keeper for team, keeper in state.active_goalkeepers.items() if team != attacking_team_id and keeper is not None]
    return opponents[0] if len(opponents) == 1 else None


def _lineup_change(state: CanonicalMatchState, command: CanonicalEventCommand) -> None:
    if command.outcome in {"on", "substitution_in"} and command.player_id is not None:
        state.player_states[command.player_id] = "on"
    elif command.outcome == "off" and command.player_id is not None:
        state.player_states[command.player_id] = "off"
    elif command.outcome == "substitution" and command.player_id is not None and command.related_player_id is not None:
        state.player_states[command.related_player_id] = "off"
        state.player_states[command.player_id] = "on"
    else:
        raise CanonicalValidationError("lineup change requires an explicit on, off, or substitution fact")


def _goalkeeper_change(state: CanonicalMatchState, command: CanonicalEventCommand) -> None:
    if command.team_id is None:
        return
    if command.outcome == "unknown":
        state.active_goalkeepers[command.team_id] = None
    elif command.outcome == "active" and command.player_id is not None:
        state.active_goalkeepers[command.team_id] = command.player_id
    else:
        raise CanonicalValidationError("goalkeeper change requires active player or explicit unknown")


def _discipline(state: CanonicalMatchState, command: CanonicalEventCommand, event_id: int) -> None:
    state.discipline.append({"event_id": event_id, "team_id": command.team_id, "player_id": command.player_id,
                              "sanction": command.outcome, "uncertainty": command.uncertainty})


def _validate_transition_outcome(command: CanonicalEventCommand) -> None:
    """Keep the accepted command vocabulary beside the transition that consumes it."""
    allowed = {
        "shot": {"goal", "save", "miss", "woodwork", "blocked"},
        "turnover": {"bad_pass", "bad_reception", "walking", "double_dribble", "offensive_foul", "steal", "three_seconds", "area_violation", "passive",
                      "technical", "interception", "unresolved_loss"},
        "recovery": {"bad_pass", "bad_reception", "walking", "double_dribble", "offensive_foul", "steal", "three_seconds", "area_violation",
                      "technical", "interception"},
        "lineup_change": {"on", "off", "substitution_in", "substitution"},
        "goalkeeper_change": {"active", "unknown"},
        "foul_sanction": {"foul", "seven_meter", "yellow_card", "red_card", "blue_card", "two_minute_exclusion"},
        "other": {"kickoff", "period_end", "timeout"},
    }
    if command.outcome not in allowed[command.kind]:
        if command.kind == "shot":
            raise CanonicalValidationError("shot requires one terminal result: goal, save, miss, woodwork, or blocked")
        raise CanonicalValidationError(f"{command.kind} requires a supported outcome")


def _latest_revision(event: CanonicalEvent) -> CanonicalEventRevision:
    return max(event.revisions, key=lambda revision: revision.revision)


def read_events(db: Session, match_id: int, include_inactive: bool = True) -> list[dict]:
    events = (db.query(CanonicalEvent).options(joinedload(CanonicalEvent.revisions).joinedload(CanonicalEventRevision.evidence))
              .filter_by(match_id=match_id).order_by(CanonicalEvent.sequence).all())
    result = []
    for event in events:
        revision = _latest_revision(event)
        payload = dict(revision.payload)
        active = payload.get("active", True)
        if include_inactive or active:
            result.append({"id": event.id, "sequence": event.sequence, "active": active, "revision": revision.revision,
                           "actor_id": revision.actor_id, "reason": revision.reason, "payload": payload,
                           "evidence": [{"id": item.id, "kind": item.kind, "reference": item.reference,
                                         "scheduled_match_id": item.scheduled_match_id,
                                         "official_snapshot_id": item.official_snapshot_id,
                                         "video_source_id": item.video_source_id,
                                         "video_anchor_seconds": item.video_anchor_seconds,
                                         "uncertainty": item.uncertainty} for item in revision.evidence]})
    return result


def _roster_sources(db: Session, match: Match) -> dict[int, str]:
    """Return the strongest documented eligibility source for each match player."""
    sources = {
        player_id: "match_squad"
        for (player_id,) in db.query(MatchSquad.player_id).filter_by(match_id=match.id).all()
    }
    for (player_id,) in (
        db.query(OfficialSnapshotPlayer.player_id)
        .join(OfficialSnapshot)
        .filter(OfficialSnapshot.match_id == match.id, OfficialSnapshotPlayer.player_id.isnot(None))
        .all()
    ):
        sources.setdefault(player_id, "official_planilla")
    if match.scheduled_match_id is not None:
        fixture = db.get(ScheduledMatch, match.scheduled_match_id)
        registration_ids = [
            registration_id for registration_id in
            (fixture.home_registration_id, fixture.away_registration_id) if registration_id is not None
        ] if fixture is not None else []
        if registration_ids:
            for (player_id,) in db.query(StageRoster.player_id).filter(StageRoster.registration_id.in_(registration_ids)).all():
                sources.setdefault(player_id, "fixture_stage_roster")
    return sources


def _match_context(db: Session, match_id: int) -> tuple[Match, set[int], dict[int, str]]:
    match = db.get(Match, match_id)
    if match is None:
        raise CanonicalValidationError("match not found")
    team_ids = {team_id for team_id in (match.home_team_id, match.away_team_id) if team_id is not None}
    return match, team_ids, _roster_sources(db, match)


def _player_team_ids(db: Session, player_ids: Mapping[int, str]) -> dict[int, int | None]:
    return {player_id: team_id for player_id, team_id in db.query(Player.id, Player.team_id).filter(Player.id.in_(player_ids)).all()}


def _payload_with_roster_sources(command: CanonicalEventCommand, roster_sources: Mapping[int, str]) -> dict:
    payload = command.model_dump(mode="json", exclude={"evidence"})
    if command.player_id is not None:
        payload["roster_source"] = roster_sources[command.player_id]
    if command.related_player_id is not None:
        payload["related_player_roster_source"] = roster_sources[command.related_player_id]
    return payload


def _is_kickoff(command: CanonicalEventCommand) -> bool:
    return command.kind == "other" and command.outcome == "kickoff"


def _is_calibrated_kickoff_payload(payload: Mapping) -> bool:
    return (payload.get("kind") == "other" and payload.get("outcome") == "kickoff"
            and payload.get("regulation_seconds") == 0 and payload.get("clock_unverified") is False)


def _project_match_state(events: list[tuple[int, int, CanonicalEventCommand]]) -> CanonicalMatchState:
    """Replay one match projection; active possessions are scoped to their command's period."""
    state = CanonicalMatchState()
    possessions: dict[int, Possession | None] = {}
    for sequence, event_id, command in sorted(events):
        state.possession = possessions.get(command.period)
        apply_transition(state, command, event_id)
        possessions[command.period] = state.possession
    if possessions:
        active_period = max(possessions)
        completed_ids = {id(possession) for possession in state.completed_possessions}
        state.completed_possessions.extend(
            possession for period, possession in possessions.items()
            if period != active_period and possession is not None and possession.terminal_basis is not None
            and id(possession) not in completed_ids
        )
        state.possession = possessions[active_period]
    return state


def _validate_active_match_events(projected: list[tuple[int, int, CanonicalEventCommand]]) -> CanonicalMatchState:
    """Validate the one authoritative active match projection."""
    payloads_by_period: dict[int, list[dict]] = {}
    for _, _, command in projected:
        payloads_by_period.setdefault(command.period, []).append(command.model_dump(mode="json"))
    for payloads in payloads_by_period.values():
        has_generic_event = any(not _is_kickoff(CanonicalEventCommand(**payload)) for payload in payloads)
        if has_generic_event and not any(_is_calibrated_kickoff_payload(payload) for payload in payloads):
            raise CanonicalValidationError("cannot leave canonical events without a calibrated kickoff at 00:00")
    return _project_match_state(projected)


def _validate_projected_match(db: Session, match_id: int, *, replacement_event_id: int | None,
                              replacement: CanonicalEventCommand, replacement_active: bool) -> CanonicalMatchState:
    """Validate the complete active match projection before any canonical mutation commits."""
    projected = []
    found_replacement = replacement_event_id is None
    for item in read_events(db, match_id, include_inactive=True):
        if item["id"] == replacement_event_id:
            found_replacement = True
            if replacement_active:
                projected.append((item["sequence"], item["id"], replacement))
        elif item["active"]:
            projected.append((item["sequence"], item["id"], CanonicalEventCommand(**item["payload"])))
    if not found_replacement:
        raise CanonicalValidationError("canonical event not found")
    if replacement_event_id is None and replacement_active:
        next_sequence = (max((sequence for sequence, _, _ in projected), default=0) + 1)
        next_event_id = (db.query(func.max(CanonicalEvent.id)).scalar() or 0) + 1
        projected.append((next_sequence, next_event_id, replacement))

    state = _validate_active_match_events(projected)

    # An inactive correction is not part of the projection, but it must still be a valid command.
    if not replacement_active:
        apply_transition(CanonicalMatchState(), replacement, replacement_event_id or 1)
    return state


def _lock_match(db: Session, match_id: int) -> Match:
    """Serialize canonical writers for one match on databases supporting row locks.

    SQLite ignores FOR UPDATE, so its unique constraints remain the fallback and
    are translated to CanonicalWriteConflictError by each writer.
    """
    match = db.query(Match).filter_by(id=match_id).with_for_update().one_or_none()
    if match is None:
        raise CanonicalValidationError("match not found")
    if not match.canonical_analysis_enabled:
        raise CanonicalValidationError("canonical analysis is disabled for this match; use legacy read-only fallback")
    return match


def require_canonical_cutover(db: Session, match_id: int) -> Match:
    """Canonical data is opt-in per match; rollback leaves legacy records untouched."""
    match = db.get(Match, match_id)
    if match is None:
        raise CanonicalValidationError("match not found")
    if not match.canonical_analysis_enabled:
        raise CanonicalValidationError("canonical analysis is disabled for this match; use legacy read-only fallback")
    return match


def create_event(db: Session, match_id: int, command: CanonicalEventCommand, actor_id: int) -> dict:
    match = _lock_match(db, match_id)
    _, team_ids, roster_sources = _match_context(db, match_id)
    validate_command(command, actor_id=actor_id, match_team_ids=team_ids, roster_sources=roster_sources,
                     player_team_ids=_player_team_ids(db, roster_sources))
    _validate_projected_match(db, match_id, replacement_event_id=None, replacement=command, replacement_active=True)
    sequence = (db.query(func.max(CanonicalEvent.sequence)).filter_by(match_id=match_id).scalar() or 0) + 1
    try:
        event = CanonicalEvent(match_id=match_id, sequence=sequence)
        db.add(event)
        db.flush()
        revision = CanonicalEventRevision(event_id=event.id, revision=1, actor_id=actor_id,
                                          payload=_payload_with_roster_sources(command, roster_sources), reason="created")
        db.add(revision)
        db.flush()
        _persist_evidence(db, revision, command, match)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise CanonicalWriteConflictError("concurrent canonical write; retry the command") from error
    except Exception:
        db.rollback()
        raise
    return read_events(db, match_id)[-1]


def revise_event(db: Session, event_id: int, revision_input: CanonicalEventRevisionInput, actor_id: int) -> dict:
    event = db.get(CanonicalEvent, event_id)
    if event is None:
        raise CanonicalValidationError("canonical event not found")
    _lock_match(db, event.match_id)
    db.refresh(event)
    match, team_ids, roster_sources = _match_context(db, event.match_id)
    validate_command(revision_input, actor_id=actor_id, match_team_ids=team_ids, roster_sources=roster_sources,
                     player_team_ids=_player_team_ids(db, roster_sources))
    latest = _latest_revision(event)
    if latest.actor_id != actor_id:
        raise PermissionError("only the recording analyst may revise this event")
    _validate_projected_match(db, event.match_id, replacement_event_id=event.id, replacement=revision_input,
                              replacement_active=latest.payload.get("active", True))
    payload = revision_payload(revision_input)
    payload.update(_payload_with_roster_sources(revision_input, roster_sources))
    payload["active"] = latest.payload.get("active", True)
    try:
        revision = CanonicalEventRevision(event_id=event.id, revision=latest.revision + 1, actor_id=actor_id,
                                          payload=payload, reason=revision_input.reason)
        db.add(revision)
        db.flush()
        _persist_evidence(db, revision, revision_input, match)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise CanonicalWriteConflictError("concurrent canonical write; retry the command") from error
    except Exception:
        db.rollback()
        raise
    return next(item for item in read_events(db, event.match_id) if item["id"] == event_id)


def deactivate_event(db: Session, event_id: int, reason: str, actor_id: int) -> dict:
    event = db.get(CanonicalEvent, event_id)
    if event is None:
        raise CanonicalValidationError("canonical event not found")
    _lock_match(db, event.match_id)
    db.refresh(event)
    latest = _latest_revision(event)
    if latest.actor_id != actor_id:
        raise PermissionError("only the recording analyst may deactivate this event")
    _validate_projected_match(db, event.match_id, replacement_event_id=event.id,
                              replacement=CanonicalEventCommand(**latest.payload), replacement_active=False)
    payload = dict(latest.payload)
    payload["active"] = False
    try:
        db.add(CanonicalEventRevision(event_id=event.id, revision=latest.revision + 1, actor_id=actor_id,
                                      payload=payload, reason=reason))
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise CanonicalWriteConflictError("concurrent canonical write; retry the command") from error
    except Exception:
        db.rollback()
        raise
    return next(item for item in read_events(db, event.match_id) if item["id"] == event_id)


def deactivate_last_event(db: Session, match_id: int, reason: str, actor_id: int) -> dict:
    """Deactivate only the latest active canonical identity, never delete its history."""
    _lock_match(db, match_id)
    active = [item for item in read_events(db, match_id, include_inactive=False)]
    if not active:
        raise CanonicalValidationError("there is no active canonical incident to delete")
    latest = max(active, key=lambda item: item["sequence"])
    if latest["actor_id"] != actor_id:
        raise CanonicalValidationError("the latest active canonical incident belongs to another analyst")
    return deactivate_event(db, latest["id"], reason, actor_id)


def reset_analyst_review(db: Session, match_id: int, reason: str, actor_id: int) -> dict:
    """Reset one analyst's workspace and audit-deactivate only their active facts atomically."""
    _lock_match(db, match_id)
    owned = sorted((item for item in read_events(db, match_id, include_inactive=False) if item["actor_id"] == actor_id), key=lambda item: item["sequence"], reverse=True)
    try:
        owned_ids = {item["id"] for item in owned}
        _validate_active_match_events([
            (item["sequence"], item["id"], CanonicalEventCommand(**item["payload"]))
            for item in read_events(db, match_id, include_inactive=False) if item["id"] not in owned_ids
        ])
        for item in owned:
            event = db.get(CanonicalEvent, item["id"])
            revision = _latest_revision(event)
            payload = dict(revision.payload)
            payload["active"] = False
            db.add(CanonicalEventRevision(event_id=event.id, revision=revision.revision + 1, actor_id=actor_id,
                                          payload=payload, reason=reason))

        session = db.query(AnalysisSession).filter_by(match_id=match_id, analyst_id=actor_id).one_or_none()
        if session is not None:
            session.video_source_id = None
            session.video_position_seconds = None
            session.clock_start_video_seconds = None
            session.angle = None
            session.filters = {}
            session.draft = {}
            session.queue = []
            session.anchors[:] = []
            session.time_segments[:] = []
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise CanonicalWriteConflictError("concurrent canonical write; retry the command") from error
    except Exception:
        db.rollback()
        raise
    return {"deactivated_events": len(owned), "session_reset": session is not None}


def read_state(db: Session, match_id: int) -> dict:
    state = _project_match_state([
        (item["sequence"], item["id"], CanonicalEventCommand(**item["payload"]))
        for item in read_events(db, match_id, include_inactive=False)
    ])
    return {"analytical_score": state.analytical_score, "possession": vars(state.possession) if state.possession else None,
            "active_goalkeepers": state.active_goalkeepers, "player_states": state.player_states,
            "discipline": state.discipline}


def read_metrics(db: Session, match_id: int) -> dict:
    events = read_events(db, match_id)
    eligible, excluded, unknown, clock_unverified = [], 0, 0, 0
    for event in events:
        payload = event["payload"]
        if payload.get("clock_unverified"):
            clock_unverified += 1
        if not event["active"] or payload.get("fact_kind") != "observed":
            excluded += 1
        elif payload.get("evidence_state") != "confirmed":
            unknown += 1
        else:
            eligible.append(event)
    metrics: dict[str, dict] = {}

    def add(name: str, event: dict, *, numerator: bool = False, denominator: str | int = "not_applicable") -> None:
        metric = metrics.setdefault(name, {"name": name, "count": 0, "numerator": 0,
                                           "denominator": denominator, "excluded": 0, "unknown": 0,
                                           "clock_unverified": 0, "evidence": []})
        metric["count"] += 1
        metric["numerator"] += int(numerator)
        metric["evidence"].append({"event_id": event["id"], "revision_id": event["revision"]})

    unresolved_possessions = 0
    for event in eligible:
        payload = event["payload"]
        kind, team_id, player_id, outcome = payload["kind"], payload.get("team_id"), payload.get("player_id"), payload.get("outcome")
        if kind == "shot":
            add("shots", event, numerator=outcome == "goal", denominator=0)
            if team_id is not None:
                add(f"team:{team_id}:shots", event, numerator=outcome == "goal", denominator=0)
            if player_id is not None:
                add(f"player:{player_id}:shots", event, numerator=outcome == "goal", denominator=0)
        elif kind in {"turnover", "recovery", "foul_sanction"}:
            label = {"turnover": "turnovers", "recovery": "recoveries", "foul_sanction": "discipline"}[kind]
            add(label, event)
            if team_id is not None:
                add(f"team:{team_id}:{label}", event)
            if player_id is not None:
                add(f"player:{player_id}:{label}", event)
        if kind == "turnover" and outcome == "unresolved_loss":
            unresolved_possessions += 1

    state = _project_match_state([
        (event["sequence"], event["id"], CanonicalEventCommand(**event["payload"]))
        for event in eligible
    ])
    for shot in state.shots:
        if shot.result == "save" and shot.goalkeeper_id is not None:
            source = next(event for event in eligible if event["id"] == shot.event_id)
            add(f"goalkeeper:{shot.goalkeeper_id}:saves", source, numerator=True, denominator=0)
    completed = len(state.completed_possessions) + int(state.possession is not None and state.possession.terminal_basis is not None)
    if completed:
        metrics["possessions"] = {"name": "possessions", "count": completed, "numerator": completed,
                                  "denominator": "not_applicable", "excluded": 0, "unknown": unresolved_possessions,
                                  "clock_unverified": 0, "evidence": []}
    for metric in metrics.values():
        if isinstance(metric["denominator"], int):
            metric["denominator"] = metric["count"]
    active_events = [event for event in events if event["active"]]
    coverage = {"active_events": len(active_events), "eligible_events": len(eligible),
                "eligible_ratio": (round(len(eligible) / len(active_events), 4) if active_events else None)}
    return {"metrics": metrics, "eligibility": {"eligible": len(eligible), "excluded": excluded,
            "unknown": unknown, "clock_unverified": clock_unverified, "unresolved": unresolved_possessions},
            "coverage": coverage,
            "evidence": {str(event["id"]): event["evidence"] for event in eligible}, "events": eligible}


_DISCIPLINE_KEYS = ("yellow", "two_minute", "red")
_WARNING_METRICS = ("goals", *_DISCIPLINE_KEYS, "blue")


def _sanction_bucket(outcome: str | None) -> str | None:
    return {"yellow_card": "yellow", "two_minute_exclusion": "two_minute", "red_card": "red",
            "blue_card": "blue"}.get(outcome or "")


def read_reconciliation(db: Session, match_id: int) -> dict:
    snapshot = db.query(OfficialSnapshot).filter_by(match_id=match_id).order_by(OfficialSnapshot.created_at.desc()).first()
    metrics = read_metrics(db, match_id)
    score: dict[int, int] = {}
    evidence = []
    discipline_events = []
    for event in metrics["events"]:
        payload = event["payload"]
        if payload["kind"] == "shot" and payload.get("outcome") == "goal" and payload.get("team_id") is not None:
            score[payload["team_id"]] = score.get(payload["team_id"], 0) + 1
            evidence.append({"event_id": event["id"], "evidence": event["evidence"]})
        elif payload["kind"] == "foul_sanction":
            discipline_events.append(event)
    if snapshot is None:
        return {"official": None, "analytical_score": score, "evidence": evidence, "discrepancies": [],
                "discipline": []}
    official = {"snapshot_id": snapshot.id, "home_score": snapshot.home_score, "away_score": snapshot.away_score}
    match = db.get(Match, match_id)
    discrepancies = [{"side": "home", "official": snapshot.home_score, "analytical": score.get(match.home_team_id, 0)},
                     {"side": "away", "official": snapshot.away_score, "analytical": score.get(match.away_team_id, 0)}]
    for item in discrepancies:
        item["discrepancy"] = item["analytical"] - item["official"]

    sides = {}
    if match.home_team_id is not None:
        sides[match.home_team_id] = "home"
    if match.away_team_id is not None:
        sides[match.away_team_id] = "away"
    official_totals: dict[str, dict[str, int]] = {}
    for player in snapshot.players:
        bucket = official_totals.setdefault(player.side, {key: 0 for key in _DISCIPLINE_KEYS})
        bucket["yellow"] += player.official_yellow
        bucket["two_minute"] += player.official_2min
        bucket["red"] += player.official_red

    def zeroed() -> dict[str, int]:
        return {key: 0 for key in _DISCIPLINE_KEYS}

    discipline = []
    for team_id, side in sides.items():
        official_counts = dict(official_totals.get(side, zeroed()))
        observed_counts = zeroed()
        team_evidence = []
        for event in discipline_events:
            payload = event["payload"]
            if payload.get("team_id") != team_id:
                continue
            key = _sanction_bucket(payload.get("outcome"))
            if key is not None:
                observed_counts[key] += 1
            team_evidence.append({"event_id": event["id"], "revision_id": event["revision"]})
        status = "match" if official_counts == observed_counts else "mismatch"
        discipline.append({"team_id": team_id, "side": side, "official": official_counts,
                           "observed": observed_counts, "status": status,
                           "coverage": {"eligible_discipline_events": len(team_evidence)},
                           "evidence": team_evidence})
    return {"official": official, "analytical_score": score, "evidence": evidence, "discrepancies": discrepancies,
            "discipline": discipline}


def _warning_bucket() -> dict:
    return {"counts": {metric: 0 for metric in _WARNING_METRICS},
            "references": {metric: {"event_ids": [], "evidence_ids": []} for metric in _WARNING_METRICS}}


def _add_warning_event(bucket: dict, metric: str, event: dict) -> None:
    bucket["counts"][metric] += 1
    reference = bucket["references"][metric]
    reference["event_ids"].append(event["id"])
    reference["evidence_ids"].extend(item["id"] for item in event["evidence"])


def _warning_metric(payload: dict) -> str | None:
    if payload.get("kind") == "shot" and payload.get("outcome") == "goal":
        return "goals"
    if payload.get("kind") == "foul_sanction":
        return _sanction_bucket(payload.get("outcome"))
    return None


def _warning_status(canonical: int | None, official: int | None) -> str:
    if canonical is None:
        return "missing_in_canonical"
    if official is None:
        return "missing_in_official"
    if canonical == official:
        return "exact"
    # Counts have zero tolerance. Direction identifies the source missing recorded facts.
    return "missing_in_canonical" if canonical < official else "missing_in_official"


def _warning_comparison(canonical: int | None, official: int | None, bucket: dict | None, metric: str) -> dict:
    reference = bucket["references"][metric] if bucket is not None else {"event_ids": [], "evidence_ids": []}
    return {"canonical": canonical, "official": official, "status": _warning_status(canonical, official),
            "tolerance": 0, "canonical_event_ids": reference["event_ids"], "evidence_ids": reference["evidence_ids"]}


def _warning_metrics(canonical: dict | None, official: dict | None) -> dict:
    return {metric: _warning_comparison(canonical["counts"][metric] if canonical else None,
                                        official[metric] if official else None, canonical, metric)
            for metric in _WARNING_METRICS}


def read_warnings_summary(db: Session, match_id: int) -> dict:
    """Compare eligible canonical player facts with the latest immutable official snapshot."""
    match = require_canonical_cutover(db, match_id)
    snapshot = db.query(OfficialSnapshot).filter_by(match_id=match_id).order_by(OfficialSnapshot.created_at.desc()).first()
    canonical_players: dict[int, dict] = {}
    canonical_total = _warning_bucket()

    for event in read_metrics(db, match_id)["events"]:
        metric = _warning_metric(event["payload"])
        if metric is None:
            continue
        _add_warning_event(canonical_total, metric, event)
        player_id = event["payload"].get("player_id")
        if player_id is None:
            continue
        player = canonical_players.setdefault(player_id, {"bucket": _warning_bucket(), "team_id": event["payload"].get("team_id")})
        _add_warning_event(player["bucket"], metric, event)

    official_players: dict[int, dict] = {}
    official_only_players: list[dict] = []
    official_total = {metric: 0 for metric in _WARNING_METRICS} if snapshot is not None else None
    if snapshot is not None:
        for row in snapshot.players:
            values = {"goals": row.official_goals, "yellow": row.official_yellow,
                      "two_minute": row.official_2min, "red": row.official_red, "blue": row.official_blue}
            for metric, value in values.items():
                official_total[metric] += value
            if row.player_id is None:
                official_only_players.append({"row": row, "values": values})
                continue
            official = official_players.setdefault(row.player_id, {"row": row, "values": {metric: 0 for metric in _WARNING_METRICS}})
            for metric, value in values.items():
                official["values"][metric] += value

    def side_for(team_id: int | None) -> str | None:
        if team_id == match.home_team_id:
            return "home"
        if team_id == match.away_team_id:
            return "away"
        return None

    players = []
    for player_id in sorted(set(canonical_players) | set(official_players)):
        canonical = canonical_players.get(player_id)
        official = official_players.get(player_id)
        source = official["row"] if official else None
        player = db.get(Player, player_id)
        players.append({"player": {"id": player_id, "name": source.name if source else player.name if player else str(player_id),
                                   "jersey_number": source.jersey_number if source else player.default_jersey_number if player else None,
                                   "side": source.side if source else side_for(canonical["team_id"])},
                        "metrics": _warning_metrics(canonical["bucket"] if canonical else None,
                                                    official["values"] if official else None)})
    for item in official_only_players:
        row = item["row"]
        players.append({"player": {"id": None, "name": row.name, "jersey_number": row.jersey_number, "side": row.side},
                        "metrics": _warning_metrics(None, item["values"])})

    limitations = [
        {"check": "goal_timestamps", "status": "not_comparable", "reason": "official snapshot has no goal timestamps"},
        {"check": "card_timestamps", "status": "not_comparable", "reason": "official snapshot has no card timestamps"},
        {"check": "goalkeeper_substitutions", "status": "not_comparable", "reason": "official snapshot has no goalkeeper substitution records"},
    ]
    return {"match_id": match_id, "official_snapshot_id": snapshot.id if snapshot else None, "players": players,
            "match_totals": {"metrics": _warning_metrics(canonical_total, official_total)}, "limitations": limitations}


def read_player_projection(
    db: Session,
    match_id: int,
    player_id: int,
    *,
    team_id: int | None = None,
    period: int | None = None,
    from_regulation_seconds: float | None = None,
    to_regulation_seconds: float | None = None,
) -> dict:
    """Replay current canonical facts without inferring goalkeeper participation."""
    require_canonical_cutover(db, match_id)
    match, team_ids, roster_sources = _match_context(db, match_id)
    if player_id not in roster_sources:
        raise CanonicalValidationError("player is not listed on the match roster or official planilla")
    if team_id is not None and team_id not in team_ids:
        raise CanonicalValidationError("team does not belong to the match")
    if from_regulation_seconds is not None and to_regulation_seconds is not None and from_regulation_seconds > to_regulation_seconds:
        raise CanonicalValidationError("from_regulation_seconds must not exceed to_regulation_seconds")

    player = db.get(Player, player_id)
    selected_team = team_id if team_id is not None else (player.team_id if player is not None else None)
    if selected_team not in team_ids:
        selected_team = None
    zones = {str(zone): 0 for zone in range(1, 10)}
    shot_map = {"zones": zones, "recorded": 0, "missing_zone": 0, "goalkeeper_unknown": 0,
                "excluded": 0, "unknown": 0, "clock_unverified": 0}
    participation = {"on": 0, "off": 0, "substitution": 0, "evidence": []}
    discipline = {"yellow": 0, "two_minute": 0, "red": 0, "evidence": []}
    metrics = {"saves": 0, "goals_conceded": 0, "save_rate": None}
    evidence_events: list[dict] = []
    active_goalkeepers: dict[int, int | None] = {}

    def matches_filter(item: dict) -> bool:
        payload = item["payload"]
        if period is not None and payload.get("period") != period:
            return False
        if team_id is not None and payload.get("team_id") != team_id:
            return False
        return True

    def event_ref(item: dict) -> dict:
        return {"id": item["id"], "revision": item["revision"], "sequence": item["sequence"],
                "period": item["payload"].get("period"), "regulation_seconds": item["payload"].get("regulation_seconds"),
                "clock_unverified": item["payload"].get("clock_unverified", False), "payload": item["payload"],
                "evidence": item["evidence"]}

    for item in read_events(db, match_id, include_inactive=False):
        payload = item["payload"]
        eligible = payload.get("fact_kind") == "observed" and payload.get("evidence_state") == "confirmed"
        if payload.get("kind") == "goalkeeper_change":
            keeper_team = payload.get("team_id")
            if eligible and keeper_team is not None:
                active_goalkeepers[keeper_team] = payload.get("player_id") if payload.get("outcome") == "active" else None

        relevant = matches_filter(item)
        if not relevant:
            continue
        if not eligible:
            shot_map["excluded"] += 1
            evidence_events.append({**event_ref(item), "bucket": "excluded"})
            continue
        is_unverified = bool(payload.get("clock_unverified"))
        has_range = from_regulation_seconds is not None or to_regulation_seconds is not None
        in_range = True
        if has_range and not is_unverified:
            seconds = payload.get("regulation_seconds")
            in_range = seconds is not None and (from_regulation_seconds is None or seconds >= from_regulation_seconds) and (to_regulation_seconds is None or seconds <= to_regulation_seconds)

        if payload.get("kind") == "lineup_change" and payload.get("player_id") == player_id:
            if is_unverified and has_range:
                evidence_events.append({**event_ref(item), "bucket": "clock_unverified"})
                continue
            if in_range:
                outcome = payload.get("outcome")
                if outcome in {"on", "substitution_in"}:
                    participation["on"] += 1
                elif outcome == "off":
                    participation["off"] += 1
                elif outcome == "substitution":
                    participation["substitution"] += 1
                participation["evidence"].append(event_ref(item))
                evidence_events.append(event_ref(item))

        if payload.get("kind") == "foul_sanction" and payload.get("player_id") == player_id and in_range and not (is_unverified and has_range):
            bucket = _sanction_bucket(payload.get("outcome"))
            if bucket is not None:
                discipline[bucket] += 1
                discipline["evidence"].append(event_ref(item))
                evidence_events.append(event_ref(item))

        if payload.get("kind") != "shot" or selected_team is None or payload.get("team_id") == selected_team:
            shot_map["excluded"] += 1
            continue
        outcome = payload.get("outcome")
        if outcome not in {"save", "goal"}:
            shot_map["excluded"] += 1
            continue
        explicit_goalkeeper = payload.get("goalkeeper_id")
        opposing = [keeper for keeper_team, keeper in active_goalkeepers.items() if keeper_team != payload.get("team_id") and keeper is not None]
        attributed = explicit_goalkeeper if explicit_goalkeeper is not None else (opposing[0] if len(opposing) == 1 else None)
        if is_unverified and has_range:
            if attributed == player_id or attributed is None:
                shot_map["clock_unverified"] += 1
                evidence_events.append({**event_ref(item), "bucket": "clock_unverified"})
            else:
                shot_map["excluded"] += 1
            continue
        if not in_range:
            continue
        if attributed is None:
            shot_map["goalkeeper_unknown"] += 1
            shot_map["unknown"] += 1
            evidence_events.append({**event_ref(item), "bucket": "goalkeeper_unknown"})
            continue
        if attributed != player_id:
            shot_map["excluded"] += 1
            continue
        if outcome == "save":
            metrics["saves"] += 1
        elif outcome == "goal":
            metrics["goals_conceded"] += 1
        zone = payload.get("shot_zone")
        if zone is None:
            shot_map["missing_zone"] += 1
        else:
            zones[str(zone)] += 1
            shot_map["recorded"] += 1
        evidence_events.append(event_ref(item))

    denominator = metrics["saves"] + metrics["goals_conceded"]
    if denominator:
        metrics["save_rate"] = {"numerator": metrics["saves"], "denominator": denominator, "value": round(metrics["saves"] / denominator, 4)}
    return {"player": {"id": player_id, "name": player.name if player else None, "team_id": selected_team,
                        "roster_source": roster_sources[player_id]},
            "filters": {"team_id": team_id, "period": period, "from_regulation_seconds": from_regulation_seconds,
                        "to_regulation_seconds": to_regulation_seconds},
            "participation": participation, "metrics": metrics, "discipline": discipline, "shot_map": shot_map,
            "evidence": evidence_events,
            "unfiltered_context": {"canonical_metrics": read_metrics(db, match_id), "reconciliation": read_reconciliation(db, match_id)}}


def legacy_dry_run(db: Session, match_id: int) -> list[dict]:
    sources = (("events", db.query(Event).filter_by(match_id=match_id).all()),
               ("analysis_events", db.query(AnalysisEvent).filter_by(match_id=match_id).all()),
               ("goalkeeper_shots", db.query(GoalkeeperShot).filter_by(match_id=match_id).all()))
    return [{"source_table": table, "source_id": row.id, "reviewed": False, "eligible": False,
             "mapping_confidence": "unreviewed", "payload": {column.name: getattr(row, column.name) for column in row.__table__.columns}}
            for table, rows in sources for row in rows]

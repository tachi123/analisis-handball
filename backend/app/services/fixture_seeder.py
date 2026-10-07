"""Validated, local-only importer for curated tournament fixture JSON."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from ..models import (
    Club,
    CompetitionTeam,
    FixtureImport,
    FixtureImportEntry,
    Round,
    ScheduledMatch,
    Season,
    TeamRegistration,
    TournamentStage,
)

RESULT_STATUSES = {"unreported", "reported", "approved", "disputed"}


class FixtureValidationError(ValueError):
    """The curated fixture does not satisfy the import contract."""


@dataclass(frozen=True)
class ImportSummary:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    byes: int = 0


def load_fixture(path: str) -> tuple[dict[str, Any], str]:
    """Read JSON without making any network or PDF request."""
    with open(path, encoding="utf-8") as fixture_file:
        text = fixture_file.read()
    try:
        return json.loads(text), text
    except json.JSONDecodeError as error:
        raise FixtureValidationError(f"invalid JSON: {error.msg}") from error


def validate_fixture(payload: Any) -> dict[str, Any]:
    """Validate all structural and cross-entry facts before database work."""
    if not isinstance(payload, dict):
        raise FixtureValidationError("fixture must be an object")
    source = _object(payload, "source")
    stage = _object(payload, "stage")
    _text(source, "label")
    _date(source, "captured_at")
    if not isinstance(stage.get("season"), int) or stage["season"] < 1:
        raise FixtureValidationError("stage.season must be a positive integer")
    for field in ("name", "category", "division", "gender"):
        _text(stage, field)
    rounds = payload.get("rounds")
    if not isinstance(rounds, list) or not rounds:
        raise FixtureValidationError("rounds must be a non-empty list")
    round_numbers, entry_keys = set(), set()
    for round_data in rounds:
        if not isinstance(round_data, dict):
            raise FixtureValidationError("round must be an object")
        number = round_data.get("number")
        if not isinstance(number, int) or number < 1 or number in round_numbers:
            raise FixtureValidationError("round numbers must be positive and unique")
        round_numbers.add(number)
        entries = round_data.get("entries")
        if not isinstance(entries, list):
            raise FixtureValidationError("round.entries must be a list")
        for entry in entries:
            _validate_entry(entry, entry_keys)
    return payload


def import_fixture(db: Session, payload: Any, raw_payload: str | None = None, dry_run: bool = False) -> ImportSummary:
    """Import a complete validated payload in one transaction, or simulate it."""
    fixture = validate_fixture(payload)
    canonical_payload = raw_payload if raw_payload is not None else json.dumps(
        fixture, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    source_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
    owns_transaction = not db.in_transaction()
    transaction = db.begin() if owns_transaction else None
    try:
        if db.query(FixtureImport).filter_by(source_sha256=source_hash).first():
            summary = ImportSummary(skipped=1)
        else:
            summary = _apply_fixture(db, fixture, source_hash)
        if dry_run and transaction:
            transaction.rollback()
        elif owns_transaction:
            transaction.commit()
        return summary
    except Exception:
        if owns_transaction:
            transaction.rollback()
        raise


def _apply_fixture(db: Session, fixture: dict[str, Any], source_hash: str) -> ImportSummary:
    stage_data, source = fixture["stage"], fixture["source"]
    season = db.query(Season).filter_by(year=stage_data["season"]).first()
    if not season:
        season = Season(year=stage_data["season"])
        db.add(season)
        db.flush()
    stage = db.query(TournamentStage).filter_by(season_id=season.id, name=stage_data["name"]).first()
    if not stage:
        stage = TournamentStage(season_id=season.id, **{key: stage_data[key] for key in ("name", "category", "division", "gender")})
        db.add(stage)
        db.flush()
    audit = FixtureImport(stage_id=stage.id, source_label=source["label"], captured_at=_parse_datetime(source["captured_at"]), source_sha256=source_hash, payload=fixture)
    db.add(audit)
    created = updated = byes = 0
    for round_data in fixture["rounds"]:
        round_ = db.query(Round).filter_by(stage_id=stage.id, round_number=round_data["number"]).first()
        if not round_:
            round_ = Round(stage_id=stage.id, round_number=round_data["number"])
            db.add(round_)
            db.flush()
        for entry in round_data["entries"]:
            if entry["kind"] == "bye":
                db.add(FixtureImportEntry(fixture_import=audit, entry_key=entry["entry_key"], kind="bye", raw_entry=entry))
                byes += 1
                continue
            home = _registration(db, stage, entry["home"])
            away = _registration(db, stage, entry["away"])
            fixture_key = entry.get("fixture_key") or _fixture_key(stage.id, round_.id, home.id, away.id, entry["entry_key"])
            match = db.query(ScheduledMatch).filter_by(fixture_key=fixture_key).first()
            if not match:
                match = ScheduledMatch(stage_id=stage.id, round_id=round_.id, home_registration_id=home.id, away_registration_id=away.id, match_number_label=entry["entry_key"], fixture_key=fixture_key)
                db.add(match)
                created += 1
            else:
                updated += 1
            _set_schedule(match, entry)
            db.add(FixtureImportEntry(fixture_import=audit, entry_key=entry["entry_key"], kind="match", raw_entry=entry, scheduled_match=match))
    return ImportSummary(created=created, updated=updated, byes=byes)


def _registration(db: Session, stage: TournamentStage, team: dict[str, Any]) -> TeamRegistration:
    club = db.query(Club).filter_by(name=team["club"]).first()
    if not club:
        club = Club(name=team["club"])
        db.add(club)
        db.flush()
    variant = team.get("variant") or ""
    competition_team = db.query(CompetitionTeam).filter_by(club_id=club.id, stage_id=stage.id, variant_key=variant).first()
    if not competition_team:
        competition_team = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix=team.get("variant"), variant_key=variant)
        db.add(competition_team)
        db.flush()
    registration = db.query(TeamRegistration).filter_by(competition_team_id=competition_team.id, stage_id=stage.id).first()
    if not registration:
        registration = TeamRegistration(competition_team_id=competition_team.id, stage_id=stage.id)
        db.add(registration)
        db.flush()
    return registration


def _set_schedule(match: ScheduledMatch, entry: dict[str, Any]) -> None:
    for field in ("venue", "court"):
        setattr(match, field, entry.get(field))
    match.scheduled_date = _parse_date(entry["date"]) if entry.get("date") else None
    match.match_time = entry.get("time")
    result = entry.get("result")
    if match.result_status == "approved":
        return
    if result:
        match.source_home_score, match.source_away_score = result["home"], result["away"]
        match.result_status, match.status = result["status"], "played"
    else:
        match.source_home_score = match.source_away_score = None
        match.result_status, match.status = "unreported", "scheduled"


def _validate_entry(entry: Any, entry_keys: set[str]) -> None:
    if not isinstance(entry, dict) or not isinstance(entry.get("entry_key"), str) or not entry["entry_key"].strip() or entry["entry_key"] in entry_keys:
        raise FixtureValidationError("entry_key must be non-empty and unique")
    entry_keys.add(entry["entry_key"])
    if entry.get("kind") == "bye":
        _team(entry, "team")
        _text(entry, "source_text")
        return
    if entry.get("kind") != "match":
        raise FixtureValidationError("entry.kind must be match or bye")
    home, away = _team(entry, "home"), _team(entry, "away")
    if (home["club"], home.get("variant")) == (away["club"], away.get("variant")):
        raise FixtureValidationError("a match requires two distinct registrations")
    for field in ("date",):
        if entry.get(field) is not None:
            _date(entry, field)
    if entry.get("time") is not None:
        _time(entry["time"])
    result = entry.get("result")
    if result is not None:
        if not isinstance(result, dict) or result.get("status") not in RESULT_STATUSES - {"unreported"}:
            raise FixtureValidationError("result.status must be reported, approved, or disputed")
        for side in ("home", "away"):
            if not isinstance(result.get(side), int) or result[side] < 0:
                raise FixtureValidationError("result scores must be non-negative integers")


def _object(value: dict[str, Any], key: str) -> dict[str, Any]:
    if not isinstance(value.get(key), dict):
        raise FixtureValidationError(f"{key} must be an object")
    return value[key]


def _text(value: dict[str, Any], key: str) -> str:
    if not isinstance(value.get(key), str) or not value[key].strip():
        raise FixtureValidationError(f"{key} must be non-empty text")
    return value[key]


def _team(entry: dict[str, Any], key: str) -> dict[str, Any]:
    team = _object(entry, key)
    _text(team, "club")
    if "variant" in team and team["variant"] is not None and (not isinstance(team["variant"], str) or not team["variant"].strip()):
        raise FixtureValidationError("team.variant must be null or non-empty text")
    return team


def _date(value: dict[str, Any], key: str) -> None:
    try:
        _parse_date(value[key])
    except (TypeError, ValueError) as error:
        raise FixtureValidationError(f"{key} must be ISO date") from error


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.combine(_parse_date(value), time.min, tzinfo=timezone.utc)


def _time(value: str) -> None:
    try:
        time.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise FixtureValidationError("time must be ISO time") from error


def _fixture_key(stage_id: int, round_id: int, home_id: int, away_id: int, entry_key: str) -> str:
    return f"stage:{stage_id}|round:{round_id}|home:{home_id}|away:{away_id}|entry:{entry_key}"

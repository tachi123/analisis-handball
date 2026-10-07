"""Evidence validation and guarded local lifecycle for the 2026 3ªM bootstrap.

Pure evidence helpers never access the database, PDFs, or loader. Lifecycle
helpers use a supplied local session and commit only exact approved targets.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..models import Club, CompetitionTeam, FixtureImport, Season, TeamRegistration, TournamentStage

STAGES = {
    "2026_Apertura_Zona_A _Mayores_3º_División_Masculino": {
        "key": "apertura-3m-2026", "name": "Apertura Zona A 2026 3ªM",
        "category": "Mayores", "division": "3ª División", "gender": "Masculino",
    },
    "2026_Torneo_Permanencia_Mayores_3º_División_Masculino": {
        "key": "permanencia-3m-2026", "name": "Torneo Permanencia 2026 3ªM",
        "category": "Mayores", "division": "3ª División", "gender": "Masculino",
    },
}


class BootstrapEvidenceError(ValueError):
    """The reviewed corpus, manifest, or approval is not safe to use."""


class BootstrapLifecycleError(ValueError):
    """The local bootstrap cannot safely create or remove records."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def build_evidence_manifest(discovery: dict[str, Any], bootstrap: dict[str, Any]) -> dict[str, Any]:
    """Build deterministic, per-PDF evidence without inferring team identities."""
    _validate_bootstrap(bootstrap)
    records = discovery.get("records")
    if not isinstance(records, list):
        raise BootstrapEvidenceError("discovery records must be a list")
    if sha256(discovery) != bootstrap["discovery_manifest_sha256"]:
        raise BootstrapEvidenceError("bootstrap manifest is not bound to this discovery manifest")

    seen_paths, seen_shas, by_stage = set(), set(), defaultdict(list)
    for record in records:
        if not isinstance(record, dict):
            raise BootstrapEvidenceError("discovery record must be an object")
        path, source_sha = record.get("source_path"), record.get("sha256")
        root = path.split("/", 1)[0] if isinstance(path, str) else None
        if root not in STAGES or not _sha(source_sha) or path in seen_paths or source_sha in seen_shas:
            raise BootstrapEvidenceError("discovery must contain unique canonical 3ªM source paths and SHA-256 values")
        aliases = record.get("duplicate_aliases", [])
        if not isinstance(aliases, list) or any(not isinstance(alias, str) or alias in seen_paths for alias in aliases):
            raise BootstrapEvidenceError("discovery aliases must be distinct source paths")
        seen_paths.update((path, *aliases)); seen_shas.add(source_sha)
        labels = _labels(record)
        by_stage[root].append({"sha256": source_sha, "source_path": path, "source_aliases": sorted(aliases), "labels": labels})

    if len(seen_shas) != 136 or len(seen_paths) != 138:
        raise BootstrapEvidenceError("discovery must contain exactly 136 canonical PDFs and 138 source paths")
    aliases = bootstrap["aliases"]
    for stage_root, stage in STAGES.items():
        observed = {label for fixture in by_stage[stage_root] for label in fixture["labels"]}
        approved = {item["source_label"] for item in aliases if stage["key"] in item["stage_keys"]}
        if observed != approved:
            raise BootstrapEvidenceError(f"aliases must exactly cover observed labels for {stage['key']}")

    stages = []
    for root, stage in STAGES.items():
        fixtures = sorted(by_stage[root], key=lambda item: (item["sha256"], item["source_path"]))
        stages.append({**stage, "fixtures": fixtures, "fixture_evidence_sha256": sha256(fixtures)})
    return {"schema_version": 1, "bootstrap_manifest_sha256": sha256(bootstrap),
            "discovery_manifest_sha256": bootstrap["discovery_manifest_sha256"],
            "canonical_pdf_count": 136, "source_path_count": 138, "stages": stages}


def dry_run(bootstrap: dict[str, Any], discovery: dict[str, Any]) -> dict[str, Any]:
    """Return validated planned evidence only; no database or loader work occurs."""
    evidence = build_evidence_manifest(discovery, bootstrap)
    return {"mode": "dry-run", "approval_required": True, "evidence": evidence}


def validate_approval_evidence(
    bootstrap: dict[str, Any],
    discovery: dict[str, Any],
    mapping: dict[str, Any],
    report: dict[str, Any],
    approval: dict[str, Any],
    *,
    reconciliation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reject approval unless it binds the exact reviewed target identities."""
    evidence = build_evidence_manifest(discovery, bootstrap)
    if reconciliation is not None and reconciliation != evidence:
        raise BootstrapEvidenceError("reconciliation report is not the canonical report for this corpus")
    expected_targets = _validate_report(bootstrap, report)
    expected_mappings = _validate_mapping(bootstrap, mapping, expected_targets)
    if (not isinstance(approval, dict) or approval.get("schema_version") != 2
            or approval.get("approval_required") is not True
            or approval.get("status") != "approved"
            or not isinstance(approval.get("approver"), str) or not approval["approver"].strip()):
        raise BootstrapEvidenceError("approval must be explicitly approved by a named approver")
    bindings = {
        "bootstrap_manifest_sha256": sha256(bootstrap),
        "mapping_sha256": sha256(mapping),
        "reconciliation_report_sha256": sha256(evidence),
        "bootstrap_report_sha256": sha256(report),
    }
    if any(approval.get(key) != value for key, value in bindings.items()):
        raise BootstrapEvidenceError("approval evidence hashes do not match the current corpus")
    expected_stages = [{"key": key, "id": target["id"]} for key, target in expected_targets.items()]
    if approval.get("stages") != expected_stages:
        raise BootstrapEvidenceError("approval target stages do not exactly match the bootstrap report")
    if approval.get("mappings") != expected_mappings:
        raise BootstrapEvidenceError("approval mappings do not exactly match the approved source-label targets")
    return evidence


def _validate_report(bootstrap: dict[str, Any], report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if (not isinstance(report, dict) or report.get("schema_version") != 2
            or report.get("bootstrap_manifest_sha256") != sha256(bootstrap)
            or not isinstance(report.get("stages"), list)):
        raise BootstrapEvidenceError("bootstrap report must be schema version 2 and bind the bootstrap manifest")
    expected = defaultdict(set)
    for alias in bootstrap["aliases"]:
        for stage_key in alias["stage_keys"]:
            expected[stage_key].add((alias["club"], alias["variant"]))
    targets: dict[str, dict[str, Any]] = {}
    stage_ids, competition_team_ids = set(), set()
    for stage in report["stages"]:
        if (not isinstance(stage, dict) or stage.get("key") in targets
                or not isinstance(stage.get("id"), int) or stage["id"] <= 0
                or stage["id"] in stage_ids):
            raise BootstrapEvidenceError("bootstrap report must contain distinct positive target-stage IDs")
        stage_ids.add(stage["id"])
        teams = stage.get("teams")
        if not isinstance(teams, list):
            raise BootstrapEvidenceError("bootstrap report teams must be a list")
        target_teams = {(team.get("club"), team.get("variant")): team.get("competition_team_id") for team in teams if isinstance(team, dict)}
        if (len(target_teams) != len(teams) or set(target_teams) != expected[stage["key"]]
                or any(not isinstance(team_id, int) or team_id <= 0 for team_id in target_teams.values())):
            raise BootstrapEvidenceError("bootstrap report teams must exactly match the stage-scoped manifest targets")
        # Validate external_code presence
        if any(not team.get("external_code") for team in teams if isinstance(team, dict)):
            raise BootstrapEvidenceError("bootstrap report teams must include external_code")
        target_team_ids = set(target_teams.values())
        if (len(target_team_ids) != len(target_teams)
                or competition_team_ids.intersection(target_team_ids)):
            raise BootstrapEvidenceError("bootstrap report must not reuse CompetitionTeam IDs across report targets")
        competition_team_ids.update(target_team_ids)
        targets[stage["key"]] = {"id": stage["id"], "teams": target_teams}
    if list(targets) != [stage["key"] for stage in STAGES.values()]:
        raise BootstrapEvidenceError("bootstrap report must contain exactly the two required target stages")
    return targets


def _validate_mapping(
    bootstrap: dict[str, Any], mapping: dict[str, Any], targets: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if (not isinstance(mapping, dict) or mapping.get("schema_version") != 2
            or mapping.get("bootstrap_manifest_sha256") != sha256(bootstrap)
            or not isinstance(mapping.get("mappings"), list)):
        raise BootstrapEvidenceError("mapping must be schema version 2 and bind the bootstrap manifest")
    expected = []
    for alias in bootstrap["aliases"]:
        for stage_key in alias["stage_keys"]:
            external_code = alias.get("external_codes", {}).get(stage_key)
            if not external_code:
                raise BootstrapEvidenceError("bootstrap manifest alias must declare external_code for stage")
            expected.append({"source_label": alias["source_label"], "stage_key": stage_key,
                             "external_code": external_code})
    expected.sort(key=lambda item: (item["stage_key"], item["source_label"]))
    if mapping["mappings"] != expected:
        raise BootstrapEvidenceError("mapping must exactly cover approved source labels and target external_codes")
    return expected


def _validate_bootstrap(bootstrap: dict[str, Any]) -> None:
    if not isinstance(bootstrap, dict) or bootstrap.get("schema_version") != 1 or not _sha(bootstrap.get("discovery_manifest_sha256")):
        raise BootstrapEvidenceError("bootstrap manifest must be schema version 1 and bind a discovery SHA-256")
    aliases = bootstrap.get("aliases")
    if not isinstance(aliases, list) or not aliases:
        raise BootstrapEvidenceError("bootstrap manifest aliases are required")
    labels = set()
    for alias in aliases:
        if not isinstance(alias, dict) or not isinstance(alias.get("source_label"), str) or not alias["source_label"].strip() or alias["source_label"] in labels:
            raise BootstrapEvidenceError("aliases must have unique exact source labels")
        labels.add(alias["source_label"])
        if not isinstance(alias.get("club"), str) or not alias["club"].strip() or alias.get("variant") not in (None, "B", "C", "D"):
            raise BootstrapEvidenceError("aliases must retain an exact club and null, B, C, or D variant")
        if not isinstance(alias.get("stage_keys"), list) or not alias["stage_keys"] or any(key not in {stage["key"] for stage in STAGES.values()} for key in alias["stage_keys"]):
            raise BootstrapEvidenceError("aliases must declare only known stage keys")


def _labels(record: dict[str, Any]) -> list[str]:
    fields = record.get("fields", {})
    values = [fields.get(side, {}).get("value") for side in ("home_name", "away_name")]
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise BootstrapEvidenceError("every canonical PDF must retain both recovered labels")
    return values


def _sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def bootstrap_competition(
    db: Session,
    bootstrap: dict[str, Any],
    discovery: dict[str, Any],
    mapping: dict[str, Any],
    reconciliation: dict[str, Any],
    report: dict[str, Any],
    approval: dict[str, Any] | None,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Commit only raw evidence that was fully validated before any DB mutation."""
    evidence = validate_approval_evidence(bootstrap, discovery, mapping, report, approval, reconciliation=reconciliation)
    transaction = db.begin_nested() if db.in_transaction() else db.begin()
    try:
        season, season_created = _season(db)
        stages, created = _provision_targets(db, bootstrap, season, mapping)
        staged_report = _report(bootstrap, stages)
        if staged_report != report:
            raise BootstrapLifecycleError("staged target IDs do not exactly match the approved bootstrap report")
        audits = _audits(db, bootstrap, stages, {"season_ids": [season.id] if season_created else [], **created})
        audit_ids = [audit.id for audit in audits]
        for audit in audits:
            audit.payload = {**audit.payload, "batch_audit_ids": audit_ids}
        if dry_run:
            transaction.rollback()
        else:
            transaction.commit()
        return staged_report
    except Exception:
        transaction.rollback()
        raise


def rehearse_competition(db: Session, bootstrap: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    """Return the target ID report from a rolled-back local transaction."""
    _validate_bootstrap(bootstrap)
    transaction = db.begin_nested() if db.in_transaction() else db.begin()
    try:
        season, _ = _season(db)
        stages, _ = _provision_targets(db, bootstrap, season, mapping)
        return _report(bootstrap, stages)
    finally:
        transaction.rollback()


def rollback_competition(db: Session, audit_id: int, approval: dict[str, Any] | None) -> None:
    """Remove only rows listed by an approved bootstrap audit, atomically."""
    audit = db.get(FixtureImport, audit_id)
    if not audit or audit.source_label != "official-3m-bootstrap:v1":
        raise BootstrapLifecycleError("bootstrap audit record was not found")
    payload = audit.payload
    _require_approval_shape_from_hash(payload.get("bootstrap_manifest_sha256"), approval)
    owned, audit_ids = payload.get("owned"), payload.get("batch_audit_ids")
    if not isinstance(owned, dict) or not isinstance(audit_ids, list) or audit_id not in audit_ids:
        raise BootstrapLifecycleError("bootstrap audit record is incomplete")
    transaction = db.begin_nested() if db.in_transaction() else db.begin()
    try:
        stage_ids = owned.get("stage_ids", [])
        for stage_id in stage_ids:
            stage = db.get(TournamentStage, stage_id)
            if not stage or stage.scheduled_matches or stage.rounds:
                raise BootstrapLifecycleError("bootstrap stages have fixture activity and cannot be rolled back")
            if any(item.id not in audit_ids for item in stage.fixture_imports):
                raise BootstrapLifecycleError("bootstrap stages have non-bootstrap imports and cannot be rolled back")
        for registration_id in owned.get("registration_ids", []):
            registration = db.get(TeamRegistration, registration_id)
            if registration and registration.roster:
                raise BootstrapLifecycleError("bootstrap registrations have roster activity and cannot be rolled back")
        for registration_id in owned.get("registration_ids", []):
            registration = db.get(TeamRegistration, registration_id)
            if registration:
                db.delete(registration)
        for team_id in owned.get("competition_team_ids", []):
            team = db.get(CompetitionTeam, team_id)
            if team:
                db.delete(team)
        for owned_audit_id in audit_ids:
            owned_audit = db.get(FixtureImport, owned_audit_id)
            if owned_audit:
                db.delete(owned_audit)
        for stage_id in stage_ids:
            stage = db.get(TournamentStage, stage_id)
            if stage:
                db.delete(stage)
        db.flush()
        for club_id in owned.get("club_ids", []):
            club = db.get(Club, club_id)
            if club and not club.competition_teams:
                db.delete(club)
        for season_id in owned.get("season_ids", []):
            season = db.get(Season, season_id)
            if season and not season.stages:
                db.delete(season)
        transaction.commit()
    except Exception:
        transaction.rollback()
        raise


def _require_approval_shape_from_hash(manifest_hash: Any, approval: dict[str, Any] | None) -> None:
    if (not isinstance(approval, dict) or approval.get("schema_version") not in (1, 2)
            or approval.get("approval_required") is not True or approval.get("status") != "approved"
            or not isinstance(approval.get("approver"), str) or not approval["approver"].strip()
            or approval.get("bootstrap_manifest_sha256") != manifest_hash
            or any(not _sha(approval.get(key)) for key in ("mapping_sha256", "reconciliation_report_sha256", "bootstrap_report_sha256"))):
        raise BootstrapLifecycleError("an explicit current maintainer approval is required")


def _season(db: Session) -> tuple[Season, bool]:
    season = db.query(Season).filter_by(year=2026).one_or_none()
    if season:
        return season, False
    season = Season(year=2026)
    db.add(season)
    db.flush()
    return season, True


def _provision_targets(db: Session, bootstrap: dict[str, Any], season: Season, mapping: dict[str, Any]) -> tuple[dict[str, TournamentStage], dict[str, list[int]]]:
    created = {"stage_ids": [], "club_ids": [], "competition_team_ids": [], "registration_ids": []}
    stages: dict[str, TournamentStage] = {}
    for stage in STAGES.values():
        target = db.query(TournamentStage).filter_by(season_id=season.id, name=stage["name"]).one_or_none()
        if target and any(getattr(target, field) != stage[field] for field in ("category", "division", "gender")):
            raise BootstrapLifecycleError("existing target stage conflicts with the exact 2026 3ªM definition")
        if not target:
            target = TournamentStage(season_id=season.id, **{field: stage[field] for field in ("name", "category", "division", "gender")})
            db.add(target); db.flush(); created["stage_ids"].append(target.id)
        stages[stage["key"]] = target
    # Deduplicate aliases by (club, variant, stage) — one CompetitionTeam per unique combination
    seen = set()
    unique_aliases = []
    for alias in bootstrap["aliases"]:
        for stage_key in alias["stage_keys"]:
            key = (alias["club"], alias["variant"], stage_key)
            if key not in seen:
                seen.add(key)
                unique_aliases.append({"club": alias["club"], "variant": alias["variant"], "stage_key": stage_key})
    for item in unique_aliases:
        target = stages[item["stage_key"]]
        club = db.query(Club).filter_by(name=item["club"]).one_or_none()
        if not club:
            club = Club(name=item["club"]); db.add(club); db.flush(); created["club_ids"].append(club.id)
        variant = item["variant"] or ""
        team = db.query(CompetitionTeam).filter_by(club_id=club.id, stage_id=target.id, variant_key=variant).one_or_none()
        if not team:
            team = CompetitionTeam(club_id=club.id, stage_id=target.id, suffix=item["variant"], variant_key=variant)
            db.add(team); db.flush(); created["competition_team_ids"].append(team.id)
        elif team.suffix != item["variant"]:
            raise BootstrapLifecycleError("existing CompetitionTeam conflicts with the exact manifest variant")
        registration = db.query(TeamRegistration).filter_by(competition_team_id=team.id, stage_id=target.id).one_or_none()
        if not registration:
            registration = TeamRegistration(competition_team_id=team.id, stage_id=target.id)
            db.add(registration); db.flush(); created["registration_ids"].append(registration.id)
    # Second pass: set external_code from mapping — iterate unique teams, not aliases
    # Build (club, variant, stage_key) -> external_code from manifest external_codes
    team_ext_codes: dict[tuple[str, str | None, str], str] = {}
    for alias in bootstrap["aliases"]:
        for stage_key in alias["stage_keys"]:
            key = (alias["club"], alias["variant"], stage_key)
            ext_code = alias.get("external_codes", {}).get(stage_key)
            if ext_code and key not in team_ext_codes:
                team_ext_codes[key] = ext_code
    with db.no_autoflush:
        for (club_name, variant, stage_key), ext_code in team_ext_codes.items():
            target = stages[stage_key]
            club = db.query(Club).filter_by(name=club_name).one()
            team = db.query(CompetitionTeam).filter_by(club_id=club.id, stage_id=target.id, variant_key=variant or "").one()
            if team.external_code != ext_code:
                team.external_code = ext_code
    db.flush()
    return stages, created


def _report(bootstrap: dict[str, Any], stages: dict[str, TournamentStage]) -> dict[str, Any]:
    result = {"schema_version": 2, "bootstrap_manifest_sha256": sha256(bootstrap), "stages": []}
    for stage in STAGES.values():
        target = stages[stage["key"]]
        teams = []
        for club, variant in sorted({(item["club"], item["variant"]) for item in bootstrap["aliases"] if stage["key"] in item["stage_keys"]}):
            team = next(team for team in target.competition_teams if team.club.name == club and team.suffix == variant)
            registration = next(item for item in team.registrations if item.stage_id == target.id)
            teams.append({"club": club, "variant": variant, "club_id": team.club_id, "competition_team_id": team.id, "registration_id": registration.id, "external_code": team.external_code})
        result["stages"].append({"key": stage["key"], "id": target.id, "teams": teams})
    return result


def _audits(db: Session, bootstrap: dict[str, Any], stages: dict[str, TournamentStage], owned: dict[str, list[int]]) -> list[FixtureImport]:
    audits = []
    manifest_hash = sha256(bootstrap)
    for stage in stages.values():
        source_hash = hashlib.sha256(f"official-3m-bootstrap:{manifest_hash}:{stage.id}".encode()).hexdigest()
        audit = db.query(FixtureImport).filter_by(source_sha256=source_hash).one_or_none()
        if not audit:
            audit = FixtureImport(stage_id=stage.id, source_label="official-3m-bootstrap:v1", captured_at=datetime.now(timezone.utc), source_sha256=source_hash, payload={"bootstrap_manifest_sha256": manifest_hash, "owned": owned})
            db.add(audit)
        audits.append(audit)
    db.flush()
    return audits

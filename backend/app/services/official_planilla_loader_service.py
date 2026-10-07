"""Approval-gated import of local planilla evidence; it never uploads PDFs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session, joinedload

from ..models import FixtureImport, Match, OfficialBatchRun, OfficialSnapshot, OfficialSnapshotPlayer, ScheduledMatch, Team
from .official_competition_bootstrap_service import sha256 as bootstrap_sha256, validate_approval_evidence
from .fixture_seeder import import_fixture
from .pdf_service import PDFParseError, PDFService


class ApprovalError(ValueError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class LoadReport:
    batch_run_id: int | None
    created: int
    reused: int
    skipped: list[dict[str, str]]
    rejected: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"batch_run_id": self.batch_run_id, "created": self.created, "reused": self.reused,
                "skipped": self.skipped, "rejected": self.rejected}


def load_approved_planillas(db: Session, derived_path: Path, approval_path: Path, *, source_root: Path | None = None,
                            manifest_path: Path | None = None, mapping_path: Path | None = None,
                            bootstrap_path: Path | None = None, bootstrap_mapping_path: Path | None = None,
                            reconciliation_path: Path | None = None, bootstrap_report_path: Path | None = None,
                            dry_run: bool = False) -> LoadReport:
    """Load exact approved derived JSON and leave the local source corpus untouched."""
    derived_bytes = derived_path.read_bytes()
    derived = _json_object(derived_bytes, "derived")
    derived_sha = sha256_bytes(derived_bytes)
    try:
        required = (bootstrap_path, bootstrap_mapping_path, reconciliation_path, bootstrap_report_path, manifest_path)
        if any(path is None for path in required):
            raise ApprovalError("bootstrap manifest, mapping, reconciliation, report, and discovery manifest are required")
        approval = _json_object(approval_path.read_bytes(), "approval")
        _validate_approval(approval, derived, derived_sha, manifest_path, mapping_path)
        bootstrap, bootstrap_mapping, reconciliation, bootstrap_report = (
            _json_object(path.read_bytes(), label) for path, label in (
                (bootstrap_path, "bootstrap manifest"), (bootstrap_mapping_path, "bootstrap mapping"),
                (reconciliation_path, "reconciliation"), (bootstrap_report_path, "bootstrap report")))
        validate_approval_evidence(bootstrap, _json_object(manifest_path.read_bytes(), "manifest"), bootstrap_mapping,
                                   bootstrap_report, _pre_derivation_approval(approval), reconciliation=reconciliation)
        _require_bootstrap_audits(db, bootstrap, bootstrap_report)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return _reject(db, derived, derived_sha, str(error))

    existing = db.query(OfficialBatchRun).filter_by(derived_sha256=derived_sha, status="completed").first()
    if existing:
        return LoadReport(existing.id, 0, len(existing.report.get("linked", [])), [], None)
    root = (source_root or derived_path.parent.parent).resolve()
    try:
        for fixture in derived["fixtures"]:
            # Derivation emits both approved stages, including an empty stage when
            # the selected corpus contains evidence for only one of them.
            if fixture.get("rounds"):
                import_fixture(db, fixture)
        batch = OfficialBatchRun(manifest_sha256=derived["manifest_sha256"], derived_sha256=derived_sha,
                                 mapping_sha256=derived.get("mapping_sha256"), status="loading", report={})
        db.add(batch)
        db.flush()
        created, reused, skipped, linked = 0, 0, [], []
        for fixture in derived["fixtures"]:
            for entry in _entries(fixture):
                outcome = _link_entry(db, batch, entry, root)
                if outcome == "created":
                    created += 1; linked.append(entry["fixture_key"])
                elif outcome == "reused":
                    reused += 1; linked.append(entry["fixture_key"])
                else:
                    skipped.append({"fixture_key": entry["fixture_key"], "reason": outcome})
        batch.status, batch.report = "completed", {"created": created, "reused": reused, "linked": linked, "skipped": skipped}
        if dry_run:
            db.rollback()
            return LoadReport(None, created, reused, skipped)
        db.commit()
        return LoadReport(batch.id, created, reused, skipped)
    except Exception:
        db.rollback()
        raise


def rollback_batch(db: Session, batch_run_id: int) -> None:
    """Remove only evidence and analysis matches owned by one completed batch."""
    batch = db.get(OfficialBatchRun, batch_run_id)
    if batch is None:
        raise ValueError("official batch run does not exist")
    snapshots = db.query(OfficialSnapshot).filter_by(batch_run_id=batch.id).all()
    for snapshot in snapshots:
        db.delete(db.get(Match, snapshot.match_id))
    batch.status, batch.rolled_back_at = "rolled_back", datetime.now(timezone.utc)
    db.commit()


def _validate_approval(approval: dict[str, Any], derived: dict[str, Any], derived_sha: str,
                       manifest_path: Path | None, mapping_path: Path | None) -> None:
    if approval.get("status") != "completed" or not isinstance(approval.get("approver"), str) or not approval["approver"].strip():
        raise ApprovalError("approval must be freshly completed by a named approver")
    if approval.get("derived_sha256") != derived_sha:
        raise ApprovalError("approval derived_sha256 does not match derived-fixtures.json")
    if approval.get("manifest_sha256") != derived.get("manifest_sha256"):
        raise ApprovalError("approval manifest_sha256 does not match derived-fixtures.json")
    if approval.get("mapping_sha256") not in (None, derived.get("mapping_sha256")):
        raise ApprovalError("approval mapping_sha256 does not match derived-fixtures.json")
    if not isinstance(derived.get("fixtures"), list):
        raise ApprovalError("derived fixtures must be a list")
    if approval.get("pre_derivation_approval_sha256") != derived.get("bootstrap_approval_sha256"):
        raise ApprovalError("completed approval is not bound to the pre-derivation approval")
    for label, path, expected in (
        ("manifest", manifest_path, derived.get("manifest_sha256")),
        ("mapping", mapping_path, derived.get("mapping_sha256")),
    ):
        if path is not None and sha256_bytes(_canonical_json_file(path, label)) != expected:
            raise ApprovalError(f"{label} does not match derived-fixtures.json")


def _pre_derivation_approval(approval: dict[str, Any]) -> dict[str, Any]:
    value = {key: value for key, value in approval.items() if key not in {
        "status", "derived_sha256", "pre_derivation_approval_sha256", "completed_at",
        "manifest_sha256"}}
    value["status"] = "approved"
    if bootstrap_sha256(value) != approval.get("pre_derivation_approval_sha256"):
        raise ApprovalError("completed approval pre-derivation binding is stale")
    return value


def _require_bootstrap_audits(db: Session, bootstrap: dict[str, Any], report: dict[str, Any]) -> None:
    manifest_hash = bootstrap_sha256(bootstrap)
    audited = {item.stage_id for item in db.query(FixtureImport).filter_by(source_label="official-3m-bootstrap:v1").all()
               if item.payload.get("bootstrap_manifest_sha256") == manifest_hash}
    if audited != {stage["id"] for stage in report["stages"]}:
        raise ApprovalError("bootstrap completion audits do not exactly match approved target stages")


def _reject(db: Session, derived: dict[str, Any], derived_sha: str, reason: str) -> LoadReport:
    batch = OfficialBatchRun(manifest_sha256=str(derived.get("manifest_sha256", "")), derived_sha256=derived_sha,
                             mapping_sha256=derived.get("mapping_sha256"), status="rejected", report={}, rejection_reason=reason)
    db.add(batch); db.commit()
    return LoadReport(batch.id, 0, 0, [], reason)


def _entries(fixture: dict[str, Any]):
    for round_ in fixture.get("rounds", []):
        for entry in round_.get("entries", []):
            if entry.get("kind") == "match" and entry.get("planilla"):
                yield entry


def _link_entry(db: Session, batch: OfficialBatchRun, entry: dict[str, Any], root: Path) -> str:
    fixture = db.query(ScheduledMatch).options(
        joinedload(ScheduledMatch.home_registration), joinedload(ScheduledMatch.away_registration),
        joinedload(ScheduledMatch.analysis_match),
    ).filter_by(fixture_key=entry["fixture_key"]).one()
    if fixture.analysis_match and fixture.analysis_match.official_snapshots:
        return "reused"
    planilla = entry["planilla"]
    try:
        path = _source_path(root, planilla["source_path"])
        preview = PDFService.preview_femebal_sheet(path.read_bytes(), path.name, "application/pdf")
    except PDFParseError:
        return "skipped_parse_error"
    except (KeyError, OSError, ValueError) as error:
        return f"invalid_source:{error}"
    provenance = preview["provenance"]
    expected = {"sha256": planilla.get("sha256"), "page_count": planilla.get("page_count"), "size_bytes": planilla.get("size")}
    if any(expected[key] is not None and provenance[key] != expected[key] for key in expected):
        return "source_provenance_mismatch"
    if not _teams_match(fixture, preview) or not _scores_match(entry, preview):
        return "sheet_fixture_mismatch"
    home, away = _legacy_teams(db, entry)
    info = preview["match_info"]
    match = Match(date=fixture.scheduled_date or date.fromisoformat(info["date"]), home_team_id=home.id, away_team_id=away.id,
                  home_score=info["home_score"], away_score=info["away_score"], scheduled_match_id=fixture.id,
                  origin="fixture")
    db.add(match); db.flush()
    snapshot = OfficialSnapshot(id=str(uuid4()), match_id=match.id, batch_run_id=batch.id, is_confirmed=True,
        source_path=str(path), confirmed_date=match.date, home_team_name=preview["home_team"]["name"],
        away_team_name=preview["away_team"]["name"], home_score=info["home_score"], away_score=info["away_score"],
        **{f"source_{key}": value for key, value in provenance.items()})
    db.add(snapshot)
    for side, parsed in (("home", preview["home_team"]["players"]), ("away", preview["away_team"]["players"])):
        for player in parsed:
            db.add(OfficialSnapshotPlayer(snapshot_id=snapshot.id, side=side, name=player["name"], jersey_number=player["number"],
                official_goals=player["goals"], official_yellow=player["yellow"], official_2min=player["two_min"], official_red=player["red"], official_blue=player["blue"]))
    fixture.source_home_score, fixture.source_away_score, fixture.result_status, fixture.status = info["home_score"], info["away_score"], "approved", "played"
    return "created"


def _source_path(root: Path, source_path: str) -> Path:
    path = (root / source_path).resolve()
    if root not in path.parents or not path.is_file():
        raise ValueError("source path is outside corpus or missing")
    return path


def _teams_match(fixture: ScheduledMatch, preview: dict[str, Any]) -> bool:
    return all(PDFService._compatibility(getattr(fixture, f"{side}_registration"), preview[f"{side}_team"]["name"])["status"] == "compatible" for side in ("home", "away"))


def _scores_match(entry: dict[str, Any], preview: dict[str, Any]) -> bool:
    result, info = entry.get("result", {}), preview["match_info"]
    return (result.get("home"), result.get("away")) == (info.get("home_score"), info.get("away_score"))


def _legacy_teams(db: Session, entry: dict[str, Any]) -> tuple[Team, Team]:
    result = []
    for side in ("home", "away"):
        data = entry[side]; name = " ".join(filter(None, (data["club"], data.get("variant"))))
        team = db.query(Team).filter_by(name=name).first()
        if not team:
            team = Team(name=name); db.add(team); db.flush()
        result.append(team)
    return tuple(result)


def _json_object(raw: bytes, label: str) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _canonical_json_file(path: Path, label: str) -> bytes:
    """Hash reviewed JSON with the derivation command's canonical representation."""
    return json.dumps(_json_object(path.read_bytes(), label), ensure_ascii=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"

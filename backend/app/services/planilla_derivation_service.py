"""Pure, deterministic derivation of curated fixtures from planilla discovery data."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
import re
from typing import Any

from .official_competition_bootstrap_service import (
    STAGES as BOOTSTRAP_STAGES,
    sha256 as bootstrap_sha256,
    validate_approval_evidence,
)


STAGES = {
    "2026_Apertura_Zona_A _Mayores_3º_División_Masculino": {
        "name": "Apertura Zona A 2026 3ªM",
        "category": "Mayores",
        "division": "3ª División",
        "gender": "Masculino",
    },
    "2026_Torneo_Permanencia_Mayores_3º_División_Masculino": {
        "name": "Torneo Permanencia 2026 3ªM",
        "category": "Mayores",
        "division": "3ª División",
        "gender": "Masculino",
    },
}


def canonical_json(value: Any) -> str:
    """Serialize an artifact as canonical UTF-8 JSON with a trailing LF."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def suggest_team_mapping(manifest: dict[str, Any]) -> dict[str, Any]:
    """Create deterministic, analyst-reviewable exact-label mapping suggestions."""
    labels = {
        label
        for record in manifest.get("records", [])
        if _stage_for(record)
        for label in (_field(_fields(record), "home_name"), _field(_fields(record), "away_name"))
        if isinstance(label, str) and label.strip()
    }
    return {
        "schema_version": 1,
        "manifest_sha256": sha256_text(canonical_json(manifest)),
        "labels": {label: _suggest_team(label) for label in sorted(labels)},
    }


def derive_fixtures(manifest: dict[str, Any], mapping: dict[str, Any], rules: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return seeder-compatible stage payloads and an unresolved-only report.

    Labels are deliberately never normalized: a source label must be present as
    an exact key in the reviewed mapping before its sheet can become a fixture.
    """
    manifest_json = canonical_json(manifest)
    manifest_sha = sha256_text(manifest_json)
    mapping_sha = sha256_text(canonical_json(mapping))
    mapping = _derivation_mapping(mapping, manifest, manifest_sha)
    _validate_rules(rules)
    entries: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unresolved = []
    sequence: Counter[str] = Counter()

    for record in sorted(manifest.get("records", []), key=lambda item: (item.get("sha256", ""), item.get("source_path", ""))):
        stage = _stage_for(record)
        if not stage:
            continue
        sha = record["sha256"]
        sequence[sha] += 1
        fields = _fields(record)
        labels = {side: _field(fields, f"{side}_name") for side in ("home", "away")}
        mapped, reasons = {}, []
        for side, label in labels.items():
            team = mapping["labels"].get(label) if isinstance(label, str) else None
            if not _valid_team(team):
                reasons.append(f"{side}_team_unresolved")
            else:
                mapped[side] = team
        date = _field(fields, "date")
        scores = {side: _field(fields, f"{side}_score") for side in ("home", "away")}
        if not isinstance(date, str) or not all(isinstance(score, int) and not isinstance(score, bool) and score >= 0 for score in scores.values()):
            reasons.append("missing_or_invalid_match_facts")
        if reasons or len(mapped) != 2:
            unresolved.append(_unresolved(record, labels, reasons, mapped, stage, scores, date, sequence[sha], entries))
            continue
        entries[stage["name"]].append(_entry(record, mapped, date, scores, sequence[sha]))

    reconciled, unresolved = _reconcile(unresolved, entries)
    for entry in reconciled:
        entries[entry.pop("_stage")].append(entry)

    fixtures = []
    for source_stage, stage in STAGES.items():
        stage_entries = entries[stage["name"]]
        by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in stage_entries:
            by_date[entry["date"]].append(entry)
        rounds = [{"number": number, "entries": sorted(by_date[date], key=lambda entry: entry["entry_key"])} for number, date in enumerate(sorted(by_date), 1)]
        fixtures.append({"source": {"label": "official planilla derivation", "captured_at": rules["captured_at"]}, "stage": {"season": 2026, **stage}, "rounds": rounds})
    derived = {"schema_version": 1, "manifest_sha256": manifest_sha, "mapping_sha256": mapping_sha, "fixtures": fixtures}
    report = {"schema_version": 1, "manifest_sha256": manifest_sha, "unresolved": sorted(unresolved, key=lambda item: (item["sha256"] or "", item["source_path"] or "")), "counts": {"fixtures_by_stage": {fixture["stage"]["name"]: sum(len(round_["entries"]) for round_ in fixture["rounds"]) for fixture in fixtures}, "rounds_by_stage": {fixture["stage"]["name"]: len(fixture["rounds"]) for fixture in fixtures}, "resolved_by_mapping": sum(len(items) for items in entries.values()) - len(reconciled), "reconciled": len(reconciled), "unresolved": len(unresolved)}}
    return derived, report


def derive_approved_fixtures(
    db: Any, manifest: dict[str, Any], mapping: dict[str, Any], rules: dict[str, Any],
    bootstrap: dict[str, Any], bootstrap_mapping: dict[str, Any], reconciliation: dict[str, Any],
    bootstrap_report: dict[str, Any], approval: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive only from a current approved bootstrap and its persisted audits."""
    validate_approval_evidence(bootstrap, manifest, bootstrap_mapping, bootstrap_report, approval,
                               reconciliation=reconciliation)
    _require_bootstrap_audits(db, bootstrap, bootstrap_report)
    _validate_mapping_against_bootstrap(mapping, bootstrap)
    derived, report = derive_fixtures(manifest, mapping, rules)
    derived["bootstrap_approval_sha256"] = bootstrap_sha256(approval)
    return derived, report


def _field(fields: dict[str, Any], name: str) -> Any:
    value = fields.get(name)
    return value.get("value") if isinstance(value, dict) else None


def _fields(record: dict[str, Any]) -> dict[str, Any]:
    return record.get("fields") if isinstance(record.get("fields"), dict) else {}


def _stage_for(record: dict[str, Any]) -> dict[str, str] | None:
    source_stage = str(record.get("source_path", "")).replace("\\", "/").split("/", 1)[0]
    return STAGES.get(source_stage)


def _suggest_team(label: str) -> dict[str, str | None]:
    club = re.sub(r"^(?:C\.?S\.?\s+y\s+C\.?|C\.?A\.?\s+y\s+S\.?|C\.?A\.?)\s+", "", label.strip(), flags=re.IGNORECASE)
    match = re.fullmatch(r"(.+?)\s+([A-Za-z])", club)
    return {"club": match.group(1) if match else club, "variant": match.group(2).upper() if match else None}


def _entry(record: dict[str, Any], teams: dict[str, Any], match_date: str, scores: dict[str, Any], sequence: int) -> dict[str, Any]:
    sha = record["sha256"]
    return {
        "entry_key": f"planilla:{sha[:8]}:{sequence}", "fixture_key": f"planilla:{sha[:8]}:{sequence}", "kind": "match",
        "home": teams["home"], "away": teams["away"], "date": match_date,
        "time": _field(_fields(record), "time"), "venue": _field(_fields(record), "venue"), "court": _field(_fields(record), "court"),
        "result": {"home": scores["home"], "away": scores["away"], "status": "reported"},
        "planilla": {key: record.get(key) for key in ("sha256", "source_path", "page_count")} | {"size": record.get("size"), "mtime": record.get("mtime"), "rosters": record.get("rosters", {})},
    }


def _unresolved(record: dict[str, Any], labels: dict[str, Any], reasons: list[str], mapped: dict[str, Any], stage: dict[str, str], scores: dict[str, Any], match_date: Any, sequence: int, entries: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {"sha256": record.get("sha256"), "source_path": record.get("source_path"), "labels": labels, "reasons": sorted(reasons), "_mapped": mapped, "_stage": stage["name"], "_scores": scores, "_date": match_date, "_sequence": sequence, "_record": record}


def _reconcile(unresolved: list[dict[str, Any]], entries: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    reconciled, remaining = [], []
    for item in unresolved:
        mapped, missing = item.pop("_mapped"), [side for side in ("home", "away") if side not in item["labels"] or not isinstance(item["labels"][side], str)]
        facts_valid = not any(reason == "missing_or_invalid_match_facts" for reason in item["reasons"])
        if len(missing) != 1 or not facts_valid or len(mapped) != 1:
            remaining.append(_strip_internal(item))
            continue
        labelled, inferred = ("away", "home") if missing[0] == "home" else ("home", "away")
        opposite = "home" if labelled == "away" else "away"
        candidates = [entry for entry in entries[item["_stage"]] if entry[opposite] == mapped[labelled] and entry["result"] == {"home": item["_scores"]["home"], "away": item["_scores"]["away"], "status": "reported"} and abs((date.fromisoformat(entry["date"]) - date.fromisoformat(item["_date"])).days) <= 7]
        if len(candidates) != 1:
            item["reasons"].append("reconciliation_no_candidate" if not candidates else "reconciliation_ambiguous")
            remaining.append(_strip_internal(item))
            continue
        teams = {labelled: mapped[labelled], inferred: candidates[0][inferred]}
        entry = _entry(item["_record"], teams, item["_date"], item["_scores"], item["_sequence"])
        entry["provenance"] = f"reconciled_from:{candidates[0]['planilla']['sha256'][:8]}"
        entry["_stage"] = item["_stage"]
        reconciled.append(entry)
    return reconciled, remaining


def _strip_internal(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if not key.startswith("_")}


def _valid_team(team: Any) -> bool:
    if not isinstance(team, dict) or not isinstance(team.get("club"), str) or not team["club"].strip():
        return False
    return team.get("variant") is None or (isinstance(team.get("variant"), str) and bool(team["variant"].strip()))


def _derivation_mapping(mapping: dict[str, Any], manifest: dict[str, Any], manifest_sha: str) -> dict[str, Any]:
    """Accept legacy reviewed maps and schema-v2 stage-scoped bootstrap maps."""
    if mapping.get("schema_version") == 1:
        _validate_mapping(mapping, manifest_sha)
        return mapping
    if (mapping.get("schema_version") != 2 or not isinstance(mapping.get("labels"), dict)
            or not isinstance(mapping.get("bootstrap_manifest_sha256"), str)):
        raise ValueError("mapping must be schema version 2 with exact stage-scoped labels")
    expected_labels = {
        _field(_fields(record), field) for record in manifest.get("records", []) if _stage_for(record)
        for field in ("home_name", "away_name")
    }
    labels = mapping["labels"]
    if set(labels) != expected_labels:
        raise ValueError("mapping must exactly cover every canonical source label")
    converted = {}
    for label, target in labels.items():
        if (not _valid_team(target) or not isinstance(target.get("stage_keys"), list)
                or not target["stage_keys"]):
            raise ValueError("mapping targets must retain club, variant, and stage keys")
        converted[label] = {"club": target["club"], "variant": target.get("variant")}
    for record in manifest.get("records", []):
        stage = _stage_for(record)
        if not stage:
            continue
        key = BOOTSTRAP_STAGES[str(record["source_path"]).split("/", 1)[0]]["key"]
        for field in ("home_name", "away_name"):
            label = _field(_fields(record), field)
            if key not in labels[label]["stage_keys"]:
                raise ValueError("mapping target is not approved for the source stage")
    return {"schema_version": 1, "manifest_sha256": manifest_sha, "labels": converted}


def _require_bootstrap_audits(db: Session, bootstrap: dict[str, Any], report: dict[str, Any]) -> None:
    from ..models import FixtureImport
    manifest_hash = bootstrap_sha256(bootstrap)
    audited = {
        item.stage_id for item in db.query(FixtureImport).filter_by(source_label="official-3m-bootstrap:v1").all()
        if item.payload.get("bootstrap_manifest_sha256") == manifest_hash
    }
    expected = {stage["id"] for stage in report["stages"]}
    if expected != audited:
        raise ValueError("bootstrap completion audits do not exactly match approved target stages")


def _validate_mapping_against_bootstrap(mapping: dict[str, Any], bootstrap: dict[str, Any]) -> None:
    if mapping.get("bootstrap_manifest_sha256") != bootstrap_sha256(bootstrap):
        raise ValueError("mapping is not bound to the approved bootstrap manifest")
    expected = {item["source_label"]: {key: item[key] for key in ("club", "variant", "stage_keys")}
                for item in bootstrap["aliases"]}
    if mapping.get("labels") != expected:
        raise ValueError("mapping does not exactly match approved stage-scoped bootstrap targets")


def _validate_mapping(mapping: dict[str, Any], manifest_sha: str) -> None:
    if not isinstance(mapping, dict) or mapping.get("schema_version") != 1 or mapping.get("manifest_sha256") != manifest_sha or not isinstance(mapping.get("labels"), dict):
        raise ValueError("mapping must be schema_version 1, bound to this manifest, and contain labels")


def _validate_rules(rules: dict[str, Any]) -> None:
    if not isinstance(rules, dict) or rules.get("schema_version") != 1 or not isinstance(rules.get("captured_at"), str) or rules.get("round_inference") != "ascending_unique_date":
        raise ValueError("rules must use schema_version 1 and ascending_unique_date inference")

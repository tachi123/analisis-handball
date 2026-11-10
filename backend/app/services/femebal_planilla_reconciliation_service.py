"""Build auditable, data-driven links between local FEMEBAL PDFs and fixture entries."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlparse


class ReconciliationError(ValueError):
    pass


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def sha256_json(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def build_femebal_planilla_reconciliation(manifest: dict[str, Any], fixture: dict[str, Any], *, source_stage: str) -> dict[str, Any]:
    """Match sheets only through the tracker URL that explicitly names that PDF.

    Header dates are retained as official-result evidence but deliberately do not
    participate in identity matching: FEMEBAL's tracker schedule can differ from
    the date written when the match closes.
    """
    records = [record for record in manifest.get("records", []) if _stage(record) == source_stage]
    tracker = _tracker_entries(fixture)
    by_pdf = _index_tracker_pdf(tracker)
    links, unmatched = [], []
    for record in sorted(records, key=lambda item: str(item.get("source_path", ""))):
        filename = PurePosixPath(str(record.get("source_path", ""))).name
        entry = by_pdf.get(filename)
        if entry is None:
            unmatched.append({"source_path": record.get("source_path"), "reason": "tracker_pdf_not_found"})
            continue
        tracker_scores = entry.get("result")
        scores = _scores(record)
        tracker_disagrees = (
            isinstance(tracker_scores, dict)
            and scores != {"home": tracker_scores.get("home"), "away": tracker_scores.get("away")}
        )
        links.append({
            "source_path": record["source_path"], "sha256": record["sha256"], "page_count": record.get("page_count"),
            "size": record.get("size"), "fixture_key": entry["fixture_key"],
            "tracker_match_id": entry.get("evidence", {}).get("tracker_match_id"),
            "tracker_scheduled_date": entry.get("date"), "official_planilla_date": _field(record, "date"),
            "pdf_url": _tracker_pdf_url(entry, filename),
            "tracker_score_disagrees": tracker_disagrees,
        })
    fixture_keys = [link["fixture_key"] for link in links]
    if len(fixture_keys) != len(set(fixture_keys)):
        raise ReconciliationError("one tracker fixture is linked to multiple local PDFs")
    return {
        "schema_version": 1, "source_stage": source_stage,
        "manifest_sha256": sha256_json(manifest), "fixture_sha256": sha256_json(fixture),
        "match_method": "explicit_tracker_pdf_url_filename", "links": links,
        "unmatched": unmatched,
        "counts": {"local_records": len(records), "linked": len(links), "unmatched": len(unmatched)},
    }


def _stage(record: dict[str, Any]) -> str:
    return str(record.get("source_path", "")).replace("\\", "/").split("/", 1)[0]


def _tracker_entries(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    return [entry for round_ in fixture.get("rounds", []) for entry in round_.get("entries", []) if entry.get("kind") == "match"]


def _index_tracker_pdf(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for entry in entries:
        for planilla in entry.get("evidence", {}).get("planillas", []):
            filename = PurePosixPath(urlparse(str(planilla.get("pdf_url", ""))).path).name
            if not filename:
                continue
            if filename in indexed:
                raise ReconciliationError(f"tracker PDF is linked to multiple fixtures: {filename}")
            indexed[filename] = entry
    return indexed


def _tracker_pdf_url(entry: dict[str, Any], filename: str) -> str:
    return next(str(item["pdf_url"]) for item in entry["evidence"]["planillas"]
                if PurePosixPath(urlparse(str(item.get("pdf_url", ""))).path).name == filename)


def _field(record: dict[str, Any], name: str) -> Any:
    value = (record.get("fields") or {}).get(name)
    return value.get("value") if isinstance(value, dict) else value


def _scores(record: dict[str, Any]) -> dict[str, Any]:
    return {"home": _field(record, "home_score"), "away": _field(record, "away_score")}

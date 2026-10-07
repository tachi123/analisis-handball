"""Read-only PDF discovery and byte-identical source canonicalization."""

from __future__ import annotations

import hashlib
import csv
import json
import os
import shutil
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pdfplumber


HASH_CHUNK_SIZE = 64 * 1024
SCHEMA_VERSION = 1
CSV_COLUMNS = (
    "schema_version", "sha256", "source_path", "page_count", "tournament", "venue", "court",
    "date", "time", "category", "match_number", "home_name", "away_name", "home_score",
    "away_score", "duplicate_aliases_json", "fields_json", "local_players_json",
    "visitante_players_json", "quality_flags_json", "parse_error",
)


def discover_pdf_paths(source_root: Path | str) -> list[Path]:
    """Return all PDF files below *source_root* in stable relative-path order."""
    root = Path(source_root)
    paths = [
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.casefold() == ".pdf" and "_indexed" not in path.relative_to(root).parts
    ]
    return sorted(paths, key=lambda path: _path_key(_relative_path(path, root)))


def sha256_file(path: Path | str) -> str:
    """Hash a file incrementally so discovery does not load whole PDFs in memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_planillas(
    source_root: Path | str,
    parse_sheet: Callable[[Path], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Hash and canonicalize PDFs, optionally parsing each unique source once.

    The caller supplies parsing so this service stays isolated from application
    models, database sessions, and confirmation workflows. Parser failures are
    retained per canonical source and do not stop the remaining scan.
    """
    root = Path(source_root)
    groups: dict[str, list[str]] = {}
    paths_by_relative: dict[str, Path] = {}

    for path in discover_pdf_paths(root):
        relative_path = _relative_path(path, root)
        paths_by_relative[relative_path] = path
        groups.setdefault(sha256_file(path), []).append(relative_path)

    records = []
    for sha256, paths in groups.items():
        ordered_paths = sorted(paths, key=_path_key)
        source_path, *duplicate_aliases = ordered_paths
        record: dict[str, Any] = {
            "sha256": sha256,
            "source_path": source_path,
            "duplicate_aliases": duplicate_aliases,
            "parsed": None,
            "parse_error": None,
            "page_count": 0,
        }
        try:
            record["page_count"] = _page_count(paths_by_relative[source_path])
        except Exception as error:
            record["parse_error"] = str(error)
        if parse_sheet is not None:
            try:
                record["parsed"] = parse_sheet(paths_by_relative[source_path])
            except Exception as error:
                record["parse_error"] = record["parse_error"] or str(error)
        records.append(record)

    return sorted(records, key=lambda record: (record["sha256"], _path_key(record["source_path"])))


def build_manifest(scan_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build schema-v1 review records from scanner results without mutating sources."""
    records = []
    for scan_record in scan_records:
        parsed = scan_record["parsed"] or {}
        fields = parsed.get("fields", {})
        record = {
            "schema_version": SCHEMA_VERSION,
            "sha256": scan_record["sha256"],
            "source_path": scan_record["source_path"],
            "duplicate_aliases": scan_record["duplicate_aliases"],
            "page_count": scan_record["page_count"],
            "fields": fields,
            "rosters": {
                "local": parsed.get("home_team", {}).get("players", []),
                "visitante": parsed.get("away_team", {}).get("players", []),
            },
            "parse_error": scan_record["parse_error"],
        }
        record["quality_flags"] = quality_flags(record)
        records.append(record)
    return {"schema_version": SCHEMA_VERSION, "records": sorted(records, key=_record_key)}


def quality_flags(record: dict[str, Any]) -> list[str]:
    """Return stable review flags derived solely from extracted evidence."""
    flags = []
    fields = record["fields"]
    warnings = [warning for field in fields.values() for warning in field.get("warnings", [])]
    if record["page_count"] > 1:
        flags.append("multi-page")
    if fields and any(not fields.get(field, {}).get("value") for field in ("home_name", "away_name")):
        flags.append("missing-team-label")
    if fields and not fields.get("court", {}).get("value"):
        flags.append("missing-court")
    if any("conflicting" in warning for warning in warnings):
        flags.append("conflicting-labelled-field")
    if any("encoding-degraded" in warning for warning in warnings):
        flags.append("encoding-degraded-source-text")
    if record["duplicate_aliases"]:
        flags.append("duplicate")
    if record["parse_error"]:
        flags.append("parse-error")
    return flags


def write_manifest_artifacts(manifest: dict[str, Any], output_dir: Path | str) -> tuple[Path, Path, Path]:
    """Write deterministic UTF-8 JSON, CSV, and Markdown review artifacts."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path, csv_path, report_path = output / "manifest.json", output / "manifest.csv", output / "report.md"
    json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    with csv_path.open("w", encoding="utf-8", newline="\n") as destination:
        writer = csv.DictWriter(destination, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for record in manifest["records"]:
            fields = record["fields"]
            writer.writerow({
                "schema_version": record["schema_version"], "sha256": record["sha256"],
                "source_path": record["source_path"], "page_count": record["page_count"],
                **{field: fields.get(field, {}).get("value") for field in CSV_COLUMNS[4:15]},
                "duplicate_aliases_json": _json(record["duplicate_aliases"]), "fields_json": _json(fields),
                "local_players_json": _json(record["rosters"]["local"]),
                "visitante_players_json": _json(record["rosters"]["visitante"]),
                "quality_flags_json": _json(record["quality_flags"]), "parse_error": record["parse_error"],
            })
    report_path.write_text(build_quality_report(manifest), encoding="utf-8", newline="\n")
    return json_path, csv_path, report_path


def write_browsable_index(manifest: dict[str, Any], source_root: Path | str, index_dir: Path | str) -> Path:
    """Create deterministic, non-destructive aliases for canonical PDF records.

    Alias names are presentation-only.  Every entry preserves its immutable
    source-relative path and SHA-256; duplicate source paths share the same
    target.  Existing files are accepted only when their bytes match the
    intended canonical source, preventing an accidental collision overwrite.
    """
    root, output = Path(source_root), Path(index_dir)
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    for record in sorted(manifest["records"], key=_record_key):
        alias = _browsable_name(record)
        source = root / record["source_path"]
        target = output / alias
        source_hash = sha256_file(source)
        if source_hash != record["sha256"]:
            raise ValueError(f"source SHA changed during indexing: {record['source_path']}")
        if target.exists() and sha256_file(target) != source_hash:
            raise ValueError(f"alias collision would overwrite a different PDF: {alias}")
        if not target.exists():
            try:
                os.link(source, target)
            except OSError:
                shutil.copy2(source, target)
        entries.append({
            "alias": alias,
            "source_path": record["source_path"],
            "source_aliases": [record["source_path"], *record["duplicate_aliases"]],
            "sha256": record["sha256"],
            "materialization": "hardlink-or-copy",
        })
    index = {"schema_version": 1, "entries": entries}
    index_path = output / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return index_path


def build_quality_report(manifest: dict[str, Any]) -> str:
    """Summarize canonical records and sorted affected paths for review."""
    records = manifest["records"]
    flag_paths: dict[str, list[str]] = {}
    for record in records:
        for flag in record["quality_flags"]:
            flag_paths.setdefault(flag, []).append(record["source_path"])
    sources = sum(1 + len(record["duplicate_aliases"]) for record in records)
    unresolved = sum(
        1 for record in records for field in record["fields"].values()
        if field.get("confidence") == "unresolved"
    )
    lines = ["# Planilla Discovery Report", "", "## Summary", "", f"- Sources: {sources}",
             f"- Canonical records: {len(records)}", f"- Duplicate aliases: {sources - len(records)}",
             f"- Pages: {sum(record['page_count'] for record in records)}", f"- Unresolved fields: {unresolved}",
             f"- Degraded records: {len(flag_paths.get('encoding-degraded-source-text', []))}",
             f"- Parse errors: {len(flag_paths.get('parse-error', []))}", "", "## Quality flags", ""]
    for flag in sorted(flag_paths):
        paths = sorted(flag_paths[flag], key=_path_key)
        lines.extend((f"### {flag} ({len(paths)})", *[f"- {path}" for path in paths], ""))
    return "\n".join(lines).rstrip() + "\n"


def _relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _path_key(path: str) -> tuple[str, str]:
    return path.casefold(), path


def _page_count(path: Path) -> int:
    with pdfplumber.open(path) as pdf:
        return len(pdf.pages)


def _record_key(record: dict[str, Any]) -> tuple[str, tuple[str, str]]:
    return record["sha256"], _path_key(record["source_path"])


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _browsable_name(record: dict[str, Any]) -> str:
    fields = record["fields"]
    match_number = fields.get("match_number", {}).get("value")
    try:
        round_number = f"R{int(str(match_number)):02d}"
    except (TypeError, ValueError):
        round_number = "R00"
    match_date = fields.get("date", {}).get("value") or "unknown-date"
    home = _slug(fields.get("home_name", {}).get("value") or "unknown-home")
    away = _slug(fields.get("away_name", {}).get("value") or "unknown-away")
    return f"{match_date}_{round_number}_{home}_vs_{away}__{record['sha256'][:8]}.pdf"


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii").lower()
    return "-".join(part for part in "".join(char if char.isalnum() else " " for char in normalized).split() if part) or "unknown"

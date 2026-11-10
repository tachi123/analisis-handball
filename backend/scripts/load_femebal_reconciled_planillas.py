"""Dry-run or load a reviewed FEMEBAL PDF-to-fixture reconciliation artifact."""
import argparse
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.models import FixtureImportEntry, OfficialBatchRun
from app.services.official_planilla_loader_service import _link_entry


def _document(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _entries(fixture: dict) -> dict:
    return {entry["fixture_key"]: entry for round_ in fixture.get("rounds", []) for entry in round_.get("entries", [])
            if entry.get("kind") == "match"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load only exact reviewed FEMEBAL PDF links")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--reconciliation", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run == args.execute:
        parser.error("choose exactly one of --dry-run or --execute")
    try:
        reconciliation, fixture = _document(args.reconciliation), _document(args.fixture)
        if reconciliation.get("schema_version") != 1 or reconciliation.get("unmatched") or reconciliation.get("counts", {}).get("linked") != reconciliation.get("counts", {}).get("local_records"):
            raise ValueError("reconciliation must be complete and have no unmatched sheets")
        tracker_entries = _entries(fixture)
        with sessionmaker(bind=create_engine(args.database_url))() as db:
            batch = OfficialBatchRun(manifest_sha256=reconciliation["manifest_sha256"], derived_sha256=reconciliation["fixture_sha256"], status="loading", report={})
            db.add(batch); db.flush()
            created = reused = 0
            skipped = []
            for link in reconciliation["links"]:
                tracker = tracker_entries.get(link["fixture_key"])
                if tracker is None:
                    raise ValueError(f"fixture key absent from tracker artifact: {link['fixture_key']}")
                entry = dict(tracker)
                # A tracker entry can point to a pre-existing planilla-backed
                # schedule whose immutable fixture_key predates this import.
                imported = db.query(FixtureImportEntry).filter_by(entry_key=link["fixture_key"]).one_or_none()
                if imported is None or imported.scheduled_match is None:
                    raise ValueError(f"tracker fixture is not imported into the target database: {link['fixture_key']}")
                entry["fixture_key"] = imported.scheduled_match.fixture_key
                entry["planilla"] = {key: link.get(key) for key in ("source_path", "sha256", "page_count", "size")}
                # The reviewed PDF identity is the official result evidence;
                # tracker scores are only reported values and may differ.
                outcome = _link_entry(db, batch, entry, args.source_root, [], validate_reported_score=False, validate_teams=False)
                if outcome == "created":
                    created += 1
                elif outcome == "reused":
                    reused += 1
                else:
                    skipped.append({"fixture_key": link["fixture_key"], "reason": outcome})
            report = {"created": created, "reused": reused, "skipped": skipped}
            if skipped:
                raise ValueError(f"reconciliation load has skipped sheets: {skipped}")
            if args.dry_run:
                db.rollback()
            else:
                batch.status, batch.report = "completed", report
                db.commit()
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

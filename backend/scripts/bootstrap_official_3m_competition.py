"""Safely rehearse, apply, or roll back the local 2026 3ªM bootstrap."""

import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.official_competition_bootstrap_service import (
    BootstrapLifecycleError, bootstrap_competition, rehearse_competition, rollback_competition,
    validate_approval_evidence,
)


def _local_database_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme.startswith("sqlite"):
        if value == "sqlite:///:memory:":
            raise argparse.ArgumentTypeError("an on-disk local SQLite URL is required")
        return value
    if parsed.scheme not in {"postgresql", "postgres"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise argparse.ArgumentTypeError("database URL must explicitly target a local SQLite or loopback PostgreSQL database")
    return value


def _json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise BootstrapLifecycleError(f"{path} must contain a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap approved local 2026 3ªM competition records")
    parser.add_argument("--database-url", required=True, type=_local_database_url)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--discovery", type=Path)
    parser.add_argument("--mapping", type=Path)
    parser.add_argument("--reconciliation", type=Path)
    parser.add_argument("--bootstrap-report", type=Path)
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument("--report", type=Path, help="write the executed bootstrap result only")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true", help="explicitly commit a bootstrap or rollback")
    parser.add_argument("--rollback-audit-id", type=int)
    args = parser.parse_args(argv)
    if args.dry_run == args.execute:
        parser.error("choose exactly one of --dry-run or --execute")
    if args.rollback_audit_id and args.dry_run:
        parser.error("rollback requires --execute")
    evidence_paths = (args.discovery, args.mapping, args.reconciliation, args.bootstrap_report)
    if not args.rollback_audit_id and any(path is None for path in evidence_paths):
        parser.error("bootstrap requires --discovery, --mapping, --reconciliation, and --bootstrap-report")
    if args.execute and not args.rollback_audit_id and not args.report:
        parser.error("--report is required for executed bootstrap")
    try:
        with sessionmaker(bind=create_engine(args.database_url))() as db:
            approval = _json(args.approval)
            if args.rollback_audit_id:
                rollback_competition(db, args.rollback_audit_id, approval)
                result = {"rolled_back_audit_id": args.rollback_audit_id}
            else:
                manifest = _json(args.manifest)
                discovery, mapping, reconciliation, report = (_json(path) for path in evidence_paths)
                if args.dry_run:
                    validate_approval_evidence(manifest, discovery, mapping, report, approval, reconciliation=reconciliation)
                    result = rehearse_competition(db, manifest, mapping)
                else:
                    result = bootstrap_competition(db, manifest, discovery, mapping, reconciliation, report, approval)
        if args.execute and args.report:
            args.report.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: bootstrap failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

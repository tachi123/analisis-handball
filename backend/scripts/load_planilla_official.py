"""Load an explicitly approved local planilla corpus into one explicit database."""

import argparse
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.official_planilla_loader_service import load_approved_planillas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load approved local planillas without copying PDF bytes")
    parser.add_argument("--database-url", required=True, help="explicit target database URL; never defaults to runtime DB")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--bootstrap-manifest", type=Path, required=True)
    parser.add_argument("--bootstrap-mapping", type=Path, required=True)
    parser.add_argument("--reconciliation", type=Path, required=True)
    parser.add_argument("--bootstrap-report", type=Path, required=True)
    parser.add_argument("--derived", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        session_factory = sessionmaker(bind=create_engine(args.database_url))
        with session_factory() as db:
            report = load_approved_planillas(
                db, args.derived, args.approval, source_root=args.source_root,
                manifest_path=args.manifest, mapping_path=args.mapping, dry_run=args.dry_run,
                bootstrap_path=args.bootstrap_manifest, bootstrap_mapping_path=args.bootstrap_mapping,
                reconciliation_path=args.reconciliation, bootstrap_report_path=args.bootstrap_report,
            )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: official load failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(report.as_dict(), ensure_ascii=False, sort_keys=True))
    return 2 if report.rejected else 0


if __name__ == "__main__":
    raise SystemExit(main())

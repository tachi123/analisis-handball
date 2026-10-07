"""Run the local curated fixture importer; it never fetches network or PDFs."""

import argparse
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.services.fixture_seeder import FixtureValidationError, import_fixture, load_fixture


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a curated fixture JSON file")
    parser.add_argument("json_path", help="explicit local fixture JSON path")
    parser.add_argument("--dry-run", action="store_true", help="validate and roll back the import")
    args = parser.parse_args()
    try:
        payload, raw_payload = load_fixture(args.json_path)
        with SessionLocal() as db:
            summary = import_fixture(db, payload, raw_payload, dry_run=args.dry_run)
    except (OSError, FixtureValidationError) as error:
        parser.error(str(error))
    print(f"created={summary.created} updated={summary.updated} skipped={summary.skipped} bye={summary.byes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

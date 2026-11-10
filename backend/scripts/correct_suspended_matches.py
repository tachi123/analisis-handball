"""Apply reviewed suspended-match corrections without touching source files.

A suspended match keeps its official planilla (which records the score at the
moment of suspension) but its final awarded result differs and its partial
player statistics must not count as official. The correction sets the final
result on the Match and fixture, marks the fixture suspended, and downgrades the
partial snapshot so confirmed-stat aggregation excludes it.
"""
import argparse
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.models import FixtureImportEntry, OfficialSnapshot, ScheduledMatch


def main(argv=None):
    parser = argparse.ArgumentParser(description="Correct suspended-match results from a reviewed JSON document")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--corrections", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run == args.execute:
        parser.error("choose exactly one of --dry-run or --execute")
    document = json.loads(args.corrections.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(document.get("corrections"), list):
        raise ValueError("corrections must be schema_version 1 with a corrections array")
    with sessionmaker(bind=create_engine(args.database_url))() as db:
        applied = []
        for correction in document["corrections"]:
            entry = db.query(FixtureImportEntry).filter_by(entry_key=correction["fixture_key"]).one_or_none()
            if entry is None or entry.scheduled_match is None:
                raise ValueError(f"fixture not imported: {correction['fixture_key']}")
            fixture = entry.scheduled_match
            match = fixture.analysis_match
            if match is None:
                raise ValueError(f"fixture has no match: {correction['fixture_key']}")
            home, away = correction["final_home_score"], correction["final_away_score"]
            match.home_score, match.away_score = home, away
            fixture.source_home_score, fixture.source_away_score = home, away
            fixture.status, fixture.result_status = "suspended", "approved"
            downgraded = 0
            for snapshot in match.official_snapshots:
                if snapshot.is_confirmed:
                    snapshot.is_confirmed = False
                    downgraded += 1
            applied.append({"fixture_key": correction["fixture_key"], "match_id": match.id,
                            "final_result": [home, away], "downgraded_snapshots": downgraded})
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
        print(json.dumps(applied, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

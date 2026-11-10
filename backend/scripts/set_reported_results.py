"""Apply reviewed reported results to fixtures without a planilla.

Reads an explicit reviewed JSON document of provisional results and records them
as result_status="reported" with a Match carrying the score. When a planilla
arrives later, the planilla loader upgrades the same Match in place.
"""
import argparse
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.models import CompetitionTeam, FixtureImportEntry, Match, Team, TeamRegistration


def _team(db, competition_team) -> Team:
    name = competition_team.display_name
    team = db.query(Team).filter_by(name=name).first()
    if team is None:
        team = Team(name=name)
        db.add(team)
        db.flush()
    return team


def main(argv=None):
    parser = argparse.ArgumentParser(description="Apply reviewed reported results without a planilla")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run == args.execute:
        parser.error("choose exactly one of --dry-run or --execute")
    document = json.loads(args.results.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(document.get("results"), list):
        raise ValueError("results must be schema_version 1 with a results array")
    with sessionmaker(bind=create_engine(args.database_url))() as db:
        applied = []
        for item in document["results"]:
            entry = db.query(FixtureImportEntry).filter_by(entry_key=item["fixture_key"]).one_or_none()
            if entry is None or entry.scheduled_match is None:
                raise ValueError(f"fixture not imported: {item['fixture_key']}")
            fixture = entry.scheduled_match
            if fixture.analysis_match and fixture.analysis_match.official_snapshots:
                raise ValueError(f"fixture already has a confirmed planilla: {item['fixture_key']}")
            home_score, away_score = item["home_score"], item["away_score"]
            fixture.source_home_score, fixture.source_away_score = home_score, away_score
            fixture.result_status, fixture.status = "reported", "played"
            home = _team(db, fixture.home_registration.competition_team)
            away = _team(db, fixture.away_registration.competition_team)
            match = fixture.analysis_match
            if match is None:
                match = Match(scheduled_match_id=fixture.id, origin="fixture")
                db.add(match)
            match.date = fixture.scheduled_date
            match.home_team_id, match.away_team_id = home.id, away.id
            match.home_score, match.away_score = home_score, away_score
            applied.append({"fixture_key": item["fixture_key"], "result": [home_score, away_score]})
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
        print(json.dumps(applied, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

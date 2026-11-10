"""Materialize reported fixture results into Match records without planillas.

A reported result carries the score but no official planilla, so it receives a
Match with origin="fixture" and no OfficialSnapshot. When the planilla arrives
later, the planilla loader upgrades the same Match in place and appends the
snapshot instead of creating a duplicate.
"""
import argparse
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.models import CompetitionTeam, Match, ScheduledMatch, Team, TeamRegistration


def _team(db, competition_team) -> Team:
    name = competition_team.display_name
    team = db.query(Team).filter_by(name=name).first()
    if team is None:
        team = Team(name=name)
        db.add(team)
        db.flush()
    return team


def main(argv=None):
    parser = argparse.ArgumentParser(description="Materialize reported results without a planilla")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--stage-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run == args.execute:
        parser.error("choose exactly one of --dry-run or --execute")
    with sessionmaker(bind=create_engine(args.database_url))() as db:
        fixtures = (
            db.query(ScheduledMatch)
            .options(
                joinedload(ScheduledMatch.home_registration).joinedload(TeamRegistration.competition_team).joinedload(CompetitionTeam.club),
                joinedload(ScheduledMatch.away_registration).joinedload(TeamRegistration.competition_team).joinedload(CompetitionTeam.club),
                joinedload(ScheduledMatch.analysis_match),
            )
            .filter(
                ScheduledMatch.stage_id == args.stage_id,
                ScheduledMatch.result_status == "reported",
                ScheduledMatch.source_home_score.isnot(None),
                ScheduledMatch.source_away_score.isnot(None),
            )
            .all()
        )
        created, reused = 0, 0
        for fixture in fixtures:
            if fixture.analysis_match is not None:
                reused += 1
                continue
            home = _team(db, fixture.home_registration.competition_team)
            away = _team(db, fixture.away_registration.competition_team)
            match = Match(date=fixture.scheduled_date, home_team_id=home.id, away_team_id=away.id,
                          home_score=fixture.source_home_score, away_score=fixture.source_away_score,
                          scheduled_match_id=fixture.id, origin="fixture")
            db.add(match)
            created += 1
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
        print({"reported_fixtures": len(fixtures), "created": created, "reused": reused})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

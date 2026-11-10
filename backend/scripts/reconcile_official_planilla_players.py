"""Safely materialize exact normalized player identities within one stage registration."""
import argparse
from collections import defaultdict
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.models import Match, OfficialSnapshot, OfficialSnapshotPlayer, Player, ScheduledMatch
from app.services.planilla_player_identity_service import normalize_name


def main(argv=None):
    parser = argparse.ArgumentParser(description="Link official planilla rows by exact normalized name within a club registration")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--stage-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run == args.execute:
        parser.error("choose exactly one of --dry-run or --execute")
    with sessionmaker(bind=create_engine(args.database_url))() as db:
        rows = db.query(OfficialSnapshotPlayer).join(OfficialSnapshot).join(Match).join(ScheduledMatch).options(
            joinedload(OfficialSnapshotPlayer.snapshot).joinedload(OfficialSnapshot.match).joinedload(Match.scheduled_match)
        ).filter(ScheduledMatch.stage_id == args.stage_id, OfficialSnapshot.is_confirmed.is_(True)).all()
        groups = defaultdict(list)
        for row in rows:
            match, fixture = row.snapshot.match, row.snapshot.match.scheduled_match
            registration_id = fixture.home_registration_id if row.side == "home" else fixture.away_registration_id
            team_id = match.home_team_id if row.side == "home" else match.away_team_id
            name = normalize_name(row.name)
            if name:
                groups[(registration_id, name, team_id)].append(row)
        created = linked = already_linked = skipped = 0
        for (_, _, team_id), members in groups.items():
            existing_ids = {row.player_id for row in members if row.player_id is not None}
            if len(existing_ids) > 1:
                skipped += len(members); continue
            player = db.get(Player, next(iter(existing_ids))) if existing_ids else None
            if player is None:
                display_name = sorted((row.name for row in members), key=lambda value: (-sum(item.name == value for item in members), value))[0]
                player = Player(name=display_name, team_id=team_id, default_jersey_number=members[0].jersey_number)
                db.add(player); db.flush(); created += 1
            if player.team_id != team_id:
                skipped += len(members); continue
            for row in members:
                if row.player_id is None:
                    row.player_id = player.id; linked += 1
                else:
                    already_linked += 1
        report = {"groups": len(groups), "created_players": created, "linked_rows": linked, "already_linked_rows": already_linked, "skipped_rows": skipped}
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

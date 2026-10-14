"""Explicitly approve or revoke official-sheet publication for matches."""
from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "/app/app")

from app.database import SessionLocal
from app.models import OfficialSnapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Approve official sheets for public static reports.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--publish", action="store_true", help="Approve the confirmed sheet for public export.")
    action.add_argument("--unpublish", action="store_true", help="Revoke approval; the next export removes its public copy.")
    parser.add_argument("match_ids", nargs="+", type=int, help="One or more match IDs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        snapshots = db.query(OfficialSnapshot).filter(
            OfficialSnapshot.match_id.in_(args.match_ids),
            OfficialSnapshot.is_confirmed.is_(True),
        ).order_by(OfficialSnapshot.match_id, OfficialSnapshot.created_at.desc(), OfficialSnapshot.id.desc()).all()
        selected: dict[int, OfficialSnapshot] = {}
        for snapshot in snapshots:
            selected.setdefault(snapshot.match_id, snapshot)
        missing = sorted(set(args.match_ids) - set(selected))
        if missing:
            raise ValueError(f"No confirmed official sheet for match IDs: {', '.join(map(str, missing))}")
        for match_id in args.match_ids:
            snapshot = selected[match_id]
            snapshot.is_publicly_published = args.publish
            print(f"Match {match_id}: {'approved' if args.publish else 'revoked'} · {snapshot.source_filename}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()

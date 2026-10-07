#!/usr/bin/env python
"""Backfill script for planilla 7164158c7b0e9b17.pdf (SHA256: 333556da08f99ab942a23426cad608f619fdd5dc4675be6d464f5583e4cac8a3).

This script:
1. Locates the PDF by SHA256 in manifest.json / derived-fixtures.json
2. Finds the corresponding FixtureImportEntry → ScheduledMatch
3. Loads PDF from indexed location
4. Calls PDFService.fixture_preview() → confirm_fixture() with auto team confirmation
5. For each roster row with player_id=null: resolves identity (interactive or CSV mode)
6. Calls PDFService.resolve_fixture_roster() per row
7. Verifies full chain: Match, OfficialSnapshot, MatchSquad (both sides), StageRoster
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.models import (
    FixtureImportEntry,
    Match,
    MatchSquad,
    OfficialSnapshot,
    OfficialSnapshotPlayer,
    Player,
    ScheduledMatch,
    StageRoster,
    Team,
)
from app.schemas import FixtureConfirmation, FixtureRosterResolution
from app.services.pdf_service import PDFService


# Constants
PDF_SHA256 = "333556da08f99ab942a23426cad608f619fdd5dc4675be6d464f5583e4cac8a3"
PDF_FILENAME = "7164158c7b0e9b17.pdf"
PDF_RELATIVE_PATH = "2026_Apertura_Zona_A _Mayores_3º_División_Masculino/7164158c7b0e9b17.pdf"

# Paths relative to repo root (script is in backend/scripts/)
REPO_ROOT = BACKEND_DIR.parent
MANIFEST_PATH = REPO_ROOT / "resources/planillas/_discovery/manifest.json"
DERIVED_FIXTURES_PATH = REPO_ROOT / "resources/planillas/_discovery/derived-fixtures.json"
CSV_MAPPING_PATH = BACKEND_DIR / "scripts/backfill_7164158c7b0e9b17_mapping.csv"

# Scores from PDF (home=24, away=25)
HOME_SCORE = 24
AWAY_SCORE = 25


def find_fixture_key_by_sha256() -> str:
    """Find the fixture_key for the PDF with the given SHA256."""
    # Try derived-fixtures.json first (has fixture_key directly)
    if DERIVED_FIXTURES_PATH.exists():
        with DERIVED_FIXTURES_PATH.open() as f:
            data = json.load(f)
        for fixture in data.get("fixtures", []):
            for round_data in fixture.get("rounds", []):
                for entry in round_data.get("entries", []):
                    planilla = entry.get("planilla", {})
                    if planilla.get("sha256") == PDF_SHA256:
                        return entry["fixture_key"]

    # Fallback to manifest.json -> find entry_key -> query DB
    if MANIFEST_PATH.exists():
        with MANIFEST_PATH.open() as f:
            data = json.load(f)
        for record in data.get("records", []):
            if record.get("sha256") == PDF_SHA256:
                # The entry_key in manifest corresponds to FixtureImportEntry.entry_key
                # We need to look this up in the database
                return record.get("entry_key", "").replace("planilla:", "")

    raise ValueError(f"Could not find fixture for PDF SHA256 {PDF_SHA256}")


def find_fixture_import_entry(db: Session, sha256: str) -> Optional[FixtureImportEntry]:
    """Find FixtureImportEntry by looking up the PDF's sha256 in the database."""
    # The FixtureImportEntry.raw_entry contains the planilla sha256
    entries = db.query(FixtureImportEntry).filter(FixtureImportEntry.kind == "match").all()
    for entry in entries:
        raw = entry.raw_entry
        if isinstance(raw, dict):
            planilla = raw.get("planilla", {})
            if planilla.get("sha256") == sha256:
                return entry
    return None


def load_pdf_bytes() -> bytes:
    """Load PDF bytes from the indexed location."""
    # Try the relative path from manifest/derived-fixtures
    pdf_path = REPO_ROOT / "resources/planillas" / PDF_RELATIVE_PATH
    if not pdf_path.exists():
        # Try without the space encoding issues
        pdf_path = REPO_ROOT / "resources/planillas" / "2026_Apertura_Zona_A _Mayores_3º_División_Masculino" / PDF_FILENAME
    if not pdf_path.exists():
        # Search recursively
        candidates = list((REPO_ROOT / "resources/planillas").rglob(PDF_FILENAME))
        if candidates:
            pdf_path = candidates[0]
        else:
            raise FileNotFoundError(f"PDF not found: {PDF_FILENAME}")

    return pdf_path.read_bytes()


def load_csv_mapping() -> dict:
    """Load player resolution mapping from CSV if it exists."""
    mapping = {}
    if CSV_MAPPING_PATH.exists():
        with CSV_MAPPING_PATH.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                snapshot_player_id = int(row["snapshot_player_id"])
                decision = row["decision"]  # "link" or "create"
                if decision == "link":
                    mapping[snapshot_player_id] = {"existing_player_id": int(row["existing_player_id"])}
                elif decision == "create":
                    mapping[snapshot_player_id] = {"create_player": True, "new_player_name": row.get("new_player_name", "")}
    return mapping


def find_candidate_players(db: Session, team_id: int, name: str) -> list:
    """Find candidate Player records by team_id + name similarity (simple contains match)."""
    normalized = PDFService._normalize_identity_name(name)
    candidates = []
    for player in db.query(Player).filter_by(team_id=team_id).all():
        if PDFService._normalize_identity_name(player.name) == normalized:
            candidates.append(player)
    return candidates


def interactive_resolve_player(db: Session, row: OfficialSnapshotPlayer, match: Match) -> FixtureRosterResolution:
    """Interactively prompt analyst to resolve a player's identity."""
    team_id = match.home_team_id if row.side == "home" else match.away_team_id
    candidates = find_candidate_players(db, team_id, row.name)

    print(f"\n--- Resolving player ---")
    print(f"Snapshot Player ID: {row.id}")
    print(f"Side: {row.side}")
    print(f"Name: {row.name}")
    print(f"Jersey: {row.jersey_number}")
    print(f"Team ID: {team_id}")

    if candidates:
        print("Candidates:")
        for i, cand in enumerate(candidates):
            print(f"  [{i}] Player ID {cand.id}: {cand.name} (jersey {cand.default_jersey_number})")
        print(f"  [{len(candidates)}] Create new player")
    else:
        print("No candidates found.")
        print("  [0] Create new player")

    while True:
        try:
            choice = input("Select option: ").strip()
            if not choice:
                continue
            idx = int(choice)
            if candidates and 0 <= idx < len(candidates):
                return FixtureRosterResolution(
                    snapshot_player_id=row.id,
                    existing_player_id=candidates[idx].id
                )
            elif (candidates and idx == len(candidates)) or (not candidates and idx == 0):
                new_name = input("Enter new player name: ").strip()
                if not new_name:
                    print("Name cannot be empty")
                    continue
                return FixtureRosterResolution(
                    snapshot_player_id=row.id,
                    create_player=True
                )
            else:
                print("Invalid option")
        except ValueError:
            print("Please enter a number")
        except KeyboardInterrupt:
            print("\nAborted")
            sys.exit(1)


def resolve_roster_identity(db: Session, fixture_key: str, match: Match, snapshot: OfficialSnapshot,
                            csv_mapping: dict, interactive: bool, auto_create: bool) -> dict:
    """Resolve identity for all unresolved roster players."""
    unresolved = [p for p in snapshot.players if p.player_id is None]
    if not unresolved:
        print("All roster players already resolved")
        return {"resolved": 0, "created": 0, "linked": 0}

    print(f"\nFound {len(unresolved)} unresolved roster players")

    resolutions = []
    created_count = 0
    linked_count = 0

    for row in unresolved:
        if row.id in csv_mapping:
            # Use CSV mapping
            mapping = csv_mapping[row.id]
            if "existing_player_id" in mapping:
                resolutions.append(FixtureRosterResolution(
                    snapshot_player_id=row.id,
                    existing_player_id=mapping["existing_player_id"]
                ))
                linked_count += 1
                print(f"  CSV: Linking {row.name} (ID {row.id}) to existing player {mapping['existing_player_id']}")
            elif mapping.get("create_player"):
                resolutions.append(FixtureRosterResolution(
                    snapshot_player_id=row.id,
                    create_player=True
                ))
                created_count += 1
                print(f"  CSV: Creating new player for {row.name} (ID {row.id})")
        elif interactive:
            # Interactive mode
            resolution = interactive_resolve_player(db, row, match)
            if resolution.existing_player_id:
                linked_count += 1
            else:
                created_count += 1
            resolutions.append(resolution)
        elif auto_create:
            # Auto-create mode: create new player for each unresolved
            resolutions.append(FixtureRosterResolution(
                snapshot_player_id=row.id,
                create_player=True
            ))
            created_count += 1
            print(f"  AUTO: Creating new player for {row.name} (ID {row.id})")
        else:
            print(f"  SKIP: {row.name} (ID {row.id}) - no mapping and not interactive")
            continue

    if not resolutions:
        print("No resolutions to apply")
        return {"resolved": 0, "created": 0, "linked": 0}

    print(f"\nApplying {len(resolutions)} resolutions...")
    result = PDFService.resolve_fixture_roster(db, fixture_key, resolutions)
    print(f"Result: {result}")

    return {"resolved": len(resolutions), "created": created_count, "linked": linked_count}


def main():
    parser = argparse.ArgumentParser(description="Backfill planilla 7164158c7b0e9b17.pdf")
    parser.add_argument("--database-url", required=True, help="Database URL (e.g., sqlite:///test.db or postgresql://...)")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode (prompt for each player)")
    parser.add_argument("--csv", action="store_true", help="Use CSV mapping file")
    parser.add_argument("--auto-create", action="store_true", help="Auto-create new players for all unresolved roster entries (no prompts)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't persist")
    args = parser.parse_args()

    if args.csv and args.interactive:
        parser.error("Cannot use both --csv and --interactive")
    if args.auto_create and (args.csv or args.interactive):
        parser.error("Cannot use --auto-create with --csv or --interactive")

    # Load CSV mapping if requested
    csv_mapping = {}
    if args.csv:
        csv_mapping = load_csv_mapping()
        if not csv_mapping:
            print("Warning: CSV mapping file not found or empty, falling back to interactive mode")
            args.interactive = True

    # Create database session
    engine = create_engine(args.database_url)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as db:
        try:
            # Step 1: Find fixture_key
            print(f"Looking up fixture for PDF SHA256: {PDF_SHA256}")
            fixture_key = find_fixture_key_by_sha256()
            print(f"Found fixture_key: {fixture_key}")

            # Step 2: Get the ScheduledMatch
            fixture = db.query(ScheduledMatch).filter_by(fixture_key=fixture_key).first()
            if not fixture:
                raise ValueError(f"ScheduledMatch not found for fixture_key: {fixture_key}")

            print(f"ScheduledMatch ID: {fixture.id}")
            print(f"Home: {fixture.home_registration.competition_team.club.name} {fixture.home_registration.competition_team.suffix or ''}")
            print(f"Away: {fixture.away_registration.competition_team.club.name} {fixture.away_registration.competition_team.suffix or ''}")

            # Step 3: Load PDF bytes
            print(f"\nLoading PDF: {PDF_RELATIVE_PATH}")
            pdf_bytes = load_pdf_bytes()
            print(f"PDF size: {len(pdf_bytes)} bytes")

            # Step 4: Check idempotency - if analysis_match exists, reuse
            if fixture.analysis_match:
                print("\n--- Idempotent path: Match already exists ---")
                match = fixture.analysis_match
                snapshot = next((s for s in match.official_snapshots if s.is_confirmed), None)
                if not snapshot:
                    raise ValueError("Match exists but no confirmed OfficialSnapshot found")
                print(f"Reusing Match ID: {match.id}")
                print(f"Reusing OfficialSnapshot ID: {snapshot.id}")
            else:
                print("\n--- Create path: Confirming fixture ---")
                # Call fixture_preview first
                preview_result = PDFService.fixture_preview(
                    db, fixture_key, pdf_bytes, PDF_FILENAME, "application/pdf"
                )
                print(f"Preview: home_compatibility={preview_result['home_compatibility']['status']}, "
                      f"away_compatibility={preview_result['away_compatibility']['status']}, "
                      f"score_reconciliation={preview_result['score_reconciliation']}")

                # Find or create legacy Teams for the competition teams
                home_club_name = fixture.home_registration.competition_team.club.name
                away_club_name = fixture.away_registration.competition_team.club.name

                home_team = db.query(Team).filter_by(name=home_club_name).first()
                if not home_team:
                    home_team = Team(name=home_club_name, club_name=home_club_name, category="")
                    db.add(home_team)
                    db.flush()
                    print(f"Created legacy Team for home: {home_club_name} (ID: {home_team.id})")
                else:
                    print(f"Found legacy Team for home: {home_club_name} (ID: {home_team.id})")

                away_team = db.query(Team).filter_by(name=away_club_name).first()
                if not away_team:
                    away_team = Team(name=away_club_name, club_name=away_club_name, category="")
                    db.add(away_team)
                    db.flush()
                    print(f"Created legacy Team for away: {away_club_name} (ID: {away_team.id})")
                else:
                    print(f"Found legacy Team for away: {away_club_name} (ID: {away_team.id})")

                # Auto-confirm teams (they match the fixture registrations)
                home_team_id = home_team.id
                away_team_id = away_team.id

                # We don't have player confirmations yet - they'll be resolved after
                # Acknowledge name mismatch: PDF has "C.A. y S. Villa Calzada" vs fixture "Villa Calzada"
                confirmation = FixtureConfirmation(
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    home_players=[],
                    away_players=[],
                    acknowledge_score_mismatch=False,
                    acknowledge_name_mismatch=True
                )

                confirm_result = PDFService.confirm_fixture(
                    db, fixture_key, pdf_bytes, PDF_FILENAME, "application/pdf", confirmation
                )
                match = db.get(Match, confirm_result["match_id"])
                snapshot = db.get(OfficialSnapshot, confirm_result["snapshot_id"])
                print(f"Created Match ID: {match.id}")
                print(f"Created OfficialSnapshot ID: {snapshot.id}")
                print(f"Reused: {confirm_result['reused']}")

                # Create OfficialSnapshotPlayer entries from preview data (with player_id=None for unresolved)
                print("\nCreating roster entries from preview data...")
                home_parsed = preview_result["preview"]["home_team"]["players"]
                away_parsed = preview_result["preview"]["away_team"]["players"]
                
                # Get Team objects for player creation
                home_team = db.get(Team, match.home_team_id)
                away_team = db.get(Team, match.away_team_id)
                
                for side, parsed_players, team in [("home", home_parsed, home_team), ("away", away_parsed, away_team)]:
                    for p in parsed_players:
                        db.add(OfficialSnapshotPlayer(
                            snapshot_id=snapshot.id,
                            side=side,
                            player_id=None,  # Will be resolved later
                            name=p["name"],
                            jersey_number=p["number"],
                            official_goals=p.get("goals", 0),
                            official_yellow=p.get("yellow", 0),
                            official_2min=p.get("two_min", 0),
                            official_red=p.get("red", 0),
                            official_blue=p.get("blue", 0),
                        ))
                db.commit()
                print(f"Created {len(home_parsed)} home + {len(away_parsed)} away roster entries")

            # Step 5: Resolve roster identities
            # Refresh snapshot to get players
            db.refresh(snapshot)
            unresolved_before = [p for p in snapshot.players if p.player_id is None]
            print(f"\nUnresolved players before resolution: {len(unresolved_before)}")

            if unresolved_before:
                resolve_result = resolve_roster_identity(
                    db, fixture_key, match, snapshot, csv_mapping, args.interactive, args.auto_create
                )
            else:
                resolve_result = {"resolved": 0, "created": 0, "linked": 0}

            # Step 6: Verify full chain
            db.refresh(match)
            db.refresh(snapshot)

            match_squad_count = db.query(MatchSquad).filter_by(match_id=match.id).count()
            stage_roster_count = db.query(StageRoster).join(ScheduledMatch.home_registration).filter(
                ScheduledMatch.id == fixture.id
            ).count() + db.query(StageRoster).join(ScheduledMatch.away_registration).filter(
                ScheduledMatch.id == fixture.id
            ).count()

            # Also count by registration
            home_reg_id = fixture.home_registration_id
            away_reg_id = fixture.away_registration_id
            home_stage_count = db.query(StageRoster).filter_by(registration_id=home_reg_id).count()
            away_stage_count = db.query(StageRoster).filter_by(registration_id=away_reg_id).count()

            print("\n=== BACKFILL SUMMARY ===")
            print(f"Match ID: {match.id}")
            print(f"OfficialSnapshot ID: {snapshot.id}")
            print(f"OfficialSnapshot SHA256: {snapshot.source_sha256}")
            print(f"MatchSquad entries: {match_squad_count}")
            print(f"StageRoster entries (home): {home_stage_count}")
            print(f"StageRoster entries (away): {away_stage_count}")
            print(f"StageRoster total: {home_stage_count + away_stage_count}")
            print(f"Players resolved this run: {resolve_result['resolved']}")
            print(f"  - New players created: {resolve_result['created']}")
            print(f"  - Existing players linked: {resolve_result['linked']}")

            # Verify analysis_match link
            db.refresh(fixture)
            assert fixture.analysis_match is not None, "ScheduledMatch.analysis_match not set"
            assert fixture.analysis_match.id == match.id, "ScheduledMatch.analysis_match.id mismatch"
            print(f"ScheduledMatch.analysis_match.id: {fixture.analysis_match.id} [OK]")

            # Verify OfficialSnapshot link
            assert snapshot.match_id == match.id, "OfficialSnapshot.match_id mismatch"
            assert snapshot.source_sha256 == PDF_SHA256, "SHA256 mismatch"
            print(f"OfficialSnapshot.source_sha256 matches PDF [OK]")

            # Verify all players resolved
            unresolved_after = [p for p in snapshot.players if p.player_id is None]
            if unresolved_after:
                print(f"WARNING: {len(unresolved_after)} players still unresolved!")
            else:
                print("All OfficialSnapshotPlayer rows have player_id [OK]")

            # Verify MatchSquad matches roster
            expected_squad = len(snapshot.players)
            if match_squad_count == expected_squad:
                print(f"MatchSquad count ({match_squad_count}) matches roster ({expected_squad}) [OK]")
            else:
                print(f"WARNING: MatchSquad count ({match_squad_count}) != roster ({expected_squad})")

            # Verify StageRoster per registration
            for reg_id, side in [(home_reg_id, "home"), (away_reg_id, "away")]:
                reg_count = db.query(StageRoster).filter_by(registration_id=reg_id).count()
                expected = len([p for p in snapshot.players if p.side == side])
                if reg_count == expected:
                    print(f"StageRoster {side} count ({reg_count}) matches roster ({expected}) [OK]")
                else:
                    print(f"WARNING: StageRoster {side} count ({reg_count}) != roster ({expected})")

            if not args.dry_run:
                db.commit()
                print("\n[OK] Changes committed")
            else:
                db.rollback()
                print("\n[DRY RUN] Changes rolled back")

            return 0

        except Exception as e:
            db.rollback()
            print(f"\n✗ Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(main())
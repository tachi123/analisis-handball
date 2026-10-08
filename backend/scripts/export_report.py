"""Export a static public report JSON for a given match ID.

This script connects to the local PostgreSQL DB only during export.
The generated JSON report has NO backend/API dependency at runtime —
it is a fully self-contained static file that can be committed to the
repo and deployed to GitHub Pages.

Usage:
    python -m backend.scripts.export_report --match-id 99 --output reports/public/report.json
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.models import (
    Match, Team, Player, MatchSquad, CanonicalEvent, CanonicalEventRevision,
    CanonicalEvidence, OfficialSnapshot, AnalysisSession, VideoSource,
    GoalkeeperShot, ScheduledMatch,
)
from app.services.canonical_analysis_service import read_metrics, read_reconciliation, read_state
from app.services.report_service import ReportService, PUBLIC_METRIC_NAMES, is_public_metric


def public_projection_from_package_type(package_dict: dict) -> dict:
    """Reproduce ReportService.public_projection logic from a dict (no DB dependency)."""

    evidence_items = []
    for item in package_dict.get("evidence", []):
        if not item.get("public_approved", True):
            continue
        public_item = {
            "reference": item.get("reference"),
            "period": item.get("period"),
            "regulation_seconds": item.get("regulation_seconds"),
            "clock_unverified": item.get("clock_unverified", False),
            "observation": item.get("public_observation", ""),
            "media_available": bool(item.get("media_public_approved", False) and item.get("public_media_url")),
        }
        if public_item["media_available"]:
            public_item["media_url"] = item.get("public_media_url")
        evidence_items.append(public_item)

    metrics = {}
    for name, value in package_dict.get("metrics", {}).items():
        if is_public_metric(name) and isinstance(value, dict):
            metric = {}
            for field in ("count", "numerator", "denominator", "excluded", "unknown", "clock_unverified"):
                if field in value:
                    metric[field] = value[field]
            if metric:
                metrics[name] = metric

    # Derive coverage from evidence periods
    all_periods = sorted({item.get("period") for item in evidence_items if item.get("period") is not None})
    coverage = None
    if all_periods:
        has_half1 = 1 in all_periods
        has_half2 = 2 in all_periods
        if has_half1 and has_half2:
            status = "complete"
            label = None
        else:
            status = "partial"
            analyzed = [p for p in all_periods if p is not None]
            label = "Analysis covering periods " + ", ".join(str(p) for p in analyzed)
        coverage = {
            "analyzed_periods": all_periods,
            "status": status,
            "label": label,
        }

    return {
        "schema_version": package_dict.get("schema_version", "public-report-v1"),
        "report_version": package_dict.get("report_version", 1),
        "match": {
            "date": package_dict["match"].date.isoformat() if hasattr(package_dict["match"], 'date') and package_dict["match"].date else (package_dict.get("match", {}).get("date").isoformat() if isinstance(package_dict.get("match"), dict) and package_dict.get("match").get("date") else None),
            "home_team": package_dict["match"].home_team.name if hasattr(package_dict["match"], 'home_team') else (package_dict.get("match", {}).get("home_team", {}).get("name") if isinstance(package_dict.get("match"), dict) else None),
            "away_team": package_dict["match"].away_team.name if hasattr(package_dict["match"], 'away_team') else (package_dict.get("match", {}).get("away_team", {}).get("name") if isinstance(package_dict.get("match"), dict) else None),
        },
        "source": {"label": package_dict.get("source_label", ""), "status": package_dict.get("source_status", "")},
        "coaching": {
            "question": package_dict.get("coaching_question", ""),
            "pattern_statement": package_dict.get("pattern_statement", ""),
            "action": {"kind": package_dict.get("action_kind", "keep"), "text": package_dict.get("action_text", "")},
        },
        "metrics": metrics,
        "reconciliation": package_dict.get("reconciliation", []),
        "uncertainty_disclosure": package_dict.get("uncertainty_disclosure", ""),
        "players": package_dict.get("players"),
        "evidence": evidence_items,
        "coverage": coverage,
    }


def main():
    parser = argparse.ArgumentParser(description="Export static public report JSON for a match")
    parser.add_argument("--match-id", type=int, required=True, help="Match ID to export")
    parser.add_argument("--output", type=str, required=True, help="Output JSON file path")
    args = parser.parse_args()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        repo_root = Path(__file__).resolve().parent.parent
        output_path = repo_root / output_path

    from sqlalchemy import event
    db = SessionLocal()

    try:
        match = db.get(Match, args.match_id)
        if match is None:
            print("Match " + str(args.match_id) + " not found in database", file=sys.stderr)
            sys.exit(1)

        print("Exporting Match " + str(args.match_id))

        metrics_data = read_metrics(db, args.match_id)
        eligibility = metrics_data.get("eligibility", {})
        print("Eligible events: " + str(eligibility.get("eligible", 0)))

        recon_data = read_reconciliation(db, args.match_id)

        events = metrics_data.get("events", [])
        eligible_events = [e for e in events if e.get("active") and e.get("payload", {}).get("fact_kind") == "observed"
                          and e.get("payload", {}).get("evidence_state") == "confirmed"]

        evidence_rows = []
        seq = 1
        for event in eligible_events:
            payload = event["payload"]
            revision = event.get("revision", 1)
            event_id = event["id"]
            ref = "Sequence " + str(seq)
            seq += 1
            period = payload.get("period", 1)
            reg_seconds = payload.get("regulation_seconds")
            clock_unverified = bool(payload.get("clock_unverified"))

            evidence_rows.append({
                "reference": ref,
                "period": period,
                "regulation_seconds": reg_seconds,
                "clock_unverified": clock_unverified,
                "public_observation": payload.get("team_action", "Canonical observation"),
                "public_approved": True,
                "media_public_approved": False,
                "public_media_url": None,
            })

        # Build players from match squad
        players_data = []
        squad = db.query(MatchSquad).options(
            joinedload(MatchSquad.player)).filter_by(match_id=args.match_id).all()

        gk_designated_players = set()
        if match.canonical_analysis_enabled:
            for event in eligible_events:
                payload = event["payload"]
                if payload.get("kind") == "shot" and payload.get("goalkeeper_id") is not None:
                    gk_designated_players.add(payload["goalkeeper_id"])

        squad_player_ids = set()
        for s in squad:
            pid = s.player_id if s.player else None
            if pid is not None:
                squad_player_ids.add(pid)

        for s in squad:
            player = s.player
            is_gk = s.is_goalkeeper
            player_id = player.id if player else None

            gk_designated = (player_id in gk_designated_players) if player_id is not None else False

            if is_gk or gk_designated:
                role = "goalkeeper"
                gk_metrics = {"saves": 0, "shots_faced": 0, "goals_conceded": 0, "save_rate": None}
                gk_count = 0

                for event in eligible_events:
                    payload = event["payload"]
                    if payload.get("kind") == "shot" and payload.get("goalkeeper_id") == player_id:
                        gk_count += 1
                        outcome = payload.get("outcome")
                        if outcome == "save":
                            gk_metrics["saves"] += 1
                        elif outcome == "goal":
                            gk_metrics["goals_conceded"] += 1
                        gk_metrics["shots_faced"] += 1

                denom = gk_metrics["saves"] + gk_metrics["goals_conceded"]
                if denom:
                    gk_metrics["save_rate"] = round(gk_metrics["saves"] / denom, 4)

                player_name = player.name if player else ("Goalkeeper " + (str(player.default_jersey_number) if player and player.default_jersey_number else "1"))

                # Compute team side from match context (MatchSquad has no side column)
                if player and player.team_id:
                    if player.team_id == match.home_team_id:
                        side = "home"
                    elif player.team_id == match.away_team_id:
                        side = "away"
                    else:
                        side = "unknown"
                else:
                    side = "unknown"

                players_data.append({
                    "slug": (player.name.lower().replace(" ", "-") if player and player.name else ("gk-" + (str(player.default_jersey_number) if player and player.default_jersey_number else "1")))[:32],
                    "name": player_name,
                    "jersey_number": player.default_jersey_number if player else 1,
                    "team_side": side,
                    "role": role,
                    "metrics": gk_metrics,
                    "evidence": [],
                })
            else:
                field_shots = 0
                field_goals = 0
                field_assists = 0
                field_turnovers = 0
                field_recoveries = 0
                field_sanctions = 0

                for event in eligible_events:
                    payload = event["payload"]
                    kind = payload.get("kind")
                    outcome = payload.get("outcome")
                    pid = payload.get("player_id")

                    if pid == player_id:
                        if kind == "shot":
                            field_shots += 1
                            if outcome == "goal":
                                field_goals += 1
                        elif kind == "turnover":
                            field_turnovers += 1
                        elif kind == "recovery":
                            field_recoveries += 1
                        elif kind == "foul_sanction":
                            field_sanctions += 1

                shot_conversion = None
                if field_shots > 0:
                    shot_conversion = round(field_goals / field_shots, 4)

                player_name = player.name if player else ("Player " + str(player_id) if player_id else "Unknown")

                # Compute team side from match context (MatchSquad has no side column)
                if player and player.team_id:
                    if player.team_id == match.home_team_id:
                        side = "home"
                    elif player.team_id == match.away_team_id:
                        side = "away"
                    else:
                        side = "unknown"
                else:
                    side = "unknown"

                players_data.append({
                    "slug": (player.name.lower().replace(" ", "-") if player and player.name else ("player-" + str(player_id)))[:32],
                    "name": player_name,
                    "jersey_number": player.default_jersey_number if player else 0,
                    "team_side": side,
                    "role": "field_player",
                    "metrics": {
                        "shot_conversion": shot_conversion,
                        "shots": field_shots,
                        "goals": field_goals,
                        "assists": field_assists,
                        "turnovers": field_turnovers,
                        "recoveries": field_recoveries,
                        "sanctions": field_sanctions,
                    },
                    "evidence": [],
                })

        home_team = match.home_team
        away_team = match.away_team
        source_label = "Match broadcast"
        source_status = "public_reference"

        if match.canonical_analysis_enabled:
            source_label = "Canonical eligible event ledger"
            source_status = "canonical-eligible"

        package_dict = {
            "match_id": args.match_id,
            "report_version": 1,
            "schema_version": "public-report-v1",
            "match": match,
            "home_team": home_team,
            "away_team": away_team,
            "coaching_question": "Analysis of Match " + str(args.match_id),
            "pattern_statement": "Match analysis covering " + str(len(eligible_events)) + " approved canonical events",
            "action_kind": "keep",
            "action_text": "Export approved facts for public report",
            "uncertainty_disclosure": "Generated from canonical analysis; partial data may apply",
            "source_label": source_label,
            "source_status": source_status,
            "metrics": metrics_data.get("metrics", {}),
            "reconciliation": recon_data.get("discrepancies", []),
            "evidence": evidence_rows,
            "players": players_data,
        }

        report = public_projection_from_package_type(package_dict)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print("Report exported to " + str(output_path))
        print("Schema: " + report["schema_version"])
        print("Report version: " + str(report["report_version"]))
        print("Home team: " + report["match"]["home_team"])
        print("Away team: " + report["match"]["away_team"])
        cov = report.get("coverage", {})
        print("Coverage: " + cov.get("status", "none"))
        if cov.get("label"):
            print(" " + cov["label"])
        print("Evidence items: " + str(len(report.get("evidence", []))))
        print("Players: " + str(len(report.get("players", []))))

        metrics = report.get("metrics", {})
        mk = list(metrics.keys())
        print("Metrics: " + str(mk))
        for name, value in metrics.items():
            cnt = value.get("count", "n/a")
            num = value.get("numerator", "n/a")
            denom = value.get("denominator", "n/a")
            print(" " + name + ": count=" + str(cnt) + " numerator=" + str(num) + " denominator=" + str(denom))

        summary = {
            "match_id": args.match_id,
            "home_team": match.home_team.name if match.home_team else None,
            "away_team": match.away_team.name if match.away_team else None,
            "date": str(match.date) if match.date else None,
            "schema_version": report["schema_version"],
            "report_version": report["report_version"],
            "coverage_status": report.get("coverage", {}).get("status", "none"),
            "evidence_count": len(report.get("evidence", [])),
            "players_count": len(report.get("players", [])),
            "metrics_count": len(metrics),
            "home_team_name": match.home_team.name,
            "away_team_name": match.away_team.name,
        }

        print("")
        print("---SUMMARY---")
        print(json.dumps(summary, ensure_ascii=False))

    except Exception as e:
        print("Export failed: " + str(e), file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
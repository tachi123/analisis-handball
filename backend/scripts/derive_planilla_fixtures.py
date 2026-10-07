"""Derive read-only, deterministic fixture JSON from reviewed planilla artifacts."""

import argparse
import json
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.planilla_derivation_service import canonical_json, derive_approved_fixtures, suggest_team_mapping


def _read(path: Path, label: str) -> dict:
    if not path.is_file():
        raise ValueError(f"{label} file does not exist: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive reviewed planilla fixtures without database or source writes")
    parser.add_argument("--database-url", required=True, help="explicit local database containing completed bootstrap audits")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--identities", type=Path, required=True, help="identity-summary.json used to verify reviewed corpus membership")
    parser.add_argument("--mapping", type=Path, required=True, help="reviewed schema-v2 exact-label mapping")
    parser.add_argument("--bootstrap-manifest", type=Path, required=True)
    parser.add_argument("--bootstrap-mapping", type=Path, required=True)
    parser.add_argument("--reconciliation", type=Path, required=True)
    parser.add_argument("--bootstrap-report", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--unresolved-output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest, identities = _read(args.manifest, "manifest"), _read(args.identities, "identities")
        if not isinstance(identities.get("input", {}).get("source_paths"), list):
            raise ValueError("identities must be an identity summary with input.source_paths")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        with sessionmaker(bind=create_engine(args.database_url))() as db:
            derived, report = derive_approved_fixtures(
                db, manifest, _read(args.mapping, "mapping"), _read(args.rules, "rules"),
                _read(args.bootstrap_manifest, "bootstrap manifest"), _read(args.bootstrap_mapping, "bootstrap mapping"),
                _read(args.reconciliation, "reconciliation"), _read(args.bootstrap_report, "bootstrap report"),
                _read(args.approval, "approval"),
            )
        args.output.write_text(canonical_json(derived), encoding="utf-8", newline="\n")
        args.unresolved_output.write_text(canonical_json(report), encoding="utf-8", newline="\n")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: derivation failed: {error}", file=sys.stderr)
        return 2 if isinstance(error, ValueError) and "does not exist" in str(error) else 1
    print(" ".join(f"{key}={value}" for key, value in report["counts"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

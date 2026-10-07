"""Create read-only player-identity review artifacts from a discovery manifest."""

import argparse
import json
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.planilla_player_identity_service import build_identities, write_identity_artifacts


ARTIFACT_NAMES = ("identities.json", "identities.csv", "conflicts.md", "identity-summary.json")


def _read_json(path: Path, label: str) -> dict:
    if not path.is_file():
        raise ValueError(f"{label} file does not exist: {path}")
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Group planilla roster rows without modifying application data")
    parser.add_argument("manifest", type=Path, help="existing discovery manifest.json")
    parser.add_argument("output", type=Path, help="directory for identity review artifacts")
    parser.add_argument("--overrides", type=Path, help="optional identity override JSON file")
    args = parser.parse_args(argv)
    try:
        manifest = _read_json(args.manifest, "manifest")
        overrides = _read_json(args.overrides, "overrides") if args.overrides else None
        result = build_identities(manifest, overrides)
        write_identity_artifacts(result, args.output)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: identity grouping failed: {error}", file=sys.stderr)
        return 2 if isinstance(error, ValueError) and "file does not exist" in str(error) else 1

    print(f"identity_count={len(result['identities'])}")
    for name in ARTIFACT_NAMES:
        print((args.output / name).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

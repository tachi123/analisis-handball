"""Create safe, browsable aliases for a planilla discovery manifest."""

import argparse
import json
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.planilla_discovery_service import write_browsable_index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create read-only planilla filename aliases")
    parser.add_argument("source", type=Path, help="source corpus root")
    parser.add_argument("manifest", type=Path, help="discovery manifest bound to the source corpus")
    parser.add_argument("output", type=Path, help="alias directory, normally resources/planillas/_indexed")
    args = parser.parse_args(argv)
    try:
        if not args.source.is_dir():
            raise ValueError(f"source directory does not exist: {args.source}")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        index = write_browsable_index(manifest, args.source, args.output)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: indexing failed: {error}", file=sys.stderr)
        return 1
    print(index.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

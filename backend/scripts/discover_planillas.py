"""Create read-only review artifacts for a local FEMEBAL planilla corpus."""

import argparse
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.planilla_discovery_service import build_manifest, scan_planillas, write_manifest_artifacts
from app.services.pdf_sheet_text_parser import parse_femebal_sheet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Discover planilla PDFs without modifying sources or application data")
    parser.add_argument("source", type=Path, help="existing directory containing PDF sources")
    parser.add_argument("output", type=Path, help="directory for manifest.json, manifest.csv, and report.md")
    args = parser.parse_args(argv)
    if not args.source.is_dir():
        print(f"error: source directory does not exist: {args.source}", file=sys.stderr)
        return 2
    try:
        manifest = build_manifest(scan_planillas(args.source, parse_femebal_sheet))
        paths = write_manifest_artifacts(manifest, args.output)
    except (OSError, ValueError) as error:
        print(f"error: discovery failed: {error}", file=sys.stderr)
        return 1
    print(f"canonical_records={len(manifest['records'])}")
    for path in paths:
        print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

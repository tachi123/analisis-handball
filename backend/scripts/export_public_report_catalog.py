"""Export one or more active matches into one public static-report catalog.

Set PUBLIC_REPORT_MATCH_IDS to a comma-separated list such as ``99,101``.
The underlying exporter is run once per match so all artifacts share the same
catalog directory while preserving the single-report fallback contract.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def match_ids(raw: str) -> list[int]:
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if not values:
        raise ValueError("PUBLIC_REPORT_MATCH_IDS must contain at least one match ID")
    try:
        return [int(value) for value in values]
    except ValueError as error:
        raise ValueError("PUBLIC_REPORT_MATCH_IDS must be comma-separated integers") from error


def main() -> None:
    ids = match_ids(os.getenv("PUBLIC_REPORT_MATCH_IDS", ""))
    exporter = Path(__file__).with_name("export_report.py")
    environment = os.environ.copy()
    environment.setdefault("PUBLIC_REPORT_OUTPUT", "/tmp/report.json")
    if not environment.get("PUBLIC_REPORT_CATALOG_OUTPUT"):
        raise ValueError("PUBLIC_REPORT_CATALOG_OUTPUT is required for catalog export")

    for match_id in ids:
        run_environment = environment.copy()
        run_environment["PUBLIC_REPORT_MATCH_ID"] = str(match_id)
        print(f"Exporting public report catalog entry for Match {match_id}")
        subprocess.run([sys.executable, str(exporter)], check=True, env=run_environment)


if __name__ == "__main__":
    main()

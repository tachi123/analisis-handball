"""Export the public 2026 competition hub.

Writes the catalog, one static artifact per tournament, the Permanencia
forecast, and the legacy single-tournament file used by older links. Everything
is derived from confirmed official planillas and the recorded fixture; the
browser never calls the private API.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.export_public_tournament import build_public_competitions, build_public_tournament


def _write(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    output = Path(os.getenv("PUBLIC_COMPETITIONS_OUTPUT", "reports/public"))
    output.mkdir(parents=True, exist_ok=True)
    catalog, documents, forecast = build_public_competitions()
    for key, document in documents.items():
        _write(output / f"tournament_{key}.json", document)
    _write(output / "forecast_permanencia-2026.json", forecast)
    _write(output / "tournaments.json", catalog)
    _write(output / "tournament.json", build_public_tournament(9))
    print(
        f"wrote {len(catalog['tournaments'])} tournament cards, "
        f"{len(documents)} tournament artifacts, 1 forecast, "
        f"and the legacy tournament.json -> {output}"
    )


if __name__ == "__main__":
    main()

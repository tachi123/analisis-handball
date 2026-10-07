"""Pure, read-only FEMEBAL sheet parsing for discovery workflows."""

from __future__ import annotations

from typing import Any

import pdfplumber

from .pdf_header_parser import parse_header_pages


def parse_femebal_sheet(pdf_file: Any) -> dict[str, Any]:
    """Extract sheet evidence and rosters without application-model dependencies."""
    data: dict[str, Any] = {
        "match_info": {},
        "home_team": {"name": "", "players": []},
        "away_team": {"name": "", "players": []},
        "fields": {},
        "warnings": [],
    }

    with pdfplumber.open(pdf_file) as pdf:
        page_data = [
            (page.extract_tables(), page.extract_text(), page_number)
            for page_number, page in enumerate(pdf.pages, start=1)
        ]
        word_pages = {
            page_number: page.extract_words(use_text_flow=True)
            for page_number, page in enumerate(pdf.pages, start=1)
            if hasattr(page, "extract_words")
        }
        header = parse_header_pages(page_data, word_pages) if word_pages else parse_header_pages(page_data)
        fields = header["fields"]
        data["fields"] = fields
        data["warnings"] = header["warnings"]
        data["match_info"] = {
            field: fields[field]["value"]
            for field in ("tournament", "venue", "court", "date", "time", "category", "match_number", "home_score", "away_score")
            if fields[field]["value"] is not None
        }
        data["home_team"]["name"] = fields["home_name"]["value"] or ""
        data["away_team"]["name"] = fields["away_name"]["value"] or ""

        for tables, _, page_number in page_data:
            _append_page_players(data, tables, page_number)

    return data


def _append_page_players(data: dict[str, Any], tables: list[list[list[Any]]], page_number: int) -> None:
    players_table = next(
        (
            table for table in tables
            if any(
                "local" in row_text and "visitante" in row_text and "n°" in row_text
                for row_text in (" ".join(str(cell) for cell in row if cell).lower() for row in table[:3])
            )
        ),
        max(tables, key=len) if tables else None,
    )
    if not players_table:
        return

    start_row_index = next(
        (index + 1 for index, row in enumerate(players_table) if "n°" in " ".join(str(cell) for cell in row if cell).lower()),
        0,
    )
    for row in players_table[start_row_index:]:
        if len(row) < 7:
            continue
        for side, offset in (("home_team", 0), ("away_team", 7)):
            if len(row) < offset + 7 or not row[offset] or not row[offset + 1]:
                continue
            player = _parse_player_row(row[offset:offset + 7])
            if player:
                player["source"] = {"page": page_number}
                data[side]["players"].append(player)


def _parse_player_row(row: list[Any]) -> dict[str, Any] | None:
    try:
        if not row[0]:
            return None
        number = str(row[0]).strip()
        if not number.isdigit() or not row[1]:
            return None
        return {
            "number": int(number),
            "name": str(row[1]).strip(),
            "goals": _clean_int(row[2]),
            "yellow": 1 if row[3] and str(row[3]).strip() not in ["-", ""] else 0,
            "two_min": _clean_int(row[4]),
            "red": 1 if row[5] and str(row[5]).strip() not in ["-", ""] else 0,
            "blue": 1 if row[6] and str(row[6]).strip() not in ["-", ""] else 0,
        }
    except Exception:
        return None


def _clean_int(value: Any) -> int:
    if not value:
        return 0
    value = str(value).strip()
    if value in ["-", "", "None"]:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0

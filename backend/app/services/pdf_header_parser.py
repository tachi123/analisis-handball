"""Conservative extraction of labelled facts from Femebal sheet blocks."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


_HEADER_LABELS = {
    "jugado en": "venue",
    "cancha": "court",
    "fecha": "date",
    "hora": "time",
    "categoria division": "category",
    "partido": "match_number",
}
_TEAM_LABELS = {"equipo local": ("home_name", "home_score"), "equipo visitante": ("away_name", "away_score")}
_FIELD_NAMES = (*_HEADER_LABELS.values(), "tournament", "home_name", "away_name", "home_score", "away_score")


def parse_header_blocks(tables: list[list[list[str | None]]], text: str | None, page: int = 1) -> dict[str, Any]:
    """Extract only uniquely labelled values; leave every uncertain fact unresolved."""
    return parse_header_pages([(tables, text, page)])


def parse_header_pages(
    pages: list[tuple[list[list[list[str | None]]], str | None, int]],
    word_pages: dict[int, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Resolve labelled header facts from every page while retaining their source."""
    candidates: dict[str, list[dict[str, Any]]] = {field: [] for field in _FIELD_NAMES}
    for tables, text, page in pages:
        for table_index, table in enumerate(tables):
            for row in table:
                for cell in row:
                    if not cell:
                        continue
                    lines = [line.strip() for line in str(cell).splitlines() if line.strip()]
                    _collect_header_candidate(candidates, lines, page, table_index)
                    _collect_team_candidate(candidates, lines, page, table_index)
        _collect_tournament_candidate(candidates, text, page)

    # Some official sheets render both side labels in a single table cell
    # ("Equip o local Equipo visitante").  Tables cannot retain the two
    # columns, so recover the labelled header from positioned words instead.
    for page, words in (word_pages or {}).items():
        _collect_positioned_team_candidates(candidates, words, page)

    fields = {field: _resolve(field, values) for field, values in candidates.items()}
    warnings = [warning for evidence in fields.values() for warning in evidence["warnings"]]
    return {"fields": fields, "warnings": warnings}


def _collect_header_candidate(candidates: dict[str, list[dict[str, Any]]], lines: list[str], page: int, table: int) -> None:
    for index in range(1, len(lines) + 1):
        label = _normalise_label(" ".join(lines[:index]))
        field = _HEADER_LABELS.get(label)
        if field and len(lines[index:]) == 1:
            raw = "\n".join(lines)
            value = lines[index]
            if field == "time":
                value = _normalise_time(value)
            candidates[field].append(_candidate(value, raw, page, table, " ".join(lines[:index])))
            return


def _collect_team_candidate(candidates: dict[str, list[dict[str, Any]]], lines: list[str], page: int, table: int) -> None:
    for index in range(1, len(lines) + 1):
        fields = _TEAM_LABELS.get(_normalise_label(" ".join(lines[:index])))
        if not fields:
            continue
        raw = "\n".join(lines)
        values = lines[index:]
        scores = [value for value in values if re.fullmatch(r"\d+", value)]
        names = [value for value in values if not re.fullmatch(r"\d+", value)]
        if len(scores) == 1:
            candidates[fields[1]].append(_candidate(int(scores[0]), raw, page, table, " ".join(lines[:index])))
        if len(names) == 1:
            candidates[fields[0]].append(_candidate(names[0], raw, page, table, " ".join(lines[:index])))
        return


def _collect_tournament_candidate(candidates: dict[str, list[dict[str, Any]]], text: str | None, page: int) -> None:
    if not text:
        return
    for line in text.splitlines():
        match = re.fullmatch(r"\s*Torneo\s+(.+?)\s*", line, re.IGNORECASE)
        if match:
            candidates["tournament"].append(_candidate(match.group(1), line, page, None, "Torneo"))


def _collect_positioned_team_candidates(candidates: dict[str, list[dict[str, Any]]], words: list[dict[str, Any]], page: int) -> None:
    """Recover side-specific headers from PDF word coordinates without guessing.

    Recovery is deliberately limited to a recognised pair of local/visitor
    labels and requires exactly one score and one non-empty name block per
    side.  The next ``Goles`` heading bounds the name block, including wrapped
    names on the following visual line.
    """
    rows = _word_rows(words)
    for index, row in enumerate(rows):
        label_text = _normalise_label(" ".join(word["text"] for word in row))
        if "equipo local" not in label_text or "equipo visitante" not in label_text:
            continue
        local = next((word for word in row if _normalise_label(word["text"]) == "local"), None)
        visitor = next((word for word in row if _normalise_label(word["text"]) == "visitante"), None)
        if local is None or visitor is None:
            continue
        local_right = local["x1"]
        visitor_left = min(word["x0"] for word in row if word["x0"] >= visitor["x0"] - 40)
        if visitor_left <= local_right:
            continue
        divider = (local_right + visitor_left) / 2
        bottom = _next_goals_top(rows[index + 1:], row[0]["top"])
        content = [candidate for candidate in rows[index + 1:] if candidate[0]["top"] < bottom]
        score_row = next((candidate for candidate in content if any(re.fullmatch(r"\d+", word["text"]) for word in candidate)), None)
        if score_row is None:
            continue
        scores = _side_tokens(score_row, divider, digits_only=True)
        name_rows = [candidate for candidate in content if candidate is not score_row]
        names = _side_names(name_rows, divider)
        label = "Equip o local / Equipo visitante"
        for side, fields in (("home", _TEAM_LABELS["equipo local"]), ("away", _TEAM_LABELS["equipo visitante"])):
            score_tokens, name = scores[side], names[side]
            raw = "\n".join(" ".join(word["text"] for word in candidate) for candidate in content)
            if len(score_tokens) == 1 and not candidates[fields[1]]:
                candidates[fields[1]].append(_candidate(int(score_tokens[0]), raw, page, None, label))
            if name and not candidates[fields[0]]:
                candidates[fields[0]].append(_candidate(name, raw, page, None, label))


def _word_rows(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    rows: list[list[dict[str, Any]]] = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        if rows and abs(rows[-1][0]["top"] - word["top"]) < 3:
            rows[-1].append(word)
        else:
            rows.append([word])
    return rows


def _next_goals_top(rows: list[list[dict[str, Any]]], minimum: float) -> float:
    return next((row[0]["top"] for row in rows if row[0]["top"] > minimum and any(_normalise_label(word["text"]) == "goles" for word in row)), float("inf"))


def _side_tokens(row: list[dict[str, Any]], divider: float, digits_only: bool) -> dict[str, list[str]]:
    result = {"home": [], "away": []}
    for word in row:
        if bool(re.fullmatch(r"\d+", word["text"])) != digits_only:
            continue
        result["home" if word["x0"] < divider else "away"].append(word["text"])
    return result


def _side_names(rows: list[list[dict[str, Any]]], divider: float) -> dict[str, str | None]:
    result: dict[str, list[str]] = {"home": [], "away": []}
    for row in rows:
        for side, tokens in _side_tokens(row, divider, digits_only=False).items():
            result[side].extend(tokens)
    return {side: " ".join(tokens) or None for side, tokens in result.items()}


def _candidate(value: str | int | None, raw: str, page: int, table: int | None, label: str) -> dict[str, Any]:
    return {"value": value, "raw": raw, "source": {"page": page, "table": table, "label": label}}


def _resolve(field: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    distinct = {str(candidate["value"]): candidate for candidate in candidates if candidate["value"] is not None}
    if len(distinct) == 1:
        evidence = next(iter(distinct.values()))
        warnings = _encoding_warnings(field, evidence["raw"])
        return {**evidence, "confidence": "high", "warnings": warnings}
    reason = "missing" if not distinct else "conflicting"
    warning = f"{field} is {reason} in labelled source blocks"
    return {"value": None, "raw": None, "source": None, "confidence": "unresolved", "warnings": [warning]}


def _normalise_label(value: str) -> str:
    value = value.replace("Equip o", "Equipo")
    value = "".join(char for char in unicodedata.normalize("NFD", value) if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _normalise_time(value: str) -> str:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?", value.strip())
    return f"{int(match.group(1)):02d}:{match.group(2)}" if match and int(match.group(1)) < 24 and int(match.group(2)) < 60 else value


def _encoding_warnings(field: str, raw: str) -> list[str]:
    return [f"{field} contains encoding-degraded source text"] if "�" in raw else []

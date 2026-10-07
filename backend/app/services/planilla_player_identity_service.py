"""Pure name comparison primitives for planilla player identity grouping."""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
import io
from itertools import combinations
import json
import os
from pathlib import Path
import tempfile
import unicodedata
from typing import Any


NAME_SIMILARITY_THRESHOLD = 0.90
CONFLICT_SIMILARITY_THRESHOLD = 2 / 3
OVERRIDE_DOCUMENT_SHAPE = {
    "schema_version": 1,
    "links": [{"action": "accept|merge|split|reject", "left_row_id": "...", "right_row_id": "..."}],
}


def normalize_name(value: str | None) -> str:
    """Return a stable comparison name without changing the raw display value.

    Names are decomposed, stripped of combining marks, case-folded, split at
    punctuation and whitespace, then ordered lexically so given/surname order
    does not affect comparison.
    """
    if not value:
        return ""

    decomposed = unicodedata.normalize("NFD", value)
    folded = "".join(
        character.casefold()
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    tokens = "".join(character if character.isalnum() else " " for character in folded).split()
    return " ".join(sorted(tokens))


def multiset_dice_score(left: str, right: str) -> float:
    """Calculate Sørensen-Dice similarity for two normalized token multisets."""
    left_tokens = left.split()
    right_tokens = right.split()
    if not left_tokens or not right_tokens:
        return 0.0

    overlap = sum((Counter(left_tokens) & Counter(right_tokens)).values())
    return (2 * overlap) / (len(left_tokens) + len(right_tokens))


def name_similarity(left: str | None, right: str | None) -> float:
    """Normalize two raw names and score their token-multiset similarity."""
    return multiset_dice_score(normalize_name(left), normalize_name(right))


def flatten_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten discovery-manifest rosters into deterministic, serializable rows."""
    rows = []
    for record in manifest.get("records", []):
        fields = record.get("fields") or {}
        source_path = record.get("source_path") or ""
        source_stage = source_path.replace("\\", "/").split("/", 1)[0]
        tournament = _field_value(fields.get("tournament"))
        for side, roster in (record.get("rosters") or {}).items():
            team = _field_value(fields.get("home_name" if side == "local" else "away_name"))
            for roster_index, player in enumerate(roster or []):
                page = (player.get("source") or {}).get("page", 0)
                raw_name = player.get("name")
                rows.append(
                    {
                        "row_id": f"{record.get('sha256', '')}:{side}:{page}:{roster_index}",
                        "source_path": source_path,
                        "scope": {
                            "source_stage": source_stage,
                            "tournament": normalize_name(tournament),
                        },
                        "name": raw_name,
                        "normalized_name": normalize_name(raw_name),
                        "team": team,
                        "normalized_team": normalize_name(team),
                        "jersey": _jersey_value(player.get("number")),
                        "stats": {key: player.get(key, 0) for key in ("goals", "yellow", "two_min", "red", "blue")},
                    }
                )
    return sorted(rows, key=lambda row: row["row_id"])


def build_identities(manifest: dict[str, Any], overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build identities, applying the documented ordered override JSON document.

    The document shape is ``{"schema_version": 1, "links": [{"action":
    "accept|merge|split|reject", "left_row_id": "...", "right_row_id": "..."}]}``.
    A later entry for the same unordered row pair replaces its earlier action.
    """
    rows = flatten_manifest(manifest)
    links = []
    by_scope: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        scope = row["scope"]
        by_scope.setdefault((scope["source_stage"], scope["tournament"]), []).append(row)

    parents = {row["row_id"]: row["row_id"] for row in rows}
    for scoped_rows in by_scope.values():
        for left, right in combinations(scoped_rows, 2):
            if not left["normalized_name"] or not right["normalized_name"]:
                continue
            score = multiset_dice_score(left["normalized_name"], right["normalized_name"])
            if score < NAME_SIMILARITY_THRESHOLD:
                if _is_same_team_name_collision(left, right, score):
                    links.append(_below_threshold_conflict(left, right, score))
                continue
            link = _classify_link(left, right, score)
            links.append(link)
    final_overrides = _validate_overrides(overrides, parents)
    for link in links:
        pair = _pair_key(link["left_row_id"], link["right_row_id"])
        if link["tier"] == "auto_group" and final_overrides.get(pair, {}).get("action") not in {"split", "reject"}:
            _union(parents, *pair)
    for pair, override in final_overrides.items():
        if override["action"] in {"accept", "merge"}:
            _union(parents, *pair)
    for pair, override in final_overrides.items():
        if override["action"] in {"split", "reject"} and _find(parents, pair[0]) == _find(parents, pair[1]):
            raise ValueError(f"Override {override['action']} contradicts a transitive component: {pair[0]}, {pair[1]}")

    members: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        members.setdefault(_find(parents, row["row_id"]), []).append(row)
    identities = [_identity(group, _component_provenance(group, final_overrides)) for group in members.values()]
    return {
        "schema_version": 1,
        "identities": sorted(identities, key=lambda item: (item["scope"]["source_stage"], item["scope"]["tournament"], item["names"], item["member_row_ids"][0])),
        "links": sorted(links, key=lambda link: (link["left_row_id"], link["right_row_id"])),
        "rows": rows,
    }


def write_identity_artifacts(result: dict[str, Any], output_directory: str | Path) -> None:
    """Atomically write deterministic UTF-8/LF review artifacts for a result."""
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    artifacts = _artifact_contents(result)
    temporary_paths: list[tuple[Path, Path]] = []
    try:
        for filename, content in artifacts.items():
            descriptor, temporary_name = tempfile.mkstemp(prefix=f".{filename}.", dir=output_directory)
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            temporary_paths.append((temporary_path, output_directory / filename))
        for temporary_path, destination in temporary_paths:
            os.replace(temporary_path, destination)
    finally:
        for temporary_path, _ in temporary_paths:
            if temporary_path.exists():
                temporary_path.unlink()


def _validate_overrides(overrides: dict[str, Any] | None, parents: dict[str, str]) -> dict[tuple[str, str], dict[str, Any]]:
    if overrides is None:
        return {}
    if not isinstance(overrides, dict) or overrides.get("schema_version") != 1 or not isinstance(overrides.get("links"), list):
        raise ValueError("Overrides must match schema_version 1 with a links array")
    final: dict[tuple[str, str], dict[str, Any]] = {}
    for sequence, item in enumerate(overrides["links"]):
        if not isinstance(item, dict) or set(item) != {"action", "left_row_id", "right_row_id"}:
            raise ValueError("Each override must contain only action, left_row_id, and right_row_id")
        action, left, right = item["action"], item["left_row_id"], item["right_row_id"]
        if action not in {"accept", "merge", "split", "reject"}:
            raise ValueError(f"Unknown override action: {action}")
        if not isinstance(left, str) or not isinstance(right, str) or left not in parents or right not in parents or left == right:
            raise ValueError("Override row IDs must name two distinct manifest rows")
        final[_pair_key(left, right)] = {"action": action, "sequence": sequence, "left_row_id": left, "right_row_id": right}
    return final


def _pair_key(left: str, right: str) -> tuple[str, str]:
    return tuple(sorted((left, right)))


def _component_provenance(group: list[dict[str, Any]], overrides: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    member_ids = {row["row_id"] for row in group}
    return [override for _, override in sorted(overrides.items()) if {override["left_row_id"], override["right_row_id"]} <= member_ids]


def _field_value(field: Any) -> str | None:
    return field.get("value") if isinstance(field, dict) else field


def _jersey_value(value: Any) -> int | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _classify_link(left: dict[str, Any], right: dict[str, Any], score: float) -> dict[str, Any]:
    same_team = left["normalized_team"] == right["normalized_team"]
    if left["normalized_team"] and right["normalized_team"] and not same_team:
        tier, reasons = "review", ["different_team"]
    elif not left["normalized_team"] or not right["normalized_team"]:
        tier, reasons = "review", ["missing_team_label"]
    else:
        reasons = ["same_team"]
        if left["jersey"] is None or right["jersey"] is None:
            reasons.append("missing_jersey")
        elif left["jersey"] != right["jersey"]:
            reasons.append("jersey_variation")
        else:
            reasons.append("same_jersey")
        tier = "auto_group"
    return {
        "left_row_id": left["row_id"], "right_row_id": right["row_id"], "score": score,
        "tier": tier, "reasons": reasons,
        "evidence": {"left": _evidence(left), "right": _evidence(right)},
    }


def _is_same_team_name_collision(left: dict[str, Any], right: dict[str, Any], score: float) -> bool:
    """Identify materially similar, below-threshold names within one team scope."""
    return (
        CONFLICT_SIMILARITY_THRESHOLD <= score < NAME_SIMILARITY_THRESHOLD
        and bool(left["normalized_team"])
        and left["normalized_team"] == right["normalized_team"]
        and _shared_normalized_token_count(left["normalized_name"], right["normalized_name"]) >= 2
    )


def _shared_normalized_token_count(left: str, right: str) -> int:
    """Count shared tokens while retaining normalized-name multiset semantics."""
    return sum((Counter(left.split()) & Counter(right.split())).values())


def _below_threshold_conflict(left: dict[str, Any], right: dict[str, Any], score: float) -> dict[str, Any]:
    return {
        "left_row_id": left["row_id"], "right_row_id": right["row_id"], "score": score,
        "tier": "conflict", "reasons": ["same_team", "below_threshold_name_collision"],
        "evidence": {"left": _evidence(left), "right": _evidence(right)},
    }


def _evidence(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row[key] for key in ("name", "normalized_name", "team", "normalized_team", "jersey")}


def _find(parents: dict[str, str], row_id: str) -> str:
    if parents[row_id] != row_id:
        parents[row_id] = _find(parents, parents[row_id])
    return parents[row_id]


def _union(parents: dict[str, str], left: str, right: str) -> None:
    left_root, right_root = _find(parents, left), _find(parents, right)
    if left_root != right_root:
        parents[max(left_root, right_root)] = min(left_root, right_root)


def _identity(group: list[dict[str, Any]], provenance: list[dict[str, Any]]) -> dict[str, Any]:
    group = sorted(group, key=lambda row: row["row_id"])
    member_ids = [row["row_id"] for row in group]
    automatic = not any(item["action"] in {"accept", "merge"} for item in provenance)
    jerseys = sorted({row["jersey"] for row in group if row["jersey"] is not None})
    return {
        "id": "identity-v1-" + hashlib.sha256(member_ids[0].encode()).hexdigest(),
        "scope": group[0]["scope"],
        "tier": "auto_group" if len(group) > 1 and automatic else "review",
        "member_row_ids": member_ids,
        "names": sorted({row["name"] for row in group if row["name"]}),
        "teams": sorted({row["team"] for row in group if row["team"]}),
        "jerseys": jerseys,
        "notes": ["jersey_variation"] if len(jerseys) > 1 else [],
        "preview": {key: sum(row["stats"][key] or 0 for row in group) for key in ("goals", "yellow", "two_min", "red", "blue")} | {"appearances": len(group)},
        "provenance": provenance,
    }


def _artifact_contents(result: dict[str, Any]) -> dict[str, str]:
    identities = result["identities"]
    rows_by_id = {row["row_id"]: row for row in result["rows"]}
    identity_document = {key: result[key] for key in ("schema_version", "identities", "links")}
    return {
        "identities.json": json.dumps(identity_document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        "identities.csv": _csv_content(identities, rows_by_id),
        "conflicts.md": _conflicts_markdown(result["links"]),
        "identity-summary.json": json.dumps(_summary(result), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    }


def _csv_content(identities: list[dict[str, Any]], rows_by_id: dict[str, dict[str, Any]]) -> str:
    fields = ("identity_id", "tier", "source_stage", "tournament", "row_id", "name", "normalized_name", "team", "jersey", "appearances", "goals", "yellow", "two_min", "red", "blue")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for identity in identities:
        for row_id in identity["member_row_ids"]:
            row = rows_by_id[row_id]
            writer.writerow({
                "identity_id": identity["id"], "tier": identity["tier"],
                "source_stage": identity["scope"]["source_stage"], "tournament": identity["scope"]["tournament"],
                "row_id": row_id, "name": row["name"] or "", "normalized_name": row["normalized_name"],
                "team": row["team"] or "", "jersey": "" if row["jersey"] is None else row["jersey"],
                **identity["preview"],
            })
    return output.getvalue()


def _conflicts_markdown(links: list[dict[str, Any]]) -> str:
    conflicts = [link for link in links if link["tier"] == "conflict"]
    lines = ["# Identity Conflicts", ""]
    for link in conflicts:
        left, right = link["evidence"]["left"], link["evidence"]["right"]
        lines.extend((
            f"## {link['left_row_id']} <> {link['right_row_id']}",
            f"- Score: {link['score']:.2f}",
            f"- Reasons: {', '.join(link['reasons'])}",
            f"- Left: {left['name'] or ''} | {left['team'] or ''} | jersey {left['jersey'] if left['jersey'] is not None else ''}",
            f"- Right: {right['name'] or ''} | {right['team'] or ''} | jersey {right['jersey'] if right['jersey'] is not None else ''}", "",
        ))
    return "\n".join(lines)


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    identities, links, rows = result["identities"], result["links"], result["rows"]
    return {
        "schema_version": 1,
        "input": {"row_count": len(rows), "source_paths": sorted({row["source_path"] for row in rows})},
        "identity_count": len(identities),
        "link_count": len(links),
        "identity_tier_counts": dict(sorted(Counter(identity["tier"] for identity in identities).items())),
        "link_tier_counts": dict(sorted(Counter(link["tier"] for link in links).items())),
        "aggregate_totals": {key: sum(identity["preview"][key] for identity in identities) for key in ("appearances", "goals", "yellow", "two_min", "red", "blue")},
    }

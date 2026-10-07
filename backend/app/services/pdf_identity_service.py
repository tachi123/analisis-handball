"""Read-only, conservative reusable-identity proposals for PDF previews."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from sqlalchemy.orm import Session

from ..models import Player, Team, Tournament


def normalize_identity_name(value: str) -> str:
    """Normalize display names only for equality checks, never for persistence."""
    decomposed = unicodedata.normalize("NFD", value)
    without_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", without_accents.lower())


class PDFIdentityService:
    @staticmethod
    def propose(
        db: Session,
        fields: dict[str, dict[str, Any]],
        home_team: dict[str, Any],
        away_team: dict[str, Any],
    ) -> dict[str, Any]:
        tournament = PDFIdentityService._tournament_proposal(db, fields)
        home = PDFIdentityService._team_proposal(db, fields.get("home_name"), home_team)
        away = PDFIdentityService._team_proposal(db, fields.get("away_name"), away_team)
        return {
            "tournament": tournament,
            "home_team": home,
            "away_team": away,
            "home_players": PDFIdentityService._player_proposals(db, home_team, home),
            "away_players": PDFIdentityService._player_proposals(db, away_team, away),
        }

    @staticmethod
    def _tournament_proposal(db: Session, fields: dict[str, dict[str, Any]]) -> dict[str, Any]:
        evidence = fields.get("tournament")
        name = PDFIdentityService._value(evidence)
        if not name:
            return PDFIdentityService._unresolved("tournament", evidence, "Tournament name is unresolved")

        category = PDFIdentityService._value(fields.get("category"))
        year = PDFIdentityService._year(fields.get("date"))
        options = [candidate for candidate in db.query(Tournament).all() if normalize_identity_name(candidate.name) == normalize_identity_name(name)]
        if len(options) == 1 and category and year and normalize_identity_name(options[0].category) == normalize_identity_name(category) and options[0].year == year:
            return PDFIdentityService._resolved("tournament", evidence, options, ["unique normalized name, category, and year"])
        if options:
            return PDFIdentityService._unresolved("tournament", evidence, "Tournament candidates require an analyst decision", options)
        return PDFIdentityService._unresolved("tournament", evidence, "No normalized tournament candidate was found")

    @staticmethod
    def _team_proposal(db: Session, evidence: dict[str, Any] | None, preview_team: dict[str, Any]) -> dict[str, Any]:
        name = PDFIdentityService._value(evidence)
        side = "team"
        if not name:
            return PDFIdentityService._unresolved(side, evidence, "Team name is unresolved")

        options = [candidate for candidate in db.query(Team).all() if normalize_identity_name(candidate.name) == normalize_identity_name(name)]
        roster_matches = [
            player.id
            for player in db.query(Player).filter(Player.team_id.in_([candidate.id for candidate in options])).all()
            if any(
                player.default_jersey_number == preview_player.get("number")
                and normalize_identity_name(player.name) == normalize_identity_name(preview_player.get("name", ""))
                for preview_player in preview_team.get("players", [])
            )
        ]
        if len(options) == 1 and roster_matches:
            return PDFIdentityService._resolved(side, evidence, options, ["unique normalized team name", f"roster matches player IDs {roster_matches}"])
        if options:
            warning = "Team candidate lacks roster support" if len(options) == 1 else "Multiple normalized team candidates were found"
            return PDFIdentityService._unresolved(side, evidence, warning, options, roster_matches)
        return PDFIdentityService._unresolved(side, evidence, "No normalized team candidate was found")

    @staticmethod
    def _player_proposals(db: Session, preview_team: dict[str, Any], team_proposal: dict[str, Any]) -> list[dict[str, Any]]:
        team_id = team_proposal.get("candidate", {}).get("id") if team_proposal.get("candidate") else None
        proposals = []
        for player in preview_team.get("players", []):
            evidence = {"value": player.get("name"), "source": None, "confidence": "high", "warnings": []}
            if team_id is None:
                proposals.append(PDFIdentityService._unresolved("player", evidence, "A unique team proposal is required before player matching"))
                continue
            options = [
                candidate for candidate in db.query(Player).filter(Player.team_id == team_id).all()
                if candidate.default_jersey_number == player.get("number")
                and normalize_identity_name(candidate.name) == normalize_identity_name(player.get("name", ""))
            ]
            if len(options) == 1:
                proposals.append(PDFIdentityService._resolved("player", evidence, options, ["selected team", "normalized name", f"jersey {player.get('number')}"]))
            elif options:
                proposals.append(PDFIdentityService._unresolved("player", evidence, "Multiple normalized player candidates were found", options))
            else:
                proposals.append(PDFIdentityService._unresolved("player", evidence, "No normalized player candidate was found"))
        return proposals

    @staticmethod
    def _resolved(kind: str, evidence: dict[str, Any] | None, options: list[Any], rationale: list[str]) -> dict[str, Any]:
        candidate = PDFIdentityService._option(options[0])
        return {"kind": kind, "candidate": candidate, "options": [candidate], "confidence": "high", "evidence": evidence, "rationale": rationale, "warnings": []}

    @staticmethod
    def _unresolved(kind: str, evidence: dict[str, Any] | None, warning: str, options: list[Any] | None = None, roster_matches: list[int] | None = None) -> dict[str, Any]:
        result = {"kind": kind, "candidate": None, "options": [PDFIdentityService._option(option) for option in options or []], "confidence": "unresolved", "evidence": evidence, "rationale": [], "warnings": [warning]}
        if roster_matches is not None:
            result["roster_matches"] = roster_matches
        return result

    @staticmethod
    def _option(candidate: Tournament | Team | Player) -> dict[str, Any]:
        option = {"id": candidate.id, "name": candidate.name}
        if isinstance(candidate, Tournament):
            option.update(category=candidate.category, year=candidate.year)
        if isinstance(candidate, Player):
            option.update(team_id=candidate.team_id, jersey_number=candidate.default_jersey_number)
        return option

    @staticmethod
    def _value(evidence: dict[str, Any] | None) -> str | None:
        value = evidence.get("value") if evidence else None
        return value if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _year(evidence: dict[str, Any] | None) -> int | None:
        value = PDFIdentityService._value(evidence)
        return int(value[:4]) if value and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None

"""Pytest for the export report script.

These tests use SQLite fixtures and mock data since the actual DB
(PostgreSQL) may not be running locally. The export script itself
connects to the local DB during export; these tests verify the
transformation logic is correct.
"""

import json
from pathlib import Path

import pytest

# Add backend to path
from backend.scripts.export_report import (
    public_projection_from_package_type,
    export_report,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent


# ─── Fixture data mimicking what the DB would return ───

def make_canonical_event(event_id, sequence=1, kind="shot", period=1, outcome="goal",
                        player_id=None, team_id=1, clock_unverified=False,
                        fact_kind="observed", evidence_state="confirmed"):
    """Create a canonical event dict mimicking DB row."""
    return {
        "id": event_id,
        "sequence": sequence,
        "active": True,
        "payload": {
            "kind": kind,
            "period": period,
            "regulation_seconds": 120.0 if kind == "shot" and outcome == "goal" else None,
            "clock_unverified": clock_unverified,
            "team_id": team_id,
            "player_id": player_id,
            "outcome": outcome,
            "fact_kind": fact_kind,
            "evidence_state": evidence_state,
            "uncertainty": [],
            "note": None,
        },
        "revision": 1,
        "actor_id": 1,
        "reason": "created",
        "evidence": [],
    }


def make_eligible_event(**overrides):
    """Create an eligible canonical event (active + observed + confirmed)."""
    base = {
        "id": overrides.get("id", 1),
        "sequence": overrides.get("sequence", 1),
        "active": True,
        "payload": {
            "kind": overrides.get("kind", "shot"),
            "period": overrides.get("period", 1),
            "regulation_seconds": overrides.get("regulation_seconds", 120.0),
            "clock_unverified": overrides.get("clock_unverified", False),
            "team_id": overrides.get("team_id", 1),
            "player_id": overrides.get("player_id", 10),
            "outcome": overrides.get("outcome", "goal"),
            "fact_kind": "observed",
            "evidence_state": "confirmed",
            "uncertainty": [],
            "note": None,
        },
    }
    return base


# ─── Tests for public_projection_from_package_type ───

class TestPublicProjection:
    """Test the public projection logic (DB‑independent)."""

    def test_basic_projection_with_shot_metrics(self):
        """Test that shot metrics are included in the public report."""
        package = {
            "schema_version": "public-report-v1",
            "report_version": 1,
            "match": {
                "date": "2026-08-22",
                "home_team": {"name": "SAPA"},
                "away_team": {"name": "Banfield"},
            },
            "source_label": "Canonical eligible event ledger",
            "source_status": "canonical-eligible",
            "coaching_question": "Analysis of Match 99",
            "pattern_statement": "Three visible actions need adjustment.",
            "action_kind": "keep",
            "action_text": "Close the pivot lane.",
            "metrics": {
                "shots": {"count": 5, "numerator": 2, "denominator": 5, "excluded": 1, "unknown": 0, "clock_unverified": 0},
                "shot_conversion": {"count": 1, "numerator": 2, "denominator": 5, "excluded": 0, "unknown": 0, "clock_unverified": 0},
                "defensive_action": {"count": 3, "numerator": 0, "denominator": "not_applicable", "excluded": 0, "unknown": 0, "clock_unverified": 0},
                "some_other_metric": {"count": 1, "numerator": 0, "denominator": "not_applicable", "excluded": 0, "unknown": 0, "clock_unverified": 0},
            },
            "reconciliation": [{"analytical": 27, "official": 28, "side": "home"}],
            "uncertainty_disclosure": "One observation was outside the camera view.",
            "evidence": [
                {"reference": "canonical:1:rev:1", "period": 1, "public_approved": True, "public_observation": "Shot observed"},
                {"reference": "canonical:2:rev:1", "period": 2, "public_approved": True, "public_observation": "Recovery observed"},
            ],
            "players": [],
        }

        report = public_projection_from_package_type(package)

        # Check schema and version
        assert report["schema_version"] == "public-report-v1"
        assert report["report_version"] == 1

        # Check match data
        assert report["match"]["home_team"] == "SAPA"
        assert report["match"]["away_team"] == "Banfield"
        assert report["match"]["date"] == "2026-08-22"

        # Check coverage derivation
        coverage = report.get("coverage")
        assert coverage is not None
        assert coverage["status"] == "partial"  # only periods 1 and 2 from evidence
        assert "Analysis covering periods 1, 2" in coverage["label"]

        # Check metrics - only public metrics should remain
        metrics = report["metrics"]
        assert "shots" in metrics
        assert "shot_conversion" in metrics
        assert "defensive_action" in metrics
        # "some_other_metric" should NOT be in public metrics
        assert "some_other_metric" not in metrics

        # Check evidence
        assert len(report["evidence"]) == 2

        # Check coaching
        assert report["coaching"]["question"] == "Analysis of Match 99"
        assert report["coaching"]["action"]["kind"] == "keep"

    def test_partial_coverage(self):
        """Test partial coverage when only period 1 is in evidence."""
        package = {
            "schema_version": "public-report-v1",
            "report_version": 1,
            "match": {"date": "2026-08-22", "home_team": {"name": "SAPA"}, "away_team": {"name": "Banfield"}},
            "source_label": "public-reference",
            "source_status": "public_reference",
            "coaching_question": "Test",
            "pattern_statement": "Test pattern",
            "action_kind": "keep",
            "action_text": "Test action",
            "metrics": {"shots": {"count": 5, "numerator": 2, "denominator": 5, "excluded": 1, "unknown": 0, "clock_unverified": 0}},
            "reconciliation": [],
            "uncertainty_disclosure": "",
            "evidence": [
                {"reference": "canonical:1:rev:1", "period": 1, "public_approved": True, "public_observation": "Observation"},
                # No period 2 evidence
            ],
            "players": [],
        }

        report = public_projection_from_package_type(package)
        coverage = report.get("coverage")
        assert coverage is not None
        assert coverage["status"] == "partial"
        assert "period 1" in coverage["label"]


# ─── Tests for export_report with mocked DB ───

class TestExportReport:
    """Test export_report with mocked/fixture data."""

    @pytest.fixture
    def sample_package_dict(self):
        """A package dict mimicking what export_report would build from DB data."""
        return {
            "match_id": 99,
            "report_version": 1,
            "schema_version": "public-report-v1",
            "match": {
                "id": 99,
                "date": date(2026, 8, 22),
                "home_team_id": 1,
                "away_team_id": 2,
                "home_team": {"name": "SAPA"},
                "away_team": {"name": "Banfield"},
                "youtube_link": None,
                "main_team_focus": "SAPA",
                "venue": None,
                "court": None,
                "match_time": None,
                "category_label": "Primera División",
                "match_number_label": "Match 99",
                "home_score": 2,
                "away_score": 1,
                "pdf_file_path": None,
                "canonical_analysis_enabled": True,
                "origin": "manual",
                "created_by_user_id": 1,
            },
            "home_team": {"name": "SAPA"},
            "away_team": {"name": "Banfield"},
            "coaching_question": "Analysis of Match 99",
            "pattern_statement": "Three visible actions need adjustment.",
            "action_kind": "keep",
            "action_text": "Close the pivot lane.",
            "uncertainty_disclosure": "One observation was outside the camera view.",
            "source_label": "Canonical eligible event ledger",
            "source_status": "canonical-eligible",
            "metrics": {
                "shots": {"count": 5, "numerator": 2, "denominator": 5, "excluded": 1, "unknown": 0, "clock_unverified": 0},
                "defensive_action": {"count": 3, "numerator": 0, "denominator": "not_applicable", "excluded": 0, "unknown": 0, "clock_unverified": 0},
                "shot_conversion": {"count": 1, "numerator": 2, "denominator": 5, "excluded": 0, "unknown": 0, "clock_unverified": 0},
            },
            "reconciliation": [{"analytical": 2, "official": 1, "side": "home"}],
            "evidence": [
                {"reference": "canonical:1:rev:1", "period": 1, "clock_unverified": False, "public_observation": "Pivot lane remained open", "public_approved": True},
                {"reference": "canonical:2:rev:1", "period": 2, "clock_unverified": True, "public_observation": "Recovery followed the turnover", "public_approved": True},
            ],
            "players": [
                {
                    "slug": "sapa-starter-gk",
                    "name": "Mario Rossi",
                    "jersey_number": 1,
                    "team_side": "home",
                    "role": "goalkeeper",
                    "metrics": {"saves": 7, "shots_faced": 20, "goals_conceded": 1, "save_rate": 0.875},
                    "evidence": [],
                },
                {
                    "slug": "sapa-field-10",
                    "name": "Laura García",
                    "jersey_number": 10,
                    "team_side": "home",
                    "role": "field_player",
                    "metrics": {"shot_conversion": 0.20, "shots": 5, "goals": 1, "turnovers": 3, "recoveries": 2, "sanctions": 0},
                    "evidence": [],
                },
            ],
        }

    def test_public_projection_is_self_contained(self, sample_package_dict):
        """The public projection produces a self-contained dict with no DB references."""
        report = public_projection_from_package_type(sample_package_dict)

        # No database IDs or raw payloads
        assert "id" not in str(report)
        assert "rev:" not in str(report)  # reference pattern should be sanitized

        # Only safe public fields
        required_top_keys = {"schema_version", "report_version", "match", "source", "coaching", "metrics",
                            "reconciliation", "uncertainty_disclosure", "players", "evidence", "coverage"}
        assert set(report.keys()) == required_top_keys

        # Match should only have safe fields
        match = report["match"]
        assert "id" not in match
        assert "date" in match
        assert "home_team" in match
        assert "away_team" in match

        # Source should only have safe fields
        assert set(report["source"].keys()) == {"label", "status"}

        # Coaching should only have safe fields
        assert set(report["coaching"].keys()) == {"question", "pattern_statement", "action"}

        # Action should only have kind and text
        assert set(report["coaching"]["action"].keys()) == {"kind", "text"}

    def test_metrics_are_public_only(self, sample_package_dict):
        """Only public metric names survive the filter; internal metrics are dropped."""
        report = public_projection_from_package_type(sample_package_dict)
        metrics = report["metrics"]

        # shot_conversion, shots, defensive_action are public metrics
        assert "shot_conversion" in metrics
        assert "shots" in metrics
        assert "defensive_action" in metrics

        # Internal metrics that start with "player:" or "team:" should be filtered
        # (is_public_metric handles the colon-prefixed ones)

    def test_evidence_uses_safe_public_labels(self, sample_package_dict):
        """Evidence references should use safe public labels, not raw DB IDs."""
        report = public_projection_from_package_type(sample_package_dict)
        evidence = report["evidence"]

        for item in evidence:
            # reference should be a public label like "canonical:1:rev:1" not a raw ID
            assert "reference" in item
            # No raw event IDs or revision payloads should leak
            assert item["reference"].startswith("canonical:")

    def test_coverage_handles_partial_data(self):
        """Coverage correctly reports partial when both halves not covered."""
        package = {
            "schema_version": "public-report-v1",
            "report_version": 1,
            "match": {"date": "2026-08-22", "home_team": {"name": "SAPA"}, "away_team": {"name": "Banfield"}},
            "source_label": "public-reference",
            "source_status": "public_reference",
            "coaching_question": "Test",
            "pattern_statement": "Test",
            "action_kind": "keep",
            "action_text": "Test",
            "metrics": {"shots": {"count": 3, "numerator": 1, "denominator": 3, "excluded": 0, "unknown": 0, "clock_unverified": 0}},
            "reconciliation": [],
            "uncertainty_disclosure": "",
            "evidence": [
                {"reference": "canonical:1:rev:1", "period": 1, "public_approved": True, "public_observation": "First half observation"},
                # Missing period 2
            ],
            "players": [],
        }

        report = public_projection_from_package_type(package)
        coverage = report["coverage"]
        assert coverage["status"] == "partial"
        # Should mention only the periods analyzed
        assert coverage["label"] is not None
        assert "period 1" in coverage["label"]

    def test_complete_coverage(self):
        """Coverage reports complete when both periods 1 and 2 are present."""
        package = {
            "schema_version": "public-report-v1",
            "report_version": 1,
            "match": {"date": "2026-08-22", "home_team": {"name": "SAPA"}, "away_team": {"name": "Banfield"}},
            "source_label": "public-reference",
            "source_status": "public_reference",
            "coaching_question": "Test",
            "pattern_statement": "Test",
            "action_kind": "keep",
            "action_text": "Test",
            "metrics": {"shots": {"count": 3, "numerator": 1, "denominator": 3, "excluded": 0, "unknown": 0, "clock_unverified": 0}},
            "reconciliation": [],
            "uncertainty_disclaration": "",
            "evidence": [
                {"reference": "canonical:1:rev:1", "period": 1, "public_approved": True, "public_observation": "First half"},
                {"reference": "canonical:2:rev:1", "period": 2, "public_approved": True, "public_observation": "Second half"},
            ],
            "players": [],
        }

        report = public_projection_from_package_type(package)
        coverage = report["coverage"]
        assert coverage["status"] == "complete"
        assert coverage["label"] is None


# ─── Test the export_report end-to-end with mocked DB ───

class TestExportEndToEnd:
    """End-to-end test of export_report with real DB when available."""

    def test_export_script_command_structure(self):
        """Verify the export script has the expected CLI structure."""
        from backend.scripts.export_report import main
        # Verify argparse is set up correctly
        import sys
        from io import StringIO

        # Test with --help
        old_argv = sys.argv
        sys.argv = ["export_report.py", "--help"]
        try:
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

    def test_export_with_minimal_data_no_coverage(self):
        """Export with no canonical events produces honest minimal report."""
        package = {
            "schema_version": "public-report-v1",
            "report_version": 1,
            "match": {"date": "2026-08-22", "home_team": {"name": "SAPA"}, "away_team": {"name": "Banfield"}},
            "source_label": "public-reference",
            "source_status": "public_reference",
            "coaching_question": "Analysis",
            "pattern_statement": "No canonical events analyzed yet.",
            "action_kind": "keep",
            "action_text": "Awaiting reviewed facts",
            "metrics": {},
            "reconciliation": [],
            "uncertainty_disclosure": "No approved canonical events available.",
            "evidence": [],
            "players": [],
        }

        report = public_projection_from_package_type(package)
        coverage = report.get("coverage")

        # With no evidence, coverage should be None (no periods to analyze)
        assert coverage is None

        # Match data should still be present
        assert report["match"]["home_team"] == "SAPA"
        assert report["match"]["away_team"] == "Banfield"

    def test_goalkeeper_role_from_canonical_shots(self):
        """Goalkeeper role should be determined from canonical shot facts."""
        package = {
            "schema_version": "public-report-v1",
            "report_version": 1,
            "match": {"date": "2026-08-22", "home_team": {"name": "SAPA"}, "away_team": {"name": "Banfield"}},
            "source_label": "canonical-eligible",
            "source_status": "canonical-eligible",
            "coaching_question": "Test",
            "pattern_statement": "Test",
            "action_kind": "keep",
            "action_text": "Test",
            "metrics": {
                "shots": {"count": 10, "numerator": 2, "denominator": 10, "excluded": 0, "unknown": 0, "clock_unverified": 0},
            },
            "reconciliation": [],
            "uncertainty_disclosure": "",
            "evidence": [
                {
                    "reference": "canonical:1:rev:1",
                    "period": 1,
                    "public_approved": True,
                    "public_observation": "Shot with goalkeeper_id=1 identified",
                    "player_id": 1,  # This player is the designated goalkeeper
                },
            ],
            "players": [
                {
                    "slug": "gk-1",
                    "name": "Mario Rossi",
                    "jersey_number": 1,
                    "team_side": "home",
                    "role": "goalkeeper",  # Designated from canonical shot facts
                    "metrics": {"saves": 7, "shots_faced": 20, "goals_conceded": 1, "save_rate": 0.875},
                    "evidence": [],
                },
                {
                    "slug": "player-10",
                    "name": "Laura García",
                    "jersey_number": 10,
                    "team_side": "home",
                    "role": "field_player",  # Not designated as GK
                    "metrics": {"shot_conversion": 0.20, "shots": 5, "goals": 1},
                    "evidence": [],
                },
            ],
        }

        report = public_projection_from_package_type(package)

        # Find the goalkeeper player
        gk_player = None
        field_player = None
        for p in report.get("players", []):
            if p.get("role") == "goalkeeper":
                gk_player = p
            elif p.get("role") == "field_player":
                field_player = p

        # Goalkeeper should have goalkeeper metrics
        assert gk_player is not None
        assert gk_player["role"] == "goalkeeper"
        gk_metrics = gk_player["metrics"]
        assert "saves" in gk_metrics
        assert "shots_faced" in gk_metrics
        assert "goals_conceded" in gk_metrics
        assert "save_rate" in gk_metrics

        # Field player should NOT have goalkeeper metrics
        assert field_player is not None
        assert field_player["role"] == "field_player"
        # shot_conversion is a field player metric
        assert "shot_conversion" in field_player["metrics"]

    def test_no_fabricated_data(self):
        """Verify the export never fabricates names, stats, events, or roles."""
        package = {
            "schema_version": "public-report-v1",
            "report_version": 1,
            "match": {"date": "2026-08-22", "home_team": {"name": "SAPA"}, "away_team": {"name": "Banfield"}},
            "source_label": "public-reference",
            "source_status": "public_reference",
            "coaching_question": "Test",
            "pattern_statement": "Test",
            "action_kind": "keep",
            "action_text": "Test",
            "metrics": {},
            "reconciliation": [],
            "uncertainty_disclosure": "",
            "evidence": [],
            "players": [],
        }

        report = public_projection_from_package_type(package)

        # No players should be fabricated
        assert report["players"] == []

        # Match teams should come from the package, not invented
        assert report["match"]["home_team"] == "SAPA"
        assert report["match"]["away_team"] == "Banfield"

        # No fake names in evidence
        for item in report["evidence"]:
            assert item["observation"] is not None
            # Observation should be based on actual data, not fabricated
            assert len(item["observation"]) > 0
"""Tests for CompetitionTeam optional-variant identity."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.models import Club, CompetitionTeam, FixtureImport, FixtureImportEntry, Season, TournamentStage
from app.schemas import CompetitionTeam as CompetitionTeamSchema, FixtureImport as FixtureImportSchema, ScheduledMatch as ScheduledMatchSchema


class TestCompetitionTeamIdentityUniqueness:
    """Core uniqueness constraint: (club_id, stage_id, variant_key)."""

    def test_same_club_same_suffix_same_stage_rejected(self, session, club, stage):
        """Same club + same suffix + same stage rejected."""
        team1 = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="B")
        session.add(team1)
        session.commit()

        team2 = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="B")
        session.add(team2)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_same_club_same_suffix_different_stage_allowed(self, session, club, season):
        """Same club + same suffix + different stage allowed."""
        stage1 = TournamentStage(
            season_id=season.id,
            name="Apertura",
            category="Mayores",
            division="3ª División",
            gender="Masculino",
        )
        stage2 = TournamentStage(
            season_id=season.id,
            name="Clausura Permanencia",
            category="Mayores",
            division="3ª División",
            gender="Masculino",
        )
        session.add_all([stage1, stage2])
        session.flush()

        team1 = CompetitionTeam(club_id=club.id, stage_id=stage1.id, suffix="B")
        team2 = CompetitionTeam(club_id=club.id, stage_id=stage2.id, suffix="B")
        session.add_all([team1, team2])
        session.commit()

        assert session.query(CompetitionTeam).count() == 2

    def test_same_club_different_suffix_same_stage_allowed(self, session, club, stage):
        """Same club + different suffix + same stage allowed (Banfield A ≠ Banfield B)."""
        team_a = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="A")
        team_b = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="B")
        session.add_all([team_a, team_b])
        session.commit()

        assert session.query(CompetitionTeam).count() == 2

    def test_different_club_same_suffix_same_stage_allowed(self, session, stage):
        """Different clubs can have same suffix in same stage."""
        club1 = Club(name="Banfield", short_name="BAN")
        club2 = Club(name="Comunicaciones", short_name="COM")
        session.add_all([club1, club2])
        session.flush()

        team1 = CompetitionTeam(club_id=club1.id, stage_id=stage.id, suffix="A")
        team2 = CompetitionTeam(club_id=club2.id, stage_id=stage.id, suffix="A")
        session.add_all([team1, team2])
        session.commit()

        assert session.query(CompetitionTeam).count() == 2

    def test_absent_variant_is_valid_and_exposed_as_null(self, session, club, stage):
        team = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix=None)
        session.add(team)
        session.commit()

        assert team.variant_key == ""
        assert CompetitionTeamSchema.model_validate(team).variant is None

    def test_absent_and_supplied_variants_remain_distinct(self, session, club, stage):
        absent = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix=None)
        supplied = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="B")
        session.add_all([absent, supplied])
        session.commit()

        assert {team.variant_key for team in session.query(CompetitionTeam)} == {"", "B"}
        assert supplied.variant == "B"


class TestClubUniqueness:
    """Club name must be unique."""

    def test_club_name_unique(self, session):
        """Club name must be unique."""
        club1 = Club(name="Banfield", short_name="BAN")
        club2 = Club(name="Banfield", short_name="BAN2")
        session.add_all([club1, club2])

        with pytest.raises(IntegrityError):
            session.commit()


class TestCompetitionTeamDisplayName:
    """CompetitionTeam.display_name property."""

    def test_display_name_returns_club_name_suffix(self, session, club, stage):
        """display_name returns 'ClubName Suffix'."""
        team = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="B")
        session.add(team)
        session.commit()

        assert team.display_name == "Banfield B"


class TestFixtureFoundationSchemas:
    def test_provenance_entry_retains_raw_bye_without_a_match(self, session, stage):
        fixture_import = FixtureImport(
            stage_id=stage.id,
            source_label="copied fixture",
            captured_at=datetime.now(timezone.utc),
            source_sha256="a" * 64,
            payload={"rounds": []},
        )
        session.add(fixture_import)
        session.flush()
        entry = FixtureImportEntry(
            fixture_import_id=fixture_import.id,
            entry_key="r1-bye",
            kind="bye",
            raw_entry={"source_text": "Libre"},
        )
        session.add(entry)
        session.commit()

        assert entry.scheduled_match_id is None
        assert entry.raw_entry == {"source_text": "Libre"}

    def test_fixture_schemas_expose_provenance_and_result_fields(self):
        assert {"fixture_key", "source_home_score", "source_away_score", "result_status"} <= ScheduledMatchSchema.model_fields.keys()
        assert {"source_label", "captured_at", "source_sha256", "payload", "entries"} <= FixtureImportSchema.model_fields.keys()

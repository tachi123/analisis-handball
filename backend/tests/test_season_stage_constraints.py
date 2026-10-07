"""Tests for Season and TournamentStage constraints.

Covers spec:
- Season year unique
- Stage name unique within season
- Delete cascade season with stages
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Season, TournamentStage


class TestSeasonConstraints:
    """Season model constraints."""

    def test_season_year_unique(self, session):
        """Season year must be unique."""
        season1 = Season(year=2026, description="Season 1")
        season2 = Season(year=2026, description="Season 2")
        session.add_all([season1, season2])

        with pytest.raises(IntegrityError):
            session.commit()

    def test_different_years_allowed(self, session):
        """Different season years allowed."""
        season1 = Season(year=2025, description="Season 2025")
        season2 = Season(year=2026, description="Season 2026")
        session.add_all([season1, season2])
        session.commit()

        assert session.query(Season).count() == 2


class TestTournamentStageConstraints:
    """TournamentStage model constraints."""

    def test_stage_name_unique_per_season(self, session, season):
        """Stage name unique per season (uq_stage_season_name)."""
        stage1 = TournamentStage(
            season_id=season.id,
            name="Clausura Permanencia",
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

        with pytest.raises(IntegrityError):
            session.commit()

    def test_same_stage_name_different_season_allowed(self, session):
        """Same stage name in different seasons allowed."""
        season1 = Season(year=2025, description="Season 2025")
        season2 = Season(year=2026, description="Season 2026")
        session.add_all([season1, season2])
        session.flush()

        stage1 = TournamentStage(
            season_id=season1.id,
            name="Clausura Permanencia",
            category="Mayores",
            division="3ª División",
            gender="Masculino",
        )
        stage2 = TournamentStage(
            season_id=season2.id,
            name="Clausura Permanencia",
            category="Mayores",
            division="3ª División",
            gender="Masculino",
        )
        session.add_all([stage1, stage2])
        session.commit()

        assert session.query(TournamentStage).count() == 2

    def test_stage_cascade_delete_with_season(self, session):
        """Deleting season cascades to stages."""
        season = Season(year=2026, description="Test Season")
        session.add(season)
        session.flush()

        stage1 = TournamentStage(
            season_id=season.id,
            name="Apertura",
            category="Mayores",
            division="3ª División",
            gender="Masculino",
        )
        stage2 = TournamentStage(
            season_id=season.id,
            name="Clausura",
            category="Mayores",
            division="3ª División",
            gender="Masculino",
        )
        session.add_all([stage1, stage2])
        session.commit()

        # Delete season - stages should cascade
        session.delete(season)
        session.commit()

        assert session.query(Season).count() == 0
        assert session.query(TournamentStage).count() == 0

    def test_stage_required_fields(self, session, season):
        """Stage requires category, division, gender."""
        stage = TournamentStage(
            season_id=season.id,
            name="Test Stage",
            category="Mayores",
            division="3ª División",
            gender="Masculino",
        )
        session.add(stage)
        session.commit()

        assert stage.category == "Mayores"
        assert stage.division == "3ª División"
        assert stage.gender == "Masculino"
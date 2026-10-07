"""Tests for TeamRegistration constraints.

Covers spec:
- Registration uniqueness: (competition_team_id, stage_id) unique
- Registration links CompetitionTeam to TournamentStage with group/seed_order
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Club,
    CompetitionTeam,
    TeamRegistration,
    TournamentStage,
)


class TestTeamRegistrationConstraints:
    """TeamRegistration model constraints."""

    def _create_registration_dependencies(self, session, stage):
        """Helper to create dependencies for registration."""
        club = Club(name="Banfield", short_name="BAN")
        session.add(club)
        session.flush()

        comp_team = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="A")
        session.add(comp_team)
        session.flush()

        return comp_team

    def test_registration_unique_per_competition_team_stage(self, session, stage):
        """Registration unique per (competition_team_id, stage_id) - uq_registration_team_stage."""
        comp_team = self._create_registration_dependencies(session, stage)

        reg1 = TeamRegistration(competition_team_id=comp_team.id, stage_id=stage.id)
        reg2 = TeamRegistration(competition_team_id=comp_team.id, stage_id=stage.id)
        session.add_all([reg1, reg2])

        with pytest.raises(IntegrityError):
            session.commit()

    def test_same_competition_team_different_stages_allowed(self, session, season):
        """Same competition team can register in different stages (if stages differ)."""
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
        session.flush()

        club = Club(name="Banfield", short_name="BAN")
        session.add(club)
        session.flush()

        comp_team = CompetitionTeam(club_id=club.id, stage_id=stage1.id, suffix="A")
        session.add(comp_team)
        session.flush()

        # CompetitionTeam is tied to stage1, but registration also references stage
        # The unique constraint is on (competition_team_id, stage_id)
        # Since comp_team.stage_id = stage1.id, a registration for stage2 would be a different stage_id
        # But the comp_team is already linked to stage1 via its own stage_id
        # This is a bit odd - let's test what the constraint actually allows
        reg1 = TeamRegistration(competition_team_id=comp_team.id, stage_id=stage1.id)
        session.add(reg1)
        session.commit()

        # The constraint allows different stage_id for same competition_team_id
        # (though logically the competition_team already belongs to a stage)
        reg2 = TeamRegistration(competition_team_id=comp_team.id, stage_id=stage2.id)
        session.add(reg2)
        session.commit()  # This is allowed by the unique constraint

        assert session.query(TeamRegistration).count() == 2

    def test_different_competition_teams_same_stage_allowed(self, session, stage):
        """Different competition teams can register in same stage."""
        club1 = Club(name="Banfield", short_name="BAN")
        club2 = Club(name="Comunicaciones", short_name="COM")
        session.add_all([club1, club2])
        session.flush()

        team1 = CompetitionTeam(club_id=club1.id, stage_id=stage.id, suffix="A")
        team2 = CompetitionTeam(club_id=club2.id, stage_id=stage.id, suffix="A")
        session.add_all([team1, team2])
        session.flush()

        reg1 = TeamRegistration(competition_team_id=team1.id, stage_id=stage.id)
        reg2 = TeamRegistration(competition_team_id=team2.id, stage_id=stage.id)
        session.add_all([reg1, reg2])
        session.commit()

        assert session.query(TeamRegistration).count() == 2

    def test_registration_group_seed_order_optional(self, session, stage):
        """Registration group and seed_order are optional."""
        comp_team = self._create_registration_dependencies(session, stage)

        reg = TeamRegistration(competition_team_id=comp_team.id, stage_id=stage.id)
        session.add(reg)
        session.commit()

        assert reg.group is None
        assert reg.seed_order is None

    def test_registration_with_group_and_seed(self, session, stage):
        """Registration can have group and seed_order."""
        comp_team = self._create_registration_dependencies(session, stage)

        reg = TeamRegistration(
            competition_team_id=comp_team.id,
            stage_id=stage.id,
            group="Zona A",
            seed_order=1,
        )
        session.add(reg)
        session.commit()

        assert reg.group == "Zona A"
        assert reg.seed_order == 1
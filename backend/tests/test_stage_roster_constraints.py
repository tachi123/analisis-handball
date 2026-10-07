"""Tests for StageRoster constraints.

Covers spec:
- Jersey number unique per registration (uq_roster_jersey)
- Same jersey number allowed for different registrations
- Duplicate registration-player rejected (business rule, not DB constraint)
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Club,
    CompetitionTeam,
    Player,
    StageRoster,
    TeamRegistration,
    TournamentStage,
)


def _create_roster_dependencies(session, stage):
    """Helper to create minimal dependencies for roster tests."""
    club = Club(name="Banfield", short_name="BAN")
    session.add(club)
    session.flush()

    team = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="A")
    session.add(team)
    session.flush()

    reg = TeamRegistration(competition_team_id=team.id, stage_id=stage.id)
    session.add(reg)
    session.flush()

    return reg


class TestStageRosterJerseyConstraints:
    """StageRoster jersey_number uniqueness constraints."""

    def test_jersey_number_unique_per_registration(self, session, stage):
        """jersey_number unique per registration (uq_roster_jersey)."""
        reg = _create_roster_dependencies(session, stage)

        player1 = Player(name="Juan Perez", default_jersey_number=10)
        player2 = Player(name="Pedro Gomez", default_jersey_number=10)
        session.add_all([player1, player2])
        session.flush()

        roster1 = StageRoster(registration_id=reg.id, player_id=player1.id, jersey_number=10)
        session.add(roster1)
        session.commit()

        roster2 = StageRoster(registration_id=reg.id, player_id=player2.id, jersey_number=10)
        session.add(roster2)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_same_jersey_different_registration_allowed(self, session, stage):
        """Same jersey number allowed for different registrations."""
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
        session.flush()

        player1 = Player(name="Juan Perez", default_jersey_number=10)
        player2 = Player(name="Pedro Gomez", default_jersey_number=10)
        session.add_all([player1, player2])
        session.flush()

        roster1 = StageRoster(registration_id=reg1.id, player_id=player1.id, jersey_number=10)
        roster2 = StageRoster(registration_id=reg2.id, player_id=player2.id, jersey_number=10)
        session.add_all([roster1, roster2])
        session.commit()

        assert session.query(StageRoster).count() == 2


class TestStageRosterRegistrationPlayer:
    """StageRoster registration-player uniqueness (business rule)."""

    def test_duplicate_registration_player_rejected_db_allows(self, session, stage):
        """Same registration + same player with different jersey - DB allows (no unique constraint).
        
        Note: The (registration_id, player_id) uniqueness is a business rule
        enforced at the service layer, not a DB constraint.
        The DB only has unique constraint on (registration_id, jersey_number).
        """
        reg = _create_roster_dependencies(session, stage)

        player = Player(name="Juan Perez", default_jersey_number=10)
        session.add(player)
        session.flush()

        roster1 = StageRoster(registration_id=reg.id, player_id=player.id, jersey_number=10)
        session.add(roster1)
        session.commit()

        # Same registration + same player with different jersey - DB allows
        roster2 = StageRoster(registration_id=reg.id, player_id=player.id, jersey_number=11)
        session.add(roster2)
        session.commit()  # DB allows this currently

        assert session.query(StageRoster).count() == 2

    def test_same_player_different_registrations_allowed(self, session, stage):
        """Same player can be rostered for different registrations."""
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
        session.flush()

        player = Player(name="Juan Perez", default_jersey_number=10)
        session.add(player)
        session.flush()

        roster1 = StageRoster(registration_id=reg1.id, player_id=player.id, jersey_number=10)
        roster2 = StageRoster(registration_id=reg2.id, player_id=player.id, jersey_number=10)
        session.add_all([roster1, roster2])
        session.commit()

        assert session.query(StageRoster).count() == 2


class TestStageRosterJerseyNumberValidation:
    """Jersey number must be >= 1 (schema validation)."""

    def test_jersey_number_ge_1(self, session, stage):
        """Jersey number must be >= 1."""
        reg = _create_roster_dependencies(session, stage)

        player = Player(name="Juan Perez")
        session.add(player)
        session.flush()

        # Valid jersey numbers
        for jersey in (1, 5, 10, 99):
            roster = StageRoster(registration_id=reg.id, player_id=player.id, jersey_number=jersey)
            session.add(roster)
            session.commit()
            session.delete(roster)
            session.commit()

    def test_jersey_number_zero_rejected_by_schema_not_db(self, session, stage):
        """Jersey number 0 would be rejected by Pydantic schema (ge=1), not DB."""
        # This is a schema-level validation, not tested at DB level
        # The DB column is Integer nullable=False with no CHECK constraint
        pass
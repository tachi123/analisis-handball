"""Tests for Round and ScheduledMatch constraints.

Covers spec:
- Round number unique per stage
- Match number label unique per round
- Home and away registrations must differ (business rule)
- Status defaults to 'scheduled'
- Status enum: scheduled | played | postponed | cancelled
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Club,
    CompetitionTeam,
    Round,
    ScheduledMatch,
    TeamRegistration,
    TournamentStage,
)


class TestRoundConstraints:
    """Round model constraints."""

    def test_round_number_unique_per_stage(self, session, stage):
        """Round number unique per stage (uq_round_stage_number)."""
        round1 = Round(stage_id=stage.id, round_number=1)
        round2 = Round(stage_id=stage.id, round_number=1)
        session.add_all([round1, round2])

        with pytest.raises(IntegrityError):
            session.commit()

    def test_different_round_numbers_same_stage_allowed(self, session, stage):
        """Different round numbers in same stage allowed."""
        round1 = Round(stage_id=stage.id, round_number=1)
        round2 = Round(stage_id=stage.id, round_number=2)
        session.add_all([round1, round2])
        session.commit()

        assert session.query(Round).count() == 2

    def test_same_round_number_different_stages_allowed(self, session, season):
        """Same round number in different stages allowed."""
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

        round1 = Round(stage_id=stage1.id, round_number=1)
        round2 = Round(stage_id=stage2.id, round_number=1)
        session.add_all([round1, round2])
        session.commit()

        assert session.query(Round).count() == 2

    def test_round_date_ranges_optional(self, session, stage):
        """Round date ranges are optional."""
        round_ = Round(stage_id=stage.id, round_number=1)
        session.add(round_)
        session.commit()

        assert round_.date_range_start is None
        assert round_.date_range_end is None


class TestScheduledMatchConstraints:
    """ScheduledMatch model constraints."""

    def _create_match_dependencies(self, session, stage):
        """Helper to create minimal dependencies for a match."""
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

        round_ = Round(stage_id=stage.id, round_number=1)
        session.add(round_)
        session.flush()

        return reg1, reg2, round_

    def test_match_number_label_unique_per_round(self, session, stage):
        """match_number_label unique per round (uq_match_round_label)."""
        reg1, reg2, round_ = self._create_match_dependencies(session, stage)

        match1 = ScheduledMatch(
            stage_id=stage.id,
            round_id=round_.id,
            home_registration_id=reg1.id,
            away_registration_id=reg2.id,
            match_number_label="F01",
            fixture_key="test:label-unique:1",
        )
        session.add(match1)
        session.flush()

        match2 = ScheduledMatch(
            stage_id=stage.id,
            round_id=round_.id,
            home_registration_id=reg2.id,
            away_registration_id=reg1.id,
            match_number_label="F01",  # Duplicate label in same round
            fixture_key="test:label-unique:2",
        )
        session.add(match2)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_same_match_number_label_different_rounds_allowed(self, session, stage):
        """Same match_number_label in different rounds allowed."""
        reg1, reg2, round1 = self._create_match_dependencies(session, stage)

        round2 = Round(stage_id=stage.id, round_number=2)
        session.add(round2)
        session.flush()

        match1 = ScheduledMatch(
            stage_id=stage.id,
            round_id=round1.id,
            home_registration_id=reg1.id,
            away_registration_id=reg2.id,
            match_number_label="F01",
            fixture_key="test:round-label:1",
        )
        match2 = ScheduledMatch(
            stage_id=stage.id,
            round_id=round2.id,
            home_registration_id=reg1.id,
            away_registration_id=reg2.id,
            match_number_label="F01",  # Same label, different round
            fixture_key="test:round-label:2",
        )
        session.add_all([match1, match2])
        session.commit()

        assert session.query(ScheduledMatch).count() == 2

    def test_home_away_registrations_differ_db_allows(self, session, stage):
        """DB allows same registration for home and away (business rule enforced at service layer)."""
        club = Club(name="Banfield", short_name="BAN")
        session.add(club)
        session.flush()

        team = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="A")
        session.add(team)
        session.flush()

        reg = TeamRegistration(competition_team_id=team.id, stage_id=stage.id)
        session.add(reg)
        session.flush()

        round_ = Round(stage_id=stage.id, round_number=1)
        session.add(round_)
        session.flush()

        # Same registration for home and away - DB doesn't enforce this
        match = ScheduledMatch(
            stage_id=stage.id,
            round_id=round_.id,
            home_registration_id=reg.id,
            away_registration_id=reg.id,  # Same as home
            match_number_label="F01",
            fixture_key="test:same-registration",
        )
        session.add(match)
        session.commit()  # DB allows this

        assert session.query(ScheduledMatch).count() == 1

    def test_status_defaults_to_scheduled(self, session, stage):
        """ScheduledMatch status defaults to 'scheduled'."""
        reg1, reg2, round_ = self._create_match_dependencies(session, stage)

        match = ScheduledMatch(
            stage_id=stage.id,
            round_id=round_.id,
            home_registration_id=reg1.id,
            away_registration_id=reg2.id,
            match_number_label="F01",
            fixture_key="test:default-status",
        )
        session.add(match)
        session.commit()

        assert match.status == "scheduled"

    def test_status_accepts_valid_values(self, session, stage):
        """Status accepts valid enum values."""
        reg1, reg2, round_ = self._create_match_dependencies(session, stage)

        for status in ("scheduled", "played", "postponed", "cancelled"):
            match = ScheduledMatch(
                stage_id=stage.id,
                round_id=round_.id,
                home_registration_id=reg1.id,
                away_registration_id=reg2.id,
                match_number_label=f"F{status[:2]}",
                fixture_key=f"test:status:{status}",
                status=status,
            )
            session.add(match)
        session.commit()

        assert session.query(ScheduledMatch).count() == 4

    def test_scheduled_date_venue_court_time_optional(self, session, stage):
        """scheduled_date, venue, court, match_time are optional."""
        reg1, reg2, round_ = self._create_match_dependencies(session, stage)

        match = ScheduledMatch(
            stage_id=stage.id,
            round_id=round_.id,
            home_registration_id=reg1.id,
            away_registration_id=reg2.id,
            match_number_label="F01",
            fixture_key="test:optional-schedule",
        )
        session.add(match)
        session.commit()

        assert match.scheduled_date is None
        assert match.venue is None
        assert match.court is None
        assert match.match_time is None

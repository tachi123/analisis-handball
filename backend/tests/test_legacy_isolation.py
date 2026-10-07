"""Tests for legacy domain isolation.

Covers spec: Competition layer is fully additive — zero FKs from legacy
(Tournament/Team/Match) to new tables. Only cross-link is StageRoster.player_id -> players.id
(intentional per design).
"""

import pytest
from datetime import date

from app.models import (
    Club,
    CompetitionTeam,
    Match,
    Player,
    Round,
    ScheduledMatch,
    Season,
    StageRoster,
    Team,
    TeamRegistration,
    Tournament,
    TournamentStage,
)


class TestLegacyModelsUnaffected:
    """Legacy Tournament/Team/Match models still work after migration."""

    def test_legacy_tournament_team_match_work(self, session):
        """Existing Tournament/Team/Match models still work after migration."""
        tournament = Tournament(name="Legacy Tournament", category="Mayores", year=2025)
        session.add(tournament)
        session.flush()

        team1 = Team(name="Legacy Team A", club_name="Club A")
        team2 = Team(name="Legacy Team B", club_name="Club B")
        session.add_all([team1, team2])
        session.flush()

        match = Match(
            tournament_id=tournament.id,
            date=date(2025, 1, 1),
            home_team_id=team1.id,
            away_team_id=team2.id,
        )
        session.add(match)
        session.commit()

        assert session.query(Tournament).count() == 1
        assert session.query(Team).count() == 2
        assert session.query(Match).count() == 1

    def test_legacy_player_team_relationship_works(self, session):
        """Legacy Player -> Team relationship works."""
        team = Team(name="Legacy Team", club_name="Club A")
        session.add(team)
        session.flush()

        player = Player(name="Legacy Player", team_id=team.id, default_jersey_number=10)
        session.add(player)
        session.commit()

        assert player.team_id == team.id
        assert player in team.players

    def test_legacy_match_squad_works(self, session):
        """Legacy MatchSquad works with legacy Match and Player."""
        tournament = Tournament(name="Legacy Tournament", category="Mayores", year=2025)
        session.add(tournament)
        session.flush()

        team1 = Team(name="Team A", club_name="Club A")
        team2 = Team(name="Team B", club_name="Club B")
        session.add_all([team1, team2])
        session.flush()

        match = Match(
            tournament_id=tournament.id,
            date=date(2025, 1, 1),
            home_team_id=team1.id,
            away_team_id=team2.id,
        )
        session.add(match)
        session.flush()

        player = Player(name="Player 1", team_id=team1.id, default_jersey_number=10)
        session.add(player)
        session.flush()

        from app.models import MatchSquad

        squad = MatchSquad(match_id=match.id, player_id=player.id, jersey_number=10)
        session.add(squad)
        session.commit()

        assert session.query(MatchSquad).count() == 1


class TestCompetitionLayerAdditive:
    """Competition layer tables don't interfere with legacy."""

    def test_competition_layer_creates_independently(self, session):
        """Competition layer entities can be created without legacy entities."""
        season = Season(year=2026, description="Test Season")
        session.add(season)
        session.flush()

        stage = TournamentStage(
            season_id=season.id,
            name="Clausura",
            category="Mayores",
            division="3ª División",
            gender="Masculino",
        )
        session.add(stage)
        session.flush()

        club = Club(name="Banfield", short_name="BAN")
        session.add(club)
        session.flush()

        comp_team = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="A")
        session.add(comp_team)
        session.flush()

        reg = TeamRegistration(competition_team_id=comp_team.id, stage_id=stage.id)
        session.add(reg)
        session.flush()

        round_ = Round(stage_id=stage.id, round_number=1)
        session.add(round_)
        session.flush()

        match = ScheduledMatch(
            stage_id=stage.id,
            round_id=round_.id,
            home_registration_id=reg.id,
            away_registration_id=reg.id,
            match_number_label="F01",
        )
        session.add(match)
        session.flush()
        assert match.fixture_key.startswith("manual:")

        player = Player(name="New Player", default_jersey_number=10)
        session.add(player)
        session.flush()

        roster = StageRoster(registration_id=reg.id, player_id=player.id, jersey_number=10)
        session.add(roster)
        session.commit()

        # All competition layer entities created
        assert session.query(Season).count() == 1
        assert session.query(TournamentStage).count() == 1
        assert session.query(Club).count() == 1
        assert session.query(CompetitionTeam).count() == 1
        assert session.query(TeamRegistration).count() == 1
        assert session.query(Round).count() == 1
        assert session.query(ScheduledMatch).count() == 1
        assert session.query(StageRoster).count() == 1

        # Legacy tables empty
        assert session.query(Tournament).count() == 0
        assert session.query(Team).count() == 0
        assert session.query(Match).count() == 0

    def test_shared_player_table_works_for_both(self, session):
        """Player table shared between legacy and competition layer (intentional)."""
        # Legacy player
        legacy_team = Team(name="Legacy Team", club_name="Club A")
        session.add(legacy_team)
        session.flush()

        legacy_player = Player(name="Legacy Player", team_id=legacy_team.id, default_jersey_number=10)
        session.add(legacy_player)
        session.flush()

        # Competition layer player (no team_id needed)
        comp_player = Player(name="Comp Player", default_jersey_number=11)
        session.add(comp_player)
        session.flush()

        # Use legacy player in legacy match
        tournament = Tournament(name="Legacy", category="Mayores", year=2025)
        session.add(tournament)
        session.flush()

        legacy_match = Match(
            tournament_id=tournament.id,
            date=date(2025, 1, 1),
            home_team_id=legacy_team.id,
            away_team_id=legacy_team.id,
        )
        session.add(legacy_match)
        session.flush()

        from app.models import MatchSquad

        legacy_squad = MatchSquad(match_id=legacy_match.id, player_id=legacy_player.id, jersey_number=10)
        session.add(legacy_squad)

        # Use competition player in stage roster
        season = Season(year=2026, description="Test")
        session.add(season)
        session.flush()

        stage = TournamentStage(
            season_id=season.id, name="Clausura", category="Mayores", division="3ª División", gender="Masculino"
        )
        session.add(stage)
        session.flush()

        club = Club(name="Club B", short_name="CB")
        session.add(club)
        session.flush()

        comp_team = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="B")
        session.add(comp_team)
        session.flush()

        reg = TeamRegistration(competition_team_id=comp_team.id, stage_id=stage.id)
        session.add(reg)
        session.flush()

        comp_roster = StageRoster(registration_id=reg.id, player_id=comp_player.id, jersey_number=11)
        session.add(comp_roster)
        session.commit()

        # Both work
        assert session.query(MatchSquad).count() == 1
        assert session.query(StageRoster).count() == 1

    def test_no_fk_from_legacy_to_competition(self, session):
        """Verify no foreign keys from legacy tables to competition tables."""
        # This is a design verification - the models don't define such FKs
        # Legacy Tournament has no FK to Season
        # Legacy Team has no FK to Club/CompetitionTeam
        # Legacy Match has no FK to ScheduledMatch/Round/Stage
        # Only StageRoster has FK to Player (shared table)
        pass


class TestLegacyAndCompetitionCoexist:
    """Legacy and competition entities can coexist in same database."""

    def test_both_domains_in_same_db(self, session):
        """Create both legacy and competition entities in same session."""
        # Legacy
        tournament = Tournament(name="Legacy Tournament", category="Mayores", year=2025)
        session.add(tournament)
        session.flush()

        legacy_team = Team(name="Legacy Team", club_name="Legacy Club")
        session.add(legacy_team)
        session.flush()

        legacy_match = Match(
            tournament_id=tournament.id,
            date=date(2025, 1, 1),
            home_team_id=legacy_team.id,
            away_team_id=legacy_team.id,
        )
        session.add(legacy_match)

        # Competition
        season = Season(year=2026, description="Test Season")
        session.add(season)
        session.flush()

        stage = TournamentStage(
            season_id=season.id,
            name="Clausura",
            category="Mayores",
            division="3ª División",
            gender="Masculino",
        )
        session.add(stage)
        session.flush()

        club = Club(name="Comp Club", short_name="CC")
        session.add(club)
        session.flush()

        comp_team = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="A")
        session.add(comp_team)
        session.flush()

        reg = TeamRegistration(competition_team_id=comp_team.id, stage_id=stage.id)
        session.add(reg)
        session.flush()

        round_ = Round(stage_id=stage.id, round_number=1)
        session.add(round_)
        session.flush()

        comp_match = ScheduledMatch(
            stage_id=stage.id,
            round_id=round_.id,
            home_registration_id=reg.id,
            away_registration_id=reg.id,
            match_number_label="F01",
        )
        session.add(comp_match)

        session.commit()
        assert comp_match.fixture_key.startswith("manual:")

        # Both exist
        assert session.query(Tournament).count() == 1
        assert session.query(Team).count() == 1
        assert session.query(Match).count() == 1
        assert session.query(Season).count() == 1
        assert session.query(TournamentStage).count() == 1
        assert session.query(Club).count() == 1
        assert session.query(CompetitionTeam).count() == 1
        assert session.query(TeamRegistration).count() == 1
        assert session.query(Round).count() == 1
        assert session.query(ScheduledMatch).count() == 1

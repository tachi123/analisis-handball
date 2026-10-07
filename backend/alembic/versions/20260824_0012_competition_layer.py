"""Add competition layer tables (Season, TournamentStage, Club, CompetitionTeam, TeamRegistration, Round, ScheduledMatch, StageRoster).

Revision ID: 20260824_0012
Revises: 20260823_0011
Create Date: 2026-08-24 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260824_0012"
down_revision = "20260823_0011"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), unique=True, nullable=False),
        sa.Column("description", sa.String(), nullable=True),
    )
    op.create_index(op.f("ix_seasons_id"), "seasons", ["id"])
    op.create_index(op.f("ix_seasons_year"), "seasons", ["year"])

    op.create_table(
        "tournament_stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("division", sa.String(), nullable=False),
        sa.Column("gender", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"]),
        sa.UniqueConstraint("season_id", "name", name="uq_stage_season_name"),
    )
    op.create_index(op.f("ix_tournament_stages_id"), "tournament_stages", ["id"])
    op.create_index(op.f("ix_tournament_stages_season_id"), "tournament_stages", ["season_id"])

    op.create_table(
        "clubs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), unique=True, nullable=False),
        sa.Column("short_name", sa.String(), nullable=True),
    )
    op.create_index(op.f("ix_clubs_id"), "clubs", ["id"])
    op.create_index(op.f("ix_clubs_name"), "clubs", ["name"])

    op.create_table(
        "competition_teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("club_id", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("suffix", sa.String(2), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"]),
        sa.ForeignKeyConstraint(["stage_id"], ["tournament_stages.id"]),
        sa.UniqueConstraint("club_id", "suffix", "stage_id", name="uq_comp_team_identity"),
    )
    op.create_index(op.f("ix_competition_teams_id"), "competition_teams", ["id"])
    op.create_index(op.f("ix_competition_teams_club_id"), "competition_teams", ["club_id"])
    op.create_index(op.f("ix_competition_teams_stage_id"), "competition_teams", ["stage_id"])

    op.create_table(
        "team_registrations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competition_team_id", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("group", sa.String(), nullable=True),
        sa.Column("seed_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["competition_team_id"], ["competition_teams.id"]),
        sa.ForeignKeyConstraint(["stage_id"], ["tournament_stages.id"]),
        sa.UniqueConstraint("competition_team_id", "stage_id", name="uq_registration_team_stage"),
    )
    op.create_index(op.f("ix_team_registrations_id"), "team_registrations", ["id"])
    op.create_index(op.f("ix_team_registrations_competition_team_id"), "team_registrations", ["competition_team_id"])
    op.create_index(op.f("ix_team_registrations_stage_id"), "team_registrations", ["stage_id"])

    op.create_table(
        "rounds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("date_range_start", sa.Date(), nullable=True),
        sa.Column("date_range_end", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["stage_id"], ["tournament_stages.id"]),
        sa.UniqueConstraint("stage_id", "round_number", name="uq_round_stage_number"),
    )
    op.create_index(op.f("ix_rounds_id"), "rounds", ["id"])
    op.create_index(op.f("ix_rounds_stage_id"), "rounds", ["stage_id"])

    op.create_table(
        "scheduled_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("round_id", sa.Integer(), nullable=False),
        sa.Column("home_registration_id", sa.Integer(), nullable=False),
        sa.Column("away_registration_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("venue", sa.String(), nullable=True),
        sa.Column("court", sa.String(), nullable=True),
        sa.Column("match_time", sa.String(), nullable=True),
        sa.Column("match_number_label", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="scheduled"),
        sa.ForeignKeyConstraint(["stage_id"], ["tournament_stages.id"]),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"]),
        sa.ForeignKeyConstraint(["home_registration_id"], ["team_registrations.id"]),
        sa.ForeignKeyConstraint(["away_registration_id"], ["team_registrations.id"]),
        sa.UniqueConstraint("round_id", "match_number_label", name="uq_match_round_label"),
    )
    op.create_index(op.f("ix_scheduled_matches_id"), "scheduled_matches", ["id"])
    op.create_index(op.f("ix_scheduled_matches_stage_id"), "scheduled_matches", ["stage_id"])
    op.create_index(op.f("ix_scheduled_matches_round_id"), "scheduled_matches", ["round_id"])
    op.create_index(op.f("ix_scheduled_matches_home_registration_id"), "scheduled_matches", ["home_registration_id"])
    op.create_index(op.f("ix_scheduled_matches_away_registration_id"), "scheduled_matches", ["away_registration_id"])
    op.create_index(op.f("ix_scheduled_matches_match_number_label"), "scheduled_matches", ["match_number_label"])

    op.create_table(
        "stage_rosters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("registration_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("jersey_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["registration_id"], ["team_registrations.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.UniqueConstraint("registration_id", "jersey_number", name="uq_roster_jersey"),
    )
    op.create_index(op.f("ix_stage_rosters_id"), "stage_rosters", ["id"])
    op.create_index(op.f("ix_stage_rosters_registration_id"), "stage_rosters", ["registration_id"])
    op.create_index(op.f("ix_stage_rosters_player_id"), "stage_rosters", ["player_id"])


def downgrade():
    op.drop_index(op.f("ix_stage_rosters_player_id"), table_name="stage_rosters")
    op.drop_index(op.f("ix_stage_rosters_registration_id"), table_name="stage_rosters")
    op.drop_index(op.f("ix_stage_rosters_id"), table_name="stage_rosters")
    op.drop_table("stage_rosters")

    op.drop_index(op.f("ix_scheduled_matches_match_number_label"), table_name="scheduled_matches")
    op.drop_index(op.f("ix_scheduled_matches_away_registration_id"), table_name="scheduled_matches")
    op.drop_index(op.f("ix_scheduled_matches_home_registration_id"), table_name="scheduled_matches")
    op.drop_index(op.f("ix_scheduled_matches_round_id"), table_name="scheduled_matches")
    op.drop_index(op.f("ix_scheduled_matches_stage_id"), table_name="scheduled_matches")
    op.drop_index(op.f("ix_scheduled_matches_id"), table_name="scheduled_matches")
    op.drop_table("scheduled_matches")

    op.drop_index(op.f("ix_rounds_stage_id"), table_name="rounds")
    op.drop_index(op.f("ix_rounds_id"), table_name="rounds")
    op.drop_table("rounds")

    op.drop_index(op.f("ix_team_registrations_stage_id"), table_name="team_registrations")
    op.drop_index(op.f("ix_team_registrations_competition_team_id"), table_name="team_registrations")
    op.drop_index(op.f("ix_team_registrations_id"), table_name="team_registrations")
    op.drop_table("team_registrations")

    op.drop_index(op.f("ix_competition_teams_stage_id"), table_name="competition_teams")
    op.drop_index(op.f("ix_competition_teams_club_id"), table_name="competition_teams")
    op.drop_index(op.f("ix_competition_teams_id"), table_name="competition_teams")
    op.drop_table("competition_teams")

    op.drop_index(op.f("ix_clubs_name"), table_name="clubs")
    op.drop_index(op.f("ix_clubs_id"), table_name="clubs")
    op.drop_table("clubs")

    op.drop_index(op.f("ix_tournament_stages_season_id"), table_name="tournament_stages")
    op.drop_index(op.f("ix_tournament_stages_id"), table_name="tournament_stages")
    op.drop_table("tournament_stages")

    op.drop_index(op.f("ix_seasons_year"), table_name="seasons")
    op.drop_index(op.f("ix_seasons_id"), table_name="seasons")
    op.drop_table("seasons")
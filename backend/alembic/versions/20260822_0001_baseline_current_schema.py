"""Baseline current schema.

Revision ID: 20260822_0001
Revises:
Create Date: 2026-08-22 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260822_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("club_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("must_change_password", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_id", "users", ["id"])

    op.create_table(
        "tournaments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tournaments_id", "tournaments", ["id"])
    op.create_index("ix_tournaments_name", "tournaments", ["name"])

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("club_name", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teams_id", "teams", ["id"])
    op.create_index("ix_teams_name", "teams", ["name"])

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("default_jersey_number", sa.Integer(), nullable=True),
        sa.Column("global_position", sa.String(), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_players_id", "players", ["id"])
    op.create_index("ix_players_name", "players", ["name"])

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("home_team_id", sa.Integer(), nullable=True),
        sa.Column("away_team_id", sa.Integer(), nullable=True),
        sa.Column("youtube_link", sa.String(), nullable=True),
        sa.Column("main_team_focus", sa.String(), nullable=True),
        sa.Column("venue", sa.String(), nullable=True),
        sa.Column("court", sa.String(), nullable=True),
        sa.Column("match_time", sa.String(), nullable=True),
        sa.Column("category_label", sa.String(), nullable=True),
        sa.Column("match_number_label", sa.String(), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("pdf_file_path", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_matches_id", "matches", ["id"])

    op.create_table(
        "match_squad",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=True),
        sa.Column("player_id", sa.Integer(), nullable=True),
        sa.Column("jersey_number", sa.Integer(), nullable=False),
        sa.Column("is_goalkeeper", sa.Boolean(), nullable=True),
        sa.Column("official_goals", sa.Integer(), nullable=True),
        sa.Column("official_yellow", sa.Integer(), nullable=True),
        sa.Column("official_2min", sa.Integer(), nullable=True),
        sa.Column("official_red", sa.Integer(), nullable=True),
        sa.Column("official_blue", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_match_squad_id", "match_squad", ["id"])

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=True),
        sa.Column("game_timestamp", sa.Float(), nullable=True),
        sa.Column("period", sa.Integer(), nullable=True),
        sa.Column("team_action", sa.String(), nullable=True),
        sa.Column("player_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(), nullable=True),
        sa.Column("result", sa.String(), nullable=True),
        sa.Column("shot_zone", sa.String(), nullable=True),
        sa.Column("loss_detail", sa.String(), nullable=True),
        sa.Column("attack_phase", sa.String(), nullable=True),
        sa.Column("assist_player_id", sa.Integer(), nullable=True),
        sa.Column("goalkeeper_id", sa.Integer(), nullable=True),
        sa.Column("sub_in_player_id", sa.Integer(), nullable=True),
        sa.Column("sub_out_player_id", sa.Integer(), nullable=True),
        sa.Column("transition_type", sa.String(), nullable=True),
        sa.Column("transition_result", sa.String(), nullable=True),
        sa.Column("sanction_type", sa.String(), nullable=True),
        sa.Column("sanction_target", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["assist_player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["goalkeeper_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["sub_in_player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["sub_out_player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_id", "events", ["id"])

    op.create_table(
        "clips",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=True),
        sa.Column("video_start", sa.Float(), nullable=True),
        sa.Column("video_end", sa.Float(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("player_tags", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clips_id", "clips", ["id"])


def downgrade():
    op.drop_index("ix_clips_id", table_name="clips")
    op.drop_table("clips")
    op.drop_index("ix_events_id", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_match_squad_id", table_name="match_squad")
    op.drop_table("match_squad")
    op.drop_index("ix_matches_id", table_name="matches")
    op.drop_table("matches")
    op.drop_index("ix_players_name", table_name="players")
    op.drop_index("ix_players_id", table_name="players")
    op.drop_table("players")
    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_index("ix_teams_id", table_name="teams")
    op.drop_table("teams")
    op.drop_index("ix_tournaments_name", table_name="tournaments")
    op.drop_index("ix_tournaments_id", table_name="tournaments")
    op.drop_table("tournaments")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

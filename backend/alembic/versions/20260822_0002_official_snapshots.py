"""Add immutable official import snapshots.

Revision ID: 20260822_0002
Revises: 20260822_0001
Create Date: 2026-08-22 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260822_0002"
down_revision = "20260822_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "official_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("source_filename", sa.String(), nullable=False),
        sa.Column("source_content_type", sa.String(), nullable=False),
        sa.Column("source_size_bytes", sa.Integer(), nullable=False),
        sa.Column("source_sha256", sa.String(), nullable=False),
        sa.Column("source_page_count", sa.Integer(), nullable=False),
        sa.Column("source_path", sa.String(), nullable=False),
        sa.Column("confirmed_date", sa.Date(), nullable=False),
        sa.Column("home_team_name", sa.String(), nullable=False),
        sa.Column("away_team_name", sa.String(), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=False),
        sa.Column("away_score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "official_snapshot_players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("jersey_number", sa.Integer(), nullable=False),
        sa.Column("official_goals", sa.Integer(), nullable=False),
        sa.Column("official_yellow", sa.Integer(), nullable=False),
        sa.Column("official_2min", sa.Integer(), nullable=False),
        sa.Column("official_red", sa.Integer(), nullable=False),
        sa.Column("official_blue", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["official_snapshots.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_official_snapshot_players_id", "official_snapshot_players", ["id"])


def downgrade():
    op.drop_index("ix_official_snapshot_players_id", table_name="official_snapshot_players")
    op.drop_table("official_snapshot_players")
    op.drop_table("official_snapshots")

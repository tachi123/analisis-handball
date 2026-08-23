"""Add goalkeeper shots table.

Revision ID: 20260823_0011
Revises: 20260823_0010
Create Date: 2026-08-23 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260823_0011"
down_revision = "20260823_0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "goalkeeper_shots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("shooter_player_id", sa.Integer(), nullable=True),
        sa.Column("shooter_label", sa.String(16), nullable=True),
        sa.Column("period", sa.Integer(), nullable=True),
        sa.Column("video_timestamp", sa.Float(), nullable=True),
        sa.Column("origin_zone", sa.String(24), nullable=True),
        sa.Column("target_zone", sa.String(16), nullable=True),
        sa.Column("shot_type", sa.String(8), nullable=True),
        sa.Column("outcome", sa.String(12), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.ForeignKeyConstraint(["shooter_player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_goalkeeper_shots_id"), "goalkeeper_shots", ["id"])
    op.create_index(op.f("ix_goalkeeper_shots_match_id"), "goalkeeper_shots", ["match_id"])


def downgrade():
    op.drop_index(op.f("ix_goalkeeper_shots_match_id"), table_name="goalkeeper_shots")
    op.drop_index(op.f("ix_goalkeeper_shots_id"), table_name="goalkeeper_shots")
    op.drop_table("goalkeeper_shots")

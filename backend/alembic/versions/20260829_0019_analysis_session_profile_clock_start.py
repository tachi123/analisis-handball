"""Persist the selected review profile and initial match-clock offset.

Revision ID: 20260829_0019
Revises: 73b208e83d81
"""
from alembic import op
import sqlalchemy as sa


revision = "20260829_0019"
down_revision = "73b208e83d81"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("analysis_sessions") as batch:
        batch.add_column(sa.Column("profile", sa.String(), nullable=False, server_default="complete"))
        batch.add_column(sa.Column("clock_start_video_seconds", sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table("analysis_sessions") as batch:
        batch.drop_column("clock_start_video_seconds")
        batch.drop_column("profile")

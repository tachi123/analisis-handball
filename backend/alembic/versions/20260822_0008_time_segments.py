"""Add discontinuous video-to-regulation time segments."""
from alembic import op
import sqlalchemy as sa


revision = "20260822_0008"
down_revision = "20260822_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "time_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("analyst_id", sa.Integer(), nullable=False),
        sa.Column("period", sa.Integer(), nullable=False),
        sa.Column("video_start_seconds", sa.Float(), nullable=False),
        sa.Column("video_end_seconds", sa.Float(), nullable=False),
        sa.Column("regulation_start_seconds", sa.Float()),
        sa.Column("regulation_end_seconds", sa.Float()),
        sa.Column("uncertainty_seconds", sa.Float(), nullable=False),
        sa.Column("coverage", sa.String(), nullable=False),
        sa.Column("clock_unverified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"]),
        sa.ForeignKeyConstraint(["analyst_id"], ["users.id"]),
    )


def downgrade():
    op.drop_table("time_segments")

"""Add observed analytical outcomes for denominator-aware metrics.

Revision ID: 20260822_0004
Revises: 20260822_0003
Create Date: 2026-08-22 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260822_0004"
down_revision = "20260822_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("analysis_events", sa.Column("outcome", sa.String(), nullable=True))


def downgrade():
    op.drop_column("analysis_events", "outcome")

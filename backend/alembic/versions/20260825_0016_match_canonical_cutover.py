"""Add opt-in per-match canonical analysis cutover control.

Revision ID: 20260825_0016
Revises: 20260825_0015
"""
from alembic import op
import sqlalchemy as sa


revision = "20260825_0016"
down_revision = "20260825_0015"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("matches") as batch_op:
        batch_op.add_column(sa.Column("canonical_analysis_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table("matches") as batch_op:
        batch_op.drop_column("canonical_analysis_enabled")

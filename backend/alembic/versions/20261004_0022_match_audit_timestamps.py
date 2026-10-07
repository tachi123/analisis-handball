"""Enforce match audit timestamps.

Revision ID: 20261004_0022
Revises: 20261004_0021
"""
from alembic import op
import sqlalchemy as sa


revision = "20261004_0022"
down_revision = "20261004_0021"
branch_labels = None
depends_on = None


def upgrade():
    # Preserve recorded values; only legacy rows missing an audit timestamp are backfilled.
    op.execute("UPDATE matches SET created_at = COALESCE(created_at, updated_at, CURRENT_TIMESTAMP) WHERE created_at IS NULL")
    op.execute("UPDATE matches SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) WHERE updated_at IS NULL")
    with op.batch_alter_table("matches") as batch:
        batch.alter_column("created_at", existing_type=sa.DateTime(), nullable=False,
                           server_default=sa.text("CURRENT_TIMESTAMP"))
        batch.alter_column("updated_at", existing_type=sa.DateTime(), nullable=False,
                           server_default=sa.text("CURRENT_TIMESTAMP"))


def downgrade():
    with op.batch_alter_table("matches") as batch:
        batch.alter_column("updated_at", existing_type=sa.DateTime(), nullable=True,
                           server_default=None)
        batch.alter_column("created_at", existing_type=sa.DateTime(), nullable=True,
                           server_default=None)

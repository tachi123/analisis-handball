"""Add explicit publication approval for official sheets.

Revision ID: 20261014_0024
Revises: 20261011_0023
"""
from alembic import op
import sqlalchemy as sa


revision = "20261014_0024"
down_revision = "20261011_0023"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("official_snapshots") as batch:
        batch.add_column(sa.Column("is_publicly_published", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_index("ix_official_snapshots_is_publicly_published", ["is_publicly_published"])


def downgrade():
    with op.batch_alter_table("official_snapshots") as batch:
        batch.drop_index("ix_official_snapshots_is_publicly_published")
        batch.drop_column("is_publicly_published")

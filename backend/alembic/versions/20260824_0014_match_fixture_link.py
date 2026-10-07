"""Add the optional one-to-one analysis match fixture bridge.

Revision ID: 20260824_0014
Revises: 20260824_0013
Create Date: 2026-08-24 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260824_0014"
down_revision = "20260824_0013"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("matches") as batch_op:
        batch_op.add_column(
            sa.Column("scheduled_match_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_matches_scheduled_match_id",
            "scheduled_matches",
            ["scheduled_match_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_matches_scheduled_match_id", ["scheduled_match_id"]
        )


def downgrade():
    with op.batch_alter_table("matches") as batch_op:
        batch_op.drop_constraint("uq_matches_scheduled_match_id", type_="unique")
        batch_op.drop_constraint("fk_matches_scheduled_match_id", type_="foreignkey")
        batch_op.drop_column("scheduled_match_id")

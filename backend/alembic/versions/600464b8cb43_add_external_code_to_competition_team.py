"""add external_code to competition_team

Revision ID: 600464b8cb43
Revises: 20260826_0018
Create Date: 2026-08-26 21:45:59.998164
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '600464b8cb43'
down_revision = '20260826_0018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "competition_teams",
        sa.Column("external_code", sa.String(64), nullable=True),
    )
    op.create_index(
        op.f("ix_competition_teams_external_code"),
        "competition_teams",
        ["external_code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_competition_teams_external_code"), table_name="competition_teams")
    op.drop_column("competition_teams", "external_code")
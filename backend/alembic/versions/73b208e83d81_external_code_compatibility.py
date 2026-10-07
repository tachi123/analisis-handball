"""preserve the historical external-code revision

Revision ID: 73b208e83d81
Revises: 600464b8cb43
Create Date: 2026-08-28 00:00:00.000000

The historical revision duplicated the external_code column and unique-index
DDL already applied by 600464b8cb43. Retain its identifier as a no-op so
preloaded databases at this revision remain resolvable without replaying DDL.
"""


# revision identifiers, used by Alembic.
revision = "73b208e83d81"
down_revision = "600464b8cb43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The preceding revision already created external_code and its unique index.
    pass


def downgrade() -> None:
    # This compatibility marker owns no schema changes to reverse.
    pass

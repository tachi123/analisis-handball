"""Track manual match origin and creator.

Revision ID: 20261004_0021
Revises: 20261003_0020
"""
from alembic import op
import sqlalchemy as sa


revision = "20261004_0021"
down_revision = "20261003_0020"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("matches") as batch:
        batch.add_column(sa.Column("origin", sa.String(), nullable=False, server_default="legacy"))
        batch.add_column(sa.Column("created_by_user_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key("fk_matches_created_by_user", "users", ["created_by_user_id"], ["id"])
        batch.create_index("ix_matches_origin", ["origin"])
        batch.create_index("ix_matches_created_by_user_id", ["created_by_user_id"])
    op.execute("UPDATE matches SET origin = 'fixture' WHERE scheduled_match_id IS NOT NULL")


def downgrade():
    with op.batch_alter_table("matches") as batch:
        batch.drop_index("ix_matches_created_by_user_id")
        batch.drop_index("ix_matches_origin")
        batch.drop_constraint("fk_matches_created_by_user", type_="foreignkey")
        batch.drop_column("updated_at")
        batch.drop_column("created_at")
        batch.drop_column("created_by_user_id")
        batch.drop_column("origin")

"""Add private server-local video assets.

Revision ID: 20261113_0025
Revises: 20261014_0024
"""
from alembic import op
import sqlalchemy as sa

revision = "20261113_0025"
down_revision = "20261014_0024"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "local_video_assets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("storage_name", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("match_id", "sha256", name="uq_local_video_asset_match_sha"),
    )
    op.create_index("ix_local_video_assets_match_id", "local_video_assets", ["match_id"])


def downgrade():
    op.drop_index("ix_local_video_assets_match_id", table_name="local_video_assets")
    op.drop_table("local_video_assets")

"""Add official preload batch provenance.

Revision ID: 20260826_0018
Revises: 20260825_0017
"""
from alembic import op
import sqlalchemy as sa


revision = "20260826_0018"
down_revision = "20260825_0017"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "official_batch_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=False),
        sa.Column("derived_sha256", sa.String(length=64), nullable=False),
        sa.Column("mapping_sha256", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("rolled_back_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_official_batch_runs_manifest_sha256", "official_batch_runs", ["manifest_sha256"])
    with op.batch_alter_table("official_snapshots") as batch:
        batch.add_column(sa.Column("batch_run_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.create_foreign_key("fk_official_snapshot_batch_run", "official_batch_runs", ["batch_run_id"], ["id"])
        batch.create_index("ix_official_snapshots_batch_run_id", ["batch_run_id"])
        batch.create_index("ix_official_snapshots_is_confirmed", ["is_confirmed"])


def downgrade():
    with op.batch_alter_table("official_snapshots") as batch:
        batch.drop_index("ix_official_snapshots_is_confirmed")
        batch.drop_index("ix_official_snapshots_batch_run_id")
        batch.drop_constraint("fk_official_snapshot_batch_run", type_="foreignkey")
        batch.drop_column("is_confirmed")
        batch.drop_column("batch_run_id")
    op.drop_index("ix_official_batch_runs_manifest_sha256", table_name="official_batch_runs")
    op.drop_table("official_batch_runs")

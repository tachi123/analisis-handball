"""Add revision-owned evidence links to canonical evidence.

Revision ID: 20260825_0017
Revises: 20260825_0016
"""
from alembic import op
import sqlalchemy as sa


revision = "20260825_0017"
down_revision = "20260825_0016"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("canonical_evidence") as batch:
        batch.add_column(sa.Column("scheduled_match_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("official_snapshot_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("video_source_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("video_anchor_seconds", sa.Float(), nullable=True))
        batch.add_column(sa.Column("report_package_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_canonical_evidence_scheduled_match", "scheduled_matches", ["scheduled_match_id"], ["id"])
        batch.create_foreign_key("fk_canonical_evidence_official_snapshot", "official_snapshots", ["official_snapshot_id"], ["id"])
        batch.create_foreign_key("fk_canonical_evidence_video_source", "video_sources", ["video_source_id"], ["id"])
        batch.create_foreign_key("fk_canonical_evidence_report_package", "report_packages", ["report_package_id"], ["id"])
        batch.alter_column("reference", existing_type=sa.String(), nullable=True)


def downgrade():
    with op.batch_alter_table("canonical_evidence") as batch:
        batch.drop_constraint("fk_canonical_evidence_report_package", type_="foreignkey")
        batch.drop_constraint("fk_canonical_evidence_video_source", type_="foreignkey")
        batch.drop_constraint("fk_canonical_evidence_official_snapshot", type_="foreignkey")
        batch.drop_constraint("fk_canonical_evidence_scheduled_match", type_="foreignkey")
        batch.alter_column("reference", existing_type=sa.String(), nullable=False)
        batch.drop_column("report_package_id")
        batch.drop_column("video_anchor_seconds")
        batch.drop_column("video_source_id")
        batch.drop_column("official_snapshot_id")
        batch.drop_column("scheduled_match_id")

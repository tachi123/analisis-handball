"""Add local report package, publication, and recovery records."""
from alembic import op
import sqlalchemy as sa


revision = "20260822_0006"
down_revision = "20260822_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("report_packages", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("match_id", sa.Integer(), nullable=False), sa.Column("analyst_id", sa.Integer(), nullable=False), sa.Column("report_version", sa.Integer(), nullable=False), sa.Column("schema_version", sa.String(), nullable=False), sa.Column("coaching_question", sa.String(), nullable=False), sa.Column("pattern_statement", sa.String(), nullable=False), sa.Column("action_kind", sa.String(), nullable=False), sa.Column("action_text", sa.String(), nullable=False), sa.Column("uncertainty_disclosure", sa.String(), nullable=False), sa.Column("metrics", sa.JSON(), nullable=False), sa.Column("reconciliation", sa.JSON(), nullable=False), sa.Column("source_label", sa.String()), sa.Column("source_status", sa.String()), sa.Column("approved_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["match_id"], ["matches.id"]), sa.ForeignKeyConstraint(["analyst_id"], ["users.id"]))
    op.create_table("report_package_evidence", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("package_id", sa.Integer(), nullable=False), sa.Column("analysis_event_id", sa.Integer()), sa.Column("reference", sa.String(), nullable=False), sa.Column("period", sa.Integer(), nullable=False), sa.Column("regulation_seconds", sa.Float()), sa.Column("clock_unverified", sa.Boolean(), nullable=False), sa.Column("public_observation", sa.String()), sa.Column("private_note", sa.String()), sa.Column("public_media_url", sa.String()), sa.Column("public_approved", sa.Boolean(), nullable=False), sa.Column("media_public_approved", sa.Boolean(), nullable=False), sa.ForeignKeyConstraint(["package_id"], ["report_packages.id"]), sa.ForeignKeyConstraint(["analysis_event_id"], ["analysis_events.id"]))
    op.create_table("recovery_artifacts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("package_id", sa.Integer(), nullable=False), sa.Column("artifact_type", sa.String(), nullable=False), sa.Column("location", sa.String(), nullable=False), sa.Column("verified_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["package_id"], ["report_packages.id"]))
    op.create_table("report_publications", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("package_id", sa.Integer(), nullable=False), sa.Column("report_version", sa.Integer(), nullable=False), sa.Column("schema_version", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("published_at", sa.DateTime()), sa.ForeignKeyConstraint(["package_id"], ["report_packages.id"]))


def downgrade():
    op.drop_table("report_publications")
    op.drop_table("recovery_artifacts")
    op.drop_table("report_package_evidence")
    op.drop_table("report_packages")

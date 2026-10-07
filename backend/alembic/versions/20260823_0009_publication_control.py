"""Add globally versioned report publication control."""
from alembic import op
import sqlalchemy as sa


revision = "20260823_0009"
down_revision = "20260822_0008"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("report_packages") as batch_op:
        batch_op.add_column(sa.Column("replaces_package_id", sa.Integer()))
        batch_op.create_foreign_key("fk_report_packages_replaces_package", "report_packages", ["replaces_package_id"], ["id"])

    # Legacy packages all used version 1. Preserve their order while giving every
    # package a distinct global version before enforcing the new constraint.
    op.execute("""
        WITH ordered AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY created_at, id) AS report_version
            FROM report_packages
        )
        UPDATE report_packages
        SET report_version = (SELECT report_version FROM ordered WHERE ordered.id = report_packages.id)
    """)
    with op.batch_alter_table("report_packages") as batch_op:
        batch_op.create_unique_constraint("uq_report_package_report_version", ["report_version"])
    op.execute("""
        UPDATE report_publications
        SET report_version = (
            SELECT report_version FROM report_packages
            WHERE report_packages.id = report_publications.package_id
        )
    """)

    with op.batch_alter_table("recovery_artifacts") as batch_op:
        batch_op.add_column(sa.Column("attested_at", sa.DateTime()))
        batch_op.add_column(sa.Column("attested_by_user_id", sa.Integer()))
        batch_op.create_foreign_key("fk_recovery_artifacts_attested_by_user", "users", ["attested_by_user_id"], ["id"])
        batch_op.create_unique_constraint("uq_recovery_artifact_package_type", ["package_id", "artifact_type"])
    op.execute("UPDATE recovery_artifacts SET attested_at = verified_at WHERE verified_at IS NOT NULL")
    with op.batch_alter_table("recovery_artifacts") as batch_op:
        batch_op.drop_column("verified_at")

    op.create_table(
        "report_publication_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("current_package_id", sa.Integer(), nullable=True),
        sa.Column("current_report_version", sa.Integer(), nullable=True),
        sa.Column("next_report_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["current_package_id"], ["report_packages.id"]),
    )
    op.execute("""
        INSERT INTO report_publication_state (id, current_package_id, current_report_version, next_report_version)
        SELECT 1,
            (SELECT package_id FROM report_publications WHERE status = 'published' ORDER BY report_version DESC, id DESC LIMIT 1),
            (SELECT MAX(report_version) FROM report_publications WHERE status = 'published'),
            COALESCE((SELECT MAX(report_version) FROM report_packages), 0) + 1
    """)


def downgrade():
    op.drop_table("report_publication_state")
    with op.batch_alter_table("recovery_artifacts") as batch_op:
        batch_op.add_column(sa.Column("verified_at", sa.DateTime()))
    op.execute("UPDATE recovery_artifacts SET verified_at = attested_at WHERE attested_at IS NOT NULL")
    with op.batch_alter_table("recovery_artifacts") as batch_op:
        batch_op.drop_constraint("uq_recovery_artifact_package_type", type_="unique")
        batch_op.drop_constraint("fk_recovery_artifacts_attested_by_user", type_="foreignkey")
        batch_op.drop_column("attested_by_user_id")
        batch_op.drop_column("attested_at")
    with op.batch_alter_table("report_packages") as batch_op:
        batch_op.drop_constraint("uq_report_package_report_version", type_="unique")
        batch_op.drop_constraint("fk_report_packages_replaces_package", type_="foreignkey")
        batch_op.drop_column("replaces_package_id")

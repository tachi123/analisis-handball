"""Make report publication records idempotent by report version."""
from alembic import op


revision = "20260822_0007"
down_revision = "20260822_0006"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("report_publications") as batch_op:
        batch_op.create_unique_constraint("uq_report_publication_version", ["package_id", "report_version"])


def downgrade():
    with op.batch_alter_table("report_publications") as batch_op:
        batch_op.drop_constraint("uq_report_publication_version", type_="unique")

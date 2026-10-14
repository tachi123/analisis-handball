"""Scope canonical ledgers and analyst workspaces to immutable analysis runs.

Revision ID: 20261011_0023
Revises: 20261004_0022
"""
from alembic import op
import sqlalchemy as sa


revision = "20261011_0023"
down_revision = "20261004_0022"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("promoted_at", sa.DateTime(), nullable=True),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_analysis_runs_match_id", "analysis_runs", ["match_id"])
    op.create_index("ix_analysis_runs_status", "analysis_runs", ["status"])
    # Every pre-run canonical ledger becomes one active, immutable legacy run.
    # Only matches that actually have canonical events or sessions get a legacy run.
    # This preserves existing PKs/payloads for Matches 16, 98, 99, etc.
    op.execute("""
        INSERT INTO analysis_runs (match_id, mode, status, created_at, promoted_at)
        SELECT match_id, 'legacy', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM (
            SELECT match_id FROM canonical_events
            UNION
            SELECT match_id FROM analysis_sessions
        ) legacy_matches
    """)
    # Matches with legacy runs already have canonical_analysis_enabled = 1 or will be enabled
    # by the cutover process. Don't auto-enable untouched matches.
    op.create_index(
        "uq_analysis_runs_active_match", "analysis_runs", ["match_id"], unique=True,
        sqlite_where=sa.text("status = 'active'"), postgresql_where=sa.text("status = 'active'"),
    )

    with op.batch_alter_table("canonical_events") as batch:
        batch.add_column(sa.Column("run_id", sa.Integer(), nullable=True))
    op.execute("""
        UPDATE canonical_events
        SET run_id = (SELECT id FROM analysis_runs WHERE analysis_runs.match_id = canonical_events.match_id AND status = 'active')
    """)
    with op.batch_alter_table("canonical_events") as batch:
        batch.alter_column("run_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key("fk_canonical_events_run", "analysis_runs", ["run_id"], ["id"])
        batch.drop_constraint("uq_canonical_event_sequence", type_="unique")
        batch.create_unique_constraint("uq_canonical_event_sequence", ["run_id", "sequence"])
        batch.create_index("ix_canonical_events_run_id", ["run_id"])

    with op.batch_alter_table("analysis_sessions") as batch:
        batch.add_column(sa.Column("run_id", sa.Integer(), nullable=True))
    op.execute("""
        UPDATE analysis_sessions
        SET run_id = (SELECT id FROM analysis_runs WHERE analysis_runs.match_id = analysis_sessions.match_id AND status = 'active')
    """)
    with op.batch_alter_table("analysis_sessions") as batch:
        batch.alter_column("run_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key("fk_analysis_sessions_run", "analysis_runs", ["run_id"], ["id"])
        batch.create_index("ix_analysis_sessions_run_id", ["run_id"])


def downgrade():
    with op.batch_alter_table("analysis_sessions") as batch:
        batch.drop_index("ix_analysis_sessions_run_id")
        batch.drop_constraint("fk_analysis_sessions_run", type_="foreignkey")
        batch.drop_column("run_id")
    with op.batch_alter_table("canonical_events") as batch:
        batch.drop_index("ix_canonical_events_run_id")
        batch.drop_constraint("uq_canonical_event_sequence", type_="unique")
        batch.create_unique_constraint("uq_canonical_event_sequence", ["match_id", "sequence"])
        batch.drop_constraint("fk_canonical_events_run", type_="foreignkey")
        batch.drop_column("run_id")
    op.drop_index("uq_analysis_runs_active_match", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_status", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_match_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")

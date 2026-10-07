"""Add the immutable canonical live-analysis ledger.

Revision ID: 20260825_0015
Revises: 20260824_0014
"""
from alembic import op
import sqlalchemy as sa


revision = "20260825_0015"
down_revision = "20260824_0014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("canonical_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.UniqueConstraint("match_id", "sequence", name="uq_canonical_event_sequence"))
    op.create_table("canonical_event_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), nullable=False), sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False), sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["canonical_events.id"]), sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.UniqueConstraint("event_id", "revision", name="uq_canonical_event_revision"))
    op.create_table("canonical_evidence",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("revision_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False), sa.Column("reference", sa.String(), nullable=False),
        sa.Column("uncertainty", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["revision_id"], ["canonical_event_revisions.id"]))
    op.create_table("canonical_projections",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("revision_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["revision_id"], ["canonical_event_revisions.id"]))
    for table, column in (("canonical_events", "match_id"), ("canonical_event_revisions", "event_id"), ("canonical_evidence", "revision_id"), ("canonical_projections", "revision_id")):
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    for table, column in (("canonical_projections", "revision_id"), ("canonical_evidence", "revision_id"), ("canonical_event_revisions", "event_id"), ("canonical_events", "match_id")):
        op.drop_index(f"ix_{table}_{column}", table_name=table)
    op.drop_table("canonical_projections")
    op.drop_table("canonical_evidence")
    op.drop_table("canonical_event_revisions")
    op.drop_table("canonical_events")

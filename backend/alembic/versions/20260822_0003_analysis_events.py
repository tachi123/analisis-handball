"""Add versioned analytical events and audit history.

Revision ID: 20260822_0003
Revises: 20260822_0002
Create Date: 2026-08-22 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260822_0003"
down_revision = "20260822_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("analysis_codebook_entries", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("version", sa.String(), nullable=False), sa.Column("code", sa.String(), nullable=False), sa.Column("category", sa.String(), nullable=False), sa.UniqueConstraint("version", "code"))
    op.bulk_insert(sa.table("analysis_codebook_entries", sa.column("version", sa.String()), sa.column("code", sa.String()), sa.column("category", sa.String())), [{"version": "mvp-1", "code": code, "category": category} for code, category in [("shot", "attack"), ("seven_meter", "attack"), ("confirmed_assist", "attack"), ("turnover", "possession"), ("recovery", "defense"), ("defensive_action", "defense"), ("foul_sanction", "discipline"), ("transition_outcome", "transition"), ("goalkeeper_outcome", "goalkeeper")]])
    op.create_table("analysis_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("match_id", sa.Integer(), nullable=False), sa.Column("codebook_entry_id", sa.Integer(), nullable=False), sa.Column("analyst_id", sa.Integer(), nullable=False), sa.Column("period", sa.Integer(), nullable=False), sa.Column("regulation_seconds", sa.Float()), sa.Column("video_timestamp", sa.Float()), sa.Column("clock_unverified", sa.Boolean(), nullable=False), sa.Column("team_action", sa.String()), sa.Column("player_id", sa.Integer()), sa.Column("turnover_cause", sa.String()), sa.Column("evidence_state", sa.String(), nullable=False), sa.Column("source", sa.String()), sa.Column("angle", sa.String()), sa.Column("note", sa.String()), sa.Column("included", sa.Boolean(), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["match_id"], ["matches.id"]), sa.ForeignKeyConstraint(["codebook_entry_id"], ["analysis_codebook_entries.id"]), sa.ForeignKeyConstraint(["analyst_id"], ["users.id"]), sa.ForeignKeyConstraint(["player_id"], ["players.id"]))
    op.create_table("analysis_event_revisions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("event_id", sa.Integer(), nullable=False), sa.Column("actor_id", sa.Integer(), nullable=False), sa.Column("before_payload", sa.JSON()), sa.Column("after_payload", sa.JSON()), sa.Column("reason", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["event_id"], ["analysis_events.id"]), sa.ForeignKeyConstraint(["actor_id"], ["users.id"]))


def downgrade():
    op.drop_table("analysis_event_revisions")
    op.drop_table("analysis_events")
    op.drop_table("analysis_codebook_entries")

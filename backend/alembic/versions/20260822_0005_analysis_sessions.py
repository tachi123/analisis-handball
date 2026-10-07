"""Add video sources, recoverable analysis sessions, and period anchors."""
from alembic import op
import sqlalchemy as sa

revision = "20260822_0005"
down_revision = "20260822_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("video_sources", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("match_id", sa.Integer(), nullable=False), sa.Column("original_url", sa.String(), nullable=False), sa.Column("provider", sa.String(), nullable=False), sa.Column("provider_video_id", sa.String(), nullable=False), sa.Column("availability_state", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["match_id"], ["matches.id"]))
    op.create_table("analysis_sessions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("match_id", sa.Integer(), nullable=False), sa.Column("analyst_id", sa.Integer(), nullable=False), sa.Column("video_source_id", sa.Integer()), sa.Column("mode", sa.String(), nullable=False), sa.Column("video_position_seconds", sa.Float()), sa.Column("angle", sa.String()), sa.Column("filters", sa.JSON(), nullable=False), sa.Column("draft", sa.JSON(), nullable=False), sa.Column("queue", sa.JSON(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["match_id"], ["matches.id"]), sa.ForeignKeyConstraint(["analyst_id"], ["users.id"]), sa.ForeignKeyConstraint(["video_source_id"], ["video_sources.id"]), sa.UniqueConstraint("match_id", "analyst_id"))
    op.create_table("time_anchors", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("session_id", sa.Integer(), nullable=False), sa.Column("analyst_id", sa.Integer(), nullable=False), sa.Column("period", sa.Integer(), nullable=False), sa.Column("video_seconds", sa.Float(), nullable=False), sa.Column("regulation_seconds", sa.Float(), nullable=False), sa.Column("uncertainty_seconds", sa.Float(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"]), sa.ForeignKeyConstraint(["analyst_id"], ["users.id"]))


def downgrade():
    op.drop_table("time_anchors")
    op.drop_table("analysis_sessions")
    op.drop_table("video_sources")

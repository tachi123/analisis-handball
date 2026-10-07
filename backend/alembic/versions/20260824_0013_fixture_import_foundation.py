"""Add fixture import provenance and stable fixture identity.

Revision ID: 20260824_0013
Revises: 20260824_0012
Create Date: 2026-08-24 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260824_0013"
down_revision = "20260824_0012"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("competition_teams") as batch_op:
        batch_op.add_column(sa.Column("variant_key", sa.String(length=2), nullable=True))
        batch_op.alter_column("suffix", existing_type=sa.String(length=2), nullable=True)
        batch_op.drop_constraint("uq_comp_team_identity", type_="unique")

    op.execute("UPDATE competition_teams SET variant_key = COALESCE(suffix, '')")

    with op.batch_alter_table("competition_teams") as batch_op:
        batch_op.alter_column("variant_key", existing_type=sa.String(length=2), nullable=False)
        batch_op.create_unique_constraint(
            "uq_comp_team_variant_identity", ["club_id", "stage_id", "variant_key"]
        )

    with op.batch_alter_table("scheduled_matches") as batch_op:
        batch_op.add_column(sa.Column("fixture_key", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("source_home_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("source_away_score", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("result_status", sa.String(), nullable=False, server_default="unreported")
        )

    op.execute(
        "UPDATE scheduled_matches SET fixture_key = "
        "'legacy:' || stage_id || ':' || round_id || ':' || "
        "home_registration_id || ':' || away_registration_id || ':' || id"
    )
    with op.batch_alter_table("scheduled_matches") as batch_op:
        batch_op.alter_column("fixture_key", existing_type=sa.String(), nullable=False)
    op.create_index("ix_scheduled_matches_fixture_key", "scheduled_matches", ["fixture_key"], unique=True)
    op.create_table(
        "fixture_imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("source_label", sa.String(), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["stage_id"], ["tournament_stages.id"]),
        sa.UniqueConstraint("source_sha256", name="uq_fixture_import_source_sha256"),
    )
    op.create_index("ix_fixture_imports_stage_id", "fixture_imports", ["stage_id"])
    op.create_index("ix_fixture_imports_source_sha256", "fixture_imports", ["source_sha256"])
    op.create_table(
        "fixture_import_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fixture_import_id", sa.Integer(), nullable=False),
        sa.Column("entry_key", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("raw_entry", sa.JSON(), nullable=False),
        sa.Column("scheduled_match_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["fixture_import_id"], ["fixture_imports.id"]),
        sa.ForeignKeyConstraint(["scheduled_match_id"], ["scheduled_matches.id"]),
        sa.UniqueConstraint("fixture_import_id", "entry_key", name="uq_fixture_import_entry_key"),
    )
    op.create_index("ix_fixture_import_entries_fixture_import_id", "fixture_import_entries", ["fixture_import_id"])
    op.create_index("ix_fixture_import_entries_scheduled_match_id", "fixture_import_entries", ["scheduled_match_id"])


def downgrade():
    op.drop_index("ix_fixture_import_entries_scheduled_match_id", table_name="fixture_import_entries")
    op.drop_index("ix_fixture_import_entries_fixture_import_id", table_name="fixture_import_entries")
    op.drop_table("fixture_import_entries")
    op.drop_index("ix_fixture_imports_source_sha256", table_name="fixture_imports")
    op.drop_index("ix_fixture_imports_stage_id", table_name="fixture_imports")
    op.drop_table("fixture_imports")
    op.drop_index("ix_scheduled_matches_fixture_key", table_name="scheduled_matches")
    with op.batch_alter_table("scheduled_matches") as batch_op:
        batch_op.drop_column("result_status")
        batch_op.drop_column("source_away_score")
        batch_op.drop_column("source_home_score")
        batch_op.drop_column("fixture_key")
    with op.batch_alter_table("competition_teams") as batch_op:
        batch_op.drop_constraint("uq_comp_team_variant_identity", type_="unique")
        # The prior schema requires a non-null suffix. Preserve the valid
        # absent-variant representation as its compatible legacy empty value.
        op.execute("UPDATE competition_teams SET suffix = '' WHERE suffix IS NULL")
        batch_op.alter_column("suffix", existing_type=sa.String(length=2), nullable=False)
        batch_op.create_unique_constraint("uq_comp_team_identity", ["club_id", "suffix", "stage_id"])
        batch_op.drop_column("variant_key")

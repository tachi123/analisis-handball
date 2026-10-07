"""Reconcile duplicate logical video sources before enforcing their identity.

Revision ID: 20261003_0020
Revises: 20260829_0019
"""
from alembic import op
import sqlalchemy as sa


revision = "20261003_0020"
down_revision = "20260829_0019"
branch_labels = None
depends_on = None


def _video_source_references(bind):
    """Return all single-column FKs that point at video_sources.id."""
    inspector = sa.inspect(bind)
    references = []
    for table_name in inspector.get_table_names():
        if table_name in {"alembic_version", "video_sources"}:
            continue
        for foreign_key in inspector.get_foreign_keys(table_name):
            if (foreign_key["referred_table"] == "video_sources"
                    and foreign_key["referred_columns"] == ["id"]
                    and len(foreign_key["constrained_columns"]) == 1):
                references.append((table_name, foreign_key["constrained_columns"][0]))
    return references


def upgrade():
    bind = op.get_bind()
    sources = sa.table(
        "video_sources",
        sa.column("id", sa.Integer),
        sa.column("match_id", sa.Integer),
        sa.column("provider", sa.String),
        sa.column("provider_video_id", sa.String),
    )
    references = _video_source_references(bind)
    duplicate_groups = bind.execute(
        sa.select(
            sources.c.match_id,
            sources.c.provider,
            sources.c.provider_video_id,
            sa.func.min(sources.c.id).label("canonical_id"),
        ).group_by(
            sources.c.match_id, sources.c.provider, sources.c.provider_video_id,
        ).having(sa.func.count(sources.c.id) > 1)
    ).mappings()

    for group in duplicate_groups:
        duplicate_ids = bind.execute(
            sa.select(sources.c.id).where(
                sources.c.match_id == group["match_id"],
                sources.c.provider == group["provider"],
                sources.c.provider_video_id == group["provider_video_id"],
                sources.c.id != group["canonical_id"],
            )
        ).scalars().all()
        for table_name, column_name in references:
            table = sa.Table(table_name, sa.MetaData(), autoload_with=bind)
            bind.execute(
                table.update().where(table.c[column_name].in_(duplicate_ids)).values(
                    {column_name: group["canonical_id"]}
                )
            )
        for table_name, column_name in references:
            table = sa.Table(table_name, sa.MetaData(), autoload_with=bind)
            remaining = bind.execute(
                sa.select(sa.func.count()).select_from(table).where(table.c[column_name].in_(duplicate_ids))
            ).scalar_one()
            if remaining:
                raise RuntimeError(
                    f"video source reconciliation left {remaining} references in {table_name}.{column_name}"
                )
        bind.execute(sources.delete().where(sources.c.id.in_(duplicate_ids)))

    with op.batch_alter_table("video_sources") as batch:
        batch.create_unique_constraint(
            "uq_video_source_match_provider_video",
            ["match_id", "provider", "provider_video_id"],
        )


def downgrade():
    with op.batch_alter_table("video_sources") as batch:
        batch.drop_constraint("uq_video_source_match_provider_video", type_="unique")

import os

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

load_dotenv()

from app import models  # noqa: F401
from app.database import Base

config = context.config
raw_database_url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
if not raw_database_url:
    raise RuntimeError("DATABASE_URL must be set to run Alembic migrations")

database_url = raw_database_url.replace("postgres://", "postgresql://", 1)
# ConfigParser treats percent-encoded credentials as interpolation tokens.
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

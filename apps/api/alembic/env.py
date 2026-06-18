"""Alembic environment configuration.

Key design decisions:
- DATABASE_URL is read from the environment so the same migration can run
  against dev, test, and production databases without code changes.
- All models are imported here (via app.models) so autogenerate can detect
  schema changes.
- We use synchronous migrations (offline and online) which is simpler and
  sufficient for this stack. If async SQLAlchemy is added later, this file
  would need to use run_async_migrations().
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Put the project root on the path so `app` is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import all models so Alembic's autogenerate detects them.
# As new models are added, import them here.
from app.models import ai_log, exercise, goal, measurement, nutrition, user, weight_entry, workout  # noqa: F401
from app.models.base import Base

# Interpret the config file for Python logging.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the DATABASE_URL from the environment if present.
db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live database connection.

    Useful for generating SQL scripts to review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

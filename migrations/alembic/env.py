"""Alembic environment configuration.

Reads DATABASE_URL from pydantic-settings (shared.config) so the connection
string is always consistent with the application.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure project root is on sys.path so shared.config is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Set up Python logging from the config file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No SQLAlchemy MetaData for autogenerate (we use raw SQL migrations)
target_metadata = None


def _get_database_url() -> str:
    """Resolve the database URL from pydantic-settings, falling back to alembic.ini."""
    try:
        from shared.config import get_settings

        return get_settings().database_url
    except Exception:
        # Fallback: use the value from alembic.ini or DATABASE_URL env var
        url = os.environ.get("DATABASE_URL")
        if url:
            return url
        return config.get_main_option("sqlalchemy.url", "")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL to stdout."""
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connect to the database."""
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _get_database_url()

    connectable = engine_from_config(
        cfg,
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

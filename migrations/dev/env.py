from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from scripts.migration_runtime import bootstrap_runtime

bootstrap_runtime(ROOT_DIR)

import smart_common.models  # noqa: F401,E402
from smart_common.core.db import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

target_env = config.get_main_option("target_env") or "dev"
database_url = config.get_main_option("sqlalchemy.url")

if not database_url:
    env_var = "DB_URL_DEV" if target_env == "dev" else "DB_URL_PROD"
    fallback = os.getenv(env_var)
    if not fallback:
        raise RuntimeError(f"Missing database URL. Set {env_var} in .env")
    config.set_main_option("sqlalchemy.url", fallback.replace("%", "%%"))
    database_url = fallback


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
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

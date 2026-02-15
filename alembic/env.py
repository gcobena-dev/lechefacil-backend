from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.config.settings import get_settings
from src.infrastructure.db.base import Base
from src.infrastructure.db.orm import (
    animal,  # noqa: F401
    animal_status,  # noqa: F401
    attachment,  # noqa: F401
    breed,  # noqa: F401
    buyer,  # noqa: F401
    lot,  # noqa: F401
    membership,  # noqa: F401
    milk_delivery,  # noqa: F401
    milk_price,  # noqa: F401
    milk_production,  # noqa: F401
    tenant_config,  # noqa: F401
    user,  # noqa: F401
    animal_event,  # noqa: F401
    animal_parentage,  # noqa: F401
    animal_certificate,  # noqa: F401
    lactation,  # noqa: F401
    notification,  # noqa: F401
    one_time_token,  # noqa: F401
    health_record,  # noqa: F401
    sire_catalog,  # noqa: F401
    semen_inventory,  # noqa: F401
    insemination,  # noqa: F401
)

config = context.config

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="lechefacil",
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    # Ensure the lechefacil schema exists and set it as default search_path
    # so all unqualified table names resolve to lechefacil (not public).
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS lechefacil"))
    connection.execute(text("SET search_path TO lechefacil"))

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema="lechefacil",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable: AsyncEngine = create_async_engine(get_url(), poolclass=pool.NullPool)

    async def run_async_migrations() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
            await connection.commit()
        await connectable.dispose()

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

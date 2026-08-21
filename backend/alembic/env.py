"""Alembic environment -- Phase 1.1.

Builds a ``DataSource`` the same way ``AppModule`` does (same entity list, imported from
``src.db.entities.ALL_ENTITIES`` so the two can never drift -- see that module's docstring), then
uses ``DataSource.get_metadata()`` (the one deliberate ``sqlalchemy.MetaData`` seam
``austial.orm`` exposes -- see that method's own docstring) as ``target_metadata`` for
autogenerate.

Async, not the classic sync template: the only Postgres driver this app depends on is
``asyncpg`` (``PostgresDriver``/``SqlAlchemyEngineDriver`` in ``austial.orm``, matching
``AppModule``'s ``DATABASE_URL``), and there is no sync driver (e.g. ``psycopg2``) installed to
back a classic sync ``engine_from_config``. Migrations therefore run over a real
``sqlalchemy.ext.asyncio`` engine and ``AsyncConnection.run_sync(...)``, per Alembic's own
documented async recipe -- not a hand-rolled workaround.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from austial.orm import DataSource, PostgresDriver
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from src.db.entities import ALL_ENTITIES

try:
    # Mirrors `ConfigModule.for_root()`'s best-effort `.env` loading (see `austial-config`) --
    # `alembic` is invoked as its own CLI process, outside the app's DI graph, so it needs the
    # same `DATABASE_URL` loaded the same way the running app gets it.
    from dotenv import load_dotenv

    load_dotenv(".env", override=False)
except ImportError:  # pragma: no cover - python-dotenv ships transitively today
    pass

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_database_url = os.environ.get("DATABASE_URL")
if not _database_url:
    raise RuntimeError(
        "DATABASE_URL must be set (see backend/.env.example) for Alembic to run -- "
        "same env var AppModule's OrmModule.for_root_async() reads via ConfigService."
    )
config.set_main_option("sqlalchemy.url", _database_url)

# `DataSource(driver, entities)` construction is cheap/side-effect-free -- no connection opened,
# see `DataSource.__init__`'s docstring -- so building the `SchemaCatalog`/`target_metadata` here
# never touches the database, exactly what Alembic needs at module-import time.
_data_source = DataSource(PostgresDriver(_database_url), ALL_ENTITIES)
target_metadata = _data_source.get_metadata()


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql` etc -- emits SQL without a live DB connection."""
    context.configure(
        url=_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

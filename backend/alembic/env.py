import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.config import get_settings, normalize_db_url
from app.models import Base
from app.models.vistas import VIEW_NAMES

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Migraciones: conexión directa de Neon (sin pooler); si no existe, la de la app.
_settings = get_settings()
_db_url, _connect_args = normalize_db_url(_settings.database_url_direct or _settings.database_url)


# Índices de expresión: Alembic no sabe compararlos y los reportaría siempre como cambiados.
_INDICES_EXPRESION = {"ix_faqs_fts"}


def include_object(obj, name, type_, reflected, compare_to):
    # Las vistas se gestionan con SQL propio en las migraciones.
    if type_ == "table" and name in VIEW_NAMES:
        return False
    return not (type_ == "index" and name in _INDICES_EXPRESION)


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(_db_url, connect_args=_connect_args, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

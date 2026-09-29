"""Motor async de SQLAlchemy y sesiones."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings, normalize_db_url

_settings = get_settings()
_url, _connect_args = normalize_db_url(_settings.database_url)

engine = create_async_engine(
    _url,
    connect_args=_connect_args,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=300,  # Neon cierra conexiones inactivas
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session

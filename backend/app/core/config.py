"""Configuración de la aplicación, leída desde variables de entorno / `.env`."""

from functools import lru_cache
from typing import Annotated, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Cadenas de Neon tal como se copian del panel (postgresql://...?sslmode=require).
    database_url: str
    database_url_direct: str | None = None

    app_env: str = "development"
    app_tz: str = "America/La_Paz"
    app_name: str = "El Mexicano API"

    jwt_secret: str = "cambiar"
    jwt_expire_minutes: int = 480

    demo_telefono_e164: str = "59170000000"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # Cada cuántos segundos se liberan las reservas vencidas (0 = desactivado).
    job_expirar_reservas_segundos: int = 60

    # Seguridad
    cookie_secure: bool = False  # true en producción (HTTPS)
    rate_limit_enabled: bool = True
    docs_enabled: bool = True
    trust_proxy_headers: bool = False  # true detrás de un proxy que fija X-Forwarded-For

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


def normalize_db_url(raw: str) -> tuple[URL, dict[str, Any]]:
    """Convierte una URL de Postgres cualquiera en una URL asyncpg + connect_args.

    asyncpg no entiende `sslmode` ni `channel_binding` (parámetros libpq que trae Neon),
    así que se quitan de la URL y el modo SSL se pasa en `connect_args`.
    """
    url = make_url(raw).set(drivername="postgresql+asyncpg")
    query = dict(url.query)
    ssl_mode = query.pop("ssl", None) or query.pop("sslmode", None)
    query.pop("sslmode", None)
    query.pop("channel_binding", None)

    host = url.host or ""
    if ssl_mode is None and host.endswith("neon.tech"):
        ssl_mode = "require"

    connect_args: dict[str, Any] = {}
    if ssl_mode and ssl_mode != "disable":
        connect_args["ssl"] = ssl_mode
    if "-pooler" in host:
        # PgBouncer en modo transacción: sin caché de sentencias preparadas.
        connect_args["statement_cache_size"] = 0
        query["prepared_statement_cache_size"] = "0"
    return url.set(query=query), connect_args


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

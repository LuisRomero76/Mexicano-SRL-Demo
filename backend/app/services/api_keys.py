"""API keys de clientes de máquina (agente de voz). Se guarda solo el SHA-256 de la key.

SHA-256 basta porque la key es aleatoria de 256 bits (no es una contraseña elegida por una persona):
no se puede adivinar por fuerza bruta y la búsqueda por hash usa el índice único.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey
from app.utils.fechas import ahora

PREFIJO = "emk_"
SCOPE_LECTURA = "bot:read"
SCOPE_ESCRITURA = "bot:write"
KEY_AGENTE = "elevenlabs-agent"

_CACHE_SEGUNDOS = 60  # una key revocada deja de funcionar en como máximo este tiempo
_cache: dict[str, tuple[float, "KeyValida"]] = {}


@dataclass(frozen=True)
class KeyValida:
    id: int
    nombre: str
    scopes: frozenset[str]


def generar() -> str:
    return PREFIJO + secrets.token_urlsafe(32)


def hash_de(clave: str) -> str:
    return hashlib.sha256(clave.encode()).hexdigest()


async def crear_o_rotar(session: AsyncSession, nombre: str, scopes: list[str]) -> str:
    """Crea la key o, si ya existe con ese nombre, la reemplaza. Devuelve la key en claro (única vez)."""
    clave = generar()
    fila = await session.scalar(select(ApiKey).where(ApiKey.nombre == nombre))
    if fila is None:
        fila = ApiKey(nombre=nombre)
        session.add(fila)
    fila.prefijo = clave[:12]
    fila.key_hash = hash_de(clave)
    fila.scopes = scopes
    fila.activo = True
    fila.revocada_at = None
    await session.commit()
    olvidar_cache()
    return clave


async def asegurar(session: AsyncSession, nombre: str, scopes: list[str]) -> str | None:
    """Crea la key solo si no existe. Devuelve la key en claro si la creó; si ya existía, None."""
    if await session.scalar(select(ApiKey.id).where(ApiKey.nombre == nombre)):
        return None
    return await crear_o_rotar(session, nombre, scopes)


async def revocar(session: AsyncSession, nombre: str) -> bool:
    resultado = await session.execute(
        update(ApiKey).where(ApiKey.nombre == nombre, ApiKey.activo).values(activo=False, revocada_at=ahora())
    )
    await session.commit()
    olvidar_cache()
    return bool(resultado.rowcount)


async def autenticar(session: AsyncSession, clave: str) -> KeyValida | None:
    if not clave.startswith(PREFIJO) or len(clave) > 100:
        return None
    digest = hash_de(clave)
    en_cache = _cache.get(digest)
    if en_cache and time.monotonic() - en_cache[0] < _CACHE_SEGUNDOS:
        return en_cache[1]
    fila = await session.scalar(select(ApiKey).where(ApiKey.key_hash == digest, ApiKey.activo))
    if not fila:
        _cache.pop(digest, None)
        return None
    valida = KeyValida(id=fila.id, nombre=fila.nombre, scopes=frozenset(fila.scopes))
    if len(_cache) > 1000:
        _cache.clear()
    _cache[digest] = (time.monotonic(), valida)
    return valida


def olvidar_cache() -> None:
    _cache.clear()

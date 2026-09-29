"""CRUD genérico con auditoría, para catálogos sin reglas de negocio propias."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflicto, NoEncontrado
from app.models import Usuario
from app.services import auditoria


def _pk_nombre(modelo: Any) -> str:
    return modelo.__mapper__.primary_key[0].name


async def listar(
    session: AsyncSession, modelo: Any, *, filtros: dict[str, Any] | None = None, limit: int = 20, offset: int = 0
) -> tuple[int, list[Any]]:
    q = select(modelo)
    for campo, valor in (filtros or {}).items():
        if valor is not None:
            q = q.where(getattr(modelo, campo) == valor)
    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    orden = getattr(modelo, _pk_nombre(modelo))
    filas = (await session.scalars(q.order_by(orden).limit(limit).offset(offset))).all()
    return total or 0, list(filas)


async def obtener(session: AsyncSession, modelo: Any, pk: Any) -> Any:
    fila = await session.get(modelo, pk)
    if fila is None:
        raise NoEncontrado(f"No existe {modelo.__tablename__} con id {pk}.")
    return fila


async def _confirmar(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise Conflicto("Ya existe un registro con esos datos o una referencia no es válida.") from exc


async def crear(session: AsyncSession, modelo: Any, datos: dict[str, Any], usuario: Usuario | None) -> Any:
    fila = modelo(**datos)
    session.add(fila)
    await session.flush()
    auditoria.registrar(
        session,
        usuario,
        f"{modelo.__tablename__}.crear",
        modelo.__tablename__,
        getattr(fila, _pk_nombre(modelo)),
        datos,
    )
    await _confirmar(session)
    await session.refresh(fila)
    return fila


async def actualizar(
    session: AsyncSession, modelo: Any, pk: Any, cambios: dict[str, Any], usuario: Usuario | None
) -> Any:
    fila = await obtener(session, modelo, pk)
    antes = {k: getattr(fila, k) for k in cambios}
    for campo, valor in cambios.items():
        setattr(fila, campo, valor)
    auditoria.registrar(
        session,
        usuario,
        f"{modelo.__tablename__}.actualizar",
        modelo.__tablename__,
        pk,
        {"antes": antes, "despues": cambios},
    )
    await _confirmar(session)
    await session.refresh(fila)
    return fila

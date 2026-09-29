"""Registro de acciones sensibles del personal."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Auditoria, Usuario


def registrar(
    session: AsyncSession,
    usuario: Usuario | None,
    accion: str,
    tabla: str,
    registro_id: Any,
    cambios: dict[str, Any] | None = None,
) -> None:
    """Agrega la fila a la sesión; se confirma junto con la operación auditada."""
    session.add(
        Auditoria(
            usuario_id=usuario.id if usuario else None,
            accion=accion,
            tabla=tabla,
            registro_id=str(registro_id),
            cambios=_serializable(cambios) if cambios else None,
        )
    )


def _serializable(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {k: _serializable(v) for k, v in valor.items()}
    if isinstance(valor, list | tuple):
        return [_serializable(v) for v in valor]
    if isinstance(valor, str | int | float | bool) or valor is None:
        return valor
    if isinstance(valor, uuid.UUID):
        return str(valor)
    return str(valor)

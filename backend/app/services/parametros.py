"""Parámetros de negocio configurables (tabla `parametros_negocio`)."""

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ParametroNegocio

# Valores por defecto si la fila no existe (mismos que los seeds).
DEFAULTS: dict[str, Any] = {
    "reserva_expira_minutos": 15,
    "reembolso_porcentaje_cliente": 85,
    "reembolso_horas_minimas": 2,
    "reembolso_porcentaje_cancelacion_empresa": 100,
    "reembolso_dias_habiles_max": 7,
    "equipaje_bodega_kg": 20,
    "equipaje_mano_kg": 5,
    "embarazo_semanas_max": 30,
    "puerta_a_puerta_peso_min_kg": 1,
    "puerta_a_puerta_costo_bs": 20,
    "encomienda_peso_max_paquete_kg": 30,
    "venta_anticipacion_max_dias": 30,
    "venta_cierre_minutos_antes": 30,
    "boletos_max_por_venta": 6,
}


async def todos(session: AsyncSession) -> dict[str, Any]:
    filas = (await session.scalars(select(ParametroNegocio))).all()
    return DEFAULTS | {f.clave: f.valor for f in filas}


async def obtener(session: AsyncSession, clave: str) -> Any:
    fila = await session.get(ParametroNegocio, clave)
    if fila is not None:
        return fila.valor
    return DEFAULTS[clave]


async def obtener_int(session: AsyncSession, clave: str) -> int:
    return int(await obtener(session, clave))


async def obtener_decimal(session: AsyncSession, clave: str) -> Decimal:
    return Decimal(str(await obtener(session, clave)))

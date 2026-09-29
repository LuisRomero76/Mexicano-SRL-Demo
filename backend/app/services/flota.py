"""Flota: alta de buses con su mapa de asientos estándar."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import Conflicto
from app.models import Asiento, Bus, TipoAsiento, Usuario
from app.schemas.admin import BusIn
from app.services import auditoria

# Mapa estándar de la flota (doble piso, 2+1): planta baja Leito Cama 1–12, planta alta Suite Cama 13–48.
MAPA_ESTANDAR = [("LEITO_CAMA", "baja", 1, 4), ("SUITE_CAMA", "alta", 13, 12)]


def plantilla_asientos(bus_id: int, tipo_id: int, planta: str, primero: int, filas: int) -> list[dict]:
    """Filas de 2+1: columnas 1 y 2 (ventana, pasillo) y columna 3 (ventana individual)."""
    asientos, numero = [], primero
    for fila in range(1, filas + 1):
        for columna, posicion in ((1, "ventana"), (2, "pasillo"), (3, "ventana")):
            asientos.append(
                {
                    "bus_id": bus_id,
                    "numero": numero,
                    "tipo_asiento_id": tipo_id,
                    "planta": planta,
                    "fila": fila,
                    "columna": columna,
                    "posicion": posicion,
                    "habilitado": True,
                }
            )
            numero += 1
    return asientos


async def asientos_estandar(session: AsyncSession, bus_id: int) -> list[dict]:
    tipos = {t.codigo: t.id for t in (await session.scalars(select(TipoAsiento))).all()}
    filas: list[dict] = []
    for codigo, planta, primero, n_filas in MAPA_ESTANDAR:
        filas += plantilla_asientos(bus_id, tipos[codigo], planta, primero, n_filas)
    return filas


async def crear_bus(session: AsyncSession, datos: BusIn, usuario: Usuario) -> Bus:
    existe = await session.scalar(
        select(Bus.id).where((Bus.numero_interno == datos.numero_interno) | (Bus.placa == datos.placa))
    )
    if existe:
        raise Conflicto("Ya existe un bus con ese número interno o placa.")
    bus = Bus(**datos.model_dump(), pisos=2, capacidad_total=0, es_dato_demo=False)
    session.add(bus)
    await session.flush()
    asientos = await asientos_estandar(session, bus.id)
    session.add_all(Asiento(**a) for a in asientos)
    bus.capacidad_total = len(asientos)
    auditoria.registrar(session, usuario, "buses.crear", "buses", bus.id, datos.model_dump())
    await session.commit()
    return await session.scalar(select(Bus).where(Bus.id == bus.id).options(selectinload(Bus.asientos)))

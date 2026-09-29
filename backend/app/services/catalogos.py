"""Catálogos: empresa, ciudades, rutas, tipos de asiento, oficinas y feriados."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NoEncontrado, ReglaNegocio
from app.models import (
    Ciudad,
    Empresa,
    Feriado,
    Oficina,
    PlantillaHorario,
    Ruta,
    RutaParada,
    TarifaPasaje,
    TipoAsiento,
)
from app.models.vistas import v_oficinas_con_horario
from app.utils.fechas import hoy
from app.utils.texto import normalizar


async def empresa(session: AsyncSession) -> Empresa:
    fila = await session.get(Empresa, 1)
    if not fila:
        raise NoEncontrado("Los datos de la empresa no están cargados. Ejecuta los seeds.")
    return fila


async def listar_ciudades(
    session: AsyncSession, *, pasajeros: bool | None = None, carga: bool | None = None
) -> list[Ciudad]:
    q = select(Ciudad).where(Ciudad.activo).order_by(Ciudad.nombre)
    if pasajeros is not None:
        q = q.where(Ciudad.es_destino_pasajeros == pasajeros)
    if carga is not None:
        q = q.where(Ciudad.es_destino_carga == carga)
    return list((await session.scalars(q)).all())


async def resolver_ciudad(session: AsyncSession, texto: str) -> Ciudad:
    """Encuentra una ciudad por nombre, código o alias, sin importar tildes ni mayúsculas."""
    buscado = normalizar(texto)
    for ciudad in await listar_ciudades(session):
        candidatos = {normalizar(ciudad.nombre), ciudad.codigo.lower()}
        candidatos.update(normalizar(a) for a in ciudad.alias_busqueda or [])
        if buscado in candidatos:
            return ciudad
    raise NoEncontrado(
        f"No reconozco la ciudad «{texto}».",
        codigo="ciudad_no_encontrada",
        detalle={"ciudad": texto},
    )


async def listar_rutas(session: AsyncSession) -> list[Ruta]:
    q = (
        select(Ruta)
        .where(Ruta.activo)
        .options(
            selectinload(Ruta.origen),
            selectinload(Ruta.destino),
            selectinload(Ruta.paradas).selectinload(RutaParada.ciudad),
        )
        .order_by(Ruta.codigo)
    )
    return list((await session.scalars(q)).all())


async def ruta_entre(session: AsyncSession, origen: Ciudad, destino: Ciudad) -> Ruta:
    ruta = await session.scalar(
        select(Ruta)
        .where(Ruta.origen_ciudad_id == origen.id, Ruta.destino_ciudad_id == destino.id, Ruta.activo)
        .options(selectinload(Ruta.origen), selectinload(Ruta.destino))
    )
    if not ruta:
        destinos = [c.nombre for c in await listar_ciudades(session, pasajeros=True) if c.codigo != "SRE"]
        raise ReglaNegocio(
            f"No tenemos la ruta {origen.nombre} – {destino.nombre}. Nuestros destinos de pasajeros son "
            f"{', '.join(destinos[:-1])} y {destinos[-1]}, siempre desde o hacia Sucre.",
            codigo="ruta_no_disponible",
        )
    return ruta


async def listar_tipos_asiento(session: AsyncSession) -> list[TipoAsiento]:
    q = select(TipoAsiento).options(selectinload(TipoAsiento.comodidades)).order_by(TipoAsiento.orden)
    return list((await session.scalars(q)).all())


async def listar_oficinas(session: AsyncSession, ciudad: str | None = None) -> list[dict]:
    q = select(v_oficinas_con_horario).order_by(v_oficinas_con_horario.c.ciudad, v_oficinas_con_horario.c.codigo)
    if ciudad:
        c = await resolver_ciudad(session, ciudad)
        q = q.where(v_oficinas_con_horario.c.ciudad_id == c.id)
    return [dict(r) for r in (await session.execute(q)).mappings().all()]


async def oficina_por_codigo(session: AsyncSession, codigo: str) -> Oficina:
    oficina = await session.scalar(
        select(Oficina)
        .where(Oficina.codigo == codigo.upper())
        .options(selectinload(Oficina.horarios), selectinload(Oficina.ciudad))
    )
    if not oficina:
        raise NoEncontrado(f"No existe la oficina {codigo}.")
    return oficina


async def horario_texto_oficina(session: AsyncSession, oficina_id: int) -> str | None:
    return await session.scalar(
        select(v_oficinas_con_horario.c.horario_texto).where(v_oficinas_con_horario.c.oficina_id == oficina_id)
    )


async def feriados_para(session: AsyncSession, departamento: str, desde: date, hasta: date) -> set[date]:
    """Feriados nacionales y del departamento en el rango."""
    q = select(Feriado.fecha).where(
        Feriado.fecha.between(desde, hasta),
        or_(Feriado.departamento.is_(None), Feriado.departamento == departamento),
    )
    return set((await session.scalars(q)).all())


async def precio_desde_por_ruta(session: AsyncSession) -> dict[int, Decimal]:
    """Precio de venta más bajo vigente hoy por ruta (sin promociones puntuales)."""
    fecha = hoy()
    filas = (
        await session.execute(
            select(TarifaPasaje.ruta_id, func.min(TarifaPasaje.precio_bs))
            .where(
                TarifaPasaje.vigente_desde <= fecha,
                or_(TarifaPasaje.vigente_hasta.is_(None), TarifaPasaje.vigente_hasta >= fecha),
            )
            .group_by(TarifaPasaje.ruta_id)
        )
    ).all()
    return dict(filas)


async def listar_feriados(session: AsyncSession, desde: date, hasta: date) -> list[Feriado]:
    q = select(Feriado).where(Feriado.fecha.between(desde, hasta)).order_by(Feriado.fecha)
    return list((await session.scalars(q)).all())


async def horarios_por_ruta(session: AsyncSession) -> dict[int, list[str]]:
    """Horas de salida de las plantillas activas y vigentes hoy ("18:30")."""
    fecha = hoy()
    filas = (
        await session.execute(
            select(PlantillaHorario.ruta_id, PlantillaHorario.hora_salida)
            .where(
                PlantillaHorario.activo,
                PlantillaHorario.vigente_desde <= fecha,
                or_(PlantillaHorario.vigente_hasta.is_(None), PlantillaHorario.vigente_hasta >= fecha),
            )
            .order_by(PlantillaHorario.hora_salida)
        )
    ).all()
    resultado: dict[int, list[str]] = {}
    for ruta_id, hora in filas:
        resultado.setdefault(ruta_id, []).append(f"{hora:%H:%M}")
    return resultado

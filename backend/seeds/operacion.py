"""Salidas: generación desde plantillas, rotación de buses, tripulación y estados según la hora."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Bus, PrecioSalida, Salida, SalidaTripulacion, TipoAsiento, Usuario
from app.models.enums import EstadoSalida, RolTripulacion, RolUsuario
from app.services import salidas as salidas_srv
from app.utils.fechas import a_local, ahora, hoy, inicio_y_fin_del_dia
from seeds.data import demo

DIAS_ATRAS = 2
DIAS_ADELANTE = 30


async def seed_salidas(session: AsyncSession) -> None:
    desde, hasta = hoy() - timedelta(days=DIAS_ATRAS), hoy() + timedelta(days=DIAS_ADELANTE)
    await salidas_srv.generar_desde_plantillas(session, desde, hasta)

    buses = {b.numero_interno: b.id for b in (await session.scalars(select(Bus).order_by(Bus.numero_interno))).all()}
    conductores = (
        await session.scalars(select(Usuario).where(Usuario.rol == RolUsuario.conductor).order_by(Usuario.email))
    ).all()
    tipos = {t.codigo: t.id for t in (await session.scalars(select(TipoAsiento))).all()}
    todas = (
        await session.scalars(
            select(Salida)
            .where(Salida.fecha_hora_salida >= inicio_y_fin_del_dia(desde)[0])
            .options(selectinload(Salida.ruta))
            .order_by(Salida.fecha_hora_salida)
        )
    ).all()

    tripulacion, promos = [], []
    momento = ahora()
    for s in todas:
        local = a_local(s.fecha_hora_salida)
        corredor = next(c for c in s.ruta.codigo.split("-") if c != "SRE")
        ida = s.ruta.codigo.startswith("SRE-")
        slot = demo.HORAS_SALIDA.index(f"{local:%H:%M}") if f"{local:%H:%M}" in demo.HORAS_SALIDA else 0
        base = demo.CORREDORES[corredor] + slot * 2
        dias = (local.date() - demo.FECHA_REFERENCIA_ROTACION).days
        indice = base + (dias % 2 if ida else (dias + 1) % 2)

        if s.bus_id is None:
            s.bus_id = buses[f"M-{indice + 1:02d}"]
            s.anden = str(demo.CORREDORES[corredor] // 4 * 2 + slot + 1)
        tripulacion += [
            {"salida_id": s.id, "usuario_id": conductores[indice * 2].id, "rol": RolTripulacion.conductor},
            {"salida_id": s.id, "usuario_id": conductores[indice * 2 + 1].id, "rol": RolTripulacion.conductor_relevo},
        ]

        # Estados según la hora actual (no toca canceladas ni las ya cerradas).
        if s.estado in (EstadoSalida.programada, EstadoSalida.demorada, EstadoSalida.abordando):
            real_salida = s.fecha_hora_salida + timedelta(minutes=s.minutos_demora)
            real_llegada = s.fecha_hora_llegada_estimada + timedelta(minutes=s.minutos_demora)
            if real_llegada <= momento:
                s.estado, s.salida_real_at, s.llegada_real_at = EstadoSalida.llegada, real_salida, real_llegada
            elif real_salida <= momento:
                s.estado, s.salida_real_at = EstadoSalida.en_ruta, real_salida

        if corredor == "SCZ" and local.isoweekday() == 2:
            promos += [
                {"salida_id": s.id, "tipo_asiento_id": tipos[c], "precio_bs": Decimal(p)}
                for c, p in demo.PROMO_MARTES.items()
            ]

    await session.flush()
    if tripulacion:
        await session.execute(insert(SalidaTripulacion).values(tripulacion).on_conflict_do_nothing())
    if promos:
        await session.execute(insert(PrecioSalida).values(promos).on_conflict_do_nothing())
    await session.commit()

"""Reportes operativos simples."""

from datetime import date, timedelta
from typing import Any

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Boleto, Encomienda, Oficina, Pago, Reembolso, Ruta, Salida, VentaPasaje
from app.models.enums import EstadoBoleto, EstadoPago, EstadoReembolso, EstadoSalida, EstadoVenta
from app.models.vistas import v_salidas_disponibles
from app.utils.fechas import TZ, ahora, hoy, inicio_y_fin_del_dia

_TZ = TZ.key


async def ventas(session: AsyncSession, desde: date, hasta: date) -> dict[str, Any]:
    inicio, _ = inicio_y_fin_del_dia(desde)
    _, fin = inicio_y_fin_del_dia(hasta)
    dia = cast(func.timezone(_TZ, VentaPasaje.pagada_at), Date)
    pagadas = [VentaPasaje.pagada_at >= inicio, VentaPasaje.pagada_at < fin]
    estados = [EstadoVenta.pagada, EstadoVenta.reembolsada_parcial, EstadoVenta.reembolsada]
    por_dia = (
        await session.execute(
            select(dia.label("fecha"), func.count(), func.sum(VentaPasaje.total_bs))
            .where(*pagadas, VentaPasaje.estado.in_(estados))
            .group_by(dia)
            .order_by(dia)
        )
    ).all()
    por_canal = (
        await session.execute(
            select(VentaPasaje.canal, func.count(), func.sum(VentaPasaje.total_bs))
            .where(*pagadas, VentaPasaje.estado.in_(estados))
            .group_by(VentaPasaje.canal)
        )
    ).all()
    por_metodo = (
        await session.execute(
            select(Pago.metodo, func.count(), func.sum(Pago.monto_bs))
            .where(
                Pago.venta_pasaje_id.is_not(None),
                Pago.pagado_at >= inicio,
                Pago.pagado_at < fin,
                Pago.estado.in_([EstadoPago.aprobado, EstadoPago.reembolsado]),
            )
            .group_by(Pago.metodo)
        )
    ).all()
    total = sum((r[2] or 0) for r in por_dia)
    return {
        "desde": desde,
        "hasta": hasta,
        "total_bs": total,
        "ventas": sum(r[1] for r in por_dia),
        "por_dia": [{"fecha": r[0], "ventas": r[1], "total_bs": r[2]} for r in por_dia],
        "por_canal": [{"canal": r[0], "ventas": r[1], "total_bs": r[2]} for r in por_canal],
        "por_metodo_pago": [{"metodo": r[0], "pagos": r[1], "total_bs": r[2]} for r in por_metodo],
    }


async def ocupacion(session: AsyncSession, fecha: date) -> list[dict[str, Any]]:
    inicio, fin = inicio_y_fin_del_dia(fecha)
    v = v_salidas_disponibles.c
    filas = (
        await session.execute(
            select(
                v.salida_id,
                v.codigo,
                v.origen,
                v.destino,
                v.fecha_hora_salida,
                v.estado,
                v.minutos_demora,
                v.bus_numero_interno,
                func.sum(v.asientos_total).label("total"),
                func.sum(v.asientos_ocupados).label("ocupados"),
            )
            .where(v.fecha_hora_salida >= inicio, v.fecha_hora_salida < fin)
            .group_by(
                v.salida_id,
                v.codigo,
                v.origen,
                v.destino,
                v.fecha_hora_salida,
                v.estado,
                v.minutos_demora,
                v.bus_numero_interno,
            )
            .order_by(v.fecha_hora_salida, v.codigo)
        )
    ).all()
    return [
        {
            "salida_id": f.salida_id,
            "salida": f.codigo,
            "ruta": f"{f.origen} – {f.destino}",
            "origen": f.origen,
            "destino": f.destino,
            "fecha_hora_salida": f.fecha_hora_salida,
            "estado": f.estado,
            "minutos_demora": f.minutos_demora,
            "bus": f.bus_numero_interno,
            "asientos_total": f.total,
            "asientos_ocupados": f.ocupados,
            "ocupacion_pct": round(100 * f.ocupados / f.total, 1) if f.total else 0,
        }
        for f in filas
    ]


async def encomiendas(session: AsyncSession) -> dict[str, Any]:
    por_estado = (await session.execute(select(Encomienda.estado, func.count()).group_by(Encomienda.estado))).all()
    por_destino = (
        await session.execute(
            select(Oficina.nombre, func.count(), func.sum(Encomienda.precio_bs))
            .join(Oficina, Oficina.id == Encomienda.oficina_destino_id)
            .group_by(Oficina.nombre)
            .order_by(func.count().desc())
        )
    ).all()
    pendientes_cobro = await session.scalar(
        select(func.coalesce(func.sum(Encomienda.precio_bs), 0)).where(Encomienda.estado_pago == EstadoPago.pendiente)
    )
    return {
        "por_estado": {e: n for e, n in por_estado},
        "por_oficina_destino": [{"oficina": o, "encomiendas": n, "total_bs": t} for o, n, t in por_destino],
        "pendiente_de_cobro_bs": pendientes_cobro,
    }


async def resumen(session: AsyncSession) -> dict[str, Any]:
    """Datos del tablero del panel en una sola llamada."""
    fecha = hoy()
    semana = await ventas(session, fecha - timedelta(days=6), fecha)
    por_dia = {d["fecha"]: d for d in semana["por_dia"]}
    ventas_7_dias = []
    for i in range(6, -1, -1):
        dia = fecha - timedelta(days=i)
        fila = por_dia.get(dia)
        ventas_7_dias.append(
            {"fecha": dia, "ventas": fila["ventas"] if fila else 0, "total_bs": fila["total_bs"] if fila else 0}
        )
    hoy_ventas = await ventas(session, fecha, fecha)
    inicio, fin = inicio_y_fin_del_dia(fecha)
    boletos_hoy = await session.scalar(
        select(func.count(Boleto.id))
        .join(VentaPasaje, VentaPasaje.id == Boleto.venta_id)
        .where(
            VentaPasaje.pagada_at >= inicio,
            VentaPasaje.pagada_at < fin,
            Boleto.estado.in_([EstadoBoleto.emitido, EstadoBoleto.abordado, EstadoBoleto.no_show]),
        )
    )
    salidas_hoy = await ocupacion(session, fecha)
    total = sum(s["asientos_total"] or 0 for s in salidas_hoy)
    ocupados = sum(s["asientos_ocupados"] or 0 for s in salidas_hoy)
    reembolsos_pendientes = (
        await session.execute(
            select(func.count(Reembolso.id), func.coalesce(func.sum(Reembolso.monto_bs), 0)).where(
                Reembolso.estado.in_([EstadoReembolso.solicitado, EstadoReembolso.aprobado])
            )
        )
    ).one()
    momento = ahora()
    novedades = (
        await session.scalars(
            select(Salida)
            .where(
                Salida.estado.in_([EstadoSalida.demorada, EstadoSalida.cancelada]),
                Salida.fecha_hora_salida >= momento - timedelta(hours=6),
                Salida.fecha_hora_salida <= momento + timedelta(days=7),
            )
            .options(
                selectinload(Salida.ruta).selectinload(Ruta.origen),
                selectinload(Salida.ruta).selectinload(Ruta.destino),
            )
            .order_by(Salida.fecha_hora_salida)
            .limit(8)
        )
    ).all()
    carga = await encomiendas(session)
    return {
        "fecha": fecha,
        "ventas_hoy_bs": hoy_ventas["total_bs"],
        "ventas_hoy": hoy_ventas["ventas"],
        "boletos_hoy": boletos_hoy or 0,
        "por_canal_hoy": hoy_ventas["por_canal"],
        "ocupacion_hoy_pct": round(100 * ocupados / total, 1) if total else 0,
        "salidas_hoy": salidas_hoy,
        "ventas_7_dias": ventas_7_dias,
        "reembolsos_pendientes": reembolsos_pendientes[0],
        "reembolsos_pendientes_bs": reembolsos_pendientes[1],
        "encomiendas_por_estado": carga["por_estado"],
        "pendiente_de_cobro_bs": carga["pendiente_de_cobro_bs"],
        "novedades": [
            {
                "salida_id": s.id,
                "codigo": s.codigo,
                "ruta": f"{s.ruta.origen.nombre} – {s.ruta.destino.nombre}",
                "fecha_hora_salida": s.fecha_hora_salida,
                "estado": s.estado,
                "minutos_demora": s.minutos_demora,
                "motivo": s.motivo_estado,
            }
            for s in novedades
        ],
    }

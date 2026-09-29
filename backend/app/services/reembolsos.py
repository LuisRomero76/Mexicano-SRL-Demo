"""Reembolsos de pasajes.

Reglas reales (FAQ del sitio):
- Solicitud del cliente: 85 % del valor pagado, hasta 2 horas antes de la salida. Después, no hay devolución.
- Cancelación atribuible a la empresa: 100 %, inmediata.
- El reembolso puede demorar hasta 7 días hábiles.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import Conflicto, NoEncontrado, ReglaNegocio
from app.models import Boleto, Pago, Reembolso, Salida, Usuario, VentaPasaje
from app.models.enums import (
    BOLETO_ACTIVO,
    EstadoBoleto,
    EstadoPago,
    EstadoReembolso,
    EstadoSalida,
    EstadoVenta,
    OrigenReembolso,
)
from app.services import auditoria, catalogos, parametros, precios
from app.utils.fechas import ahora, hoy, sumar_dias_habiles


async def _pago_aprobado(session: AsyncSession, venta_id: uuid.UUID) -> Pago:
    pago = await session.scalar(
        select(Pago).where(
            Pago.venta_pasaje_id == venta_id, Pago.estado.in_([EstadoPago.aprobado, EstadoPago.reembolsado])
        )
    )
    if not pago:
        raise ReglaNegocio("La venta no tiene un pago aprobado.")
    return pago


async def _fecha_limite(session: AsyncSession) -> object:
    dias = await parametros.obtener_int(session, "reembolso_dias_habiles_max")
    inicio = hoy()
    feriados = await catalogos.feriados_para(session, "", inicio, inicio + timedelta(days=30))
    return sumar_dias_habiles(inicio, dias, feriados)


async def _actualizar_estado_venta(session: AsyncSession, venta_id: uuid.UUID) -> None:
    venta = await session.scalar(
        select(VentaPasaje).where(VentaPasaje.id == venta_id).options(selectinload(VentaPasaje.boletos))
    )
    reembolsados = [b for b in venta.boletos if b.estado == EstadoBoleto.reembolsado]
    if not reembolsados:
        return
    venta.estado = (
        EstadoVenta.reembolsada if len(reembolsados) == len(venta.boletos) else EstadoVenta.reembolsada_parcial
    )


async def solicitar(
    session: AsyncSession,
    numero_boleto: str,
    motivo: str,
    *,
    usuario: Usuario | None = None,
    documento: str | None = None,
) -> Reembolso:
    boleto = await session.scalar(
        select(Boleto)
        .where(Boleto.numero_boleto == numero_boleto.strip().upper())
        .options(selectinload(Boleto.salida), selectinload(Boleto.pasajero))
        .with_for_update(of=Boleto)
    )
    if not boleto or (documento and boleto.pasajero.numero_documento != documento.strip().upper()):
        raise NoEncontrado(f"No encontré el boleto {numero_boleto}.", codigo="boleto_no_encontrado")
    if boleto.estado != EstadoBoleto.emitido:
        raise ReglaNegocio(
            f"Solo se reembolsan pasajes pagados y no usados (el boleto está {boleto.estado}).",
            codigo="boleto_no_reembolsable",
        )
    salida: Salida = boleto.salida
    if salida.estado == EstadoSalida.cancelada:
        raise ReglaNegocio("La salida fue cancelada: el reembolso del 100 % ya se generó automáticamente.")
    horas_min = await parametros.obtener_int(session, "reembolso_horas_minimas")
    if salida.fecha_hora_salida - ahora() < timedelta(hours=horas_min):
        raise ReglaNegocio(
            f"No aplica devolución a menos de {horas_min} horas de la hora de salida del bus.",
            codigo="fuera_de_plazo",
        )
    pago = await _pago_aprobado(session, boleto.venta_id)
    porcentaje = await parametros.obtener_decimal(session, "reembolso_porcentaje_cliente")
    original = boleto.total_bs
    reembolso = Reembolso(
        pago_id=pago.id,
        boleto_id=boleto.id,
        origen=OrigenReembolso.solicitud_cliente,
        monto_original_bs=original,
        porcentaje_retencion=100 - porcentaje,
        monto_bs=precios.redondear(original * porcentaje / 100),
        motivo=motivo,
        estado=EstadoReembolso.solicitado,
        fecha_limite_pago=await _fecha_limite(session),
    )
    session.add(reembolso)
    boleto.estado = EstadoBoleto.reembolsado
    await session.flush()
    await _actualizar_estado_venta(session, boleto.venta_id)
    auditoria.registrar(session, usuario, "reembolso.solicitar", "boletos", boleto.id, {"monto": reembolso.monto_bs})
    await session.commit()
    return await obtener(session, reembolso.id)


async def por_cancelacion_de_salida(session: AsyncSession, salida: Salida, usuario: Usuario | None) -> int:
    """Cancela reservas sin pagar y reembolsa al 100 % los boletos emitidos. No hace commit."""
    porcentaje = await parametros.obtener_decimal(session, "reembolso_porcentaje_cancelacion_empresa")
    boletos = (
        await session.scalars(
            select(Boleto)
            .where(Boleto.salida_id == salida.id, Boleto.estado.in_(BOLETO_ACTIVO))
            .options(selectinload(Boleto.venta))
        )
    ).all()
    fecha_limite = await _fecha_limite(session)
    reembolsados = 0
    ventas: set[uuid.UUID] = set()
    for b in boletos:
        ventas.add(b.venta_id)
        if b.estado == EstadoBoleto.reservado:
            b.estado = EstadoBoleto.cancelado
            b.venta.estado = EstadoVenta.cancelada
            continue
        pago = await _pago_aprobado(session, b.venta_id)
        session.add(
            Reembolso(
                pago_id=pago.id,
                boleto_id=b.id,
                origen=OrigenReembolso.cancelacion_empresa,
                monto_original_bs=b.total_bs,
                porcentaje_retencion=100 - porcentaje,
                monto_bs=precios.redondear(b.total_bs * porcentaje / 100),
                motivo=f"Cancelación de la salida {salida.codigo}: {salida.motivo_estado or 'sin motivo'}",
                estado=EstadoReembolso.aprobado,
                fecha_limite_pago=fecha_limite,
                resuelto_at=ahora(),
                resuelto_por_usuario_id=usuario.id if usuario else None,
            )
        )
        b.estado = EstadoBoleto.reembolsado
        reembolsados += 1
    await session.flush()
    for venta_id in ventas:
        await _actualizar_estado_venta(session, venta_id)
    return reembolsados


async def obtener(session: AsyncSession, reembolso_id: uuid.UUID) -> Reembolso:
    reembolso = await session.scalar(
        select(Reembolso).where(Reembolso.id == reembolso_id).execution_options(populate_existing=True)
    )
    if not reembolso:
        raise NoEncontrado("No existe ese reembolso.")
    return reembolso


async def resolver(
    session: AsyncSession, reembolso_id: uuid.UUID, nuevo: EstadoReembolso, usuario: Usuario, nota: str | None = None
) -> Reembolso:
    reembolso = await obtener(session, reembolso_id)
    permitidas = {
        EstadoReembolso.solicitado: {EstadoReembolso.aprobado, EstadoReembolso.rechazado},
        EstadoReembolso.aprobado: {EstadoReembolso.pagado},
    }
    if nuevo not in permitidas.get(reembolso.estado, set()):
        raise ReglaNegocio(f"No se puede pasar un reembolso de «{reembolso.estado}» a «{nuevo}».")

    if nuevo == EstadoReembolso.rechazado and reembolso.boleto_id:
        boleto = await session.get(Boleto, reembolso.boleto_id)
        ocupado = await session.scalar(
            select(Boleto.id).where(
                Boleto.salida_id == boleto.salida_id,
                Boleto.numero_asiento == boleto.numero_asiento,
                Boleto.estado.in_(BOLETO_ACTIVO),
            )
        )
        if ocupado:
            raise Conflicto("El asiento ya fue vendido a otra persona; no se puede rechazar el reembolso.")
        boleto.estado = EstadoBoleto.emitido
        venta = await session.scalar(
            select(VentaPasaje).where(VentaPasaje.id == boleto.venta_id).options(selectinload(VentaPasaje.boletos))
        )
        venta.estado = (
            EstadoVenta.pagada
            if all(b.estado != EstadoBoleto.reembolsado for b in venta.boletos)
            else EstadoVenta.reembolsada_parcial
        )

    reembolso.estado = nuevo
    reembolso.resuelto_at = ahora()
    reembolso.resuelto_por_usuario_id = usuario.id

    if nuevo == EstadoReembolso.pagado:
        pago = await session.get(Pago, reembolso.pago_id)
        devuelto = await session.scalar(
            select(func.coalesce(func.sum(Reembolso.monto_original_bs), 0)).where(
                Reembolso.pago_id == pago.id,
                Reembolso.estado == EstadoReembolso.pagado,
                Reembolso.id != reembolso.id,
            )
        )
        if Decimal(devuelto) + reembolso.monto_original_bs >= pago.monto_bs:
            pago.estado = EstadoPago.reembolsado

    auditoria.registrar(
        session, usuario, f"reembolso.{nuevo}", "reembolsos", reembolso.id, {"nota": nota} if nota else None
    )
    await session.commit()
    return await obtener(session, reembolso.id)


async def listar(
    session: AsyncSession, *, estado: EstadoReembolso | None = None, limit: int = 20, offset: int = 0
) -> tuple[int, list[Reembolso]]:
    q = select(Reembolso)
    if estado:
        q = q.where(Reembolso.estado == estado)
    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    filas = (await session.scalars(q.order_by(Reembolso.solicitado_at.desc()).limit(limit).offset(offset))).all()
    return total or 0, list(filas)


async def con_detalle(session: AsyncSession, filas: list[Reembolso]) -> list[dict]:
    """Agrega boleto, pasajero, reserva y salida a cada reembolso (para listados y respuestas)."""
    ids = [r.boleto_id for r in filas if r.boleto_id]
    boletos = {}
    if ids:
        boletos = {
            b.id: b
            for b in (
                await session.scalars(
                    select(Boleto)
                    .where(Boleto.id.in_(ids))
                    .options(selectinload(Boleto.pasajero), selectinload(Boleto.venta), selectinload(Boleto.salida))
                )
            ).all()
        }
    salida = []
    for r in filas:
        b = boletos.get(r.boleto_id)
        salida.append(
            {
                "id": r.id,
                "origen": r.origen,
                "estado": r.estado,
                "monto_original_bs": r.monto_original_bs,
                "porcentaje_retencion": r.porcentaje_retencion,
                "monto_bs": r.monto_bs,
                "motivo": r.motivo,
                "solicitado_at": r.solicitado_at,
                "fecha_limite_pago": r.fecha_limite_pago,
                "resuelto_at": r.resuelto_at,
                "numero_boleto": b.numero_boleto if b else None,
                "pasajero": b.pasajero.nombre_completo if b else None,
                "codigo_reserva": b.venta.codigo_reserva if b else None,
                "salida": b.salida.codigo if b else None,
            }
        )
    return salida

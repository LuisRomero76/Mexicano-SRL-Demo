"""Reservas y venta de pasajes: crear, pagar (simulado), cancelar, expirar, abordar y equipaje."""

import secrets
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import Conflicto, NoEncontrado, ReglaNegocio
from app.models import Asiento, Boleto, Cliente, Equipaje, Factura, Pago, Ruta, Salida, Usuario, VentaPasaje
from app.models.enums import (
    CanalVenta,
    EstadoBoleto,
    EstadoPago,
    EstadoSalida,
    EstadoVenta,
    MetodoPago,
    TipoEquipaje,
    TipoPasajero,
)
from app.schemas.ventas import EquipajeIn, PagoIn, PasajeroIn, PersonaIn, ReservaIn
from app.services import auditoria, parametros, precios, salidas
from app.utils.codigos import formato_numero_boleto, generar_codigo_reserva, normalizar_codigo_reserva
from app.utils.fechas import a_local, ahora, edad_en, fecha_legible

METODOS_ONLINE = {MetodoPago.qr, MetodoPago.tarjeta_debito, MetodoPago.tarjeta_credito, MetodoPago.tigo_money}
TARJETA_RECHAZADA = "0002"


# --- Clientes ----------------------------------------------------------------------------------


async def upsert_cliente(session: AsyncSession, datos: PersonaIn) -> Cliente:
    """Busca al cliente por documento; si existe, actualiza sus datos de contacto."""
    cliente = await session.scalar(
        select(Cliente).where(
            Cliente.tipo_documento == datos.tipo_documento,
            Cliente.numero_documento == datos.numero_documento,
            Cliente.complemento.is_not_distinct_from(datos.complemento),
        )
    )
    if cliente is None:
        cliente = Cliente(
            tipo_documento=datos.tipo_documento,
            numero_documento=datos.numero_documento,
            complemento=datos.complemento,
            es_dato_demo=False,
        )
        session.add(cliente)
    cliente.nombres = datos.nombres
    cliente.apellidos = datos.apellidos
    if datos.extension:
        cliente.extension = datos.extension
    for campo in ("fecha_nacimiento", "telefono", "email", "nit_facturacion", "razon_social_facturacion"):
        valor = getattr(datos, campo, None)
        if valor:
            setattr(cliente, "telefono_e164" if campo == "telefono" else campo, valor)
    await session.flush()
    return cliente


# --- Crear reserva -----------------------------------------------------------------------------


async def _siguiente_numero_boleto(session: AsyncSession) -> str:
    return formato_numero_boleto(await session.scalar(text("SELECT nextval('seq_numero_boleto')")))


async def _codigo_reserva_libre(session: AsyncSession) -> str:
    while True:
        codigo = generar_codigo_reserva()
        if not await session.scalar(select(VentaPasaje.id).where(VentaPasaje.codigo_reserva == codigo)):
            return codigo


async def _validar_pasajero(session: AsyncSession, p: PasajeroIn, politica, canal: CanalVenta, salida: Salida) -> None:
    nombre = f"{p.nombres} {p.apellidos}"
    if politica is None:
        raise ReglaNegocio(f"Tipo de pasajero no habilitado: {p.tipo_pasajero}.")
    if politica.solo_boleteria and canal != CanalVenta.boleteria:
        raise ReglaNegocio(
            f"La tarifa «{politica.nombre}» de {nombre} solo se vende en boleterías"
            + (f", presentando: {politica.requisito}." if politica.requisito else "."),
            codigo="tarifa_solo_boleteria",
        )
    fecha_viaje = a_local(salida.fecha_hora_salida).date()
    edad = edad_en(p.fecha_nacimiento, fecha_viaje) if p.fecha_nacimiento else None
    tiene_rango = politica.edad_min is not None or politica.edad_max is not None
    if tiene_rango and p.tipo_pasajero != TipoPasajero.adulto:
        if edad is None:
            raise ReglaNegocio(f"Indica la fecha de nacimiento de {nombre}.")
        if (politica.edad_min is not None and edad < politica.edad_min) or (
            politica.edad_max is not None and edad > politica.edad_max
        ):
            raise ReglaNegocio(f"La edad de {nombre} ({edad} años) no corresponde a la tarifa «{politica.nombre}».")
    if p.tipo_pasajero == TipoPasajero.adulto and edad is not None and edad < 12:
        raise ReglaNegocio(
            f"{nombre} tiene {edad} años: los menores viajan con tarifa de menor, que se compra en boletería "
            "con el Permiso de Viaje.",
            codigo="menor_como_adulto",
        )
    if p.tipo_pasajero == TipoPasajero.menor and not p.permiso_viaje_numero:
        raise ReglaNegocio(
            f"{nombre} necesita el Permiso de Viaje de la Defensoría de la Niñez y Adolescencia.",
            codigo="falta_permiso_viaje",
        )
    if p.tipo_pasajero == TipoPasajero.embarazada:
        maximo = await parametros.obtener_int(session, "embarazo_semanas_max")
        if p.semanas_gestacion is None:
            raise ReglaNegocio(f"Indica las semanas de gestación de {nombre}.")
        if p.semanas_gestacion > maximo:
            raise ReglaNegocio(
                f"Las embarazadas pueden viajar hasta las {maximo} semanas de gestación.",
                codigo="gestacion_excedida",
            )
    elif p.semanas_gestacion is not None:
        raise ReglaNegocio("Las semanas de gestación solo aplican al tipo de pasajero «embarazada».")


async def crear_reserva(
    session: AsyncSession,
    datos: ReservaIn,
    *,
    canal: CanalVenta = CanalVenta.web,
    usuario: Usuario | None = None,
) -> VentaPasaje:
    maximo = await parametros.obtener_int(session, "boletos_max_por_venta")
    if len(datos.pasajeros) > maximo:
        raise ReglaNegocio(f"Se pueden comprar como máximo {maximo} boletos por reserva.")

    # Bloquea la salida: serializa las ventas concurrentes sobre el mismo viaje.
    salida = await salidas.obtener(session, datos.salida_id, bloquear=True)
    cierre, max_dias = await salidas.ventana_de_venta(session)
    if canal == CanalVenta.boleteria:
        cierre = 0  # en ventanilla se vende hasta la hora de salida
    if not salidas.es_vendible(salida.estado, salida.fecha_hora_salida, cierre, max_dias):
        raise ReglaNegocio(
            "Esta salida ya no está disponible para la venta.",
            codigo="salida_no_vendible",
            detalle={"estado": salida.estado},
        )
    if salida.bus_id is None:
        raise ReglaNegocio("Esta salida todavía no tiene bus asignado.", codigo="salida_sin_bus")

    asientos = {
        a.numero: a for a in (await session.scalars(select(Asiento).where(Asiento.bus_id == salida.bus_id))).all()
    }
    ocupados = await salidas.numeros_ocupados(session, salida.id)
    politicas = await precios.politicas(session)

    for p in datos.pasajeros:
        asiento = asientos.get(p.numero_asiento)
        if not asiento or not asiento.habilitado:
            raise ReglaNegocio(f"El asiento {p.numero_asiento} no existe en este bus.", codigo="asiento_invalido")
        if p.numero_asiento in ocupados:
            raise Conflicto(f"El asiento {p.numero_asiento} ya está ocupado.", codigo="asiento_ocupado")
        await _validar_pasajero(session, p, politicas.get(p.tipo_pasajero), canal, salida)

    comprador = await upsert_cliente(session, datos.comprador)
    venta = VentaPasaje(
        codigo_reserva=await _codigo_reserva_libre(session),
        comprador_cliente_id=comprador.id,
        canal=canal,
        estado=EstadoVenta.pendiente_pago,
        expira_at=ahora() + timedelta(minutes=await parametros.obtener_int(session, "reserva_expira_minutos")),
        vendida_por_usuario_id=usuario.id if usuario else None,
        oficina_venta_id=usuario.oficina_id if usuario else None,
    )
    session.add(venta)
    await session.flush()

    subtotal = descuento = Decimal("0.00")
    bases: dict[int, precios.PrecioBase] = {}
    for p in datos.pasajeros:
        asiento = asientos[p.numero_asiento]
        if asiento.tipo_asiento_id not in bases:
            bases[asiento.tipo_asiento_id] = await precios.precio_base(session, salida, asiento.tipo_asiento_id)
        precio = precios.aplicar_politica(bases[asiento.tipo_asiento_id], politicas[p.tipo_pasajero])
        pasajero = await upsert_cliente(session, p)
        session.add(
            Boleto(
                numero_boleto=await _siguiente_numero_boleto(session),
                venta_id=venta.id,
                salida_id=salida.id,
                asiento_id=asiento.id,
                numero_asiento=asiento.numero,
                tipo_asiento_id=asiento.tipo_asiento_id,
                pasajero_cliente_id=pasajero.id,
                tipo_pasajero=p.tipo_pasajero,
                precio_bs=precio.precio_bs,
                descuento_bs=precio.descuento_bs,
                estado=EstadoBoleto.reservado,
                viaja_con_perro_guia=p.viaja_con_perro_guia,
                semanas_gestacion=p.semanas_gestacion,
                permiso_viaje_numero=p.permiso_viaje_numero,
            )
        )
        subtotal += precio.precio_bs
        descuento += precio.descuento_bs

    venta.subtotal_bs = subtotal
    venta.descuento_bs = descuento
    venta.total_bs = subtotal - descuento
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if "uq_boletos_asiento_activo" in str(exc.orig):
            raise Conflicto("Uno de los asientos acaba de ser tomado. Elige otro.", codigo="asiento_ocupado") from exc
        raise
    return await obtener(session, venta.codigo_reserva)


# --- Consultar ---------------------------------------------------------------------------------


async def obtener(session: AsyncSession, codigo: str, *, documento: str | None = None) -> VentaPasaje:
    codigo = normalizar_codigo_reserva(codigo)
    salida_de_boleto = selectinload(VentaPasaje.boletos).selectinload(Boleto.salida)
    venta = await session.scalar(
        select(VentaPasaje)
        .where(VentaPasaje.codigo_reserva == codigo)
        .options(
            selectinload(VentaPasaje.comprador),
            selectinload(VentaPasaje.boletos).selectinload(Boleto.pasajero),
            selectinload(VentaPasaje.boletos).selectinload(Boleto.tipo_asiento),
            salida_de_boleto.selectinload(Salida.ruta).selectinload(Ruta.origen),
            salida_de_boleto.selectinload(Salida.ruta).selectinload(Ruta.destino),
            salida_de_boleto.selectinload(Salida.oficina_salida),
        )
        .execution_options(populate_existing=True)
    )
    no_encontrada = NoEncontrado(
        f"No encontré la reserva {codigo}. Revisa el código de 6 caracteres.", codigo="reserva_no_encontrada"
    )
    if not venta:
        raise no_encontrada
    if documento is not None:
        doc = documento.strip().upper()
        documentos = {venta.comprador.numero_documento} | {b.pasajero.numero_documento for b in venta.boletos}
        if doc not in documentos:
            raise no_encontrada  # no revela si el código existe
    if venta.estado == EstadoVenta.pendiente_pago and venta.expira_at and venta.expira_at <= ahora():
        _expirar(venta)
        await session.commit()
    return venta


def _expirar(venta: VentaPasaje) -> None:
    venta.estado = EstadoVenta.expirada
    for b in venta.boletos:
        if b.estado == EstadoBoleto.reservado:
            b.estado = EstadoBoleto.cancelado


async def pago_y_factura(session: AsyncSession, venta: VentaPasaje) -> tuple[Pago | None, Factura | None]:
    pago = await session.scalar(
        select(Pago)
        .where(Pago.venta_pasaje_id == venta.id)
        .options(selectinload(Pago.factura))
        .order_by(Pago.created_at.desc())
        .limit(1)
    )
    return pago, pago.factura if pago else None


def mensaje_reserva(venta: VentaPasaje) -> str:
    salida = venta.boletos[0].salida if venta.boletos else None
    viaje = (
        f"{salida.ruta.origen.nombre} – {salida.ruta.destino.nombre} del {fecha_legible(salida.fecha_hora_salida)}"
        if salida
        else ""
    )
    n = len(venta.boletos)
    match venta.estado:
        case EstadoVenta.pendiente_pago:
            return (
                f"Reserva {venta.codigo_reserva}: {n} asiento(s) para {viaje}. Total Bs {venta.total_bs:.2f}. "
                f"Paga antes de las {a_local(venta.expira_at):%H:%M} o se liberan los asientos."
            )
        case EstadoVenta.pagada:
            demora = (
                f" La salida tiene una demora de {salida.minutos_demora} minutos."
                if salida and salida.estado == EstadoSalida.demorada
                else ""
            )
            return f"Reserva {venta.codigo_reserva} pagada: {n} boleto(s) para {viaje}.{demora}"
        case EstadoVenta.expirada:
            return f"La reserva {venta.codigo_reserva} expiró sin pago y los asientos se liberaron."
        case EstadoVenta.cancelada:
            return f"La reserva {venta.codigo_reserva} fue cancelada."
        case _:
            return f"La reserva {venta.codigo_reserva} tiene boletos reembolsados ({venta.estado})."


async def a_respuesta(session: AsyncSession, venta: VentaPasaje) -> dict[str, Any]:
    pago, factura = await pago_y_factura(session, venta)
    s = venta.boletos[0].salida
    return {
        "codigo_reserva": venta.codigo_reserva,
        "estado": venta.estado,
        "canal": venta.canal,
        "comprador": venta.comprador.nombre_completo,
        "subtotal_bs": venta.subtotal_bs,
        "descuento_bs": venta.descuento_bs,
        "total_bs": venta.total_bs,
        "expira_at": venta.expira_at if venta.estado == EstadoVenta.pendiente_pago else None,
        "pagada_at": venta.pagada_at,
        "salida": {
            "id": s.id,
            "codigo": s.codigo,
            "origen": s.ruta.origen.nombre,
            "destino": s.ruta.destino.nombre,
            "fecha_hora_salida": s.fecha_hora_salida,
            "fecha_hora_llegada_estimada": s.fecha_hora_llegada_estimada,
            "estado": s.estado,
            "minutos_demora": s.minutos_demora,
            "anden": s.anden,
            "oficina_salida": s.oficina_salida.nombre if s.oficina_salida else None,
            "direccion_salida": s.oficina_salida.direccion if s.oficina_salida else None,
        },
        "boletos": [
            {
                "numero_boleto": b.numero_boleto,
                "numero_asiento": b.numero_asiento,
                "clase": b.tipo_asiento.nombre,
                "pasajero": b.pasajero.nombre_completo,
                "documento": f"{b.pasajero.tipo_documento.upper()} {b.pasajero.numero_documento}",
                "tipo_pasajero": b.tipo_pasajero,
                "precio_bs": b.precio_bs,
                "descuento_bs": b.descuento_bs,
                "total_bs": b.total_bs,
                "estado": b.estado,
                "codigo_qr": b.codigo_qr,
                "viaja_con_perro_guia": b.viaja_con_perro_guia,
            }
            for b in venta.boletos
        ],
        "pago": pago,
        "factura": factura,
        "mensaje": mensaje_reserva(venta),
    }


# --- Pagar (simulado) --------------------------------------------------------------------------


def _codigo_qr(boleto: Boleto) -> str:
    return f"MX|{boleto.numero_boleto}|{secrets.token_hex(4).upper()}"


async def pagar(session: AsyncSession, codigo: str, datos: PagoIn, *, usuario: Usuario | None = None) -> VentaPasaje:
    venta = await obtener(session, codigo)
    if venta.estado != EstadoVenta.pendiente_pago:
        raise ReglaNegocio(mensaje_reserva(venta), codigo="reserva_no_pagable")
    if usuario is None and datos.metodo not in METODOS_ONLINE:
        raise ReglaNegocio("En línea se puede pagar con QR, tarjeta de débito o crédito y Tigo Money.")
    if datos.metodo == MetodoPago.credito_corporativo:
        raise ReglaNegocio("El crédito corporativo solo aplica a carga y encomiendas.")
    salida = venta.boletos[0].salida
    if salida.estado not in salidas.ESTADOS_VENDIBLES or salida.fecha_hora_salida <= ahora():
        raise ReglaNegocio("La salida ya partió o fue cancelada; no se puede pagar la reserva.")

    ultimos4 = datos.numero_tarjeta[-4:] if datos.numero_tarjeta else None
    if usuario:
        proveedor = "boleteria"
    elif datos.metodo == MetodoPago.tigo_money:
        proveedor = "tigo_money"
    else:
        proveedor = "pagoseguro"
    pago = Pago(
        venta_pasaje_id=venta.id,
        metodo=datos.metodo,
        monto_bs=venta.total_bs,
        proveedor=proveedor,
        transaccion_externa_id=f"SIM-{secrets.token_hex(6).upper()}",
        ultimos4_tarjeta=ultimos4,
        qr_payload=(
            f"000201|BOB|{venta.total_bs:.2f}|ELMEXICANO|{venta.codigo_reserva}"
            if datos.metodo == MetodoPago.qr
            else None
        ),
        cobrado_por_usuario_id=usuario.id if usuario else None,
    )
    session.add(pago)

    if ultimos4 == TARJETA_RECHAZADA:
        pago.estado = EstadoPago.rechazado
        await session.commit()
        raise ReglaNegocio(
            "El banco rechazó la tarjeta. Prueba con otro medio de pago; la reserva sigue vigente.",
            codigo="pago_rechazado",
        )

    momento = ahora()
    pago.estado = EstadoPago.aprobado
    pago.pagado_at = momento
    venta.estado = EstadoVenta.pagada
    venta.pagada_at = momento
    venta.expira_at = None
    for b in venta.boletos:
        b.estado = EstadoBoleto.emitido
        b.codigo_qr = _codigo_qr(b)
    await session.flush()

    comprador = venta.comprador
    session.add(
        Factura(
            pago_id=pago.id,
            numero_factura=await session.scalar(text("SELECT nextval('seq_numero_factura')")),
            cuf=secrets.token_hex(20).upper(),
            nit_ci_cliente=datos.nit_facturacion or comprador.nit_facturacion or comprador.numero_documento,
            razon_social_cliente=(
                datos.razon_social_facturacion or comprador.razon_social_facturacion or comprador.apellidos.upper()
            ),
            monto_total_bs=venta.total_bs,
        )
    )
    if usuario:
        auditoria.registrar(
            session,
            usuario,
            "venta.cobrar",
            "ventas_pasaje",
            venta.id,
            {"metodo": datos.metodo, "monto": venta.total_bs},
        )
    await session.commit()
    return await obtener(session, venta.codigo_reserva)


async def cancelar(session: AsyncSession, codigo: str, *, documento: str | None = None) -> VentaPasaje:
    venta = await obtener(session, codigo, documento=documento)
    if venta.estado != EstadoVenta.pendiente_pago:
        raise ReglaNegocio(
            "Solo se pueden cancelar reservas pendientes de pago. Para un boleto pagado solicita el reembolso.",
            codigo="reserva_no_cancelable",
        )
    venta.estado = EstadoVenta.cancelada
    for b in venta.boletos:
        b.estado = EstadoBoleto.cancelado
    await session.commit()
    return await obtener(session, venta.codigo_reserva)


async def expirar_vencidas(session: AsyncSession) -> int:
    """Libera los asientos de las reservas vencidas. La usa la tarea periódica."""
    ventas = (
        await session.scalars(
            select(VentaPasaje)
            .where(VentaPasaje.estado == EstadoVenta.pendiente_pago, VentaPasaje.expira_at <= ahora())
            .options(selectinload(VentaPasaje.boletos))
            .with_for_update(skip_locked=True, of=VentaPasaje)
        )
    ).all()
    for v in ventas:
        _expirar(v)
    await session.commit()
    return len(ventas)


# --- Boletos: abordaje y equipaje --------------------------------------------------------------


async def boleto_por_codigo(session: AsyncSession, codigo: str) -> Boleto:
    codigo = codigo.strip().upper()
    es_qr = codigo.startswith("MX|")
    q = select(Boleto).options(
        selectinload(Boleto.pasajero),
        selectinload(Boleto.salida).selectinload(Salida.ruta),
        selectinload(Boleto.tipo_asiento),
    )
    q = q.where(Boleto.codigo_qr == codigo) if es_qr else q.where(Boleto.numero_boleto == codigo)
    boleto = await session.scalar(q)
    if not boleto:
        raise NoEncontrado(
            "El código QR no corresponde a ningún boleto." if es_qr else f"No existe el boleto {codigo}.",
            codigo="boleto_no_encontrado",
        )
    return boleto


async def abordar(session: AsyncSession, codigo: str, usuario: Usuario) -> Boleto:
    boleto = await boleto_por_codigo(session, codigo)
    if boleto.estado == EstadoBoleto.abordado:
        raise Conflicto(f"El boleto {boleto.numero_boleto} ya fue usado para abordar.", codigo="ya_abordado")
    if boleto.estado != EstadoBoleto.emitido:
        raise ReglaNegocio(f"El boleto {boleto.numero_boleto} no es válido para abordar ({boleto.estado}).")
    if boleto.salida.estado not in salidas.ESTADOS_VENDIBLES:
        raise ReglaNegocio(f"La salida {boleto.salida.codigo} está en estado {boleto.salida.estado}.")
    if boleto.salida.fecha_hora_salida - ahora() > timedelta(hours=3):
        raise ReglaNegocio("El abordaje abre 3 horas antes de la salida.")
    boleto.estado = EstadoBoleto.abordado
    boleto.abordado_at = ahora()
    auditoria.registrar(session, usuario, "boleto.abordar", "boletos", boleto.id)
    await session.commit()
    return boleto


async def registrar_equipaje(
    session: AsyncSession, numero_boleto: str, datos: EquipajeIn, usuario: Usuario
) -> Equipaje:
    boleto = await boleto_por_codigo(session, numero_boleto)
    if boleto.estado not in (EstadoBoleto.emitido, EstadoBoleto.abordado):
        raise ReglaNegocio("Solo se registra equipaje de boletos emitidos.")
    clave = "equipaje_bodega_kg" if datos.tipo == TipoEquipaje.bodega else "equipaje_mano_kg"
    permitido = await parametros.obtener_decimal(session, clave)
    ya_registrado = await session.scalar(
        select(func.coalesce(func.sum(Equipaje.peso_kg), 0)).where(
            Equipaje.boleto_id == boleto.id, Equipaje.tipo == datos.tipo
        )
    )
    peso = Decimal(str(datos.peso_kg))
    restante = max(Decimal(0), permitido - Decimal(ya_registrado))
    exceso = max(Decimal(0), peso - restante)
    cantidad = await session.scalar(select(func.count()).where(Equipaje.boleto_id == boleto.id))
    equipaje = Equipaje(
        boleto_id=boleto.id,
        etiqueta=f"{boleto.numero_boleto}-{cantidad + 1}",
        tipo=datos.tipo,
        piezas=datos.piezas,
        peso_kg=peso,
        peso_permitido_kg=permitido,
        exceso_kg=exceso,
        cargo_exceso_bs=precios.redondear(exceso * boleto.salida.ruta.cargo_exceso_equipaje_kg_bs),
        descripcion=datos.descripcion,
    )
    session.add(equipaje)
    auditoria.registrar(session, usuario, "boleto.equipaje", "boletos", boleto.id, {"peso": peso, "exceso": exceso})
    await session.commit()
    return equipaje


async def listar_ventas(
    session: AsyncSession,
    *,
    estado: EstadoVenta | None = None,
    canal: CanalVenta | None = None,
    documento: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, list[VentaPasaje]]:
    q = select(VentaPasaje)
    if estado:
        q = q.where(VentaPasaje.estado == estado)
    if canal:
        q = q.where(VentaPasaje.canal == canal)
    if documento:
        q = q.where(VentaPasaje.comprador.has(Cliente.numero_documento == documento.strip().upper()))
    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    filas = (
        await session.scalars(
            q.options(selectinload(VentaPasaje.comprador))
            .order_by(VentaPasaje.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return total or 0, list(filas)

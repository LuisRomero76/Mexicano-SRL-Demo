"""Carga y encomiendas: cotización, registro, rastreo, despacho, eventos, cobro y entrega."""

import hmac
import secrets
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import Conflicto, NoEncontrado, ReglaNegocio
from app.models import (
    Ciudad,
    Cliente,
    CuentaCorporativa,
    Encomienda,
    EncomiendaEvento,
    Oficina,
    Pago,
    Ruta,
    RutaParada,
    Salida,
    TarifaCarga,
    Usuario,
    VehiculoCarga,
)
from app.models.enums import (
    EstadoEncomienda,
    EstadoPago,
    MetodoPago,
    ModalidadEntrega,
    PagoEn,
    TipoEnvio,
    TipoOficina,
)
from app.models.vistas import v_encomienda_rastreo
from app.schemas.carga import EncomiendaIn, EntregaIn, EventoIn
from app.services import auditoria, catalogos, parametros, precios, reservas, salidas
from app.utils.codigos import generar_pin
from app.utils.fechas import ahora, fecha_legible, hoy

E = EstadoEncomienda

TRANSICIONES: dict[EstadoEncomienda, set[EstadoEncomienda]] = {
    E.registrada: {E.recibida_en_origen, E.cancelada},
    E.recibida_en_origen: {E.en_transito, E.cancelada},
    E.en_transito: {E.llegada_a_destino},
    E.llegada_a_destino: {E.lista_para_retiro, E.en_reparto},
    E.lista_para_retiro: {E.entregada, E.en_reparto, E.devuelta},
    E.en_reparto: {E.entregada, E.intento_fallido},
    E.intento_fallido: {E.en_reparto, E.lista_para_retiro, E.devuelta},
    E.entregada: set(),
    E.devuelta: set(),
    E.cancelada: set(),
}

ESTADOS_FINALES = {E.entregada, E.devuelta, E.cancelada}
ESTADOS_EN_ORIGEN = {E.registrada, E.recibida_en_origen, E.cancelada}

ESTADO_LEGIBLE = {
    E.registrada: "Registrada",
    E.recibida_en_origen: "Recibida en la oficina de origen",
    E.en_transito: "En tránsito",
    E.llegada_a_destino: "Llegó a la ciudad de destino",
    E.lista_para_retiro: "Lista para recoger",
    E.en_reparto: "En reparto a domicilio",
    E.entregada: "Entregada",
    E.intento_fallido: "Intento de entrega fallido",
    E.devuelta: "Devuelta al remitente",
    E.cancelada: "Cancelada",
}


# --- Cotización --------------------------------------------------------------------------------


async def _tarifa(session: AsyncSession, origen: Ciudad, destino: Ciudad, tipo: TipoEnvio) -> TarifaCarga:
    fecha = hoy()
    tarifa = await session.scalar(
        select(TarifaCarga)
        .where(
            TarifaCarga.origen_ciudad_id == origen.id,
            TarifaCarga.destino_ciudad_id == destino.id,
            TarifaCarga.tipo_envio == tipo,
            TarifaCarga.vigente_desde <= fecha,
            or_(TarifaCarga.vigente_hasta.is_(None), TarifaCarga.vigente_hasta >= fecha),
        )
        .order_by(TarifaCarga.vigente_desde.desc())
        .limit(1)
    )
    if not tarifa:
        raise NoEncontrado(f"No hay tarifa de {tipo} de {origen.nombre} a {destino.nombre}.", codigo="sin_tarifa_carga")
    return tarifa


async def _cotizar(
    session: AsyncSession,
    origen: Ciudad,
    destino: Ciudad,
    peso_kg: Decimal,
    tipo: TipoEnvio | None,
    puerta_a_puerta: bool,
) -> dict[str, Any]:
    ciudades_carga = [c.nombre for c in await catalogos.listar_ciudades(session, carga=True)]
    for ciudad in (origen, destino):
        if not ciudad.es_destino_carga:
            raise ReglaNegocio(
                f"No enviamos carga a {ciudad.nombre}. Destinos: {', '.join(ciudades_carga)}.",
                codigo="ciudad_sin_carga",
            )
    if origen.id == destino.id:
        raise ReglaNegocio("El origen y el destino deben ser ciudades distintas.")
    if peso_kg <= 0:
        raise ReglaNegocio("El peso debe ser mayor a cero.")

    limite = await parametros.obtener_decimal(session, "encomienda_peso_max_paquete_kg")
    tipo = tipo or (TipoEnvio.carga if peso_kg > limite else TipoEnvio.paquete)
    if tipo in (TipoEnvio.sobre, TipoEnvio.paquete) and peso_kg > limite:
        raise ReglaNegocio(
            f"Sobres y paquetes admiten hasta {limite:.0f} kg. Para más peso el envío es carga (con GPS).",
            codigo="peso_excede_paquete",
        )
    if tipo == TipoEnvio.carga and peso_kg <= limite:
        raise ReglaNegocio(
            f"La carga es para envíos de más de {limite:.0f} kg; hasta ese peso envíalo como paquete.",
            codigo="peso_insuficiente_carga",
        )
    if puerta_a_puerta and not destino.tiene_puerta_a_puerta:
        conp = [c.nombre for c in await catalogos.listar_ciudades(session) if c.tiene_puerta_a_puerta]
        raise ReglaNegocio(
            f"El servicio puerta a puerta solo está disponible en {' y '.join(conp)}.",
            codigo="sin_puerta_a_puerta",
        )

    tarifa = await _tarifa(session, origen, destino, tipo)
    if tarifa.peso_max_kg is not None and peso_kg > tarifa.peso_max_kg:
        raise ReglaNegocio(
            f"Un {tipo} admite hasta {tarifa.peso_max_kg:.0f} kg; envíalo como paquete.",
            codigo="peso_excede_tipo",
        )
    kg_adicionales = max(Decimal(0), peso_kg - tarifa.peso_min_kg)
    cargo_adicional = precios.redondear(kg_adicionales * tarifa.precio_kg_adicional_bs)
    recargo = tarifa.recargo_puerta_a_puerta_bs if puerta_a_puerta else Decimal("0.00")
    total = tarifa.precio_base_bs + cargo_adicional + recargo
    extra = " con entrega puerta a puerta" if puerta_a_puerta else ""
    return {
        "origen": origen.nombre,
        "destino": destino.nombre,
        "tipo_envio": tipo,
        "peso_kg": float(peso_kg),
        "puerta_a_puerta": puerta_a_puerta,
        "precio_base_bs": tarifa.precio_base_bs,
        "kg_adicionales": float(kg_adicionales),
        "precio_kg_adicional_bs": tarifa.precio_kg_adicional_bs,
        "cargo_peso_adicional_bs": cargo_adicional,
        "recargo_puerta_a_puerta_bs": recargo,
        "total_bs": total,
        "mensaje": (
            f"Enviar un {tipo} de {peso_kg:g} kg de {origen.nombre} a {destino.nombre}{extra} cuesta "
            f"Bs {total:.2f}. Puedes pagar en origen o en destino."
        ),
    }


async def cotizar(
    session: AsyncSession,
    origen: str,
    destino: str,
    peso_kg: float,
    tipo: TipoEnvio | None = None,
    puerta_a_puerta: bool = False,
) -> dict[str, Any]:
    return await _cotizar(
        session,
        await catalogos.resolver_ciudad(session, origen),
        await catalogos.resolver_ciudad(session, destino),
        Decimal(str(peso_kg)),
        tipo,
        puerta_a_puerta,
    )


# --- Rutas de carga ----------------------------------------------------------------------------


async def secuencia_ruta(session: AsyncSession, ruta_id: int) -> list[int]:
    """IDs de ciudades por las que pasa la ruta, en orden (origen, paradas con carga, destino)."""
    ruta = await session.get(Ruta, ruta_id)
    paradas = (
        await session.scalars(
            select(RutaParada.ciudad_id)
            .where(RutaParada.ruta_id == ruta_id, RutaParada.permite_carga)
            .order_by(RutaParada.orden)
        )
    ).all()
    return [ruta.origen_ciudad_id, *paradas, ruta.destino_ciudad_id]


async def ruta_conecta(session: AsyncSession, ruta_id: int, origen_id: int, destino_id: int) -> bool:
    seq = await secuencia_ruta(session, ruta_id)
    return origen_id in seq and destino_id in seq and seq.index(origen_id) < seq.index(destino_id)


async def _horas_estimadas(session: AsyncSession, origen_id: int, destino_id: int) -> int:
    """Estimación: salida esa noche + tiempo de viaje; con transbordo en Sucre, un día más."""
    for ruta in (await session.scalars(select(Ruta).where(Ruta.activo))).all():
        if await ruta_conecta(session, ruta.id, origen_id, destino_id):
            return 24 + ruta.duracion_estimada_min // 60
    return 48


# --- Registro ----------------------------------------------------------------------------------


async def _oficina(session: AsyncSession, codigo: str) -> Oficina:
    oficina = await session.scalar(
        select(Oficina).where(Oficina.codigo == codigo.upper()).options(selectinload(Oficina.ciudad))
    )
    if not oficina or not oficina.activo:
        raise NoEncontrado(f"No existe la oficina {codigo}.")
    if oficina.tipo == TipoOficina.boleteria:
        raise ReglaNegocio(f"{oficina.nombre} es una boletería; las encomiendas se reciben en bodegas.")
    return oficina


async def _crear_pago(session: AsyncSession, enc: Encomienda, metodo: MetodoPago, usuario: Usuario | None) -> Pago:
    if metodo == MetodoPago.credito_corporativo:
        raise ReglaNegocio("Para crédito corporativo usa pago_en = credito_corporativo.")
    pago = Pago(
        encomienda_id=enc.id,
        metodo=metodo,
        monto_bs=enc.precio_bs,
        estado=EstadoPago.aprobado,
        proveedor="bodega",
        transaccion_externa_id=f"SIM-{secrets.token_hex(6).upper()}",
        pagado_at=ahora(),
        cobrado_por_usuario_id=usuario.id if usuario else None,
    )
    session.add(pago)
    enc.estado_pago = EstadoPago.aprobado
    return pago


def _descripcion(enc: Encomienda, estado: EstadoEncomienda, oficina: Oficina | None) -> str:
    origen = enc.oficina_origen.ciudad.nombre
    destino = enc.oficina_destino.ciudad.nombre
    match estado:
        case E.registrada:
            return f"Registramos tu envío en {oficina.nombre if oficina else origen}."
        case E.recibida_en_origen:
            return f"Recibimos tu envío en {oficina.nombre if oficina else origen}."
        case E.en_transito:
            return f"Tu envío salió de {origen} rumbo a {destino}."
        case E.llegada_a_destino:
            return f"Tu envío llegó a {destino}."
        case E.lista_para_retiro:
            o = enc.oficina_destino
            return f"Tu envío está listo para recoger en {o.nombre} ({o.direccion})."
        case E.en_reparto:
            return "Tu envío está en camino a la dirección de entrega."
        case E.entregada:
            return "Tu envío fue entregado."
        case E.intento_fallido:
            return "No pudimos entregar tu envío; nos comunicaremos contigo para coordinar."
        case E.devuelta:
            return "Tu envío fue devuelto al remitente."
        case _:
            return "El envío fue cancelado."


def _agregar_evento(
    session: AsyncSession,
    enc: Encomienda,
    estado: EstadoEncomienda,
    *,
    oficina: Oficina | None = None,
    descripcion: str | None = None,
    visible: bool = True,
    usuario: Usuario | None = None,
    latitud: float | None = None,
    longitud: float | None = None,
    momento=None,
) -> EncomiendaEvento:
    if estado != enc.estado and estado not in TRANSICIONES[enc.estado]:
        raise ReglaNegocio(
            f"La encomienda {enc.numero_guia} no puede pasar de «{ESTADO_LEGIBLE[enc.estado]}» a "
            f"«{ESTADO_LEGIBLE[estado]}».",
            codigo="transicion_invalida",
        )
    if oficina is None:
        oficina = enc.oficina_origen if estado in ESTADOS_EN_ORIGEN else enc.oficina_destino
    evento = EncomiendaEvento(
        encomienda_id=enc.id,
        estado=estado,
        oficina_id=oficina.id if oficina else None,
        ciudad_id=oficina.ciudad_id if oficina else None,
        descripcion=descripcion or _descripcion(enc, estado, oficina),
        latitud=latitud,
        longitud=longitud,
        ocurrido_at=momento or ahora(),
        registrado_por_usuario_id=usuario.id if usuario else None,
        visible_cliente=visible,
    )
    session.add(evento)
    enc.estado = estado
    return evento


async def registrar(session: AsyncSession, datos: EncomiendaIn, usuario: Usuario | None) -> Encomienda:
    origen = await _oficina(session, datos.oficina_origen_codigo)
    destino = await _oficina(session, datos.oficina_destino_codigo)
    if origen.ciudad_id == destino.ciudad_id:
        raise ReglaNegocio("La oficina de destino debe estar en otra ciudad.")
    puerta = datos.modalidad_entrega == ModalidadEntrega.puerta_a_puerta
    cotizacion = await _cotizar(
        session, origen.ciudad, destino.ciudad, Decimal(str(datos.peso_kg)), datos.tipo_envio, puerta
    )

    cuenta = None
    if datos.cuenta_corporativa_codigo:
        cuenta = await session.scalar(
            select(CuentaCorporativa).where(CuentaCorporativa.codigo == datos.cuenta_corporativa_codigo.upper())
        )
        if not cuenta or not cuenta.activo:
            raise NoEncontrado("No existe esa cuenta corporativa.")
    if datos.pago_en == PagoEn.credito_corporativo:
        disponible = cuenta.limite_credito_bs - cuenta.saldo_pendiente_bs
        if cotizacion["total_bs"] > disponible:
            raise ReglaNegocio(
                f"La cuenta {cuenta.codigo} no tiene crédito suficiente (disponible Bs {disponible:.2f}).",
                codigo="credito_insuficiente",
            )
    if usuario is None and datos.metodo_pago == MetodoPago.efectivo:
        raise ReglaNegocio("El pago en efectivo se hace en la bodega.")

    remitente = await reservas.upsert_cliente(session, datos.remitente)
    horas = await _horas_estimadas(session, origen.ciudad_id, destino.ciudad_id)
    enc = Encomienda(
        numero_guia=str(await session.scalar(text("SELECT nextval('seq_numero_guia')"))),
        tipo_envio=cotizacion["tipo_envio"],
        remitente_cliente_id=remitente.id,
        cuenta_corporativa_id=cuenta.id if cuenta else None,
        destinatario_nombre=datos.destinatario_nombre.strip(),
        destinatario_tipo_documento=datos.destinatario_tipo_documento,
        destinatario_numero_documento=datos.destinatario_numero_documento,
        destinatario_telefono_e164=datos.destinatario_telefono,
        oficina_origen_id=origen.id,
        oficina_destino_id=destino.id,
        modalidad_entrega=datos.modalidad_entrega,
        direccion_entrega=datos.direccion_entrega,
        referencia_entrega=datos.referencia_entrega,
        descripcion_contenido=datos.descripcion_contenido,
        cantidad_bultos=datos.cantidad_bultos,
        peso_kg=Decimal(str(datos.peso_kg)),
        largo_cm=datos.largo_cm,
        ancho_cm=datos.ancho_cm,
        alto_cm=datos.alto_cm,
        valor_declarado_bs=datos.valor_declarado_bs,
        es_fragil=datos.es_fragil,
        es_mudanza=datos.es_mudanza,
        precio_bs=cotizacion["total_bs"],
        pago_en=datos.pago_en,
        estado_pago=EstadoPago.pendiente,
        estado=E.registrada,
        codigo_retiro=generar_pin(),
        fecha_estimada_entrega=ahora() + timedelta(hours=horas),
        registrada_por_usuario_id=usuario.id if usuario else None,
        observaciones=datos.observaciones,
        es_dato_demo=False,
    )
    enc.oficina_origen = origen
    enc.oficina_destino = destino
    session.add(enc)
    await session.flush()

    if datos.pago_en == PagoEn.origen:
        await _crear_pago(session, enc, datos.metodo_pago, usuario)
    elif datos.pago_en == PagoEn.credito_corporativo:
        cuenta.saldo_pendiente_bs += enc.precio_bs
        enc.estado_pago = EstadoPago.aprobado

    enc.estado = E.registrada
    session.add(
        EncomiendaEvento(
            encomienda_id=enc.id,
            estado=E.registrada,
            oficina_id=origen.id,
            ciudad_id=origen.ciudad_id,
            descripcion=_descripcion(enc, E.registrada, origen),
            registrado_por_usuario_id=usuario.id if usuario else None,
        )
    )
    _agregar_evento(session, enc, E.recibida_en_origen, oficina=origen, usuario=usuario)
    auditoria.registrar(
        session,
        usuario,
        "encomienda.registrar",
        "encomiendas",
        enc.id,
        {"guia": enc.numero_guia, "precio": enc.precio_bs},
    )
    await session.commit()
    return await obtener(session, enc.numero_guia)


# --- Consultas ---------------------------------------------------------------------------------


def _validar_guia(numero_guia: str) -> str:
    guia = "".join(c for c in numero_guia if c.isdigit())
    if len(guia) != 8:
        raise ReglaNegocio(f"El número de guía tiene 8 dígitos; recibí «{numero_guia}».", codigo="guia_invalida")
    return guia


async def obtener(session: AsyncSession, numero_guia: str, *, bloquear: bool = False) -> Encomienda:
    guia = _validar_guia(numero_guia)
    q = (
        select(Encomienda)
        .where(Encomienda.numero_guia == guia)
        .options(
            selectinload(Encomienda.remitente),
            selectinload(Encomienda.oficina_origen).selectinload(Oficina.ciudad),
            selectinload(Encomienda.oficina_destino).selectinload(Oficina.ciudad),
            selectinload(Encomienda.eventos).selectinload(EncomiendaEvento.ciudad),
        )
        .execution_options(populate_existing=True)
    )
    if bloquear:
        q = q.with_for_update(of=Encomienda)
    enc = await session.scalar(q)
    if not enc:
        raise NoEncontrado(f"No encontré la guía {guia}. ¿Puedes confirmar los 8 dígitos?", codigo="guia_no_encontrada")
    return enc


def a_respuesta(enc: Encomienda) -> dict[str, Any]:
    return {
        "id": enc.id,
        "numero_guia": enc.numero_guia,
        "tipo_envio": enc.tipo_envio,
        "estado": enc.estado,
        "remitente": enc.remitente.nombre_completo,
        "destinatario_nombre": enc.destinatario_nombre,
        "destinatario_telefono_e164": enc.destinatario_telefono_e164,
        "oficina_origen": enc.oficina_origen.nombre,
        "oficina_destino": enc.oficina_destino.nombre,
        "oficina_origen_codigo": enc.oficina_origen.codigo,
        "oficina_destino_codigo": enc.oficina_destino.codigo,
        "ciudad_origen": enc.oficina_origen.ciudad.nombre,
        "ciudad_destino": enc.oficina_destino.ciudad.nombre,
        "modalidad_entrega": enc.modalidad_entrega,
        "direccion_entrega": enc.direccion_entrega,
        "referencia_entrega": enc.referencia_entrega,
        "valor_declarado_bs": enc.valor_declarado_bs,
        "vehiculo_carga_id": enc.vehiculo_carga_id,
        "descripcion_contenido": enc.descripcion_contenido,
        "cantidad_bultos": enc.cantidad_bultos,
        "peso_kg": float(enc.peso_kg),
        "es_fragil": enc.es_fragil,
        "es_mudanza": enc.es_mudanza,
        "precio_bs": enc.precio_bs,
        "pago_en": enc.pago_en,
        "estado_pago": enc.estado_pago,
        "codigo_retiro": enc.codigo_retiro,
        "salida_id": enc.salida_id,
        "fecha_registro": enc.fecha_registro,
        "fecha_estimada_entrega": enc.fecha_estimada_entrega,
        "fecha_entrega": enc.fecha_entrega,
        "entregado_a_nombre": enc.entregado_a_nombre,
        "eventos": [_evento_dict(ev) for ev in enc.eventos],
    }


def _evento_dict(ev: EncomiendaEvento) -> dict[str, Any]:
    return {
        "estado": ev.estado,
        "descripcion": ev.descripcion,
        "ciudad": ev.ciudad.nombre if ev.ciudad else None,
        "ocurrido_at": ev.ocurrido_at,
    }


def mensaje_rastreo(fila: dict[str, Any], horario: str | None) -> str:
    estado = EstadoEncomienda(fila["estado"])
    guia = fila["numero_guia"]
    base = f"La guía {guia} ({fila['ciudad_origen']} → {fila['ciudad_destino']}) está: {ESTADO_LEGIBLE[estado]}."
    pago = (
        " Tiene un pago pendiente que se cancela al recoger."
        if fila["pago_en"] == PagoEn.destino and fila["estado_pago"] == EstadoPago.pendiente
        else ""
    )
    if estado == E.lista_para_retiro:
        h = f" Horario: {horario}." if horario else ""
        return (
            f"{base} Puedes recogerla en {fila['oficina_destino']}, {fila['oficina_destino_direccion']}.{h} "
            f"Presenta tu documento y el código de retiro.{pago}"
        )
    if estado == E.entregada and fila["fecha_entrega"]:
        return f"{base} Se entregó el {fecha_legible(fila['fecha_entrega'])}."
    if estado not in ESTADOS_FINALES and fila["fecha_estimada_entrega"]:
        return f"{base} Llegada estimada: {fecha_legible(fila['fecha_estimada_entrega'])}.{pago}"
    return base + pago


async def rastreo_publico(session: AsyncSession, numero_guia: str) -> dict[str, Any]:
    guia = _validar_guia(numero_guia)
    fila = (
        (await session.execute(select(v_encomienda_rastreo).where(v_encomienda_rastreo.c.numero_guia == guia)))
        .mappings()
        .first()
    )
    if not fila:
        raise NoEncontrado(f"No encontré la guía {guia}. ¿Puedes confirmar los 8 dígitos?", codigo="guia_no_encontrada")
    eventos = (
        await session.scalars(
            select(EncomiendaEvento)
            .where(EncomiendaEvento.encomienda_id == fila["encomienda_id"], EncomiendaEvento.visible_cliente)
            .options(selectinload(EncomiendaEvento.ciudad))
            .order_by(EncomiendaEvento.ocurrido_at.desc(), EncomiendaEvento.id.desc())
        )
    ).all()
    retiro = fila["modalidad_entrega"] == ModalidadEntrega.retiro_en_oficina
    horario = await catalogos.horario_texto_oficina(session, fila["oficina_destino_id"]) if retiro else None
    return {
        "numero_guia": guia,
        "tipo_envio": fila["tipo_envio"],
        "estado": fila["estado"],
        "estado_legible": ESTADO_LEGIBLE[EstadoEncomienda(fila["estado"])],
        "ciudad_origen": fila["ciudad_origen"],
        "ciudad_destino": fila["ciudad_destino"],
        "modalidad_entrega": fila["modalidad_entrega"],
        "lista_para_retiro": fila["estado"] == E.lista_para_retiro,
        "pago_pendiente_en_destino": fila["pago_en"] == PagoEn.destino and fila["estado_pago"] == EstadoPago.pendiente,
        "oficina_retiro": fila["oficina_destino"] if retiro else None,
        "direccion_retiro": fila["oficina_destino_direccion"] if retiro else None,
        "telefono_oficina": fila["oficina_destino_telefono_e164"] if retiro else None,
        "horario_oficina": horario,
        "cantidad_bultos": fila["cantidad_bultos"],
        "fecha_registro": fila["fecha_registro"],
        "fecha_estimada_entrega": fila["fecha_estimada_entrega"],
        "fecha_entrega": fila["fecha_entrega"],
        "eventos": [_evento_dict(ev) for ev in eventos],
        "mensaje": mensaje_rastreo(dict(fila), horario),
    }


async def listar(
    session: AsyncSession,
    *,
    estado: EstadoEncomienda | None = None,
    telefono: str | None = None,
    oficina_codigo: str | None = None,
    buscar: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, list[Encomienda]]:
    q = select(Encomienda)
    if buscar:
        patron = f"%{buscar.strip()}%"
        q = q.where(
            or_(
                Encomienda.numero_guia.ilike(patron),
                Encomienda.destinatario_nombre.ilike(patron),
                Encomienda.remitente.has(Cliente.numero_documento.ilike(patron)),
            )
        )
    if estado:
        q = q.where(Encomienda.estado == estado)
    if telefono:
        q = q.where(Encomienda.destinatario_telefono_e164 == telefono)
    if oficina_codigo:
        oficina = await session.scalar(select(Oficina.id).where(Oficina.codigo == oficina_codigo.upper()))
        q = q.where(or_(Encomienda.oficina_origen_id == oficina, Encomienda.oficina_destino_id == oficina))
    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    filas = (
        await session.scalars(
            q.options(
                selectinload(Encomienda.remitente),
                selectinload(Encomienda.oficina_origen).selectinload(Oficina.ciudad),
                selectinload(Encomienda.oficina_destino).selectinload(Oficina.ciudad),
                selectinload(Encomienda.eventos).selectinload(EncomiendaEvento.ciudad),
            )
            .order_by(Encomienda.fecha_registro.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return total or 0, list(filas)


# --- Operación ---------------------------------------------------------------------------------


async def registrar_evento(session: AsyncSession, numero_guia: str, datos: EventoIn, usuario: Usuario) -> Encomienda:
    enc = await obtener(session, numero_guia, bloquear=True)
    if datos.estado == E.entregada:
        raise ReglaNegocio("Para entregar usa la operación de entrega, que verifica el código de retiro.")
    if datos.estado == E.en_reparto and enc.modalidad_entrega != ModalidadEntrega.puerta_a_puerta:
        raise ReglaNegocio("Solo las encomiendas puerta a puerta salen a reparto.")
    if datos.estado == E.en_transito and enc.tipo_envio != "carga" and not enc.salida_id:
        raise ReglaNegocio("Asigna primero la salida (bus) que llevará la encomienda.")
    oficina = await _oficina(session, datos.oficina_codigo) if datos.oficina_codigo else None
    _agregar_evento(
        session,
        enc,
        datos.estado,
        oficina=oficina,
        descripcion=datos.descripcion,
        visible=datos.visible_cliente,
        usuario=usuario,
        latitud=datos.latitud,
        longitud=datos.longitud,
    )
    await session.commit()
    return await obtener(session, enc.numero_guia)


async def despachar(session: AsyncSession, numero_guia: str, salida_id, usuario: Usuario) -> Encomienda:
    enc = await obtener(session, numero_guia, bloquear=True)
    if enc.estado != E.recibida_en_origen:
        raise ReglaNegocio(f"Solo se despachan encomiendas recibidas en origen (está {ESTADO_LEGIBLE[enc.estado]}).")
    if enc.tipo_envio == TipoEnvio.carga:
        raise ReglaNegocio("La carga de más de 30 kg viaja en furgón con GPS: asígnale un vehículo.")
    salida = await salidas.obtener(session, salida_id)
    if salida.estado not in salidas.ESTADOS_VENDIBLES:
        raise ReglaNegocio(f"La salida {salida.codigo} ya partió o fue cancelada.")
    if not await ruta_conecta(session, salida.ruta_id, enc.oficina_origen.ciudad_id, enc.oficina_destino.ciudad_id):
        raise ReglaNegocio(
            f"La salida {salida.codigo} no pasa por {enc.oficina_origen.ciudad.nombre} y "
            f"{enc.oficina_destino.ciudad.nombre} en ese orden.",
            codigo="salida_no_conecta",
        )
    enc.salida_id = salida.id
    _agregar_evento(
        session,
        enc,
        E.recibida_en_origen,
        descripcion=f"Asignada a la salida {salida.codigo}.",
        visible=False,
        usuario=usuario,
    )
    await session.commit()
    return await obtener(session, enc.numero_guia)


async def asignar_vehiculo(session: AsyncSession, numero_guia: str, vehiculo_id: int, usuario: Usuario) -> Encomienda:
    enc = await obtener(session, numero_guia, bloquear=True)
    vehiculo = await session.get(VehiculoCarga, vehiculo_id)
    if not vehiculo or not vehiculo.activo:
        raise NoEncontrado("No existe ese vehículo.")
    if enc.estado != E.recibida_en_origen:
        raise ReglaNegocio("Solo se despacha carga recibida en origen.")
    if enc.peso_kg > vehiculo.capacidad_kg:
        raise ReglaNegocio(f"La carga supera la capacidad del vehículo ({vehiculo.capacidad_kg} kg).")
    enc.vehiculo_carga_id = vehiculo.id
    _agregar_evento(
        session,
        enc,
        E.en_transito,
        usuario=usuario,
        latitud=float(vehiculo.ultima_latitud) if vehiculo.ultima_latitud else None,
        longitud=float(vehiculo.ultima_longitud) if vehiculo.ultima_longitud else None,
        descripcion=f"Tu carga salió de {enc.oficina_origen.ciudad.nombre} en furgón con seguimiento GPS.",
    )
    await session.commit()
    return await obtener(session, enc.numero_guia)


async def _de_salida(session: AsyncSession, salida: Salida, estado: EstadoEncomienda) -> list[Encomienda]:
    return list(
        (
            await session.scalars(
                select(Encomienda)
                .where(Encomienda.salida_id == salida.id, Encomienda.estado == estado)
                .options(
                    selectinload(Encomienda.oficina_origen).selectinload(Oficina.ciudad),
                    selectinload(Encomienda.oficina_destino).selectinload(Oficina.ciudad),
                )
            )
        ).all()
    )


async def al_partir_salida(session: AsyncSession, salida: Salida, usuario: Usuario | None) -> int:
    encs = await _de_salida(session, salida, E.recibida_en_origen)
    for enc in encs:
        _agregar_evento(session, enc, E.en_transito, usuario=usuario)
    return len(encs)


async def al_llegar_salida(session: AsyncSession, salida: Salida, usuario: Usuario | None) -> int:
    encs = await _de_salida(session, salida, E.en_transito)
    for enc in encs:
        _agregar_evento(session, enc, E.llegada_a_destino, usuario=usuario)
    return len(encs)


async def al_cancelar_salida(session: AsyncSession, salida: Salida, usuario: Usuario | None) -> int:
    encs = await _de_salida(session, salida, E.recibida_en_origen)
    for enc in encs:
        enc.salida_id = None
        _agregar_evento(
            session,
            enc,
            E.recibida_en_origen,
            visible=False,
            usuario=usuario,
            descripcion=f"La salida {salida.codigo} se canceló; pendiente de reasignar.",
        )
    return len(encs)


async def cobrar(session: AsyncSession, numero_guia: str, metodo: MetodoPago, usuario: Usuario) -> Encomienda:
    enc = await obtener(session, numero_guia, bloquear=True)
    if enc.estado_pago != EstadoPago.pendiente:
        raise Conflicto("Esta encomienda no tiene pagos pendientes.")
    await _crear_pago(session, enc, metodo, usuario)
    auditoria.registrar(session, usuario, "encomienda.cobrar", "encomiendas", enc.id, {"metodo": metodo})
    await session.commit()
    return await obtener(session, enc.numero_guia)


async def entregar(session: AsyncSession, numero_guia: str, datos: EntregaIn, usuario: Usuario) -> Encomienda:
    enc = await obtener(session, numero_guia, bloquear=True)
    if enc.estado not in (E.lista_para_retiro, E.en_reparto):
        raise ReglaNegocio(
            f"La encomienda no está lista para entregar ({ESTADO_LEGIBLE[enc.estado]}).", codigo="no_entregable"
        )
    if not hmac.compare_digest(enc.codigo_retiro or "", datos.codigo_retiro):
        raise ReglaNegocio("El código de retiro no coincide.", codigo="codigo_retiro_incorrecto")
    if enc.estado_pago == EstadoPago.pendiente:
        if not datos.metodo_pago:
            raise ReglaNegocio(
                f"Hay un pago pendiente de Bs {enc.precio_bs:.2f}: indica el método de pago.",
                codigo="pago_pendiente",
            )
        await _crear_pago(session, enc, datos.metodo_pago, usuario)
    enc.fecha_entrega = ahora()
    enc.entregado_a_nombre = datos.recibido_por_nombre
    enc.entregado_a_documento = datos.recibido_por_documento.upper()
    _agregar_evento(session, enc, E.entregada, usuario=usuario)
    auditoria.registrar(
        session,
        usuario,
        "encomienda.entregar",
        "encomiendas",
        enc.id,
        {"recibido_por": datos.recibido_por_nombre, "documento": datos.recibido_por_documento},
    )
    await session.commit()
    return await obtener(session, enc.numero_guia)

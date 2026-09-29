"""Datos transaccionales demo: clientes, ventas, encomiendas y puerta a puerta.

Se generan con una semilla fija (resultados reproducibles) y fechas relativas a "ahora".
"""

import random
import secrets
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Asiento,
    Boleto,
    Ciudad,
    Cliente,
    CuentaCorporativa,
    Encomienda,
    EncomiendaEvento,
    Factura,
    Oficina,
    Pago,
    Reembolso,
    Ruta,
    Salida,
    SolicitudPuertaAPuerta,
    Usuario,
    VehiculoCarga,
    VentaPasaje,
)
from app.models.enums import (
    CanalVenta,
    EstadoBoleto,
    EstadoEncomienda,
    EstadoPago,
    EstadoReembolso,
    EstadoSalida,
    EstadoSolicitudPuerta,
    EstadoVenta,
    FranjaHoraria,
    MetodoPago,
    ModalidadEntrega,
    OrigenReembolso,
    PagoEn,
    RolUsuario,
    TipoEnvio,
    TipoPasajero,
    TipoSolicitudPuerta,
)
from app.services import carga as carga_srv
from app.services import catalogos, precios
from app.services import salidas as salidas_srv
from app.utils.codigos import formato_numero_boleto, formato_solicitud_puerta, generar_codigo_reserva
from app.utils.fechas import a_local, ahora, combinar, edad_en, es_dia_habil, hoy
from seeds.data import demo

E = EstadoEncomienda
rnd = random.Random(2026)

GUIA_PRUEBA_INICIAL = "26000101"
TELEFONO_OTRO = "59171234567"


@dataclass
class Ctx:
    telefono_demo: str
    ciudades: dict[str, Ciudad] = field(default_factory=dict)
    oficinas: dict[str, Oficina] = field(default_factory=dict)
    salidas: list[Salida] = field(default_factory=list)
    asientos: dict[int, list[Asiento]] = field(default_factory=dict)
    ocupados: dict = field(default_factory=dict)
    usuarios: dict[str, Usuario] = field(default_factory=dict)
    clientes: list[Cliente] = field(default_factory=list)
    politicas: dict = field(default_factory=dict)
    cuentas: list[CuentaCorporativa] = field(default_factory=list)
    vehiculos: list[VehiculoCarga] = field(default_factory=list)
    secuencias_rutas: dict[int, list[int]] = field(default_factory=dict)
    precios_cache: dict = field(default_factory=dict)


async def ya_sembrado(session: AsyncSession) -> bool:
    return bool(await session.scalar(select(Encomienda.id).where(Encomienda.numero_guia == GUIA_PRUEBA_INICIAL)))


async def _nextval(session: AsyncSession, secuencia: str) -> int:
    return await session.scalar(text(f"SELECT nextval('{secuencia}')"))


async def _cargar_ctx(session: AsyncSession, telefono_demo: str) -> Ctx:
    ctx = Ctx(telefono_demo=telefono_demo)
    ctx.ciudades = {c.codigo: c for c in (await session.scalars(select(Ciudad))).all()}
    ctx.oficinas = {
        o.codigo: o for o in (await session.scalars(select(Oficina).options(selectinload(Oficina.ciudad)))).all()
    }
    ctx.salidas = list(
        (
            await session.scalars(
                select(Salida)
                .where(Salida.bus_id.is_not(None))
                .options(
                    selectinload(Salida.ruta).selectinload(Ruta.origen),
                    selectinload(Salida.ruta).selectinload(Ruta.destino),
                )
                .order_by(Salida.fecha_hora_salida)
            )
        ).all()
    )
    for a in (await session.scalars(select(Asiento).order_by(Asiento.numero))).all():
        ctx.asientos.setdefault(a.bus_id, []).append(a)
    ctx.usuarios = {u.email: u for u in (await session.scalars(select(Usuario))).all()}
    ctx.politicas = await precios.politicas(session)
    ctx.cuentas = list((await session.scalars(select(CuentaCorporativa))).all())
    ctx.vehiculos = list((await session.scalars(select(VehiculoCarga))).all())
    for r in (await session.scalars(select(Ruta))).all():
        ctx.secuencias_rutas[r.id] = await carga_srv.secuencia_ruta(session, r.id)
    return ctx


# --- Clientes ----------------------------------------------------------------------------------


async def _clientes(session: AsyncSession, ctx: Ctx) -> None:
    filas = [
        Cliente(
            tipo_documento="ci",
            numero_documento="6123456",
            extension="CH",
            nombres="Andrea",
            apellidos="Salazar Rocha",
            fecha_nacimiento=date(1990, 4, 12),
            telefono_e164=ctx.telefono_demo,
            email="andrea.salazar@correo.demo",
            es_dato_demo=True,
        ),
        Cliente(
            tipo_documento="ci",
            numero_documento="4987321",
            extension="CH",
            nombres="Mario",
            apellidos="Céspedes Poma",
            fecha_nacimiento=date(1978, 9, 3),
            telefono_e164=TELEFONO_OTRO,
            es_dato_demo=True,
        ),
        Cliente(
            tipo_documento="ci",
            numero_documento="15123987",
            extension="CH",
            nombres="Valentina",
            apellidos="Salazar Rocha",
            fecha_nacimiento=date(2018, 6, 20),
            es_dato_demo=True,
        ),
    ]
    usados = {"6123456", "4987321", "15123987"}
    while len(filas) < 40:
        ci = str(rnd.randint(3_000_000, 9_999_999))
        if ci in usados:
            continue
        usados.add(ci)
        nombre = rnd.choice(demo.NOMBRES)
        apellidos = f"{rnd.choice(demo.APELLIDOS)} {rnd.choice(demo.APELLIDOS)}"
        nacimiento = date(rnd.randint(1948, 2005), rnd.randint(1, 12), rnd.randint(1, 28))
        filas.append(
            Cliente(
                tipo_documento="ci",
                numero_documento=ci,
                extension=rnd.choice(demo.EXTENSIONES),
                nombres=nombre,
                apellidos=apellidos,
                fecha_nacimiento=nacimiento,
                telefono_e164=f"591{rnd.choice('67')}{rnd.randint(0, 9_999_999):07d}",
                email=(
                    f"{nombre.lower()}.{apellidos.split()[0].lower()}{rnd.randint(1, 99)}@correo.demo".translate(
                        str.maketrans("áéíóúñ", "aeioun")
                    )
                    if rnd.random() < 0.6
                    else None
                ),
                es_dato_demo=True,
            )
        )
    session.add_all(filas)
    await session.flush()
    ctx.clientes = filas


# --- Ventas de pasajes -------------------------------------------------------------------------


async def _precio(session: AsyncSession, ctx: Ctx, salida: Salida, tipo_asiento_id: int, tipo: TipoPasajero):
    clave = (salida.id, tipo_asiento_id)
    if clave not in ctx.precios_cache:
        ctx.precios_cache[clave] = await precios.precio_base(session, salida, tipo_asiento_id)
    return precios.aplicar_politica(ctx.precios_cache[clave], ctx.politicas[tipo])


def _asiento_libre(ctx: Ctx, salida: Salida, numero: int | None = None, clase_id: int | None = None) -> Asiento | None:
    ocupados = ctx.ocupados.setdefault(salida.id, set())
    candidatos = [
        a
        for a in ctx.asientos[salida.bus_id]
        if a.numero not in ocupados
        and (numero is None or a.numero == numero)
        and (clase_id is None or a.tipo_asiento_id == clase_id)
    ]
    if not candidatos:
        return None
    asiento = candidatos[0] if numero else rnd.choice(candidatos)
    ocupados.add(asiento.numero)
    return asiento


def _salida_por_codigo(ctx: Ctx, codigo: str) -> Salida | None:
    return next((s for s in ctx.salidas if s.codigo == codigo), None)


def _metodo(canal: CanalVenta) -> MetodoPago:
    if canal == CanalVenta.boleteria:
        return rnd.choice([MetodoPago.efectivo, MetodoPago.efectivo, MetodoPago.qr])
    return rnd.choice(
        [MetodoPago.qr, MetodoPago.qr, MetodoPago.tarjeta_debito, MetodoPago.tarjeta_credito, MetodoPago.tigo_money]
    )


async def _crear_venta(
    session: AsyncSession,
    ctx: Ctx,
    salida: Salida,
    comprador: Cliente,
    pasajeros: list[tuple[Cliente, TipoPasajero, Asiento]],
    *,
    canal: CanalVenta,
    estado: EstadoVenta,
    codigo: str | None = None,
    metodo: MetodoPago | None = None,
    momento: datetime | None = None,
) -> VentaPasaje:
    momento = momento or min(
        ahora(), salida.fecha_hora_salida - timedelta(days=rnd.randint(1, 8), hours=rnd.randint(0, 20))
    )
    boletero = next(
        (u for u in ctx.usuarios.values() if u.rol == RolUsuario.boletero and u.oficina_id == salida.oficina_salida_id),
        None,
    )
    venta = VentaPasaje(
        codigo_reserva=codigo or generar_codigo_reserva(),
        comprador_cliente_id=comprador.id,
        canal=canal,
        estado=estado,
        vendida_por_usuario_id=boletero.id if canal == CanalVenta.boleteria and boletero else None,
        oficina_venta_id=salida.oficina_salida_id if canal == CanalVenta.boleteria else None,
        created_at=momento,
    )
    session.add(venta)
    await session.flush()

    pagada = estado in (EstadoVenta.pagada, EstadoVenta.reembolsada, EstadoVenta.reembolsada_parcial)
    subtotal = descuento = Decimal("0.00")
    for cliente, tipo, asiento in pasajeros:
        precio = await _precio(session, ctx, salida, asiento.tipo_asiento_id, tipo)
        numero = formato_numero_boleto(await _nextval(session, "seq_numero_boleto"))
        if not pagada:
            estado_boleto = EstadoBoleto.reservado if estado == EstadoVenta.pendiente_pago else EstadoBoleto.cancelado
        elif salida.estado in (EstadoSalida.en_ruta, EstadoSalida.llegada):
            estado_boleto = EstadoBoleto.abordado if rnd.random() < 0.92 else EstadoBoleto.no_show
        else:
            estado_boleto = EstadoBoleto.emitido
        session.add(
            Boleto(
                numero_boleto=numero,
                venta_id=venta.id,
                salida_id=salida.id,
                asiento_id=asiento.id,
                numero_asiento=asiento.numero,
                tipo_asiento_id=asiento.tipo_asiento_id,
                pasajero_cliente_id=cliente.id,
                tipo_pasajero=tipo,
                precio_bs=precio.precio_bs,
                descuento_bs=precio.descuento_bs,
                estado=estado_boleto,
                codigo_qr=f"MX|{numero}|{secrets.token_hex(4).upper()}" if pagada else None,
                permiso_viaje_numero=f"DNA-{rnd.randint(10000, 99999)}" if tipo == TipoPasajero.menor else None,
                abordado_at=salida.fecha_hora_salida - timedelta(minutes=rnd.randint(5, 40))
                if estado_boleto == EstadoBoleto.abordado
                else None,
                created_at=momento,
            )
        )
        subtotal += precio.precio_bs
        descuento += precio.descuento_bs
    venta.subtotal_bs, venta.descuento_bs, venta.total_bs = subtotal, descuento, subtotal - descuento

    if estado == EstadoVenta.pendiente_pago:
        venta.expira_at = ahora() + timedelta(hours=24)
    elif estado == EstadoVenta.expirada:
        venta.expira_at = momento + timedelta(minutes=15)
    if pagada:
        metodo = metodo or _metodo(canal)
        venta.pagada_at = momento + timedelta(minutes=3)
        pago = Pago(
            venta_pasaje_id=venta.id,
            metodo=metodo,
            monto_bs=venta.total_bs,
            estado=EstadoPago.aprobado,
            proveedor="boleteria" if canal == CanalVenta.boleteria else "pagoseguro",
            transaccion_externa_id=f"SIM-{secrets.token_hex(6).upper()}",
            ultimos4_tarjeta=f"{rnd.randint(1000, 9999)}"
            if metodo in (MetodoPago.tarjeta_credito, MetodoPago.tarjeta_debito)
            else None,
            pagado_at=venta.pagada_at,
            cobrado_por_usuario_id=venta.vendida_por_usuario_id,
            created_at=venta.pagada_at,
        )
        session.add(pago)
        await session.flush()
        session.add(
            Factura(
                pago_id=pago.id,
                numero_factura=await _nextval(session, "seq_numero_factura"),
                cuf=secrets.token_hex(20).upper(),
                nit_ci_cliente=comprador.numero_documento,
                razon_social_cliente=comprador.apellidos.upper(),
                monto_total_bs=venta.total_bs,
                fecha_emision=venta.pagada_at,
            )
        )
    await session.flush()
    return venta


async def _reservas_fijas(session: AsyncSession, ctx: Ctx) -> Salida:
    demo_cli, otro, _hija = ctx.clientes[:3]
    manana, en_3 = hoy() + timedelta(days=1), hoy() + timedelta(days=3)
    s1 = _salida_por_codigo(ctx, f"SRE-SCZ-{manana:%y%m%d}-2000")
    s2 = _salida_por_codigo(ctx, f"SRE-LPZ-{en_3:%y%m%d}-2000")
    dia_tja = hoy() if combinar(hoy(), datetime.min.time().replace(hour=19)) > ahora() else manana
    s3 = _salida_por_codigo(ctx, f"SRE-TJA-{dia_tja:%y%m%d}-2000")

    await _crear_venta(
        session,
        ctx,
        s1,
        demo_cli,
        [
            (demo_cli, TipoPasajero.adulto, _asiento_libre(ctx, s1, 14)),
            (otro, TipoPasajero.adulto, _asiento_libre(ctx, s1, 15)),
        ],
        canal=CanalVenta.web,
        estado=EstadoVenta.pagada,
        codigo="MX7K2P",
        metodo=MetodoPago.qr,
        momento=ahora() - timedelta(hours=5),
    )
    await _crear_venta(
        session,
        ctx,
        s2,
        demo_cli,
        [(demo_cli, TipoPasajero.adulto, _asiento_libre(ctx, s2, 5))],
        canal=CanalVenta.web,
        estado=EstadoVenta.pendiente_pago,
        codigo="MX9H4R",
        momento=ahora() - timedelta(minutes=10),
    )
    await _crear_venta(
        session,
        ctx,
        s3,
        demo_cli,
        [(demo_cli, TipoPasajero.adulto, _asiento_libre(ctx, s3, 20))],
        canal=CanalVenta.app_movil,
        estado=EstadoVenta.pagada,
        codigo="MX3T8W",
        metodo=MetodoPago.tarjeta_credito,
        momento=ahora() - timedelta(days=2),
    )
    return s3


async def _ventas_aleatorias(session: AsyncSession, ctx: Ctx, cantidad: int = 57) -> None:
    canales = (
        [CanalVenta.web] * 10
        + [CanalVenta.boleteria] * 6
        + [CanalVenta.app_movil] * 2
        + [CanalVenta.telefono, CanalVenta.whatsapp_chat]
    )
    # Las ventas se concentran en lo reciente: viajes ya realizados y los próximos 7 días.
    momento = ahora()
    grupos = [
        [s for s in ctx.salidas if s.fecha_hora_salida <= momento],
        [s for s in ctx.salidas if momento < s.fecha_hora_salida <= momento + timedelta(days=7)],
        [s for s in ctx.salidas if s.fecha_hora_salida > momento + timedelta(days=7)],
    ]
    creadas = 0
    while creadas < cantidad:
        salida = rnd.choice(rnd.choices(grupos, weights=[4, 4, 2])[0])
        if salida.estado == EstadoSalida.cancelada:
            continue
        canal = rnd.choice(canales)
        comprador = rnd.choice(ctx.clientes[3:])
        pasajeros = []
        for i in range(rnd.choices([1, 2, 3], weights=[6, 3, 1])[0]):
            cliente = comprador if i == 0 else rnd.choice(ctx.clientes[3:])
            if any(p[0].id == cliente.id for p in pasajeros):
                continue
            edad = edad_en(cliente.fecha_nacimiento, a_local(salida.fecha_hora_salida).date())
            tipo = TipoPasajero.adulto_mayor if canal == CanalVenta.boleteria and edad >= 60 else TipoPasajero.adulto
            asiento = _asiento_libre(ctx, salida)
            if asiento:
                pasajeros.append((cliente, tipo, asiento))
        if not pasajeros:
            continue
        if salida.fecha_hora_salida <= ahora():
            estado = EstadoVenta.pagada
        else:
            estado = rnd.choices([EstadoVenta.pagada, EstadoVenta.expirada, EstadoVenta.cancelada], weights=[8, 1, 1])[
                0
            ]
        if estado != EstadoVenta.pagada:
            for _, _, a in pasajeros:  # los asientos de ventas no pagadas quedan libres
                ctx.ocupados[salida.id].discard(a.numero)
        await _crear_venta(session, ctx, salida, comprador, pasajeros, canal=canal, estado=estado)
        creadas += 1


async def _reembolsos_cliente(session: AsyncSession, ctx: Ctx) -> None:
    """Tres boletos futuros con reembolso pedido por el cliente (85 %), en distintos estados."""
    boletos = (
        await session.scalars(
            select(Boleto)
            .join(Salida, Salida.id == Boleto.salida_id)
            .where(
                Boleto.estado == EstadoBoleto.emitido,
                Salida.fecha_hora_salida > ahora() + timedelta(days=2),
                Salida.estado == EstadoSalida.programada,
            )
            .options(selectinload(Boleto.venta).selectinload(VentaPasaje.boletos))
            .order_by(Boleto.numero_boleto)
            .limit(3)
        )
    ).all()
    supervisor = ctx.usuarios["supervisor@elmexicanosrl.com"]
    for b, estado in zip(
        boletos, [EstadoReembolso.solicitado, EstadoReembolso.aprobado, EstadoReembolso.pagado], strict=False
    ):
        pago = await session.scalar(select(Pago).where(Pago.venta_pasaje_id == b.venta_id))
        session.add(
            Reembolso(
                pago_id=pago.id,
                boleto_id=b.id,
                origen=OrigenReembolso.solicitud_cliente,
                monto_original_bs=b.total_bs,
                porcentaje_retencion=Decimal(15),
                monto_bs=precios.redondear(b.total_bs * Decimal("0.85")),
                motivo="Cambio de planes del pasajero",
                estado=estado,
                fecha_limite_pago=hoy() + timedelta(days=9),
                resuelto_at=ahora() if estado != EstadoReembolso.solicitado else None,
                resuelto_por_usuario_id=supervisor.id if estado != EstadoReembolso.solicitado else None,
            )
        )
        b.estado = EstadoBoleto.reembolsado
        todos = all(x.estado == EstadoBoleto.reembolsado for x in b.venta.boletos)
        b.venta.estado = EstadoVenta.reembolsada if todos else EstadoVenta.reembolsada_parcial
        if estado == EstadoReembolso.pagado and todos:
            pago.estado = EstadoPago.reembolsado
    await session.commit()


# --- Encomiendas -------------------------------------------------------------------------------


def _pares_conectados(ctx: Ctx) -> list[tuple[str, str, int]]:
    por_id = {c.id: c.codigo for c in ctx.ciudades.values()}
    pares = []
    for ruta_id, seq in ctx.secuencias_rutas.items():
        for i, o in enumerate(seq):
            for d in seq[i + 1 :]:
                pares.append((por_id[o], por_id[d], ruta_id))
    return pares


def _bodega(ctx: Ctx, ciudad: str) -> Oficina:
    return rnd.choice([o for o in ctx.oficinas.values() if o.ciudad.codigo == ciudad and o.tipo != "boleteria"])


def _tiempos_crecientes(tiempos: list[datetime]) -> list[datetime]:
    """Garantiza orden estricto y que ninguno quede en el futuro."""
    tope = ahora() - timedelta(minutes=5)
    salida = []
    for i, t in enumerate(reversed(tiempos)):
        limite = tope - timedelta(minutes=10 * i) if not salida else salida[-1] - timedelta(minutes=10)
        salida.append(min(t, limite))
    return list(reversed(salida))


CAMINO_RETIRO = [
    E.registrada,
    E.recibida_en_origen,
    E.en_transito,
    E.llegada_a_destino,
    E.lista_para_retiro,
    E.entregada,
]
CAMINO_PUERTA = [E.registrada, E.recibida_en_origen, E.en_transito, E.llegada_a_destino, E.en_reparto, E.entregada]


def _camino(objetivo: EstadoEncomienda, puerta: bool) -> list[EstadoEncomienda]:
    base = CAMINO_PUERTA if puerta else CAMINO_RETIRO
    if objetivo == E.cancelada:
        return [E.registrada, E.recibida_en_origen, E.cancelada]
    if objetivo == E.intento_fallido:
        return CAMINO_PUERTA[:5] + [E.intento_fallido]
    if objetivo == E.devuelta:
        return CAMINO_RETIRO[:5] + [E.devuelta]
    return base[: base.index(objetivo) + 1]


def _salida_para(ctx: Ctx, origen: Oficina, destino: Oficina, estados: set[EstadoSalida]) -> Salida | None:
    candidatas = [
        s
        for s in ctx.salidas
        if s.estado in estados
        and origen.ciudad_id in ctx.secuencias_rutas[s.ruta_id]
        and destino.ciudad_id in ctx.secuencias_rutas[s.ruta_id]
        and ctx.secuencias_rutas[s.ruta_id].index(origen.ciudad_id)
        < ctx.secuencias_rutas[s.ruta_id].index(destino.ciudad_id)
    ]
    if not candidatas:
        return None
    if estados == {EstadoSalida.llegada}:
        return rnd.choice(candidatas[-4:])  # de las más recientes
    return rnd.choice(candidatas)


async def _crear_encomienda(
    session: AsyncSession,
    ctx: Ctx,
    *,
    origen: Oficina,
    destino: Oficina,
    tipo: TipoEnvio,
    peso: Decimal,
    objetivo: EstadoEncomienda,
    remitente: Cliente,
    destinatario: tuple[str, str],
    puerta: bool = False,
    direccion: str | None = None,
    pago_en: PagoEn = PagoEn.origen,
    guia: str | None = None,
    pin: str | None = None,
) -> Encomienda:
    cot = await carga_srv._cotizar(session, origen.ciudad, destino.ciudad, peso, tipo, puerta)
    camino = _camino(objetivo, puerta)

    # Momentos de cada paso: anclados a una salida real si la encomienda viaja en bus.
    salida = vehiculo = None
    if tipo != TipoEnvio.carga and E.en_transito in camino:
        estados = {EstadoSalida.en_ruta} if objetivo == E.en_transito else {EstadoSalida.llegada}
        salida = _salida_para(ctx, origen, destino, estados)
    elif tipo != TipoEnvio.carga and objetivo == E.recibida_en_origen and rnd.random() < 0.6:
        salida = _salida_para(ctx, origen, destino, {EstadoSalida.programada})
    if tipo == TipoEnvio.carga and E.en_transito in camino:
        vehiculo = rnd.choice([v for v in ctx.vehiculos if v.tipo == "furgon"])

    if salida and salida.estado != EstadoSalida.programada:
        t_transito = salida.salida_real_at or salida.fecha_hora_salida
        t_llegada = salida.llegada_real_at or (t_transito + timedelta(minutes=salida.ruta.duracion_estimada_min))
    else:
        t_transito = ahora() - timedelta(days=rnd.randint(1, 8), hours=rnd.randint(0, 12))
        t_llegada = t_transito + timedelta(hours=rnd.randint(12, 20))
    t_recibida = t_transito - timedelta(hours=rnd.randint(3, 20))
    if objetivo == E.recibida_en_origen:
        t_recibida = ahora() - timedelta(hours=rnd.randint(1, 30))
    momentos = {
        E.registrada: t_recibida - timedelta(minutes=5),
        E.recibida_en_origen: t_recibida,
        E.cancelada: t_recibida + timedelta(hours=2),
        E.en_transito: t_transito,
        E.llegada_a_destino: t_llegada,
        E.lista_para_retiro: t_llegada + timedelta(hours=1),
        E.en_reparto: t_llegada + timedelta(hours=3),
        E.intento_fallido: t_llegada + timedelta(hours=6),
    }
    momentos[E.entregada] = momentos[camino[-2]] + timedelta(hours=rnd.randint(2, 30))
    momentos[E.devuelta] = momentos[E.lista_para_retiro] + timedelta(days=3)
    tiempos = _tiempos_crecientes([momentos[e] for e in camino])

    bodeguero = next((u for u in ctx.usuarios.values() if u.oficina_id == origen.id), None)
    enc = Encomienda(
        numero_guia=guia or str(await _nextval(session, "seq_numero_guia")),
        tipo_envio=tipo,
        remitente_cliente_id=remitente.id,
        cuenta_corporativa_id=rnd.choice(ctx.cuentas).id if pago_en == PagoEn.credito_corporativo else None,
        destinatario_nombre=destinatario[0],
        destinatario_tipo_documento="ci",
        destinatario_numero_documento=str(rnd.randint(3_000_000, 9_999_999)),
        destinatario_telefono_e164=destinatario[1],
        oficina_origen_id=origen.id,
        oficina_destino_id=destino.id,
        modalidad_entrega=ModalidadEntrega.puerta_a_puerta if puerta else ModalidadEntrega.retiro_en_oficina,
        direccion_entrega=direccion,
        descripcion_contenido=rnd.choice(
            demo.CONTENIDOS_CARGA if tipo == TipoEnvio.carga else demo.CONTENIDOS_ENCOMIENDA
        ),
        cantidad_bultos=rnd.randint(1, 3) if tipo != TipoEnvio.sobre else 1,
        peso_kg=peso,
        es_fragil=rnd.random() < 0.2,
        es_mudanza=tipo == TipoEnvio.carga and rnd.random() < 0.4,
        precio_bs=cot["total_bs"],
        pago_en=pago_en,
        estado_pago=EstadoPago.pendiente,
        estado=camino[-1],
        salida_id=salida.id if salida else None,
        vehiculo_carga_id=vehiculo.id if vehiculo else None,
        codigo_retiro=pin or f"{rnd.randint(0, 9999):04d}",
        fecha_registro=tiempos[0],
        fecha_estimada_entrega=tiempos[0]
        + timedelta(hours=await carga_srv._horas_estimadas(session, origen.ciudad_id, destino.ciudad_id)),
        registrada_por_usuario_id=bodeguero.id if bodeguero else None,
        es_dato_demo=True,
        created_at=tiempos[0],
    )
    if objetivo == E.entregada:
        enc.fecha_entrega = tiempos[-1]
        enc.entregado_a_nombre = destinatario[0]
        enc.entregado_a_documento = enc.destinatario_numero_documento
    session.add(enc)
    await session.flush()

    for estado, momento in zip(camino, tiempos, strict=True):
        en_origen = estado in (E.registrada, E.recibida_en_origen, E.cancelada)
        oficina = origen if en_origen else destino
        enc.oficina_origen, enc.oficina_destino = origen, destino
        lat = lon = None
        if estado == E.en_transito and vehiculo:
            lat, lon = float(vehiculo.ultima_latitud), float(vehiculo.ultima_longitud)
        session.add(
            EncomiendaEvento(
                encomienda_id=enc.id,
                estado=estado,
                oficina_id=oficina.id,
                ciudad_id=oficina.ciudad_id,
                descripcion=carga_srv._descripcion(enc, estado, oficina),
                latitud=lat,
                longitud=lon,
                ocurrido_at=momento,
                registrado_por_usuario_id=bodeguero.id if bodeguero else None,
            )
        )

    # Pago
    if pago_en == PagoEn.credito_corporativo:
        enc.estado_pago = EstadoPago.aprobado
        cuenta = next(c for c in ctx.cuentas if c.id == enc.cuenta_corporativa_id)
        cuenta.saldo_pendiente_bs += enc.precio_bs
    elif pago_en == PagoEn.origen or objetivo == E.entregada:
        enc.estado_pago = EstadoPago.aprobado
        session.add(
            Pago(
                encomienda_id=enc.id,
                metodo=rnd.choice([MetodoPago.efectivo, MetodoPago.qr]),
                monto_bs=enc.precio_bs,
                estado=EstadoPago.aprobado,
                proveedor="bodega",
                transaccion_externa_id=f"SIM-{secrets.token_hex(6).upper()}",
                pagado_at=tiempos[1] if pago_en == PagoEn.origen else tiempos[-1],
            )
        )
    await session.flush()
    return enc


def _destinatario_aleatorio() -> tuple[str, str]:
    nombre = f"{rnd.choice(demo.NOMBRES)} {rnd.choice(demo.APELLIDOS)} {rnd.choice(demo.APELLIDOS)}"
    return nombre, f"591{rnd.choice('67')}{rnd.randint(0, 9_999_999):07d}"


async def _encomiendas_fijas(session: AsyncSession, ctx: Ctx) -> Encomienda:
    of = ctx.oficinas
    demo_dest = ("Andrea Salazar Rocha", ctx.telefono_demo)
    remitente = ctx.clientes[5]
    base = dict(remitente=remitente)
    await _crear_encomienda(
        session,
        ctx,
        origen=of["SRE-BOD"],
        destino=of["SCZ-BOD2"],
        tipo=TipoEnvio.paquete,
        peso=Decimal("4.5"),
        objetivo=E.lista_para_retiro,
        destinatario=demo_dest,
        guia="26000101",
        pin="4821",
        **base,
    )
    await _crear_encomienda(
        session,
        ctx,
        origen=of["SRE-BOD"],
        destino=of["LPZ-BOD"],
        tipo=TipoEnvio.paquete,
        peso=Decimal("12"),
        objetivo=E.en_transito,
        destinatario=demo_dest,
        guia="26000102",
        pin="7305",
        **base,
    )
    await _crear_encomienda(
        session,
        ctx,
        origen=of["SRE-BOD"],
        destino=of["TJA-BOD"],
        tipo=TipoEnvio.sobre,
        peso=Decimal("0.5"),
        objetivo=E.entregada,
        destinatario=demo_dest,
        guia="26000103",
        pin="1946",
        **base,
    )
    enc_104 = await _crear_encomienda(
        session,
        ctx,
        origen=of["SCZ-BOD2"],
        destino=of["SRE-BOD"],
        tipo=TipoEnvio.paquete,
        peso=Decimal("8"),
        objetivo=E.en_reparto,
        destinatario=demo_dest,
        puerta=True,
        direccion=demo.CALLES_SUCRE[0],
        guia="26000104",
        pin="5518",
        **base,
    )
    await _crear_encomienda(
        session,
        ctx,
        origen=of["SRE-BOD"],
        destino=of["PTS-BOD"],
        tipo=TipoEnvio.paquete,
        peso=Decimal("3"),
        objetivo=E.lista_para_retiro,
        destinatario=("Mario Céspedes Poma", TELEFONO_OTRO),
        guia="26000105",
        pin="3072",
        **base,
    )
    await _crear_encomienda(
        session,
        ctx,
        origen=of["SRE-BOD"],
        destino=of["EAT-BOD"],
        tipo=TipoEnvio.paquete,
        peso=Decimal("6"),
        objetivo=E.llegada_a_destino,
        destinatario=demo_dest,
        pago_en=PagoEn.destino,
        guia="26000106",
        pin="8664",
        **base,
    )
    return enc_104


async def _encomiendas_aleatorias(session: AsyncSession, ctx: Ctx) -> None:
    objetivos = (
        [E.recibida_en_origen] * 7
        + [E.en_transito] * 7
        + [E.llegada_a_destino] * 4
        + [E.lista_para_retiro] * 8
        + [E.en_reparto] * 2
        + [E.entregada] * 12
        + [E.intento_fallido, E.devuelta]
        + [E.cancelada] * 2
    )
    pares = _pares_conectados(ctx)
    for objetivo in objetivos:
        requiere_puerta = objetivo in (E.en_reparto, E.intento_fallido)
        tipo = rnd.choices([TipoEnvio.paquete, TipoEnvio.sobre, TipoEnvio.carga], weights=[7, 2, 1])[0]
        if tipo == TipoEnvio.carga:
            o, d = rnd.choice([("SRE", "SCZ"), ("SCZ", "SRE"), ("SRE", "LPZ"), ("SCZ", "LPZ")])
        else:
            o, d, _ = rnd.choice(pares)
        if requiere_puerta and d not in ("SRE", "SCZ"):
            o, d = rnd.choice([("SCZ", "SRE"), ("SRE", "SCZ")])
        puerta = requiere_puerta or (
            d in ("SRE", "SCZ") and objetivo not in (E.lista_para_retiro, E.devuelta) and rnd.random() < 0.3
        )
        peso = {
            TipoEnvio.sobre: Decimal(str(round(rnd.uniform(0.1, 1.5), 1))),
            TipoEnvio.paquete: Decimal(str(round(rnd.uniform(2, 30), 1))),
            TipoEnvio.carga: Decimal(rnd.randint(35, 400)),
        }[tipo]
        if objetivo == E.en_transito and tipo != TipoEnvio.carga:
            origen, destino = _bodega(ctx, o), _bodega(ctx, d)
            if not _salida_para(ctx, origen, destino, {EstadoSalida.en_ruta}):
                tipo, peso = TipoEnvio.carga, Decimal(rnd.randint(35, 400))
        calles = demo.CALLES_SUCRE if d == "SRE" else demo.CALLES_SANTA_CRUZ
        await _crear_encomienda(
            session,
            ctx,
            origen=_bodega(ctx, o),
            destino=_bodega(ctx, d),
            tipo=tipo,
            peso=peso,
            objetivo=objetivo,
            remitente=rnd.choice(ctx.clientes[3:]),
            destinatario=_destinatario_aleatorio(),
            puerta=puerta,
            direccion=rnd.choice(calles) if puerta else None,
            pago_en=rnd.choices([PagoEn.origen, PagoEn.destino, PagoEn.credito_corporativo], weights=[6, 3, 1])[0],
        )


# --- Puerta a puerta ---------------------------------------------------------------------------


async def _dias_habiles(session: AsyncSession, ciudad: Ciudad, desde: date, cantidad: int, paso: int) -> list[date]:
    feriados = await catalogos.feriados_para(
        session, ciudad.departamento, desde - timedelta(days=40), desde + timedelta(days=40)
    )
    dias, actual = [], desde
    while len(dias) < cantidad:
        if es_dia_habil(actual, feriados):
            dias.append(actual)
        actual += timedelta(days=paso)
    return dias


async def _puerta_a_puerta(session: AsyncSession, ctx: Ctx, enc_104: Encomienda) -> None:
    sucre, scz = ctx.ciudades["SRE"], ctx.ciudades["SCZ"]
    repartidores = {
        "SRE": ctx.usuarios["reparto.sucre@elmexicanosrl.com"],
        "SCZ": ctx.usuarios["reparto.santacruz@elmexicanosrl.com"],
    }
    furgonetas = {v.ciudad_base_id: v for v in ctx.vehiculos if v.tipo == "furgoneta_reparto"}
    hoy_habil = (await _dias_habiles(session, sucre, hoy(), 1, 1))[0]
    futuros = {
        c: await _dias_habiles(session, ctx.ciudades[c], hoy() + timedelta(days=1), 4, 1) for c in ("SRE", "SCZ")
    }
    pasados = {
        c: await _dias_habiles(session, ctx.ciudades[c], hoy() - timedelta(days=1), 3, -1) for c in ("SRE", "SCZ")
    }
    demo_cli = ctx.clientes[0]

    plan = [
        ("SRE", TipoSolicitudPuerta.entrega, hoy_habil, EstadoSolicitudPuerta.en_camino, demo_cli, enc_104),
        ("SRE", TipoSolicitudPuerta.recojo, futuros["SRE"][0], EstadoSolicitudPuerta.confirmada, demo_cli, None),
        ("SRE", TipoSolicitudPuerta.recojo, futuros["SRE"][1], EstadoSolicitudPuerta.solicitada, None, None),
        ("SRE", TipoSolicitudPuerta.entrega, pasados["SRE"][0], EstadoSolicitudPuerta.completada, None, None),
        ("SRE", TipoSolicitudPuerta.recojo, pasados["SRE"][1], EstadoSolicitudPuerta.fallida, None, None),
        ("SCZ", TipoSolicitudPuerta.recojo, futuros["SCZ"][0], EstadoSolicitudPuerta.solicitada, None, None),
        ("SCZ", TipoSolicitudPuerta.entrega, futuros["SCZ"][1], EstadoSolicitudPuerta.confirmada, None, None),
        ("SCZ", TipoSolicitudPuerta.recojo, pasados["SCZ"][0], EstadoSolicitudPuerta.completada, None, None),
        ("SCZ", TipoSolicitudPuerta.entrega, pasados["SCZ"][1], EstadoSolicitudPuerta.completada, None, None),
        ("SCZ", TipoSolicitudPuerta.recojo, futuros["SCZ"][2], EstadoSolicitudPuerta.cancelada, None, None),
    ]
    for ciudad_cod, tipo, fecha, estado, cliente, enc in plan:
        ciudad = sucre if ciudad_cod == "SRE" else scz
        cliente = cliente or rnd.choice(ctx.clientes[3:])
        calles = demo.CALLES_SUCRE if ciudad_cod == "SRE" else demo.CALLES_SANTA_CRUZ
        asignada = estado in (
            EstadoSolicitudPuerta.en_camino,
            EstadoSolicitudPuerta.completada,
            EstadoSolicitudPuerta.fallida,
            EstadoSolicitudPuerta.confirmada,
        )
        session.add(
            SolicitudPuertaAPuerta(
                codigo=formato_solicitud_puerta(await _nextval(session, "seq_solicitud_puerta")),
                tipo=tipo,
                ciudad_id=ciudad.id,
                cliente_id=cliente.id,
                contacto_telefono_e164=cliente.telefono_e164 or ctx.telefono_demo,
                direccion=enc.direccion_entrega if enc else rnd.choice(calles),
                referencia="Portón negro, timbre 2" if rnd.random() < 0.5 else None,
                fecha_programada=fecha,
                franja=FranjaHoraria.manana_08_12 if tipo == TipoSolicitudPuerta.entrega else FranjaHoraria.tarde_14_17,
                peso_estimado_kg=Decimal(str(round(rnd.uniform(1, 25), 1))),
                descripcion="Caja mediana" if tipo == TipoSolicitudPuerta.recojo else "Entrega de encomienda",
                encomienda_id=enc.id if enc else None,
                vehiculo_carga_id=furgonetas[ciudad.id].id if asignada else None,
                repartidor_usuario_id=repartidores[ciudad_cod].id if asignada else None,
                estado=estado,
                canal=rnd.choice([CanalVenta.whatsapp_chat, CanalVenta.telefono, CanalVenta.web]),
                costo_bs=Decimal(20),
            )
        )
    await session.flush()


# --- Orquestación ------------------------------------------------------------------------------


async def seed_transaccional(session: AsyncSession, telefono_demo: str) -> None:
    ctx = await _cargar_ctx(session, telefono_demo)
    await _clientes(session, ctx)
    salida_demorada = await _reservas_fijas(session, ctx)

    manana, en_5 = hoy() + timedelta(days=1), hoy() + timedelta(days=5)
    cancelada = _salida_por_codigo(ctx, f"LPZ-SRE-{en_5:%y%m%d}-1830")
    for i in range(3):  # ventas en la salida que se cancelará: generan reembolsos del 100 %
        comprador = ctx.clientes[10 + i]
        await _crear_venta(
            session,
            ctx,
            cancelada,
            comprador,
            [(comprador, TipoPasajero.adulto, _asiento_libre(ctx, cancelada))],
            canal=CanalVenta.web,
            estado=EstadoVenta.pagada,
        )
    await _ventas_aleatorias(session, ctx)
    await session.commit()

    # Primero la cancelación (reembolsos del 100 %), después los reembolsos pedidos por clientes.
    admin = ctx.usuarios["admin@elmexicanosrl.com"]
    await salidas_srv.cambiar_estado(
        session,
        cancelada.id,
        EstadoSalida.cancelada,
        usuario=admin,
        motivo="Bloqueo de carretera reportado en el tramo Oruro – Potosí",
    )
    await _reembolsos_cliente(session, ctx)
    await salidas_srv.cambiar_estado(
        session,
        salida_demorada.id,
        EstadoSalida.demorada,
        usuario=admin,
        minutos_demora=45,
        motivo="Llegada tardía del bus desde Tarija",
    )
    otra = _salida_por_codigo(ctx, f"SCZ-SRE-{manana:%y%m%d}-1830")
    await salidas_srv.cambiar_estado(
        session,
        otra.id,
        EstadoSalida.demorada,
        usuario=admin,
        minutos_demora=30,
        motivo="Mantenimiento preventivo del bus antes de la salida",
    )

    enc_104 = await _encomiendas_fijas(session, ctx)
    await _encomiendas_aleatorias(session, ctx)
    await _puerta_a_puerta(session, ctx, enc_104)
    await session.commit()

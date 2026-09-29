"""Salidas (viajes): generación, búsqueda, mapa de asientos, estados, bus, tripulación y manifiesto."""

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import Conflicto, NoEncontrado, ReglaNegocio
from app.models import (
    Boleto,
    Bus,
    Encomienda,
    Equipaje,
    PlantillaHorario,
    Ruta,
    Salida,
    SalidaTripulacion,
    Usuario,
    VentaPasaje,
)
from app.models.enums import (
    BOLETO_ACTIVO,
    EstadoBoleto,
    EstadoBus,
    EstadoSalida,
    EstadoVenta,
    RolTripulacion,
    RolUsuario,
)
from app.models.vistas import v_salidas_disponibles
from app.services import auditoria, catalogos, parametros, precios
from app.utils.fechas import a_local, ahora, combinar, inicio_y_fin_del_dia

TRANSICIONES: dict[EstadoSalida, set[EstadoSalida]] = {
    EstadoSalida.programada: {
        EstadoSalida.abordando,
        EstadoSalida.demorada,
        EstadoSalida.en_ruta,
        EstadoSalida.cancelada,
    },
    EstadoSalida.demorada: {
        EstadoSalida.demorada,
        EstadoSalida.abordando,
        EstadoSalida.en_ruta,
        EstadoSalida.cancelada,
    },
    EstadoSalida.abordando: {EstadoSalida.en_ruta, EstadoSalida.demorada, EstadoSalida.cancelada},
    EstadoSalida.en_ruta: {EstadoSalida.llegada},
    EstadoSalida.llegada: set(),
    EstadoSalida.cancelada: set(),
}

ESTADOS_VENDIBLES = {EstadoSalida.programada, EstadoSalida.demorada, EstadoSalida.abordando}

# Tiempo mínimo entre la llegada de un bus y su siguiente salida.
MARGEN_ROTACION = timedelta(hours=2)


def codigo_salida(ruta: Ruta, momento: datetime) -> str:
    local = a_local(momento)
    return f"{ruta.codigo}-{local:%y%m%d}-{local:%H%M}"


async def obtener(session: AsyncSession, salida_id: uuid.UUID, *, bloquear: bool = False) -> Salida:
    q = (
        select(Salida)
        .where(Salida.id == salida_id)
        .options(
            selectinload(Salida.ruta).selectinload(Ruta.origen),
            selectinload(Salida.ruta).selectinload(Ruta.destino),
            selectinload(Salida.bus),
            selectinload(Salida.oficina_salida),
        )
        # Refresca el objeto aunque ya esté en la sesión (p. ej. tras cambiar el bus).
        .execution_options(populate_existing=True)
    )
    if bloquear:
        q = q.with_for_update(of=Salida)
    salida = await session.scalar(q)
    if not salida:
        raise NoEncontrado("No existe esa salida.", codigo="salida_no_encontrada")
    return salida


async def obtener_por_codigo(session: AsyncSession, codigo: str) -> Salida:
    salida_id = await session.scalar(select(Salida.id).where(Salida.codigo == codigo.upper()))
    if not salida_id:
        raise NoEncontrado(f"No existe la salida {codigo}.", codigo="salida_no_encontrada")
    return await obtener(session, salida_id)


# --- Generación ------------------------------------------------------------------------------


async def generar_desde_plantillas(session: AsyncSession, desde: date, hasta: date) -> list[Salida]:
    """Crea las salidas de las plantillas activas entre dos fechas (idempotente por código)."""
    if hasta < desde:
        raise ReglaNegocio("La fecha final debe ser posterior a la inicial.")
    plantillas = (
        await session.scalars(
            select(PlantillaHorario).where(PlantillaHorario.activo).options(selectinload(PlantillaHorario.ruta))
        )
    ).all()
    inicio, _ = inicio_y_fin_del_dia(desde)
    _, fin = inicio_y_fin_del_dia(hasta)
    existentes = set(
        (
            await session.scalars(
                select(Salida.codigo).where(Salida.fecha_hora_salida >= inicio, Salida.fecha_hora_salida < fin)
            )
        ).all()
    )
    nuevas: list[Salida] = []
    dia = desde
    while dia <= hasta:
        for p in plantillas:
            vigente = p.vigente_desde <= dia and (p.vigente_hasta is None or dia <= p.vigente_hasta)
            if not vigente or dia.isoweekday() not in p.dias_semana:
                continue
            momento = combinar(dia, p.hora_salida)
            codigo = codigo_salida(p.ruta, momento)
            if codigo in existentes:
                continue
            salida = Salida(
                codigo=codigo,
                ruta_id=p.ruta_id,
                plantilla_id=p.id,
                oficina_salida_id=p.oficina_salida_id,
                fecha_hora_salida=momento,
                fecha_hora_llegada_estimada=momento + timedelta(minutes=p.ruta.duracion_estimada_min),
                estado=EstadoSalida.programada,
                es_dato_demo=p.es_dato_demo,
            )
            session.add(salida)
            nuevas.append(salida)
            existentes.add(codigo)
        dia += timedelta(days=1)
    await session.flush()
    return nuevas


# --- Búsqueda y disponibilidad ----------------------------------------------------------------


async def ventana_de_venta(session: AsyncSession) -> tuple[int, int]:
    return (
        await parametros.obtener_int(session, "venta_cierre_minutos_antes"),
        await parametros.obtener_int(session, "venta_anticipacion_max_dias"),
    )


def es_vendible(estado: EstadoSalida | str, fecha_hora_salida: datetime, cierre_min: int, max_dias: int) -> bool:
    momento = ahora()
    return (
        EstadoSalida(estado) in ESTADOS_VENDIBLES
        and momento < fecha_hora_salida - timedelta(minutes=cierre_min)
        and fecha_hora_salida - momento <= timedelta(days=max_dias + 1)
    )


async def buscar(session: AsyncSession, origen: str, destino: str, fecha: date) -> tuple[Ruta, list[dict[str, Any]]]:
    ciudad_origen = await catalogos.resolver_ciudad(session, origen)
    ciudad_destino = await catalogos.resolver_ciudad(session, destino)
    ruta = await catalogos.ruta_entre(session, ciudad_origen, ciudad_destino)
    inicio, fin = inicio_y_fin_del_dia(fecha)
    v = v_salidas_disponibles.c
    filas = (
        (
            await session.execute(
                select(v_salidas_disponibles)
                .where(v.ruta_id == ruta.id, v.fecha_hora_salida >= inicio, v.fecha_hora_salida < fin)
                .order_by(v.fecha_hora_salida, v.tipo_asiento_id)
            )
        )
        .mappings()
        .all()
    )
    return ruta, await _agrupar_por_salida(session, filas)


async def _agrupar_por_salida(session: AsyncSession, filas) -> list[dict[str, Any]]:
    cierre, max_dias = await ventana_de_venta(session)
    salidas: dict[uuid.UUID, dict[str, Any]] = {}
    for f in filas:
        s = salidas.get(f["salida_id"])
        if s is None:
            s = salidas[f["salida_id"]] = {
                "id": f["salida_id"],
                "codigo": f["codigo"],
                "origen": f["origen"],
                "destino": f["destino"],
                "fecha_hora_salida": f["fecha_hora_salida"],
                "fecha_hora_llegada_estimada": f["fecha_hora_llegada_estimada"],
                "estado": f["estado"],
                "minutos_demora": f["minutos_demora"],
                "anden": f["anden"],
                "bus": f["bus_numero_interno"],
                "vendible": es_vendible(f["estado"], f["fecha_hora_salida"], cierre, max_dias),
                "clases": [],
            }
        s["clases"].append(
            {
                "tipo_asiento_id": f["tipo_asiento_id"],
                "codigo": f["tipo_asiento_codigo"],
                "nombre": f["tipo_asiento"],
                "precio_bs": f["precio_bs"],
                "precio_maximo_referencial_bs": f["precio_maximo_referencial_bs"],
                "asientos_libres": f["asientos_libres"],
                "asientos_total": f["asientos_total"],
            }
        )
    return list(salidas.values())


async def resumen_disponibilidad(session: AsyncSession, salida_id: uuid.UUID) -> dict[str, Any] | None:
    filas = (
        (
            await session.execute(
                select(v_salidas_disponibles)
                .where(v_salidas_disponibles.c.salida_id == salida_id)
                .order_by(v_salidas_disponibles.c.tipo_asiento_id)
            )
        )
        .mappings()
        .all()
    )
    agrupado = await _agrupar_por_salida(session, filas)
    return agrupado[0] if agrupado else None


async def numeros_ocupados(session: AsyncSession, salida_id: uuid.UUID) -> set[int]:
    return set(
        (
            await session.scalars(
                select(Boleto.numero_asiento).where(Boleto.salida_id == salida_id, Boleto.estado.in_(BOLETO_ACTIVO))
            )
        ).all()
    )


async def mapa_asientos(session: AsyncSession, salida_id: uuid.UUID) -> dict[str, Any]:
    salida = await obtener(session, salida_id)
    if salida.bus_id is None:
        raise ReglaNegocio("Esta salida todavía no tiene bus asignado.", codigo="salida_sin_bus")
    bus = await session.scalar(select(Bus).where(Bus.id == salida.bus_id).options(selectinload(Bus.asientos)))
    ocupados = await numeros_ocupados(session, salida_id)
    tipos = {t.id: t for t in await catalogos.listar_tipos_asiento(session)}
    asientos = []
    for a in bus.asientos:
        if not a.habilitado:
            estado = "no_disponible"
        elif a.numero in ocupados:
            estado = "ocupado"
        else:
            estado = "libre"
        asientos.append(
            {
                "numero": a.numero,
                "planta": a.planta,
                "fila": a.fila,
                "columna": a.columna,
                "posicion": a.posicion,
                "tipo_asiento": tipos[a.tipo_asiento_id].codigo,
                "estado": estado,
            }
        )
    return {"salida": salida, "asientos": asientos}


# --- Operación --------------------------------------------------------------------------------


async def cambiar_estado(
    session: AsyncSession,
    salida_id: uuid.UUID,
    nuevo: EstadoSalida,
    *,
    usuario: Usuario | None,
    minutos_demora: int | None = None,
    motivo: str | None = None,
) -> Salida:
    # Import local: carga y reembolsos dependen de este módulo.
    from app.services import carga, reembolsos

    salida = await obtener(session, salida_id, bloquear=True)
    anterior = salida.estado
    if nuevo not in TRANSICIONES[anterior]:
        raise ReglaNegocio(f"No se puede pasar una salida de «{anterior}» a «{nuevo}».", codigo="transicion_invalida")
    if nuevo == EstadoSalida.demorada:
        if not minutos_demora or minutos_demora <= 0:
            raise ReglaNegocio("Indica los minutos de demora.")
        salida.minutos_demora = minutos_demora
    if nuevo == EstadoSalida.cancelada and not motivo:
        raise ReglaNegocio("Indica el motivo de la cancelación.")
    salida.estado = nuevo
    salida.motivo_estado = motivo or salida.motivo_estado

    resumen: dict[str, Any] = {}
    if nuevo == EstadoSalida.en_ruta:
        salida.salida_real_at = ahora()
        resumen["no_show"] = await _marcar_no_show(session, salida)
        resumen["encomiendas_en_transito"] = await carga.al_partir_salida(session, salida, usuario)
    elif nuevo == EstadoSalida.llegada:
        salida.llegada_real_at = ahora()
        resumen["encomiendas_llegadas"] = await carga.al_llegar_salida(session, salida, usuario)
    elif nuevo == EstadoSalida.cancelada:
        resumen["reembolsos"] = await reembolsos.por_cancelacion_de_salida(session, salida, usuario)
        resumen["encomiendas_liberadas"] = await carga.al_cancelar_salida(session, salida, usuario)

    auditoria.registrar(
        session,
        usuario,
        "salida.estado",
        "salidas",
        salida.id,
        {"antes": anterior, "despues": nuevo, "minutos_demora": salida.minutos_demora, "motivo": motivo, **resumen},
    )
    await session.commit()
    return await obtener(session, salida_id)


async def _marcar_no_show(session: AsyncSession, salida: Salida) -> int:
    boletos = (
        await session.scalars(
            select(Boleto).where(Boleto.salida_id == salida.id, Boleto.estado == EstadoBoleto.emitido)
        )
    ).all()
    for b in boletos:
        b.estado = EstadoBoleto.no_show
    # Reservas sin pagar de esta salida ya no se pueden pagar.
    ventas = (
        (
            await session.scalars(
                select(VentaPasaje)
                .join(Boleto, Boleto.venta_id == VentaPasaje.id)
                .where(Boleto.salida_id == salida.id, VentaPasaje.estado == EstadoVenta.pendiente_pago)
                .options(selectinload(VentaPasaje.boletos))
            )
        )
        .unique()
        .all()
    )
    for v in ventas:
        v.estado = EstadoVenta.expirada
        for b in v.boletos:
            b.estado = EstadoBoleto.cancelado
    return len(boletos)


async def bus_superpuesto(session: AsyncSession, bus_id: int, salida: Salida) -> Salida | None:
    return await session.scalar(
        select(Salida).where(
            Salida.bus_id == bus_id,
            Salida.id != salida.id,
            Salida.estado != EstadoSalida.cancelada,
            Salida.fecha_hora_salida < salida.fecha_hora_llegada_estimada + MARGEN_ROTACION,
            Salida.fecha_hora_llegada_estimada + MARGEN_ROTACION > salida.fecha_hora_salida,
        )
    )


async def asignar_bus(session: AsyncSession, salida_id: uuid.UUID, bus_id: int, usuario: Usuario | None) -> Salida:
    salida = await obtener(session, salida_id, bloquear=True)
    if salida.estado not in ESTADOS_VENDIBLES:
        raise ReglaNegocio("Solo se puede cambiar el bus antes de la partida.")
    bus = await session.scalar(select(Bus).where(Bus.id == bus_id).options(selectinload(Bus.asientos)))
    if not bus or not bus.activo:
        raise NoEncontrado("No existe ese bus.")
    if bus.estado != EstadoBus.operativo:
        raise ReglaNegocio(f"El bus {bus.numero_interno} está en {bus.estado}.")
    choque = await bus_superpuesto(session, bus.id, salida)
    if choque:
        raise Conflicto(
            f"El bus {bus.numero_interno} ya está asignado a la salida {choque.codigo}.",
            codigo="bus_ocupado",
        )
    asientos = {a.numero: a for a in bus.asientos if a.habilitado}
    boletos = (
        await session.scalars(select(Boleto).where(Boleto.salida_id == salida.id, Boleto.estado.in_(BOLETO_ACTIVO)))
    ).all()
    for b in boletos:
        nuevo = asientos.get(b.numero_asiento)
        if not nuevo or nuevo.tipo_asiento_id != b.tipo_asiento_id:
            raise Conflicto(
                f"El bus {bus.numero_interno} no tiene el asiento {b.numero_asiento} de la misma clase "
                f"(boleto {b.numero_boleto}).",
                codigo="mapa_incompatible",
            )
        b.asiento_id = nuevo.id
    anterior = salida.bus_id
    salida.bus_id = bus.id
    auditoria.registrar(
        session,
        usuario,
        "salida.asignar_bus",
        "salidas",
        salida.id,
        {"antes": anterior, "despues": bus.id, "boletos_movidos": len(boletos)},
    )
    await session.commit()
    return await obtener(session, salida_id)


async def asignar_tripulacion(
    session: AsyncSession,
    salida_id: uuid.UUID,
    miembros: list[tuple[uuid.UUID, RolTripulacion]],
    usuario: Usuario | None,
) -> list[SalidaTripulacion]:
    salida = await obtener(session, salida_id, bloquear=True)
    if not any(rol == RolTripulacion.conductor for _, rol in miembros):
        raise ReglaNegocio("La tripulación debe incluir al menos un conductor.")
    if salida.ruta.duracion_estimada_min > 8 * 60 and not any(
        rol == RolTripulacion.conductor_relevo for _, rol in miembros
    ):
        raise ReglaNegocio("Un viaje de más de 8 horas requiere conductor de relevo.")
    ids = [u for u, _ in miembros]
    if len(set(ids)) != len(ids):
        raise ReglaNegocio("Una persona no puede figurar dos veces en la tripulación.")
    usuarios = {u.id: u for u in (await session.scalars(select(Usuario).where(Usuario.id.in_(ids)))).all()}
    for usuario_id, rol in miembros:
        u = usuarios.get(usuario_id)
        if not u or not u.activo:
            raise NoEncontrado(f"No existe el usuario {usuario_id}.")
        if rol != RolTripulacion.ayudante and u.rol != RolUsuario.conductor:
            raise ReglaNegocio(f"{u.nombre_completo} no es conductor.")
        choque = await session.scalar(
            select(Salida.codigo)
            .join(SalidaTripulacion, SalidaTripulacion.salida_id == Salida.id)
            .where(
                SalidaTripulacion.usuario_id == usuario_id,
                Salida.id != salida.id,
                Salida.estado != EstadoSalida.cancelada,
                Salida.fecha_hora_salida < salida.fecha_hora_llegada_estimada + MARGEN_ROTACION,
                Salida.fecha_hora_llegada_estimada + MARGEN_ROTACION > salida.fecha_hora_salida,
            )
        )
        if choque:
            raise Conflicto(f"{u.nombre_completo} ya está asignado a la salida {choque}.", codigo="tripulante_ocupado")

    actuales = (await session.scalars(select(SalidaTripulacion).where(SalidaTripulacion.salida_id == salida.id))).all()
    for t in actuales:
        await session.delete(t)
    await session.flush()
    for usuario_id, rol in miembros:
        session.add(SalidaTripulacion(salida_id=salida.id, usuario_id=usuario_id, rol=rol))
    auditoria.registrar(
        session,
        usuario,
        "salida.tripulacion",
        "salidas",
        salida.id,
        {"miembros": [{"usuario_id": u, "rol": r} for u, r in miembros]},
    )
    await session.commit()
    return await tripulacion(session, salida.id)


async def tripulacion(session: AsyncSession, salida_id: uuid.UUID) -> list[SalidaTripulacion]:
    return list(
        (
            await session.scalars(
                select(SalidaTripulacion)
                .where(SalidaTripulacion.salida_id == salida_id)
                .options(selectinload(SalidaTripulacion.usuario))
            )
        ).all()
    )


async def listar(
    session: AsyncSession,
    *,
    fecha: date | None = None,
    ruta_codigo: str | None = None,
    estado: EstadoSalida | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[Salida]]:
    condiciones = []
    if fecha:
        inicio, fin = inicio_y_fin_del_dia(fecha)
        condiciones += [Salida.fecha_hora_salida >= inicio, Salida.fecha_hora_salida < fin]
    if ruta_codigo:
        condiciones.append(Salida.ruta.has(Ruta.codigo == ruta_codigo.upper()))
    if estado:
        condiciones.append(Salida.estado == estado)
    filtro = and_(*condiciones) if condiciones else True
    total = await session.scalar(select(func.count()).select_from(Salida).where(filtro))
    q = (
        select(Salida)
        .where(filtro)
        .options(
            selectinload(Salida.ruta).selectinload(Ruta.origen),
            selectinload(Salida.ruta).selectinload(Ruta.destino),
            selectinload(Salida.bus),
            selectinload(Salida.oficina_salida),
        )
        .order_by(Salida.fecha_hora_salida, Salida.codigo)
        .limit(limit)
        .offset(offset)
    )
    return total or 0, list((await session.scalars(q)).all())


async def manifiesto(session: AsyncSession, salida_id: uuid.UUID) -> dict[str, Any]:
    salida = await obtener(session, salida_id)
    boletos = (
        await session.scalars(
            select(Boleto)
            .where(
                Boleto.salida_id == salida.id,
                Boleto.estado.in_([EstadoBoleto.emitido, EstadoBoleto.abordado, EstadoBoleto.no_show]),
            )
            .options(selectinload(Boleto.pasajero), selectinload(Boleto.tipo_asiento))
            .order_by(Boleto.numero_asiento)
        )
    ).all()
    equipaje_por_boleto = dict(
        (
            await session.execute(
                select(Equipaje.boleto_id, func.sum(Equipaje.peso_kg))
                .where(Equipaje.boleto_id.in_([b.id for b in boletos]))
                .group_by(Equipaje.boleto_id)
            )
        ).all()
    )
    encomiendas = (
        await session.scalars(
            select(Encomienda)
            .where(Encomienda.salida_id == salida.id)
            .options(selectinload(Encomienda.oficina_destino))
            .order_by(Encomienda.numero_guia)
        )
    ).all()
    return {
        "salida": salida,
        "tripulacion": await tripulacion(session, salida.id),
        "pasajeros": [
            {
                "numero_asiento": b.numero_asiento,
                "clase": b.tipo_asiento.nombre,
                "numero_boleto": b.numero_boleto,
                "pasajero": b.pasajero.nombre_completo,
                "documento": f"{b.pasajero.tipo_documento.upper()} {b.pasajero.numero_documento}",
                "tipo_pasajero": b.tipo_pasajero,
                "estado": b.estado,
                "equipaje_kg": equipaje_por_boleto.get(b.id, 0),
            }
            for b in boletos
        ],
        "encomiendas": [
            {
                "numero_guia": e.numero_guia,
                "tipo_envio": e.tipo_envio,
                "bultos": e.cantidad_bultos,
                "peso_kg": e.peso_kg,
                "destino": e.oficina_destino.nombre,
                "estado": e.estado,
            }
            for e in encomiendas
        ],
    }


async def precios_por_clase(session: AsyncSession, salida: Salida) -> list[dict[str, Any]]:
    resultado = []
    for tipo in await catalogos.listar_tipos_asiento(session):
        try:
            base = await precios.precio_base(session, salida, tipo.id)
        except NoEncontrado:
            continue
        resultado.append(
            {
                "tipo_asiento": tipo.codigo,
                "nombre": tipo.nombre,
                "precio_bs": base.precio_adulto_bs,
                "precio_maximo_referencial_bs": base.precio_maximo_referencial_bs,
                "es_precio_especial": base.es_precio_especial_salida,
            }
        )
    return resultado


# --- Calendario y próximas salidas (portal) ---------------------------------------------------


async def calendario(
    session: AsyncSession, origen: str, destino: str, desde: date, dias: int
) -> tuple[Ruta, list[dict[str, Any]]]:
    """Por cada día: cantidad de salidas vendibles con asientos y el precio más bajo."""
    ciudad_origen = await catalogos.resolver_ciudad(session, origen)
    ciudad_destino = await catalogos.resolver_ciudad(session, destino)
    ruta = await catalogos.ruta_entre(session, ciudad_origen, ciudad_destino)
    inicio, _ = inicio_y_fin_del_dia(desde)
    _, fin = inicio_y_fin_del_dia(desde + timedelta(days=dias - 1))
    v = v_salidas_disponibles.c
    filas = (
        (
            await session.execute(
                select(v_salidas_disponibles)
                .where(v.ruta_id == ruta.id, v.fecha_hora_salida >= inicio, v.fecha_hora_salida < fin)
                .order_by(v.fecha_hora_salida, v.tipo_asiento_id)
            )
        )
        .mappings()
        .all()
    )
    resultado = {
        desde + timedelta(days=d): {
            "fecha": desde + timedelta(days=d),
            "salidas": 0,
            "precio_desde_bs": None,
            "disponible": False,
        }
        for d in range(dias)
    }
    for s in await _agrupar_por_salida(session, filas):
        dia = resultado.get(a_local(s["fecha_hora_salida"]).date())
        if dia is None or not s["vendible"]:
            continue
        precios_libres = [
            c["precio_bs"] for c in s["clases"] if c["asientos_libres"] > 0 and c["precio_bs"] is not None
        ]
        if not precios_libres:
            continue
        dia["salidas"] += 1
        dia["disponible"] = True
        minimo = min(precios_libres)
        dia["precio_desde_bs"] = minimo if dia["precio_desde_bs"] is None else min(dia["precio_desde_bs"], minimo)
    return ruta, list(resultado.values())


async def proximas(session: AsyncSession, limite: int = 10) -> list[dict[str, Any]]:
    """Salidas de todas las rutas entre hace 2 h y las próximas 26 h (tablero de salidas)."""
    momento = ahora()
    v = v_salidas_disponibles.c
    filas = (
        (
            await session.execute(
                select(v_salidas_disponibles)
                .where(
                    v.fecha_hora_salida >= momento - timedelta(hours=2),
                    v.fecha_hora_salida <= momento + timedelta(hours=26),
                )
                .order_by(v.fecha_hora_salida, v.ruta_codigo, v.tipo_asiento_id)
            )
        )
        .mappings()
        .all()
    )
    agrupadas = [s for s in await _agrupar_por_salida(session, filas) if s["estado"] != EstadoSalida.llegada]
    return agrupadas[:limite]


async def ocupacion_de(session: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, int]]:
    """(ocupados, total) por salida; vacío para salidas sin bus."""
    if not ids:
        return {}
    v = v_salidas_disponibles.c
    filas = (
        await session.execute(
            select(v.salida_id, func.sum(v.asientos_ocupados), func.sum(v.asientos_total))
            .where(v.salida_id.in_(ids))
            .group_by(v.salida_id)
        )
    ).all()
    return {f[0]: (int(f[1] or 0), int(f[2] or 0)) for f in filas}

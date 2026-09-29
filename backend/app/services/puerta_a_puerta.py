"""Servicio puerta a puerta (real): Sucre y Santa Cruz, desde 1 kg, lunes a viernes.

Entregas de 08:00 a 12:00 y recojos de 14:00 a 17:00.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NoEncontrado, ReglaNegocio
from app.models import Encomienda, SolicitudPuertaAPuerta, Usuario, VehiculoCarga
from app.models.enums import (
    CanalVenta,
    EstadoSolicitudPuerta,
    FranjaHoraria,
    ModalidadEntrega,
    RolUsuario,
    TipoSolicitudPuerta,
)
from app.schemas.carga import SolicitudPuertaIn, SolicitudPuertaUpdate
from app.services import auditoria, catalogos, parametros, reservas
from app.utils.codigos import formato_solicitud_puerta
from app.utils.fechas import ahora, es_dia_habil, fecha_legible, hoy

FRANJA_POR_TIPO = {
    TipoSolicitudPuerta.entrega: FranjaHoraria.manana_08_12,
    TipoSolicitudPuerta.recojo: FranjaHoraria.tarde_14_17,
}
FRANJA_TEXTO = {
    FranjaHoraria.manana_08_12: "de 08:00 a 12:00",
    FranjaHoraria.tarde_14_17: "de 14:00 a 17:00",
}
HORA_CIERRE_FRANJA = {FranjaHoraria.manana_08_12: 12, FranjaHoraria.tarde_14_17: 17}

S = EstadoSolicitudPuerta
TRANSICIONES = {
    S.solicitada: {S.confirmada, S.cancelada},
    S.confirmada: {S.en_camino, S.cancelada},
    S.en_camino: {S.completada, S.fallida},
    S.fallida: {S.confirmada, S.cancelada},
    S.completada: set(),
    S.cancelada: set(),
}


async def crear(
    session: AsyncSession, datos: SolicitudPuertaIn, *, canal: CanalVenta, usuario: Usuario | None = None
) -> SolicitudPuertaAPuerta:
    ciudad = await catalogos.resolver_ciudad(session, datos.ciudad)
    if not ciudad.tiene_puerta_a_puerta:
        raise ReglaNegocio(
            "El servicio puerta a puerta solo está disponible en Sucre y Santa Cruz.", codigo="sin_puerta_a_puerta"
        )
    franja = FRANJA_POR_TIPO[datos.tipo]
    fecha = datos.fecha_programada
    feriados = await catalogos.feriados_para(session, ciudad.departamento, fecha, fecha)
    if not es_dia_habil(fecha, feriados):
        motivo = "feriado" if fecha in feriados else "fin de semana"
        raise ReglaNegocio(
            f"El {fecha_legible(fecha)} es {motivo}: el servicio atiende de lunes a viernes hábiles.",
            codigo="dia_no_habil",
        )
    if fecha < hoy() or (fecha == hoy() and ahora().hour >= HORA_CIERRE_FRANJA[franja] - 1):
        raise ReglaNegocio("Esa franja ya no está disponible; elige otra fecha.", codigo="franja_vencida")
    peso_min = await parametros.obtener_decimal(session, "puerta_a_puerta_peso_min_kg")
    if datos.peso_estimado_kg is not None and Decimal(str(datos.peso_estimado_kg)) < peso_min:
        raise ReglaNegocio(f"El servicio es desde {peso_min:g} kg.")

    encomienda = None
    if datos.numero_guia:
        from app.services import carga

        encomienda = await carga.obtener(session, datos.numero_guia)
        if datos.tipo == TipoSolicitudPuerta.entrega and encomienda.oficina_destino.ciudad_id != ciudad.id:
            raise ReglaNegocio("La encomienda no tiene como destino esta ciudad.")

    cliente = await reservas.upsert_cliente(session, datos.cliente)
    numero = await session.scalar(text("SELECT nextval('seq_solicitud_puerta')"))
    solicitud = SolicitudPuertaAPuerta(
        codigo=formato_solicitud_puerta(numero),
        tipo=datos.tipo,
        ciudad_id=ciudad.id,
        cliente_id=cliente.id,
        contacto_telefono_e164=datos.telefono,
        direccion=datos.direccion,
        referencia=datos.referencia,
        latitud=datos.latitud,
        longitud=datos.longitud,
        fecha_programada=fecha,
        franja=franja,
        peso_estimado_kg=datos.peso_estimado_kg,
        descripcion=datos.descripcion,
        encomienda_id=encomienda.id if encomienda else None,
        estado=S.solicitada,
        canal=canal,
        costo_bs=await parametros.obtener_decimal(session, "puerta_a_puerta_costo_bs"),
    )
    session.add(solicitud)
    if encomienda and encomienda.modalidad_entrega != ModalidadEntrega.puerta_a_puerta:
        encomienda.modalidad_entrega = ModalidadEntrega.puerta_a_puerta
        encomienda.direccion_entrega = datos.direccion
    if usuario:
        auditoria.registrar(session, usuario, "puerta.crear", "solicitudes_puerta_a_puerta", solicitud.codigo)
    await session.commit()
    return await obtener(session, solicitud.codigo)


async def obtener(session: AsyncSession, codigo: str) -> SolicitudPuertaAPuerta:
    codigo = codigo.strip().upper()
    if codigo.isdigit():
        codigo = formato_solicitud_puerta(int(codigo))
    solicitud = await session.scalar(
        select(SolicitudPuertaAPuerta)
        .where(SolicitudPuertaAPuerta.codigo == codigo)
        .options(selectinload(SolicitudPuertaAPuerta.ciudad), selectinload(SolicitudPuertaAPuerta.cliente))
        .execution_options(populate_existing=True)
    )
    if not solicitud:
        raise NoEncontrado(f"No existe la solicitud {codigo}.")
    return solicitud


async def a_respuesta(session: AsyncSession, s: SolicitudPuertaAPuerta) -> dict[str, Any]:
    guia = await session.scalar(select(Encomienda.numero_guia).where(Encomienda.id == s.encomienda_id))
    repartidor = await session.get(Usuario, s.repartidor_usuario_id) if s.repartidor_usuario_id else None
    vehiculo = await session.get(VehiculoCarga, s.vehiculo_carga_id) if s.vehiculo_carga_id else None
    accion = "recoger tu envío" if s.tipo == TipoSolicitudPuerta.recojo else "entregar tu envío"
    return {
        "id": s.id,
        "codigo": s.codigo,
        "tipo": s.tipo,
        "ciudad": s.ciudad.nombre,
        "cliente": s.cliente.nombre_completo,
        "contacto_telefono_e164": s.contacto_telefono_e164,
        "direccion": s.direccion,
        "referencia": s.referencia,
        "fecha_programada": s.fecha_programada,
        "franja": s.franja,
        "franja_texto": FRANJA_TEXTO[s.franja],
        "peso_estimado_kg": float(s.peso_estimado_kg) if s.peso_estimado_kg is not None else None,
        "estado": s.estado,
        "canal": s.canal,
        "costo_bs": s.costo_bs,
        "numero_guia": guia,
        "descripcion": s.descripcion,
        "repartidor_usuario_id": s.repartidor_usuario_id,
        "repartidor": repartidor.nombre_completo if repartidor else None,
        "vehiculo_carga_id": s.vehiculo_carga_id,
        "vehiculo": vehiculo.placa if vehiculo else None,
        "mensaje": (
            f"Solicitud {s.codigo} ({s.estado}): pasaremos a {accion} el {fecha_legible(s.fecha_programada)} "
            f"{FRANJA_TEXTO[s.franja]} en {s.direccion}, {s.ciudad.nombre}."
        ),
    }


async def actualizar(
    session: AsyncSession, codigo: str, datos: SolicitudPuertaUpdate, usuario: Usuario
) -> SolicitudPuertaAPuerta:
    s = await obtener(session, codigo)
    cambios: dict[str, Any] = {}
    if datos.estado and datos.estado != s.estado:
        if datos.estado not in TRANSICIONES[s.estado]:
            raise ReglaNegocio(f"No se puede pasar la solicitud de «{s.estado}» a «{datos.estado}».")
        cambios["estado"] = {"antes": s.estado, "despues": datos.estado}
        s.estado = datos.estado
    if datos.repartidor_usuario_id:
        repartidor = await session.get(Usuario, datos.repartidor_usuario_id)
        if not repartidor or repartidor.rol != RolUsuario.repartidor:
            raise ReglaNegocio("El usuario indicado no es repartidor.")
        s.repartidor_usuario_id = repartidor.id
        cambios["repartidor"] = str(repartidor.id)
    if datos.vehiculo_carga_id:
        if not await session.get(VehiculoCarga, datos.vehiculo_carga_id):
            raise NoEncontrado("No existe ese vehículo.")
        s.vehiculo_carga_id = datos.vehiculo_carga_id
        cambios["vehiculo"] = datos.vehiculo_carga_id
    auditoria.registrar(session, usuario, "puerta.actualizar", "solicitudes_puerta_a_puerta", s.codigo, cambios)
    await session.commit()
    return await obtener(session, s.codigo)


async def listar(
    session: AsyncSession,
    *,
    ciudad: str | None = None,
    fecha=None,
    estado: EstadoSolicitudPuerta | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, list[SolicitudPuertaAPuerta]]:
    q = select(SolicitudPuertaAPuerta)
    if ciudad:
        c = await catalogos.resolver_ciudad(session, ciudad)
        q = q.where(SolicitudPuertaAPuerta.ciudad_id == c.id)
    if fecha:
        q = q.where(SolicitudPuertaAPuerta.fecha_programada == fecha)
    if estado:
        q = q.where(SolicitudPuertaAPuerta.estado == estado)
    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    filas = (
        await session.scalars(
            q.options(selectinload(SolicitudPuertaAPuerta.ciudad), selectinload(SolicitudPuertaAPuerta.cliente))
            .order_by(SolicitudPuertaAPuerta.fecha_programada, SolicitudPuertaAPuerta.franja)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return total or 0, list(filas)

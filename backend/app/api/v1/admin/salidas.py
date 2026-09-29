"""Operación de salidas: programación, bus, tripulación, estados, precios especiales y manifiesto."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.dialects.postgresql import insert

from app.core.deps import PaginacionDep, SessionDep, requiere_roles
from app.core.errors import ReglaNegocio
from app.models import PrecioSalida, Salida, Usuario
from app.models.enums import EstadoSalida, RolUsuario
from app.schemas.admin import (
    AsignarBusIn,
    EstadoSalidaIn,
    GenerarSalidasIn,
    GenerarSalidasOut,
    ManifiestoOut,
    MiembroTripulacionOut,
    PrecioSalidaIn,
    SalidaAdminOut,
    TripulacionIn,
)
from app.schemas.common import Pagina
from app.schemas.ventas import PrecioClase
from app.services import auditoria, precios, salidas

R = RolUsuario
router = APIRouter(prefix="/salidas", tags=["Admin · Salidas"])
_supervisor = Depends(requiere_roles(R.supervisor))
_lectura = Depends(requiere_roles(R.supervisor, R.boletero, R.conductor, R.encargado_bodega))


def _salida_out(s: Salida, ocupacion: tuple[int, int] | None = None) -> dict:
    return {
        "asientos_ocupados": ocupacion[0] if ocupacion else None,
        "asientos_total": ocupacion[1] if ocupacion else None,
        "id": s.id,
        "codigo": s.codigo,
        "ruta": s.ruta.codigo,
        "origen": s.ruta.origen.nombre,
        "destino": s.ruta.destino.nombre,
        "fecha_hora_salida": s.fecha_hora_salida,
        "fecha_hora_llegada_estimada": s.fecha_hora_llegada_estimada,
        "estado": s.estado,
        "minutos_demora": s.minutos_demora,
        "motivo_estado": s.motivo_estado,
        "bus": s.bus.numero_interno if s.bus else None,
        "anden": s.anden,
        "oficina_salida": s.oficina_salida.nombre if s.oficina_salida else None,
        "salida_real_at": s.salida_real_at,
        "llegada_real_at": s.llegada_real_at,
    }


def _tripulacion_out(miembros) -> list[dict]:
    return [
        {
            "usuario_id": t.usuario_id,
            "nombre": t.usuario.nombre_completo,
            "rol": t.rol,
            "licencia_conducir": t.usuario.licencia_conducir,
        }
        for t in miembros
    ]


@router.get("", response_model=Pagina[SalidaAdminOut], summary="Listar salidas")
async def listar(
    session: SessionDep,
    pag: PaginacionDep,
    fecha: date | None = None,
    ruta: str | None = None,
    estado: EstadoSalida | None = None,
    _: Usuario = _lectura,
):
    total, items = await salidas.listar(
        session, fecha=fecha, ruta_codigo=ruta, estado=estado, limit=pag.limit, offset=pag.offset
    )
    ocup = await salidas.ocupacion_de(session, [s.id for s in items])
    return {
        "total": total,
        "limit": pag.limit,
        "offset": pag.offset,
        "items": [_salida_out(s, ocup.get(s.id)) for s in items],
    }


@router.post(
    "/generar",
    response_model=GenerarSalidasOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generar salidas desde las plantillas de horario",
)
async def generar(session: SessionDep, datos: GenerarSalidasIn, usuario: Usuario = _supervisor):
    if (datos.hasta - datos.desde).days > 90:
        raise ReglaNegocio("Genera como máximo 90 días por vez.")
    nuevas = await salidas.generar_desde_plantillas(session, datos.desde, datos.hasta)
    auditoria.registrar(
        session, usuario, "salidas.generar", "salidas", f"{datos.desde}..{datos.hasta}", {"creadas": len(nuevas)}
    )
    await session.commit()
    return {"creadas": len(nuevas), "codigos": [s.codigo for s in nuevas]}


@router.get("/{salida_id}", response_model=SalidaAdminOut, summary="Detalle de una salida")
async def detalle(session: SessionDep, salida_id: uuid.UUID, _: Usuario = _lectura):
    ocup = await salidas.ocupacion_de(session, [salida_id])
    return _salida_out(await salidas.obtener(session, salida_id), ocup.get(salida_id))


@router.post(
    "/{salida_id}/estado",
    response_model=SalidaAdminOut,
    summary="Cambiar el estado (abordando, en ruta, llegada, demora, cancelación)",
    description=(
        "`en_ruta` marca no-show a quien no abordó y pone en tránsito las encomiendas asignadas. "
        "`llegada` las marca como llegadas a destino. `cancelada` reembolsa el 100 % de los boletos pagados."
    ),
)
async def cambiar_estado(
    session: SessionDep, salida_id: uuid.UUID, datos: EstadoSalidaIn, usuario: Usuario = _supervisor
):
    s = await salidas.cambiar_estado(
        session, salida_id, datos.estado, usuario=usuario, minutos_demora=datos.minutos_demora, motivo=datos.motivo
    )
    return _salida_out(s)


@router.put("/{salida_id}/bus", response_model=SalidaAdminOut, summary="Asignar o cambiar el bus")
async def asignar_bus(session: SessionDep, salida_id: uuid.UUID, datos: AsignarBusIn, usuario: Usuario = _supervisor):
    return _salida_out(await salidas.asignar_bus(session, salida_id, datos.bus_id, usuario))


@router.get("/{salida_id}/tripulacion", response_model=list[MiembroTripulacionOut], summary="Tripulación")
async def ver_tripulacion(session: SessionDep, salida_id: uuid.UUID, _: Usuario = _lectura):
    return _tripulacion_out(await salidas.tripulacion(session, salida_id))


@router.put("/{salida_id}/tripulacion", response_model=list[MiembroTripulacionOut], summary="Asignar tripulación")
async def asignar_tripulacion(
    session: SessionDep, salida_id: uuid.UUID, datos: TripulacionIn, usuario: Usuario = _supervisor
):
    miembros = [(m.usuario_id, m.rol) for m in datos.miembros]
    return _tripulacion_out(await salidas.asignar_tripulacion(session, salida_id, miembros, usuario))


@router.put(
    "/{salida_id}/precios",
    response_model=list[PrecioClase],
    summary="Precio especial por clase para esta salida (temporada, feriado, promoción)",
)
async def precio_especial(
    session: SessionDep, salida_id: uuid.UUID, datos: list[PrecioSalidaIn], usuario: Usuario = _supervisor
):
    salida = await salidas.obtener(session, salida_id)
    for p in datos:
        tarifa = await precios.tarifa_vigente(session, salida, p.tipo_asiento_id)
        if p.precio_bs > tarifa.precio_maximo_referencial_bs:
            raise ReglaNegocio(
                f"El precio no puede superar la tarifa máxima referencial (Bs {tarifa.precio_maximo_referencial_bs})."
            )
        stmt = insert(PrecioSalida).values(
            salida_id=salida.id, tipo_asiento_id=p.tipo_asiento_id, precio_bs=p.precio_bs
        )
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=["salida_id", "tipo_asiento_id"], set_={"precio_bs": stmt.excluded.precio_bs}
            )
        )
    auditoria.registrar(
        session, usuario, "salida.precios", "salidas", salida.id, {"precios": [p.model_dump() for p in datos]}
    )
    await session.commit()
    return await salidas.precios_por_clase(session, salida)


@router.get("/{salida_id}/manifiesto", response_model=ManifiestoOut, summary="Manifiesto de pasajeros y carga")
async def manifiesto(session: SessionDep, salida_id: uuid.UUID, _: Usuario = _lectura):
    m = await salidas.manifiesto(session, salida_id)
    return {
        "salida": _salida_out(m["salida"]),
        "tripulacion": _tripulacion_out(m["tripulacion"]),
        "pasajeros": m["pasajeros"],
        "encomiendas": m["encomiendas"],
        "total_pasajeros": len(m["pasajeros"]),
        "total_encomiendas_kg": float(sum(e["peso_kg"] for e in m["encomiendas"])),
    }

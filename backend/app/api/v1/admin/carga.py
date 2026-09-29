"""Bodega: registro de encomiendas, eventos de rastreo, despacho, cobro, entrega y puerta a puerta."""

from datetime import date

from fastapi import APIRouter, Depends, status

from app.core.deps import PaginacionDep, SessionDep, requiere_roles
from app.models import Usuario
from app.models.enums import CanalVenta, EstadoEncomienda, EstadoSolicitudPuerta, RolUsuario
from app.schemas.admin import AsignarVehiculoIn
from app.schemas.carga import (
    CobroIn,
    DespachoIn,
    EncomiendaIn,
    EncomiendaOut,
    EntregaIn,
    EventoIn,
    SolicitudPuertaAdminOut,
    SolicitudPuertaIn,
    SolicitudPuertaUpdate,
)
from app.schemas.common import Pagina
from app.services import carga, puerta_a_puerta
from app.utils.telefonos import normalizar_e164

R = RolUsuario
router = APIRouter(tags=["Admin · Carga y encomiendas"])
_bodega = Depends(requiere_roles(R.encargado_bodega, R.supervisor))
_bodega_o_reparto = Depends(requiere_roles(R.encargado_bodega, R.supervisor, R.repartidor))
_puerta = Depends(requiere_roles(R.encargado_bodega, R.supervisor, R.repartidor, R.soporte))


@router.get("/encomiendas", response_model=Pagina[EncomiendaOut], summary="Listar encomiendas")
async def listar(
    session: SessionDep,
    pag: PaginacionDep,
    estado: EstadoEncomienda | None = None,
    telefono: str | None = None,
    oficina: str | None = None,
    q: str | None = None,
    _: Usuario = _bodega_o_reparto,
):
    total, items = await carga.listar(
        session,
        estado=estado,
        telefono=normalizar_e164(telefono) if telefono else None,
        oficina_codigo=oficina,
        buscar=q,
        limit=pag.limit,
        offset=pag.offset,
    )
    return {"total": total, "limit": pag.limit, "offset": pag.offset, "items": [carga.a_respuesta(e) for e in items]}


@router.post(
    "/encomiendas",
    response_model=EncomiendaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una encomienda (genera guía de 8 dígitos y PIN de retiro)",
)
async def registrar(session: SessionDep, datos: EncomiendaIn, usuario: Usuario = _bodega):
    return carga.a_respuesta(await carga.registrar(session, datos, usuario))


@router.get("/encomiendas/{numero_guia}", response_model=EncomiendaOut, summary="Detalle completo de una encomienda")
async def detalle(session: SessionDep, numero_guia: str, _: Usuario = _bodega_o_reparto):
    return carga.a_respuesta(await carga.obtener(session, numero_guia))


@router.post(
    "/encomiendas/{numero_guia}/eventos",
    response_model=EncomiendaOut,
    summary="Registrar un evento de rastreo (actualiza el estado)",
)
async def evento(session: SessionDep, numero_guia: str, datos: EventoIn, usuario: Usuario = _bodega_o_reparto):
    return carga.a_respuesta(await carga.registrar_evento(session, numero_guia, datos, usuario))


@router.post(
    "/encomiendas/{numero_guia}/despachar",
    response_model=EncomiendaOut,
    summary="Asignar la encomienda a una salida (bus)",
)
async def despachar(session: SessionDep, numero_guia: str, datos: DespachoIn, usuario: Usuario = _bodega):
    return carga.a_respuesta(await carga.despachar(session, numero_guia, datos.salida_id, usuario))


@router.post(
    "/encomiendas/{numero_guia}/vehiculo",
    response_model=EncomiendaOut,
    summary="Despachar carga (> 30 kg) en furgón con GPS",
)
async def vehiculo(session: SessionDep, numero_guia: str, datos: AsignarVehiculoIn, usuario: Usuario = _bodega):
    return carga.a_respuesta(await carga.asignar_vehiculo(session, numero_guia, datos.vehiculo_id, usuario))


@router.post("/encomiendas/{numero_guia}/cobrar", response_model=EncomiendaOut, summary="Cobrar pago pendiente")
async def cobrar(session: SessionDep, numero_guia: str, datos: CobroIn, usuario: Usuario = _bodega_o_reparto):
    return carga.a_respuesta(await carga.cobrar(session, numero_guia, datos.metodo, usuario))


@router.post(
    "/encomiendas/{numero_guia}/entregar",
    response_model=EncomiendaOut,
    summary="Entregar al destinatario (verifica el PIN de retiro y cobra si hay pago en destino)",
)
async def entregar(session: SessionDep, numero_guia: str, datos: EntregaIn, usuario: Usuario = _bodega_o_reparto):
    return carga.a_respuesta(await carga.entregar(session, numero_guia, datos, usuario))


# --- Puerta a puerta ---------------------------------------------------------------------------


@router.get("/puerta-a-puerta", response_model=Pagina[SolicitudPuertaAdminOut], summary="Listar solicitudes")
async def listar_puerta(
    session: SessionDep,
    pag: PaginacionDep,
    ciudad: str | None = None,
    fecha: date | None = None,
    estado: EstadoSolicitudPuerta | None = None,
    _: Usuario = _puerta,
):
    total, items = await puerta_a_puerta.listar(
        session, ciudad=ciudad, fecha=fecha, estado=estado, limit=pag.limit, offset=pag.offset
    )
    return {
        "total": total,
        "limit": pag.limit,
        "offset": pag.offset,
        "items": [await puerta_a_puerta.a_respuesta(session, s) for s in items],
    }


@router.post(
    "/puerta-a-puerta",
    response_model=SolicitudPuertaAdminOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una solicitud recibida por teléfono o WhatsApp",
)
async def crear_puerta(
    session: SessionDep, datos: SolicitudPuertaIn, canal: CanalVenta = CanalVenta.telefono, usuario: Usuario = _puerta
):
    solicitud = await puerta_a_puerta.crear(session, datos, canal=canal, usuario=usuario)
    return await puerta_a_puerta.a_respuesta(session, solicitud)


@router.get("/puerta-a-puerta/{codigo}", response_model=SolicitudPuertaAdminOut, summary="Ver una solicitud")
async def ver_puerta(session: SessionDep, codigo: str, _: Usuario = _puerta):
    return await puerta_a_puerta.a_respuesta(session, await puerta_a_puerta.obtener(session, codigo))


@router.patch(
    "/puerta-a-puerta/{codigo}",
    response_model=SolicitudPuertaAdminOut,
    summary="Actualizar estado, repartidor o vehículo",
)
async def actualizar_puerta(session: SessionDep, codigo: str, datos: SolicitudPuertaUpdate, usuario: Usuario = _puerta):
    solicitud = await puerta_a_puerta.actualizar(session, codigo, datos, usuario)
    return await puerta_a_puerta.a_respuesta(session, solicitud)

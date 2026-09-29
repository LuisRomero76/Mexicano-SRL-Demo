"""Boletería: venta en ventanilla (con tarifas especiales), cobro, abordaje, equipaje y reembolsos."""

import uuid

from fastapi import APIRouter, Depends, status

from app.core.deps import PaginacionDep, SessionDep, requiere_roles
from app.models import Usuario
from app.models.enums import CanalVenta, EstadoReembolso, EstadoVenta, RolUsuario
from app.schemas.admin import ReembolsoAdminIn, ReembolsoOut, ResolverReembolsoIn, VentaResumenOut
from app.schemas.common import Pagina
from app.schemas.ventas import AbordajeIn, BoletoOut, EquipajeIn, EquipajeOut, PagoIn, ReservaIn, ReservaOut
from app.services import reembolsos, reservas

R = RolUsuario
router = APIRouter(tags=["Admin · Boletería"])
_boleteria = Depends(requiere_roles(R.boletero, R.supervisor))
_abordaje = Depends(requiere_roles(R.boletero, R.supervisor, R.conductor))


@router.get("/ventas", response_model=Pagina[VentaResumenOut], summary="Listar ventas")
async def listar(
    session: SessionDep,
    pag: PaginacionDep,
    estado: EstadoVenta | None = None,
    canal: CanalVenta | None = None,
    documento: str | None = None,
    _: Usuario = _boleteria,
):
    total, items = await reservas.listar_ventas(
        session, estado=estado, canal=canal, documento=documento, limit=pag.limit, offset=pag.offset
    )
    return {
        "total": total,
        "limit": pag.limit,
        "offset": pag.offset,
        "items": [
            {
                "codigo_reserva": v.codigo_reserva,
                "estado": v.estado,
                "canal": v.canal,
                "comprador": v.comprador.nombre_completo,
                "total_bs": v.total_bs,
                "created_at": v.created_at,
                "pagada_at": v.pagada_at,
            }
            for v in items
        ],
    }


@router.post(
    "/ventas",
    response_model=ReservaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Vender en boletería (permite tarifas de menor, adulto mayor y discapacidad)",
)
async def vender(session: SessionDep, datos: ReservaIn, usuario: Usuario = _boleteria):
    venta = await reservas.crear_reserva(session, datos, canal=CanalVenta.boleteria, usuario=usuario)
    return await reservas.a_respuesta(session, venta)


@router.get("/ventas/{codigo}", response_model=ReservaOut, summary="Ver una venta")
async def ver(session: SessionDep, codigo: str, _: Usuario = _boleteria):
    return await reservas.a_respuesta(session, await reservas.obtener(session, codigo))


@router.post("/ventas/{codigo}/cobrar", response_model=ReservaOut, summary="Cobrar en ventanilla (incluye efectivo)")
async def cobrar(session: SessionDep, codigo: str, datos: PagoIn, usuario: Usuario = _boleteria):
    venta = await reservas.pagar(session, codigo, datos, usuario=usuario)
    return await reservas.a_respuesta(session, venta)


def _boleto_out(b) -> dict:
    return {
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


@router.post("/boletos/abordar", response_model=BoletoOut, summary="Registrar abordaje (número de boleto o QR)")
async def abordar(session: SessionDep, datos: AbordajeIn, usuario: Usuario = _abordaje):
    return _boleto_out(await reservas.abordar(session, datos.codigo, usuario))


@router.post(
    "/boletos/{numero_boleto}/equipajes",
    response_model=EquipajeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar equipaje (20 kg bodega + 5 kg mano; el exceso se cobra por kg según ruta)",
)
async def equipaje(session: SessionDep, numero_boleto: str, datos: EquipajeIn, usuario: Usuario = _abordaje):
    return await reservas.registrar_equipaje(session, numero_boleto, datos, usuario)


@router.post(
    "/boletos/{numero_boleto}/reembolso",
    response_model=ReembolsoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar la solicitud de reembolso de un boleto (85 %)",
)
async def solicitar_reembolso(
    session: SessionDep, numero_boleto: str, datos: ReembolsoAdminIn, usuario: Usuario = _boleteria
):
    r = await reembolsos.solicitar(session, numero_boleto, datos.motivo, usuario=usuario)
    return (await reembolsos.con_detalle(session, [r]))[0]


@router.get(
    "/reembolsos", response_model=Pagina[ReembolsoOut], summary="Listar reembolsos", tags=["Admin · Reembolsos"]
)
async def listar_reembolsos(
    session: SessionDep,
    pag: PaginacionDep,
    estado: EstadoReembolso | None = None,
    _: Usuario = Depends(requiere_roles(R.supervisor, R.soporte)),
):
    total, items = await reembolsos.listar(session, estado=estado, limit=pag.limit, offset=pag.offset)
    return {
        "total": total,
        "limit": pag.limit,
        "offset": pag.offset,
        "items": await reembolsos.con_detalle(session, items),
    }


@router.post(
    "/reembolsos/{reembolso_id}/resolver",
    response_model=ReembolsoOut,
    summary="Aprobar, rechazar o marcar como pagado un reembolso",
    tags=["Admin · Reembolsos"],
)
async def resolver_reembolso(
    session: SessionDep,
    reembolso_id: uuid.UUID,
    datos: ResolverReembolsoIn,
    usuario: Usuario = Depends(requiere_roles(R.supervisor)),
):
    r = await reembolsos.resolver(session, reembolso_id, datos.estado, usuario, datos.nota)
    return (await reembolsos.con_detalle(session, [r]))[0]

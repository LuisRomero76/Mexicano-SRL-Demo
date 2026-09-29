from fastapi import APIRouter, Depends, Query, status

from app.core.deps import SessionDep
from app.core.ratelimit import limitar
from app.models.enums import CanalVenta
from app.schemas.admin import ReembolsoIn, ReembolsoOut
from app.schemas.ventas import PagoIn, ReservaIn, ReservaOut
from app.services import reembolsos, reservas

# 40 solicitudes por minuto e IP: evita adivinar códigos de reserva o documentos.
router = APIRouter(tags=["Reservas y pasajes"], dependencies=[Depends(limitar("reservas", 40, 60))])

_DOCUMENTO = Query(description="Documento del comprador o de un pasajero (protege los datos de la reserva)")


@router.post(
    "/reservas",
    response_model=ReservaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Reservar asientos (queda pendiente de pago)",
    description=(
        "Bloquea los asientos por `reserva_expira_minutos` (15 por defecto). En línea solo se venden tarifas "
        "de adulto y embarazada; menores, adultos mayores y personas con discapacidad compran en boletería."
    ),
)
async def crear(session: SessionDep, datos: ReservaIn):
    venta = await reservas.crear_reserva(session, datos, canal=CanalVenta.web)
    return await reservas.a_respuesta(session, venta)


@router.get("/reservas/{codigo}", response_model=ReservaOut, summary="Consultar una reserva")
async def consultar(session: SessionDep, codigo: str, documento: str = _DOCUMENTO):
    venta = await reservas.obtener(session, codigo, documento=documento)
    return await reservas.a_respuesta(session, venta)


@router.post(
    "/reservas/{codigo}/pagar",
    response_model=ReservaOut,
    summary="Pagar una reserva (pago simulado)",
    description="QR, tarjeta de débito o crédito y Tigo Money. Una tarjeta terminada en 0002 simula un rechazo.",
)
async def pagar(session: SessionDep, codigo: str, datos: PagoIn):
    venta = await reservas.pagar(session, codigo, datos)
    return await reservas.a_respuesta(session, venta)


@router.post("/reservas/{codigo}/cancelar", response_model=ReservaOut, summary="Cancelar una reserva sin pagar")
async def cancelar(session: SessionDep, codigo: str, documento: str = _DOCUMENTO):
    venta = await reservas.cancelar(session, codigo, documento=documento)
    return await reservas.a_respuesta(session, venta)


@router.post(
    "/boletos/{numero_boleto}/reembolso",
    response_model=ReembolsoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Solicitar el reembolso de un boleto (85 %, hasta 2 h antes)",
)
async def reembolso(session: SessionDep, numero_boleto: str, datos: ReembolsoIn):
    r = await reembolsos.solicitar(session, numero_boleto, datos.motivo, documento=datos.documento)
    return (await reembolsos.con_detalle(session, [r]))[0]

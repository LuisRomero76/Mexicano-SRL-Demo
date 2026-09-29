from fastapi import APIRouter, Depends, Query, status

from app.core.deps import SessionDep
from app.core.ratelimit import limitar
from app.models.enums import CanalVenta, TipoEnvio
from app.schemas.carga import CotizacionOut, RastreoOut, SolicitudPuertaIn, SolicitudPuertaOut
from app.services import carga, puerta_a_puerta

# 60 solicitudes por minuto e IP: evita barridos de números de guía.
router = APIRouter(tags=["Carga y encomiendas"], dependencies=[Depends(limitar("carga", 60, 60))])


@router.get("/carga/cotizar", response_model=CotizacionOut, summary="Cotizar un envío")
async def cotizar(
    session: SessionDep,
    origen: str = Query(examples=["Sucre"]),
    destino: str = Query(examples=["Santa Cruz"]),
    peso_kg: float = Query(gt=0, examples=[12]),
    tipo: TipoEnvio | None = Query(None, description="Si se omite se deduce del peso"),
    puerta_a_puerta: bool = Query(False, description="Entrega a domicilio (solo Sucre y Santa Cruz)"),
):
    return await carga.cotizar(session, origen, destino, peso_kg, tipo, puerta_a_puerta)


@router.get(
    "/encomiendas/rastreo/{numero_guia}",
    response_model=RastreoOut,
    summary="Rastrear una encomienda (vista pública)",
    description="Muestra estado, ciudades, oficina de retiro e historial. Nunca nombres, teléfonos, montos ni PIN.",
)
async def rastrear(session: SessionDep, numero_guia: str):
    return await carga.rastreo_publico(session, numero_guia)


@router.post(
    "/puerta-a-puerta",
    response_model=SolicitudPuertaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Solicitar recojo o entrega a domicilio",
    description="Sucre y Santa Cruz, lunes a viernes hábiles. Entregas 08:00–12:00, recojos 14:00–17:00.",
)
async def solicitar_puerta(session: SessionDep, datos: SolicitudPuertaIn):
    solicitud = await puerta_a_puerta.crear(session, datos, canal=CanalVenta.web)
    return await puerta_a_puerta.a_respuesta(session, solicitud)

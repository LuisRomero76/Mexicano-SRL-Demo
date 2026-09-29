from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends

from app.core.deps import TODO_EL_PERSONAL, SessionDep, requiere_roles
from app.core.errors import ReglaNegocio
from app.models import Usuario
from app.models.enums import RolUsuario
from app.services import reportes
from app.utils.fechas import hoy

router = APIRouter(prefix="/reportes", tags=["Admin · Reportes"])
_supervisor = Depends(requiere_roles(RolUsuario.supervisor))


@router.get("/ventas", summary="Ventas por día, canal y método de pago")
async def ventas(
    session: SessionDep, desde: date | None = None, hasta: date | None = None, _: Usuario = _supervisor
) -> dict[str, Any]:
    hasta = hasta or hoy()
    desde = desde or hasta - timedelta(days=6)
    if desde > hasta:
        raise ReglaNegocio("«desde» debe ser anterior a «hasta».")
    return await reportes.ventas(session, desde, hasta)


@router.get("/ocupacion", summary="Ocupación de las salidas de un día")
async def ocupacion(session: SessionDep, fecha: date | None = None, _: Usuario = _supervisor) -> list[dict[str, Any]]:
    return await reportes.ocupacion(session, fecha or hoy())


@router.get("/encomiendas", summary="Encomiendas por estado y destino, y saldo por cobrar")
async def encomiendas(session: SessionDep, _: Usuario = _supervisor) -> dict[str, Any]:
    return await reportes.encomiendas(session)


@router.get("/resumen", summary="Resumen del tablero (KPIs, salidas de hoy, novedades)")
async def resumen(session: SessionDep, _: Usuario = Depends(requiere_roles(*TODO_EL_PERSONAL))) -> dict[str, Any]:
    return await reportes.resumen(session)

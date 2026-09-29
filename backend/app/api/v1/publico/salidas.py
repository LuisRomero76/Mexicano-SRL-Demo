import uuid
from datetime import date

from fastapi import APIRouter, Query

from app.core.deps import SessionDep
from app.schemas.ventas import BusquedaSalidasOut, CalendarioOut, SalidaDetalleOut, SalidaResumen
from app.services import salidas
from app.utils.fechas import a_local, fecha_legible, hoy

router = APIRouter(prefix="/salidas", tags=["Salidas y asientos"])


@router.get("", response_model=BusquedaSalidasOut, summary="Buscar salidas por origen, destino y fecha")
async def buscar(
    session: SessionDep,
    origen: str = Query(examples=["Sucre"], description="Nombre, código o alias de la ciudad"),
    destino: str = Query(examples=["Santa Cruz"]),
    fecha: date | None = Query(None, description="Por defecto, hoy"),
):
    fecha = fecha or hoy()
    ruta, lista = await salidas.buscar(session, origen, destino, fecha)
    vendibles = [s for s in lista if s["vendible"]]
    if vendibles:
        horas = ", ".join(f"{a_local(s['fecha_hora_salida']):%H:%M}" for s in vendibles)
        mensaje = (
            f"Hay {len(vendibles)} salida(s) de {ruta.origen.nombre} a {ruta.destino.nombre} el "
            f"{fecha_legible(fecha)}: {horas}."
        )
    else:
        mensaje = (
            f"No hay salidas disponibles de {ruta.origen.nombre} a {ruta.destino.nombre} el {fecha_legible(fecha)}."
        )
    return {
        "ruta": ruta.codigo,
        "origen": ruta.origen.nombre,
        "destino": ruta.destino.nombre,
        "fecha": fecha,
        "distancia_km": ruta.distancia_km,
        "duracion_estimada_min": ruta.duracion_estimada_min,
        "salidas": lista,
        "mensaje": mensaje,
    }


@router.get(
    "/calendario",
    response_model=CalendarioOut,
    summary="Disponibilidad y precio más bajo por día (franja de fechas)",
)
async def calendario(
    session: SessionDep,
    origen: str = Query(examples=["Sucre"]),
    destino: str = Query(examples=["Santa Cruz"]),
    desde: date | None = Query(None, description="Por defecto, hoy"),
    dias: int = Query(7, ge=1, le=31),
):
    ruta, lista = await salidas.calendario(session, origen, destino, desde or hoy(), dias)
    return {"ruta": ruta.codigo, "origen": ruta.origen.nombre, "destino": ruta.destino.nombre, "dias": lista}


@router.get(
    "/proximas",
    response_model=list[SalidaResumen],
    summary="Tablero de salidas: próximas salidas de todas las rutas",
)
async def proximas(session: SessionDep, limite: int = Query(10, ge=1, le=30)):
    return await salidas.proximas(session, limite)


@router.get("/{salida_id}", response_model=SalidaDetalleOut, summary="Detalle de una salida con mapa de asientos")
async def detalle(session: SessionDep, salida_id: uuid.UUID):
    mapa = await salidas.mapa_asientos(session, salida_id)
    return {
        "salida": await salidas.resumen_disponibilidad(session, salida_id),
        "precios": await salidas.precios_por_clase(session, mapa["salida"]),
        "asientos": mapa["asientos"],
    }

from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.core.deps import SessionDep
from app.schemas.catalogos import (
    CiudadOut,
    EmpresaOut,
    FeriadoOut,
    OficinaDetalleOut,
    OficinaOut,
    PoliticasOut,
    RutaOut,
    TipoAsientoOut,
)
from app.services import catalogos, parametros, precios
from app.utils.fechas import hoy

router = APIRouter(tags=["Catálogos"])


@router.get("/empresa", response_model=EmpresaOut, summary="Datos y contactos de la empresa")
async def empresa(session: SessionDep):
    return await catalogos.empresa(session)


@router.get("/ciudades", response_model=list[CiudadOut], summary="Ciudades donde opera la empresa")
async def ciudades(
    session: SessionDep,
    pasajeros: bool | None = Query(None, description="Solo destinos de pasajeros"),
    carga: bool | None = Query(None, description="Solo destinos de carga"),
):
    return await catalogos.listar_ciudades(session, pasajeros=pasajeros, carga=carga)


@router.get("/rutas", response_model=list[RutaOut], summary="Rutas de pasajeros con distancia, duración y paradas")
async def rutas(session: SessionDep):
    desde = await catalogos.precio_desde_por_ruta(session)
    horarios = await catalogos.horarios_por_ruta(session)
    return [
        {
            "id": r.id,
            "codigo": r.codigo,
            "origen": r.origen.nombre,
            "destino": r.destino.nombre,
            "distancia_km": r.distancia_km,
            "duracion_estimada_min": r.duracion_estimada_min,
            "duracion_texto": f"{r.duracion_estimada_min // 60} h"
            + (f" {r.duracion_estimada_min % 60} min" if r.duracion_estimada_min % 60 else ""),
            "cargo_exceso_equipaje_kg_bs": r.cargo_exceso_equipaje_kg_bs,
            "precio_desde_bs": desde.get(r.id),
            "horarios": horarios.get(r.id, []),
            "paradas": [
                {
                    "ciudad": p.ciudad.nombre,
                    "orden": p.orden,
                    "km_desde_origen": p.km_desde_origen,
                    "minutos_desde_origen": p.minutos_desde_origen,
                    "permite_pasajeros": p.permite_pasajeros,
                }
                for p in r.paradas
            ],
        }
        for r in await catalogos.listar_rutas(session)
    ]


@router.get("/tipos-asiento", response_model=list[TipoAsientoOut], summary="Clases de servicio y comodidades")
async def tipos_asiento(session: SessionDep):
    return await catalogos.listar_tipos_asiento(session)


@router.get("/oficinas", response_model=list[OficinaOut], summary="Boleterías y bodegas con horario")
async def oficinas(session: SessionDep, ciudad: str | None = Query(None, examples=["Santa Cruz"])):
    return await catalogos.listar_oficinas(session, ciudad)


@router.get("/oficinas/{codigo}", response_model=OficinaDetalleOut, summary="Detalle de una oficina")
async def oficina(session: SessionDep, codigo: str):
    return await catalogos.oficina_por_codigo(session, codigo)


@router.get(
    "/politicas",
    response_model=PoliticasOut,
    summary="Tarifas especiales, equipaje, reembolsos y otras políticas del viaje",
)
async def politicas(session: SessionDep):
    p = await parametros.todos(session)
    return {
        "tipos_pasajero": list((await precios.politicas(session)).values()),
        **{
            k: p[k]
            for k in (
                "equipaje_bodega_kg",
                "equipaje_mano_kg",
                "reembolso_porcentaje_cliente",
                "reembolso_horas_minimas",
                "reembolso_porcentaje_cancelacion_empresa",
                "reembolso_dias_habiles_max",
                "embarazo_semanas_max",
                "reserva_expira_minutos",
                "boletos_max_por_venta",
            )
        },
    }


@router.get("/feriados", response_model=list[FeriadoOut], summary="Feriados nacionales y departamentales")
async def feriados(
    session: SessionDep,
    desde: date | None = Query(None, description="Por defecto, hoy"),
    hasta: date | None = Query(None, description="Por defecto, 90 días después de «desde»"),
):
    desde = desde or hoy()
    return await catalogos.listar_feriados(session, desde, hasta or desde + timedelta(days=90))

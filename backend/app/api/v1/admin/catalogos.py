"""Administración de catálogos, personal, parámetros y auditoría."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete, func, or_, select

from app.api.v1.admin.crud import crud_router
from app.core.deps import TODO_EL_PERSONAL, PaginacionDep, SessionDep, requiere_roles
from app.core.errors import NoEncontrado, ReglaNegocio
from app.models import (
    Auditoria,
    BotConsultaLog,
    Bus,
    Cliente,
    CuentaCorporativa,
    Faq,
    Feriado,
    HorarioOficina,
    Oficina,
    PaginaContenido,
    ParametroNegocio,
    PlantillaHorario,
    Ruta,
    TarifaCarga,
    TarifaPasaje,
    Usuario,
    VehiculoCarga,
)
from app.models.enums import RolUsuario
from app.schemas.admin import (
    AuditoriaOut,
    BotConsultaOut,
    BusIn,
    BusOut,
    BusUpdate,
    ClienteOut,
    CuentaCorporativaIn,
    CuentaCorporativaOut,
    CuentaCorporativaUpdate,
    DirectorioOut,
    FaqAdminOut,
    FaqIn,
    FaqUpdate,
    FeriadoIn,
    HorarioIn,
    OficinaAdminOut,
    OficinaIn,
    OficinaUpdate,
    PaginaUpdate,
    ParametroOut,
    ParametroUpdate,
    PlantillaIn,
    PlantillaOut,
    PlantillaUpdate,
    RutaAdminOut,
    RutaUpdate,
    TarifaCargaIn,
    TarifaCargaOut,
    TarifaCargaUpdate,
    TarifaPasajeIn,
    TarifaPasajeOut,
    TarifaPasajeUpdate,
    UsuarioIn,
    UsuarioOut,
    UsuarioUpdate,
    VehiculoIn,
    VehiculoOut,
    VehiculoUpdate,
)
from app.schemas.catalogos import FeriadoOut, HorarioOut, PaginaOut
from app.schemas.common import Pagina
from app.services import auditoria, crud, flota, usuarios

R = RolUsuario
router = APIRouter(tags=["Admin · Catálogos"])
_supervisor = Depends(requiere_roles(R.supervisor))
_admin = Depends(requiere_roles())  # solo admin

# --- CRUD genéricos ----------------------------------------------------------------------------

for sub in (
    crud_router(
        modelo=Oficina,
        prefijo="/oficinas",
        nombre="oficinas",
        salida=OficinaAdminOut,
        entrada=OficinaIn,
        cambios=OficinaUpdate,
        filtros=("ciudad_id", "tipo", "activo"),
    ),
    crud_router(
        modelo=VehiculoCarga,
        prefijo="/vehiculos-carga",
        nombre="vehículos de carga",
        salida=VehiculoOut,
        entrada=VehiculoIn,
        cambios=VehiculoUpdate,
        filtros=("tipo", "ciudad_base_id"),
        roles_lectura=(R.supervisor, R.encargado_bodega, R.repartidor),
    ),
    crud_router(
        modelo=Ruta,
        prefijo="/rutas",
        nombre="rutas",
        salida=RutaAdminOut,
        cambios=RutaUpdate,
    ),
    crud_router(
        modelo=PlantillaHorario,
        prefijo="/plantillas-horario",
        nombre="plantillas de horario",
        salida=PlantillaOut,
        entrada=PlantillaIn,
        cambios=PlantillaUpdate,
        filtros=("ruta_id", "activo"),
    ),
    crud_router(
        modelo=TarifaPasaje,
        prefijo="/tarifas-pasaje",
        nombre="tarifas de pasaje",
        salida=TarifaPasajeOut,
        entrada=TarifaPasajeIn,
        cambios=TarifaPasajeUpdate,
        filtros=("ruta_id", "tipo_asiento_id"),
        roles_lectura=(R.supervisor, R.boletero),
    ),
    crud_router(
        modelo=TarifaCarga,
        prefijo="/tarifas-carga",
        nombre="tarifas de carga",
        salida=TarifaCargaOut,
        entrada=TarifaCargaIn,
        cambios=TarifaCargaUpdate,
        filtros=("origen_ciudad_id", "destino_ciudad_id", "tipo_envio"),
        roles_lectura=(R.supervisor, R.encargado_bodega),
    ),
    crud_router(
        modelo=Faq,
        prefijo="/faqs",
        nombre="preguntas frecuentes",
        salida=FaqAdminOut,
        entrada=FaqIn,
        cambios=FaqUpdate,
        filtros=("categoria_id", "activo"),
        roles=(R.supervisor, R.soporte),
    ),
    crud_router(
        modelo=CuentaCorporativa,
        prefijo="/cuentas-corporativas",
        nombre="cuentas corporativas",
        salida=CuentaCorporativaOut,
        entrada=CuentaCorporativaIn,
        cambios=CuentaCorporativaUpdate,
        pk=uuid.UUID,
        filtros=("activo",),
        roles_lectura=(R.supervisor, R.encargado_bodega),
    ),
    crud_router(
        modelo=ParametroNegocio,
        prefijo="/parametros",
        nombre="parámetros de negocio",
        salida=ParametroOut,
        cambios=ParametroUpdate,
        pk=str,
        roles=(),
    ),
):
    router.include_router(sub)


# --- Oficinas: horarios ------------------------------------------------------------------------


@router.put(
    "/oficinas/{oficina_id}/horarios",
    response_model=list[HorarioOut],
    summary="Reemplazar el horario de atención de una oficina",
)
async def reemplazar_horarios(
    session: SessionDep, oficina_id: int, horarios: list[HorarioIn], usuario: Usuario = _supervisor
):
    if not await session.get(Oficina, oficina_id):
        raise NoEncontrado("No existe esa oficina.")
    for h in horarios:
        if h.hora_cierre <= h.hora_apertura:
            raise ReglaNegocio(f"Horario inválido el día {h.dia_semana}: el cierre debe ser posterior a la apertura.")
    await session.execute(delete(HorarioOficina).where(HorarioOficina.oficina_id == oficina_id))
    session.add_all(HorarioOficina(oficina_id=oficina_id, **h.model_dump()) for h in horarios)
    auditoria.registrar(
        session, usuario, "oficinas.horarios", "oficinas", oficina_id, {"horarios": [h.model_dump() for h in horarios]}
    )
    await session.commit()
    return (
        await session.scalars(
            select(HorarioOficina).where(HorarioOficina.oficina_id == oficina_id).order_by(HorarioOficina.dia_semana)
        )
    ).all()


# --- Buses -------------------------------------------------------------------------------------


@router.get("/buses", response_model=list[BusOut], summary="Listar buses")
async def listar_buses(session: SessionDep, _: Usuario = Depends(requiere_roles(R.supervisor, R.boletero))):
    return (await session.scalars(select(Bus).order_by(Bus.numero_interno))).all()


@router.post(
    "/buses",
    response_model=BusOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un bus (crea su mapa de 48 asientos)",
)
async def crear_bus(session: SessionDep, datos: BusIn, usuario: Usuario = _supervisor):
    return await flota.crear_bus(session, datos, usuario)


@router.patch("/buses/{bus_id}", response_model=BusOut, summary="Modificar un bus (estado, datos)")
async def actualizar_bus(session: SessionDep, bus_id: int, datos: BusUpdate, usuario: Usuario = _supervisor):
    return await crud.actualizar(session, Bus, bus_id, datos.model_dump(exclude_unset=True), usuario)


# --- Feriados y páginas ------------------------------------------------------------------------


@router.get("/feriados", response_model=list[FeriadoOut], summary="Listar feriados")
async def feriados(
    session: SessionDep,
    desde: date | None = None,
    hasta: date | None = None,
    _: Usuario = Depends(requiere_roles(R.supervisor, R.encargado_bodega, R.repartidor, R.soporte)),
):
    q = select(Feriado).order_by(Feriado.fecha)
    if desde:
        q = q.where(Feriado.fecha >= desde)
    if hasta:
        q = q.where(Feriado.fecha <= hasta)
    return (await session.scalars(q)).all()


@router.post("/feriados", response_model=FeriadoOut, status_code=status.HTTP_201_CREATED, summary="Agregar feriado")
async def crear_feriado(session: SessionDep, datos: FeriadoIn, usuario: Usuario = _supervisor):
    return await crud.crear(session, Feriado, datos.model_dump(), usuario)


@router.delete("/feriados/{feriado_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar feriado")
async def eliminar_feriado(session: SessionDep, feriado_id: int, usuario: Usuario = _supervisor):
    feriado = await crud.obtener(session, Feriado, feriado_id)
    await session.delete(feriado)
    auditoria.registrar(session, usuario, "feriados.eliminar", "feriados", feriado_id, {"fecha": feriado.fecha})
    await session.commit()


@router.put("/paginas/{slug}", response_model=PaginaOut, summary="Editar una página de contenido")
async def editar_pagina(
    session: SessionDep,
    slug: str,
    datos: PaginaUpdate,
    usuario: Usuario = Depends(requiere_roles(R.supervisor, R.soporte)),
):
    pagina_id = await session.scalar(select(PaginaContenido.id).where(PaginaContenido.slug == slug))
    if not pagina_id:
        raise NoEncontrado(f"No existe la página «{slug}».")
    return await crud.actualizar(session, PaginaContenido, pagina_id, datos.model_dump(exclude_unset=True), usuario)


# --- Personal ----------------------------------------------------------------------------------


@router.get(
    "/usuarios/directorio",
    response_model=list[DirectorioOut],
    summary="Personal activo (nombre y rol) para asignar tripulación o repartidores",
)
async def directorio(
    session: SessionDep,
    rol: RolUsuario | None = None,
    _: Usuario = Depends(requiere_roles(*TODO_EL_PERSONAL)),
):
    q = select(Usuario).where(Usuario.activo).order_by(Usuario.apellidos, Usuario.nombres)
    if rol:
        q = q.where(Usuario.rol == rol)
    return [
        {
            "id": u.id,
            "nombre": u.nombre_completo,
            "rol": u.rol,
            "oficina_id": u.oficina_id,
            "licencia_conducir": u.licencia_conducir,
        }
        for u in (await session.scalars(q)).all()
    ]


@router.get("/usuarios", response_model=Pagina[UsuarioOut], summary="Listar personal")
async def listar_usuarios(
    session: SessionDep, pag: PaginacionDep, rol: RolUsuario | None = None, _: Usuario = _supervisor
):
    total, items = await crud.listar(session, Usuario, filtros={"rol": rol}, limit=pag.limit, offset=pag.offset)
    return {"total": total, "limit": pag.limit, "offset": pag.offset, "items": items}


@router.post("/usuarios", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED, summary="Crear usuario")
async def crear_usuario(session: SessionDep, datos: UsuarioIn, usuario: Usuario = _admin):
    return await usuarios.crear(session, datos, usuario)


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioOut, summary="Modificar usuario")
async def actualizar_usuario(
    session: SessionDep, usuario_id: uuid.UUID, datos: UsuarioUpdate, usuario: Usuario = _admin
):
    return await usuarios.actualizar(session, usuario_id, datos, usuario)


# --- Clientes y auditoría ----------------------------------------------------------------------


@router.get("/clientes", response_model=Pagina[ClienteOut], summary="Buscar clientes")
async def buscar_clientes(
    session: SessionDep,
    pag: PaginacionDep,
    q: str | None = Query(None, description="Documento, teléfono o nombre"),
    _: Usuario = Depends(requiere_roles(R.supervisor, R.boletero, R.encargado_bodega, R.soporte)),
):
    consulta = select(Cliente)
    if q:
        patron = f"%{q.strip()}%"
        consulta = consulta.where(
            or_(
                Cliente.numero_documento.ilike(patron),
                Cliente.telefono_e164.ilike(patron),
                (Cliente.nombres + " " + Cliente.apellidos).ilike(patron),
            )
        )
    total = await session.scalar(select(func.count()).select_from(consulta.subquery()))
    items = (
        await session.scalars(consulta.order_by(Cliente.apellidos, Cliente.nombres).limit(pag.limit).offset(pag.offset))
    ).all()
    return {"total": total or 0, "limit": pag.limit, "offset": pag.offset, "items": items}


@router.get("/auditoria", response_model=Pagina[AuditoriaOut], summary="Registro de auditoría (más reciente primero)")
async def listar_auditoria(
    session: SessionDep,
    pag: PaginacionDep,
    tabla: str | None = None,
    registro_id: str | None = None,
    _: Usuario = _supervisor,
):
    q = select(Auditoria)
    if tabla:
        q = q.where(Auditoria.tabla == tabla)
    if registro_id:
        q = q.where(Auditoria.registro_id == registro_id)
    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    items = (await session.scalars(q.order_by(Auditoria.id.desc()).limit(pag.limit).offset(pag.offset))).all()
    ids = {a.usuario_id for a in items if a.usuario_id}
    nombres = (
        {u.id: u.nombre_completo for u in (await session.scalars(select(Usuario).where(Usuario.id.in_(ids)))).all()}
        if ids
        else {}
    )
    filas = [AuditoriaOut.model_validate(a).model_copy(update={"usuario": nombres.get(a.usuario_id)}) for a in items]
    return {"total": total or 0, "limit": pag.limit, "offset": pag.offset, "items": filas}


@router.get("/auditoria/tablas", response_model=list[str], summary="Tablas con registros de auditoría")
async def tablas_auditoria(session: SessionDep, _: Usuario = _supervisor):
    return (await session.scalars(select(Auditoria.tabla).distinct().order_by(Auditoria.tabla))).all()


@router.get(
    "/bot/consultas",
    response_model=Pagina[BotConsultaOut],
    summary="Consultas del agente de voz (más reciente primero)",
)
async def consultas_bot(
    session: SessionDep,
    pag: PaginacionDep,
    tool: str | None = None,
    encontrado: bool | None = None,
    _: Usuario = _supervisor,
):
    q = select(BotConsultaLog)
    if tool:
        q = q.where(BotConsultaLog.tool == tool)
    if encontrado is not None:
        q = q.where(BotConsultaLog.encontrado == encontrado)
    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    items = (await session.scalars(q.order_by(BotConsultaLog.id.desc()).limit(pag.limit).offset(pag.offset))).all()
    return {"total": total or 0, "limit": pag.limit, "offset": pag.offset, "items": items}

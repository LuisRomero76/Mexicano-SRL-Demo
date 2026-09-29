"""Fábrica de routers CRUD para catálogos simples."""

from typing import Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel

from app.core.deps import PaginacionDep, SessionDep, requiere_roles
from app.core.errors import ReglaNegocio
from app.models import Usuario
from app.models.enums import RolUsuario
from app.schemas.common import Pagina
from app.services import crud


def _convertir(tipo: type, crudo: str) -> Any:
    if tipo is bool:
        if crudo.lower() not in ("true", "false", "1", "0"):
            raise ValueError
        return crudo.lower() in ("true", "1")
    return tipo(crudo)


def crud_router(
    *,
    modelo: Any,
    prefijo: str,
    nombre: str,
    salida: type[BaseModel],
    entrada: type[BaseModel] | None = None,
    cambios: type[BaseModel] | None = None,
    pk: type = int,
    filtros: tuple[str, ...] = (),
    roles: tuple[RolUsuario, ...] = (RolUsuario.supervisor,),
    roles_lectura: tuple[RolUsuario, ...] | None = None,
) -> APIRouter:
    router = APIRouter(prefix=prefijo)
    lectura = Depends(requiere_roles(*(roles_lectura or roles)))
    escritura = Depends(requiere_roles(*roles))
    tipos = {f: modelo.__table__.c[f].type.python_type for f in filtros}
    doc_filtros = {
        "parameters": [
            {
                "name": f,
                "in": "query",
                "required": False,
                "schema": {"type": "string"},
                "description": f"Filtrar por {f}",
            }
            for f in filtros
        ]
    }

    @router.get("", response_model=Pagina[salida], summary=f"Listar {nombre}", openapi_extra=doc_filtros)
    async def listar(request: Request, session: SessionDep, pag: PaginacionDep, _: Usuario = lectura):
        valores = {}
        for campo, tipo in tipos.items():
            crudo = request.query_params.get(campo)
            if crudo is None:
                continue
            try:
                valores[campo] = _convertir(tipo, crudo)
            except ValueError as exc:
                raise ReglaNegocio(f"Valor inválido para el filtro «{campo}»: {crudo}") from exc
        total, items = await crud.listar(session, modelo, filtros=valores, limit=pag.limit, offset=pag.offset)
        return {"total": total, "limit": pag.limit, "offset": pag.offset, "items": items}

    @router.get("/{item_id}", response_model=salida, summary=f"Obtener {nombre}")
    async def obtener(session: SessionDep, item_id: pk, _: Usuario = lectura):  # type: ignore[valid-type]
        return await crud.obtener(session, modelo, item_id)

    if entrada is not None:

        @router.post("", response_model=salida, status_code=status.HTTP_201_CREATED, summary=f"Crear {nombre}")
        async def crear(session: SessionDep, datos: entrada, usuario: Usuario = escritura):  # type: ignore[valid-type]
            return await crud.crear(session, modelo, datos.model_dump(), usuario)

    if cambios is not None:

        @router.patch("/{item_id}", response_model=salida, summary=f"Modificar {nombre}")
        async def actualizar(
            session: SessionDep,
            item_id: pk,  # type: ignore[valid-type]
            datos: cambios,  # type: ignore[valid-type]
            usuario: Usuario = escritura,
        ):
            return await crud.actualizar(session, modelo, item_id, datos.model_dump(exclude_unset=True), usuario)

    return router

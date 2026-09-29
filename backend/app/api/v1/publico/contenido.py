from fastapi import APIRouter, Query

from app.core.deps import SessionDep
from app.schemas.catalogos import FaqBusquedaOut, FaqCategoriaOut, PaginaOut
from app.services import contenido

router = APIRouter(tags=["Centro de ayuda"])


@router.get("/faqs", response_model=list[FaqCategoriaOut], summary="Preguntas frecuentes por categoría")
async def faqs(session: SessionDep, categoria: str | None = Query(None, examples=["pasajeros"])):
    return [
        {"id": c.id, "codigo": c.codigo, "nombre": c.nombre, "preguntas": preguntas}
        for c, preguntas in await contenido.listar_faqs(session, categoria)
    ]


@router.get("/faqs/buscar", response_model=FaqBusquedaOut, summary="Buscar en las preguntas frecuentes")
async def buscar(session: SessionDep, q: str = Query(min_length=2, examples=["puedo llevar a mi perro"])):
    resultados = await contenido.buscar_faqs(session, q)
    mensaje = (
        resultados[0].respuesta_corta_voz or resultados[0].respuesta
        if resultados
        else "No encontré una respuesta. Escríbenos por WhatsApp al +591 71420823."
    )
    return {"consulta": q, "resultados": resultados, "mensaje": mensaje}


@router.get("/paginas", response_model=list[PaginaOut], summary="Páginas de contenido del sitio")
async def paginas(session: SessionDep):
    return await contenido.listar_paginas(session)


@router.get("/paginas/{slug}", response_model=PaginaOut, summary="Una página de contenido")
async def pagina(session: SessionDep, slug: str):
    return await contenido.pagina(session, slug)

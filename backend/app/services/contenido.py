"""Centro de ayuda (FAQ) y páginas de contenido del sitio."""

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NoEncontrado
from app.models import Faq, FaqCategoria, PaginaContenido
from app.utils.texto import normalizar

_DOCUMENTO = func.to_tsvector(literal_column("'spanish'"), Faq.pregunta + " " + Faq.respuesta)


async def listar_faqs(session: AsyncSession, categoria: str | None = None) -> list[tuple[FaqCategoria, list[Faq]]]:
    """Categorías con sus preguntas activas (sin modificar la relación del ORM)."""
    q = select(FaqCategoria).options(selectinload(FaqCategoria.faqs)).order_by(FaqCategoria.orden)
    if categoria:
        q = q.where(FaqCategoria.codigo == categoria)
    return [(c, [f for f in c.faqs if f.activo]) for c in (await session.scalars(q)).all()]


async def buscar_faqs(session: AsyncSession, texto: str, limite: int = 3) -> list[Faq]:
    """Full-text en español; si no hay resultados, busca en palabras clave sin tildes."""
    consulta = func.websearch_to_tsquery(literal_column("'spanish'"), texto)
    rango = func.ts_rank(_DOCUMENTO, consulta)
    filas = (
        await session.scalars(
            select(Faq)
            .where(Faq.activo, _DOCUMENTO.op("@@")(consulta))
            .options(selectinload(Faq.categoria))
            .order_by(rango.desc(), Faq.orden)
            .limit(limite)
        )
    ).all()
    if filas:
        return list(filas)

    terminos = [t for t in normalizar(texto).split() if len(t) > 3]
    if not terminos:
        return []
    todas = (await session.scalars(select(Faq).where(Faq.activo).options(selectinload(Faq.categoria)))).all()
    puntaje = []
    for f in todas:
        claves = " ".join(normalizar(k) for k in (f.palabras_clave or [])) + " " + normalizar(f.pregunta)
        n = sum(1 for t in terminos if t[:5] in claves)
        if n:
            puntaje.append((n, f))
    puntaje.sort(key=lambda x: (-x[0], x[1].orden))
    return [f for _, f in puntaje[:limite]]


async def faq_por_slug(session: AsyncSession, slug: str) -> Faq:
    faq = await session.scalar(select(Faq).where(Faq.slug == slug).options(selectinload(Faq.categoria)))
    if not faq:
        raise NoEncontrado("No existe esa pregunta.")
    return faq


async def pagina(session: AsyncSession, slug: str) -> PaginaContenido:
    fila = await session.scalar(select(PaginaContenido).where(PaginaContenido.slug == slug))
    if not fila:
        raise NoEncontrado(f"No existe la página «{slug}».")
    return fila


async def listar_paginas(session: AsyncSession) -> list[PaginaContenido]:
    return list((await session.scalars(select(PaginaContenido).order_by(PaginaContenido.id))).all())

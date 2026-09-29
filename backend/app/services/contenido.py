"""Centro de ayuda (FAQ) y páginas de contenido del sitio."""

import re

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


# Palabras frecuentes en una pregunta que no dicen de qué trata.
_VACIAS = {"quiero", "puedo", "puede", "como", "donde", "cuando", "cuanto", "tengo", "hacer", "esta", "para", "pasa"}


def _terminos(texto: str) -> list[str]:
    """Palabras con significado del texto, sin tildes."""
    return [t for t in normalizar(texto).split() if len(t) > 3 and t not in _VACIAS]


def _coincide(termino: str, palabra: str) -> bool:
    # Palabras largas por su raíz ("equipaje" ~ "equipajes"); las de 4 letras, completas ("pasa" ≠ "pasaje").
    return palabra.startswith(termino[:5]) if len(termino) >= 5 else palabra == termino


def _puntaje(terminos: list[str], textos: list[str]) -> int:
    palabras = normalizar(" ".join(textos)).split()
    return sum(1 for t in terminos if any(_coincide(t, p) for p in palabras))


async def buscar_faqs(session: AsyncSession, texto: str, limite: int = 3) -> list[Faq]:
    """Primero por las palabras clave curadas de cada pregunta; si ninguna coincide, full-text en español
    y, como último recurso, coincidencias en el título de la pregunta."""
    terminos = _terminos(texto)
    todas = (await session.scalars(select(Faq).where(Faq.activo).options(selectinload(Faq.categoria)))).all()
    por_clave = [(n, f) for f in todas if (n := _puntaje(terminos, list(f.palabras_clave or [])))]
    if por_clave:
        # Empates: gana la que más menciona los términos en su texto (ranking full-text con OR).
        limpios = [re.sub(r"[^a-z0-9ñ]", "", t) for t in terminos]
        consulta_o = " | ".join(t for t in limpios if t)
        rangos: dict[int, float] = {}
        if consulta_o:
            filas_rango = await session.execute(
                select(
                    Faq.id, func.ts_rank(_DOCUMENTO, func.to_tsquery(literal_column("'spanish'"), consulta_o))
                ).where(Faq.id.in_([f.id for _, f in por_clave]))
            )
            rangos = {fid: rango for fid, rango in filas_rango.all()}
        por_clave.sort(key=lambda x: (-x[0], -rangos.get(x[1].id, 0), x[1].orden))
        return [f for _, f in por_clave[:limite]]

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

    por_titulo = [(n, f) for f in todas if (n := _puntaje(terminos, [f.pregunta]))]
    por_titulo.sort(key=lambda x: (-x[0], x[1].orden))
    return [f for _, f in por_titulo[:limite]]


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

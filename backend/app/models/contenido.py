"""Módulo G — Centro de ayuda y contenido."""

from sqlalchemy import ForeignKey, Index, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FaqCategoria(TimestampMixin, Base):
    __tablename__ = "faq_categorias"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(60))
    orden: Mapped[int] = mapped_column(SmallInteger, server_default="0")

    faqs: Mapped[list["Faq"]] = relationship(back_populates="categoria", order_by="Faq.orden")


class Faq(TimestampMixin, Base):
    __tablename__ = "faqs"
    __table_args__ = (
        Index(
            "ix_faqs_fts",
            text("to_tsvector('spanish', pregunta || ' ' || respuesta)"),
            postgresql_using="gin",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("faq_categorias.id"))
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    pregunta: Mapped[str] = mapped_column(String(200))
    respuesta: Mapped[str] = mapped_column(Text)
    respuesta_corta_voz: Mapped[str | None] = mapped_column(String(400))
    palabras_clave: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    orden: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))
    activo: Mapped[bool] = mapped_column(server_default=text("true"))

    categoria: Mapped[FaqCategoria] = relationship(back_populates="faqs")


class PaginaContenido(TimestampMixin, Base):
    __tablename__ = "paginas_contenido"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    titulo: Mapped[str] = mapped_column(String(150))
    meta_descripcion: Mapped[str | None] = mapped_column(String(300))
    contenido_md: Mapped[str] = mapped_column(Text)
    url_original: Mapped[str | None] = mapped_column(String(300))

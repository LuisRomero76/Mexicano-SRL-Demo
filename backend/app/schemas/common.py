"""Tipos comunes de los esquemas: montos, fechas en hora de Bolivia y paginación."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

from app.utils.fechas import a_local

# Montos en Bs: se envían como número con 2 decimales.
Monto = Annotated[
    Decimal,
    PlainSerializer(
        lambda v: float(Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        return_type=float,
        when_used="json",
    ),
]

# Fechas y horas: siempre en America/La_Paz (-04:00).
FechaHora = Annotated[
    datetime,
    PlainSerializer(lambda v: a_local(v).isoformat(), return_type=str, when_used="json"),
]


class Esquema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Pagina[T](BaseModel):
    total: int
    limit: int
    offset: int
    items: list[T]


class Mensaje(BaseModel):
    mensaje: str

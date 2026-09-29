"""Fechas en la zona horaria de negocio (America/La_Paz, UTC-4 sin horario de verano)."""

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/La_Paz")

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def ahora() -> datetime:
    return datetime.now(TZ)


def hoy() -> date:
    return ahora().date()


def a_local(dt: datetime) -> datetime:
    return dt.astimezone(TZ)


def combinar(fecha: date, hora: time) -> datetime:
    return datetime.combine(fecha, hora, tzinfo=TZ)


def inicio_y_fin_del_dia(fecha: date) -> tuple[datetime, datetime]:
    inicio = combinar(fecha, time.min)
    return inicio, inicio + timedelta(days=1)


def es_dia_habil(fecha: date, feriados: Iterable[date] = ()) -> bool:
    return fecha.isoweekday() <= 5 and fecha not in set(feriados)


def sumar_dias_habiles(fecha: date, dias: int, feriados: Iterable[date] = ()) -> date:
    feriados = set(feriados)
    actual = fecha
    while dias > 0:
        actual += timedelta(days=1)
        if es_dia_habil(actual, feriados):
            dias -= 1
    return actual


def fecha_legible(dt: datetime | date) -> str:
    """'martes 30 de septiembre, 20:00' (hora local)."""
    if isinstance(dt, datetime):
        dt = a_local(dt)
        base = f"{DIAS_SEMANA[dt.weekday()]} {dt.day} de {MESES[dt.month - 1]}"
        return f"{base}, {dt:%H:%M}"
    return f"{DIAS_SEMANA[dt.weekday()]} {dt.day} de {MESES[dt.month - 1]}"


def edad_en(fecha_nacimiento: date, fecha: date) -> int:
    return (
        fecha.year - fecha_nacimiento.year - ((fecha.month, fecha.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
    )

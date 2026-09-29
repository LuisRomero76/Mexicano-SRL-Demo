"""Límite de intentos en memoria (ventana deslizante) para endpoints sensibles.

Protege contra fuerza bruta (login) y enumeración (reservas por código, guías). Es por proceso:
con varias réplicas conviene reemplazarlo por uno compartido (Redis) o por el del proxy.
"""

import time
from collections import deque
from collections.abc import Callable

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import DemasiadosIntentos


class Limitador:
    def __init__(self) -> None:
        self._golpes: dict[str, deque[float]] = {}

    def registrar(self, clave: str, maximo: int, ventana: float) -> int:
        """Devuelve 0 si se permite; si no, los segundos que faltan para reintentar."""
        ahora = time.monotonic()
        cola = self._golpes.setdefault(clave, deque())
        while cola and cola[0] <= ahora - ventana:
            cola.popleft()
        if len(cola) >= maximo:
            return int(cola[0] + ventana - ahora) + 1
        cola.append(ahora)
        if len(self._golpes) > 50_000:  # evita crecer sin límite
            self._golpes = {k: v for k, v in self._golpes.items() if v}
        return 0

    def reiniciar(self) -> None:
        self._golpes.clear()


limitador = Limitador()


def ip_cliente(request: Request) -> str:
    if get_settings().trust_proxy_headers:
        reenviada = request.headers.get("x-forwarded-for")
        if reenviada:
            return reenviada.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"


def limitar(nombre: str, maximo: int, ventana_segundos: float) -> Callable:
    """Dependencia de FastAPI: `Depends(limitar("login", 10, 300))`."""

    async def _dependencia(request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return
        espera = limitador.registrar(f"{nombre}:{ip_cliente(request)}", maximo, ventana_segundos)
        if espera:
            raise DemasiadosIntentos(
                f"Demasiados intentos. Vuelve a intentar en {espera} segundos.",
                detalle={"reintentar_en_segundos": espera},
            )

    return _dependencia

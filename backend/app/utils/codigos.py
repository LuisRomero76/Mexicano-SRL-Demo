"""Códigos legibles y fáciles de dictar."""

import secrets

# Sin 0/O, 1/I/L para evitar confusiones al leer o dictar.
ALFABETO_DICTABLE = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generar_codigo_reserva(largo: int = 6) -> str:
    return "".join(secrets.choice(ALFABETO_DICTABLE) for _ in range(largo))


def generar_pin(largo: int = 4) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(largo))


def normalizar_codigo_reserva(valor: str) -> str:
    """Tolera minúsculas, espacios y guiones: 'mx7-k2p' -> 'MX7K2P'."""
    return "".join(c for c in valor.upper() if c.isalnum())


def formato_numero_boleto(n: int) -> str:
    return f"B{n}"


def formato_solicitud_puerta(n: int) -> str:
    return f"PP-{n:06d}"

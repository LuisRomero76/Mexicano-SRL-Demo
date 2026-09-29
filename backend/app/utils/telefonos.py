"""Teléfonos en formato E.164 guardado como solo dígitos (ej. 59168779945)."""

import re

CODIGO_BOLIVIA = "591"


def normalizar_e164(valor: str | None, codigo_pais: str = CODIGO_BOLIVIA) -> str | None:
    """Devuelve solo dígitos con código de país, o None si no parece un teléfono.

    Acepta '+591 687-79945', '0059168779945', '68779945' (asume Bolivia), 'whatsapp:+591...'.
    """
    if not valor:
        return None
    digitos = re.sub(r"\D", "", valor)
    if digitos.startswith("00"):
        digitos = digitos[2:]
    if len(digitos) == 8 and codigo_pais == CODIGO_BOLIVIA:
        digitos = codigo_pais + digitos
    if not 10 <= len(digitos) <= 15:
        return None
    return digitos


def formato_legible(e164: str | None) -> str | None:
    """'59168779945' -> '+591 68779945'."""
    if not e164:
        return None
    if e164.startswith(CODIGO_BOLIVIA):
        return f"+{CODIGO_BOLIVIA} {e164[3:]}"
    return f"+{e164}"


def url_whatsapp(e164: str | None) -> str | None:
    return f"https://wa.me/{e164}" if e164 else None

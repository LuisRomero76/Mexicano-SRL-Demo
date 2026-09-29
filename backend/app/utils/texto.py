import re
import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios simples: '  Potosí ' -> 'potosi'."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


def slugify(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalizar(texto)).strip("-")

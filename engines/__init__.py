from __future__ import annotations

from engines.base import GenericCorrectionEngine, TextCorrectionEngine
from engines.registry import (
    available_genre_ids,
    get_engine,
    list_engines,
    register_engine,
)

# Registro de motores por genero. Agrega un archivo nuevo e importalo aqui.
register_engine(GenericCorrectionEngine())

from engines import periodismo as _periodismo  # noqa: E402,F401
from engines import nota_informativa as _nota_informativa  # noqa: E402,F401

__all__ = [
    "TextCorrectionEngine",
    "available_genre_ids",
    "get_engine",
    "list_engines",
    "register_engine",
]

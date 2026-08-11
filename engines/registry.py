from __future__ import annotations

from engines.base import TextCorrectionEngine


_ENGINES: dict[str, TextCorrectionEngine] = {}


def register_engine(engine: TextCorrectionEngine) -> TextCorrectionEngine:
    if not engine.id:
        raise ValueError("El motor necesita un id.")
    _ENGINES[engine.id] = engine
    return engine


def get_engine(genre: str) -> TextCorrectionEngine:
    key = (genre or "generico").strip().lower()
    if key not in _ENGINES:
        available = ", ".join(sorted(_ENGINES)) or "(ninguno)"
        raise ValueError(f"Genero desconocido: {genre!r}. Disponibles: {available}")
    return _ENGINES[key]


def list_engines() -> list[TextCorrectionEngine]:
    return [engine for _, engine in sorted(_ENGINES.items())]


def available_genre_ids() -> list[str]:
    return sorted(_ENGINES)

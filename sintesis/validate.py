from __future__ import annotations

import unicodedata
from datetime import date, datetime

from .errors import ApiError

MEDIUM_LABELS = {
    "radio": "Radio",
    "tv": "TV",
    "prensa": "Prensa",
    "portal": "Portal",
}

_MEDIUM_ALIASES = {
    "radio": "radio",
    "tv": "tv",
    "television": "tv",
    "prensa": "prensa",
    "impreso": "prensa",
    "impresos": "prensa",
    "periodico": "prensa",
    "diario": "prensa",
    "portal": "portal",
    "web": "portal",
    "digital": "portal",
    "internet": "portal",
}


def fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value.casefold())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.split())


def clean_text(value: object, max_len: int, *, allow_empty: bool = True) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\x00", "")
    text = "".join(ch for ch in text if ch in "\n\t" or ch >= " ")
    text = text.strip()
    if not allow_empty and not text:
        raise ApiError("Falta un dato obligatorio.")
    return text[:max_len]


def parse_date(value: object) -> date:
    text = clean_text(value, 10, allow_empty=False)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ApiError("La fecha debe ir como AAAA-MM-DD.") from exc


def parse_medium(value: object) -> str:
    key = fold(clean_text(value, 40, allow_empty=False)).replace(" ", "")
    medium = _MEDIUM_ALIASES.get(key)
    if not medium:
        raise ApiError("El medio debe ser radio, tv, prensa o portal.")
    return medium


def valid_email(value: str) -> bool:
    if len(value) > 254 or value.count("@") != 1 or any(ch.isspace() for ch in value):
        return False
    local, domain = value.split("@", 1)
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def contains_phrase(haystack: str, phrase: str) -> bool:
    needle = fold(phrase)
    if len(needle) < 3:
        return False
    return needle in fold(haystack)


def normalize_phrase(value: object) -> str:
    phrase = clean_text(value, 120, allow_empty=False)
    if len(fold(phrase)) < 3:
        raise ApiError("La palabra clave debe tener al menos 3 letras.")
    return phrase


def safe_http_url(value: str) -> str:
    text = value.strip()
    if text.startswith("https://") or text.startswith("http://"):
        return text
    return ""

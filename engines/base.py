from __future__ import annotations

import re
from abc import ABC, abstractmethod


class TextCorrectionEngine(ABC):
    """Motor de correccion de texto propio de un genero editorial."""

    id: str
    label: str
    description: str = ""

    def correct_block(self, text: str) -> str:
        """Corrige un bloque/parrafo ya extraido."""
        return self.correct_document(text)

    @abstractmethod
    def correct_document(self, text: str) -> str:
        """Corrige el texto completo de una pagina o documento."""


def clean_paragraph(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return ""

    paragraph = lines[0]
    for line in lines[1:]:
        if paragraph.endswith("-") and line[:1].islower():
            paragraph = paragraph[:-1] + line
        else:
            paragraph += " " + line

    paragraph = re.sub(r"\s+([,.;:!?])", r"\1", paragraph)
    paragraph = re.sub(r"([,;:])(?=\S)", r"\1 ", paragraph)
    paragraph = re.sub(r"(\w)-\s+([a-záéíóúüñ])", r"\1\2", paragraph)
    paragraph = re.sub(r"([¿¡])\s+", r"\1", paragraph)
    paragraph = re.sub(r"\s+([•*-]\s+)", r"\n\n\1", paragraph)
    paragraph = re.sub(r"\s+(\d+\.\s+)", r"\n\n\1", paragraph)
    paragraph = re.sub(r"[ \t]{2,}", " ", paragraph)
    paragraph = re.sub(r"\n\n\s+", "\n\n", paragraph)
    return paragraph.strip()


def repair_drop_cap_paragraph_breaks(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        prefix, cap, first_letter = match.groups()
        if cap == "E" and first_letter.lower() in "aáeéiíoóuúü":
            return f"{prefix}El {first_letter}"
        return f"{prefix}{cap}{first_letter}"

    return re.sub(
        r"(^|\n\n)([A-ZÁÉÍÓÚÜÑ])\n\n([a-záéíóúüñ])",
        replace,
        text,
    )


def clean_document_text(text: str) -> str:
    paragraphs = [clean_paragraph(part) for part in re.split(r"\n{2,}", text)]
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    return repair_drop_cap_paragraph_breaks("\n\n".join(paragraphs))


def is_short_upper_line(text: str, max_length: int = 80) -> bool:
    return bool(text and len(text) <= max_length and text == text.upper())


def repair_missing_drop_capital(text: str) -> str:
    repairs = (
        (r"^n\s+([A-ZÁÉÍÓÚÜÑ])", r"En \1"),
        (r"^l\s+([a-záéíóúüñ])", r"El \1"),
        (r"^a\s+([a-záéíóúüñ])", r"La \1"),
        (r"^os\s+([a-záéíóúüñ])", r"Los \1"),
        (r"^as\s+([a-záéíóúüñ])", r"Las \1"),
    )
    for pattern, replacement in repairs:
        repaired = re.sub(pattern, replacement, text, count=1)
        if repaired != text:
            return repaired
    return text


def merge_floating_drop_caps(text_blocks: list[str]) -> list[str]:
    merged: list[str] = []
    index = 0
    while index < len(text_blocks):
        current = text_blocks[index].strip()
        if (
            index + 1 < len(text_blocks)
            and re.fullmatch(r"[A-ZÁÉÍÓÚÜÑ]", current)
            and re.match(r"^[a-záéíóúüñ]", text_blocks[index + 1].lstrip())
        ):
            following = text_blocks[index + 1].lstrip()
            # Capitulares tipicas; evita pegar "U"+"baja" en medio del texto.
            if current == "E" and following[:1].lower() in "aáeéiíoóuúü":
                merged.append(f"El {following}")
                index += 2
                continue
            if current == "U" and following.lower().startswith("n "):
                merged.append(f"U{following}")  # Un ...
                index += 2
                continue
            if current in {"L", "A", "N", "D", "T", "S", "C", "P", "M", "H"}:
                if current == "E":
                    merged.append(f"El {following}")
                else:
                    merged.append(f"{current}{following}")
                index += 2
                continue
            # Otras letras sueltas: no fusionar (ruido / callouts).
            merged.append(text_blocks[index])
            index += 1
            continue

        merged.append(text_blocks[index])
        index += 1
    return merged


def apply_replacements(text: str, replacements: dict[str, str]) -> str:
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def split_glued_uppercase_words(text: str) -> str:
    return re.sub(r"([a-záéíóúüñ])([A-ZÁÉÍÓÚÜÑ]{2,})", r"\1 \2", text)


def split_glued_spanish_words(text: str) -> str:
    """Separa pegados frecuentes: minuscula+Mayuscula y articulos/preposiciones."""
    # Solo si la segunda parte inicia en MAYUSCULA real (sin IGNORECASE).
    text = re.sub(
        r"([a-záéíóúüñ])([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñáéíóúüñ])",
        r"\1 \2",
        text,
    )
    particles = (
        r"El|La|Los|Las|Un|Una|De|Del|Al|En|Con|Por|Para|Que|Se|Su|Sus|"
        r"Es|Fue|Ha|Han|Como|M[aá]s|Muy|Lo|Le|Les|"
        r"Si|S[ií]|Ya|Hoy|Tras|Entre|Sobre|Desde|Hasta|V[ií]a|"
        r"el|la|los|las|un|una|de|del|al|en|con|por|para|que|se|su|sus|"
        r"es|fue|ha|han|como|m[aá]s|muy|lo|le|les|"
        r"si|s[ií]|ya|hoy|tras|entre|sobre|desde|hasta|v[ií]a"
    )
    text = re.sub(
        rf"\b({particles})([A-ZÁÉÍÓÚÜÑ])",
        r"\1 \2",
        text,
    )
    # Digito pegado a particula: 16dejulio
    text = re.sub(
        r"(\d)(de|del|en|al|a|y|por|con|la|las|los|el|un|una)(?=[a-záéíóúüñ])",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    # Punto pegado a mayuscula: seguridad.Quien
    text = re.sub(r"([a-záéíóúüñ])\.([A-ZÁÉÍÓÚÜÑ])", r"\1. \2", text)
    return text


class GenericCorrectionEngine(TextCorrectionEngine):
    """Reglas compartidas: parrafos, guiones y letras capitales."""

    id = "generico"
    label = "Generico"
    description = "Limpieza base sin diccionario de un genero concreto."

    def correct_block(self, text: str) -> str:
        return repair_missing_drop_capital(text)

    def correct_document(self, text: str) -> str:
        return clean_document_text(text)

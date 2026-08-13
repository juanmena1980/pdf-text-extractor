from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from engines import available_genre_ids, get_engine
from engines.base import (
    TextCorrectionEngine,
    clean_document_text,
    clean_paragraph,
    is_short_upper_line,
    merge_floating_drop_caps,
)


def _bootstrap_local_packages() -> None:
    """Solo runtime portable local de este proyecto (sin otros repos)."""
    if getattr(sys, "frozen", False):
        return
    candidate = Path(__file__).resolve().parent / "runtime" / "site-packages"
    if candidate.exists():
        sys.path.insert(0, str(candidate))


_bootstrap_local_packages()

try:
    import fitz  # PyMuPDF
except ImportError as exc:
    raise SystemExit(
        "PyMuPDF no esta instalado. Ejecuta: python -m pip install -r requirements.txt"
    ) from exc


@dataclass
class PageText:
    page: int
    char_count: int
    word_count: int
    text: str


@dataclass
class PdfResult:
    source_pdf: str
    output_txt: str
    output_json: str | None
    page_count: int
    char_count: int
    word_count: int
    encrypted: bool
    needs_ocr: bool
    genre: str


@dataclass
class TextBlock:
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float
    text: str


def discover_pdfs(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            raise ValueError(f"El archivo no es PDF: {input_path}")
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(f"No existe la ruta: {input_path}")

    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(path for path in input_path.glob(pattern) if path.is_file())


def safe_output_stem(pdf_path: Path, base_input: Path) -> str:
    try:
        relative = pdf_path.relative_to(base_input if base_input.is_dir() else base_input.parent)
    except ValueError:
        relative = pdf_path.name

    raw = str(relative.with_suffix(""))
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._-")
    digest = hashlib.sha1(str(pdf_path.resolve()).encode("utf-8")).hexdigest()[:8]
    return f"{slug or 'pdf'}_{digest}"


def line_text_from_spans(line: dict) -> str:
    pieces = []
    previous_x1: float | None = None
    previous_text = ""

    for span in line.get("spans", []):
        text = span.get("text", "")
        if not text:
            continue

        x0 = float(span.get("bbox", (0, 0, 0, 0))[0])
        if (
            pieces
            and previous_x1 is not None
            and x0 - previous_x1 > 0.7
            and previous_text[-1:].isalnum()
            and text[:1].isalnum()
        ):
            pieces.append(" ")

        pieces.append(text)
        previous_x1 = float(span.get("bbox", (0, 0, 0, 0))[2])
        previous_text = text

    return "".join(pieces)


def block_text_from_dict(block: dict) -> str:
    lines = []
    for line in block.get("lines", []):
        text = line_text_from_spans(line).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def is_efinfo_banner(text: str) -> bool:
    lowered = text.lower()
    return "efinfo" in lowered or "libre utilización de obras" in lowered


def _bbox_size(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    x0, y0, x1, y1 = bbox
    return max(0.0, x1 - x0), max(0.0, y1 - y0)


def is_wide_photograph(
    bbox: tuple[float, float, float, float], page_width: float, page_height: float
) -> bool:
    """Fotos anchas (no columnas de texto ni timelines estrechos)."""
    width, height = _bbox_size(bbox)
    return width >= page_width * 0.40 and height >= page_height * 0.10


def is_portrait_photo_inset(
    bbox: tuple[float, float, float, float], page_width: float, page_height: float
) -> bool:
    """Miniaturas/retratos verticales (p. ej. cita tipografica dentro de foto)."""
    x0, y0, x1, y1 = bbox
    width, height = _bbox_size(bbox)
    # Sidebars/timelines de pagina completa no son miniaturas.
    if y0 < page_height * 0.25 and height >= page_height * 0.45:
        return False
    return page_width * 0.08 <= width <= page_width * 0.20 and height >= page_height * 0.22


def looks_like_graphic_overlay_text(text: str) -> bool:
    """Texto decorativo dentro de foto/miniatura (letras separadas o etiquetas)."""
    lowered = text.lower()
    markers = (
        r"diagn[oó]sti\s+cos",
        r"\bev\s+itar",
        r"concentra\s+ra\b",
        r"institucio\s*$",
        r"institucio\s+nes",
        r"guberna\s*mentales",
        r"nes\s*guberna",
        r"\bsis\s+tema\b",
        r"adicionalmen\s+te",
        r"^ra el poder\b",
    )
    if any(re.search(pattern, lowered) for pattern in markers):
        return True
    compact = re.sub(r"\s+", " ", text.strip())
    if re.fullmatch(
        r"(INTEGRANTE|DEL COMIT[EÉ] DE|PARTICIPACI[OÓ]N|CIUDADANA\.?)",
        compact,
        flags=re.IGNORECASE,
    ):
        return True
    # Titulos cortos sobreimpresos en foto (p. ej. SISTEMA NACIONAL)
    if compact.isupper() and 8 <= len(compact) <= 40 and " " in compact:
        return True
    return False


def collect_photograph_bboxes(
    page: fitz.Page,
) -> tuple[list[tuple[float, float, float, float]], list[tuple[float, float, float, float]]]:
    page_width = float(page.rect.width)
    page_height = float(page.rect.height)
    wide: list[tuple[float, float, float, float]] = []
    portraits: list[tuple[float, float, float, float]] = []
    try:
        infos = page.get_image_info(xrefs=True)
    except Exception:
        infos = []
    for info in infos:
        bbox = info.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        box = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
        if is_wide_photograph(box, page_width, page_height):
            wide.append(box)
        elif is_portrait_photo_inset(box, page_width, page_height):
            portraits.append(box)
    return wide, portraits


def is_photo_caption(
    block: TextBlock, photos: list[tuple[float, float, float, float]]
) -> bool:
    text = block.text.strip()
    if re.search(r"\bFOTOS?\s*:", text, flags=re.IGNORECASE):
        return True
    for x0, y0, x1, y1 in photos:
        # Pie tipico: justo debajo o rozando el borde inferior de la foto.
        if block.y0 >= y1 - 18 and block.y0 <= y1 + 90:
            overlaps_x = block.x1 >= x0 - 25 and block.x0 <= x1 + 25
            if overlaps_x:
                return True
    return False


def text_inside_photograph(
    block: TextBlock, photos: list[tuple[float, float, float, float]], bottom_margin: float = 22.0
) -> bool:
    cx = (block.x0 + block.x1) / 2.0
    cy = (block.y0 + block.y1) / 2.0
    for x0, y0, x1, y1 in photos:
        if x0 < cx < x1 and y0 < cy < (y1 - bottom_margin):
            return True
    return False


def looks_like_headline(block: TextBlock) -> bool:
    """Titular de nota (no necesariamente masthead gigante)."""
    text = block.text.strip()
    if len(text) < 8:
        return False
    if block.font_size >= 14.0:
        return True
    return block.font_size >= 12.0 and len(text.split()) >= 3


def looks_like_article_body(text: str) -> bool:
    """Parrafo periodistico real (conservar aunque caiga sobre bbox de foto)."""
    compact = re.sub(r"\s+", " ", text.strip())
    if len(compact) < 35:
        return False
    words = compact.split()
    if len(words) < 8:
        return False
    if looks_like_graphic_overlay_text(compact) and not re.search(r"[.!?].{15,}", compact):
        return False
    return bool(re.search(r"[.!,;:]", compact)) or len(compact) >= 80


def is_masthead_title(block: TextBlock) -> bool:
    """Titular tipografico grande sobre imagen de portada/banner."""
    return block.font_size >= 28.0 and len(block.text.strip()) >= 3


def filter_text_inside_photos(
    blocks: list[TextBlock],
    wide_photos: list[tuple[float, float, float, float]],
    portrait_photos: list[tuple[float, float, float, float]],
) -> list[TextBlock]:
    """Omite overlays en fotos; conserva titulares, cuerpo y pies de foto."""
    all_photos = wide_photos + portrait_photos
    if not all_photos:
        return blocks

    filtered: list[TextBlock] = []
    for block in blocks:
        if is_photo_caption(block, wide_photos):
            filtered.append(block)
            continue

        if text_inside_photograph(block, wide_photos):
            # En recortes con foto grande el texto de la nota suele vivir
            # dentro del bbox: conservar titulares y parrafos reales.
            if (
                is_masthead_title(block)
                or looks_like_headline(block)
                or looks_like_article_body(block.text)
                or is_author_byline(block.text, block.font_size)
            ):
                filtered.append(block)
            continue

        # Miniaturas verticales: omitir overlays/citas, no el cuerpo de timelines.
        if text_inside_photograph(block, portrait_photos, bottom_margin=8.0):
            compact = block.text.strip()
            if looks_like_graphic_overlay_text(compact) or re.fullmatch(
                r"[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+){0,3},?",
                compact,
            ):
                continue
            # Fragmentos cortos tipicos de la cita tipografica partida
            if len(compact) <= 40 and not re.search(r"\d{4}\.", compact):
                if re.search(r"\s", compact) and not re.search(r"[.!?]$", compact):
                    # p. ej. "ra el poder en las institucio"
                    if looks_like_graphic_overlay_text(compact) or re.match(
                        r"^[a-záéíóúüñ]", compact
                    ):
                        continue

        filtered.append(block)
    return filtered


def repair_oversized_drop_cap_blocks(blocks: list[TextBlock]) -> list[TextBlock]:
    """Repara capitulares gigantes tipo '1 Sistema...' o 'a polémica ... IL'."""
    repaired: list[TextBlock] = []
    index = 0
    while index < len(blocks):
        block = blocks[index]
        text = block.text.strip()
        if block.font_size >= 28 and re.match(r"^1\s+Sistema\b", text):
            text = re.sub(r"^1\s+", "El ", text)
            text = re.sub(r"Anti-\s*E\s*$", "Anti", text)
            merge_at = None
            for look_ahead in range(index + 1, min(index + 8, len(blocks))):
                candidate = blocks[look_ahead]
                # Misma columna aproximada.
                if abs(candidate.x0 - block.x0) > 80 and abs(candidate.x1 - block.x1) > 80:
                    continue
                following = candidate.text.lstrip()
                lower_follow = following.lower()
                if lower_follow.startswith("corrupción") or lower_follow.startswith("corrupcion"):
                    merge_at = look_ahead
                    token = "corrupción" if lower_follow.startswith("corrupción") else "corrupcion"
                    rest = following[len(token) :]
                    text = text[: -len("Anti")] + "Anticorrupción" + rest
                    break
            repaired.append(
                TextBlock(
                    block.x0,
                    block.y0,
                    block.x1,
                    block.y1,
                    min(block.font_size, 12.0),
                    text.strip(),
                )
            )
            if merge_at is None:
                index += 1
            else:
                for mid in range(index + 1, merge_at):
                    repaired.append(blocks[mid])
                index = merge_at + 1
            continue

        if block.font_size >= 28 and re.match(r"^a\s+\S", text, flags=re.IGNORECASE):
            text = re.sub(r"^a\s+", "La ", text, count=1, flags=re.IGNORECASE)
            text = re.sub(r"\s+IL\s*$", "", text)
            text = re.sub(r"\s+I\s*$", "", text)
            repaired.append(
                TextBlock(
                    block.x0,
                    block.y0,
                    block.x1,
                    block.y1,
                    min(block.font_size, 12.0),
                    text.strip(),
                )
            )
            index += 1
            continue

        # Titular con capitular perdida: "electoral, a eterna controversia"
        if block.font_size >= 28 and re.search(
            r",\s*a\s+eterna\s+controversia\b", text, flags=re.IGNORECASE
        ):
            text = re.sub(
                r",\s*a\s+(eterna\s+controversia)\b",
                r", la \1",
                text,
                count=1,
                flags=re.IGNORECASE,
            )
            repaired.append(
                TextBlock(
                    block.x0,
                    block.y0,
                    block.x1,
                    block.y1,
                    block.font_size,
                    text.strip(),
                )
            )
            index += 1
            continue

        repaired.append(block)
        index += 1
    return repaired


def extract_text_blocks(page: fitz.Page, header_percent: float, footer_percent: float) -> list[TextBlock]:
    page_dict = page.get_text("dict", sort=False)
    page_height = float(page.rect.height)
    top_limit = page_height * max(0.0, min(header_percent, 40.0)) / 100.0
    bottom_limit = page_height * (1.0 - max(0.0, min(footer_percent, 40.0)) / 100.0)
    wide_photos, portrait_photos = collect_photograph_bboxes(page)

    blocks = []
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        x0, y0, x1, y1 = block.get("bbox", (0, 0, 0, 0))
        text = clean_paragraph(block_text_from_dict(block))
        if re.fullmatch(r"(pagina|página|page)\s+\d+", text, flags=re.IGNORECASE):
            continue
        # Omite URLs sueltas; conserva emails de credito de autor.
        if text.lower().startswith("www."):
            continue
        if "@" in text and not re.fullmatch(
            r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
            text.strip(),
        ):
            continue
        if is_efinfo_banner(text):
            continue
        if text:
            sizes = [
                float(span.get("size", 0.0))
                for line in block.get("lines", [])
                for span in line.get("spans", [])
            ]
            font_size = max(sizes, default=0.0)
            in_header_or_footer = y0 < top_limit or y1 > bottom_limit
            # Conserva titulares (no solo masthead >=28) aunque invadan el margen.
            if in_header_or_footer and font_size < 14.0:
                continue
            # Omite tipografia minuscula tipica de infografias/diagramas.
            # Conserva creditos de redaccion (~6.6pt) y pies de foto.
            if font_size and font_size < 6.5:
                continue
            if (
                font_size
                and font_size < 6.8
                and not re.search(r"\bFOTOS?\s*:", text, flags=re.IGNORECASE)
                and not is_newsroom_credit(text)
            ):
                continue
            # Tablas/infografias leidas a lo ancho: repeticiones de etiquetas.
            if text.count("Gasto operativo:") >= 2 or text.count("Total:") >= 2:
                continue
            if text.count("Gasto de campaña:") >= 2 or text.count("Gasto de campana:") >= 2:
                continue
            blocks.append(
                TextBlock(
                    float(x0),
                    float(y0),
                    float(x1),
                    float(y1),
                    font_size,
                    text,
                )
            )
    blocks = filter_text_inside_photos(blocks, wide_photos, portrait_photos)
    return repair_oversized_drop_cap_blocks(blocks)


def sort_blocks_by_columns(blocks: list[TextBlock], page_width: float) -> list[TextBlock]:
    """Ordena por columnas completas (izquierda → derecha), no por bandas horizontales."""
    if len(blocks) <= 1:
        return blocks

    content_width = max((block.x1 for block in blocks), default=page_width) - min(
        (block.x0 for block in blocks), default=0.0
    )
    full_width = max(page_width * 0.45, content_width * 0.55)

    titles: list[TextBlock] = []
    body: list[TextBlock] = []
    for block in blocks:
        width = block.x1 - block.x0
        compact = block.text.strip()
        word_count = len(compact.split())
        # Callouts numericos gigantes (p. ej. "2") no son titulos de pagina.
        is_numeric_callout = bool(re.fullmatch(r"\d+\.?", compact)) or (
            block.font_size >= 28.0 and len(compact) <= 3
        )
        # Citas/pull quotes tampoco (rompen el orden de columnas).
        is_pull_quote = bool(re.match(r"^[\"“«'‘]", compact))
        is_banner_title = (not is_numeric_callout) and (not is_pull_quote) and (
            block.font_size >= 28
            or (
                width >= full_width
                and block.font_size >= 14.0
                and len(compact) > 2
                and not re.fullmatch(r"\d+\.?", compact)
            )
            or (
                # Titulares de nota relativamente anchos (no bajadas/ estrechos).
                block.font_size >= 14.0
                and width >= page_width * 0.30
                and 3 <= word_count <= 24
                and not re.search(r"[.!?]$", compact)
            )
            or (
                # Bajada/deck bajo el titulo.
                10.8 <= block.font_size < 14.0
                and width >= page_width * 0.35
                and 12 <= word_count <= 45
                and not re.search(r"[.!?]$", compact)
            )
        )
        if is_banner_title:
            titles.append(block)
        else:
            body.append(block)

    if not body:
        return sorted(titles, key=lambda block: (block.y0, block.x0))

    # Creditos de autor salen del flujo de columnas (evita pegarlos al inicio de otra).
    bylines: list[TextBlock] = []
    column_body: list[TextBlock] = []
    for block in body:
        if is_author_byline(block.text, block.font_size):
            bylines.append(block)
        else:
            column_body.append(block)
    bylines.sort(key=lambda block: (block.y0, block.x0))

    # Agrupa el cuerpo en columnas por ancla x0.
    by_x = sorted(column_body, key=lambda block: (block.x0, block.y0))
    clusters: list[list[TextBlock]] = []
    x_anchor_tolerance = page_width * 0.12
    for block in by_x:
        best_cluster: list[TextBlock] | None = None
        best_distance = float("inf")
        for cluster in clusters:
            cluster_anchor = min(item.x0 for item in cluster)
            distance = abs(block.x0 - cluster_anchor)
            if distance < best_distance:
                best_cluster = cluster
                best_distance = distance
        if best_cluster is not None and best_distance <= x_anchor_tolerance:
            best_cluster.append(block)
        else:
            clusters.append([block])

    clusters.sort(key=lambda cluster: min(block.x0 for block in cluster))
    for cluster in clusters:
        cluster.sort(key=lambda block: (block.y0, block.x0))

    # Inserta titulos/banner por posicion vertical respecto a las columnas.
    titles_sorted = sorted(titles, key=lambda block: (block.y0, block.x0))
    if not titles_sorted and not bylines:
        ordered: list[TextBlock] = []
        for cluster in clusters:
            ordered.extend(cluster)
        return ordered

    ordered = []
    title_index = 0
    byline_index = 0
    column_cursors = [0] * len(clusters)

    while (
        title_index < len(titles_sorted)
        or byline_index < len(bylines)
        or any(column_cursors[i] < len(clusters[i]) for i in range(len(clusters)))
    ):
        # Y del proximo bloque de columna (sin creditos).
        column_y = float("inf")
        for idx, cluster in enumerate(clusters):
            cursor = column_cursors[idx]
            if cursor < len(cluster):
                column_y = min(column_y, cluster[cursor].y0)
        byline_y = (
            bylines[byline_index].y0 if byline_index < len(bylines) else float("inf")
        )
        next_content_y = min(column_y, byline_y)

        if title_index < len(titles_sorted) and titles_sorted[title_index].y0 <= next_content_y + 8:
            ordered.append(titles_sorted[title_index])
            title_index += 1
            continue

        # Creditos de autor: despues de titulos superiores y antes de cualquier columna.
        if byline_index < len(bylines):
            blocking_title = (
                title_index < len(titles_sorted)
                and titles_sorted[title_index].y0 < byline_y - 5
            )
            if not blocking_title:
                ordered.append(bylines[byline_index])
                byline_index += 1
                continue

        # Emite una columna completa a la vez (flujo periodistico clasico).
        # Solo titulos anchos/masthead cortan la columna; bajadas locales no.
        progressed = False
        for idx, cluster in enumerate(clusters):
            if column_cursors[idx] >= len(cluster):
                continue
            limit_y = float("inf")
            if title_index < len(titles_sorted):
                for title in titles_sorted[title_index:]:
                    title_width = title.x1 - title.x0
                    if title.font_size >= 28.0 or title_width >= full_width * 0.85:
                        limit_y = title.y0
                        break
            while column_cursors[idx] < len(cluster) and cluster[column_cursors[idx]].y0 < limit_y:
                ordered.append(cluster[column_cursors[idx]])
                column_cursors[idx] += 1
                progressed = True
            if progressed:
                break
        if not progressed:
            # Evita bucles si solo quedan titulos/creditos por debajo.
            if title_index < len(titles_sorted):
                ordered.append(titles_sorted[title_index])
                title_index += 1
            elif byline_index < len(bylines):
                ordered.append(bylines[byline_index])
                byline_index += 1
            else:
                break

    return ordered


def same_column(previous: TextBlock, current: TextBlock, page_width: float) -> bool:
    """Misma columna solo si comparten ancla X y no hay salto hacia arriba (cambio de columna)."""
    if abs(previous.x0 - current.x0) > page_width * 0.12:
        return False
    # Al terminar una columna el siguiente bloque vuelve arriba: no fusionar.
    if current.y0 + 35.0 < previous.y0:
        return False
    return True


def is_newsroom_credit(text: str) -> bool:
    """Creditos tipicos de redaccion en tipografia muy chica."""
    compact = text.strip()
    return bool(
        re.fullmatch(
            r"(De la Redacci[oó]n|Redacci[oó]n|Staff|Agencias?|Corresponsal(?:es)?)\.?",
            compact,
            flags=re.IGNORECASE,
        )
    )


def looks_like_upper_author_line(text: str) -> bool:
    """Linea de autor en mayusculas (corta); no titulares largos."""
    compact = text.strip().lstrip("-–— ").strip()
    if not is_short_upper_line(compact, max_length=40):
        return False
    parts = re.sub(r"[./]", " ", compact).split()
    return 2 <= len(parts) <= 5


def is_author_byline(text: str, font_size: float) -> bool:
    """Credito de autor tipico: nombre en title case y tipografia chica."""
    if font_size > 9.5:
        return False
    compact = text.strip()
    if not compact or len(compact) > 60 or re.search(r"[.!?]$", compact):
        return False
    if is_newsroom_credit(compact):
        return True
    # Email de autor
    if re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", compact):
        return True
    # "- ROBERTO AGUILAR" / "ROBERTO AGUILAR" / "VÍCTOR CHÁVEZ"
    stripped = compact.lstrip("-–— ").strip()
    if is_short_upper_line(stripped, max_length=40) and 2 <= len(stripped.split()) <= 5:
        return True
    return bool(
        re.match(
            r"^[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ.]+){1,5}$",
            compact,
        )
    )


def page_text_human(
    page: fitz.Page,
    engine: TextCorrectionEngine,
    header_percent: float,
    footer_percent: float,
) -> str:
    page_width = float(page.rect.width)
    blocks = extract_text_blocks(page, header_percent, footer_percent)
    ordered = sort_blocks_by_columns(blocks, page_width)
    merged_blocks: list[TextBlock] = []
    for block in ordered:
        previous_is_short_heading = bool(merged_blocks and is_short_upper_line(merged_blocks[-1].text))
        previous_font = merged_blocks[-1].font_size if merged_blocks else 0.0
        compatible_font = abs(previous_font - block.font_size) <= 5.0
        previous_text = merged_blocks[-1].text.strip() if merged_blocks else ""
        # Evita mezclar subtítulos reales con el cuerpo; no aplica a inicios de
        # párrafo tras capitular (font ~12 con continuación en minúscula).
        heading_to_body_boundary = (
            previous_font >= 13.0
            and block.font_size <= 10.5
            and (
                previous_is_short_heading
                or len(previous_text.split()) <= 8
            )
        )
        # Titular de nota (~11-13pt) seguido de lead en tipografia menor.
        title_to_body_boundary = (
            previous_font >= 11.0
            and block.font_size <= previous_font - 2.0
            and bool(re.match(r"^[A-ZÁÉÍÓÚÜÑ¿¡\"«]", block.text.strip()))
            and not re.search(r"[,:;]$", previous_text)
        )
        previous_is_author_credit = bool(
            merged_blocks and is_author_byline(previous_text, previous_font)
        )
        next_is_author_credit = is_author_byline(block.text.strip(), block.font_size)
        # Evita fusionar dos parrafos de cuerpo cuando el anterior no cierra con punto.
        new_paragraph_boundary = (
            len(previous_text) >= 90
            and bool(re.match(r"^[A-ZÁÉÍÓÚÜÑ¿¡\"«]", block.text.strip()))
            and not re.search(r"[,:;]$", previous_text)
            and abs(previous_font - block.font_size) <= 2.5
            and previous_font <= 12.5
        )
        next_is_all_caps = bool(
            re.match(
                r"^[A-ZÁÉÍÓÚÜÑ0-9][A-ZÁÉÍÓÚÜÑ0-9\s.,;:¿?¡!\"'()-]{2,}$",
                block.text.strip(),
            )
        )
        both_upper_headings = (
            is_short_upper_line(previous_text, max_length=80)
            and next_is_all_caps
            and previous_font >= 12.0
            and block.font_size >= 12.0
        )
        # Titular/bajada corta seguida de lead de nota.
        subhead_to_body_boundary = (
            len(previous_text.split()) <= 14
            and previous_font >= 10.5
            and not re.search(r"[.!?]$", previous_text)
            and bool(
                re.match(
                    r"^(En|El|La|Los|Las|Un|Una|Por|Para|Tras|Seg[uú]n)\s",
                    block.text.strip(),
                )
            )
            and not re.match(
                r"^(En|El|La|Los|Las|Un|Una|Por|Para|Tras|Seg[uú]n)\s",
                previous_text,
            )
        )
        if (
            merged_blocks
            and same_column(merged_blocks[-1], block, page_width)
            and (not previous_is_short_heading or both_upper_headings)
            and not previous_is_author_credit
            and not next_is_author_credit
            and compatible_font
            and not heading_to_body_boundary
            and not title_to_body_boundary
            and not subhead_to_body_boundary
            and not new_paragraph_boundary
            and not re.search(r'[.!?:"”)]$', merged_blocks[-1].text)
            and not (next_is_all_caps and not both_upper_headings)
        ):
            merged_blocks[-1].text = f"{merged_blocks[-1].text} {block.text}"
            merged_blocks[-1].x0 = min(merged_blocks[-1].x0, block.x0)
            merged_blocks[-1].y0 = min(merged_blocks[-1].y0, block.y0)
            merged_blocks[-1].x1 = max(merged_blocks[-1].x1, block.x1)
            merged_blocks[-1].y1 = max(merged_blocks[-1].y1, block.y1)
        else:
            merged_blocks.append(block)

    text_blocks = [block.text for block in merged_blocks]
    while (
        len(text_blocks) >= 2
        and is_short_upper_line(text_blocks[0], max_length=24)
        and is_short_upper_line(text_blocks[1], max_length=24)
        and "." not in text_blocks[0]
        and "." not in text_blocks[1]
    ):
        text_blocks[0:2] = [f"{text_blocks[0]} {text_blocks[1]}"]

    # Une solo lineas de autores en mayusculas cortas, no titulares largos.
    author_start = 0
    while author_start < len(text_blocks) and not looks_like_upper_author_line(
        text_blocks[author_start]
    ):
        author_start += 1
    author_end = author_start
    while author_end < len(text_blocks) and looks_like_upper_author_line(text_blocks[author_end]):
        author_end += 1
    if author_end - author_start > 1:
        text_blocks[author_start:author_end] = [
            " / ".join(text_blocks[author_start:author_end])
        ]

    index = 0
    while index < len(text_blocks) - 1:
        if (
            is_short_upper_line(text_blocks[index])
            and is_short_upper_line(text_blocks[index + 1])
            and re.match(r"^(Y|E|&)\s+", text_blocks[index + 1])
        ):
            text_blocks[index:index + 2] = [f"{text_blocks[index]} / {text_blocks[index + 1]}"]
            continue
        index += 1

    # Une "Nombre Apellido,\nINTEGRANTE\nDEL COMITÉ..." en una sola linea.
    index = 0
    while index < len(text_blocks):
        current = text_blocks[index].rstrip()
        if current.endswith(",") and index + 1 < len(text_blocks) and is_short_upper_line(text_blocks[index + 1]):
            end = index + 1
            while end < len(text_blocks) and is_short_upper_line(text_blocks[end]):
                end += 1
            text_blocks[index:end] = [" ".join(part.strip() for part in text_blocks[index:end])]
            index += 1
            continue
        if is_short_upper_line(current) and index + 1 < len(text_blocks) and is_short_upper_line(text_blocks[index + 1]):
            end = index + 1
            while end < len(text_blocks) and is_short_upper_line(text_blocks[end]):
                end += 1
            if end - index > 1:
                text_blocks[index:end] = [" ".join(part.strip() for part in text_blocks[index:end])]
                index += 1
                continue
        index += 1

    text_blocks = merge_floating_drop_caps(text_blocks)
    text_blocks = [engine.correct_block(block) for block in text_blocks]
    return engine.correct_document("\n\n".join(text_blocks))


def page_text(
    page: fitz.Page,
    mode: str,
    engine: TextCorrectionEngine,
    header_percent: float = 0.0,
    footer_percent: float = 0.0,
) -> str:
    if mode == "human":
        return page_text_human(
            page,
            engine=engine,
            header_percent=header_percent,
            footer_percent=footer_percent,
        )

    if mode == "blocks":
        blocks = page.get_text("blocks", sort=True)
        text_blocks = [block[4].strip() for block in blocks if len(block) >= 5 and block[4].strip()]
        return engine.correct_document(clean_document_text("\n\n".join(text_blocks)))

    return engine.correct_document(clean_document_text(page.get_text("text", sort=True).strip()))


def join_cross_page_paragraphs(page_texts: list[str]) -> str:
    """Une parrafos partidos por salto de pagina (p. ej. '... acuerdo y' + 'de ahi...')."""
    if not page_texts:
        return ""

    combined = page_texts[0].rstrip()
    for part in page_texts[1:]:
        next_part = part.lstrip()
        if not next_part:
            continue
        if not combined:
            combined = next_part.rstrip()
            continue

        prev_tail = combined.rstrip()
        ends_sentence = bool(re.search(r'[.!?…"”»)\]]$', prev_tail))
        next_starts_lower = bool(re.match(r"^[a-záéíóúüñ¿¡]", next_part))
        ends_with_connector = bool(
            re.search(
                r"(?i)\b(y|e|o|u|de|del|la|el|los|las|un|una|en|con|por|para|que|se|al|a|su|sus)$",
                prev_tail,
            )
        )

        if next_starts_lower and (not ends_sentence or ends_with_connector):
            combined = f"{prev_tail} {next_part}"
        else:
            combined = f"{prev_tail}\n\n{next_part}"
        combined = combined.rstrip()

    return combined


def extract_one_pdf(
    pdf_path: Path,
    output_dir: Path,
    base_input: Path,
    mode: str,
    write_pages_json: bool,
    header_percent: float = 8.0,
    footer_percent: float = 5.0,
    genre: str = "nota_informativa",
) -> PdfResult:
    engine = get_engine(genre)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = safe_output_stem(pdf_path, base_input)
    txt_path = output_dir / f"{stem}.txt"
    json_path = output_dir / f"{stem}.pages.json"

    pages: list[PageText] = []
    encrypted = False

    with fitz.open(pdf_path) as doc:
        encrypted = bool(doc.is_encrypted)
        if encrypted and not doc.authenticate(""):
            raise ValueError(f"PDF encriptado o protegido: {pdf_path}")

        all_text_parts: list[str] = []
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            text = page_text(
                page,
                mode,
                engine=engine,
                header_percent=header_percent if mode == "human" else 0.0,
                footer_percent=footer_percent if mode == "human" else 0.0,
            )
            words = text.split()
            pages.append(
                PageText(
                    page=page_index + 1,
                    char_count=len(text),
                    word_count=len(words),
                    text=text,
                )
            )
            if text:
                all_text_parts.append(text)

    full_text = join_cross_page_paragraphs(all_text_parts).rstrip() + "\n"
    # Reaplica el documento completo para unir tambien cortes tipicos del genero.
    full_text = engine.correct_document(full_text).rstrip() + "\n"
    txt_path.write_text(full_text, encoding="utf-8")

    output_json: str | None = None
    if write_pages_json:
        json_payload = {
            "source_pdf": str(pdf_path),
            "genre": engine.id,
            "pages": [asdict(page) for page in pages],
        }
        json_path.write_text(
            json.dumps(json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        output_json = str(json_path)

    char_count = sum(page.char_count for page in pages)
    word_count = sum(page.word_count for page in pages)
    return PdfResult(
        source_pdf=str(pdf_path),
        output_txt=str(txt_path),
        output_json=output_json,
        page_count=len(pages),
        char_count=char_count,
        word_count=word_count,
        encrypted=encrypted,
        needs_ocr=char_count == 0,
        genre=engine.id,
    )


def extract_pdfs(
    input_path: Path,
    output_dir: Path,
    recursive: bool,
    mode: str,
    write_pages_json: bool,
    header_percent: float = 8.0,
    footer_percent: float = 5.0,
    genre: str = "nota_informativa",
) -> list[PdfResult]:
    pdfs = discover_pdfs(input_path, recursive)
    if not pdfs:
        raise ValueError(f"No se encontraron PDFs en: {input_path}")

    results = []
    for pdf_path in pdfs:
        results.append(
            extract_one_pdf(
                pdf_path=pdf_path,
                output_dir=output_dir,
                base_input=input_path,
                mode=mode,
                write_pages_json=write_pages_json,
                header_percent=header_percent,
                footer_percent=footer_percent,
                genre=genre,
            )
        )
    return results


def write_manifest(output_dir: Path, results: Iterable[PdfResult]) -> Path:
    manifest_path = output_dir / "manifest.json"
    payload = [asdict(result) for result in results]
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    genres = available_genre_ids()
    parser = argparse.ArgumentParser(
        description="Extrae texto de PDFs con PyMuPDF y genera TXT + JSON."
    )
    parser.add_argument("input", help="PDF o carpeta con PDFs.")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="text",
        help="Carpeta de salida. Default: text",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Busca PDFs tambien en subcarpetas.",
    )
    parser.add_argument(
        "--mode",
        choices=["human", "text", "blocks"],
        default="human",
        help="human quita header/footer y ordena columnas; text preserva flujo general; blocks separa bloques.",
    )
    parser.add_argument(
        "--genre",
        choices=genres,
        default="nota_informativa",
        help="Motor de correccion por genero editorial. Default: nota_informativa.",
    )
    parser.add_argument(
        "--header-percent",
        type=float,
        default=8.0,
        help="Porcentaje superior de cada pagina que se ignora en modo human. Default: 8.",
    )
    parser.add_argument(
        "--footer-percent",
        type=float,
        default=5.0,
        help="Porcentaje inferior de cada pagina que se ignora en modo human. Default: 5.",
    )
    parser.add_argument(
        "--no-pages-json",
        action="store_true",
        help="No genera JSON por pagina.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    results = extract_pdfs(
        input_path=input_path,
        output_dir=output_dir,
        recursive=args.recursive,
        mode=args.mode,
        write_pages_json=not args.no_pages_json,
        header_percent=args.header_percent,
        footer_percent=args.footer_percent,
        genre=args.genre,
    )
    manifest_path = write_manifest(output_dir, results)

    print(f"PDFs procesados: {len(results)}")
    print(f"Genero: {args.genre}")
    print(f"Manifest: {manifest_path}")
    for result in results:
        ocr_hint = " necesita OCR" if result.needs_ocr else ""
        print(
            f"- {result.source_pdf} -> {result.output_txt} "
            f"({result.page_count} paginas, {result.word_count} palabras){ocr_hint}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

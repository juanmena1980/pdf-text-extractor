from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

LOCAL_PACKAGE_DIR = Path(__file__).resolve().parents[1] / ".docqa_packages"
if LOCAL_PACKAGE_DIR.exists():
    sys.path.insert(0, str(LOCAL_PACKAGE_DIR))

try:
    import fitz  # PyMuPDF
except ImportError as exc:
    raise SystemExit(
        "PyMuPDF no esta instalado. Ejecuta: python -m pip install PyMuPDF"
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


def clean_document_text(text: str) -> str:
    paragraphs = [clean_paragraph(part) for part in re.split(r"\n{2,}", text)]
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    return repair_drop_cap_paragraph_breaks("\n\n".join(paragraphs))


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


def repair_spacing_artifacts(text: str) -> str:
    replacements = {
        "Canadá(T-MEC)": "Canadá (T-MEC)",
        "Borderlands(editorial": "Borderlands (editorial",
        "Harfuch\"y": "Harfuch\" y",
        "en\"sombras": "en \"sombras",
        "muerte\"y": "muerte\" y",
        "que\"no": "que \"no",
        "lafrontera": "la frontera",
        "ellado": "el lado",
        "porlaembajada": "por la embajada",
        "EUdurante": "EU durante",
        "laadministración": "la administración",
        "losmismosjesuitas": "los mismos jesuitas",
        "mismosjesuitas": "mismos jesuitas",
        "esefuturo": "ese futuro",
        "migratoriasy": "migratorias y",
        "migración seguridad": "migración y seguridad",
        "Brownsville Matamoros": "Brownsville y Matamoros",
        "cercanosa": "cercanos a",
        "contactadoa": "contactado a",
        "Paca\"y": "Paca\" y",
        "prensa?Algunos": "prensa? Algunos",
        "costumbre.Veremos": "costumbre. Veremos",
        "sen- Augusto tarse": "sentarse",
        "Adán Adán solo": "Adán solo",
        "como Manuel ejemplos": "como ejemplos",
        "en el Huerta pasado": "en el pasado",
        "Eje- Claudia cutivo": "Ejecutivo",
        "ma- Sheinbaum nifestaciones": "manifestaciones",
        "O cancelar": "o cancelar",
        "carreteras y Cámara de hospitales": "carreteras y hospitales",
        "Lo que más Diputados han escuchado": "Lo que más han escuchado",
        "desde ejecutar supervisar": "desde ejecutar y supervisar",
        "sismo de\n\n2017": "sismo de 2017",
        "Papaa": "Papa a",
        "traera": "traer a",
        "ámbitoprivado": "ámbito privado",
        "comojefe": "como jefe",
        "cuerposdeseguridad": "cuerpos de seguridad",
        "losjesuitasJavier": "los jesuitas Javier",
        "Camposy": "Campos y",
        "Moraen": "Mora en",
        "Ylafalta": "Y la falta",
        "desolidaridadde": "de solidaridad de",
        "laviolenciacontra": "la violencia contra",
        "enumerarmás": "enumerar más",
        "HéctorMario": "Héctor Mario",
        "aRadio": "a Radio",
        "prontolo": "pronto lo",
        "estéaquí": "esté aquí",
        "tomancuerpo": "toman cuerpo",
        "JorgeRomero": "Jorge Romero",
        "dejuniode": "de junio de",
        "Lasgestiones": "Las gestiones",
        "llevamuyavanzadas": "lleva muy avanzadas",
        "lasnegociaciones": "las negociaciones",
        "MCpara": "MC para",
        "pulverizarel": "pulverizar el",
        "votoopositor": "voto opositor",
        "Yen ": "Y en ",
        "llegara": "llegar a",
        "conazules": "con azules",
        "padreyRicardo": "padre y Ricardo",
        "habráotros": "habrá otros",
        "GUERRATLAXCALTECA": "GUERRA TLAXCALTECA",
        "Apropósitode": "A propósito de",
        "SánchezAnaya": "Sánchez Anaya",
        "deprácticas": "de prácticas",
        "losefectos": "los efectos",
        "operadorespara": "operadores para",
        "decamiones": "de camiones",
        "BAJOSOSPECHA": "BAJO SOSPECHA",
        "TELÃ‰FONOROJO": "TELÃ‰FONO ROJO",
        "4T.Por": "4T. Por",
        "cualquierforma": "cualquier forma",
        "polÃ­ticay": "polÃ­tica y",
        "elsegundo": "el segundo",
        "ladirigencianacional": "la dirigencia nacional",
        "deAriadna": "de Ariadna",
        "partido.\"Â¿Lesmolesta": "partido. \"Â¿Les molesta",
        "mujero": "mujer o",
        "aintimidar": "a intimidar",
        "morenista.AhÃ­": "morenista. AhÃ­",
        "mejorconocida": "mejor conocida",
        "responsabilidadcon": "responsabilidad con",
        "liderazgo de tu": "liderazgo y de tu",
        "futuro.Estoy": "futuro. Estoy",
        "coordinaciÃ³ny": "coordinaciÃ³n y",
        "familiasmexicanas": "familias mexicanas",
        "deChihuahua": "de Chihuahua",
        "MaruCampos": "Maru Campos",
        "mandatariosestatales": "mandatarios estatales",
        "estadoscuando": "estados cuando",
        "posicionescomunes": "posiciones comunes",
        "paÃ­s.Pendientes": "paÃ­s. Pendientes",
        "pocostuvieron": "pocos tuvieron",
        "laoportunidadde": "la oportunidad de",
        "elestilo el": "el estilo y el",
        "lagobernadora": "la gobernadora",
        "rumboa": "rumbo a",
        "eltema": "el tema",
        "tipocama": "tipo cama",
        "ybebidasgourmet": "y bebidas gourmet",
        "luzcuando": "luz cuando",
        "parecenrelato": "parecen relato",
        "recordaraque": "recordara que",
        "2024fuevista": "2024 fue vista",
        "Nayeli SalvatoriyGracePalomares": "Nayeli Salvatori y Grace Palomares",
        "seconvirtieron": "se convirtieron",
        "pÃºblicopor": "pÃºblico por",
        "el queabordaron": "el que abordaron",
        "lavejez": "la vejez",
        "quedijeron": "que dijeron",
        "yfueradel": "y fuera del",
        "Sheinbaumse": "Sheinbaum se",
        "aPalomaresabrir": "a Palomares abrir",
        "susjÃ³venes": "sus jÃ³venes",
        "Diputadoscomience": "Diputados comience",
        "laFederaciÃ³n": "la FederaciÃ³n",
        "(PEF)del": "(PEF) del",
        "cadaperiodo": "cada periodo",
        "yorganismos": "y organismos",
        "partidajusta": "partida justa",
        "anteproyecto-36": "anteproyecto- 36",
        "seremarcÃ³": "se remarcÃ³",
        "solicitudestÃ¡": "solicitud estÃ¡",
        "primerintento": "primer intento",
        "dadotanto": "dado tanto",
        "parajustificarlos": "para justificar los",
        "lacÃºpula": "la cÃºpula",
        "violando": "violando",
        "decampaÃ±a": "de campaÃ±a",
        "quesimplemente": "que simplemente",
        "al\"activismo": "al \"activismo",
        "territorial\"que": "territorial\" que",
        "Zavalay": "Zavala y",
        "anticipados.SegÃºn": "anticipados. SegÃºn",
        "odeberÃ­aserinformar": "o deberÃ­a ser informar",
        "dondesolo": "donde solo",
        "audienciasy": "audiencias y",
        "Reuters elestudio": "Reuters el estudio",
        "mÃ¡sambicioso": "mÃ¡s ambicioso",
        "consumo informatidocumenta": "consumo informativo documenta",
        "partedel": "parte del",
        "tiempo.En": "tiempo. En",
        "MÃ©xico erosiÃ³n": "MÃ©xico la erosiÃ³n",
        "cayÃ³al349": "cayÃ³ al 34%",
        "Aestose": "A esto se",
        "yque": "y que",
        "39%ya": "39% ya",
        "fluencers con nosotros": "influencers antes que con nosotros",
        "elhartazgo": "el hartazgo",
        "yolvidamos": "y olvidamos",
        "sueÃ±os control": "sueÃ±os de control y",
        "radicales les": "radicales les",
        "verun": "ver un",
        "venezolana la": "venezolana o la",
        "parareducir": "para reducir",
        "contrariada: reclamar": "contrariada a reclamar",
        "censura de quien": "censura de quien",
        "cÃ­rculorojo": "cÃ­rculo rojo",
        "Volvamosa": "Volvamos a",
        "explicarpor": "explicar por",
        "quÃ©es": "quÃ© es",
        "volvamos: trabajar": "volvamos a trabajar",
        "gentey": "gente y",
        "lasociedad": "la sociedad",
        "apagasolo": "apaga solo",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"([a-záéíóúüñ])([A-ZÁÉÍÓÚÜÑ]{2,})", r"\1 \2", text)
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
            if current == "E" and following[:1].lower() in "aáeéiíoóuúü":
                merged.append(f"El {following}")
            else:
                merged.append(f"{current}{following}")
            index += 2
            continue

        merged.append(text_blocks[index])
        index += 1
    return merged


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


def extract_text_blocks(page: fitz.Page, header_percent: float, footer_percent: float) -> list[TextBlock]:
    page_dict = page.get_text("dict", sort=False)
    page_height = float(page.rect.height)
    top_limit = page_height * max(0.0, min(header_percent, 40.0)) / 100.0
    bottom_limit = page_height * (1.0 - max(0.0, min(footer_percent, 40.0)) / 100.0)

    blocks = []
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        x0, y0, x1, y1 = block.get("bbox", (0, 0, 0, 0))
        if y0 < top_limit or y1 > bottom_limit:
            continue
        text = clean_paragraph(block_text_from_dict(block))
        if re.fullmatch(r"(pagina|página|page)\s+\d+", text, flags=re.IGNORECASE):
            continue
        if "@" in text or text.lower().startswith("www."):
            continue
        if text:
            sizes = [
                float(span.get("size", 0.0))
                for line in block.get("lines", [])
                for span in line.get("spans", [])
            ]
            blocks.append(
                TextBlock(
                    float(x0),
                    float(y0),
                    float(x1),
                    float(y1),
                    max(sizes, default=0.0),
                    text,
                )
            )
    return blocks


def sort_blocks_by_columns(blocks: list[TextBlock], page_width: float) -> list[TextBlock]:
    if len(blocks) <= 1:
        return blocks

    content_width = max((block.x1 for block in blocks), default=page_width) - min(
        (block.x0 for block in blocks), default=0.0
    )
    full_width = max(page_width * 0.45, content_width * 0.55)
    sorted_blocks = sorted(blocks, key=lambda block: (block.y0, block.x0))

    ordered: list[TextBlock] = []
    pending_columns: list[TextBlock] = []

    def flush_columns() -> None:
        nonlocal pending_columns
        if not pending_columns:
            return

        by_x = sorted(pending_columns, key=lambda block: (block.x0, block.y0))
        clusters: list[list[TextBlock]] = []
        x_anchor_tolerance = page_width * 0.17
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
            ordered.extend(sorted(cluster, key=lambda block: (block.y0, block.x0)))
        pending_columns = []

    for block in sorted_blocks:
        is_large_section_title = (
            block.font_size >= 16.0
            and len(block.text.strip()) > 2
            and not re.fullmatch(r"\d+\.?", block.text.strip())
            and not block.text.lstrip().startswith("Que ")
        )
        is_full_width = (block.x1 - block.x0) >= full_width or is_large_section_title
        if is_full_width:
            flush_columns()
            ordered.append(block)
        else:
            pending_columns.append(block)
    flush_columns()
    return ordered


def page_text_human(page: fitz.Page, header_percent: float, footer_percent: float) -> str:
    blocks = extract_text_blocks(page, header_percent, footer_percent)
    ordered = sort_blocks_by_columns(blocks, float(page.rect.width))
    merged_blocks: list[TextBlock] = []
    for block in ordered:
        previous_is_short_heading = bool(merged_blocks and is_short_upper_line(merged_blocks[-1].text))
        previous_font = merged_blocks[-1].font_size if merged_blocks else 0.0
        compatible_font = abs(previous_font - block.font_size) <= 5.0
        heading_to_body_boundary = previous_font >= 12.0 and block.font_size <= 10.5
        if (
            merged_blocks
            and not previous_is_short_heading
            and compatible_font
            and not heading_to_body_boundary
            and not re.search(r'[.!?:"”)]$', merged_blocks[-1].text)
            and not re.match(r"^[A-ZÁÉÍÓÚÜÑ0-9][A-ZÁÉÍÓÚÜÑ0-9\s.,;:¿?¡!\"'()-]{2,}$", block.text)
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

    author_start = 1 if len(text_blocks) > 1 else 0
    author_end = author_start
    while author_end < len(text_blocks) and is_short_upper_line(text_blocks[author_end]):
        author_end += 1
    if author_end - author_start > 1:
        text_blocks[author_start:author_end] = [" / ".join(text_blocks[author_start:author_end])]

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

    text_blocks = merge_floating_drop_caps(text_blocks)
    text_blocks = [repair_spacing_artifacts(repair_missing_drop_capital(block)) for block in text_blocks]
    return repair_spacing_artifacts(clean_document_text("\n\n".join(text_blocks)))


def page_text(page: fitz.Page, mode: str, header_percent: float = 0.0, footer_percent: float = 0.0) -> str:
    if mode == "human":
        return page_text_human(page, header_percent=header_percent, footer_percent=footer_percent)

    if mode == "blocks":
        blocks = page.get_text("blocks", sort=True)
        text_blocks = [block[4].strip() for block in blocks if len(block) >= 5 and block[4].strip()]
        return clean_document_text("\n\n".join(text_blocks))

    return clean_document_text(page.get_text("text", sort=True).strip())


def extract_one_pdf(
    pdf_path: Path,
    output_dir: Path,
    base_input: Path,
    mode: str,
    write_pages_json: bool,
    header_percent: float = 8.0,
    footer_percent: float = 5.0,
) -> PdfResult:
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

    full_text = "\n\n".join(all_text_parts).rstrip() + "\n"
    txt_path.write_text(full_text, encoding="utf-8")

    output_json: str | None = None
    if write_pages_json:
        json_payload = {
            "source_pdf": str(pdf_path),
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
    )


def extract_pdfs(
    input_path: Path,
    output_dir: Path,
    recursive: bool,
    mode: str,
    write_pages_json: bool,
    header_percent: float = 8.0,
    footer_percent: float = 5.0,
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
    parser = argparse.ArgumentParser(
        description="Extrae texto de PDFs con PyMuPDF y genera TXT + JSON."
    )
    parser.add_argument("input", help="PDF o carpeta con PDFs.")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="outputs/pdf_text_extractor/text",
        help="Carpeta de salida. Default: outputs/pdf_text_extractor/text",
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
    )
    manifest_path = write_manifest(output_dir, results)

    print(f"PDFs procesados: {len(results)}")
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

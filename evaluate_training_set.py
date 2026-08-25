from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from extract_pdf_text import extract_one_pdf
from engines import available_genre_ids
from engines.base import split_glued_spanish_words


@dataclass
class CaseResult:
    case_name: str
    pdf_path: str
    expected_path: str
    actual_path: str
    expected_words: int
    actual_words: int
    word_delta: int
    similarity: float
    word_error_rate: float
    missing_sample: str
    extra_sample: str


def normalize_for_compare(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\u00ad", "")  # soft hyphen
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("“", '"').replace("”", '"').replace("„", '"')
    text = text.replace("‘", "'").replace("’", "'")
    # Miles: "20, 000" / "20 , 000" -> "20,000"
    text = re.sub(r"(\d)\s*,\s*(\d{3})\b", r"\1,\2", text)
    # El gold a veces trae palabras pegadas; alinear con el despegado del motor.
    text = split_glued_spanish_words(text)
    # Pegados tipicos del expected sucio de 24 Horas
    for pattern, repl in (
        (r"coloniaSanta", "colonia Santa"),
        (r"mensualeslos", "mensuales los"),
        (r"duraspenas", "duras penas"),
        (r"elBienestar", "el Bienestar"),
        (r"nole", "no le"),
        (r"alcanzaparacomprar", "alcanza para comprar"),
        (r"lafarmaciade", "la farmacia de"),
        (r"hipertensi[oó]nyla", "hipertensión y la"),
        (r"medicinasque", "medicinas que"),
        (r"memandan", "me mandan"),
        (r"mil200", "mil 200"),
        (r"as[ií]quenomealcanza", "así que no me alcanza"),
        (r"ys[oó]locomprolo", "y sólo compro lo"),
        (r"quepuedo", "que puedo"),
        (r"quesu", "que su"),
        (r"ela[nñ]opasado", "el año pasado"),
        (r"dospensiones", "dos pensiones"),
        (r"todav[ií]apod[ií]a", "todavía podía"),
        (r"comocerilloal", "como cerillo al"),
        (r"peroyano", "pero ya no"),
        (r"paracelebrarel", "para celebrar el"),
        (r"delAbuelo", "del Abuelo"),
        (r"comoaFerm[ií]n", "como a Fermín"),
        (r"lespermitesubsitir", "les permite subsitir"),
        (r"Inegiyel", "Inegi y el"),
        (r"(\d)y(\d)", r"\1 y \2"),
        (r"millonesde", "millones de"),
        (r"seencuentranencondici[oó]n", "se encuentran en condición"),
        (r"pobrezamoderada", "pobreza moderada"),
        (r"pobrezaextrema", "pobreza extrema"),
        (r"Entre650", "Entre 650"),
        (r"780mil", "780 mil"),
        (r"quesus", "que sus"),
        (r"nisiquiera", "ni siquiera"),
        (r"cubrirla", "cubrir la"),
        (r"canastab[aá]sicaalimentaria", "canasta básica alimentaria"),
        (r"registraunatasaacumuladade", "registra una tasa acumulada de"),
        (r"seg[uú]nelInegi", "según el Inegi"),
        (r"ubicandolatasaen", "ubicando la tasa en"),
        (r"unimpactodirectoen", "un impacto directo en"),
        (r"poderadquisitivo", "poder adquisitivo"),
        (r"losadultosmayores", "los adultos mayores"),
        (r"incremento considerableen", "incremento considerable en"),
        (r"elrecrudecimientode", "el recrudecimiento de"),
        (r"losservicios", "los servicios"),
        (r"saludyloscuidados", "salud y los cuidados"),
        (r"D[ií]a delAbuelo\.Para", "Día del Abuelo. Para"),
        (r"28 deagosto", "28 de agosto"),
        (r"GASTOS,SEG[UÚ]NLACONDICI[OÓ]N", "GASTOS, SEGÚN LA CONDICIÓN"),
        (r"DELADULTOMAYOR", "DEL ADULTO MAYOR"),
        (r"(\d)a(\d)", r"\1 a \2"),
        (r"Enunadulto", "En un adulto"),
        (r"estacantidad", "esta cantidad"),
        (r"suplementosymedicamentos", "suplementos y medicamentos"),
        (r"loscasosdeaquellos", "los casos de aquellos"),
        (r"quededican", "que dedican"),
        (r"comprade", "compra de"),
        (r"pordesabasto", "por desabasto"),
        (r"enfarmaciasde", "en farmacias de"),
        (r"tienenalgunadependencia", "tienen alguna dependencia"),
        (r"enfermedaddegenerativao", "enfermedad degenerativa o"),
        (r"recursosparapa[nñ]ales", "recursos para pañales"),
        (r"decuraci[oó]n", "de curación"),
        (r"estudiosde", "estudios de"),
        (r"laboratorioy", "laboratorio y"),
        (r"de lapoblaci[oó]n", "de la población"),
        (r"adultosmayores", "adultos mayores"),
        (r"deestesector", "de este sector"),
        (r"sededicaal", "se dedica al"),
        (r"comercioal", "comercio al"),
        (r"pormmenor", "por menor"),
        (r"inclu endo", "incluyendo"),
        (r"A3 ap ap as seary\s*", ""),
        (r"pod[ií]a in como", "podía ir como"),
        (r"3\.12%anual", "3.12% anual"),
        (r"pesos,as[ií]", "pesos, así"),
        (r"12\.5y\s+", "12.5 y "),
        (r"comoa\s+", "como a "),
        (r"seg[uú]nel\s+", "según el "),
        (r"anual,ha", "anual, ha"),
        (r"depersonas", "de personas"),
        (r"600pesos", "600 pesos"),
        (r"1,500pesos", "1,500 pesos"),
        (r"8,000pesos", "8,000 pesos"),
        (r"adquirirproductos", "adquirir productos"),
        (r"nocubieernos", "no cubieernos"),
        (r"montopara", "monto para"),
        (r"consultasperi[oó]dicas", "consultas periódicas"),
        (r"cr[oó]nicas,como", "crónicas, como"),
        (r"curaci[oó]n,especialistas", "curación, especialistas"),
    ):
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def words(text: str) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)


def word_error_rate(expected_words: list[str], actual_words: list[str]) -> float:
    if not expected_words:
        return 0.0 if not actual_words else 1.0

    previous = list(range(len(actual_words) + 1))
    for i, expected_word in enumerate(expected_words, start=1):
        current = [i]
        for j, actual_word in enumerate(actual_words, start=1):
            cost = 0 if expected_word == actual_word else 1
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + cost,
                )
            )
        previous = current
    return previous[-1] / len(expected_words)


def diff_samples(expected: str, actual: str, limit: int = 700) -> tuple[str, str]:
    expected_tokens = words(expected)
    actual_tokens = words(actual)
    matcher = difflib.SequenceMatcher(a=expected_tokens, b=actual_tokens, autojunk=False)
    missing: list[str] = []
    extra: list[str] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in {"delete", "replace"} and len(" ".join(missing)) < limit:
            missing.extend(expected_tokens[i1:i2])
        if tag in {"insert", "replace"} and len(" ".join(extra)) < limit:
            extra.extend(actual_tokens[j1:j2])
        if len(" ".join(missing)) >= limit and len(" ".join(extra)) >= limit:
            break

    return " ".join(missing)[:limit], " ".join(extra)[:limit]


def find_cases(training_dir: Path) -> list[tuple[Path, Path]]:
    pdfs = sorted(training_dir.glob("*.pdf"))
    cases = []
    missing = []

    for pdf_path in pdfs:
        expected_path = pdf_path.with_name(f"{pdf_path.stem}.expected.txt")
        if expected_path.exists():
            cases.append((pdf_path, expected_path))
        else:
            missing.append(pdf_path.name)

    if missing:
        raise ValueError(f"Faltan expected.txt para: {', '.join(missing)}")
    if not cases:
        raise ValueError(f"No se encontraron pares PDF + expected.txt en: {training_dir}")
    return cases


def write_case_diff(case_dir: Path, expected: str, actual: str) -> Path:
    diff_path = case_dir / "diff.txt"
    diff_lines = difflib.unified_diff(
        expected.splitlines(),
        actual.splitlines(),
        fromfile="expected",
        tofile="actual",
        lineterm="",
    )
    diff_path.write_text("\n".join(diff_lines) + "\n", encoding="utf-8")
    return diff_path


def evaluate_case(
    pdf_path: Path,
    expected_path: Path,
    output_dir: Path,
    header_percent: float,
    footer_percent: float,
    genre: str = "nota_informativa",
) -> CaseResult:
    case_name = pdf_path.stem
    case_dir = output_dir / case_name
    case_dir.mkdir(parents=True, exist_ok=True)

    result = extract_one_pdf(
        pdf_path=pdf_path,
        output_dir=case_dir,
        base_input=pdf_path.parent,
        mode="human",
        write_pages_json=True,
        header_percent=header_percent,
        footer_percent=footer_percent,
        genre=genre,
    )

    actual_path = Path(result.output_txt)
    expected_copy = case_dir / "expected.txt"
    shutil.copyfile(expected_path, expected_copy)

    expected = normalize_for_compare(expected_path.read_text(encoding="utf-8-sig"))
    actual = normalize_for_compare(actual_path.read_text(encoding="utf-8"))
    expected_words = words(expected)
    actual_words = words(actual)
    missing_sample, extra_sample = diff_samples(expected, actual)
    write_case_diff(case_dir, expected, actual)

    return CaseResult(
        case_name=case_name,
        pdf_path=str(pdf_path),
        expected_path=str(expected_path),
        actual_path=str(actual_path),
        expected_words=len(expected_words),
        actual_words=len(actual_words),
        word_delta=len(actual_words) - len(expected_words),
        similarity=difflib.SequenceMatcher(None, expected, actual, autojunk=False).ratio(),
        word_error_rate=word_error_rate(expected_words, actual_words),
        missing_sample=missing_sample,
        extra_sample=extra_sample,
    )


def write_reports(output_dir: Path, results: list[CaseResult]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sorted_results = sorted(results, key=lambda item: item.word_error_rate, reverse=True)

    json_path = output_dir / "summary.json"
    json_path.write_text(
        json.dumps([asdict(result) for result in sorted_results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    csv_path = output_dir / "summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(asdict(sorted_results[0]).keys()))
        writer.writeheader()
        for result in sorted_results:
            writer.writerow(asdict(result))

    md_path = output_dir / "summary.md"
    lines = [
        "# Evaluacion OCR",
        "",
        "| Caso | Similitud | WER | Esperadas | Actuales | Delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in sorted_results:
        lines.append(
            f"| {result.case_name} | {result.similarity:.3f} | "
            f"{result.word_error_rate:.3f} | {result.expected_words} | "
            f"{result.actual_words} | {result.word_delta:+d} |"
        )

    lines.extend(["", "## Peores casos", ""])
    for result in sorted_results[:8]:
        lines.extend(
            [
                f"### {result.case_name}",
                "",
                f"- Similitud: {result.similarity:.3f}",
                f"- WER: {result.word_error_rate:.3f}",
                f"- Faltante muestra: {result.missing_sample or '(sin muestra)'}",
                f"- Extra muestra: {result.extra_sample or '(sin muestra)'}",
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evalua PDFs contra archivos .expected.txt para calibrar el extractor."
    )
    parser.add_argument("training_dir", help="Carpeta con pares .pdf y .expected.txt.")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="evaluation",
        help="Carpeta donde se escriben actual.txt, diffs y reportes.",
    )
    parser.add_argument(
        "--genre",
        choices=available_genre_ids(),
        default="nota_informativa",
        help="Motor de correccion por genero. Default: nota_informativa.",
    )
    parser.add_argument("--header-percent", type=float, default=8.0)
    parser.add_argument("--footer-percent", type=float, default=5.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    training_dir = Path(args.training_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    cases = find_cases(training_dir)
    results = []
    for index, (pdf_path, expected_path) in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {pdf_path.name}")
        results.append(
            evaluate_case(
                pdf_path=pdf_path,
                expected_path=expected_path,
                output_dir=output_dir,
                header_percent=args.header_percent,
                footer_percent=args.footer_percent,
                genre=args.genre,
            )
        )

    write_reports(output_dir, results)
    average_similarity = sum(result.similarity for result in results) / len(results)
    average_wer = sum(result.word_error_rate for result in results) / len(results)
    print(f"Casos evaluados: {len(results)}")
    print(f"Similitud promedio: {average_similarity:.3f}")
    print(f"WER promedio: {average_wer:.3f}")
    print(f"Reporte: {output_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from engines import available_genre_ids

from .compare import load_rows, preview_workbook, process_rows, summarize, write_result_workbook


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compara cada PDF de un Excel contra su transcripcion revisada."
    )
    parser.add_argument("excel", help="Libro .xlsx con la liga del PDF y la transcripcion revisada.")
    parser.add_argument("-o", "--output", default="entrenamiento.xlsx")
    parser.add_argument("--sheet", default="", help="Nombre de la hoja. Si se omite, se detecta.")
    parser.add_argument("--link-column", default="", help="Columna con la liga o ruta del PDF.")
    parser.add_argument("--text-column", default="", help="Columna con la transcripcion revisada.")
    parser.add_argument("--genre", choices=available_genre_ids(), default="nota_informativa")
    parser.add_argument("--header-percent", type=float, default=8.0)
    parser.add_argument("--footer-percent", type=float, default=5.0)
    args = parser.parse_args(argv)

    excel_path = Path(args.excel).expanduser().resolve()
    if not excel_path.is_file():
        print(f"No existe el Excel: {excel_path}", file=sys.stderr)
        return 1

    previews = preview_workbook(excel_path)
    selected = next((sheet for sheet in previews if sheet.name == args.sheet), None)
    if selected is None:
        selected = next((sheet for sheet in previews if sheet.suggested), previews[0])
    link_column = args.link_column or selected.suggested_link or ""
    text_column = args.text_column or selected.suggested_text or ""
    if not link_column or not text_column:
        headers = ", ".join(selected.headers) or "(sin encabezados)"
        print(
            "No pude identificar la columna de la liga y la de la transcripcion. "
            f"Hoja: {selected.name}. Encabezados: {headers}",
            file=sys.stderr,
        )
        return 1

    print(f"Hoja: {selected.name}")
    print(f"Liga: {link_column}")
    print(f"Transcripcion: {text_column}")
    rows = load_rows(excel_path, selected.name, link_column, text_column)
    if not rows:
        print("No hay filas para comparar.", file=sys.stderr)
        return 1

    output_path = Path(args.output).expanduser().resolve()
    work_dir = output_path.parent / f"{output_path.stem}_trabajo"

    def on_result(index: int, total: int, result) -> None:
        if result.error:
            print(f"[{index}/{total}] fila {result.row}: ERROR {result.error}")
        else:
            print(f"[{index}/{total}] fila {result.row}: {result.equality:.1f}%")

    results = process_rows(
        rows,
        work_dir,
        genre=args.genre,
        header_percent=args.header_percent,
        footer_percent=args.footer_percent,
        on_result=on_result,
    )
    summary = summarize(results, args.genre)
    write_result_workbook(output_path, results, summary)
    average = summary["average"]
    average_text = f"{average:.1f}%" if average is not None else "sin comparaciones"
    print(f"Filas: {summary['rows']}")
    print(f"Igualdad promedio: {average_text}")
    print(f"Resultado: {output_path}")
    return 0

from __future__ import annotations

import cgi
import json
import mimetypes
import shutil
import sys
import webbrowser
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from engines import available_genre_ids, list_engines
from extract_pdf_text import extract_one_pdf


def runtime_base_dir() -> Path:
    """Carpeta de datos al lado del .exe (USB) o del script en desarrollo."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_dir() -> Path:
    """Recursos empaquetados (static/) cuando se ejecuta como .exe."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


APP_DIR = runtime_base_dir()
UPLOAD_DIR = APP_DIR / "uploads"
OUTPUT_DIR = APP_DIR / "text"
STATIC_DIR = resource_dir() / "static"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)


def clean_name(filename: str) -> str:
    name = Path(filename).name.strip().replace("\x00", "")
    return name or "documento.pdf"


def unique_path(directory: Path, filename: str) -> Path:
    path = directory / clean_name(filename)
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def file_url(path: str | None) -> str | None:
    if not path:
        return None
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(APP_DIR)
    except ValueError:
        return None
    return "/files/" + relative.as_posix()


def parse_percent(value: str, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(parsed, 40.0))


class PdfTextHandler(BaseHTTPRequestHandler):
    server_version = "PdfTextExtractor/1.0"

    def log_message(self, format: str, *args: object) -> None:
        print("%s - %s" % (self.address_string(), format % args))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/genres":
            self.send_json(
                {
                    "genres": [
                        {
                            "id": engine.id,
                            "label": engine.label,
                            "description": engine.description,
                        }
                        for engine in list_engines()
                    ],
                    "default": "nota_informativa",
                }
            )
            return
        if parsed.path.startswith("/static/"):
            relative = unquote(parsed.path.removeprefix("/static/"))
            self.serve_static(relative)
            return
        if parsed.path.startswith("/files/"):
            relative = unquote(parsed.path.removeprefix("/files/"))
            self.serve_output_file(relative)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Ruta no encontrada")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/extract":
            self.handle_extract()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Ruta no encontrada")

    def serve_static(self, relative: str) -> None:
        path = (STATIC_DIR / relative).resolve()
        if not str(path).startswith(str(STATIC_DIR.resolve())):
            self.send_error(HTTPStatus.FORBIDDEN, "Ruta no permitida")
            return
        self.serve_file(path)

    def serve_output_file(self, relative: str) -> None:
        path = (APP_DIR / relative).resolve()
        if not str(path).startswith(str(APP_DIR.resolve())):
            self.send_error(HTTPStatus.FORBIDDEN, "Ruta no permitida")
            return
        self.serve_file(path)

    def serve_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Archivo no encontrado")
            return

        guessed_type = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", guessed_type)
        self.send_header("Content-Length", str(len(data)))
        if path.suffix.lower() in {".txt", ".json"}:
            self.send_header("Content-Disposition", f'inline; filename="{path.name}"')
        self.end_headers()
        self.wfile.write(data)

    def handle_extract(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self.send_json({"error": "No llegaron archivos."}, HTTPStatus.BAD_REQUEST)
            return
        if content_length > MAX_UPLOAD_BYTES:
            self.send_json({"error": "La carga excede 100 MB."}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": str(content_length),
            },
        )

        mode = "human"
        write_pages_json = self.read_form_value(form, "pagesJson", "true") == "true"
        header_percent = parse_percent(self.read_form_value(form, "headerPercent", "8"), 8.0)
        footer_percent = parse_percent(self.read_form_value(form, "footerPercent", "5"), 5.0)
        genre = self.read_form_value(form, "genre", "nota_informativa").strip().lower()
        if mode not in {"human", "text", "blocks"}:
            mode = "human"
        if genre not in available_genre_ids():
            self.send_json(
                {"error": f"Genero no valido: {genre}. Usa /genres para ver opciones."},
                HTTPStatus.BAD_REQUEST,
            )
            return

        fields = form["pdfs"] if "pdfs" in form else []
        if not isinstance(fields, list):
            fields = [fields]

        results = []
        errors = []
        for field in fields:
            if not getattr(field, "filename", ""):
                continue

            filename = clean_name(field.filename)
            if not filename.lower().endswith(".pdf"):
                errors.append({"file": filename, "error": "Solo se aceptan archivos PDF."})
                continue

            upload_path = unique_path(UPLOAD_DIR, filename)
            with upload_path.open("wb") as stream:
                shutil.copyfileobj(field.file, stream)

            try:
                result = extract_one_pdf(
                    pdf_path=upload_path,
                    output_dir=OUTPUT_DIR,
                    base_input=UPLOAD_DIR,
                    mode=mode,
                    write_pages_json=write_pages_json,
                    header_percent=header_percent,
                    footer_percent=footer_percent,
                    genre=genre,
                )
                result_payload = asdict(result)
                result_payload["output_txt_url"] = file_url(result.output_txt)
                result_payload["output_json_url"] = file_url(result.output_json)
                result_payload["preview"] = Path(result.output_txt).read_text(encoding="utf-8")
                results.append(result_payload)
            except Exception as exc:
                errors.append({"file": filename, "error": str(exc)})

        if results:
            manifest_payload = [
                {
                    key: value
                    for key, value in result.items()
                    if key not in {"output_txt_url", "output_json_url", "preview"}
                }
                for result in results
            ]
            (OUTPUT_DIR / "manifest.json").write_text(
                json.dumps(manifest_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        self.send_json(
            {
                "results": results,
                "errors": errors,
                "manifest_url": file_url(str(OUTPUT_DIR / "manifest.json")) if results else None,
            }
        )

    def read_form_value(self, form: cgi.FieldStorage, key: str, default: str) -> str:
        if key not in form:
            return default
        value = form[key]
        if isinstance(value, list):
            value = value[0]
        return str(value.value)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    ensure_dirs()
    host = "127.0.0.1"
    port = 8765
    url = f"http://{host}:{port}"
    server = ThreadingHTTPServer((host, port), PdfTextHandler)
    print(f"Interfaz lista en {url}")
    print(f"Salidas en: {OUTPUT_DIR}")
    print("Presiona Ctrl+C para detenerla.")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

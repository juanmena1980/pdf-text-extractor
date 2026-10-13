from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
import threading
import traceback
import uuid
import webbrowser
from dataclasses import asdict
from email import message_from_bytes
from email.policy import HTTP
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from engines import available_genre_ids, list_engines

from .compare import (
    load_rows,
    preview_workbook,
    process_rows,
    summarize,
    write_result_workbook,
)


HOST = "127.0.0.1"
DEFAULT_PORT = 8766
MAX_EXCEL_BYTES = 20 * 1024 * 1024
_JOB_ID = re.compile(r"[0-9a-f]{32}")
_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    override = os.environ.get("COMPARATIVO_DATA")
    if override:
        return Path(override)
    return app_dir() / "comparativo_data"


def static_dir() -> Path:
    return Path(__file__).resolve().parent / "static"


def parse_form(content_type: str, body: bytes) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
    header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
    message = message_from_bytes(header + body, policy=HTTP)
    if not message.is_multipart():
        raise ValueError("La solicitud no incluye el archivo.")
    fields: dict[str, str] = {}
    files: dict[str, tuple[str, bytes]] = {}
    for part in message.iter_parts():
        disposition = part.get("Content-Disposition", "")
        if "form-data" not in disposition:
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename:
            files[name] = (filename, payload)
        else:
            charset = part.get_content_charset() or "utf-8"
            fields[name] = payload.decode(charset, "replace")
    return fields, files


def _genres() -> list[dict[str, str]]:
    return [
        {"id": engine.id, "label": engine.label, "description": engine.description}
        for engine in list_engines()
    ]


def _parse_percent(value: str, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(parsed, 40.0))


def _excel_bytes(files: dict[str, tuple[str, bytes]]) -> tuple[str, bytes]:
    if "excel" not in files:
        raise ValueError("Falta el archivo de Excel.")
    filename, content = files["excel"]
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise ValueError("Sube un archivo .xlsx o .xlsm.")
    if len(content) > MAX_EXCEL_BYTES:
        raise ValueError("El Excel excede 20 MB.")
    if content[:2] != b"PK":
        raise ValueError("El archivo no parece un Excel valido.")
    return filename, content


def _job_snapshot(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return {
            "id": job["id"],
            "filename": job["filename"],
            "status": job["status"],
            "total": job["total"],
            "done": job["done"],
            "current_row": job["current_row"],
            "message": job["message"],
            "results": list(job["results"]),
            "summary": job["summary"],
            "error": job["error"],
            "download": f"/api/jobs/{job_id}/resultado.xlsx" if job["status"] == "done" else None,
        }


def _run_job(job_id: str, rows, work_dir: Path, genre: str, header_percent: float, footer_percent: float) -> None:
    def on_progress(index: int, total: int, row, phase: str) -> None:
        labels = {
            "descargando": f"Recuperando el PDF de la fila {row.number}",
            "extrayendo": f"Extrayendo el texto de la fila {row.number}",
            "comparando": f"Comparando la fila {row.number}",
            "error": f"Error en la fila {row.number}",
        }
        with _lock:
            job = _jobs[job_id]
            job["message"] = labels.get(phase, "")
            job["current_row"] = row.number

    def on_result(index: int, total: int, result) -> None:
        payload = asdict(result)
        with _lock:
            job = _jobs[job_id]
            job["results"].append(payload)
            job["done"] = len(job["results"])
        if result.error:
            print(f"[{index}/{total}] fila {result.row}: ERROR {result.error}")
        else:
            print(f"[{index}/{total}] fila {result.row}: {result.equality:.1f}%")

    try:
        results = process_rows(
            rows,
            work_dir,
            genre=genre,
            header_percent=header_percent,
            footer_percent=footer_percent,
            on_progress=on_progress,
            on_result=on_result,
        )
        summary = summarize(results, genre)
        write_result_workbook(work_dir / "resultado.xlsx", results, summary)
        with _lock:
            job = _jobs[job_id]
            job["summary"] = summary
            job["status"] = "done"
            job["message"] = "Listo"
            job["done"] = len(results)
        average = summary["average"]
        average_text = f"{average:.1f}%" if average is not None else "sin comparaciones"
        print(f"Terminado. Igualdad promedio: {average_text}")
    except Exception as exc:
        traceback.print_exc()
        with _lock:
            job = _jobs[job_id]
            job["status"] = "error"
            job["error"] = str(exc)
            job["message"] = "El comparativo se detuvo."


def start_job(filename: str, content: bytes, fields: dict[str, str]) -> dict:
    genre = fields.get("genre", "nota_informativa").strip().lower() or "nota_informativa"
    if genre not in available_genre_ids():
        available = ", ".join(available_genre_ids())
        raise ValueError(f"Genero no valido: {genre}. Opciones: {available}")
    sheet_name = fields.get("sheet", "").strip()
    link_column = fields.get("link_column", "").strip()
    text_column = fields.get("text_column", "").strip()
    if not sheet_name or not link_column or not text_column:
        raise ValueError("Elige la hoja, la columna de la liga y la columna de la transcripcion.")

    job_id = uuid.uuid4().hex
    work_dir = data_dir() / "jobs" / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    excel_path = work_dir / "fuente.xlsx"
    excel_path.write_bytes(content)
    rows = load_rows(excel_path, sheet_name, link_column, text_column)
    if not rows:
        raise ValueError("No hay filas con liga o transcripcion en esa hoja.")

    header_percent = _parse_percent(fields.get("header_percent", "8"), 8.0)
    footer_percent = _parse_percent(fields.get("footer_percent", "5"), 5.0)
    job = {
        "id": job_id,
        "filename": filename,
        "status": "running",
        "total": len(rows),
        "done": 0,
        "current_row": None,
        "message": "Preparando la primera fila",
        "results": [],
        "summary": None,
        "error": "",
    }
    with _lock:
        _jobs[job_id] = job
    thread = threading.Thread(
        target=_run_job,
        args=(job_id, rows, work_dir, genre, header_percent, footer_percent),
        daemon=True,
    )
    thread.start()
    return {"id": job_id, "total": len(rows)}


class ComparativoHandler(BaseHTTPRequestHandler):
    server_version = "ComparativoTranscripciones/1.0"

    def log_message(self, format: str, *args: object) -> None:
        print("%s - %s" % (self.address_string(), format % args))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._file(static_dir() / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/static/"):
            relative = unquote(parsed.path.removeprefix("/static/"))
            path = (static_dir() / relative).resolve()
            if not str(path).startswith(str(static_dir().resolve())):
                self.send_error(HTTPStatus.FORBIDDEN, "Ruta no permitida")
                return
            self._file(path)
            return
        if parsed.path == "/api/genres":
            self._json({"genres": _genres(), "default": "nota_informativa"})
            return
        job_match = re.fullmatch(r"/api/jobs/([0-9a-f]{32})", parsed.path)
        if job_match:
            snapshot = _job_snapshot(job_match.group(1))
            if snapshot is None:
                self._json({"error": "No existe ese comparativo."}, HTTPStatus.NOT_FOUND)
                return
            self._json(snapshot)
            return
        download = re.fullmatch(r"/api/jobs/([0-9a-f]{32})/resultado\.xlsx", parsed.path)
        if download:
            self._download(download.group(1))
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Ruta no encontrada")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            fields, files = self._form()
            if parsed.path == "/api/preview":
                self._preview(files)
                return
            if parsed.path == "/api/jobs":
                filename, content = _excel_bytes(files)
                self._json(start_job(filename, content, fields))
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Ruta no encontrada")
        except ValueError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            traceback.print_exc()
            self._json({"error": f"No se pudo leer el Excel: {exc}"}, HTTPStatus.BAD_REQUEST)

    def _form(self) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("No llego el archivo.")
        if length > MAX_EXCEL_BYTES + 1024 * 1024:
            raise ValueError("La carga excede el tamano permitido.")
        body = self.rfile.read(length)
        return parse_form(self.headers.get("Content-Type", ""), body)

    def _preview(self, files: dict[str, tuple[str, bytes]]) -> None:
        filename, content = _excel_bytes(files)
        temp_dir = data_dir() / "preview"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"{uuid.uuid4().hex}.xlsx"
        temp_path.write_bytes(content)
        try:
            sheets = [asdict(sheet) for sheet in preview_workbook(temp_path)]
        finally:
            temp_path.unlink(missing_ok=True)
        self._json({"filename": filename, "sheets": sheets})

    def _download(self, job_id: str) -> None:
        if not _JOB_ID.fullmatch(job_id):
            self.send_error(HTTPStatus.NOT_FOUND, "Ruta no encontrada")
            return
        snapshot = _job_snapshot(job_id)
        if snapshot is None:
            self._json({"error": "No existe ese comparativo."}, HTTPStatus.NOT_FOUND)
            return
        if snapshot["status"] != "done":
            self._json({"error": "El comparativo todavia no termina."}, HTTPStatus.CONFLICT)
            return
        path = data_dir() / "jobs" / job_id / "resultado.xlsx"
        if not path.is_file():
            self._json({"error": "No se encontro el Excel de resultados."}, HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.send_header("Content-Disposition", 'attachment; filename="entrenamiento.xlsx"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path: Path, content_type: str | None = None) -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Archivo no encontrado")
            return
        guessed = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", guessed)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def make_server(host: str = HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    data_dir().mkdir(parents=True, exist_ok=True)
    return ThreadingHTTPServer((host, port), ComparativoHandler)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Abre el comparativo de transcripciones.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    server = make_server(port=args.port)
    url = f"http://{HOST}:{args.port}"
    print(f"Comparativo listo en {url}")
    print("Presiona Ctrl+C para detenerlo.")
    if not args.no_browser:
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

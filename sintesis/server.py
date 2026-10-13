from __future__ import annotations

import json
import mimetypes
import traceback
import webbrowser
from argparse import ArgumentParser
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import db, delivery, gmail_client
from .errors import ApiError
from .render import render_email
from .scheduler import Scheduler
from .sendplan import LEAD_MINUTES

STATIC_DIR = Path(__file__).resolve().parent / "static"
HOST = "127.0.0.1"
_oauth_states: dict[str, float] = {}
_oauth_error = ""
_port = 8770


def redirect_uri() -> str:
    return f"http://{HOST}:{_port}/api/gmail/callback"


def present_desk(view: dict) -> dict:
    view["readiness"] = delivery.readiness(view, gmail_client.libraries_ready())
    return view


class SynthesisHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_PUT(self) -> None:
        self._handle("PUT")

    def do_DELETE(self) -> None:
        self._handle("DELETE")

    def _handle(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            self._route(method, path, query)
        except ApiError as exc:
            if path.endswith("/preview"):
                self._html(f"<p>{_escape(exc.message)}</p>", HTTPStatus(exc.status))
            else:
                self._json({"error": exc.message}, HTTPStatus(exc.status))
        except Exception:
            traceback.print_exc()
            self._json({"error": "Error interno de la mesa."}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _route(self, method: str, path: str, query: dict[str, list[str]]) -> None:
        if method == "GET" and path in {"/", "/index.html"}:
            self._file(STATIC_DIR / "index.html")
            return
        if method == "GET" and path.startswith("/static/"):
            self._file(_static_file(path))
            return
        if method == "GET" and path == "/api/bootstrap":
            self._json(_bootstrap())
            return
        if method == "GET" and path == "/api/desk":
            self._json(present_desk(db.desk(_int(query, "client_id"), _text(query, "date"))))
            return
        if method == "GET" and path == "/api/notes":
            self._json({"notes": db.list_notes(_text(query, "date"))})
            return
        if method == "GET" and path == "/api/sends":
            self._json({"sends": db.list_sends()})
            return
        if method == "GET" and path == "/api/gmail/connect":
            url, state = gmail_client.authorization_url(db.data_dir(), redirect_uri())
            _oauth_states[state] = datetime.now().timestamp()
            self._redirect(url)
            return
        if method == "GET" and path == "/api/gmail/callback":
            self._oauth_callback(query)
            return

        preview = _match(path, r"/api/syntheses/(\d+)/preview")
        if method == "GET" and preview:
            model = db.document_model(int(preview.group(1)))
            html = render_email(model["client"]["name"], model["edition"], model["sections"])
            self._html(html)
            return

        if method == "POST" and path == "/api/clients":
            self._json(db.save_client(self._body()))
            return
        client_update = _match(path, r"/api/clients/(\d+)")
        if method == "PUT" and client_update:
            payload = self._body()
            payload["id"] = int(client_update.group(1))
            self._json(db.save_client(payload))
            return
        if method == "DELETE" and client_update:
            db.delete_client(int(client_update.group(1)))
            self._json({"ok": True})
            return
        recipients = _match(path, r"/api/clients/(\d+)/recipients")
        if method == "POST" and recipients:
            body = self._body()
            self._json(
                db.add_recipient(int(recipients.group(1)), body.get("email", ""), body.get("name", ""))
            )
            return
        recipient = _match(path, r"/api/recipients/(\d+)")
        if method == "DELETE" and recipient:
            db.delete_recipient(int(recipient.group(1)))
            self._json({"ok": True})
            return
        if method == "POST" and path == "/api/keywords":
            body = self._body()
            self._json(
                db.add_keyword(
                    int(body.get("client_id")),
                    body.get("phrase", ""),
                    body.get("section_name", ""),
                    body.get("weight", 1),
                )
            )
            return
        keyword = _match(path, r"/api/keywords/(\d+)")
        if method == "DELETE" and keyword:
            db.delete_keyword(int(keyword.group(1)))
            self._json({"ok": True})
            return
        if method == "POST" and path == "/api/notes":
            self._json(db.create_note(self._body()))
            return
        if method == "POST" and path == "/api/notes/import":
            self._json(db.import_notes(self._body().get("notes", [])))
            return
        if method == "POST" and path == "/api/notes/example":
            edition = self._body().get("fecha")
            self._json(db.load_example(edition or None))
            return
        note = _match(path, r"/api/notes/(\d+)")
        if method == "PUT" and note:
            self._json(db.update_note(int(note.group(1)), self._body()))
            return
        if method == "DELETE" and note:
            db.delete_note(int(note.group(1)))
            self._json({"ok": True})
            return
        if method == "POST" and path == "/api/desk/attach":
            body = self._body()
            self._json(
                present_desk(
                    db.attach_note(
                        int(body.get("client_id")),
                        body.get("date", ""),
                        int(body.get("note_id")),
                        body.get("section_name", ""),
                    )
                )
            )
            return
        if method == "POST" and path == "/api/desk/reclassify":
            body = self._body()
            client_id = body.get("client_id")
            self._json(db.reclassify(body.get("date", ""), int(client_id) if client_id else None))
            return
        layout = _match(path, r"/api/syntheses/(\d+)/layout")
        if method == "POST" and layout:
            result = db.save_layout(int(layout.group(1)), self._body())
            result["desk"] = present_desk(result["desk"])
            self._json(result)
            return
        review = _match(path, r"/api/syntheses/(\d+)/review")
        if method == "POST" and review:
            result = delivery.review(int(review.group(1)))
            result["desk"] = present_desk(db.desk(result["client_id"], result["edition_date"]))
            self._json(result)
            return
        reopen = _match(path, r"/api/syntheses/(\d+)/reopen")
        if method == "POST" and reopen:
            self._json(present_desk(db.reopen(int(reopen.group(1)))))
            return
        retry = _match(path, r"/api/syntheses/(\d+)/retry")
        if method == "POST" and retry:
            result = delivery.retry(int(retry.group(1)))
            result["desk"] = present_desk(db.desk(result["client_id"], result["edition_date"]))
            self._json(result)
            return
        if method == "POST" and path == "/api/gmail/credentials":
            gmail_client.save_client_secrets(db.data_dir(), self._body())
            self._json({"ok": True})
            return
        account = _match(path, r"/api/gmail/accounts/(\d+)")
        if method == "DELETE" and account:
            db.delete_gmail_account(int(account.group(1)))
            self._json({"ok": True})
            return
        raise ApiError("No encontré esa ruta.", 404)

    def _oauth_callback(self, query: dict[str, list[str]]) -> None:
        global _oauth_error
        error = _text(query, "error", required=False)
        state = _text(query, "state", required=False)
        created = _oauth_states.pop(state, None) if state else None
        if error or not created or datetime.now().timestamp() - created > 900:
            _oauth_error = "Google no autorizó la cuenta. Intenta conectarla otra vez."
            self._redirect("/?vista=config&gmail=error")
            return
        try:
            email, token_json = gmail_client.exchange_code(
                db.data_dir(),
                redirect_uri(),
                _text(query, "code"),
            )
            db.upsert_gmail_account(email, token_json)
        except ApiError as exc:
            _oauth_error = exc.message
            self._redirect("/?vista=config&gmail=error")
            return
        _oauth_error = ""
        self._redirect("/?vista=config&gmail=ok")

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 8_000_000:
            raise ApiError("El archivo es demasiado grande.", 413)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ApiError("El JSON no se pudo leer.") from exc
        if not isinstance(data, dict):
            raise ApiError("Se esperaba un objeto JSON.")
        return data

    def _json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _file(self, path: Path) -> None:
        if not path.is_file():
            raise ApiError("No encontré el archivo.", 404)
        data = path.read_bytes()
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }.get(path.suffix.lower(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        if args and len(args) >= 2 and str(args[1]).startswith(("4", "5")):
            super().log_message(fmt, *args)


def _bootstrap() -> dict:
    return {
        "clients": db.list_clients(),
        "accounts": db.list_gmail_accounts(),
        "libraries_ready": gmail_client.libraries_ready(),
        "credentials_loaded": gmail_client.credentials_path(db.data_dir()).is_file(),
        "oauth_error": _oauth_error,
        "lead_minutes": LEAD_MINUTES,
        "today": date.today().isoformat(),
        "redirect_uri": redirect_uri(),
    }


def _static_file(url_path: str) -> Path:
    relative = url_path.removeprefix("/static/").replace("\\", "/")
    if not relative or ".." in relative.split("/"):
        raise ApiError("No encontré el archivo.", 404)
    path = (STATIC_DIR / relative).resolve()
    try:
        path.relative_to(STATIC_DIR.resolve())
    except ValueError as exc:
        raise ApiError("No encontré el archivo.", 404) from exc
    return path


def _match(path: str, pattern: str):
    import re

    return re.fullmatch(pattern, path)


def _text(query: dict[str, list[str]], key: str, required: bool = True) -> str:
    values = query.get(key) or []
    value = values[0].strip() if values else ""
    if required and not value:
        raise ApiError(f"Falta {key}.")
    return value


def _int(query: dict[str, list[str]], key: str) -> int:
    try:
        return int(_text(query, key))
    except ValueError as exc:
        raise ApiError(f"{key} no es válido.") from exc


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main(argv: list[str] | None = None) -> int:
    global _port
    parser = ArgumentParser(description="Mesa de síntesis de medios")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    _port = args.port
    db.init_db()
    Scheduler().start()
    try:
        server = ThreadingHTTPServer((HOST, _port), SynthesisHandler)
    except OSError as exc:
        print(f"No se pudo abrir el puerto {_port}: {exc}")
        return 1
    url = f"http://{HOST}:{_port}"
    print(f"Mesa de síntesis lista en {url}")
    print(f"Datos en: {db.data_dir()}")
    print("El programador de Gmail trabaja mientras esta ventana sigue abierta.")
    print("Presiona Ctrl+C para detenerla.")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMesa detenida.")
    finally:
        server.server_close()
    return 0

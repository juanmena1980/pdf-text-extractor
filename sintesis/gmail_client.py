from __future__ import annotations

import json
from pathlib import Path

from .errors import ApiError

SCOPES = (
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
)


def libraries_ready() -> bool:
    try:
        import google.auth.transport.requests  # noqa: F401
        import google.oauth2.credentials  # noqa: F401
        import google_auth_oauthlib.flow  # noqa: F401
    except ImportError:
        return False
    return True


def require_libraries() -> None:
    if libraries_ready():
        return
    raise ApiError(
        "Faltan las librerías de Google. En esta carpeta ejecuta: "
        "python -m pip install -r requirements-sintesis.txt"
    )


def credentials_path(data_dir: Path) -> Path:
    return data_dir / "credentials.json"


def save_client_secrets(data_dir: Path, payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ApiError("El archivo de Google no tiene el formato esperado.")
    if payload.get("type") == "service_account" or "private_key" in payload:
        raise ApiError(
            "Ese archivo es una cuenta de servicio. "
            "Crea un cliente OAuth de tipo Aplicación de escritorio y sube ese JSON."
        )
    block = payload.get("installed") or payload.get("web")
    if not isinstance(block, dict) or not block.get("client_id") or not block.get("client_secret"):
        raise ApiError(
            "No reconocí el JSON. Descarga el cliente OAuth de tipo Aplicación de escritorio."
        )
    path = credentials_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def authorization_url(data_dir: Path, redirect_uri: str) -> tuple[str, str]:
    require_libraries()
    path = credentials_path(data_dir)
    if not path.is_file():
        raise ApiError("Primero sube el JSON del cliente OAuth de Google.")
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(str(path), scopes=SCOPES, redirect_uri=redirect_uri)
    url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    return url, state


def exchange_code(data_dir: Path, redirect_uri: str, code: str) -> tuple[str, str]:
    require_libraries()
    import os

    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow

    path = credentials_path(data_dir)
    flow = Flow.from_client_secrets_file(str(path), scopes=SCOPES, redirect_uri=redirect_uri)
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise ApiError(f"Google no entregó el acceso: {exc}") from exc
    creds = flow.credentials
    if not creds.refresh_token:
        raise ApiError(
            "Google no entregó un acceso permanente. Quita el permiso de la app en la cuenta "
            "y vuelve a conectar, aceptando el acceso."
        )
    email = _email_from_id_token(creds)
    stored = Credentials(
        token=creds.token,
        refresh_token=creds.refresh_token,
        token_uri=creds.token_uri,
        client_id=creds.client_id,
        client_secret=creds.client_secret,
        scopes=list(SCOPES),
    )
    # AuthorizedSession se usa al enviar; aquí solo confirmamos que el token responde.
    try:
        session = AuthorizedSession(stored)
        response = session.get("https://www.googleapis.com/oauth2/v2/userinfo", timeout=30)
        if response.status_code == 200:
            fetched = str(response.json().get("email") or "").strip()
            if fetched:
                email = fetched
    except Exception:
        pass
    if not email:
        raise ApiError("No pude leer el correo de la cuenta conectada.")
    return email, stored.to_json()


def send_html(
    token_json: str,
    *,
    sender: str,
    to: list[str],
    bcc: list[str],
    subject: str,
    plain: str,
    html: str,
) -> tuple[str, str]:
    require_libraries()
    import base64
    from email.message import EmailMessage

    from google.auth.transport.requests import AuthorizedSession, Request
    from google.oauth2.credentials import Credentials

    creds = Credentials.from_authorized_user_info(json.loads(token_json), list(SCOPES))
    if not creds.valid:
        if not creds.refresh_token:
            raise ApiError("La cuenta de Gmail ya no tiene acceso. Vuelve a conectarla.")
        try:
            creds.refresh(Request())
        except Exception as exc:
            raise ApiError(f"No se pudo renovar el acceso de Gmail: {exc}") from exc
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(to)
    if bcc:
        message["Bcc"] = ", ".join(bcc)
    message["Subject"] = subject
    message.set_content(plain)
    message.add_alternative(html, subtype="html")
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    session = AuthorizedSession(creds)
    response = session.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        json={"raw": raw},
        timeout=60,
    )
    if response.status_code == 401:
        raise ApiError("Gmail rechazó la cuenta. Vuelve a conectarla.")
    if response.status_code >= 400:
        detail = _gmail_error(response)
        raise ApiError(f"Gmail rechazó el envío ({response.status_code}). {detail}")
    payload = response.json()
    message_id = str(payload.get("id") or "")
    if not message_id:
        raise ApiError("Gmail no confirmó el envío.")
    return message_id, creds.to_json()


def _email_from_id_token(creds) -> str:
    token = getattr(creds, "id_token", None)
    if not isinstance(token, str) or token.count(".") < 2:
        return ""
    import base64

    try:
        payload = token.split(".")[1]
        padding = "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload + padding))
    except Exception:
        return ""
    return str(data.get("email") or "").strip()


def _gmail_error(response) -> str:
    try:
        payload = response.json()
    except Exception:
        return response.text[:240]
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])[:300]
    return str(payload)[:300]

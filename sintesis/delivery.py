from __future__ import annotations

import traceback
from datetime import datetime

from . import db, gmail_client
from .errors import ApiError
from .render import render_email, render_plain, render_subject
from .sendplan import describe_result, plan_send
from .validate import parse_date


def readiness(view: dict, libraries_ready: bool) -> dict:
    synthesis = view.get("synthesis") or {}
    status = synthesis.get("status")
    active = view["counts"]["active"]
    recipients = view["counts"]["recipients"]
    sender = view.get("sender")
    checks = [
        {
            "ok": active > 0,
            "label": f"{active} notas incluidas" if active else "No hay notas incluidas",
        },
        {
            "ok": recipients > 0,
            "label": f"{recipients} destinatarios" if recipients else "Falta al menos un destinatario",
        },
        {
            "ok": bool(sender),
            "label": f"Gmail listo: {sender['email']}" if sender else "Falta asignar la cuenta de Gmail",
        },
        {
            "ok": libraries_ready,
            "label": "Librerías de Google listas"
            if libraries_ready
            else "Faltan las librerías de Google en esta computadora",
        },
    ]
    if status == "enviando":
        checks.append({"ok": False, "label": "El envío ya está en curso"})
    if status == "enviada":
        checks.append({"ok": False, "label": "Ya se envió. Ábrela si vas a mandar una corrección"})
    return {"ok": all(item["ok"] for item in checks), "checks": checks}


def review(synthesis_id: int) -> dict:
    bundle = db.send_bundle(synthesis_id)
    status = bundle["synthesis"]["status"]
    if status == "enviada":
        raise ApiError("Ya se envió. Ábrela de nuevo si necesitas mandar una corrección.")
    if status == "enviando":
        raise ApiError("El envío está en curso.")
    _ensure_sendable(bundle)
    edition = parse_date(bundle["synthesis"]["edition_date"])
    plan = plan_send(datetime.now(), edition, bundle["client"]["send_time"])
    sender = bundle["account"]["email"]
    now = datetime.now()
    if plan.immediate:
        if not db.claim_for_send(synthesis_id, plan.send_at, now):
            raise ApiError("Ya se está enviando.")
        message_id = _deliver(synthesis_id)
        return {
            "mode": "enviada",
            "message": describe_result(plan, sender),
            "gmail_message_id": message_id,
            "client_id": bundle["client"]["id"],
            "edition_date": bundle["synthesis"]["edition_date"],
        }
    db.mark_scheduled(synthesis_id, plan.send_at, now)
    print(
        f"Síntesis {synthesis_id} programada para {plan.send_at.strftime('%H:%M')} "
        f"desde {sender}."
    )
    return {
        "mode": "programada",
        "message": describe_result(plan, sender),
        "client_id": bundle["client"]["id"],
        "edition_date": bundle["synthesis"]["edition_date"],
    }


def retry(synthesis_id: int) -> dict:
    bundle = db.send_bundle(synthesis_id)
    if bundle["synthesis"]["status"] != "error":
        raise ApiError("Solo se reintenta un envío con error.")
    _ensure_sendable(bundle)
    now = datetime.now().replace(microsecond=0)
    if not db.claim_for_send(synthesis_id, now, now):
        raise ApiError("Ya se está enviando.")
    message_id = _deliver(synthesis_id)
    sender = bundle["account"]["email"]
    return {
        "mode": "enviada",
        "message": f"El correo salió ahora desde {sender}.",
        "gmail_message_id": message_id,
        "client_id": bundle["client"]["id"],
        "edition_date": bundle["synthesis"]["edition_date"],
    }


def dispatch_due() -> None:
    now_iso = datetime.now().replace(microsecond=0).isoformat(timespec="seconds")
    for synthesis_id in db.claim_due(now_iso):
        try:
            _deliver(synthesis_id)
        except Exception:
            traceback.print_exc()


def _ensure_sendable(bundle: dict) -> None:
    gmail_client.require_libraries()
    missing = []
    if not bundle["sections"]:
        missing.append("no hay notas incluidas")
    if not bundle["recipients"]:
        missing.append("faltan destinatarios")
    if not bundle["account"]:
        missing.append("falta la cuenta de Gmail")
    if missing:
        raise ApiError("No se puede enviar: " + "; ".join(missing) + ".")


def _deliver(synthesis_id: int) -> str:
    bundle = db.send_bundle(synthesis_id)
    if bundle["synthesis"]["status"] != "enviando":
        raise ApiError("La síntesis no está lista para enviarse.")
    try:
        _ensure_sendable(bundle)
        edition = parse_date(bundle["synthesis"]["edition_date"])
        client = bundle["client"]
        subject = render_subject(client["subject_template"], client["name"], edition)
        sections = bundle["sections"]
        recipients = [item["email"] for item in bundle["recipients"]]
        sender = bundle["account"]["email"]
        if client["use_bcc"]:
            to = [sender]
            bcc = recipients
        else:
            to = recipients
            bcc = []
        message_id, token_json = gmail_client.send_html(
            bundle["account"]["token_json"],
            sender=sender,
            to=to,
            bcc=bcc,
            subject=subject,
            plain=render_plain(client["name"], edition, sections),
            html=render_email(client["name"], edition, sections),
        )
        db.update_gmail_token(bundle["account"]["id"], token_json)
        db.mark_sent(synthesis_id, message_id)
    except Exception as exc:
        message = exc.message if isinstance(exc, ApiError) else str(exc)
        db.mark_error(synthesis_id, message)
        if isinstance(exc, ApiError):
            raise
        raise ApiError(f"No se pudo enviar por Gmail: {message}") from exc
    print(f"Correo enviado · síntesis {synthesis_id} · {message_id}")
    return message_id

from __future__ import annotations

from datetime import date
from html import escape

from .validate import MEDIUM_LABELS, safe_http_url

_MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def fecha_larga(value: date) -> str:
    return f"{_DIAS[value.weekday()]} {value.day} de {_MESES[value.month - 1]} de {value.year}"


def render_subject(template: str, client_name: str, edition: date) -> str:
    base = " ".join((template or "").split()) or "Síntesis {cliente} — {fecha}"
    return (
        base.replace("{cliente}", client_name)
        .replace("{fecha}", edition.strftime("%d/%m/%Y"))
        .replace("{fecha_larga}", fecha_larga(edition))
    )


def _paragraphs(text: str) -> str:
    chunks = [chunk.strip() for chunk in text.replace("\r\n", "\n").split("\n")]
    parts = [f'<p style="margin:8px 0 0;">{escape(chunk)}</p>' for chunk in chunks if chunk]
    return "".join(parts)


def _meta(item: dict) -> str:
    medium = item.get("medium_label") or MEDIUM_LABELS.get(item.get("medium", ""), "Nota")
    parts = [medium, item.get("outlet") or ""]
    if item.get("program"):
        parts.append(item["program"])
    if item.get("published_time"):
        parts.append(item["published_time"])
    if item.get("author"):
        parts.append(item["author"])
    return " · ".join(part for part in parts if part)


def render_plain(client_name: str, edition: date, sections: list[dict]) -> str:
    lines = ["SÍNTESIS DE MEDIOS", client_name, fecha_larga(edition), ""]
    for section in sections:
        lines.append(section["name"].upper())
        lines.append("")
        for index, item in enumerate(section["items"], start=1):
            lines.append(f"{index}. {_meta(item)}")
            lines.append(item.get("title") or "")
            if item.get("body"):
                lines.append(item["body"].strip())
            url = safe_http_url(item.get("url") or "")
            if url:
                lines.append(url)
            lines.append("")
    lines.append("Enviado desde la mesa de síntesis.")
    return "\n".join(lines).strip() + "\n"


def render_email(client_name: str, edition: date, sections: list[dict]) -> str:
    blocks: list[str] = []
    for section in sections:
        notes: list[str] = []
        for index, item in enumerate(section["items"], start=1):
            url = safe_http_url(item.get("url") or "")
            link = ""
            if url:
                href = escape(url, quote=True)
                link = (
                    f'<p style="margin:8px 0 0;"><a href="{href}" '
                    f'style="color:#1f4d45;">Abrir nota</a></p>'
                )
            notes.append(
                "<tr>"
                f'<td style="width:36px;vertical-align:top;padding:14px 0;'
                f'font:700 18px Georgia,serif;color:#9a4034;">{index}</td>'
                '<td style="padding:14px 0;border-bottom:1px solid #eadfce;">'
                f'<div style="font:600 12px Segoe UI,sans-serif;letter-spacing:.04em;'
                f'text-transform:uppercase;color:#6d6458;">{escape(_meta(item))}</div>'
                f'<div style="margin-top:4px;font:24px/1.25 Georgia,serif;color:#1c1915;">'
                f'{escape(item.get("title") or "")}</div>'
                f'{_paragraphs(item.get("body") or "")}'
                f"{link}</td></tr>"
            )
        blocks.append(
            '<h2 style="margin:28px 0 0;font:700 13px Segoe UI,sans-serif;'
            'letter-spacing:.12em;text-transform:uppercase;color:#1f4d45;">'
            f'{escape(section["name"])}</h2>'
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
            f'style="border-collapse:collapse;">{"".join(notes)}</table>'
        )

    body = "".join(blocks) or (
        '<p style="font:16px Segoe UI,sans-serif;">Esta síntesis no tiene notas.</p>'
    )
    return f"""<!doctype html>
<html lang="es">
  <body style="margin:0;background:#f3efe6;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3efe6;">
      <tr>
        <td align="center" style="padding:24px 12px;">
          <table role="presentation" width="640" cellspacing="0" cellpadding="0" style="width:640px;max-width:100%;background:#fffdf8;border:1px solid #e4d8c6;">
            <tr>
              <td style="padding:28px 32px;background:#17241f;color:#f6f1e7;">
                <div style="font:600 12px Segoe UI,sans-serif;letter-spacing:.16em;text-transform:uppercase;color:#d7c4a4;">Síntesis de medios</div>
                <div style="margin-top:8px;font:36px/1.15 Georgia,serif;">{escape(client_name)}</div>
                <div style="margin-top:8px;font:16px Segoe UI,sans-serif;color:#efe6d6;">{escape(fecha_larga(edition))}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 32px 32px;">{body}</td>
            </tr>
            <tr>
              <td style="padding:16px 32px 24px;border-top:1px solid #eadfce;font:13px Segoe UI,sans-serif;color:#6d6458;">
                Enviado desde la mesa de síntesis. El personal no tiene que armar un documento ni entrar a Gmail.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

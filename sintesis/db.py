from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from .errors import ApiError
from .sample import DEMO_CLIENT, DEMO_KEYWORDS, DEMO_NOTES, demo_send_time
from .sendplan import InvalidSendTime, describe_plan, normalize_hhmm, plan_send
from .validate import (
    MEDIUM_LABELS,
    clean_text,
    contains_phrase,
    fold,
    normalize_phrase,
    parse_date,
    parse_medium,
    valid_email,
)

_override: Path | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS gmail_accounts (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    token_json TEXT NOT NULL,
    connected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    send_time TEXT NOT NULL DEFAULT '08:00',
    subject_template TEXT NOT NULL DEFAULT 'Síntesis {cliente} — {fecha}',
    use_bcc INTEGER NOT NULL DEFAULT 1,
    gmail_account_id INTEGER REFERENCES gmail_accounts(id) ON DELETE SET NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipients (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    UNIQUE(client_id, email)
);

CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    section_name TEXT NOT NULL,
    phrase TEXT NOT NULL,
    weight INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    published_on TEXT NOT NULL,
    published_time TEXT NOT NULL DEFAULT '',
    medium TEXT NOT NULL,
    outlet TEXT NOT NULL,
    program TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    author TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS syntheses (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    edition_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'borrador',
    reviewed_at TEXT,
    send_at TEXT,
    sent_at TEXT,
    gmail_message_id TEXT,
    error TEXT,
    UNIQUE(client_id, edition_date)
);

CREATE TABLE IF NOT EXISTS synthesis_sections (
    synthesis_id INTEGER NOT NULL REFERENCES syntheses(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (synthesis_id, name)
);

CREATE TABLE IF NOT EXISTS synthesis_items (
    id INTEGER PRIMARY KEY,
    synthesis_id INTEGER NOT NULL REFERENCES syntheses(id) ON DELETE CASCADE,
    note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    section_name TEXT NOT NULL,
    position INTEGER NOT NULL,
    discarded INTEGER NOT NULL DEFAULT 0,
    origin TEXT NOT NULL DEFAULT 'auto',
    match_phrase TEXT NOT NULL DEFAULT '',
    UNIQUE(synthesis_id, note_id)
);

CREATE INDEX IF NOT EXISTS idx_notes_date ON notes(published_on);
CREATE INDEX IF NOT EXISTS idx_items_syn ON synthesis_items(synthesis_id, discarded, position);
CREATE INDEX IF NOT EXISTS idx_syn_status ON syntheses(status, send_at);
"""

STATUS_LABELS = {
    "borrador": "Borrador",
    "programada": "Programada",
    "enviando": "Enviando",
    "enviada": "Enviada",
    "error": "Error de envío",
}

LOCKED = {"enviada", "enviando"}


def set_data_dir(path: Path | None) -> None:
    global _override
    _override = None if path is None else Path(path)


def data_dir() -> Path:
    if _override is not None:
        return _override
    env = os.environ.get("SINTESIS_DATA")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "sintesis_data"


def db_path() -> Path:
    return data_dir() / "sintesis.db"


def init_db() -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    connection = _connect()
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(SCHEMA)
    finally:
        connection.close()


@contextmanager
def _immediate():
    connection = _connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(db_path(), timeout=15, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def _now() -> str:
    return datetime.now().replace(microsecond=0).isoformat(timespec="seconds")


def _rows(connection: sqlite3.Connection, query: str, params: tuple = ()) -> list[dict]:
    return [dict(row) for row in connection.execute(query, params).fetchall()]


def _one(connection: sqlite3.Connection, query: str, params: tuple = ()) -> dict | None:
    row = connection.execute(query, params).fetchone()
    return dict(row) if row else None


def _status_label(synthesis: dict | None) -> str:
    if not synthesis:
        return "Sin armar"
    if synthesis["status"] == "borrador" and synthesis.get("sent_at"):
        return "Corrección abierta"
    return STATUS_LABELS.get(synthesis["status"], synthesis["status"])


def list_gmail_accounts() -> list[dict]:
    with _immediate() as connection:
        return _rows(
            connection,
            "SELECT id, email, connected_at FROM gmail_accounts ORDER BY email",
        )


def upsert_gmail_account(email: str, token_json: str) -> dict:
    normalized = clean_text(email, 254, allow_empty=False).casefold()
    if not valid_email(normalized):
        raise ApiError("La cuenta de Gmail no tiene un correo válido.")
    with _immediate() as connection:
        current = _one(connection, "SELECT id FROM gmail_accounts WHERE email = ?", (normalized,))
        if current:
            connection.execute(
                "UPDATE gmail_accounts SET token_json = ?, connected_at = ? WHERE id = ?",
                (token_json, _now(), current["id"]),
            )
            account_id = current["id"]
        else:
            account_id = connection.execute(
                "INSERT INTO gmail_accounts (email, token_json, connected_at) VALUES (?, ?, ?)",
                (normalized, token_json, _now()),
            ).lastrowid
        row = _one(
            connection,
            "SELECT id, email, connected_at FROM gmail_accounts WHERE id = ?",
            (account_id,),
        )
    return row


def update_gmail_token(account_id: int, token_json: str) -> None:
    with _immediate() as connection:
        connection.execute(
            "UPDATE gmail_accounts SET token_json = ? WHERE id = ?",
            (token_json, account_id),
        )


def delete_gmail_account(account_id: int) -> None:
    with _immediate() as connection:
        connection.execute("DELETE FROM gmail_accounts WHERE id = ?", (account_id,))


def gmail_token(account_id: int) -> dict:
    with _immediate() as connection:
        row = _one(connection, "SELECT * FROM gmail_accounts WHERE id = ?", (account_id,))
    if not row:
        raise ApiError("No encontré la cuenta de Gmail.", 404)
    return row


def list_clients() -> list[dict]:
    with _immediate() as connection:
        clients = _rows(connection, "SELECT * FROM clients WHERE active = 1 ORDER BY name")
        return [_client_public(connection, client) for client in clients]


def save_client(payload: dict) -> dict:
    name = clean_text(payload.get("name"), 120, allow_empty=False)
    try:
        send_time = normalize_hhmm(str(payload.get("send_time") or "08:00"))
    except InvalidSendTime as exc:
        raise ApiError(str(exc)) from exc
    subject = clean_text(payload.get("subject_template"), 200) or "Síntesis {cliente} — {fecha}"
    use_bcc = 1 if payload.get("use_bcc", True) else 0
    gmail_account_id = payload.get("gmail_account_id")
    gmail_account_id = int(gmail_account_id) if gmail_account_id else None
    client_id = payload.get("id")
    with _immediate() as connection:
        if gmail_account_id and not _one(
            connection, "SELECT id FROM gmail_accounts WHERE id = ?", (gmail_account_id,)
        ):
            raise ApiError("Esa cuenta de Gmail no está conectada.")
        try:
            if client_id:
                current = _require_client(connection, int(client_id))
                connection.execute(
                    """
                    UPDATE clients
                    SET name = ?, send_time = ?, subject_template = ?, use_bcc = ?, gmail_account_id = ?
                    WHERE id = ?
                    """,
                    (name, send_time, subject, use_bcc, gmail_account_id, current["id"]),
                )
                saved_id = current["id"]
            else:
                saved_id = connection.execute(
                    """
                    INSERT INTO clients
                        (name, send_time, subject_template, use_bcc, gmail_account_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (name, send_time, subject, use_bcc, gmail_account_id, _now()),
                ).lastrowid
        except sqlite3.IntegrityError as exc:
            raise ApiError("Ya hay un cliente con ese nombre.") from exc
        client = _require_client(connection, saved_id)
        return _client_public(connection, client)


def delete_client(client_id: int) -> None:
    with _immediate() as connection:
        _require_client(connection, client_id)
        sent = _one(
            connection,
            "SELECT id FROM syntheses WHERE client_id = ? AND status = 'enviada'",
            (client_id,),
        )
        if sent:
            raise ApiError("Este cliente ya tiene síntesis enviadas. Se conserva para el historial.")
        connection.execute("DELETE FROM clients WHERE id = ?", (client_id,))


def add_recipient(client_id: int, email: str, name: str = "") -> dict:
    address = clean_text(email, 254, allow_empty=False).casefold()
    if not valid_email(address):
        raise ApiError("El destinatario no tiene un correo válido.")
    label = clean_text(name, 120)
    with _immediate() as connection:
        _require_client(connection, client_id)
        try:
            recipient_id = connection.execute(
                "INSERT INTO recipients (client_id, email, name) VALUES (?, ?, ?)",
                (client_id, address, label),
            ).lastrowid
        except sqlite3.IntegrityError as exc:
            raise ApiError("Ese destinatario ya está en el cliente.") from exc
        return _one(connection, "SELECT * FROM recipients WHERE id = ?", (recipient_id,))


def delete_recipient(recipient_id: int) -> None:
    with _immediate() as connection:
        connection.execute("DELETE FROM recipients WHERE id = ?", (recipient_id,))


def add_keyword(client_id: int, phrase: str, section_name: str, weight: int = 1) -> dict:
    clean_phrase = normalize_phrase(phrase)
    section = clean_text(section_name, 80, allow_empty=False)
    try:
        score = int(weight)
    except (TypeError, ValueError) as exc:
        raise ApiError("El peso de la palabra clave debe ser un número.") from exc
    score = min(10, max(1, score))
    with _immediate() as connection:
        _require_client(connection, client_id)
        current = _rows(connection, "SELECT phrase FROM keywords WHERE client_id = ?", (client_id,))
        if any(fold(row["phrase"]) == fold(clean_phrase) for row in current):
            raise ApiError("Esa palabra clave ya existe en el cliente.")
        keyword_id = connection.execute(
            """
            INSERT INTO keywords (client_id, section_name, phrase, weight)
            VALUES (?, ?, ?, ?)
            """,
            (client_id, section, clean_phrase, score),
        ).lastrowid
        return _one(connection, "SELECT * FROM keywords WHERE id = ?", (keyword_id,))


def delete_keyword(keyword_id: int) -> None:
    with _immediate() as connection:
        connection.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))


def list_notes(edition: str) -> list[dict]:
    day = parse_date(edition).isoformat()
    with _immediate() as connection:
        notes = _rows(
            connection,
            "SELECT * FROM notes WHERE published_on = ? ORDER BY published_time, id",
            (day,),
        )
        return [_note_public(connection, note) for note in notes]


def create_note(payload: dict) -> dict:
    with _immediate() as connection:
        note_id = _insert_note(connection, payload)
        note = _one(connection, "SELECT * FROM notes WHERE id = ?", (note_id,))
        _reclassify_note(connection, note)
        return _note_public(connection, note)


def update_note(note_id: int, payload: dict) -> dict:
    with _immediate() as connection:
        current = _one(connection, "SELECT * FROM notes WHERE id = ?", (note_id,))
        if not current:
            raise ApiError("No encontré la nota.", 404)
        _guard_note_edit(connection, note_id)
        fields = _note_fields(payload, current["published_on"])
        connection.execute(
            """
            UPDATE notes
            SET published_on = ?, published_time = ?, medium = ?, outlet = ?, program = ?,
                title = ?, body = ?, url = ?, author = ?
            WHERE id = ?
            """,
            (*fields, note_id),
        )
        note = _one(connection, "SELECT * FROM notes WHERE id = ?", (note_id,))
        _reclassify_note(connection, note)
        return _note_public(connection, note)


def delete_note(note_id: int) -> None:
    with _immediate() as connection:
        if not _one(connection, "SELECT id FROM notes WHERE id = ?", (note_id,)):
            raise ApiError("No encontré la nota.", 404)
        _guard_note_edit(connection, note_id)
        connection.execute("DELETE FROM notes WHERE id = ?", (note_id,))


def import_notes(items: list) -> dict:
    if not isinstance(items, list):
        raise ApiError("El import debe ser una lista de notas.")
    if len(items) > 500:
        raise ApiError("Importa hasta 500 notas por vez.")
    created = 0
    with _immediate() as connection:
        for item in items:
            if not isinstance(item, dict):
                raise ApiError("Cada nota importada debe ser un objeto.")
            note_id = _insert_note(connection, item)
            note = _one(connection, "SELECT * FROM notes WHERE id = ?", (note_id,))
            _reclassify_note(connection, note)
            created += 1
    return {"created": created}


def load_example(edition: str | None = None) -> dict:
    day = parse_date(edition).isoformat() if edition else date.today().isoformat()
    with _immediate() as connection:
        client = _one(connection, "SELECT * FROM clients WHERE name = ?", (DEMO_CLIENT,))
        if not client:
            client_id = connection.execute(
                """
                INSERT INTO clients (name, send_time, subject_template, use_bcc, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (
                    DEMO_CLIENT,
                    demo_send_time(),
                    "Síntesis {cliente} — {fecha}",
                    _now(),
                ),
            ).lastrowid
            for phrase, section, weight in DEMO_KEYWORDS:
                connection.execute(
                    """
                    INSERT INTO keywords (client_id, section_name, phrase, weight)
                    VALUES (?, ?, ?, ?)
                    """,
                    (client_id, section, phrase, weight),
                )
            connection.execute(
                "INSERT INTO recipients (client_id, email, name) VALUES (?, ?, ?)",
                (client_id, "redaccion@example.com", "Redacción"),
            )
        else:
            client_id = client["id"]
        created = 0
        for item in DEMO_NOTES:
            title = item["titulo"]
            exists = _one(
                connection,
                """
                SELECT id FROM notes
                WHERE published_on = ? AND outlet = ? AND title = ?
                """,
                (day, item["fuente"], title),
            )
            if exists:
                continue
            payload = {
                "fecha": day,
                "medio": item["medio"],
                "fuente": item["fuente"],
                "programa": item.get("programa", ""),
                "hora": item.get("hora", ""),
                "titulo": title,
                "texto": item["texto"],
                "url": item.get("url", ""),
                "autor": item.get("autor", ""),
            }
            note_id = _insert_note(connection, payload)
            note = _one(connection, "SELECT * FROM notes WHERE id = ?", (note_id,))
            _reclassify_note(connection, note)
            created += 1
    return {"client_id": client_id, "edition_date": day, "created": created}


def reclassify(edition: str, client_id: int | None = None) -> dict:
    day = parse_date(edition).isoformat()
    with _immediate() as connection:
        notes = _rows(connection, "SELECT * FROM notes WHERE published_on = ?", (day,))
        for note in notes:
            _reclassify_note(connection, note, only_client_id=client_id)
    return {"updated": len(notes)}


def desk(client_id: int, edition: str) -> dict:
    day = parse_date(edition)
    with _immediate() as connection:
        client = _require_client(connection, client_id)
        return _desk(connection, client, day)


def save_layout(synthesis_id: int, payload: dict) -> dict:
    sections = payload.get("sections")
    discarded_ids = payload.get("discarded_ids") or []
    if not isinstance(sections, list) or not isinstance(discarded_ids, list):
        raise ApiError("El orden de la síntesis no tiene el formato esperado.")
    with _immediate() as connection:
        synthesis = _require_synthesis(connection, synthesis_id)
        if synthesis["status"] in LOCKED:
            raise ApiError("La síntesis ya se envió o está saliendo. Ábrela de nuevo para corregirla.")
        existing = {
            row["id"]: row
            for row in _rows(
                connection,
                "SELECT * FROM synthesis_items WHERE synthesis_id = ?",
                (synthesis_id,),
            )
        }
        incoming: list[int] = []
        clean_sections: list[tuple[str, list[int]]] = []
        seen_names: set[str] = set()
        for section in sections:
            if not isinstance(section, dict):
                raise ApiError("Hay un grupo mal formado.")
            name = clean_text(section.get("name"), 80, allow_empty=False)
            folded = fold(name)
            if folded in seen_names:
                raise ApiError(f"Hay dos grupos llamados {name}.")
            seen_names.add(folded)
            item_ids = section.get("item_ids") or []
            if not isinstance(item_ids, list):
                raise ApiError("Las notas del grupo no tienen el formato esperado.")
            parsed_ids = [int(item_id) for item_id in item_ids]
            clean_sections.append((name, parsed_ids))
            incoming.extend(parsed_ids)
        discarded = [int(item_id) for item_id in discarded_ids]
        incoming.extend(discarded)
        if set(incoming) != set(existing) or len(incoming) != len(existing):
            raise ApiError("La mesa cambió. Vuelve a cargarla.", 409)
        connection.execute(
            "DELETE FROM synthesis_sections WHERE synthesis_id = ?",
            (synthesis_id,),
        )
        for position, (name, _item_ids) in enumerate(clean_sections):
            connection.execute(
                "INSERT INTO synthesis_sections (synthesis_id, name, position) VALUES (?, ?, ?)",
                (synthesis_id, name, position),
            )
        for name, item_ids in clean_sections:
            for position, item_id in enumerate(item_ids):
                _update_item(connection, existing[item_id], name, position, discarded=0)
        for position, item_id in enumerate(discarded):
            previous = existing[item_id]
            _update_item(
                connection,
                previous,
                previous["section_name"],
                position,
                discarded=1,
            )
        active = connection.execute(
            "SELECT COUNT(*) AS n FROM synthesis_items WHERE synthesis_id = ? AND discarded = 0",
            (synthesis_id,),
        ).fetchone()["n"]
        cancelled = False
        if active == 0 and synthesis["status"] == "programada":
            connection.execute(
                """
                UPDATE syntheses
                SET status = 'borrador', send_at = NULL, error = NULL
                WHERE id = ?
                """,
                (synthesis_id,),
            )
            cancelled = True
        client = _require_client(connection, synthesis["client_id"])
        view = _desk(connection, client, parse_date(synthesis["edition_date"]))
    return {
        "desk": view,
        "schedule_cancelled": cancelled,
        "message": "Se canceló el envío porque la síntesis quedó vacía." if cancelled else "",
    }


def attach_note(client_id: int, edition: str, note_id: int, section_name: str) -> dict:
    day = parse_date(edition)
    section = clean_text(section_name, 80) or "General"
    with _immediate() as connection:
        client = _require_client(connection, client_id)
        note = _one(connection, "SELECT * FROM notes WHERE id = ?", (note_id,))
        if not note:
            raise ApiError("No encontré la nota.", 404)
        synthesis = _ensure_synthesis(connection, client_id, day.isoformat(), strict=True)
        current = _one(
            connection,
            "SELECT * FROM synthesis_items WHERE synthesis_id = ? AND note_id = ?",
            (synthesis["id"], note_id),
        )
        _ensure_section(connection, synthesis["id"], section)
        if current and not current["discarded"]:
            raise ApiError("Esa nota ya está en la síntesis.")
        if current and current["discarded"]:
            position = _next_item_position(connection, synthesis["id"], section)
            connection.execute(
                """
                UPDATE synthesis_items
                SET section_name = ?, position = ?, discarded = 0, origin = 'manual'
                WHERE id = ?
                """,
                (section, position, current["id"]),
            )
        else:
            position = _next_item_position(connection, synthesis["id"], section)
            connection.execute(
                """
                INSERT INTO synthesis_items
                    (synthesis_id, note_id, section_name, position, discarded, origin, match_phrase)
                VALUES (?, ?, ?, ?, 0, 'manual', '')
                """,
                (synthesis["id"], note_id, section, position),
            )
        return _desk(connection, client, day)


def document_model(synthesis_id: int) -> dict:
    with _immediate() as connection:
        synthesis = _require_synthesis(connection, synthesis_id)
        client = _require_client(connection, synthesis["client_id"])
        edition = parse_date(synthesis["edition_date"])
        from .render import render_subject

        return {
            "synthesis": synthesis,
            "client": client,
            "edition": edition,
            "subject": render_subject(client["subject_template"], client["name"], edition),
            "sections": _active_sections(connection, synthesis_id),
            "recipients": _rows(
                connection,
                "SELECT * FROM recipients WHERE client_id = ? ORDER BY email",
                (client["id"],),
            ),
        }


def mark_scheduled(synthesis_id: int, send_at: datetime, reviewed_at: datetime) -> None:
    with _immediate() as connection:
        cursor = connection.execute(
            """
            UPDATE syntheses
            SET status = 'programada', send_at = ?, reviewed_at = ?, error = NULL
            WHERE id = ? AND status IN ('borrador', 'programada', 'error')
            """,
            (
                send_at.replace(microsecond=0).isoformat(timespec="seconds"),
                reviewed_at.replace(microsecond=0).isoformat(timespec="seconds"),
                synthesis_id,
            ),
        )
        if cursor.rowcount != 1:
            raise ApiError("No se pudo programar la síntesis.")


def claim_for_send(synthesis_id: int, send_at: datetime, reviewed_at: datetime) -> bool:
    with _immediate() as connection:
        cursor = connection.execute(
            """
            UPDATE syntheses
            SET status = 'enviando', send_at = ?, reviewed_at = ?, error = NULL
            WHERE id = ? AND status IN ('borrador', 'programada', 'error')
            """,
            (
                send_at.replace(microsecond=0).isoformat(timespec="seconds"),
                reviewed_at.replace(microsecond=0).isoformat(timespec="seconds"),
                synthesis_id,
            ),
        )
        return cursor.rowcount == 1


def claim_due(now_iso: str) -> list[int]:
    with _immediate() as connection:
        rows = _rows(
            connection,
            """
            SELECT id FROM syntheses
            WHERE status = 'programada' AND send_at IS NOT NULL AND send_at <= ?
            """,
            (now_iso,),
        )
        claimed: list[int] = []
        for row in rows:
            cursor = connection.execute(
                """
                UPDATE syntheses
                SET status = 'enviando', error = NULL
                WHERE id = ? AND status = 'programada'
                """,
                (row["id"],),
            )
            if cursor.rowcount:
                claimed.append(row["id"])
        return claimed


def mark_sent(synthesis_id: int, message_id: str) -> None:
    with _immediate() as connection:
        connection.execute(
            """
            UPDATE syntheses
            SET status = 'enviada', sent_at = ?, gmail_message_id = ?, error = NULL
            WHERE id = ?
            """,
            (_now(), message_id, synthesis_id),
        )


def mark_error(synthesis_id: int, message: str) -> None:
    with _immediate() as connection:
        connection.execute(
            "UPDATE syntheses SET status = 'error', error = ? WHERE id = ?",
            (message[:500], synthesis_id),
        )


def reopen(synthesis_id: int) -> dict:
    with _immediate() as connection:
        synthesis = _require_synthesis(connection, synthesis_id)
        if synthesis["status"] != "enviada":
            raise ApiError("Solo se puede reabrir una síntesis ya enviada.")
        connection.execute(
            "UPDATE syntheses SET status = 'borrador', error = NULL WHERE id = ?",
            (synthesis_id,),
        )
        client = _require_client(connection, synthesis["client_id"])
        return _desk(connection, client, parse_date(synthesis["edition_date"]))


def list_sends() -> list[dict]:
    with _immediate() as connection:
        rows = _rows(
            connection,
            """
            SELECT s.*, c.name AS client_name, c.send_time
            FROM syntheses s
            JOIN clients c ON c.id = s.client_id
            WHERE s.status != 'borrador' OR s.sent_at IS NOT NULL
            ORDER BY COALESCE(s.sent_at, s.send_at, s.reviewed_at) DESC
            LIMIT 80
            """,
        )
    for row in rows:
        row["status_label"] = _status_label(row)
    return rows


def send_bundle(synthesis_id: int) -> dict:
    with _immediate() as connection:
        synthesis = _require_synthesis(connection, synthesis_id)
        client = _require_client(connection, synthesis["client_id"])
        recipients = _rows(
            connection,
            "SELECT * FROM recipients WHERE client_id = ? ORDER BY email",
            (client["id"],),
        )
        account = None
        if client["gmail_account_id"]:
            account = _one(
                connection,
                "SELECT * FROM gmail_accounts WHERE id = ?",
                (client["gmail_account_id"],),
            )
        sections = _active_sections(connection, synthesis_id)
    return {
        "synthesis": synthesis,
        "client": client,
        "recipients": recipients,
        "account": account,
        "sections": sections,
    }


def _desk(connection: sqlite3.Connection, client: dict, day: date) -> dict:
    synthesis = _one(
        connection,
        "SELECT * FROM syntheses WHERE client_id = ? AND edition_date = ?",
        (client["id"], day.isoformat()),
    )
    sections: list[dict] = []
    discarded: list[dict] = []
    assigned: set[int] = set()
    if synthesis:
        section_rows = _rows(
            connection,
            "SELECT name FROM synthesis_sections WHERE synthesis_id = ? ORDER BY position, name",
            (synthesis["id"],),
        )
        items = _rows(
            connection,
            """
            SELECT i.*, n.published_time, n.medium, n.outlet, n.program, n.title, n.body,
                   n.url, n.author, n.published_on
            FROM synthesis_items i
            JOIN notes n ON n.id = i.note_id
            WHERE i.synthesis_id = ?
            ORDER BY i.position, i.id
            """,
            (synthesis["id"],),
        )
        grouped: dict[str, list[dict]] = {row["name"]: [] for row in section_rows}
        for item in items:
            assigned.add(item["note_id"])
            public = _item_public(item)
            if item["discarded"]:
                discarded.append(public)
            else:
                grouped.setdefault(item["section_name"], []).append(public)
        known = {row["name"] for row in section_rows}
        for name in grouped:
            if name not in known and grouped[name]:
                section_rows.append({"name": name})
        sections = [{"name": row["name"], "items": grouped.get(row["name"], [])} for row in section_rows]
    notes = _rows(
        connection,
        "SELECT * FROM notes WHERE published_on = ? ORDER BY published_time, id",
        (day.isoformat(),),
    )
    unassigned = [_note_brief(note) for note in notes if note["id"] not in assigned]
    plan = plan_send(datetime.now(), day, client["send_time"])
    active = sum(len(section["items"]) for section in sections)
    sender = None
    if client["gmail_account_id"]:
        sender = _one(
            connection,
            "SELECT id, email FROM gmail_accounts WHERE id = ?",
            (client["gmail_account_id"],),
        )
    recipients = _rows(
        connection,
        "SELECT id, email, name FROM recipients WHERE client_id = ? ORDER BY email",
        (client["id"],),
    )
    return {
        "client": _client_public(connection, client),
        "edition_date": day.isoformat(),
        "synthesis": _synthesis_public(synthesis),
        "sections": sections,
        "discarded": discarded,
        "unassigned": unassigned,
        "plan": plan.as_dict(),
        "plan_text": describe_plan(plan),
        "counts": {
            "active": active,
            "discarded": len(discarded),
            "recipients": len(recipients),
        },
        "sender": sender,
        "recipients": recipients,
    }


def _active_sections(connection: sqlite3.Connection, synthesis_id: int) -> list[dict]:
    rows = _rows(
        connection,
        """
        SELECT i.position, i.section_name, n.medium, n.outlet, n.program, n.title, n.body,
               n.url, n.author, n.published_time, s.position AS section_position
        FROM synthesis_items i
        JOIN notes n ON n.id = i.note_id
        LEFT JOIN synthesis_sections s
          ON s.synthesis_id = i.synthesis_id AND s.name = i.section_name
        WHERE i.synthesis_id = ? AND i.discarded = 0
        ORDER BY COALESCE(s.position, 999), i.position, i.id
        """,
        (synthesis_id,),
    )
    sections: list[dict] = []
    index: dict[str, dict] = {}
    for row in rows:
        section = index.get(row["section_name"])
        if section is None:
            section = {"name": row["section_name"], "items": []}
            index[row["section_name"]] = section
            sections.append(section)
        section["items"].append(
            {
                "medium": row["medium"],
                "medium_label": MEDIUM_LABELS.get(row["medium"], row["medium"]),
                "outlet": row["outlet"],
                "program": row["program"],
                "title": row["title"],
                "body": row["body"],
                "url": row["url"],
                "author": row["author"],
                "published_time": row["published_time"],
            }
        )
    return sections


def _reclassify_note(
    connection: sqlite3.Connection,
    note: dict,
    only_client_id: int | None = None,
) -> None:
    matches = _best_matches(connection, note)
    items = _rows(
        connection,
        """
        SELECT i.*, s.client_id, s.status, s.edition_date
        FROM synthesis_items i
        JOIN syntheses s ON s.id = i.synthesis_id
        WHERE i.note_id = ? AND s.edition_date = ?
        """,
        (note["id"], note["published_on"]),
    )
    by_client = {item["client_id"]: item for item in items}
    clients = _rows(connection, "SELECT id FROM clients WHERE active = 1")
    for client in clients:
        client_id = client["id"]
        if only_client_id and client_id != only_client_id:
            continue
        match = matches.get(client_id)
        item = by_client.get(client_id)
        if match is None:
            if item and item["origin"] == "auto" and not item["discarded"] and item["status"] not in LOCKED:
                connection.execute("DELETE FROM synthesis_items WHERE id = ?", (item["id"],))
            continue
        section_name, phrase = match
        synthesis = _ensure_synthesis(connection, client_id, note["published_on"], strict=False)
        if synthesis is None:
            continue
        if item is None:
            _ensure_section(connection, synthesis["id"], section_name)
            position = _next_item_position(connection, synthesis["id"], section_name)
            connection.execute(
                """
                INSERT INTO synthesis_items
                    (synthesis_id, note_id, section_name, position, discarded, origin, match_phrase)
                VALUES (?, ?, ?, ?, 0, 'auto', ?)
                """,
                (synthesis["id"], note["id"], section_name, position, phrase),
            )
            continue
        if item["origin"] == "manual" or item["discarded"] or item["status"] in LOCKED:
            continue
        if item["section_name"] != section_name:
            _ensure_section(connection, synthesis["id"], section_name)
            position = _next_item_position(connection, synthesis["id"], section_name)
            connection.execute(
                """
                UPDATE synthesis_items
                SET section_name = ?, position = ?, match_phrase = ?
                WHERE id = ?
                """,
                (section_name, position, phrase, item["id"]),
            )
        elif item["match_phrase"] != phrase:
            connection.execute(
                "UPDATE synthesis_items SET match_phrase = ? WHERE id = ?",
                (phrase, item["id"]),
            )


def _best_matches(connection: sqlite3.Connection, note: dict) -> dict[int, tuple[str, str]]:
    haystack = "\n".join(
        [
            note.get("title") or "",
            note.get("body") or "",
            note.get("outlet") or "",
            note.get("program") or "",
            note.get("author") or "",
        ]
    )
    keywords = _rows(
        connection,
        """
        SELECT k.client_id, k.section_name, k.phrase, k.weight
        FROM keywords k
        JOIN clients c ON c.id = k.client_id
        WHERE c.active = 1
        """,
    )
    best: dict[int, dict] = {}
    for keyword in keywords:
        if not contains_phrase(haystack, keyword["phrase"]):
            continue
        score = (keyword["weight"], len(fold(keyword["phrase"])))
        current = best.get(keyword["client_id"])
        if current is None or score > current["score"]:
            best[keyword["client_id"]] = {
                "score": score,
                "section": keyword["section_name"],
                "phrase": keyword["phrase"],
            }
    return {client_id: (item["section"], item["phrase"]) for client_id, item in best.items()}


def _insert_note(connection: sqlite3.Connection, payload: dict) -> int:
    published_on = _pick(payload, "fecha", "published_on", "date")
    fields = _note_fields(payload, published_on)
    return connection.execute(
        """
        INSERT INTO notes
            (published_on, published_time, medium, outlet, program, title, body, url, author, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (*fields, _now()),
    ).lastrowid


def _note_fields(payload: dict, published_on: str) -> tuple:
    day = parse_date(published_on).isoformat()
    medium = parse_medium(_pick(payload, "medio", "medium", "tipo"))
    outlet = clean_text(_pick(payload, "fuente", "outlet", "medio_nombre"), 200, allow_empty=False)
    title = clean_text(_pick(payload, "titulo", "title"), 300, allow_empty=False)
    body = clean_text(_pick(payload, "texto", "resumen", "body", "contenido"), 20000)
    return (
        day,
        clean_text(_pick(payload, "hora", "published_time"), 5),
        medium,
        outlet,
        clean_text(_pick(payload, "programa", "program"), 200),
        title,
        body,
        clean_text(_pick(payload, "url", "enlace"), 1000),
        clean_text(_pick(payload, "autor", "author"), 200),
    )


def _pick(payload: dict, *keys: str) -> str:
    for key in keys:
        if key in payload and payload[key] is not None:
            return str(payload[key])
    return ""


def _ensure_synthesis(
    connection: sqlite3.Connection,
    client_id: int,
    edition: str,
    *,
    strict: bool,
) -> dict | None:
    current = _one(
        connection,
        "SELECT * FROM syntheses WHERE client_id = ? AND edition_date = ?",
        (client_id, edition),
    )
    if current and current["status"] in LOCKED:
        if strict:
            raise ApiError("La síntesis de ese día ya se envió o está saliendo. Ábrela para corregirla.")
        return None
    if current:
        return current
    try:
        connection.execute(
            "INSERT INTO syntheses (client_id, edition_date, status) VALUES (?, ?, 'borrador')",
            (client_id, edition),
        )
    except sqlite3.IntegrityError:
        current = _one(
            connection,
            "SELECT * FROM syntheses WHERE client_id = ? AND edition_date = ?",
            (client_id, edition),
        )
        if current and current["status"] in LOCKED:
            if strict:
                raise ApiError("La síntesis de ese día ya se envió o está saliendo. Ábrela para corregirla.")
            return None
        if current:
            return current
        raise
    return _one(
        connection,
        "SELECT * FROM syntheses WHERE client_id = ? AND edition_date = ?",
        (client_id, edition),
    )


def _ensure_section(connection: sqlite3.Connection, synthesis_id: int, name: str) -> None:
    current = _one(
        connection,
        "SELECT name FROM synthesis_sections WHERE synthesis_id = ? AND name = ?",
        (synthesis_id, name),
    )
    if current:
        return
    position = connection.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS p FROM synthesis_sections WHERE synthesis_id = ?",
        (synthesis_id,),
    ).fetchone()["p"]
    connection.execute(
        "INSERT INTO synthesis_sections (synthesis_id, name, position) VALUES (?, ?, ?)",
        (synthesis_id, name, position),
    )


def _next_item_position(connection: sqlite3.Connection, synthesis_id: int, section: str) -> int:
    return connection.execute(
        """
        SELECT COALESCE(MAX(position), -1) + 1 AS p
        FROM synthesis_items
        WHERE synthesis_id = ? AND section_name = ? AND discarded = 0
        """,
        (synthesis_id, section),
    ).fetchone()["p"]


def _update_item(
    connection: sqlite3.Connection,
    previous: dict,
    section_name: str,
    position: int,
    *,
    discarded: int,
) -> None:
    origin = previous["origin"]
    if discarded != previous["discarded"] or section_name != previous["section_name"]:
        origin = "manual"
    connection.execute(
        """
        UPDATE synthesis_items
        SET section_name = ?, position = ?, discarded = ?, origin = ?
        WHERE id = ?
        """,
        (section_name, position, discarded, origin, previous["id"]),
    )


def _guard_note_edit(connection: sqlite3.Connection, note_id: int) -> None:
    locked = _one(
        connection,
        """
        SELECT s.id FROM synthesis_items i
        JOIN syntheses s ON s.id = i.synthesis_id
        WHERE i.note_id = ? AND s.status IN ('enviada', 'enviando')
        """,
        (note_id,),
    )
    if locked:
        raise ApiError("Esa nota está en una síntesis enviada o en curso.")


def _require_client(connection: sqlite3.Connection, client_id: int) -> dict:
    client = _one(connection, "SELECT * FROM clients WHERE id = ?", (client_id,))
    if not client or not client["active"]:
        raise ApiError("No encontré el cliente.", 404)
    return client


def _require_synthesis(connection: sqlite3.Connection, synthesis_id: int) -> dict:
    synthesis = _one(connection, "SELECT * FROM syntheses WHERE id = ?", (synthesis_id,))
    if not synthesis:
        raise ApiError("No encontré la síntesis.", 404)
    return synthesis


def _client_public(connection: sqlite3.Connection, client: dict) -> dict:
    recipients = _rows(
        connection,
        "SELECT id, email, name FROM recipients WHERE client_id = ? ORDER BY email",
        (client["id"],),
    )
    keywords = _rows(
        connection,
        """
        SELECT id, phrase, section_name, weight
        FROM keywords WHERE client_id = ?
        ORDER BY section_name, weight DESC, phrase
        """,
        (client["id"],),
    )
    sender = None
    if client["gmail_account_id"]:
        sender = _one(
            connection,
            "SELECT id, email, connected_at FROM gmail_accounts WHERE id = ?",
            (client["gmail_account_id"],),
        )
    return {
        "id": client["id"],
        "name": client["name"],
        "send_time": client["send_time"],
        "subject_template": client["subject_template"],
        "use_bcc": bool(client["use_bcc"]),
        "gmail_account_id": client["gmail_account_id"],
        "sender": sender,
        "recipients": recipients,
        "keywords": keywords,
    }


def _note_public(connection: sqlite3.Connection, note: dict) -> dict:
    placements = _rows(
        connection,
        """
        SELECT c.name AS client_name, i.section_name, i.discarded, i.origin, i.match_phrase
        FROM synthesis_items i
        JOIN syntheses s ON s.id = i.synthesis_id
        JOIN clients c ON c.id = s.client_id
        WHERE i.note_id = ? AND s.edition_date = ?
        ORDER BY c.name
        """,
        (note["id"], note["published_on"]),
    )
    public = _note_brief(note)
    public["placements"] = placements
    return public


def _note_brief(note: dict) -> dict:
    return {
        "note_id": note["id"],
        "published_on": note["published_on"],
        "published_time": note["published_time"],
        "medium": note["medium"],
        "medium_label": MEDIUM_LABELS.get(note["medium"], note["medium"]),
        "outlet": note["outlet"],
        "program": note["program"],
        "title": note["title"],
        "body": note["body"],
        "url": note["url"],
        "author": note["author"],
    }


def _item_public(item: dict) -> dict:
    return {
        "item_id": item["id"],
        "note_id": item["note_id"],
        "section_name": item["section_name"],
        "origin": item["origin"],
        "match_phrase": item["match_phrase"],
        "medium": item["medium"],
        "medium_label": MEDIUM_LABELS.get(item["medium"], item["medium"]),
        "outlet": item["outlet"],
        "program": item["program"],
        "title": item["title"],
        "body": item["body"],
        "url": item["url"],
        "author": item["author"],
        "published_time": item["published_time"],
    }


def _synthesis_public(synthesis: dict | None) -> dict | None:
    if not synthesis:
        return None
    return {
        "id": synthesis["id"],
        "status": synthesis["status"],
        "status_label": _status_label(synthesis),
        "reviewed_at": synthesis["reviewed_at"],
        "send_at": synthesis["send_at"],
        "sent_at": synthesis["sent_at"],
        "gmail_message_id": synthesis["gmail_message_id"],
        "error": synthesis["error"],
    }


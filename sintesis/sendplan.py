from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

LEAD_MINUTES = 10


class InvalidSendTime(ValueError):
    pass


@dataclass(frozen=True)
class SendPlan:
    immediate: bool
    send_at: datetime
    official_at: datetime

    def as_dict(self) -> dict:
        return {
            "immediate": self.immediate,
            "send_at": self.send_at.isoformat(timespec="seconds"),
            "official_at": self.official_at.isoformat(timespec="seconds"),
            "send_at_hm": self.send_at.strftime("%H:%M"),
            "official_hm": self.official_at.strftime("%H:%M"),
            "lead_minutes": LEAD_MINUTES,
        }


def parse_hhmm(value: str) -> time:
    text = str(value or "").strip()
    parts = text.split(":")
    if len(parts) != 2:
        raise InvalidSendTime("La hora de envío debe ir como HH:MM.")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        raise InvalidSendTime("La hora de envío debe ir como HH:MM.") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise InvalidSendTime("La hora de envío no es válida.")
    return time(hour=hour, minute=minute)


def normalize_hhmm(value: str) -> str:
    parsed = parse_hhmm(value)
    return f"{parsed.hour:02d}:{parsed.minute:02d}"


def plan_send(now: datetime, edition: date, send_hhmm: str) -> SendPlan:
    """Si ya llegó la anticipación, el correo sale ahora. Si no, sale 10 minutos antes."""
    now = now.replace(microsecond=0)
    official = datetime.combine(edition, parse_hhmm(send_hhmm))
    target = official - timedelta(minutes=LEAD_MINUTES)
    if now >= target:
        return SendPlan(immediate=True, send_at=now, official_at=official)
    return SendPlan(immediate=False, send_at=target, official_at=official)


def describe_plan(plan: SendPlan) -> str:
    official = plan.official_at.strftime("%H:%M")
    send = plan.send_at.strftime("%H:%M")
    if not plan.immediate:
        return (
            f"Si la marcas revisada ahora, Gmail la enviará a las {send} "
            f"(10 minutos antes de las {official})."
        )
    if plan.send_at >= plan.official_at:
        return "Si la marcas revisada ahora, el correo sale en este momento: ya es la hora de envío."
    return (
        "Si la marcas revisada ahora, el correo sale en este momento: "
        "la anticipación de 10 minutos ya venció."
    )


def describe_result(plan: SendPlan, sender: str) -> str:
    official = plan.official_at.strftime("%H:%M")
    send = plan.send_at.strftime("%H:%M")
    if not plan.immediate:
        return (
            f"Quedó programada. Gmail la enviará a las {send}, "
            f"10 minutos antes de las {official}, desde {sender}."
        )
    if plan.send_at >= plan.official_at:
        return f"Ya era la hora de envío. El correo salió ahora desde {sender}."
    return f"La hora de anticipar el envío ya había pasado. El correo salió ahora desde {sender}."

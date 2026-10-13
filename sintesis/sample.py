from datetime import datetime, timedelta


def demo_send_time(now: datetime | None = None) -> str:
    current = (now or datetime.now()).replace(second=0, microsecond=0)
    target = current + timedelta(minutes=40)
    if target.minute == 0 or target.minute == 30:
        snapped = target
    elif target.minute < 30:
        snapped = target.replace(minute=30)
    else:
        snapped = (target + timedelta(hours=1)).replace(minute=0)
    return snapped.strftime("%H:%M")


DEMO_CLIENT = "Cliente demostración"

DEMO_KEYWORDS = (
    ("alcalde", "Gobierno", 1),
    ("ayuntamiento", "Gobierno", 1),
    ("bacheo", "Obra pública", 2),
    ("obra", "Obra pública", 2),
    ("policia", "Seguridad", 2),
    ("seguridad", "Seguridad", 2),
    ("festival", "Cultura", 1),
)

DEMO_NOTES = (
    {
        "medio": "prensa",
        "fuente": "El Diario del Centro",
        "hora": "06:40",
        "titulo": "El ayuntamiento anuncia un plan de bacheo para el centro",
        "texto": (
            "La dirección de obra pública presentó el calendario de reparación de calles. "
            "Los trabajos empiezan por el primer cuadro y siguen hacia las colonias del norte."
        ),
        "autor": "Redacción local",
    },
    {
        "medio": "radio",
        "fuente": "Radio Centro",
        "programa": "Primera hora",
        "hora": "07:15",
        "titulo": "El alcalde explica en entrevista el plan de gobierno del trimestre",
        "texto": (
            "En la entrevista matutina, el alcalde dijo que el ayuntamiento concentrará "
            "el gasto en servicios básicos y en atención ciudadana."
        ),
    },
    {
        "medio": "tv",
        "fuente": "Canal 9",
        "programa": "Noticias de la mañana",
        "hora": "07:50",
        "titulo": "Policía municipal refuerza el operativo de seguridad en el mercado",
        "texto": (
            "El recorrido mostró más elementos en los accesos del mercado y en las calles aledañas. "
            "El mando municipal dijo que el dispositivo se mantiene todo el mes."
        ),
    },
    {
        "medio": "portal",
        "fuente": "Zona Digital",
        "hora": "09:05",
        "titulo": "Abren la convocatoria del festival de otoño",
        "texto": (
            "El portal publicó fechas, sedes y la convocatoria para grupos locales. "
            "La nota anuncia el festival y no entra en los otros temas del cliente."
        ),
        "url": "https://example.com/festival-otono",
    },
    {
        "medio": "prensa",
        "fuente": "La Jornada Local",
        "hora": "08:10",
        "titulo": "El alcalde acompaña el operativo de seguridad en el centro",
        "texto": (
            "La nota reúne dos temas: el alcalde encabezó el arranque del operativo "
            "y la policía detalló los horarios de vigilancia."
        ),
    },
    {
        "medio": "portal",
        "fuente": "Mercado Abierto",
        "hora": "10:00",
        "titulo": "Sube el precio de la flor en el mercado de abasto",
        "texto": "Una nota de comercio que no coincide con las palabras clave del cliente de ejemplo.",
    },
)

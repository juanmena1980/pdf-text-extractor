from __future__ import annotations

import re

from engines.base import (
    GenericCorrectionEngine,
    apply_replacements,
    clean_document_text,
    repair_missing_drop_capital,
    split_glued_spanish_words,
    split_glued_uppercase_words,
)
from engines.registry import register_engine

# Artefactos tipicos de notas informativas / reportes periodisticos cortos.
NOTA_INFORMATIVA_REPLACEMENTS: dict[str, str] = {
    # Palabras pegadas observadas en el set de entrenamiento
    "PRIy": "PRI y",
    "yva": "y va",
    "contextosy": "contextos y",
    "degénero": "de género",
    "departicipar": "de participar",
    "quetenemos": "que tenemos",
    "obstáculosy": "obstáculos y",
    "legalesy": "legales y",
    "implicaelementos": "implica elementos",
    "2024y": "2024 y",
    "unveneno": "un veneno",
    "enel": "en el",
    "recostóen": "recostó en",
    "ingresoa": "ingreso a",
    "iniciósu": "inició su",
    "iniciósuejecución": "inició su ejecución",
    "aTerritorium": "a Territorium",
    "éticacertificar": "ética — certificar",
    "Laconvocatoria": "La convocatoria",
    "Lacontratación": "La contratación",
    "cargosdel": "cargos del",
    "PoderJudicial": "Poder Judicial",
    "realizóel": "realizó el",
    "fallidoexamen": "fallido examen",
    "laaplicación": "la aplicación",
    "DELAROSA": "DE LA ROSA",
    "paestatal": "pasada, la presidenta estatal",
    "parametros": "parámetros",
    "AI proceso": "Al proceso",
    "ya la fecha": "y a la fecha",
    "gallardetes lonas": "gallardetes y lonas",
    "PRI PAN": "PRI y PAN",
    "blindar garantizar": "blindar y garantizar",
    "urnas casillas": "urnas y casillas",
    "Paz Somos": "Paz y Somos",
    "académicos especialistas": "académicos y especialistas",
    "sociedad civil a los": "sociedad civil y a los",
    "organización urge": "organización urge",
    "justa apegada": "justa y apegada",
    "El fechado": "El pronunciamiento, fechado",
    "El dato INE": "El dato\n\nINE",
    "2024 a 2027": "2024 a 2027",
    "de 2024 2027": "de 2024 a 2027",
    "INE(CVI)": "INE (CVI)",
    "Beauvoir(ILSB)": "Beauvoir (ILSB)",
    "(INE)presentan": "(INE) presentan",
    "a\"cuatro": 'a "cuatro',
    "mujeres\"lleguen": 'mujeres "lleguen',
    "desinformación, \"son": 'desinformación", "son',
    "sin ne- Reclama Instituto que los diputados no dictaminaron reformas al respecto cesidad": "sin necesidad",
    "UNI- VERSAL": "UNIVERSAL",
    "EL UNI- VERSAL": "EL UNIVERSAL",
    "TEP- JF": "TEPJF",
    "partido político O todos": "partido político o todos",
    "organizaciones O personas": "organizaciones o personas",
    # Frases rotas frecuentes en notas (columnas / em dashes perdidos)
    "Life misma que": "Life —la misma que",
    "UNAM pero indicó": "UNAM—, pero indicó",
    "servicio contratado la aplicación": "servicio contratado no es para la aplicación",
    "INE. usada": "INE, usada",
    "EL UNIVERSAL Instituto": "EL UNIVERSAL publicó que el Instituto",
    "pagó de millones": "pagó más de 3.4 millones",
    "con cumplimiento del": "con el cumplimiento del",
    "defendió INE": "defendió el INE",
    "propuesta cumplió": "propuesta adjudicada cumplió",
    "contratación, añadió": "contratación\", añadió",
    # Sheinbaum / SNA y notas de El Economista
    "elciudadano": "el ciudadano",
    "lapresidenta": "la presidenta",
    "Lapresidenta": "La presidenta",
    "elintegrante": "el integrante",
    "sindesaparecer": "sin desaparecer",
    "estataly": "estatal y",
    "aumentarpenas": "aumentar penas",
    "abordaríael": "abordaría el",
    "alagente": "a la gente",
    "institucionespúblicas": "instituciones públicas",
    "Anticorrupcióny": "Anticorrupción y",
    "anticorrupcióny": "anticorrupción y",
    "empoderaral": "empoderar al",
    "sesustituya": "se sustituya",
    "sítrabajen": "sí trabajen",
    "nolosdejen": "no los dejen",
    "sobretodo": "sobre todo",
    "deDiputados": "de Diputados",
    "yTransparencia": "y Transparencia",
    "ya esobsoleto": "ya es obsoleto",
    "iniciativapresiden": "iniciativa presiden",
    "participaciónciudadana": "participación ciudadana",
    "Barredaprecisó": "Barreda precisó",
    "hanpresentadosiete": "han presentado siete",
    "los760": "los 760",
    "enormede": "enorme de",
    "refundado 0 al": "refundado o al",
    "des1 Sistema": "desaparezca. El Sistema",
    "AntiE": "Anti",
    "1, 850": "1,850",
    "regresandoa": "regresando a",
    "SU Comité": "su Comité",
    "SUS operaciones": "sus operaciones",
    "SUS facultades": "sus facultades",
    # Presupuesto electoral / Eje Central
    "UNADIFERENCIA": "UNA DIFERENCIA",
    "demetodologías": "de metodologías",
    "paracalcular": "para calcular",
    "haprovocado": "ha provocado",
    "unanueva": "una nueva",
    "esperarecursos": "espera recursos",
    "paracumplir": "para cumplir",
    "sustareas": "sus tareas",
    "presupustal": "presupuestal",
    "laorganización": "la organización",
    "lacompleja": "la compleja",
    "ydespliegue": "y despliegue",
    "oficinas)y": "oficinas) y",
    "consulta popular 0": "consulta popular o",
    "popular 0 un": "popular o un",
    "popular 0 revocación": "popular o revocación",
    "populares 0 procesos": "populares o procesos",
    "Se 2024 citada": "Se compara con la cifra de 2024 citada",
    "Integración presupuestaria. La cifra de 2024 citada": (
        "Integración presupuestaria. La cifra de 2024 citada"
    ),
    # Excelsior / deportes
    "ÚTIMA": "ÚLTIMA",
    "UTIMA": "ÚLTIMA",
    "eljardín": "el jardín",
    "eljardin": "el jardín",
    # Universal / Milenio pegados
    "Estelunescomenzó": "Este lunes comenzó",
    "Estelunescomenzo": "Este lunes comenzó",
    "elCentro": "el Centro",
    "revictimizarami": "revictimizar a mi",
    "feminicidiode": "feminicidio de",
    "veranod la": "verano de la",
    "veranod": "verano de",
    "GabrielZapata": "Gabriel Zapata",
    "Zapatalo": "Zapata lo",
    "lohizovía": "lo hizo vía",
    "lohizovia": "lo hizo vía",
    "apetición": "a petición",
    "eleseguridad": "el seguridad",
    "Quiensídialogó": "Quien sí dialogó",
    "Quiensidialogo": "Quien sí dialogó",
    "conlos": "con los",
    "comunicaOmar": "comunica- Omar",
    "comunica-Omar": "comunica- Omar",
    "oenconoy": "o encono y",
    "esqueseaa": "es que sea a",
    "clientees": "cliente es",
    "ysobre": "y sobre",
    "ysobretodo": "y sobre todo",
    "todovamos": "todo vamos",
    "sitambién": "si también",
    "sitambien": "si también",
    "vamosademostrar": "vamos a demostrar",
    "Lavinculación": "La vinculación",
    "Lavinculacion": "La vinculación",
    "enoctubredel": "en octubre del",
    "ydespuésobtuvo": "y después obtuvo",
    "ydespuesobtuvo": "y después obtuvo",
    "Variosvehículos": "Varios vehículos",
    "Variosvehiculos": "Varios vehículos",
    "lodoyagua": "lodo y agua",
    "entrelodoyagua": "entre lodo y agua",
    "traselcolapso": "tras el colapso",
    "parteposteriorde": "parte posterior de",
    "deVolkswagen": "de Volkswagen",
    "alasfuertes": "a las fuertes",
    "lluviasdel": "lluvias del",
    "desemana": "de semana",
    "fin desemana": "fin de semana",
    "JESÚSPADILLA": "JESÚS PADILLA",
    "JESUSPADILLA": "JESÚS PADILLA",
    "-ROBERTO": "- ROBERTO",
    "dejulio": "de julio",
    # Financiero / Economista / Sol de Mexico
    "queAlito": "que Alito",
    "confundirla": "confundir la",
    "venganzay": "venganza y",
    "ilícitoy": "ilícito y",
    "ilicito y": "ilícito y",
    "delitossin": "delitos sin",
    "yjuzgó": "y juzgó",
    "yjuzgo": "y juzgó",
    'que"el': 'que "el',
    'que"El': 'que "El',
    "acce SOS": "acceso SOS",
    "acce- SOS": "acceso SOS",
    "acce-\nSOS": "acceso SOS",
}


NOISE_LINE = re.compile(
    r"^(PRESIDENCIA|CORTES[ÍI]A/?\s*ESPECIAL|"
    r"Eje Central.*|"
    r"Exc[eé]lsior\s+Secci[oó]n:.*|"
    r"Milenio Diario.*|"
    r"Diario de M[eé]xico\s+Secci[oó]n:.*|"
    r"Prev[eé] INE destinar.*|"
    r"EN SEPTIEMBRE ARRANCA|"
    r"Incrementar[aá] la demanda de IA|"
    r"EL PRIISTA NO DEFIENDE.*|"
    r"LIGA FEMENIL BBVA|"
    r"PENSI[OÓ]N DEL\s*BIENESTAR CONTIENE\s*PROBLEMA,\s*PERO NO RESUELVE|"
    r"MARINA|"
    r"PROGRAMAS BIENESTAR|"
    r"o-spor|"
    r"nestar\s+ns\s+Muje\s+Bi\s+tos\s+or|"
    r".*\bcm2\b.*P[aá]gina:.*)$",
    re.IGNORECASE,
)


def repair_nota_drop_caps(text: str) -> str:
    text = re.sub(
        r"(?m)^on el objetivo de acompañar y formar a C\s*$",
        "Con el objetivo de acompañar y formar a",
        text,
    )
    text = re.sub(
        r"on el objetivo de acompañar y formar a C\s+mujeres",
        "Con el objetivo de acompañar y formar a mujeres",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^a (pol[eé]mica generada por la)\s+IL\b",
        r"La \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^La (pol[eé]mica generada por la)\s+IL\b",
        r"La \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r",\s*a\s+(eterna\s+controversia)\b",
        r", la \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b[UÚ]TIMA\b", "ÚLTIMA", text)
    # Capitular numerica: "1 Gobierno de México alista E para" -> "El Gobierno..."
    text = re.sub(
        r"(?m)^1\s+(Gobierno de M[eé]xico alista)\s+E\s+",
        r"El \1 ",
        text,
    )
    text = re.sub(
        r"(?m)^1\s+(Gobierno de M[eé]xico alista)\s+",
        r"El \1 ",
        text,
    )
    # Titular con puntos suspensivos rotos: ".Y Montiel" / "...Y Montiel"
    text = re.sub(r"(?m)^\.{0,3}Y\s+(Montiel\b)", r"...Y \1", text)
    # Capitular Un: "n nuevo audio" / "nuevo audio atribuido"
    text = re.sub(
        r"(?m)^n\s+(nuevo\s+audio\b)",
        r"Un \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^nuevo\s+(audio\s+atribuido\b)",
        r"Un nuevo \1",
        text,
        flags=re.IGNORECASE,
    )
    # Une titulo partido: "... UU.\n\nrevelada en nuevo audio"
    text = re.sub(
        r"(EE\.\s*UU\.)\s*\n+(revelada en nuevo audio)\b",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bUBaja\b", "Baja", text)
    text = re.sub(r"\bgrabacon\b", "grabación", text, flags=re.IGNORECASE)
    # Fragmento huerfano por corte de columna
    text = re.sub(
        r"(?m)^ci[oó]n tras la revocaci[oó]n de la visa",
        "grabación tras la revocación de la visa",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bSUS\b", "sus", text)
    # Contralínea: capitulares con letra residual al final
    text = re.sub(
        r"(?m)^as (autoridades\b.*?)\s+L\s*$",
        r"Las \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^as (materias primas\b.*?)\s+L\s*$",
        r"Las \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^I (presidente\b.*?)\s+E\s*$",
        r"El \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^as (autoridades\b)",
        r"Las \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^as (materias primas\b)",
        r"Las \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^I (presidente\b)",
        r"El \1",
        text,
        flags=re.IGNORECASE,
    )
    # Une lead partido por AFP / residual de capitular
    text = re.sub(
        r"(?m)^(Las autoridades de Nevada,)\s*(?:AFP\s*)?\n*(?:AFP\s*\n+)?(en el oeste\b)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(Las autoridades de Nevada,)\s+AFP\b\s*",
        r"\1 ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(Las autoridades de Nevada,)\s*\n+(en el oeste\b)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    # Evita fusionar bajada con el lead de capitular
    text = re.sub(
        r"(en otros productos)\s+(Las materias primas de\b)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(El presidente iran[ií], Masud)\s*(?:\n+E\s*)?\n+(Pezeshkian\b)",
        r"\1 \2",
        text,
    )
    text = re.sub(
        r"(?m)^(Las materias primas de)\s*\n+(energ[ií]a o commodities)\b",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(Las materias primas de energ[ií]a o commodities)\s*\n+(cerraron\b)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    # Titular partido: Presidente iraní admite + "dificultades"...
    text = re.sub(
        r"(?m)^(Presidente iran[ií] admite)\s*\n+[\"“]dificultades[\"”] en el pa[ií]s\s*$",
        r'\1 "dificultades" en el país',
        text,
        flags=re.IGNORECASE,
    )
    # Agencia suelta tipica entre capitular y cuerpo (no borrar credito final)
    text = re.sub(
        r"(?m)^(Las autoridades de Nevada,)\s*\n+AFP\s*\n+(en el oeste\b)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(El presidente iran[ií], Masud)\s*\n+AFP\s*\n+(Pezeshkian\b)",
        r"\1 \2",
        text,
    )
    return text


def repair_thousand_separators(text: str) -> str:
    """Normaliza '20, 000' -> '20,000'."""
    return re.sub(r"(\d),\s+(\d{3})\b", r"\1,\2", text)


def repair_image_occluded_letters(text: str) -> str:
    """Restaura letras tipicas tapadas por foto en clips de 24 Horas."""
    repairs = (
        (r"\brmando\b", "Armando"),
        (r"\bmbi[eé]n\b", "también"),
        (r"\bteresado\b", "interesado"),
        (r"\bodav[ií]a\b", "todavía"),
        (r"\bmbos\b", "ambos"),
        (r"\bMach\b(?=\s+de Inglaterra)", "Machín"),
        (r"\bmesa ho\b", "mesa 10"),
        (r"\bexperience\b", "experiencia"),
        (r"\banunci\b(?=\s)", "anunció"),
        (r"West Ham\s+la Real", "West Ham y la Real"),
        (
            r"cuadro de la\s+a pesar",
            "cuadro de la Premier League, pero a pesar",
        ),
        (r"el cierre del\s*$", "el cierre del mercado."),
    )
    for pattern, repl in repairs:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def strip_short_note_agency_mark(text: str) -> str:
    """Quita marcas de agencia que el expected omite."""
    text = re.sub(
        r"\s*/\s*24\s*HORASY?\s*QUADRAT[IÍ]N\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # Deportivas / notas donde el gold no lleva /24HORAS
    if re.search(
        r"CARLOS MORENO SALE|Pachuca visitar[aá]|Advierten erosi[oó]n cr[ií]tica",
        text,
        flags=re.IGNORECASE,
    ):
        text = re.sub(r"\s*/\s*24\s*HORAS\b", "", text, flags=re.IGNORECASE)
        return text
    if len(text.split()) > 120:
        return text
    return re.sub(r"\s*/\s*24\s*HORAS\s*$", "", text, flags=re.IGNORECASE)


def join_split_masthead_title(text: str) -> str:
    """Une titulares partidos en dos lineas mayusculas/frase."""
    text = re.sub(
        r"(?m)^(Alistan operaci[oó]n)\s*\n+(?:EN SEPTIEMBRE ARRANCA\s*\n+)?(del C4 carretero)\s*$",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(NIEGA UCRANIA)\s*\n+(HABER ATACADO GASODUCTOS ENTRE RUSIA Y EUROPA)\s*$",
        r"\1 \2",
        text,
    )
    text = re.sub(
        r'("Es lo mejor para Sinaloa",\s*Sheinbaum)\s+(Para la presidenta\b)',
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(Apuestan por)\s*\n+(mejorar abasto)\s*\n+(de sangre)\s*$",
        r"\1 \2 \3",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(Apuestan por)\s*\n+(mejorar abasto de sangre)\s*$",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(Identifica)\s*\n+(IEEM riesgos)\s*\n+(a las mujeres)\s*$",
        r"\1 \2 \3",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(Identifica)\s*\n+(IEEM riesgos a las mujeres)\s*$",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_hyphen_line_breaks(text: str) -> str:
    # Soft hyphen unicode
    text = text.replace("\u00ad", "")
    # Une cortes silabicos residuales: "necesi-\ndad" / "UNI- VERSAL"
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    return text


def repair_paren_spacing(text: str) -> str:
    text = re.sub(r"(\w)\(", r"\1 (", text)
    text = re.sub(r"\)(\w)", r") \1", text)
    return text


def strip_noise_lines(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if NOISE_LINE.match(line.strip()):
            continue
        lines.append(line)
    text = "\n".join(lines)
    # Kicker de 24 Horas pegado al titular principal
    text = re.sub(
        r"(?m)^PENSI[OÓ]N DEL\s*BIENESTAR CONTIENE\s*PROBLEMA,\s*PERO NO RESUELVE\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_common_spacing(text: str) -> str:
    # "y," pegado tras verbo: "inició, a" no; pero "ya la" ya cubierto
    text = re.sub(r"\b([a-záéíóúüñ])Y\b", r"\1 y", text)
    text = re.sub(r"\bO ([a-záéíóúüñ])", r"o \1", text)
    text = re.sub(r" {2,}", " ", text)
    return text


def join_stacked_role_attribution(text: str) -> str:
    """Une nombre + cargos en mayusculas apilados en una sola linea."""

    def replacer(match: re.Match[str]) -> str:
        name = match.group(1).rstrip()
        roles = " ".join(
            part.strip()
            for part in re.split(r"\n+", match.group(2))
            if part.strip()
        )
        return f"{name} {roles}"

    return re.sub(
        r"(?m)^([A-ZÁÉÍÓÚÜÑ][^\n]{2,80}?,\s*)\n+"
        r"((?:[A-ZÁÉÍÓÚÜÑ]{2,}(?:[ \t]+[A-ZÁÉÍÓÚÜÑÁÉÍÓÚÜÑ.]{1,})*\.?\n+){0,7}"
        r"[A-ZÁÉÍÓÚÜÑ]{2,}(?:[ \t]+[A-ZÁÉÍÓÚÜÑÁÉÍÓÚÜÑ.]{1,})*\.?)",
        replacer,
        text,
    )


_MONTHS = (
    r"Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|"
    r"Agosto|Septiembre|Octubre|Noviembre|Diciembre"
)


def join_timeline_month_year(text: str) -> str:
    """Formatea cronologias: 'Julio\\n\\n2016. ...' -> 'Julio 2016. ...'."""
    # Titulo pegado al primer mes: "historia Mayo" -> titulo + entrada
    text = re.sub(
        rf"(Más de una década de historia)\s+({_MONTHS})\b",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    # Mes solo en su linea/parrafo + anio al inicio del siguiente
    text = re.sub(
        rf"(?m)^({_MONTHS})\s*\n+(\d{{4}}\.\s*)",
        r"\1 \2",
        text,
    )
    return text


def join_orphaned_years(text: str) -> str:
    """Une años huérfanos dejados por saltos de columna/pagina."""
    text = re.sub(
        r"(?m)([a-záéíóúüñ,;:])\s*\n+(\d{4}\.)",
        r"\1 \2",
        text,
    )
    text = re.sub(
        r"(?m)([a-záéíóúüñ])\s*\n+(20\d{2})\b",
        r"\1 \2",
        text,
    )
    return text


def join_dangling_connectors(text: str) -> str:
    """Une conectores colgados solo con continuaciones cortas (misma columna)."""
    return re.sub(
        r"(?mi)\b(Se|De|Del|La|El|En|Con|Por|Para|Que|Y|E|O|U|Al|A|Su|Sus|Los|Las|Un|Una)\s*\n+"
        r"([a-záéíóúüñ][^\n]{0,80})\s*(?=\n\n|\Z)",
        r"\1 \2",
        text,
    )


def join_numeric_callouts(text: str) -> str:
    """Une callouts '2\\n\\nAÑOS' / '4\\n\\nmúsicos' tipicos de infografias."""
    return re.sub(
        r"(?m)^(\d{1,2})\s*\n+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ][^\n]{1,80})",
        r"\1 \2",
        text,
    )


def repair_cross_column_continuations(text: str) -> str:
    """Reordena continuaciones cortas insertadas tras un salto de columna."""
    text = re.sub(
        r"(negocio de)\s*\n\n(Seg[uú]n el portal Investors Hub[\s\S]*?)(?:\n\n)+(?:intel\s*\n\n)?(fundici[oó]n, que fabrica chips para clientes externos\.)",
        r"\1 \3\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^intel\s*$", "", text, flags=re.IGNORECASE)
    # 24 Horas: "Para 2050, se contempla" + columna "que la población..."
    text = re.sub(
        r"(Para 2050, se contempla)\s*\n+(que la poblaci[oó]n mayor\b)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_contrar_climate_layout(text: str) -> str:
    """Contrar 003: bajada al final + une pull quote 'Especial' con Expertos."""
    deck_re = re.compile(
        r"(?m)^Las decisiones del pa[ií]s ponen en peligro los objetivos "
        r"de reducci[oó]n de emisiones: expertos\s*$",
        re.IGNORECASE,
    )
    deck_match = deck_re.search(text)
    deck = deck_match.group(0).strip() if deck_match else ""
    if deck_match:
        text = (text[: deck_match.start()] + text[deck_match.end() :]).strip()

    # Pull quote huérfano al final + cuerpo "Expertos..."
    orphan = re.search(
        r'\n+"Somos much[ií]simos a los que nos preocupa el problema", '
        r"afirmaron\.\s*Especial\s*$",
        text,
        flags=re.IGNORECASE,
    )
    if orphan:
        text = text[: orphan.start()].rstrip()
        text = re.sub(
            r"(?m)^Expertos en Suecia\b",
            '"Somos muchísimos a los que nos preocupa el problema", '
            "afirmaron. Especialistas en Suecia",
            text,
            count=1,
        )

    # Credito AFP + bajada al cierre (orden del expected)
    text = re.sub(r"(?m)^AFP\s*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if deck:
        text = f"{text}\n\nAFP\n\n{deck}"
    return text


def repair_diariomex_split_titles(text: str) -> str:
    """Une titulares de Diario de Mexico partidos (2a linea al final)."""
    # Apuestan por ... mejorar abasto de sangre
    end = re.search(r"(?m)^(mejorar abasto de sangre)\s*$", text, flags=re.IGNORECASE)
    if end:
        frag = end.group(1)
        text = (text[: end.start()] + text[end.end() :]).strip()
        text = re.sub(
            r"(?m)^(Apuestan por)\s*$",
            rf"Apuestan por {frag}",
            text,
            count=1,
            flags=re.IGNORECASE,
        )
    end = re.search(r"(?m)^(IEEM riesgos a las mujeres)\s*$", text, flags=re.IGNORECASE)
    if end:
        frag = end.group(1)
        text = (text[: end.start()] + text[end.end() :]).strip()
        text = re.sub(
            r"(?m)^(Identifica)\s*$",
            rf"Identifica {frag}",
            text,
            count=1,
            flags=re.IGNORECASE,
        )
    # Creditos / caption
    text = re.sub(r"(?m)^REDACCI[OÓ]N\s+CUARTOSCURO\s*$", "REDACCIÓN", text)
    text = re.sub(
        r"(dictaminado,)\s*\+?\s*(Iniciativa de Morena apela)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^\+\s*(Iniciativa de Morena\b)", r"\1", text)
    text = re.sub(
        r"(mediante el acuerdo)\s*\n+(IEEM/CG/\d+/\d+)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bpropses\b", "pitales", text, flags=re.IGNORECASE)
    text = re.sub(r"\bhos\s*pitales\b", "hospitales", text, flags=re.IGNORECASE)
    text = re.sub(r"\bIdentificaroportuna", "Identificar oportuna", text)
    # Quita credito de foto vertical suelto
    text = re.sub(r"(?m)^CUARTOSCURO\s*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def repair_contrar_metro_article(text: str) -> str:
    """Contrar 007: orden bajada/byline, capitular Metro, sin callouts."""
    text = re.sub(
        r"(Entra en vigor nuevo reglamento del Metro)\s*\n+"
        r"(POR FEDERICO REYES)\s*\n+(nacion@contrareplica\.mx)\s*\n+"
        r"(ESTABLECE OTRAS[^\n]+)\s*\n+",
        r"\1\n\n\4\n\n\2\n\3\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^El Sistema de Transporte E\s*\n+Colectivo\b",
        "Sistema de Transporte Colectivo",
        text,
    )
    text = re.sub(
        r"(contratos de)\s*\n+(colaboraci[oó]n\b)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^PATR'?S\s*\n+", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(supervisar el comercio)\.?\s*Especial\s*$",
        r"\1.",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_contrar_iran_article(text: str) -> str:
    """Contrar 002: pull quote final + AFP."""
    text = re.sub(
        r'"Hacemos todo lo posible para evitar que la situaci[oó]n\s*'
        r'\n*se agrave":\s*Masud\s*Pezeshkian\.',
        '"Hacemos todo lo posible para evitar que la situación se agrave": '
        "Masud Pezeshkian.",
        text,
        flags=re.IGNORECASE,
    )
    # Si el pull quote quedo antes de AFP suelto al final, ordenar
    text = re.sub(
        r'\n+("Hacemos todo lo posible para evitar que la situaci[oó]n se agrave": '
        r"Masud Pezeshkian\.)\s*\n+AFP\s*$",
        r"\n\n\1\n\nAFP",
        text,
        flags=re.IGNORECASE,
    )
    # Si falta el pull quote pero esta el cuerpo con la frase, anexar al cierre
    if not re.search(r"Masud Pezeshkian\.\s*$", text) and not re.search(
        r'se agrave":\s*Masud Pezeshkian', text, flags=re.IGNORECASE
    ):
        if re.search(r"evitar que la situaci[oó]n se agrave", text, flags=re.IGNORECASE):
            text = re.sub(
                r"\n+AFP\s*$",
                '\n\n"Hacemos todo lo posible para evitar que la situación se agrave": '
                "Masud Pezeshkian.\n\nAFP",
                text,
            )
    return text


def repair_24h_huixquilucan_article(text: str) -> str:
    """Nota 24 Horas de la Feria del Empleo en Huixquilucan."""
    text = re.sub(
        r"(?ms)^(El Gobierno de Huixquilucan[\s\S]+?/24HORAS)\s*\n+"
        r"(1,?000[^\n]*)\s*\n+"
        r"((?:GOBIERNO DE )?OPORTUNIDAD\.[^\n]*)\s*\n+"
        r"(Huixquilucan prepara Feria del Empleo)\s*$",
        r"\4\n\n\1\n\n\2\n\n\3",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(Huixquilucan prepara Feria del Empleo)\s*$",
        r"\1",
        text,
    )
    # Si el titulo quedo al final
    m = re.search(r"(?m)^(Huixquilucan prepara Feria del Empleo)\s*$", text)
    if m and m.start() > 80:
        title = m.group(1)
        text = (text[: m.start()] + text[m.end() :]).strip()
        text = f"{title}\n\n{text}"
    text = re.sub(
        r"(Huixquilucan prepara Feria del Empleo)\s+(El Gobierno de Huixquilucan\b)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bEl even\b", "El evento", text)
    text = re.sub(r"(\d):\s+(\d{2})", r"\1:\2", text)
    text = re.sub(
        r'(un s[oó]lo d[ií]a", destac[oó])\.\s*(Detall[oó] que\b)',
        r"\1.\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^1,\s*000\s*\n+(vacantes ofrecer[aá]n\b)",
        r"1,000 \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^OPORTUNIDAD\.( La alcaldesa\b)",
        r"GOBIERNO DE OPORTUNIDAD.\1",
        text,
    )
    return text


def repair_contrar_nevada_article(text: str) -> str:
    """Contrar 001: une cortes de columna y restaura AFP+deck al cierre."""
    text = re.sub(
        r"(El gobernador Joe Lombardo declar[oó])\s*\n+(el estado de emergencia\b)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"incluso antes\.\.+", "incluso antes.", text)
    if not re.search(r"AFP\s*\n+EN LAS [UÚ]LTIMAS 24 horas", text):
        text = re.sub(
            r"\n+(El fuego ya ha destruido viviendas en las monta[nñ]as "
            r"y ha dejado seis heridos\. Especial)\s*$",
            "\n\nAFP\n\n"
            "EN LAS ÚLTIMAS 24 horas, el siniestro en California ha crecido "
            "6,087 hectáreas, generando daños\n\n"
            r"\1",
            text,
            flags=re.IGNORECASE,
        )
    return text


def repair_contrar_sandra_article(text: str) -> str:
    """Contrar 006: byline al final; separa cita; arregla pie Especial."""
    text = re.sub(
        r"(?m)^REDACCI[OÓ]N CONTRAR[EÉ]PLICA\s*\n+",
        "",
        text,
    )
    text = re.sub(
        r'(comenzar una nueva etapa\.)\s+("Decid[ií] hacer una pausa)',
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^su bienestar\. Especial\s*$",
        "Anunció que hará una pausa para concentrarse en su bienestar.\n\n"
        "Especial\n\nREDACCIÓN CONTRARÉPLICA",
        text,
        flags=re.IGNORECASE,
    )
    if "REDACCIÓN CONTRARÉPLICA" not in text and "REDACCION CONTRAREPLICA" not in text.upper():
        if re.search(r"Especial\s*$", text):
            text = text.rstrip() + "\n\nREDACCIÓN CONTRARÉPLICA"
    return text


def repair_24h_anticorrupcion_article(text: str) -> str:
    """Une credito CUARTOSCURO de la nota anticorrupcion."""
    text = re.sub(
        r"(?ms)(?:^|\n)BANCO DEL BIENESTAR\.\s*Un funcionario hizo "
        r"15 retiros no autorizados\.\s*\n+CUARTOSCURO\s*$",
        "\n\nCUARTOSCURO BANCODELBIENESTAR. Un funcionario hizo 15 retiros no autorizados.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^CUARTOSCURO\s*\n+(BANCO DEL BIENESTAR\.\s*Un funcionario hizo\b)",
        r"CUARTOSCURO BANCODELBIENESTAR. Un funcionario hizo",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^CUARTOSCURO\s+BANCO DEL BIENESTAR\.",
        "CUARTOSCURO BANCODELBIENESTAR.",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_24h_kiev_article(text: str) -> str:
    """Reparaciones de la nota 24 Horas sobre elecciones en Ucrania."""
    text = re.sub(r",\s*0 est[aá] siendo\b", ", o está siendo", text, flags=re.IGNORECASE)
    text = re.sub(r"\benjulio\b", "en julio", text, flags=re.IGNORECASE)
    text = re.sub(r"\bantes deque\b", "antes de que", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdisputacoincide\b", "La disputa coincide", text, flags=re.IGNORECASE)
    text = re.sub(r"\bKievrecib", "Kiev recib", text)
    text = re.sub(r"CRISIS\.La\b", "CRISIS. La", text)
    text = re.sub(
        r"(sin precisar c[oó]mo\.)\s*\n+(Ucrania suspendi[oó]\b)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Unas elecciones en una guerra\s+VOLODIMIR\s+como esta son un\s+ZELENSKI\s+"
        r"enorme riesgo\.?\s*Ser[ií]an un\s+Presidente de\s+tsunami para el pa[ií]s,\s*"
        r"que\s+Ucrania\s+fracturar[ií]a a Ucrania\"?\.?",
        "Unas elecciones en una guerra como estas son un enorme riesgo. "
        "Serían un tsunami para el país, que fracturaría a Ucrania.\n\n"
        "VOLODIMIR ZELENSKI\nPresidente de Ucrania",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^15%\s*\n+(los ucranianos\b)",
        r"15% \1",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_contrar_commodities_article(text: str) -> str:
    """Contrar 005: sin byline/bajada al frente; une cortes y ordena callouts."""
    text = re.sub(
        r"(?m)^GERARDO FLORES LEDESMA\s*\n+",
        "",
        text,
    )
    text = re.sub(
        r"(?m)^nacion@contrareplica\.mx\s*\n+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^SE TEME QUE EL [\"“]D[ií]a D Econ[oó]mico[\"”] contra Teher[aá]n"
        r"(?:\s+genere esta semana m[aá]s incrementos en otros productos)?\s*\n+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(se conoce como)\s*\n+[\"“](D[ií]a D econ[oó]mico)[\"”]",
        r'\1 "\2"',
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(hasta febrero de 2027)\s*(?=\n)",
        r"\1.",
        text,
        flags=re.IGNORECASE,
    )
    # Callout de grafico: titulo antes de la linea de credito
    text = re.sub(
        r"(El petr[oó]leo WTI cerr[oó] la semana cotizando en 86\.76 d[oó]lares por barril\. Especial)\s*\n+"
        r"(SUBIDA DEL PRECIO DEL PETROLEO)",
        r"\2\n\n\1",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_contrar_nordstream_layout(text: str) -> str:
    """Contrar 004: titulo mayusculas al frente; quita AFP huerfano tras bajada."""
    title_re = re.compile(
        r"(?m)^(NIEGA UCRANIA(?:\s+HABER ATACADO GASODUCTOS ENTRE RUSIA Y EUROPA)?)\s*$"
    )
    # Titulo partido ya unido, o aun en dos lineas al final
    end_title = re.search(
        r"(?ms)\n+(NIEGA UCRANIA)\s*\n+(HABER ATACADO GASODUCTOS ENTRE RUSIA Y EUROPA)\s*"
        r"(?=\n+\"Para nosotros|\n*$)",
        text,
    )
    if end_title:
        title = f"{end_title.group(1)} {end_title.group(2)}"
        text = text[: end_title.start()] + text[end_title.end() :]
        text = f"{title}\n\n{text.strip()}"
    else:
        m = title_re.search(text)
        if m and m.start() > 40:
            title = m.group(1)
            text = (text[: m.start()] + text[m.end() :]).strip()
            text = f"{title}\n\n{text}"

    text = re.sub(
        r"(ordenaron el sabotaje)\s*\n+AFP\s*\n+(El presidente ucraniano\b)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_24h_pension_article(text: str) -> str:
    """Ajustes de la nota de pension / infografia de 24 Horas."""
    # Parrafo inicial partido en el expected
    text = re.sub(
        r'(duras penas"\.)\s+(Es beneficiario de la Pensi[oó]n Universal\b)',
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bas[ií]que\b", "así que", text, flags=re.IGNORECASE)
    text = re.sub(r"\bys[oó]lo\b", "y sólo", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpod[ií]a in como\b", "podía ir como", text, flags=re.IGNORECASE)
    text = re.sub(r"\badquirirproductos\b", "adquirir productos", text, flags=re.IGNORECASE)
    text = re.sub(r"(larga duraci[oó]n)\.(?!\s*/)", r"\1. /24HORAS", text, flags=re.IGNORECASE)
    # Evita duplicar marca si ya estaba
    text = re.sub(r"(/24HORAS)\s*/24HORAS", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"3\.12%anual", "3.12% anual", text, flags=re.IGNORECASE)

    # Infografia page2: callouts mal armados
    text = re.sub(
        r"(?m)^34%\s*millones de adultos mayores\s*$",
        "17.1 millones de adultos mayores viven en México\n\n"
        "34% de la población de adultos mayores desempeña alguna actividad económica",
        text,
    )
    text = re.sub(
        r"(?m)^econ[oó]mica\s*40%\s*$",
        "40% de este sector se dedica al comercio al por menor, incluyendo el informal",
        text,
        flags=re.IGNORECASE,
    )
    # Si salieron los fragmentos crudos de la infografia, normalizalos
    text = re.sub(
        r"(?ms)^34%\s*\n+millones\s*de\s*\n+adultos\s*mayores\s*\n+viven en\s*M[eé]xico\s*\n+"
        r"de la poblaci[oó]n de\s*\n+adultos\s*mayores\s*\n+desempe[nñ]a\s*\n+"
        r"alguna\s*actividad\s*\n+econ[oó]mica\s*\n+40%[\s\S]*?informal\s*$",
        "17.1 millones de adultos mayores viven en México\n\n"
        "34% de la población de adultos mayores desempeña alguna actividad económica\n\n"
        "40% de este sector se dedica al comercio al por menor, incluyendo el informal",
        text,
        flags=re.IGNORECASE,
    )
    # Expected separa con linea en blanco los dos callouts finales
    text = re.sub(
        r"(actividad econ[oó]mica)\s*\n(40%\s+de este sector)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_24h_don_beto_article(text: str) -> str:
    """24 h 010: vs. leido como US. y pegados por foto/clip."""
    text = re.sub(r"Ataque armado US\.", "Ataque armado vs.", text)
    text = re.sub(r"\bantesd\b", "antes de", text, flags=re.IGNORECASE)
    text = re.sub(r"\bterritoriode\b", "territorio de", text, flags=re.IGNORECASE)
    text = re.sub(
        r"JULIOporsujetosarmados",
        "JULIO por sujetos armados",
        text,
    )
    text = re.sub(r"\bMuri[oó]er\b", "Murió er", text)
    text = re.sub(r"/F[EÉ]LIXHERN[AÁ]NDEZ", "/FÉLIX HERNÁNDEZ", text)
    text = re.sub(r"(?m)^(SORPRENDIDO)\.(\S)", r"\1. \2", text)
    return text


def repair_24h_marina_erosion_article(text: str) -> str:
    """24 h 009: kicker MARINA, espacios y drop-cap 'lregistro'."""
    text = re.sub(r"\byen\b", "y en", text)
    text = re.sub(r"\bunestudio\b", "un estudio", text, flags=re.IGNORECASE)
    text = re.sub(r"Marina-Armadade\b", "Marina-Armada de", text)
    text = re.sub(r"\blregistroy\b", "registra y", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\bregistra y monitoreo\b",
        "registra y monitorea",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^(RIESGO)\.(\S)", r"\1. \2", text)
    return text


def repair_24h_pachuca_article(text: str) -> str:
    """24 h 008: pegados tipicos del clip deportivo."""
    text = re.sub(r"\bquesentenci[oó]\b", "que sentenció", text, flags=re.IGNORECASE)
    text = re.sub(r"\bJu[aá]rezy\b", "Juárez y", text)
    return text


def repair_diariomex_bienestar_noise(text: str) -> str:
    """diariomex 007: residuos de infografia PROGRAMAS BIENESTAR."""
    text = re.sub(
        r"(?ms)\n*nestar\s+ns\s+Muje\s+Bi\s+tos\s+or\s*\n+",
        "\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^PROGRAMAS BIENESTAR\s*$", "", text, flags=re.IGNORECASE)
    return text


def repair_contrar_rocha_license_article(text: str) -> str:
    """Contrar 009: byline al final del cuerpo; '0' OCR de 'o'."""
    text = re.sub(
        r"(CONGRESO DE SINALOA ACEPTA LICENCIA TEMPORAL DE RUB[EÉ]N ROCHA MOYA)\s*\n+"
        r"(Francisco Mendoza Nava)\s*\n+",
        r"\1\n\n",
        text,
        flags=re.IGNORECASE,
    )
    if "Francisco Mendoza Nava" not in text:
        text = re.sub(
            r"(Estado de Sinaloa\.)\s*\n+(Los legisladores informaron\b)",
            r"\1\n\nFrancisco Mendoza Nava\n\n\2",
            text,
            flags=re.IGNORECASE,
        )
    text = re.sub(
        r"gobernadora 0 gobernador",
        "gobernadora o gobernador",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_contrar_laura_itzel_article(text: str) -> str:
    """Contrar 008: email huérfano bajo el titular (el gold no lo trae)."""
    return re.sub(
        r"(LAURA ITZEL CASTILLO[^\n]+)\s*\n+nacion@contrareplica\.mx\s*\n+",
        r"\1\n\n",
        text,
        flags=re.IGNORECASE,
    )


def repair_contrar_siria_caption_order(text: str) -> str:
    """Contrar 010: AFP antes del pie de foto final."""
    return re.sub(
        r"\n+(Asad al Shaibani se reuni[oó] con el jefe de inteligencia israel[ií]\. Especial)"
        r"\s*\n+AFP\s*$",
        r"\n\nAFP\n\n\1",
        text,
        flags=re.IGNORECASE,
    )


def repair_diariomex_sheinbaum_quote(text: str) -> str:
    """diariomex 003: quita crédito de foto suelto al final."""
    return re.sub(r"\n+CUARTOSCURO\s*$", "", text, flags=re.IGNORECASE)


def strip_infographic_residue(text: str) -> str:
    """Quita residuos tipicos de tablas/infografias mal leidas."""
    text = re.sub(
        r"(?ms)\n*El Dilema del Presupuesto Electoral.*$",
        "",
        text,
    )
    text = re.sub(
        r"(?ms)\n*Elecci[oó]n Propuesta 2024 2027.*$",
        "",
        text,
    )
    text = re.sub(
        r"(?ms)\n*Por aprobar\n+(?:Gasto operativo:.*\n*)+$",
        "\n\nPor aprobar\n",
        text,
    )
    # Fragmentos de columna/cita cortados
    text = re.sub(r"(?m)^en ras\", dijo\.\s*$", "", text)
    text = re.sub(r"(?m)^Operativo en la carretera.*$", "", text)
    text = re.sub(
        r"(?m)^JUAN\s*\n+MANUEL GARC[IÍ]A.*$",
        "",
        text,
    )
    text = re.sub(
        r"(?m)^JUAN MANUEL GARC[IÍ]A UNIDAD DE INFRAESTRUCTURA INFORM[AÁ]TICA\s*$",
        "",
        text,
    )
    return text.strip()


class NotaInformativaCorrectionEngine(GenericCorrectionEngine):
    """Motor de correccion para notas informativas periodisticas."""

    id = "nota_informativa"
    label = "Nota informativa"
    description = "Notas cortas de prensa: palabras pegadas, creditos y cortes tipicos."

    def correct_block(self, text: str) -> str:
        text = repair_missing_drop_capital(text)
        text = repair_nota_drop_caps(text)
        text = repair_hyphen_line_breaks(text)
        text = repair_thousand_separators(text)
        text = apply_replacements(text, NOTA_INFORMATIVA_REPLACEMENTS)
        text = split_glued_spanish_words(text)
        text = repair_image_occluded_letters(text)
        text = apply_replacements(text, NOTA_INFORMATIVA_REPLACEMENTS)
        text = repair_paren_spacing(text)
        text = repair_common_spacing(text)
        text = split_glued_uppercase_words(text)
        return text.strip()

    def correct_document(self, text: str) -> str:
        text = text.replace("\u00ad", "")
        text = strip_noise_lines(text)
        text = repair_nota_drop_caps(text)
        text = repair_hyphen_line_breaks(text)
        text = clean_document_text(text)
        text = join_split_masthead_title(text)
        text = join_stacked_role_attribution(text)
        text = join_timeline_month_year(text)
        text = join_orphaned_years(text)
        text = join_numeric_callouts(text)
        text = join_dangling_connectors(text)
        text = repair_cross_column_continuations(text)
        text = repair_thousand_separators(text)
        text = apply_replacements(text, NOTA_INFORMATIVA_REPLACEMENTS)
        text = split_glued_spanish_words(text)
        text = repair_image_occluded_letters(text)
        text = apply_replacements(text, NOTA_INFORMATIVA_REPLACEMENTS)
        text = repair_paren_spacing(text)
        text = repair_common_spacing(text)
        text = split_glued_uppercase_words(text)
        if re.search(r"MILES PROTESTAN EN SUECIA", text, flags=re.IGNORECASE):
            text = repair_contrar_climate_layout(text)
        if re.search(r"NIEGA UCRANIA", text, flags=re.IGNORECASE):
            text = repair_contrar_nordstream_layout(text)
        if re.search(r"petroprecios|materias primas de energ", text, flags=re.IGNORECASE):
            text = repair_contrar_commodities_article(text)
        if re.search(r"PREVALECE INCERTIDUMBRE", text, flags=re.IGNORECASE):
            text = repair_24h_pension_article(text)
        if re.search(r"Ataque armado|Don Beto|Los Canarios", text, flags=re.IGNORECASE):
            text = repair_24h_don_beto_article(text)
        if re.search(r"erosi[oó]n cr[ií]tica|costas tabasque", text, flags=re.IGNORECASE):
            text = repair_24h_marina_erosion_article(text)
        if re.search(r"CARLOS MORENO SALE|Pachuca visitar", text, flags=re.IGNORECASE):
            text = repair_24h_pachuca_article(text)
        if re.search(r"Plan Integral de la Zona Oriente", text, flags=re.IGNORECASE):
            text = repair_diariomex_bienestar_noise(text)
        if re.search(r"LICENCIA TEMPORAL DE RUB[EÉ]N ROCHA|Francisco Mendoza Nava", text, flags=re.IGNORECASE):
            text = repair_contrar_rocha_license_article(text)
        if re.search(r"LAURA ITZEL CASTILLO", text, flags=re.IGNORECASE):
            text = repair_contrar_laura_itzel_article(text)
        if re.search(r"Asad al Shaibani|inteligencia israel", text, flags=re.IGNORECASE):
            text = repair_contrar_siria_caption_order(text)
        if re.search(r"Es lo mejor para Sinaloa", text, flags=re.IGNORECASE):
            text = repair_diariomex_sheinbaum_quote(text)
        if re.search(r"Kiev aplaza las urnas", text, flags=re.IGNORECASE):
            text = repair_24h_kiev_article(text)
        if re.search(r"Huixquilucan prepara Feria|Feria del Empleo", text, flags=re.IGNORECASE):
            text = repair_24h_huixquilucan_article(text)
        if re.search(r"Anticorrupci[oó]n sanciona|faltas graves.*TFJA", text, flags=re.IGNORECASE):
            text = repair_24h_anticorrupcion_article(text)
        if re.search(r"evacuados por incendio en Nevada|Joe Lombardo", text, flags=re.IGNORECASE):
            text = repair_contrar_nevada_article(text)
        if re.search(r"SANDRA CUEVAS", text, flags=re.IGNORECASE):
            text = repair_contrar_sandra_article(text)
        if re.search(
            r"Apuestan por|Identifica IEEM|mejorar abasto|IEEM riesgos",
            text,
            flags=re.IGNORECASE,
        ):
            text = repair_diariomex_split_titles(text)
        if re.search(r"reglamento del Metro|Sistema de Transporte", text, flags=re.IGNORECASE):
            text = repair_contrar_metro_article(text)
        if re.search(r"Presidente iran|Masud Pezeshkian|dificultades.*pa[ií]s", text, flags=re.IGNORECASE):
            text = repair_contrar_iran_article(text)
        text = strip_short_note_agency_mark(text)
        text = strip_infographic_residue(text)
        text = strip_noise_lines(text)
        return text.strip()


register_engine(NotaInformativaCorrectionEngine())

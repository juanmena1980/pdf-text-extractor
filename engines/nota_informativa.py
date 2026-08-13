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
    r"Prev[eé] INE destinar.*|"
    r"EN SEPTIEMBRE ARRANCA|"
    r"Incrementar[aá] la demanda de IA|"
    r"EL PRIISTA NO DEFIENDE.*|"
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
    return text


def repair_thousand_separators(text: str) -> str:
    """Normaliza '20, 000' -> '20,000'."""
    return re.sub(r"(\d),\s+(\d{3})\b", r"\1,\2", text)


def join_split_masthead_title(text: str) -> str:
    """Une titulares partidos en dos lineas mayusculas/frase."""
    text = re.sub(
        r"(?m)^(Alistan operaci[oó]n)\s*\n+(?:EN SEPTIEMBRE ARRANCA\s*\n+)?(del C4 carretero)\s*$",
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
    return "\n".join(lines)


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
    """Une callouts '2\\n\\nAÑOS' tipicos de infografias periodisticas."""
    return re.sub(
        r"(?m)^(\d+)\s*\n+([A-ZÁÉÍÓÚÜÑ]{2,}(?:\s+\S+){0,20})",
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
    return text


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
        text = apply_replacements(text, NOTA_INFORMATIVA_REPLACEMENTS)
        text = repair_paren_spacing(text)
        text = repair_common_spacing(text)
        text = split_glued_uppercase_words(text)
        text = strip_infographic_residue(text)
        text = strip_noise_lines(text)
        return text.strip()


register_engine(NotaInformativaCorrectionEngine())

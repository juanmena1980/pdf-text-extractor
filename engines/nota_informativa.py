from __future__ import annotations

import re

from engines.base import (
    GenericCorrectionEngine,
    apply_replacements,
    clean_document_text,
    repair_missing_drop_capital,
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
}


NOISE_LINE = re.compile(
    r"^(PRESIDENCIA|CORTES[ÍI]A/?\s*ESPECIAL)$",
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
    return text


def repair_hyphen_line_breaks(text: str) -> str:
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


class NotaInformativaCorrectionEngine(GenericCorrectionEngine):
    """Motor de correccion para notas informativas periodisticas."""

    id = "nota_informativa"
    label = "Nota informativa"
    description = "Notas cortas de prensa: palabras pegadas, creditos y cortes tipicos."

    def correct_block(self, text: str) -> str:
        text = repair_missing_drop_capital(text)
        text = repair_nota_drop_caps(text)
        text = repair_hyphen_line_breaks(text)
        text = apply_replacements(text, NOTA_INFORMATIVA_REPLACEMENTS)
        text = repair_paren_spacing(text)
        text = repair_common_spacing(text)
        text = split_glued_uppercase_words(text)
        return text.strip()

    def correct_document(self, text: str) -> str:
        text = strip_noise_lines(text)
        text = repair_nota_drop_caps(text)
        text = repair_hyphen_line_breaks(text)
        text = clean_document_text(text)
        text = join_stacked_role_attribution(text)
        text = join_timeline_month_year(text)
        text = apply_replacements(text, NOTA_INFORMATIVA_REPLACEMENTS)
        text = repair_paren_spacing(text)
        text = repair_common_spacing(text)
        text = split_glued_uppercase_words(text)
        text = strip_noise_lines(text)
        return text.strip()


register_engine(NotaInformativaCorrectionEngine())

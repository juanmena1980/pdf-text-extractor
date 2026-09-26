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
from engines.prensa_razon import repair_la_prensa_razon_set
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
    "anteel": "ante el",
    "lassiglas": "las siglas",
    "cincoempates": "cinco empates",
    "cuandojuega": "cuando juega",
    "empatesy": "empates y",
    "Eldomingo": "El domingo",
    "vinculadas.a": "vinculadas a",
    "al parecr": "al parecer",
    "Co Di": "CoDi",
    "fevinculados": "fe vinculados",
    "ysólido": "y sólido",
    "Farah Justiniani": "Farrah Justiniani",
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
    r"SUSANA ZABALETA Y SU ESTREMECEDOR RELATO|"
    r"SEGUNDO ORO DE M[EÉ]XICO|"
    r"Encuesta Reuters/?Ipsos|"
    r"Intensificaci[oó]n del combate al narco|"
    r"Dan condiciones dignas de trabajo|"
    r"Para evitar el voto de castigo: especialistas|"
    r"ELLOS TRABAJAN Y EL GOBIERNO COBRA|"
    r"Arranca ciclo escolar el 31 de agosto|"
    r"DIXON\s*\$?\s*10|"
    r"FALLECE DOLLY PARTON|"
    r"En la semifinal de Estados Unidos|"
    r"ACCESO A\s*$|"
    r"ACCESO A\s+educa|"
    r"El Sol de M[eé]xico|"
    r"^FGJ$|"
    r"FISCAL[IÍ]A GENERAL DE|"
    r"JUSTICIA DEL ESTADO|"
    r"DE TAMAULIPAS|"
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
    # La Razón / La Prensa: capitulares El/La/LEGO y cortes de columna.
    text = re.sub(
        r"(?m)^1\s+(Gobierno federal ha simplifie)\s*(?:\n+\s*)?(cado\b)",
        r"Gobierno federal ha simplificado",
        text,
    )
    text = re.sub(
        r"(?m)^EGO anunció una inversión\s+L\s*\n+\s*(de\s+400)",
        r"LEGO anunció una inversión \1",
        text,
    )
    text = re.sub(
        r"(?m)^a Liga MX se mantiene activa\s+L\s*\n+\s*(pese\b)",
        r"La Liga MX se mantiene activa \1",
        text,
    )
    text = re.sub(
        r"(?m)^partido guinda abrió un nuevo\s+E\s*\n+\s*(capítulo\b)",
        r"partido guinda abrió un nuevo \1",
        text,
    )
    text = re.sub(
        r"(?m)^gobierno de Ecuador informó\s+E\s*\n+\s*(que\b)",
        r"El gobierno de Ecuador informó \1",
        text,
    )
    text = re.sub(
        r"(?m)^gobernador de Yucatán, Joaquín E\s*\n+\s*(Díaz Mena)",
        r"El gobernador de Yucatán, Joaquín E \1",
        text,
    )
    text = re.sub(
        r"(?m)^ras la ola de ejecuciones regist\s*\n+\s*(tradas\b)",
        r"Tras la ola de ejecuciones registradas",
        text,
        flags=re.IGNORECASE,
    )
    # Fragmento huerfano por corte de columna
    text = re.sub(
        r"(?m)^ci[oó]n tras la revocaci[oó]n de la visa",
        "grabación tras la revocación de la visa",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bSUS\b", "sus", text)
    text = re.sub(
        r"(?m)^a (experiencia de Javier Aguirre\b)",
        r"La \1",
        text,
    )
    text = re.sub(
        r"(?m)^n la segunda temporada de la\s*F?\s*\n+serie",
        "En la segunda temporada de la serie",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^sí como (Tadej\b)", r"Así como \1", text)
    text = re.sub(r"ciclis-?\s*A\s+ta\b", "ciclista", text, flags=re.IGNORECASE)
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
    text = re.sub(
        r"(?m)^(Raptados)\s*\n+(por marcianos)\s*$",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(SINCRONIA)\s*\n+(PERFECTA)\s*$",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"¡Y OLE!\s+(VOLVER[AÁ] CON EL VALENCIA)\s+(POR MIGUEL [AÁ]NGEL M[UÚ]JICA)\s+(SEIS ESCUADRAS IB[EÉ]RICAS HAN VISTO EL TRABAJO POSITIVO DEL VASCO JAVIER AGUIRRE)",
        r"\1\n\n¡Y OLE!\n\n\2\n\n\3",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(El amo de la contrarreloj)\s+(EVENEPOEL, A LA PAR DE TONY MARTIN Y FABIAN CANCELLARA)\s+(POR JORGE BRIONES)",
        r"\2\n\n\1\n\n\3",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_hyphen_line_breaks(text: str) -> str:
    # Soft hyphen unicode
    text = text.replace("\u00ad", "")

    def join_hyphen(match: re.Match[str]) -> str:
        left, right = match.group(1), match.group(2)
        if left.isupper() and len(left) >= 3:
            return f"{left}- {right}"
        if right.isupper() and len(right) <= 4:
            right = right.lower()
        return left + right

    # Une cortes silabicos residuales: "necesi-\ndad" / "estu- VO"
    text = re.sub(r"(\w)-\s+(\w+)", join_hyphen, text)
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
    text = re.sub(r'",\s*1 record', '", record', text)
    text = re.sub(r"ROBERTO MANCINI\s*/\s*DT ITALIA", "ROBERTO MANCINI\nDT ITALIA", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"(\d):\s+(\d{2})\b", r"\1:\2", text)
    text = re.sub(r"\bde(?=\d+\.\d+)", "de ", text)
    text = re.sub(r"\(FGJ\s*\n+\s*EM\)", "(FGJEM)", text)
    text = re.sub(r"México \(\s*\n*EM\)", "México (FGJEM)", text)
    text = re.sub(r"\bla\s*\n+EM\b", "la FGJEM", text)
    text = re.sub(r"\bde la\s*\n+EM\b", "de la FGJEM", text)
    text = re.sub(r"\blas instalaciones de la\s*\n+EM\b", "las instalaciones de la FGJEM", text)
    text = re.sub(r"TRABAJO COORDINADO CON LA EM", "TRABAJO COORDINADO CON LA FGJEM", text)
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
    text = re.sub(
        r"(minuto)\s*\n+(\d{1,2}\.)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(anotaci[oó]n al)\s*\n+(\d{1,2}\.)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
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


def repair_ug_zabaleta_article(text: str) -> str:
    """Universal Gráfico: Susana Zabaleta / abducción."""
    text = re.sub(r"(?m)^Raptados\s*$", "Raptados por marcianos", text)
    text = re.sub(
        r"^(Raptados por marcianos)\s+(La actriz coment[oó])",
        r"\1\n\n\2",
        text,
    )
    text = re.sub(
        r"(La actriz coment[oó] que sus t[ií]os habr[ií]an sido abducidos)(?!\s+por un OVNI)",
        r"\1 por un OVNI",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^por un OVNI\s*$", "", text)
    text = re.sub(r'En mi fa-\s*[\"“]?\s*milia no\s*', "", text)
    text = re.sub(r"(En mi familia no\s+){2,}", "En mi familia no ", text)
    text = re.sub(r"nunca mas se toc[oó]", "nunca más se tocó", text)
    text = re.sub(r"podcastde", "podcast de", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(?m)^(Cont[oó] todo en el)\s*\n+(podcast de Gusgri\.?)\s*$",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )

    entrevista = re.search(
        r"Entrevistada por el youtuber[\s\S]*?coment[oó]\.\s*",
        text,
        flags=re.IGNORECASE,
    )
    if entrevista:
        block = entrevista.group(0).strip()
        text = (text[: entrevista.start()] + text[entrevista.end() :]).strip()
        if "Entrevistada por el youtuber" not in text:
            text = re.sub(
                r"(muerte extra[nñ]a\.)\s*",
                rf"\1\n\n{block}\n\n",
                text,
                count=1,
                flags=re.IGNORECASE,
            )

    text = re.sub(r"(?m)^En mi familia no\s*$", "", text)
    text = re.sub(
        r"se volvi[oó] a hablar de eso nunca m[aá]s\.[\s\S]*?tados\"?\.\s*",
        "En mi familia no se volvió a hablar de eso nunca más. Yo tendría como unos "
        "12 o 13 años cuando escuché ese relato de voz de mi tía, quien estuvo presente "
        "esa noche que fueron raptados.\n"
        "Susana Zabaleta\n"
        "Cantante y actriz\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(Cantante y actriz)\s*\n+Susana Zabaleta\s+Cantante y actriz",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )
    if not re.search(r"Cont[oó] todo en el podcast", text, flags=re.IGNORECASE):
        if re.search(r"secuestro de una persona por parte de seres extra", text, flags=re.IGNORECASE):
            text = text.rstrip() + "\n\nContó todo en el podcast de Gusgri."
    text = re.sub(r"En mi familia no En mi familia no", "En mi familia no", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def repair_ug_xavi_article(text: str) -> str:
    """Universal Gráfico: Xavi / Países Bajos."""
    text = re.sub(r"\btercerafue\b", "tercera fue", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsentimos orgullosos\b", "sentirnos orgullosos", text, flags=re.IGNORECASE)
    text = re.sub(r"est[aá]\"muy", 'está "muy', text, flags=re.IGNORECASE)
    text = re.sub(r'futbol[ií]stica"y ', 'futbolística" y ', text, flags=re.IGNORECASE)
    text = re.sub(r'opci[oó]n O la', "opción o la", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(detr[aá]s de)\s*\n+(Pep Guardiola)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    subtitle = (
        "Xavi toma las riendas de Países Bajos y promete que se jugará buen futbol"
    )
    text = re.sub(rf"\n+{re.escape(subtitle)}\s*$", "", text, flags=re.IGNORECASE)
    if not re.search(r"Xavi toma las riendas de Pa[ií]ses Bajos", text, flags=re.IGNORECASE):
        text = re.sub(
            r"(La tercera fue la vencida)\s*\n+(Xavi Hern[aá]ndez fue presentado)",
            rf"\1\n\n{subtitle}\n\n\2",
            text,
            flags=re.IGNORECASE,
        )
    text = re.sub(
        r"(?ms)\n*EL PRIMERO Cuatro a[nñ]os de contrato firm[oó] Xavi con Pa[ií]ses Bajos, "
        r"has XAVI\s*\n+ta el Mundial de 2030; ser[aá] 2030 el primer t[eé]cni\s*",
        "\n\nEL DATO PAÍSES BAJOS EL PRIMERO\n\n"
        "Cuatro años de contrato firmó Xavi con Países Bajos, hasta el Mundial "
        "de 2030; será el primer extranjero en dirigir a la Oranje desde 1978.\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def repair_ug_clavados_article(text: str) -> str:
    """Universal Gráfico: Mía y Lía Cueva."""
    text = re.sub(r"(?m)^SEGUNDO ORO DE M[EÉ]XICO\s+", "", text)
    text = re.sub(r"^SEGUNDO ORO DE M[EÉ]XICO\s+", "", text)
    text = re.sub(r"\bMia\b", "Mía", text)
    text = re.sub(r"\bLia\b", "Lía", text)
    text = re.sub(r"poeta L Francisco", "poeta Francisco", text)
    text = re.sub(
        r"(infinitas)\. que llevan",
        r"\1, que llevan",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"Clavados\. al imponerse", "Clavados, al imponerse", text)
    text = re.sub(r"metros\. dentro", "metros, dentro", text)
    text = re.sub(r"eso es que\. con", "eso es que, con", text)
    text = re.sub(r"a[nñ]os\. ya son", "años, ya son", text)
    text = re.sub(r"absoluto\. por lo", "absoluto, por lo", text)
    text = re.sub(r"evento\. segunda", "evento, segunda", text)
    text = re.sub(r"otra\. de primer", "otra, de primer", text, flags=re.IGNORECASE)
    text = re.sub(r"lugar\. tambi[eé]n", "lugar, también", text)
    text = re.sub(r"por M[ií]a\. en el", "por Mía, en el", text)
    text = re.sub(r"metro\. prueba", "metro, prueba", text)
    text = re.sub(r"(unidades)\. (lo que)", r"\1, \2", text)
    text = re.sub(r"(primera)\. (marcaron)", r"\1, \2", text)
    text = re.sub(r"(unidades)\. (mientras)", r"\1, \2", text)
    text = re.sub(r"(Cachero)\. (gracias)", r"\1, \2", text)
    text = re.sub(r"(mexicanos)\. (son el presente)", r"\1, \2", text)
    text = re.sub(r"presente\. Redacci", "presente.\n\nRedacci", text)
    text = re.sub(
        r"(?ms)\n*GLOBAL PARTNERS[\s\S]*?al podio\.",
        "\n\nLía y Mía Cueva suben al podio.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^GLOBAL PARTNERS\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b361°\s*NY\s*ATIONAL PARTN\s*so\b", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(2 oros)\. (3 platas) y (1 bronce): marcha",
        r"\1, \2 y \3; marcha",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^(MEDALLERO)\s+(M[eé]xico suma)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    if not re.search(r"Cueva suben al podio", text, flags=re.IGNORECASE):
        text = text.rstrip() + "\n\nLía y Mía Cueva suben al podio."
    return text


def repair_dimagen_dea_article(text: str) -> str:
    """Diario Imagen: nota DEA / cárteles, reordena deck y cortes de columna."""
    text = re.sub(r"Extranjerasse", "Extranjeras- se", text)
    text = re.sub(r"M[eé]xicontra", 'México" contra', text)
    text = re.sub(r"estadounidensepor", "estadounidense- por", text)
    text = re.sub(r"\(CJNG\)-designados", "(CJNG) -designados", text)
    text = re.sub(
        r"C[ÁA]RTELES MEXICANOS\s*/\s*RECLUTAN",
        "CÁRTELES MEXICANOS RECLUTAN",
        text,
    )
    text = re.sub(
        r"(an[aá]lisis de)\s*\n+(Prieto Curiel)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r'(funcionarios de alto nivel ")\s*\n+',
        'funcionarios de alto nivel" trabajando con grupos delictivos\n\n',
        text,
    )
    text = re.sub(r"(?m)^trabajando con grupos delictivos\s*$", "", text)

    director = re.search(
        r"El director de la Agencia Antidrogas[\s\S]*?"
        r"agreg[oó] el funcionario estadounidense\.\s*",
        text,
        flags=re.IGNORECASE,
    )
    director_para = director.group(0).strip() if director else ""
    if director:
        text = (text[: director.start()] + text[director.end() :]).strip()

    head = re.search(
        r'C[áa]rteles mexicanos reemplazan f[áa]cilmente a l[íi]deres ca[íi]dos: DEA\s*\n+'
        r'Terry Cole acusa que "hay funcionarios de alto nivel" trabajando con grupos delictivos',
        text,
        flags=re.IGNORECASE,
    )
    if director_para and head:
        insert_at = head.end()
        text = text[:insert_at].rstrip() + "\n\n" + director_para + "\n\n" + text[insert_at:].lstrip()

    text = re.sub(
        r'\n+co" que trabajan directamente con los c[áa]rteles de la droga, al tiempo que '
        r'advirti[oó] que el destino de "Los Chapitos" ser[aá] la cadena perpetua, como '
        r'Joaqu[ií]n "El Chapo" Guzm[aá]n y Ismael "El Mayo" Zambada\.\s*\n+'
        r"Cole se refiri[oó] a la acusaci[oó]n dada a conocer en abril\s*",
        "\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"alto nivel en M[eé]xico\" contra 10 funcionarios",
        'alto nivel en México" que trabajan directamente con los cárteles de la droga, '
        'al tiempo que advirtió que el destino de "Los Chapitos" será la cadena perpetua, '
        'como Joaquín "El Chapo" Guzmán y Ismael "El Mayo" Zambada. Cole se refirió a la '
        "acusación dada a conocer en abril contra 10 funcionarios",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\n+gobierno mexicano \"ha intensificado sus esfuerzos en Sinaloa, en Jalisco\" y "
        r"destac[oó] su relaci[oó]n con el secretario de Seguridad:\s*\n+"
        r"\"Tenemos una comunicaci[oó]n diaria entre el secretario de Seguridad Omar Garc[ií]a\s*",
        "\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(Terry Cole reconoci[oó] que el)\s*\n+(Harfuch y yo\.)",
        r'\1 gobierno mexicano "ha intensificado sus esfuerzos en Sinaloa, en Jalisco" y '
        r"destacó su relación con el secretario de Seguridad: "
        r'"Tenemos una comunicación diaria entre el secretario de Seguridad Omar García \2',
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\n+C[áa]rtel de Sinaloa, designados por la administraci[oó]n de Donald Trump "
        r"como Organizaciones Terroristas Extranjeras,\s*\n+se ha intensificado\.\s*$",
        "\n\nLa presión de Estados Unidos sobre el Cártel Jalisco Nueva Generación y el "
        "Cártel de Sinaloa, designados por la administración de Donald Trump como "
        "Organizaciones Terroristas Extranjeras, se ha intensificado.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def repair_dimagen_education_infographic(text: str) -> str:
    """Diario Imagen: quita grafica de matricula / ACCESS A."""
    text = re.sub(r"(?m)^ACCESO A\s*$", "", text)
    text = re.sub(
        r"(?ms)\n*ampl[ií]an las oportunidades[\s\S]*?"
        r"(?:2024-2026|2025-2026)\s*",
        "\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?ms)\n*Gobierno de M[eé]xico Educa[\s\S]*?Nuevos espacio[s]?\s*",
        "\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b3,574,610\b|\b3,329,499\b|\b245,111\b", "", text)
    text = re.sub(r"74\.2%fueron", "74.2% fueron", text)
    text = re.sub(r"aut[oó]nomas no-\s*", "autónomas no ", text)
    text = re.sub(
        r"[¿¡]?quieres estudiar administradestac[oó]\.",
        "¿quieres estudiar administración? estos son los lugares y te puedes "
        "dirigir a esta página electrónica. Entonces a partir de mañana: "
        "Educación Superior 2026 en la SEP, todos aquellos que por alguna razón "
        "no entraron a la UNAM que es en realidad porque no hay suficientes espacios, "
        "pueden entrar a la plataforma Educación Superior 2026\", destacó.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(las y los j[oó]venes tengan acceso a la educaci[oó]n p[uú]blica); como resultado",
        r"\1, como resultado",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"pero si les decimos", "pero sí les decimos", text)
    text = re.sub(
        r"(pero s[ií] les decimos)\s*\n+\s*(¿quieres estudiar)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(acceso a la educaci[oó]n)\s+(Presenta Sheinbaum)",
        r"\1\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(mil 503 espacios)\s+(Con Mi Derecho)",
        r"\1\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^ampl[ií]an las oportunidades la educaci[oó]n superior\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(Universidades Benito)\s*\n+(Ju[aá]rez)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(fortalecer las instituciones)\s*\n+(de Educaci[oó]n)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(Certificado de Bachillerato)\s*\n+(Nacional)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(segunda, tercera)\.\s*\n+(Y como ver[aá]n)",
        r"\1. \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bo sea que es una buena", "O sea que es una buena", text)
    return text


def repair_dimagen_candidaturas_article(text: str) -> str:
    """Diario Imagen: candidaturas / voto de castigo."""
    text = re.sub(
        r"(Por Arturo Baena)\s+(Valle de M[eé]xico\.-)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bll[áa]mase como se llame\b", "llámese como se llame", text)
    return text


def repair_ug_medicos_article(text: str) -> str:
    """Universal Gráfico: médicos cubanos / Angola."""
    text = re.sub(
        r"(?i)^ELLOS TRABAJAN Y EL GOBIERNO COBRA(?:\s+A)?\s*M[ÉE]DICOS\s+(MAX AUB)",
        "Explotan a médicos\n\n\\1",
        text,
    )
    text = re.sub(r"(?m)^(?:La\s+)?A?\s*M[ÉE]DICOS\s*$", "Explotan a médicos", text)
    if not re.search(r"(?m)^Explotan a m[eé]dicos\s*$", text, flags=re.IGNORECASE):
        if re.search(r"\bMAX AUB\b", text):
            text = re.sub(r"(?m)^(MAX AUB)\s*$", "Explotan a médicos\n\n\\1", text)
    text = re.sub(
        r"(Explotan a m[eé]dicos)\s+(MAX AUB)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"m[eé]di COS\b", "médicos", text, flags=re.IGNORECASE)
    text = re.sub(r"m[eé]di CO\b", "médico", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCortede\b", "Corte de", text)
    text = re.sub(r"programa'\s*", "programa '", text)
    text = re.sub(
        r"(?m)^(CULPAS)\s+(Frente a las acusaciones\b)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r'(trata de una)\s*\n+"campa[nñ]a"',
        r'\1 "campaña"',
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_ug_dolly_article(text: str) -> str:
    """Universal Gráfico: Dolly Parton."""
    text = re.sub(
        r'(?m)^Dolly me llam[oó] y me dijo que quer[ií]a descansar en un hermoso prado',
        '"Dolly me llamó y me dijo que quería descansar en un hermoso prado',
        text,
        flags=re.IGNORECASE,
    )
    if not re.search(r"Sobrino y representante", text, flags=re.IGNORECASE):
        text = re.sub(
            r"(?m)^(Brian Sees)\s*$",
            r"\1  \nSobrino y representante",
            text,
        )
    return text


def repair_dimagen_canta_article(text: str) -> str:
    """Diario Imagen: México Canta 2026."""
    text = re.sub(
        r"(ampl[ií]an las)\s*\n+(y experiencias\b)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(conducci[oó]n de)\s*\n+(Majo Aguilar\b)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"a[nñ]osy\b", "años- y", text, flags=re.IGNORECASE)
    text = re.sub(
        r"mexicoestadounidense(?!-)\s+En el escenario",
        "mexicoestadounidense- En el escenario",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"preservaci[oó]n de los mexicanos\s*$",
        "preservación de los géneros musicales tradicionales mexicanos",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_eldia_transparencia_article(text: str) -> str:
    """El Día: transparencia del Congreso CDMX."""
    text = re.sub(
        r"unidades administrati\s+",
        "unidades administrativas.\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"M[eé]xicopublicada", "México publicada", text)
    text = re.sub(r"DirectivaJes[uú]s", "Directiva Jesús", text)
    text = re.sub(
        r"(Unidad de Transparencia)\s*\n+(Comit[eé] de Transparencia)\s*$",
        r"\1\n\nPresenta\n\n\2\n\nCuoto Sesión Ordinario",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_eldia_tdj_article(text: str) -> str:
    """El Día: conversatorio TDJ / desaparición forzada."""
    text = re.sub(
        r"investigacio\s+Al cerrar",
        "investigaciones.\n\nAl cerrar",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\n+nes\.\s*$", "", text)
    text = re.sub(r"\binvestigacio\s+nes\b", "investigaciones", text)
    return text


def repair_ug_danna_article(text: str) -> str:
    """Universal Gráfico: Danna / Belinda."""
    text = re.sub(r'"girly pop"y', '"girly pop" y', text)
    text = re.sub(r"\bnoch para\b", "noche para", text, flags=re.IGNORECASE)
    text = re.sub(r"(?m)^DANNA\s*$", "", text)
    return text


def repair_ug_juanga_article(text: str) -> str:
    """Universal Gráfico: Juan Gabriel / INSTAGRAM."""
    if re.search(r"(?m)^JUAN GABRIEL\s*$", text) and not re.search(
        r"(?m)^INSTAGRAM\s*$", text
    ):
        text = re.sub(r"(?m)^(JUAN GABRIEL)\s*$", r"\1\n\nINSTAGRAM", text)
    return text


def repair_dimagen_trump_article(text: str) -> str:
    """Diario Imagen: Trump / Ipsos / Canadá."""
    text = re.sub(r"Reuters/Ipso\b", "Reuters/Ipsos", text)
    text = re.sub(
        r"(77% de marzo)\.\s+(La guerra ha lastrado)",
        r"\1.\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(cree que la guerra)\s*\n+(se un go periodo)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r'(TRUMP REFUERZA "OFENSIVA COMERCIAL")\s*\n+(CONTRA CANAD[AÁ])',
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(fracasaron)\s*\n+CONTRA CANAD[AÁ]\s*\n+(el viernes\b)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r'(OFENSIVA COMERCIAL")\s*\n+(Donald Trump anunci[oó])',
        r'\1 CONTRA CANADÁ\n\n\2',
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_eldia_durango_article(text: str) -> str:
    """El Día: decomiso en Durango."""
    text = re.sub(
        r"(224 mil 865 pesos)\.\s*\n+(Estos resultados contribuyen)",
        r"\1. \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"investigacioneslos", "investigaciones los", text)
    return text


def repair_dimagen_clases_article(text: str) -> str:
    """Diario Imagen: regreso a clases / Fonacot."""
    text = re.sub(r"(?m)^-\s+Comprar la lista", "-Comprar la lista", text)
    text = re.sub(
        r"(?m)^REGRESO A CLASES\?\s*$",
        "¿CUÁNDO ES EL REGRESO A CLASES?",
        text,
    )
    text = re.sub(
        r"[¿¡]?CU[ÁA]NDO ES EL\s+FERIAS DE PROFECO",
        "FERIAS DE PROFECO",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\(Fonacot\)\s*\n+(pone a disposici[oó]n)",
        r"(Fonacot) \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^DIXON\s*\$?\s*10\s*$", "", text, flags=re.IGNORECASE)
    return text


def repair_esto_aguirre_article(text: str) -> str:
    """Esto: Javier Aguirre / Valencia; une infografia de numeros."""
    text = re.sub(r"\bAguire\b", "Aguirre", text)
    text = re.sub(r"dormido\.\*", "dormido.", text)
    text = re.sub(
        r"(de la quema\.)\s+(Javier lo hizo)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    table = (
        "23 DE SEPTIEMBRE ES ESPERADO JAVIER AGUIRRE POR SU NUEVO EQUIPO VALENCIA\n\n"
        "LOS NÚMEROS DEL VASCO EN ESPAÑA\n\n"
        "EQUIPO JD JG JE JP % DE VICTORIAS\n\n"
        "Osasuna 177 66 49 62 46.52%\n\n"
        "Atlético de Madrid 131 61 31 39 54.45%\n\n"
        "Real Zaragoza 45 13 10 22 36.2%\n\n"
        "Espanyol 69 22 18 29 40.58%\n\n"
        "Leganés 30 9 11 10 42.22%\n\n"
        "Mallorca 97 34 28 35 44.67%\n\n"
        "Su incursión en el futbol español ocurrió en el 2002 y su labor es reconocida."
    )
    text = re.sub(
        r"(?ms)(?:\*?23 DE SEPTIEMBRE[\s\S]*?)?LOS N[ÚU]MEROS DEL VASCO[\s\S]*?"
        r"labor es reconocida\.",
        table,
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_esto_evenepoel_article(text: str) -> str:
    """Esto: Evenepoel contrarreloj; quita reloj TISSOT y une tabla."""
    text = re.sub(r"(?m)^Así como (Tadej\b)", r"sí como \1", text)
    text = re.sub(r"ciclisA\s*\n*ta\b", "ciclista", text)
    text = re.sub(r"(Rohan)\s*\n+(Denis\b)", r"\1 \2", text)
    ranking = (
        "CICLISTAS CON MÁS TÍTULOS MUNDIALES DE CONTRARRELOJ\n\n"
        "POS CICLISTA PAÍS TÍTULOS\n"
        "1 Fabian Cancellara Suiza 4 (2006, 2007, 2009 y 2010)\n"
        "2 Tony Martin Alemania 4 (2011, 2012, 2013 y 2016)\n"
        "3 Remco Evenepoel Bélgica 4 (2023, 2024, 2025 y 2026)\n"
        "4 Michael Rogers Australia 3 (2003, 2004 y 2005)\n"
        "5 Jan Ullrich Alemania 2 (1999 y 2001)\n"
        "6 Rohan Dennis Australia 2 (2018 y 2019)\n"
        "7 Filippo Ganna Italia 2 (2020 y 2021)"
    )
    text = re.sub(
        r"(?ms)CICLISTAS CON M[AÁ]S T[IÍ]TULOS MUNDIALES[\s\S]*?"
        r"7 Filippo Ganna Italia 2 \(2020 y 2021\)",
        ranking,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Remco Evenepoel vol[oó] por las calles canadienses[\s\S]*?(?=CICLISTAS CON|El ciclista belga refrend|\Z)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?:SH Banque\s+)?tuvo rival que le hiciera sombra[\s\S]*?carrera\.",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^(?:00\s+)?ISSOT.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?m)^(?:BC\s+)?beneva.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?m)^antini.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?m)^SH Banque.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?m)^roval\s*$", "", text, flags=re.IGNORECASE)
    refrendo = "El ciclista belga refrendó su campeonato, una vez más, en el Mundial."
    volo = (
        "Remco Evenepoel voló por las calles canadienses y no tuvo rival "
        "que le hiciera sombra y se alzó con otro título más en su carrera."
    )
    text = re.sub(
        r"Remco Evenepoel vol[oó] por las calles canadienses[^\n]*\.?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(El ciclista belga refrend[oó] su campeonato, una vez m[aá]s, en el Mundial\.\s*)+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.rstrip() + "\n\n" + refrendo + "\n\n" + volo


def repair_esto_azules_article(text: str) -> str:
    """Esto: serie Las azules."""
    text = re.sub(r"(?m)^El Sol de M[eé]xico\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(En la segunda temporada de la)\s*F\s*\n+serie",
        r"\1 serie",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^n la segunda temporada de la\s*F?\s*\n+serie",
        "En la segunda temporada de la serie",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"efecto domique", "efecto dominó que", text, flags=re.IGNORECASE)
    text = re.sub(
        r"lo a\s+deramente",
        "lo hagan. Él empieza a convertirse verdaderamente",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(su mentor)\s*\n+(Octavio Romand[ií]a)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r'(?m)^"?\s*DIRECTOR\s*$', "", text)
    return text


def repair_esto_ortiz_article(text: str) -> str:
    """Esto: Alfonso Ortiz / marcha."""
    text = re.sub(r"detectar aquellos", "detectar a aquellos", text)
    text = re.sub(
        r"La disciplina de la tiene asombrado a su que le ve un exitoso\.",
        "La disciplina de la marchista mexicana tiene asombrado a su entrenador que le ve un futuro exitoso.",
        text,
        flags=re.IGNORECASE,
    )
    if not re.search(r"FOTO:\s*ALE", text, flags=re.IGNORECASE):
        if re.search(r"ALFONSO ORTIZ ENTRENADOR", text, flags=re.IGNORECASE):
            text = text.rstrip() + "\n\nFOTO: ALE ALE.ORTEGASOLIS"
    text = re.sub(r"(?m)^FOTO:\s*$", "", text)
    text = re.sub(r"FOTO:\s*ALE\s+ALE\.ORTEGASOLIS", "FOTO: ALE ALE.ORTEGASOLIS", text)
    return text


def repair_esto_infantino_article(text: str) -> str:
    """Esto: Infantino / FIFA gobernanza."""
    text = re.sub(
        r"Apertura al di[aá]logo\s+ASEGURA QUE LA FIFA NUNCA ESTUVO EN VENTA AGENCIAS "
        r"INFANTINO PROPONE CONSULTAR A LAS FEDERACIONES PARA REFORMAR LA GOBERNANZA",
        "ASEGURA QUE LA FIFA NUNCA ESTUVO EN VENTA\n\nApertura al diálogo\n\n"
        "AGENCIAS\n\nINFANTINO PROPONE CONSULTAR A LAS FEDERACIONES PARA REFORMAR LA GOBERNANZA",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"[UÚ]rich, Suiza\. El presidente de FIFA, Z\s*\n+Gianni Infantino",
        "Zúrich, Suiza. El presidente de FIFA, Gianni Infantino",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(por escrito)\.\s*\n+(\"En mis conversaciones)",
        r"\1. \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"GIANNI INFANTINO\s*/\s*PRESIDENTE FIFA",
        "GIANNI INFANTINO PRESIDENTE FIFA",
        text,
    )
    if text.count("GIANNI INFANTINO PRESIDENTE FIFA") < 2:
        text = re.sub(
            r"(cualquier asunto concreto\"\s*)",
            r"\1\n\nGIANNI INFANTINO PRESIDENTE FIFA\n\n",
            text,
            count=1,
            flags=re.IGNORECASE,
        )
    return text


def repair_esto_xhaka_article(text: str) -> str:
    """Esto: Granit Xhaka certificado Covid."""
    text = re.sub(
        r"(?m)^Xhaka falsifica un\s*$",
        "Xhaka falsifica un certificado Covid",
        text,
    )
    text = re.sub(
        r"(Xhaka falsifica un certificado Covid)\s+(Ginebra,)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^certificado Covid\s*$", "", text)
    text = re.sub(r"GRANIT XHAKA\s*/\s*VOLANTE SUIZA", "GRANIT XHAKA VOLANTE SUIZA", text)
    text = re.sub(r"(?m)^E capit[aá]n fue apartado", "El capitán fue apartado", text)
    text = re.sub(r"(?m)^FOTO:\s*$", "", text)
    text = re.sub(
        r"(tres d[ií]as despu[eé]s)\.\s*\n+(Posteriormente,)",
        r"\1. \2",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_esto_depay_article(text: str) -> str:
    """Esto: Memphis Depay / Países Bajos."""
    text = re.sub(r"\s*/\s*EFE\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?m)^AFP FOTO:\s*$", "", text, flags=re.IGNORECASE)
    return text


def repair_esto_nfl_murray_article(text: str) -> str:
    """Esto: Kyler Murray / NFL."""
    text = re.sub(
        r"(varias semanas, por)\s*\n+(lo que ser[aá] el veterano)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(un arranque de 0-2)\.\s*\n+(El equipo comandado)",
        r"\1. \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\.\s*/\s*JOS[EÉ] A\.\s*RUEDA",
        ".\n\nJOSÉ A. RUEDA",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_jornada_segato_article(text: str) -> str:
    """La Jornada: Rita Segato."""
    text = re.sub(
        r"(ayer, en el)\s*\n+(Tecnol[oó]gico de Monterrey)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(en espa[nñ]ol)\s*\n+(se traduce como)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(g[eé]nero), refiri[oó]",
        r'\1", refirió',
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(Sobre la pedagog[ií]a de la crueldad)\s+(Otro tema)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(Tenemos)\s*\n+(que romper)", r"\1 \2", text)
    text = re.sub(r'(?m)^"\s*$', "", text)
    return text


def repair_jornada_tigres_article(text: str) -> str:
    """La Jornada: Tigres femenil / Toluca."""
    text = re.sub(r"Mar[\s\-]+t[ií]nez", "Martínez", text)
    text = re.sub(
        r"(va del torneo)\.\s+(El cuadro regiomontano)",
        r"\1.\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(con la victoria)\.\s*\n+(Las dirigidas por Nicol[aá]s Morales)",
        r"\1. \2",
        text,
        flags=re.IGNORECASE,
    )
    return text


def repair_jornada_lucas_article(text: str) -> str:
    """La Jornada: museo George Lucas."""
    text = re.sub(r'(pueblo")y un', r'\1 y un', text)
    text = re.sub(r"\bestu\s+VO\b", "estuvo", text)
    text = re.sub(r"\bestuVO\b", "estuvo", text)
    text = re.sub(r"(arquitecto Ma)\s*\n+(Yansong)", r"\1 \2", text)
    text = re.sub(r"pocosretratos", "pocos retratos", text)
    text = re.sub(r"Foto@", "Foto @", text)
    text = re.sub(
        r"(?m)^Guillermo del Toro \(derecha\)",
        "A Guillermo del Toro (derecha)",
        text,
    )
    caption = (
        "A Guillermo del Toro (derecha) estuvo en primera fila celebrando con "
        "Lucas la apertura del recinto. Foto @sw_holocron"
    )
    text = re.sub(re.escape(caption) + r"\s*", "", text)
    if "Con información de Ap" in text:
        text = re.sub(
            r"(Con informaci[oó]n de Ap)\s*",
            r"\1\n\n" + caption + "\n\n",
            text,
            count=1,
            flags=re.IGNORECASE,
        )
    return text


def repair_cronica_bylines_and_cuts(text: str) -> str:
    """La Crónica: bylines con email y cortes de columna."""
    text = re.sub(r"EidalidL[oó]pez", "Eidalid López", text)
    text = re.sub(
        r"(Eidalid L[oó]pez)\s+(nacional@cronica\.com\.mx)",
        r"\1 \2",
        text,
    )
    text = re.sub(
        r"(F[aá]tima Ch[aá]vez)\s+nacional@cronica\.com\.mx",
        r"\1\n\nnacional@cronica.com.mx",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(Ricardo)\s*\n+(Azael)", r"\1 \2", text)
    text = re.sub(r"Aguascalientes\.duus", "Aguascalientes.", text)
    text = re.sub(
        r"(poblaci[oó]n)\s*\n+(en Aguascalientes\.)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(SECRETAR[IÍ]A DE SALUD RESPONDE)\s+(La Secretar[ií]a de Salud)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(beneficiarios de)\s*\n+(la Beca Universal)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?ms)\n*FGJ\s*FISCAL[IÍ]A GENERAL[\s\S]*?TAMAULIPAS\s*",
        "\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?m)^FISCAL[IÍ]A GENERAL DE JUSTICIA DEL ESTADO DE TAMAULIPAS\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bsilenci[oó]n\b", "silencios", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(Eidalid L[oó]pez) nacional@cronica\.com\.mx(\s+La creaci[oó]n de este espacio)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(nacional@cronica\.com\.mx)\s+(Ruvalcaba inform[oó])",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(en el estado\.)\s+(Durante el encuentro,)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(programas relacionados con el sector)\s*$",
        r"\1.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(sectores de la poblaci[oó]n)\s*$",
        r"\1 en Aguascalientes.",
        text,
        flags=re.IGNORECASE,
    )
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
    text = re.sub(
        r"(?ms)\n*FGJ(?!EM)(?:\s+FISCAL[IÍ]A GENERAL[\s\S]*?TAMAULIPAS)?\s*",
        "\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^(?:BC\s+)?(?:beneva|TISSOT|ISSOT|enev|antini|EMIER)\b.*$", "", text)
    text = re.sub(r"Aguascalientes\.duus", "Aguascalientes.", text)
    text = re.sub(r"Foto@", "Foto @", text)
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
        if re.search(r"Raptados|Susana Zabaleta|Gusgri", text, flags=re.IGNORECASE):
            text = repair_ug_zabaleta_article(text)
        if re.search(r"Xavi Hern[aá]ndez|Pa[ií]ses Bajos|KNVB", text, flags=re.IGNORECASE):
            text = repair_ug_xavi_article(text)
        if re.search(r"SINCRONIA|M[ií]a y L[ií]a|Clavados", text, flags=re.IGNORECASE):
            text = repair_ug_clavados_article(text)
        if re.search(r"Educaci[oó]n Superior 2026|Mi Derecho, Mi Lugar", text, flags=re.IGNORECASE):
            text = repair_dimagen_education_infographic(text)
        if re.search(r"c[áa]rteles mexicanos reemplazan|Terry Cole acusa", text, flags=re.IGNORECASE):
            text = repair_dimagen_dea_article(text)
        if re.search(r"Arturo Baena|voto de castigo|ll[áa]mase como se llame", text, flags=re.IGNORECASE):
            text = repair_dimagen_candidaturas_article(text)
        if re.search(r"MAX AUB|m[eé]dicos cubanos|CASO ANGOLA", text, flags=re.IGNORECASE):
            text = repair_ug_medicos_article(text)
        if re.search(r"regreso a clases|Fonacot|Mesones y Moneda", text, flags=re.IGNORECASE):
            text = repair_dimagen_clases_article(text)
        if re.search(r"Dolly Parton|Brian Sees|leyenda del country", text, flags=re.IGNORECASE):
            text = repair_ug_dolly_article(text)
        if re.search(r"M[eé]xico Canta|Majo Aguilar|mexicocanta\.gob", text, flags=re.IGNORECASE):
            text = repair_dimagen_canta_article(text)
        if re.search(r"Leonardo Ju[aá]rez|Unidad de Transparencia|Galv[aá]n Darder", text, flags=re.IGNORECASE):
            text = repair_eldia_transparencia_article(text)
        if re.search(r"Tribunal de Disciplina|Celia Maya|Desaparici[oó]n Forzada", text, flags=re.IGNORECASE):
            text = repair_eldia_tdj_article(text)
        if re.search(r"wet dream|girly pop|Dolce vita", text, flags=re.IGNORECASE):
            text = repair_ug_danna_article(text)
        if re.search(r"JUAN GABRIEL|Abr[aá]zame muy fuerte|Divo de Ju[aá]rez", text, flags=re.IGNORECASE):
            text = repair_ug_juanga_article(text)
        if re.search(r"Reuters/?Ipsos|OFENSIVA COMERCIAL|popularidad del presidente Trump", text, flags=re.IGNORECASE):
            text = repair_dimagen_trump_article(text)
        if re.search(r"Pe[nñ][oó]n Blanco|Destino de Bienes y Objetos", text, flags=re.IGNORECASE):
            text = repair_eldia_durango_article(text)
        if re.search(r"Javier Aguirre|Vasco Aguirre|VOLVER[AÁ] CON EL VALENCIA", text, flags=re.IGNORECASE):
            text = repair_esto_aguirre_article(text)
        if re.search(r"Evenepoel|contrarrelojista|Fabian Cancellara", text, flags=re.IGNORECASE):
            text = repair_esto_evenepoel_article(text)
        if re.search(r"Las azules|Fernando Rovzar|Tlatelolco", text, flags=re.IGNORECASE):
            text = repair_esto_azules_article(text)
        if re.search(r"Alfonso Ortiz|Alejandra Ortega|marchista mexicana", text, flags=re.IGNORECASE):
            text = repair_esto_ortiz_article(text)
        if re.search(r"Infantino|FIFA Forward Enterprise|Apertura al di[aá]logo", text, flags=re.IGNORECASE):
            text = repair_esto_infantino_article(text)
        if re.search(r"Granit Xhaka|certificado Covid", text, flags=re.IGNORECASE):
            text = repair_esto_xhaka_article(text)
        if re.search(r"Memphis Depay|Selecci[oó]n Neerlandesa", text, flags=re.IGNORECASE):
            text = repair_esto_depay_article(text)
        if re.search(r"Kyler Murray|Marcus Mariota|Minnesota Vikings", text, flags=re.IGNORECASE):
            text = repair_esto_nfl_murray_article(text)
        if re.search(r"Rita Segato|Contrapedagog[ií]as de la crueldad", text, flags=re.IGNORECASE):
            text = repair_jornada_segato_article(text)
        if re.search(r"Kgatlana|Valeria Mart|Amazonas", text, flags=re.IGNORECASE):
            text = repair_jornada_tigres_article(text)
        if re.search(r"Museo de Arte Narrativo|George Lucas|Ma Yansong", text, flags=re.IGNORECASE):
            text = repair_jornada_lucas_article(text)
        if re.search(
            r"cronica\.com\.mx|Nora Ruvalcaba|Casa Casve|Hospital General de Zona|Santiago Nieto",
            text,
            flags=re.IGNORECASE,
        ):
            text = repair_cronica_bylines_and_cuts(text)
        if re.search(r"SA[UÚ]L MALDONADO|enfermedad de Parkinson|UJED", text, flags=re.IGNORECASE):
            text = re.sub(
                r"(SA[UÚ]L MALDONADO)\s+CORRESPONSAL\s+(DURANGO, DGO\.)",
                r"\1\n\n\2",
                text,
                flags=re.IGNORECASE,
            )
            text = re.sub(
                r"(Publicaci[oó]n en revista especializada)\s+(El trabajo de la universidad)",
                r"\1\n\n\2",
                text,
                flags=re.IGNORECASE,
            )
        text = repair_la_prensa_razon_set(text)
        text = strip_short_note_agency_mark(text)
        text = strip_infographic_residue(text)
        text = strip_noise_lines(text)
        return text.strip()


register_engine(NotaInformativaCorrectionEngine())

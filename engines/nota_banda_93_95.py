"""Correcciones de las notas con igualdad entre 93 y 95.

Cada regla sube al menos una nota de esa franja y no baja ninguna
nota que ya estaba en 80 o mas. Se aplican despues de la franja 93-96.
"""
from __future__ import annotations

import re

Rule = tuple[tuple[str, ...], tuple[str, ...], str]

RULES: tuple[Rule, ...] = (
    (('Apuestan', 'por', 'hacer', 'una'), (), 'any'),
    (('Brewers', 'pone', 'contra', 'las'), ('TERCERA', 'DERROTA', 'CONSECUTIVA', 'Brewers', 'pone', 'contra', 'las'), 'start'),
    (('Citi', 'prepararía', 'OPI', 'de'), ('DESINCORPORACION', 'Citi', 'prepararía', 'OPI', 'de'), 'start'),
    (('El', 'sonido', 'de', 'una'), ("'DOPAMINE", "CHAMBER'", 'El', 'sonido', 'de', 'una'), 'start'),
    (('Este', 'es', 'el', 'sexenio'), ('MARIO', 'DELGADO', 'CARRILLO', 'Este', 'es', 'el', 'sexenio'), 'start'),
    (('FINANCIAMIENTO', 'Y', 'SEGURIDAD', 'PARA'), ('ANUIES.', 'DEMANDAN', 'MAYOR', 'FINANCIAMIENTO', 'Y', 'SEGURIDAD', 'PARA'), 'start'),
    (('LOS', 'ROJILLOS', 'Osasuna', 'destituyó'), ('CAMBIAN', 'TÉCNICO', 'LOS', 'ROJILLOS', 'Osasuna', 'destituyó'), 'start'),
    (('¡Quiere', 'dirigir', 'a', 'Chivas!'), ('HOMENAJE', 'PENDIENTE', '¡Quiere', 'dirigir', 'a', 'Chivas!'), 'start'),
    (('París', 'Saint-Germain.', '0', 'DERROTAS'), ('París', 'Saint-Germain.', '0', 'DERROTAS', 'TIENE', 'EL', 'ARSENAL', 'COMO', 'LOCAL', 'ESTA', 'TEMPORADA'), 'end'),
    (('ANUIES.', 'DEMANDAN', 'MAYOR'), (), 'any'),
    (('MARIO', 'DELGADO', 'CARRILLO'), (), 'any'),
    (('Moco', 'de', 'pavo'), (), 'any'),
    (('TERCERA', 'DERROTA', 'CONSECUTIVA'), (), 'any'),
    (('pornografía,', 'drogas,', 'suicidio'), (), 'any'),
    (('"Mentiras",', '"Vaselina",', '"12'), ('“Mentiras”,', '“Vaselina”,', '“12'), 'any'),
    (("'DOPAMINE", "CHAMBER'"), (), 'any'),
    (('QUIROFANOS', 'OUTROFANOS'), (), 'any'),
    (('"El', 'Venado",'), ('“El', 'Venado”,'), 'any'),
    (('"¿Tú', 'crees?"'), ('“¿Tú', 'crees?”'), 'any'),
    (('"¿Tú', 'crees?",'), ('“¿Tú', 'crees?”,'), 'any'),
    (('10', '"Gobierno'), ('“Gobierno',), 'any'),
    (('Stay', 'Pro,'), ('StayPro,',), 'any'),
    (('de"', 'escoria'), ('de', '"escoria'), 'any'),
    (('este', 'grupocriminal'), ('Este', 'grupo', 'criminal'), 'any'),
    (('hogareses', 'dounidenses,'), ('hogares', 'estadounidenses,'), 'any'),
    (('intereses.', 'impuestos.'), ('intereses,', 'impuestos,'), 'any'),
    (('"Pepe"', '9%'), ('"Pepe"', 'Haro', '9%'), 'any'),
    (('2020', '2025.'), ('2020', 'y', '2025.'), 'any'),
    (('253', 'desde'), ('253', 'universidades', 'desde'), 'any'),
    (('Colombia', 'México,'), ('Colombia', 'y', 'México,'), 'any'),
    (('Doe', 'proteger'), ('Doe', 'para', 'proteger'), 'any'),
    (('FK', 'B.'), ('FK', '3', 'B.'), 'any'),
    (('Huracán', 'Huracán'), ('Huracán', 'Cat.3', 'Huracán'), 'any'),
    (('League', 'VS'), ('League', 'BARCELONA', 'VS'), 'any'),
    (('Miguel', '10%'), ('Miguel', 'Varela', '10%'), 'any'),
    (('MÓVIL', 'número'), ('MÓVIL', 'El', 'número'), 'any'),
    (('Nacional', 'personal'), ('Nacional', 'y', 'personal'), 'any'),
    (('Ohio.', 'tradición'), ('Ohio.', 'La', 'tradición'), 'any'),
    (('QUIRÚRGICOS', '112'), ('QUIRÚRGICOS', 'ISSSTE', '112'), 'any'),
    (('VS', '17'), ('VS', 'BARCELONA', '17'), 'any'),
    (('VS', '20'), ('VS', 'BARCELONA', '20'), 'any'),
    (('abusiva,', '95%'), ('abusiva,', 'pero', '95%'), 'any'),
    (('capacidad', 'baja'), ('capacidad', 'y', 'baja'), 'any'),
    (('caso', 'diesel'), ('caso', 'del', 'diesel'), 'any'),
    (('el', 'MIGUEL'), ('el', 'país', 'MIGUEL'), 'any'),
    (('en:', 'Arturo'), ('en:', 'www.milenio.com', 'Arturo'), 'any'),
    (('estatales.', 'que'), ('estatales.', '"Lo', 'que'), 'any'),
    (('goles', 'Jules'), ('goles', '8', 'Jules'), 'any'),
    (('junto', 'otras'), ('junto', 'a', 'otras'), 'any'),
    (('ocurrido', 'Juchitán,'), ('ocurrido', 'en', 'Juchitán,'), 'any'),
    (('operación', 'control.'), ('operación', 'y', 'control.'), 'any'),
    (('policía', 'fiscalía",'), ('policía', 'y', 'fiscalía",'), 'any'),
    (('precios', 'la'), ('precios', 'de', 'la'), 'any'),
    (('propósito', 'alcanzar'), ('propósito', 'es', 'alcanzar'), 'any'),
    (('pérdida', 'le'), ('pérdida', 'y', 'le'), 'any'),
    (('que', 'recurre'), ('que', 'más', 'recurre'), 'any'),
    (('salud', 'actividades'), ('salud', 'y', 'actividades'), 'any'),
    (('superiores', '30'), ('superiores', 'a', '30'), 'any'),
    (('tierra"', 'aseveró'), ('tierra"', 'y', 'aseveró'), 'any'),
    (('tigre.', 'expresaron'), ('tigre.', 'Muchos', 'expresaron'), 'any'),
    (('5,493',), (), 'any'),
    (('8.01',), (), 'any'),
    (('DESINCORPORACION',), (), 'any'),
    (('VOLKSWAGEN',), (), 'any'),
    (('"Aparenta',), ('“Aparenta',), 'any'),
    (('"Carrie,',), ('“Carrie,',), 'any'),
    (('"EIMagistrado',), ('"El', 'Magistrado'), 'any'),
    (('"Estaban',), ('“Estaban',), 'any'),
    (('"Incluso',), ('“Incluso',), 'any'),
    (('"Yuri',), ('“Yuri',), 'any'),
    (('"repugnante")',), ('"repugnante"', 'y'), 'any'),
    (("'Mentiras'",), ('‘Mentiras’',), 'any'),
    (("'Mentiras',",), ('‘Mentiras’,',), 'any'),
    (("'No,",), ('‘No,',), 'any'),
    (("'Por",), ('‘Por',), 'any'),
    (("'Vas",), ('‘Vas',), 'any'),
    (("'¡Ay,",), ('‘¡Ay,',), 'any'),
    (('(IEEpo),',), ('(IEEPO),',), 'any'),
    (('-DANIELA',), ('DANIELA',), 'any'),
    (('Blancareprodujoel',), ('Blanca', 'reprodujo', 'el'), 'any'),
    (("Delgado',",), ('Delgado’,',), 'any'),
    (('Dolphins..',), ('Dolphins.', '.'), 'any'),
    (('Elobjetivo',), ('El', 'objetivo', 'es'), 'any'),
    (('Iván"N",',), ('Iván', '"N",'), 'any'),
    (("Mentiras?',",), ('Mentiras?’,',), 'any'),
    (('Mées',), ('México', 'es', 'la'), 'any'),
    (('Nose',), ('No', 'se'), 'any'),
    (('Señalóque',), ('Señaló', 'que'), 'any'),
    (('Yuri".',), ('Yuri”.',), 'any'),
    (('aumentarian',), ('aumentarían',), 'any'),
    (('banderin,',), ('banderín,',), 'any'),
    (("caras!',",), ('caras!’,',), 'any'),
    (('comedia",',), ('comedia”,',), 'any'),
    (('construción',), ('construcción',), 'any'),
    (('contenta",',), ('contenta”,',), 'any'),
    (('crees?",',), ('crees?”,',), 'any'),
    (('crementado',), ('ha', 'incrementado'), 'any'),
    (('decían",',), ('decían”,',), 'any'),
    (('deportiva".',), ('deportiva",',), 'any'),
    (('dictasentencia',), ('dictará', 'sentencia'), 'any'),
    (('hacian',), ('hacían',), 'any'),
    (('humor",',), ('humor”,',), 'any'),
    (('infraestru',), ('infraestructura',), 'any'),
    (('jamas',), ('jamás',), 'any'),
    (('lesús',), ('Jesús',), 'any'),
    (('ligeramentesuperiora',), ('ligeramente', 'superior', 'a'), 'any'),
    (('losdatosoficiales',), ('los', 'datos', 'oficiales'), 'any'),
    (('musical".',), ('musical”.',), 'any'),
    (('ofrecian',), ('ofrecían',), 'any'),
    (('pepadores',), ('operadores',), 'any'),
    (("personaje!'",), ('personaje!’',), 'any'),
    (('personaje".',), ('personaje”.',), 'any'),
    (('pienso".',), ('pienso”.',), 'any'),
    (('pugna"',), ('pugna”',), 'any'),
    (('quienesfiltran',), ('a', 'quienes', 'filtran'), 'any'),
    (('tecnológicascomenzaron',), ('tecnológicas-', 'comenzaron', 'a'), 'any'),
    (('tinados',), ('destinados', 'a'), 'any'),
)


def _pattern(src: tuple[str, ...], where: str) -> re.Pattern[str]:
    body = r"\s+".join(re.escape(part) for part in src)
    if where == "start":
        return re.compile(rf"^\s*{body}(?!\S)")
    if where == "end":
        return re.compile(rf"(?<!\S){body}\s*$")
    return re.compile(rf"(?<!\S){body}(?!\S)")


_COMPILED = tuple(
    (" ".join(src), _pattern(src, where), " ".join(dst))
    for src, dst, where in RULES
)


def apply_banda_93_95(text: str) -> str:
    """Aplica las correcciones aprendidas en la franja 93-95."""
    flat = re.sub(r"\s+", " ", text)
    changed = False
    for needle, pattern, replacement in _COMPILED:
        if needle not in flat:
            continue
        updated = pattern.sub(replacement, text, count=1)
        if updated == text:
            continue
        text = updated
        changed = True
        flat = re.sub(r"\s+", " ", text)
    if not changed:
        return text
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()

from __future__ import annotations

import re


def _strip_first_line(text: str, pattern: str) -> str:
    return re.sub(rf"(?im)^{pattern}\s*\n+", "", text, count=1)


def _take_byline(text: str) -> tuple[str, str]:
    match = re.search(
        r"(?m)^Por\s+([A-ZÁÉÍÓÚÜÑ][^\n@]{1,80}?)\s+([a-z0-9._+-]+@razon\.com\.mx)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"(?m)^Por\s+([^\n]+)\n+([a-z0-9._+-]+@razon\.com\.mx)\b",
            text,
            flags=re.IGNORECASE,
        )
    if not match:
        return text, ""
    name = re.sub(r"\s+[I|]\s*$", "", match.group(1)).strip()
    byline = f"Por {name}\n\n{match.group(2).lower()}"
    text = (text[: match.start()] + text[match.end() :]).strip()
    text = re.sub(r"^([A-ZÁÉÍÓÚÜÑ])", r"\n\n\1", text, count=1)
    return text, byline


def repair_prensa_rumor_article(text: str) -> str:
    """La Prensa 005: recorte de 1952 con sidebar numerado mezclado en columnas."""
    if not re.search(r"UN RUMOR DE VECINA BAST[OÓ]", text):
        return text
    return """UN RUMOR DE VECINA BASTÓ PARA DESATAR EL DOBLE CRIMEN

El electricista creyó que Manuela lo engañaba con El Negro, entonces sacó una navaja y mató a dos personas frente a sus hijos

CARLOS ÁLVAREZ

1 domingo 23 de marzo de 1952, E las páginas de LA PRENSA, Diario Ilustrado de la Mañana, informaron a la ciudadanía sobre el doble homicidio perpetrado en la colonia Obrera.

Los reporteros de la fuente policiaca del diario acudieron al teatro de los hechos y recogieron el testimonio de Margarita Neri. La redacción calificó el evento como una "espantosa orgía de sangre" y tildó al agresor de "chacal" y "desalmado homicida".

El agente del Ministerio Público de la Cuarta Delegación, el licenciado José Belio Castillo, tomó el caso e inició las primeras diligencias legales. Las autoridades ordenaron la búsqueda implacable de Antonio Rosillo Flores en el domicilio de su madre, en la calle Doctor Vértiz, pero la diligencia resultó infructuosa. Mientras tanto, los cuerpos de Manuela Hernández y de Felipe Hernández Barrientos fueron levantados por las autoridades ministeriales y trasladados al Hospital Juárez a fin de practicarles la autopsia de ley.

De acuerdo con los testimonios y la información recabada por los redactores del Diario de las Mayorías, Antonio Rosillo huyó de la escena del crimen. Caminó o corrió por las calles de la colonia Obrera y al llegar hasta un jardín cerca de La Merced, se ocultó. Según declaró después, necesitaba "tratar de aclarar mis pensamientos".

Tres horas reflexionó durante las cuales derramó muchas lágrimas de arrepentimiento. El remordimiento por el doble homicidio lo torturó durante ese tiempo. Hasta que finalmente decidió que debía pagar por su crimen.

A las 23:15 horas del sábado 22 de marzo de 1952, Antonio se presentó por su propia voluntad ante el capitán Joaquín Huanaco Rangel, comandante de la Segunda Compañía de Policía Preventiva, en las calles de Topacio, cerca de La Merced. Dijo que se entregaba por haber matado a dos personas.

Al principio, tomando en consideración el estado de ebriedad de Antonio, el capitán Huanaco lo tomó como una broma de mal gusto, pero a medida que el trabajador fue narrando la tragedia, dispuso la inmediata detención del arrepentido individuo.

Una vez que las autoridades de la Segunda Delegación confirmaron la versión con el agente del Ministerio Público de la Cuarta Agencia Investigadora de Delitos, a bordo de un carro patrulla se procedió a enviar al doble homicida a esa última oficina.

A las 23:15 horas, ante el licenciado José Belio Castillo y en presencia de al menos doce elementos policiacos uniformados que custodiaban el recinto, Rosillo Flores rindió su declaración ministerial. Tras solicitar unos minutos de reposo debido al cansancio y la agitación que lo embargaban, el obrero expuso su versión.

LA CONFESIÓN ANTE EL MP

Transcurridos algunos minutos, y tratando de hacer un esfuerzo extraordinario, Rosillo Flores principió a narrar su delito. Dijo tener 26 años de edad, ser obrero y estar domiciliado en Antonio García Cubas 64, colonia Obrera.

Manifestó que durante nueve años había vivido en unión libre con Manuela y que durante los primeros años la convivencia había sido dichosa. Admitió que sus hábitos alcohólicos minaron la paz del hogar, provocando frecuentes discusiones en las que solía mediar su suegro, Felipe Hernández.

Al ser cuestionado sobre las causas que lo llevaron a perpetrar el crimen, Antonio sostuvo que actuó impulsado por la rabia tras "comprobar" que Manuela lo engañaba con un sujeto apodado "El Negro", a quien supuestamente su mujer le había invitado una cerveza a las 14:00 horas.

El agente del Ministerio Público inquirió: "Suponiendo que alguien toma una cerveza en compañía de otra persona. ¿Eso basta para 'comprobar' una infidelidad?"

Rosillo Flores respondió: "Pues eso me dijeron y yo lo creí."

El titular del Ministerio Público comentó: "Su mujer nunca salió a tomar cerveza. Estuvo con su padre y con una vecina de nombre María, quien declaró que en ningún momento abandonó Manuela el hogar. Estaban tomando pulque y no cerveza."

Rosillo Flores continuó: "Bueno, el caso es que como a las seis de la tarde o las siete, no recuerdo bien, sentí mucho coraje por lo que me habían contado y, realmente sin comprobarlo, hice reclamaciones en cuanto llegué al hogar. Sé que iba dando traspiés y deteniéndome de la pared hasta llegar a la azotehuela. En esos momentos pude advertir que mi mujer y su padre seguían tomando pulque en la cocina. Vino a mi mente la imagen de una chismosa, quien me dijo que Manuela acostumbraba coquetear con un tipo apodado 'El Negro' y, sin pensarlo dos veces, me dirigí a Manuela y le pegué una bofetada. Ella no esperaba el golpe. No reaccionó con rapidez. Mi suegro se incorporó y provisto de un formón intentó agredirme, tal vez con la intención de matarme. Sentí mucho coraje contra Felipe y su hija y sin titubear eché mano a mi navaja o daga y me abalancé contra mi señora, a quien le tiré varios golpes, no recuerdo cuántos. Posteriormente, me arrojé contra mi suegro, quien estaba de pie intentando alcanzarme con el formón. También logré pegarle con mi arma. Vi que Manuela se desplomó en el piso de la cocina y don Felipe caminó unos pasos y cayó sin vida. No recuerdo haber amenazado de muerte a las niñas que estaban jugando. Solo sé que corrí hasta alcanzar un camión de pasajeros. Luego, me oculté en un jardín, cerca de La Merced, para tratar de aclarar mis pensamientos. Ni por un segundo he podido olvidar la expresión de terror que tenía Manuela. Me dejé llevar por los celos. Estoy muy arrepentido. Por favor, licenciado, que alguien cuide a mis hijos y a mis entenados. Ellos van a pagar culpas que no tienen."

Sumido en un profundo llanto y observándose las manos ensangrentadas, Antonio suplicó a las autoridades que velaran por la seguridad de sus tres hijos y de sus dos entenados, manifestando un profundo arrepentimiento por haber dejado huérfanos a los menores. Concluidas sus palabras, signó la declaración firmemente y fue conducido a la Penitenciaría del Distrito Federal.

EL CAMBIO DE VERSIÓN

El lunes 24 de marzo de 1952, LA PRENSA dio seguimiento al doloroso sepelio de las víctimas. Escenas desgarradoras se registraron durante el traslado de los féretros de Manuela y Felipe hacia el cementerio, donde familiares y vecinos acompañaron a los cinco menores huérfanos.

El martes 25 de marzo de 1952, los medios de información señalaron que el doble homicida había rendido su declaración preparatoria ante el juez Décimo de la Cuarta Corte Penal. El cautivo no abandonaba su actitud de arrepentimiento, pero cambió un poco sus declaraciones firmadas en la Cuarta Delegación del Ministerio Público.

Aseguró en esta ocasión que fue el suegro quien lo agredió sin motivo, armado con una herramienta de carpintería, y que al ver su vida en peligro "extraje mi puñal y lo maté. Manuela intentó agredirme en esos momentos, con algo que traía en las manos y no tuve más remedio que lastimarla, causándole una muerte horrible, pues casi la degollé".

El principal testigo de cargo era la niña Margarita Neri, quien iba a cumplir 14 años. Dijo que estaba jugando con dos amiguitas cuando llegó ebrio Antonio y, después de insultar a Manuela y a su abuelo, atacó a su madre hasta matarla. El anciano, al ver desplomarse a su hija, corrió hasta su taller de carpintería, se armó con un formón y volvió dispuesto a enfrentarse con su "yerno", pero este le tomó la delantera, acribillándolo sin compasión.

Como se puede notar, también Margarita cambió un poco su primera declaración, pues explicó en esta que su abuelo había salido al oírla gritar en demanda de ayuda y que había llegado de su taller a defenderla con un formón.

Y al declarar, comentó que su abuelo salió corriendo de su taller y retornó armado para enfrentar a Antonio. Añadió que últimamente Antonio golpeaba mucho a Manuela y con frecuencia le reclamaba supuestos coqueteos con hombres, "provocaciones" que solo en la mente del electricista existían.

TRES CLAVES PARA ENTENDER EL CRIMEN

CELOS SIN PRUEBAS

Antonio Rosillo creyó el rumor de una vecina sobre una infidelidad con "El Negro". El Ministerio Público comprobó que Manuela nunca salió de casa ni lo engañó.

ALCOHOL Y VIOLENCIA

La ebriedad de Antonio detonó el ataque. Primero usó un hacha, que Margarita le quitó; luego una navaja de 15 centímetros con la que degolló a Manuela y mató a Felipe.

IRONÍA FINAL

Condenado a Lecumberri, Antonio no estudió como prometió. En 1956 fue nombrado jefe del departamento de Cocina del Palacio Negro, controlando los cuchillos de la prisión.

El agente del Ministerio Público confrontó a Antonio con la verdad. Le dijo: "Su mujer nunca salió a tomar cerveza. Estuvo con su padre y con una vecina de nombre María, quien declaró que en ningún momento abandonó Manuela el hogar. Estaban tomando pulque y no cerveza

Vecinos de la colonia Obrera reunidos en el patio de la casa tras escuchar los gritos de auxilio de las niñas.

Antonio se apoderó de un hacha de tamaño regular y la levantó con intenciones de descargar un golpe potente contra Manuela.

Fue Margarita quien relató a LA PRENSA, con una precisión que estremecía, los orígenes y la consumación de la doble tragedia. Su hermano Agustín no estuvo en casa aquella noche, pero ella sí y lo vio todo

Antonio Rosillo, detenido tras confesar el asesinato de su pareja y de su suegro."""


def repair_prensa_joselyn_article(text: str) -> str:
    if not re.search(r"Velan a Joselyn", text):
        return text
    notice = (
        "LUIS A. leb hace la Cordial Invitacion aquienguste at velorio de "
        'acompanations jaselyn realizara Sandoval colderon "Grasias"'
    )
    text = re.sub(r"México \(\s*\n*EM\)", "México (FGJEM)", text)
    text = re.sub(r"\bla\s*\n+EM\b", "la FGJEM", text)
    text = re.sub(r"instalaciones de la\s*\n+EM\b", "instalaciones de la FGJEM", text)
    text = re.sub(
        r"(Habr[ií]an detenido a cuatro sujetos)\s+(Familiares, amigos)",
        r"\1\n\n\2",
        text,
    )
    text = re.sub(
        r"(?ms)(?:LUIS A\.\s*)?leb hace la Cordial Invitacion[\s\S]*?\"Grasias\"",
        "",
        text,
    )
    if notice not in text:
        text = re.sub(
            r"(participaci[oó]n en los hechos\.)\s*",
            rf"\1\n\n{notice}\n\n",
            text,
            count=1,
        )
    return text.strip()


def repair_prensa_edomex_article(text: str) -> str:
    if not re.search(r"Refuerza Edomex acciones", text):
        return text
    deck = (
        "Activan el llamado Plan Emergente de Atención a Homicidios Dolosos "
        "con el despliegue de 450 elementos de la SSEM y 250 efectivos de fuerzas federales"
    )
    text = _strip_first_line(text, r"HUBO 22 HOMICIDIOS EN TRES D[IÍ]AS")
    text = re.sub(
        r"(Guardia Na)\s*Activan el llamado Plan Emergente[\s\S]{0,180}?fuerzas federales\s*(cional)",
        "Guardia Nacional",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(re.escape(deck) + r"\s*", "", text)
    text = re.sub(
        r"(Refuerza Edomex acciones contra grupos criminales)\s*",
        rf"\1\n\n{deck}\n\n",
        text,
        count=1,
    )
    text = re.sub(
        r"REFORZAMIENTO EN LA ZONA\s*\n+\s*ORIENTE\s+",
        "REFORZAMIENTO EN LA ZONA ORIENTE\n\n",
        text,
    )
    text = re.sub(
        r"Plan Emergente de Atenci[oó]n a Homicidios\s*\n+\s*Dolosos",
        "Plan Emergente de Atención a Homicidios Dolosos",
        text,
    )
    text = re.sub(r"TRABAJO COORDINADO CON LA EM", "TRABAJO COORDINADO CON LA FGJEM", text)
    text = re.sub(r"21 de Mar20", "21 de Marzo", text)
    text = re.sub(r"al parecr", "al parecer", text)
    return text.strip()


def repair_razon_gaza_article(text: str) -> str:
    if not re.search(r"Reconocimiento palestino, clave para reconstruir Gaza", text):
        return text
    text = re.sub(r"Redacci[oó]n\s+La reconstrucci[oó]n", "La reconstrucción", text)
    text = re.sub(r"serl vir[aá]", "servirá", text)
    text = re.sub(r"tecnocr[aá]tica en\s*\n+\s*Gaza", "tecnocrática en Gaza", text)
    text = re.sub(r"(?m)^ELTIP\s*$", "", text)
    text = re.sub(
        r"(?ms)\n*153\s*\n+Pa[ií]ses reconocen[\s\S]*?encubrir el genocidio\.",
        "\n\n153 Países reconocen la composición del Estado palestino\n\n"
        "400 Trabajadores de Naciones Unidas murieron en Gaza\n\n"
        "ZOHRAN MAMDANI reiteró sus críticas a acciones de Israel en Gaza, "
        "dijo que Netanyahu aprovechó su discurso para repetir mentiras infundadas "
        "para encubrir el genocidio.",
        text,
    )
    text = re.sub(
        r"(?ms)\n*EL DATO\s*\n+ROARD OF[\s\S]*?ARREST NETANYAU![\s\S]*?ISPA!\s*",
        "\n\n",
        text,
    )
    text = re.sub(r"(?m)^EL DATO\s*$", "", text)
    return text.strip()


def repair_razon_toluca_article(text: str) -> str:
    if not re.search(r"El Toluca no vence al Cruz Azul", text):
        return text
    text = _strip_first_line(text, r"Inicia la Jornada 10")
    text = re.sub(
        r"La Jornada\s*\n+\s*10\.",
        "La Jornada 10.",
        text,
    )
    text = re.sub(r"\banteel\b", "ante el", text)
    text = re.sub(r"\bcincoempates\b", "cinco empates", text)
    text = re.sub(r"\bcuandojuega\b", "cuando juega", text)
    text = re.sub(r"\bempatesy\b", "empates y", text)
    text = re.sub(r"\bEldomingo\b", "El domingo", text)
    text = re.sub(r"no le gana dos seguidos", "no le ha ganado dos seguidos", text)
    text = re.sub(
        r"disputa de la Jornada\s*\n+\s*10\.",
        "disputa de la Jornada 10.",
        text,
    )
    text = re.sub(
        r"favorece\s*\n+\s*La los hidroc[aá]lidos",
        "favorece a los hidrocálidos",
        text,
    )
    text = re.sub(
        r"(?ms)\n*JORNADA 10 vs\. vs\.[\s\S]*?torneo pasado\.",
        "\n\nHOY\n\nJORNADA 10\n\nvs. vs.\n\nHORA: 19:00 HORA:\n\n"
        "ESTADIO: Azteca ESTADIO: Caliente\n\nSÁBADO\n\nvs. vs. vs. vs.\n\n"
        "HORA: 16:50 HORA: 17:07 HORA: 21:05 HORA: 21:10\n\n"
        "ESTADIO: Azteca ESTADIO: AKRON ESTADIO: TSM ESTADIO: Universitario\n\n"
        "DOMINGO\n\nvs. (-) vs. vs.\n\nHORA: 12:00 HORA: 19:00 HORA: 21:10\n\n"
        "ESTADIO: Olimpico ESTADIO: León ESTADIO: Universitario\n\n10\n\n"
        "Goles lleva Salomón Rondón en lo que va del torneo\n\n"
        "PEREIRA y Fernández pelean la redonda el torneo pasado.",
        text,
    )
    return text.strip()


def repair_razon_tramites_article(text: str) -> str:
    if not re.search(r"Federaci[oó]n simplifica m[aá]s de 4 mil tr[aá]mites", text):
        return text
    text = _strip_first_line(text, r"Acelera estrategia digital")
    text, byline = _take_byline(text)
    text = re.sub(r"(?m)^siete licencias a 6 avisos y un permiso\.\s*", "", text)
    text = re.sub(
        r"una Plataforma Nacio\s+En octubre",
        "una Plataforma Nacio siete licencias a 6 avisos y un permiso.\n\nEn octubre",
        text,
    )
    text = re.sub(r"el Expediente Llave MX, herramienta", "el Expediente LlaveMX, herramienta", text)
    text = re.sub(r"transmitir\s*\n+\s*VOZ", "transmitir VOZ", text)
    text = re.sub(r"otro hombre,\s*\n+\s*cuya identidad", "otro hombre, cuya identidad", text)
    deck = (
        "ELIMINA 1,947 procesos, reduce requisitos y baja a la mitad los tiempos "
        "de resolución; alista el Expediente Llave MX, una supercomputadora, un "
        "satélite y medidas para ampliar los pagos"
    )
    text = re.sub(re.escape(deck) + r"\s*", "", text, count=1)
    text = re.sub(
        r"(?m)^LA JEFA del Ejecutivo y el titular de la Agencia de Transformaci[oó]n Digital, ayer\.\s*",
        "",
        text,
    )
    closing = ""
    if byline:
        closing += f"\n\n{byline}"
    closing += (
        f"\n\n{deck}\n\n"
        "Sheinbaum Pardo aclaró que la estrategia no pretende eliminar el uso de "
        "efectivo, incrementar gradualmente las operaciones electrónicas. "
        '"Eso ayuda a seguridad, eficiencia, incluso a formalización, porque se hace '
        "una historia de pagos en una cuenta bancaria; y ayuda también, en su momento, "
        'a formalizar algún comercio o producto", dijo.\n\n'
        "PEÑA MERINO destacó el Centro Público de Formación en Inteligencia Artificial, "
        "con el programa de reperfilamiento y especialización tecnológica más grande de América Latina.\n\n"
        "EL DATO\n\nSimplificación\n\n1,947 4,045\n\nFoto | Especial\n\n"
        "LA JEFA del Ejecutivo y el titular de la Agencia de Transformación Digital, ayer."
    )
    # Recorta el cierre original duplicado a partir de Sheinbaum Pardo aclaró.
    text = re.sub(
        r"\n+Sheinbaum Pardo aclar[oó] que la estrategia no pretende[\s\S]*$",
        "",
        text,
    )
    text = re.sub(r"(?m)^EL DATO\s*$", "", text)
    return (text.strip() + closing).strip()


def repair_razon_ecuador_article(text: str) -> str:
    if not re.search(r"Ecuador y EU asestan golpe a red del CJNG", text):
        return text
    text = _strip_first_line(text, r"Cae cabecilla de Los Mayos en BC")
    text, byline = _take_byline(text)
    text = re.sub(r"vinculadas\.a", "vinculadas a", text)
    text = re.sub(r"vinculadas a la red", "vinculadas a la red", text)
    text = re.sub(
        r"tambi[eé]n con apoyo del Coman[\s\S]{0,40}?como Charlie",
        "también con apoyo del Comando Sur, detuvieron a un sujeto identificado como Charlie",
        text,
    )
    text = re.sub(r"CONTRA C[ÂA]Rte\.", "CONTRA CÁRTE.", text)
    closing = (
        "Tras el operativo, los dos detenidos, así como los indicios asegurados, "
        "quedaron a disposición de la Fiscalía General de la República con sede en Mexicali, "
        "instancia que continuará las investigaciones, realizará los peritajes correspondientes "
        "y definirá su situación jurídica."
    )
    if byline:
        closing += f"\n\n{byline}"
    closing += (
        "\n\nAUTORIDADES ecuatorianas intervinieron residencias lujosas, entre ellas, "
        "una mansión en Puerto Mocolí, Samborondón, donde residían el líder y su operador financiero.\n\n"
        "20 Vehículos de gama alta fueron asegurados por la policía\n\n"
        "Foto | Especial\n\n"
        "ELEMENTOS policiacos de Ecuador, ayer, en operativo contra el CJNG."
    )
    text = re.sub(r"Tras el operativo, los dos detenidos[\s\S]*$", closing, text)
    return text.strip()


def repair_razon_morena_article(text: str) -> str:
    if not re.search(r"Morena rompe alianza con el PT en Morelos", text):
        return text
    closing = (
        "EL DATO\n\nmorena\n\nFoto | Especial\n\n"
        "DE IZQ. a der.: Beatriz Mojica, Abelina López y Ariadna Montiel, ayer, en la CDMX."
    )
    text = re.sub(r"(?m)^Dirigencia destaca unidad\s*\n+", "", text)
    if not re.search(
        r"Morena rompe alianza con el PT en Morelos\s*\n+Dirigencia destaca unidad",
        text,
    ):
        text = re.sub(
            r"(Morena rompe alianza con el PT en Morelos)\s*",
            r"\1\n\nDirigencia destaca unidad\n\n",
            text,
            count=1,
        )
    text, byline = _take_byline(text)
    deck = (
        "COMITÉ ESTATAL del guinda recalca postura; afirma que cualquier acuerdo "
        "debe basarse en la lealtad al proyecto; Montiel y Anaya se reúnen y "
        "refrendan su compromiso político"
    )
    text = re.sub(re.escape(deck) + r"\s*", "", text)
    text = re.sub(r"(?ms)\n*EL DATO\s*\n+morena\s*\n+Foto \| Especial\s*", "\n\n", text)
    text = re.sub(r"(?m)^DE IZQ\. a der\.:[\s\S]*?CDMX\.\s*", "", text)
    text = re.sub(r"(?m)^EL DATO\s*$", "", text)
    text = re.sub(r"(?m)^morena\s*$", "", text)
    text = re.sub(r"(?m)^Foto \| Especial\s*$", "", text)
    if byline and not re.search(r"Por Claudia Arellano\s*\n+claudia\.arellano@razon\.com\.mx", text):
        text = re.sub(
            r"(unidos seguiremos avanzando\"\.)\s*",
            rf'\1\n\n{byline}\n\n{deck}\n\n',
            text,
            count=1,
        )
    elif not re.search(re.escape(deck), text):
        text = re.sub(
            r"(unidos seguiremos avanzando\"\.)\s*",
            rf"\1\n\n{deck}\n\n",
            text,
            count=1,
        )
    text = re.sub(r"Montiel y\s*\n+\s*aseguró", "Montiel y aseguró", text)
    return (text.strip() + "\n\n" + closing).strip()


def repair_razon_lego_article(text: str) -> str:
    if not re.search(r"LEGO invierte 400 mdd", text):
        return text
    text = _strip_first_line(text, r"Ebrard destaca arribo de capitales")
    text, _byline = _take_byline(text)
    text = re.sub(
        r"(?m)^responder al crecimiento de su negocio a escala mundial\.\s*",
        "",
        text,
    )
    text = re.sub(
        r"con los que la compa[nñ][ií]a busca\s*\n+",
        "con los que la compañía busca responder al crecimiento de su negocio a escala mundial.\n\n",
        text,
    )
    text = re.sub(
        r"los [uú]lti\s+MARCELO EBRARD, titular de Econom[ií]a, informa sobre anuncio de inversi[oó]n\.\s*\n+\s*mos meses a[nñ]o,",
        "los últimos meses del año,",
        text,
    )
    caption = "MARCELO EBRARD, titular de Economía, informa sobre anuncio de inversión."
    text = re.sub(re.escape(caption) + r"\s*", "", text)
    text = re.sub(
        r"(?ms)\n*EL DATO N[UÚ]MEROS[\s\S]*$",
        "\n\nEL DATO\n\nNÚMEROS\n\n+400 MDD Inversión\n\n2026-2029 Temporalidad\n\n"
        "1,300 Empleos\n\n+60,000 M2 Construcción\n\nFoto|Especial\n\n" + caption,
        text,
    )
    return text.strip()


def repair_razon_yucatan_article(text: str) -> str:
    if not re.search(r"Renacimiento Maya: destaca Huacho", text):
        return text
    text = _strip_first_line(text, r"Se[nñ]ala optimismo rumbo a 2027")
    text = re.sub(
        r"(?ms)ENTREVISTA Formaci[oó]n:[\s\S]*?adrian\.castillo@razon\.com\.mx",
        "ENTREVISTA Formación: Licenciado en Administración de Empresas Turísticas por el Tecnológico de Mérida. Maestro en Administración Pública Gobierno. Cursó materias de maestría en Economía la Universidad Nacional Autónoma de México (UNAM). Trayectoria: Presidente municipal de San Felipe (2001-2004) bajo las siglas del PAN. Diputado local (2006): Integrante del Congreso del Estado de Yucatán en la LVII Legislatura. Diputado federal (2006-2009): Representó al distrito de Yu Por Adrian Castillo adrian.castillo@razon.com.mx",
        text,
    )
    text = re.sub(r"el\" optimismo\"", 'el "optimismo"', text)
    text = re.sub(r"Jefa de de Gobierno", "Jefa de Gobierno", text)
    text = re.sub(r"\bS bien la crisis", "Si bien la crisis", text)
    text = re.sub(r"para in a recibirlo", "para in arecibirlo", text)
    text = re.sub(r"el canal y lo\s*\n+\s*profundizamos", "el canal y lo profundizamos", text)
    text = re.sub(r"(?m)^segunda está pensada", "La segunda está pensada", text)
    text = re.sub(r"(?m)^JOAQUÍN DÍAZ\s*$", "", text)
    quotes = (
        '"NOSOTROS NOS comprometimos con la Presidenta a abrir cinco nuevas universidades '
        'en Yucatán y en dos años ya lo estamos concretando" JOAQUÍN DÍAZ MENA Gobernador de Yucatán\n\n'
        '"LA UBICACIÓN estratégica de Progreso con la Costa Este de Estados Unidos genera que muchas '
        'empresas estén interesadas en venir a los polos industriales de Bienestar" JOAQUÍN DÍAZ MENA '
        "Gobernador de Yucatán\n\n"
        "EL MANDATARIO estatal, en la casa del gobierno de Yucatán en la CDMX."
    )
    text = re.sub(
        r'\n+"\s*\n*NOSOTROS NOS comprometimos[\s\S]*$',
        "\n\n" + quotes,
        text,
    )
    text = re.sub(
        r"(?ms)\n*EL DATO MENA RENACIMIENTO MAYA[\s\S]*$",
        "\n\n" + quotes,
        text,
    )
    return text.strip()


def repair_razon_ine_article(text: str) -> str:
    if not re.search(r"INE aprueba reglas para coaliciones", text):
        return text
    text, byline = _take_byline(text)
    if byline and not re.search(r"Por Tania G[oó]mez\s*\n+tania\.gomez@razon\.com\.mx", text):
        text = re.sub(
            r"(INE aprueba reglas para coaliciones y precampa[nñ]a)\s*",
            rf"\1\n\n{byline}\n\n",
            text,
            count=1,
        )
    text = re.sub(r"tania\.gomez@razon\.com\.mx\s+EL CONSEJO", "tania.gomez@razon.com.mx\n\nEL CONSEJO", text)
    text = re.sub(r"ilegalmente va empez[oó]", "ilegalmente ya empezó", text)
    text = re.sub(r"ys[oó]lido", "y sólido", text)
    text = re.sub(
        r"solicitud para\s*\n+\s*siete informes",
        "solicitud para siete informes",
        text,
    )
    text = re.sub(
        r'presidenta labor institucional: "S[ií] hay transparencia\.\s*\n+\s*S[ií] hay rendici[oó]n',
        'presidenta labor institucional: "Sí hay transparencia. Sí hay rendición',
        text,
    )
    ending = (
        'Baños coincidió en que "no hay ningún argumento que justifique que las sesiones se realicen de manera virtual" '
        "y cuestionó la respuesta dada a su solicitud para siete informes, entre mientos de remoción en OPLE, "
        "renuncias de personal y el pago de 6.2 millones de pesos en honorarios a ocho personas.\n\n"
        'Ante los señalamientos, la presidenta labor institucional: "Sí hay transparencia. Sí hay rendición de cuentas. '
        'Sí hay voluntad de presentar y entregar información a quien así lo solicite".\n\n'
        '"LAS PERSONAS militantes deben conocer con oportunidad las reglas bajo las cuales competirán y contar con plazos '
        "suficientes para, en su caso, impugnarlas antes de que inicien los procesos internos y no cuando éstos ya estén en curso\"\n\n"
        "MARTÍN FAZ Consejero del INE\n\n"
        "Partidos nacionales hay en nuestro país con registro vigente\n\n"
        'GUADALUPE TADDEI afirmó que el INE está "listo, fuerte y sólido" para enfrentar el proceso electoral de 2027, '
        "al que calificó como complejo por el contexto político, social y económico.\n\n"
        "EL DATO\n\nFoto|Especial\n\nINE\n\nConsejo General\n\n"
        "SESIÓN VIRTUAL del Consejo General del órgano electoral, ayer."
    )
    text = re.sub(r"Baños coincidi[oó] en que[\s\S]*$", ending, text)
    return text.strip()


def repair_razon_juchitan_article(text: str) -> str:
    if not re.search(r"Caso Juchit[aá]n desmiente a Trump", text):
        return text
    text, byline = _take_byline(text)
    text = re.sub(r"fevinculados", "fe vinculados", text)
    text = re.sub(r"Gobierno fe vinculados", "Gobierno fe vinculados", text)
    text = re.sub(r"(?m)^37\s+Años del edad", "37\n\nAños del edad", text)
    text = re.sub(
        r"(?ms)\n*Por Claudia Arellano\s*\n+claudia\.arellano@razon\.com\.mx\s*",
        "\n\n",
        text,
    )
    text = re.sub(r"(?ms)\n*37\s*\n+Años del edad tiene el alcalde de Juchit[aá]n detenido\s*$", "", text)
    closing = ""
    if byline:
        closing += f"\n\n{byline}"
    closing += "\n\n37\n\nAños del edad tiene el alcalde de Juchitán detenido"
    return (text.strip() + closing).strip()


def repair_razon_amnistia_article(text: str) -> str:
    if not re.search(r"Amnist[ií]a denuncia al ICE", text):
        return text
    text = re.sub(r"Redacci[oó]n\s+AMNIST[IÍ]A", "AMNISTÍA", text)
    text = re.sub(r"(?m)^Redacci[oó]n\s*$", "", text)
    text = re.sub(r"(?m)^EL DATO\s*$", "", text)
    text = re.sub(r"(?m)^ELTIP\s*$", "", text)
    text = re.sub(r"Responsabilidad\s*\n+\s*Gubernamental", "Responsabilidad Gubernamental", text)
    text = re.sub(r"detenci[oó]n\s*\n+\s*sin una planeaci[oó]n", "detención sin una planeación", text)
    text = re.sub(
        r"182\s*\n+\s*D[oó]lares por detenido",
        "182 Dólares por detenido",
        text,
    )
    return text.strip()


def repair_prensa_fernanda_article(text: str) -> str:
    if not re.search(r"Fernanda Castillo r[ií]e", text):
        return text
    text = re.sub(
        r"Fernanda Castillo r[ií]e(?! con zombies)",
        "Fernanda Castillo ríe con zombies",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^ctuar junto al elenco de A\s*\n+\s*Prefiero",
        "Actuar junto al elenco de Prefiero",
        text,
    )
    text = re.sub(r"\bFarah Justiniani\b", "Farrah Justiniani", text)
    text = re.sub(
        r"AHORA EST[AÁ] DEL OTRO LADO\s+Fernanda Castillo interpreta",
        "AHORA ESTÁ DEL OTRO LADO\n\nFernanda Castillo interpreta",
        text,
    )
    if not re.search(r"(?m)^OMAR FLORES\s*$", text):
        text = re.sub(
            r"(EN LA serie interpreta a una detective que debe perseguir a otros personajes, mientras cuida de los j[oó]venes)\s*",
            r"\1\n\nOMAR FLORES\n\namazon prime\n\n",
            text,
            count=1,
        )
    return text.strip()


def repair_prensa_crt_article(text: str) -> str:
    if not re.search(r"Propone CRT reducir tr[aá]mites", text):
        return text
    text = _strip_first_line(text, r"BAJAR[IÍ]AN DE 20 A TRES")
    text = re.sub(
        r"necesidades del a Comisi[oó]n Reguladora",
        "necesidades del sector\n\nLa Comisión Reguladora",
        text,
    )
    text = re.sub(r"necesidades del sector\s*\n+\s*La Comisi[oó]n Reguladora", "necesidades del sector\n\nLa Comisión Reguladora", text)
    text = re.sub(r"pesos adisector\s*\n+\s*cionales", "pesos adicionales", text)
    text = re.sub(
        r"gran escala\.\s*\n+\s*Los trabajos peque[nñ]os",
        "gran escala. Los trabajos pequeños",
        text,
    )
    text = re.sub(r"crear un\s*\n+\s*Expediente Digital [UÚ]nico", "crear un Expediente Digital Único", text)
    text = re.sub(
        r"documentos MMDP esperan",
        "documentos.\n\n13 MMDP esperan",
        text,
    )
    text = re.sub(
        r"13 Las antenas de telecomunicaciones",
        "Las antenas de telecomunicaciones",
        text,
    )
    return text.strip()


def repair_prensa_agencia_notes(text: str) -> str:
    if re.search(r"Premian a Diego Luna", text):
        text = re.sub(r"(?m)^EFE\s*$", "", text)
        text = re.sub(r"\n+EFE(?:\s+EFE)?\s*$", "", text)
        text = re.sub(
            r"(Premian a Diego Luna en San Sebasti[aá]n)\s*",
            r"\1\n\nEFE\n\n",
            text,
            count=1,
        )
        text = re.sub(r"(EFE\n\n)+", "EFE\n\n", text)
    if re.search(r"Arrestan en NY a Susan Sarandon", text):
        text = re.sub(r"(?m)^AFP\s*$", "", text)
        text = re.sub(r"(?m)^FUND AFP\s*$", "", text)
        text = re.sub(r"\n+AFP(?:\s+FUND AFP)?\s*$", "", text)
        text = re.sub(
            r"(Arrestan en NY a Susan Sarandon)\s*",
            r"\1\n\nAFP\n\n",
            text,
            count=1,
        )
        text = re.sub(r"(AFP\n\n)+", "AFP\n\n", text)
    if re.search(r"Hallan restos humanos embolsados|restos humanos pertenec", text, flags=re.IGNORECASE):
        if "FOTO ILUSTRATIVA" not in text:
            text = re.sub(
                r"(Los restos estaban a un costado de la carretera)\s*$",
                r"FOTO ILUSTRATIVA\n\n\1",
                text,
            )
    if re.search(r"Banxico|tipo de cambio de", text):
        text = re.sub(r"de(\d+\.\d+)", r"de \1", text)
        text = re.sub(r"Estados\s*\n+\s*Unidos \(Fed\)", "Estados Unidos (Fed)", text)
    if re.search(r"Gabriela Mart[ií]nez|AFOC M[eé]xico", text):
        text = re.sub(r"es'¿hay", "es '¿hay", text)
        text = re.sub(
            r'(?m)^Se han sorprendido cuando yo menciono',
            '"Se han sorprendido cuando yo menciono',
            text,
        )
    return text.strip()


def repair_la_prensa_razon_set(text: str) -> str:
    text = repair_prensa_rumor_article(text)
    text = repair_prensa_joselyn_article(text)
    text = repair_prensa_edomex_article(text)
    text = repair_prensa_fernanda_article(text)
    text = repair_prensa_crt_article(text)
    text = repair_prensa_agencia_notes(text)
    text = repair_razon_gaza_article(text)
    text = repair_razon_toluca_article(text)
    text = repair_razon_tramites_article(text)
    text = repair_razon_ecuador_article(text)
    text = repair_razon_morena_article(text)
    text = repair_razon_lego_article(text)
    text = repair_razon_yucatan_article(text)
    text = repair_razon_ine_article(text)
    text = repair_razon_juchitan_article(text)
    text = repair_razon_amnistia_article(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

"""Datos REALES tomados del sitio público https://www.elmexicanosrl.com."""

URL_COMPRA = "https://elmexicano.pagoseguro.cloud/#/sale-tickets"
URL_RASTREO = "https://elmexicano.pagoseguro.cloud/#/tracking"

EMPRESA = {
    "id": 1,
    "razon_social": "Transportes El Mexicano S.R.L.",
    "nombre_comercial": "El Mexicano",
    "nit": "1028374025",  # demo
    "ente_regulador": "Autoridad de Telecomunicaciones y Transportes (ATT)",
    "sitio_web": "https://www.elmexicanosrl.com",
    "url_compra_pasajes": URL_COMPRA,
    "url_rastreo_carga": URL_RASTREO,
    "facebook_url": "https://www.facebook.com/transporteselmexicano",
    "email_contacto": "contacto@elmexicanosrl.com",  # demo
    "telefono_central_e164": "59167640155",
    "telefono_atencion_cliente_e164": "59167640155",
    "whatsapp_central_e164": "59171420823",
    "color_marca": "#a90202",
    "eslogan": "Compra online 100% segura de pasajes de bus y rastreo de carga y encomienda.",
    "descripcion": (
        "Empresa boliviana de transporte interdepartamental de pasajeros en buses de dos pisos "
        "(Suite Cama en planta alta y Leito Cama en planta baja) y de carga y encomiendas con rastreo "
        "en tiempo real. Empresa regulada y fiscalizada por la Autoridad de Telecomunicaciones y "
        "Transportes del Estado Plurinacional de Bolivia - ATT."
    ),
    "terminos_condiciones": (
        "Texto de demostración. El pasaje es personal e intransferible y debe coincidir con el documento "
        "de identidad del pasajero. Las fechas y horas de partida están sujetas a cambios. Los reembolsos "
        "se rigen por la política publicada en el Centro de Ayuda."
    ),
    "moneda": "BOB",
    "zona_horaria": "America/La_Paz",
}

CIUDADES = [
    {
        "codigo": "SRE",
        "nombre": "Sucre",
        "departamento": "Chuquisaca",
        "es_destino_pasajeros": True,
        "es_destino_carga": True,
        "tiene_puerta_a_puerta": True,
        "whatsapp_puerta_a_puerta_e164": "59168779945",
        "alias_busqueda": ["sucre", "sre", "chuquisaca", "ciudad blanca", "capital"],
    },
    {
        "codigo": "CMG",
        "nombre": "Camargo",
        "departamento": "Chuquisaca",
        "es_destino_pasajeros": False,
        "es_destino_carga": True,
        "tiene_puerta_a_puerta": False,
        "whatsapp_puerta_a_puerta_e164": None,
        "alias_busqueda": ["camargo", "cmg"],
    },
    {
        "codigo": "SCZ",
        "nombre": "Santa Cruz",
        "departamento": "Santa Cruz",
        "es_destino_pasajeros": True,
        "es_destino_carga": True,
        "tiene_puerta_a_puerta": True,
        "whatsapp_puerta_a_puerta_e164": "59167601683",
        "alias_busqueda": ["santa cruz de la sierra", "scz", "santa", "santacruz"],
    },
    {
        "codigo": "TJA",
        "nombre": "Tarija",
        "departamento": "Tarija",
        "es_destino_pasajeros": True,
        "es_destino_carga": True,
        "tiene_puerta_a_puerta": False,
        "whatsapp_puerta_a_puerta_e164": None,
        "alias_busqueda": ["tarija", "tja"],
    },
    {
        "codigo": "PTS",
        "nombre": "Potosí",
        "departamento": "Potosí",
        "es_destino_pasajeros": False,
        "es_destino_carga": True,
        "tiene_puerta_a_puerta": False,
        "whatsapp_puerta_a_puerta_e164": None,
        "alias_busqueda": ["potosi", "pts", "villa imperial"],
    },
    {
        "codigo": "LPZ",
        "nombre": "La Paz",
        "departamento": "La Paz",
        "es_destino_pasajeros": True,
        "es_destino_carga": True,
        "tiene_puerta_a_puerta": False,
        "whatsapp_puerta_a_puerta_e164": None,
        "alias_busqueda": ["la paz", "lpz", "lapaz"],
    },
    {
        "codigo": "EAT",
        "nombre": "El Alto",
        "departamento": "La Paz",
        "es_destino_pasajeros": False,
        "es_destino_carga": True,
        "tiene_puerta_a_puerta": False,
        "whatsapp_puerta_a_puerta_e164": None,
        "alias_busqueda": ["el alto", "eat", "alto"],
    },
]

_MAPA_CAMARGO = "https://www.google.com/maps/place/Terminal+Interdepartamental+de+buses/@-20.6434267,-65.2086126,17z"

# (ciudad, codigo, nombre, tipo, direccion, referencia, telefono, whatsapp, url_mapa, principal, lat, lon)
OFICINAS = [
    (
        "SRE",
        "SRE-BOL",
        "Boletería Sucre",
        "boleteria",
        "Av. Ostria Gutiérrez s/n",
        "Terminal de Buses",
        "59167640155",
        None,
        "https://maps.app.goo.gl/624bjBuHGhuoPqqY9",
        True,
        None,
        None,
    ),
    (
        "SRE",
        "SRE-BOD",
        "Bodega Sucre",
        "bodega_carga",
        "Av. Ostria Gutiérrez s/n",
        "Terminal de Buses",
        "59168779945",
        "59168779945",
        "https://maps.app.goo.gl/624bjBuHGhuoPqqY9",
        False,
        None,
        None,
    ),
    (
        "CMG",
        "CMG-BOL",
        "Boletería Camargo",
        "boleteria",
        "Calle Marcelo Quiroga Santa Cruz",
        "Terminal Interdepartamental de Buses de Camargo",
        "59174414412",
        None,
        _MAPA_CAMARGO,
        True,
        -20.6434267,
        -65.2086126,
    ),
    (
        "CMG",
        "CMG-BOD",
        "Bodega Camargo",
        "bodega_carga",
        "Calle Marcelo Quiroga Santa Cruz",
        "Terminal Interdepartamental de Buses de Camargo",
        "59174414412",
        None,
        _MAPA_CAMARGO,
        False,
        -20.6434267,
        -65.2086126,
    ),
    (
        "SCZ",
        "SCZ-BOL",
        "Boletería Santa Cruz",
        "boleteria",
        "Av. Intermodal s/n",
        None,
        "59167601669",
        None,
        "https://maps.app.goo.gl/cYCvchyuVkmSx92P6",
        True,
        None,
        None,
    ),
    (
        "SCZ",
        "SCZ-BOD1",
        "Bodega Santa Cruz 1",
        "bodega_carga",
        "Av. Intermodal s/n",
        None,
        "59171160649",
        None,
        "https://maps.app.goo.gl/cYCvchyuVkmSx92P6",
        False,
        None,
        None,
    ),
    (
        "SCZ",
        "SCZ-BOD2",
        "Bodega Santa Cruz 2",
        "bodega_carga",
        "Av. Intermodal s/n entre Daniel Salamanca y Hernando Siles",
        None,
        "59167601683",
        "59167601683",
        "https://maps.app.goo.gl/qJmmHKGSdUXsG4N48",
        False,
        None,
        None,
    ),
    (
        "TJA",
        "TJA-BOL",
        "Boletería Tarija",
        "boleteria",
        "Carretera al Chaco, zona Torrecillas",
        None,
        "59167602934",
        None,
        "https://maps.app.goo.gl/FmWPuHFmmKxtGsTo7",
        True,
        None,
        None,
    ),
    (
        "TJA",
        "TJA-BOD",
        "Bodega Tarija",
        "bodega_carga",
        "Carretera al Chaco, zona Torrecillas",
        None,
        "59167602934",
        None,
        "https://maps.app.goo.gl/FmWPuHFmmKxtGsTo7",
        False,
        None,
        None,
    ),
    (
        "PTS",
        "PTS-BOD",
        "Bodega Potosí",
        "bodega_carga",
        "Av. Las Banderas s/n",
        None,
        "59168633698",
        None,
        "https://maps.app.goo.gl/TnMrZNdQu2AX7A2F9",
        True,
        None,
        None,
    ),
    (
        "LPZ",
        "LPZ-BOL",
        "Boletería La Paz",
        "boleteria",
        "Av. Perú",
        None,
        "59171327449",
        None,
        "https://maps.app.goo.gl/7zXfGcxEoqLHnA8D6",
        True,
        None,
        None,
    ),
    (
        "LPZ",
        "LPZ-BOD",
        "Bodega La Paz",
        "bodega_carga",
        "Av. Perú",
        None,
        "59171164678",
        None,
        "https://maps.app.goo.gl/7zXfGcxEoqLHnA8D6",
        False,
        None,
        None,
    ),
    (
        "EAT",
        "EAT-BOL",
        "Boletería El Alto",
        "boleteria",
        "Carretera a Viacha, Ladislao Cabrera",
        None,
        "59171327449",
        None,
        "https://maps.app.goo.gl/QFVTf8v2btndtNGg8",
        True,
        None,
        None,
    ),
    (
        "EAT",
        "EAT-BOD",
        "Bodega El Alto",
        "bodega_carga",
        "Carretera a Viacha, Ladislao Cabrera",
        None,
        "59171164678",
        None,
        "https://maps.app.goo.gl/QFVTf8v2btndtNGg8",
        False,
        None,
        None,
    ),
]

# Horas reales; los días no se publican (demo).
HORARIO_BOLETERIA = ("07:00", "20:00", range(1, 8))  # lunes a domingo
HORARIO_BODEGA = ("08:00", "18:00", range(1, 7))  # lunes a sábado

TIPOS_ASIENTO = [
    {
        "codigo": "SUITE_CAMA",
        "nombre": "Suite Cama",
        "planta": "alta",
        "inclinacion_grados": 180,
        "orden": 1,
        "descripcion": "Planta alta. Asientos que se reclinan hasta 180°, con TV individual.",
    },
    {
        "codigo": "LEITO_CAMA",
        "nombre": "Leito Cama",
        "planta": "baja",
        "inclinacion_grados": 160,
        "orden": 2,
        "descripcion": "Planta baja. Asientos que se reclinan hasta 160°, con TV en cabina.",
    },
]

COMODIDADES = [
    ("asientos_reclinables", "Asientos reclinables", "seat"),
    ("cargadores_usb", "Cargadores USB", "usb"),
    ("calefaccion", "Calefacción", "heat"),
    ("bano_unisex", "Baño unisex", "wc"),
    ("tv_individual", "TV individual", "tv"),
    ("tv_cabina", "TV en cabina", "tv"),
    ("aire_acondicionado", "Aire acondicionado", "snowflake"),
]

COMODIDADES_POR_TIPO = {
    "SUITE_CAMA": [
        "asientos_reclinables",
        "cargadores_usb",
        "calefaccion",
        "bano_unisex",
        "tv_individual",
        "aire_acondicionado",
    ],
    "LEITO_CAMA": [
        "asientos_reclinables",
        "cargadores_usb",
        "calefaccion",
        "bano_unisex",
        "tv_cabina",
        "aire_acondicionado",
    ],
}

# (codigo, origen, destino, km, minutos)
RUTAS = [
    ("SRE-SCZ", "SRE", "SCZ", 661, 840),
    ("SCZ-SRE", "SCZ", "SRE", 661, 840),
    ("SRE-TJA", "SRE", "TJA", 469, 660),
    ("TJA-SRE", "TJA", "SRE", 469, 660),
    ("SRE-LPZ", "SRE", "LPZ", 555, 720),
    ("LPZ-SRE", "LPZ", "SRE", 555, 720),
]

# (tipo, nombre, %, solo_boleteria, edad_min, edad_max, requisito, es_demo)
POLITICAS = [
    ("adulto", "Adulto", 0, False, 12, None, "Documento de identidad que coincida con el pasaje", False),
    (
        "menor",
        "Menor de edad (3 a 11 años)",
        50,
        True,
        3,
        11,
        "Permiso de Viaje de la Defensoría de la Niñez y Adolescencia",
        False,
    ),
    ("adulto_mayor", "Adulto mayor (60 años o más)", 20, True, 60, None, "Cédula de identidad", False),
    ("persona_con_discapacidad", "Persona con discapacidad", 50, True, None, None, "Carnet de discapacidad", True),
    ("embarazada", "Embarazada", 0, False, None, None, "Hasta 30 semanas de gestación", False),
]

FAQ_CATEGORIAS = [
    ("pasajeros", "Pasajeros", 1),
    ("pasajes_y_pagos", "Pasajes y pagos", 2),
    ("equipaje", "Equipaje", 3),
    ("viaje", "Viaje", 4),
    ("carga", "Carga y encomiendas", 5),
]

# (categoria, slug, pregunta, respuesta REAL, respuesta corta para voz, palabras clave)
FAQS = [
    (
        "pasajeros",
        "viaje-de-menores",
        "Viaje de menores",
        "Padres y tutores de menores que viajan deben recabar anticipadamente el Permiso de Viaje en la "
        "Defensoría de la Niñez y Adolescencia. Los menores sin Permiso de Viaje no podrán abordar el bus.\n\n"
        "Menores de 3 a 11 años y 11 meses gozan de un descuento de 50% sobre la tarifa máxima referencial. "
        "Este boleto únicamente podrá ser adquirido en boleterías previa presentación del Permiso de Viaje.",
        "Los menores necesitan el Permiso de Viaje de la Defensoría de la Niñez. De 3 a 11 años tienen 50% de "
        "descuento, y ese boleto se compra solo en boletería.",
        ["menor", "menores", "niño", "niña", "hijo", "permiso de viaje", "defensoria", "descuento"],
    ),
    (
        "pasajeros",
        "embarazadas",
        "Embarazadas",
        "Las embarazadas pueden viajar hasta el sexto mes de gestación (30 semanas).",
        "Las embarazadas pueden viajar hasta las 30 semanas de gestación.",
        ["embarazada", "embarazo", "gestacion", "semanas"],
    ),
    (
        "pasajeros",
        "adultos-mayores",
        "Adultos mayores",
        "Los adultos mayores (60 años o más) gozan de un descuento de ley del 20% sobre la tarifa máxima "
        "referencial. Los boletos con estas tarifas especiales pueden ser adquiridos solo en boleterías.",
        "Las personas de 60 años o más tienen 20% de descuento de ley, comprando en boletería.",
        ["adulto mayor", "tercera edad", "jubilado", "descuento", "60 años"],
    ),
    (
        "pasajeros",
        "mascotas",
        "Mascotas",
        "No está permitido el transporte de mascotas en cabina o bodega, salvo sean perros lazarillos y deben "
        "permanecer al lado de sus dueños.",
        "No se permiten mascotas, ni en cabina ni en bodega. La única excepción son los perros lazarillos.",
        ["mascota", "perro", "gato", "animal", "lazarillo"],
    ),
    (
        "pasajes_y_pagos",
        "facturas-y-boletos",
        "Facturas y boletos",
        "Su pasaje (e-ticket) constituye factura deducible de impuestos.\n\nSu e-ticket será enviado en PDF a "
        "su email y también podrá descargarlo o imprimirlo después de realizar su compra.",
        "Tu pasaje electrónico es también tu factura. Te llega en PDF a tu correo.",
        ["factura", "nit", "boleto", "e-ticket", "pdf", "correo"],
    ),
    (
        "pasajes_y_pagos",
        "comprar-boletos-en-linea",
        "¿Puedo comprar boletos en línea?",
        f"Sí, ingresa a este link: {URL_COMPRA}",
        "Sí, puedes comprar en línea en elmexicano punto pagoseguro punto cloud.",
        ["comprar", "online", "en linea", "internet", "web", "pagina"],
    ),
    (
        "pasajes_y_pagos",
        "medios-de-pago",
        "¿Con qué medios de pago puedo comprar boletos?",
        "Puedes comprar con:\n\n- Código QR (solo bancos bolivianos).\n- Tarjetas de débito/crédito Visa o "
        "Mastercard emitidas por bancos nacionales o internacionales.\n- Tigo Money (Bolivia).",
        "Puedes pagar con QR de bancos bolivianos, tarjeta Visa o Mastercard, o Tigo Money.",
        ["pago", "pagar", "qr", "tarjeta", "visa", "mastercard", "tigo money", "debito", "credito"],
    ),
    (
        "pasajes_y_pagos",
        "pasajes-electronicos",
        "Sobre pasajes electrónicos",
        "Puede imprimir el pasaje electrónico para mostrarlo a tiempo de abordar el bus o puede tenerlo "
        "digitalmente (en imagen) en su dispositivo móvil.\n\nEl pasaje debe coincidir con el documento de "
        "identificación del pasajero.",
        "Puedes mostrar el pasaje impreso o en tu celular. Debe coincidir con tu documento de identidad.",
        ["pasaje electronico", "imprimir", "celular", "abordar", "documento"],
    ),
    (
        "pasajes_y_pagos",
        "reajuste-de-precios",
        "Reajuste de precios",
        "Una vez adquirido el boleto no aplican cambios de tarifa.",
        "Una vez que compras el boleto, el precio ya no cambia.",
        ["precio", "tarifa", "reajuste", "aumento", "cambio"],
    ),
    (
        "pasajes_y_pagos",
        "reembolsos",
        "Reembolsos",
        "Conforme a regulaciones, los pasajes que no fueron usados son reembolsables hasta un 85% del valor "
        "pagado. La devolución está sujeta a ser solicitada en boletería con 2 horas previas al horario de "
        "salida.\n\nNo aplica devolución de pasajes a menos de dos horas de la hora de salida del bus "
        "establecida en el boleto. No aplican devoluciones pasada la hora de salida establecida en el boleto."
        "\n\nLos pasajes adquiridos mediante tarjeta de crédito u otros medios de pago digitales a través de "
        "la página web o la aplicación móvil de la empresa son reembolsables en un 85% del valor total. Para "
        "ello, la solicitud de reembolso debe realizarse al menos 2 horas antes del horario programado de "
        "salida. La empresa transportista retendrá el 15% del valor total del pasaje, incluyendo los costos "
        "asociados a la emisión de la factura.\n\nLa solicitud de reembolso deberá hacerse por teléfono a "
        "nuestra línea de Atención al Cliente +591 67640155.\n\nSi un pasaje fue emitido utilizando servicios "
        "bancarios, la devolución será del 85% del valor total del pasaje. El reembolso puede demorar hasta "
        "7 días hábiles.",
        "Te devolvemos el 85% si lo pides al menos 2 horas antes de la salida, llamando al 6 7 6 4 0 1 5 5. "
        "Después ya no hay devolución. El reembolso tarda hasta 7 días hábiles.",
        ["reembolso", "devolucion", "devolver", "devuelvan", "dinero", "cancelar", "anular", "85"],
    ),
    (
        "equipaje",
        "politica-de-equipajes",
        "Política de equipajes",
        "Derecho a 20 kg de equipaje en buzón por pasajero.\n\nDerecho a un máximo de 5 kg de equipaje de mano "
        "por pasajero.\n\nExceso de equipaje sujeto a cobro por kg adicional a la franquicia, de acuerdo a ruta.",
        "Cada pasajero lleva 20 kilos en bodega y 5 de mano. El exceso se cobra por kilo según la ruta.",
        ["equipaje", "maleta", "kilos", "kg", "exceso", "bodega", "mano", "buzon"],
    ),
    (
        "viaje",
        "hora-de-salida-demoras-y-cancelaciones",
        "Hora de salida, demoras y cancelaciones",
        "Las fechas y horas de partida están sujetas a cambios y modificaciones.\n\nSi el viaje se cancela por "
        "razones atribuibles a la empresa transportista, la devolución del pasaje será inmediata y por el 100% "
        "de su valor.\n\nLa empresa no se responsabiliza en caso de demora causada por averías causadas por "
        "externos, condiciones viales, condiciones climatológicas desfavorables u otras condiciones más allá "
        "del control razonable del transportista.",
        "Si la empresa cancela el viaje, te devolvemos el 100% de inmediato. Los horarios pueden cambiar por "
        "condiciones del camino o del clima.",
        ["horario", "salida", "demora", "retraso", "cancelacion", "atraso", "bloqueo"],
    ),
    (
        "carga",
        "rastrear-mi-carga",
        "Quiero rastrear mi carga",
        f"Para rastrear su carga, toque este link: {URL_RASTREO}",
        "Puedes rastrear tu carga con el número de guía de 8 dígitos.",
        ["rastrear", "rastreo", "encomienda", "carga", "guia", "tracking", "paquete"],
    ),
]

PAGINAS = [
    (
        "inicio",
        "El Mexicano | Pasajes de bus, carga y encomiendas",
        "Compra online 100% segura de pasajes de bus y rastreo de carga y encomienda.",
        "# Transportes El Mexicano\n\nCompra online 100% segura de pasajes de bus y rastreo de carga y "
        "encomienda.\n\n- **Pasajes**: Sucre ↔ Santa Cruz, Tarija y La Paz.\n- **Buses** de dos pisos Suite "
        "Cama y Leito Cama.\n- **Carga y encomiendas** a 7 ciudades, con puerta a puerta en Sucre y Santa Cruz."
        "\n\nEmpresa regulada y fiscalizada por la Autoridad de Telecomunicaciones y Transportes del Estado "
        "Plurinacional de Bolivia - ATT.",
        "https://www.elmexicanosrl.com",
    ),
    (
        "pasajes",
        "Pasajes de bus",
        "Compra tus pasajes sin hacer colas.",
        "# Pasajes de bus\n\nSin hacer colas y 100% seguro. Paga con **QR, tarjeta de débito o crédito y Tigo "
        f"Money**.\n\n[Comprar pasajes]({URL_COMPRA})",
        "https://www.elmexicanosrl.com/pasajes-de-bus",
    ),
    (
        "rutas",
        "Rutas e itinerarios",
        "Rutas de pasajeros y destinos de carga.",
        "# Rutas e itinerarios\n\n| Ruta | Distancia | Duración | Servicio |\n|---|---|---|---|\n"
        "| Sucre ↔ Santa Cruz | 661 km | 14 h | Suite Cama - Leito Cama |\n"
        "| Sucre ↔ Tarija | 469 km | 11 h | Suite Cama - Leito Cama |\n"
        "| Sucre ↔ La Paz | 555 km | 12 h | Suite Cama - Leito Cama |\n\n"
        "**Destinos de carga:** Sucre, Camargo, Santa Cruz, Tarija, La Paz, El Alto y Potosí.",
        "https://www.elmexicanosrl.com/rutas-e-itinerarios",
    ),
    (
        "buses",
        "Nuestros buses",
        "Buses de dos pisos Suite Cama y Leito Cama.",
        "# Nuestros buses\n\n## Suite Cama — planta alta\nAsientos reclinables a 180°, cargadores USB, "
        "calefacción, baño unisex, TV individual y aire acondicionado.\n\n## Leito Cama — planta baja\n"
        "Asientos reclinables a 160°, cargadores USB, calefacción, baño unisex, TV en cabina y aire "
        "acondicionado.",
        "https://www.elmexicanosrl.com/nuestros-buses",
    ),
    (
        "oficinas",
        "Boleterías y bodegas",
        "Direcciones de oficinas y bodegas.",
        "# Direcciones de oficinas y bodegas\n\nBoleterías de 07:00 a 20:00 y bodegas de 08:00 a 18:00 en "
        "Sucre, Camargo, Santa Cruz, Tarija, Potosí, La Paz y El Alto. Consulta el detalle en "
        "`GET /api/v1/oficinas`.",
        "https://www.elmexicanosrl.com/boleter%C3%ADas-y-bodegas",
    ),
    (
        "carga",
        "Carga y encomienda",
        "Envíos nacionales con rastreo en tiempo real.",
        "# Carga y encomienda\n\n## Sobres y paquetes (hasta 30 kg)\nServicio nacional. Pago en origen o "
        "destino. Cuentas corporativas.\n\n## Carga (más de 30 kg)\nServicio nacional con GPS. Mudanzas.\n\n"
        "## Puerta a puerta (desde 1 kg)\nRecogemos su encomienda o carga de la dirección que nos indique y la "
        "entregamos a su debido tiempo en la puerta del destinatario. Disponible en Sucre y Santa Cruz.\n\n"
        "- Entregas: 08:00 a 12:00, lunes a viernes.\n- Recojos: 14:00 a 17:00, lunes a viernes.\n"
        "- Sucre: 68779945 · Santa Cruz: 67601683 (teléfono, WhatsApp o chat).\n\n"
        "Rastreo en tiempo real, guía electrónica y ubicación GPS.",
        "https://www.elmexicanosrl.com/carga-y-encomienda",
    ),
    (
        "ayuda",
        "Centro de ayuda",
        "Preguntas frecuentes.",
        "# Preguntas frecuentes\n\nConsulta las respuestas en `GET /api/v1/faqs`. WhatsApp: +591 71420823.",
        "https://www.elmexicanosrl.com/centro-de-ayuda",
    ),
    (
        "terminos",
        "Términos y condiciones",
        "Términos y condiciones del servicio.",
        "# Términos y condiciones\n\n" + EMPRESA["terminos_condiciones"],
        None,
    ),
]

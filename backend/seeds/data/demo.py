"""Datos FICTICIOS (demo). Todo lo de este archivo se marca con es_dato_demo = true donde aplica."""

from datetime import date

PASSWORD_DEMO = "ElMexicano2026!"

# (numero_interno, placa, marca, modelo, año, estado)
BUSES = [
    ("M-01", "4521KDB", "Marcopolo", "Paradiso G7 1800 DD", 2022, "operativo"),
    ("M-02", "4522KDB", "Marcopolo", "Paradiso G7 1800 DD", 2022, "operativo"),
    ("M-03", "3987JHT", "Marcopolo", "Paradiso G7 1800 DD", 2021, "operativo"),
    ("M-04", "3988JHT", "Marcopolo", "Paradiso G7 1800 DD", 2021, "operativo"),
    ("M-05", "5102LPA", "Busscar", "Vissta Buss DD", 2023, "operativo"),
    ("M-06", "5103LPA", "Busscar", "Vissta Buss DD", 2023, "operativo"),
    ("M-07", "4870KZX", "Irizar", "i8 DD", 2022, "operativo"),
    ("M-08", "4871KZX", "Irizar", "i8 DD", 2022, "operativo"),
    ("M-09", "3456JAB", "Marcopolo", "Paradiso G7 1800 DD", 2020, "operativo"),
    ("M-10", "3457JAB", "Marcopolo", "Paradiso G7 1800 DD", 2020, "operativo"),
    ("M-11", "5340LRC", "Busscar", "Vissta Buss DD", 2024, "operativo"),
    ("M-12", "5341LRC", "Busscar", "Vissta Buss DD", 2024, "operativo"),
    ("M-13", "2981HTP", "Marcopolo", "Paradiso G7 1800 DD", 2018, "mantenimiento"),
    ("M-14", "5390LSD", "Irizar", "i8 DD", 2024, "operativo"),
]

# Rotación: corredor -> (índice del primer bus). Cada horario de un corredor usa 2 buses.
CORREDORES = {"SCZ": 0, "TJA": 4, "LPZ": 8}
HORAS_SALIDA = ["18:30", "20:00"]
FECHA_REFERENCIA_ROTACION = date(2026, 1, 1)

# (placa, tipo, capacidad_kg, ciudad_base, lat, lon)
VEHICULOS = [
    ("2210GPS", "furgon", 3500, "SRE", -19.0282, -65.2478),
    ("2211GPS", "furgon", 3500, "SCZ", -17.7919, -63.1611),
    ("1780RPD", "furgoneta_reparto", 800, "SRE", -19.0431, -65.2592),
    ("1781RPD", "furgoneta_reparto", 800, "SCZ", -17.7834, -63.1821),
]

CARGO_EXCESO_EQUIPAJE = {"SCZ": 6, "TJA": 5, "LPZ": 5}  # Bs por kg, según corredor

# (ruta, ciudad, orden, km, minutos)
PARADAS = [
    ("SRE-TJA", "PTS", 1, 156, 180),
    ("SRE-TJA", "CMG", 2, 300, 390),
    ("TJA-SRE", "CMG", 1, 169, 270),
    ("TJA-SRE", "PTS", 2, 313, 480),
    ("SRE-LPZ", "EAT", 1, 540, 690),
    ("LPZ-SRE", "EAT", 1, 15, 30),
]

# corredor -> {clase: (precio, máximo referencial)}
TARIFAS_PASAJE = {
    "SCZ": {"SUITE_CAMA": (180, 210), "LEITO_CAMA": (150, 175)},
    "LPZ": {"SUITE_CAMA": (170, 195), "LEITO_CAMA": (140, 160)},
    "TJA": {"SUITE_CAMA": (150, 175), "LEITO_CAMA": (120, 140)},
}
TARIFAS_VIGENTES_DESDE = date(2026, 1, 1)
# Promoción de los martes en Sucre ↔ Santa Cruz (precios_salida)
PROMO_MARTES = {"SUITE_CAMA": 160, "LEITO_CAMA": 130}

# tipo -> (peso_min, peso_max, base, por kg adicional)
TARIFAS_CARGA = {
    "sobre": (0, 2, 15, 0),
    "paquete": (5, 30, 25, 3),
    "carga": (31, None, 120, 2.5),
}
RECARGO_PUERTA_A_PUERTA = 20

PARAMETROS = {
    "reserva_expira_minutos": (15, "Minutos para pagar una reserva antes de liberar los asientos", True),
    "reembolso_porcentaje_cliente": (85, "Porcentaje devuelto cuando el cliente pide el reembolso", False),
    "reembolso_horas_minimas": (2, "Horas mínimas antes de la salida para pedir reembolso", False),
    "reembolso_porcentaje_cancelacion_empresa": (100, "Porcentaje devuelto si la empresa cancela", False),
    "reembolso_dias_habiles_max": (7, "Plazo máximo del reembolso en días hábiles", False),
    "equipaje_bodega_kg": (20, "Franquicia de equipaje en buzón por pasajero", False),
    "equipaje_mano_kg": (5, "Máximo de equipaje de mano por pasajero", False),
    "embarazo_semanas_max": (30, "Semanas de gestación máximas para viajar", False),
    "puerta_a_puerta_peso_min_kg": (1, "Peso mínimo del servicio puerta a puerta", False),
    "puerta_a_puerta_costo_bs": (20, "Costo de una solicitud de recojo o entrega a domicilio", True),
    "encomienda_peso_max_paquete_kg": (30, "Peso máximo de sobres y paquetes; más es carga", False),
    "venta_anticipacion_max_dias": (30, "Días de anticipación máxima para vender", True),
    "venta_cierre_minutos_antes": (30, "La venta en línea cierra estos minutos antes de la salida", True),
    "boletos_max_por_venta": (6, "Boletos máximos por reserva", True),
}

FERIADOS = [
    (date(2026, 1, 1), "Año Nuevo", None),
    (date(2026, 1, 22), "Día del Estado Plurinacional", None),
    (date(2026, 2, 16), "Carnaval", None),
    (date(2026, 2, 17), "Carnaval", None),
    (date(2026, 4, 3), "Viernes Santo", None),
    (date(2026, 5, 1), "Día del Trabajo", None),
    (date(2026, 6, 4), "Corpus Christi", None),
    (date(2026, 6, 21), "Año Nuevo Andino Amazónico", None),
    (date(2026, 8, 6), "Día de la Independencia", None),
    (date(2026, 11, 2), "Día de Todos los Difuntos", None),
    (date(2026, 12, 25), "Navidad", None),
    (date(2027, 1, 1), "Año Nuevo", None),
    (date(2027, 1, 22), "Día del Estado Plurinacional", None),
    (date(2027, 2, 8), "Carnaval", None),
    (date(2027, 2, 9), "Carnaval", None),
    (date(2027, 3, 26), "Viernes Santo", None),
    (date(2027, 5, 1), "Día del Trabajo", None),
    (date(2027, 5, 27), "Corpus Christi", None),
    (date(2027, 6, 21), "Año Nuevo Andino Amazónico", None),
    (date(2027, 8, 6), "Día de la Independencia", None),
    (date(2027, 11, 2), "Día de Todos los Difuntos", None),
    (date(2027, 12, 25), "Navidad", None),
    (date(2026, 4, 15), "Aniversario de Tarija", "Tarija"),
    (date(2026, 5, 25), "Aniversario de Chuquisaca", "Chuquisaca"),
    (date(2026, 7, 16), "Aniversario de La Paz", "La Paz"),
    (date(2026, 9, 24), "Aniversario de Santa Cruz", "Santa Cruz"),
    (date(2026, 11, 10), "Aniversario de Potosí", "Potosí"),
    (date(2027, 4, 15), "Aniversario de Tarija", "Tarija"),
    (date(2027, 5, 25), "Aniversario de Chuquisaca", "Chuquisaca"),
    (date(2027, 7, 16), "Aniversario de La Paz", "La Paz"),
    (date(2027, 9, 24), "Aniversario de Santa Cruz", "Santa Cruz"),
    (date(2027, 11, 10), "Aniversario de Potosí", "Potosí"),
]

# (email, nombres, apellidos, rol, oficina, teléfono)
PERSONAL = [
    ("admin@elmexicanosrl.com", "Carlos", "Mendoza Arce", "admin", "SRE-BOL", "59170100001"),
    ("supervisor@elmexicanosrl.com", "Patricia", "Rojas Salinas", "supervisor", "SRE-BOL", "59170100002"),
    ("boleteria.sucre@elmexicanosrl.com", "Juan", "Pérez Calvimontes", "boletero", "SRE-BOL", "59170100003"),
    ("boleteria.santacruz@elmexicanosrl.com", "María", "Gutiérrez Añez", "boletero", "SCZ-BOL", "59170100004"),
    ("boleteria.lapaz@elmexicanosrl.com", "Luis", "Quispe Mamani", "boletero", "LPZ-BOL", "59170100005"),
    ("boleteria.tarija@elmexicanosrl.com", "Ana", "Vargas Castellanos", "boletero", "TJA-BOL", "59170100006"),
    ("bodega.sucre@elmexicanosrl.com", "Roberto", "Flores Torrico", "encargado_bodega", "SRE-BOD", "59170100007"),
    (
        "bodega.santacruz@elmexicanosrl.com",
        "Carmen",
        "Choque Justiniano",
        "encargado_bodega",
        "SCZ-BOD2",
        "59170100008",
    ),
    ("bodega.lapaz@elmexicanosrl.com", "Jorge", "Mamani Condori", "encargado_bodega", "LPZ-BOD", "59170100009"),
    ("reparto.sucre@elmexicanosrl.com", "Diego", "Arancibia Padilla", "repartidor", "SRE-BOD", "59170100010"),
    ("reparto.santacruz@elmexicanosrl.com", "Fernando", "Soliz Suárez", "repartidor", "SCZ-BOD2", "59170100011"),
    ("soporte@elmexicanosrl.com", "Lucía", "Zárate Villarroel", "soporte", "SRE-BOL", "59170100012"),
]

NOMBRES = [
    "Juan",
    "María",
    "José",
    "Ana",
    "Luis",
    "Carmen",
    "Carlos",
    "Rosa",
    "Jorge",
    "Lucía",
    "Miguel",
    "Patricia",
    "Fernando",
    "Gabriela",
    "Marco",
    "Verónica",
    "Álvaro",
    "Daniela",
    "Rodrigo",
    "Paola",
    "Sergio",
    "Mariela",
    "Wilson",
    "Ximena",
    "Edwin",
    "Roxana",
    "Ramiro",
    "Silvia",
    "Freddy",
    "Claudia",
    "Gonzalo",
    "Andrea",
    "Hugo",
    "Wendy",
    "Iván",
    "Jhoselin",
    "Marcelo",
    "Karina",
    "Óscar",
    "Nancy",
]
APELLIDOS = [
    "Mamani",
    "Quispe",
    "Flores",
    "Rodríguez",
    "Vargas",
    "Choque",
    "Gutiérrez",
    "Rojas",
    "Pérez",
    "Condori",
    "Fernández",
    "Mendoza",
    "Torrico",
    "Salazar",
    "Arce",
    "Zárate",
    "Villarroel",
    "Castellanos",
    "Justiniano",
    "Suárez",
    "Padilla",
    "Calvimontes",
    "Arancibia",
    "Soliz",
    "Añez",
    "Terrazas",
    "Paredes",
    "Céspedes",
    "Montaño",
    "Rivero",
    "Guzmán",
    "Poma",
    "Limachi",
    "Coca",
    "Aguilera",
    "Durán",
]
EXTENSIONES = ["CH", "SC", "LP", "TJ", "PT", "CB", "OR"]

CALLES_SUCRE = [
    "Calle Junín 450, zona Central",
    "Av. Hernando Siles 1220",
    "Calle Loa 780, zona San Roque",
    "Av. Las Américas 356",
    "Calle Ravelo 215",
]
CALLES_SANTA_CRUZ = [
    "Av. San Martín 1450, Equipetrol",
    "Calle Sucre 320, casco viejo",
    "Av. Banzer 4to anillo, calle 5 #88",
    "Av. Alemana 6to anillo, calle Los Pinos 12",
    "Calle Ñuflo de Chávez 145",
]

CUENTAS_CORPORATIVAS = [
    (
        "CORP001",
        "Distribuidora Andina S.R.L.",
        "3024581011",
        "Mónica Paredes",
        "59172100001",
        "compras@andina.demo",
        15000,
        30,
    ),
    (
        "CORP002",
        "Textiles Chuquisaca S.A.",
        "1029384020",
        "Raúl Terrazas",
        "59172100002",
        "logistica@texchuq.demo",
        8000,
        15,
    ),
    (
        "CORP003",
        "Agroexport Oriente S.R.L.",
        "4501928014",
        "Silvia Céspedes",
        "59172100003",
        "despachos@agroriente.demo",
        25000,
        30,
    ),
]

CONTENIDOS_ENCOMIENDA = [
    "Documentos",
    "Ropa y calzados",
    "Repuestos de vehículo",
    "Medicamentos",
    "Productos artesanales",
    "Libros",
    "Equipo electrónico",
    "Víveres",
    "Herramientas",
    "Material de escritorio",
    "Chocolates de Sucre",
    "Muestras comerciales",
]
CONTENIDOS_CARGA = ["Mudanza de departamento", "Maquinaria liviana", "Mercadería para tienda", "Muebles"]

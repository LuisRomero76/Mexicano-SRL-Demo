"""Vistas de PostgreSQL: SQL de creación (usado por la migración) y tablas de solo lectura.

Las tablas se declaran en un `MetaData` propio para que Alembic no intente crearlas.
"""

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    Uuid,
)

_TZ = "America/La_Paz"
_ACTIVOS = "('reservado', 'emitido', 'abordado')"
_DIAS = "ARRAY['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']"

V_SALIDAS_DISPONIBLES_SQL = f"""
CREATE OR REPLACE VIEW v_salidas_disponibles AS
SELECT
    s.id AS salida_id,
    s.codigo,
    s.estado,
    s.fecha_hora_salida,
    s.fecha_hora_llegada_estimada,
    s.minutos_demora,
    s.anden,
    r.id AS ruta_id,
    r.codigo AS ruta_codigo,
    co.nombre AS origen,
    cd.nombre AS destino,
    b.id AS bus_id,
    b.numero_interno AS bus_numero_interno,
    ta.id AS tipo_asiento_id,
    ta.codigo AS tipo_asiento_codigo,
    ta.nombre AS tipo_asiento,
    COALESCE(ps.precio_bs, t.precio_bs) AS precio_bs,
    t.precio_maximo_referencial_bs,
    COUNT(a.id) FILTER (WHERE a.habilitado) AS asientos_total,
    COUNT(bo.id) FILTER (WHERE a.habilitado) AS asientos_ocupados,
    COUNT(a.id) FILTER (WHERE a.habilitado) - COUNT(bo.id) FILTER (WHERE a.habilitado) AS asientos_libres
FROM salidas s
JOIN rutas r ON r.id = s.ruta_id
JOIN ciudades co ON co.id = r.origen_ciudad_id
JOIN ciudades cd ON cd.id = r.destino_ciudad_id
JOIN buses b ON b.id = s.bus_id
JOIN asientos a ON a.bus_id = b.id
JOIN tipos_asiento ta ON ta.id = a.tipo_asiento_id
LEFT JOIN boletos bo
    ON bo.salida_id = s.id AND bo.numero_asiento = a.numero AND bo.estado IN {_ACTIVOS}
LEFT JOIN precios_salida ps ON ps.salida_id = s.id AND ps.tipo_asiento_id = ta.id
LEFT JOIN LATERAL (
    SELECT tp.precio_bs, tp.precio_maximo_referencial_bs
    FROM tarifas_pasaje tp
    WHERE tp.ruta_id = r.id
      AND tp.tipo_asiento_id = ta.id
      AND tp.vigente_desde <= (s.fecha_hora_salida AT TIME ZONE '{_TZ}')::date
      AND (tp.vigente_hasta IS NULL OR tp.vigente_hasta >= (s.fecha_hora_salida AT TIME ZONE '{_TZ}')::date)
    ORDER BY tp.vigente_desde DESC
    LIMIT 1
) t ON true
GROUP BY s.id, r.id, co.nombre, cd.nombre, b.id, ta.id, ps.precio_bs, t.precio_bs, t.precio_maximo_referencial_bs
"""

V_ENCOMIENDA_RASTREO_SQL = """
CREATE OR REPLACE VIEW v_encomienda_rastreo AS
SELECT
    e.id AS encomienda_id,
    e.numero_guia,
    e.tipo_envio,
    e.estado,
    e.modalidad_entrega,
    e.pago_en,
    e.estado_pago,
    e.peso_kg,
    e.cantidad_bultos,
    e.fecha_registro,
    e.fecha_estimada_entrega,
    e.fecha_entrega,
    co.nombre AS ciudad_origen,
    oo.nombre AS oficina_origen,
    cd.nombre AS ciudad_destino,
    od.id AS oficina_destino_id,
    od.nombre AS oficina_destino,
    od.direccion AS oficina_destino_direccion,
    od.telefono_e164 AS oficina_destino_telefono_e164,
    ue.estado AS ultimo_evento_estado,
    ue.descripcion AS ultimo_evento_descripcion,
    ue.ocurrido_at AS ultimo_evento_at
FROM encomiendas e
JOIN oficinas oo ON oo.id = e.oficina_origen_id
JOIN ciudades co ON co.id = oo.ciudad_id
JOIN oficinas od ON od.id = e.oficina_destino_id
JOIN ciudades cd ON cd.id = od.ciudad_id
LEFT JOIN LATERAL (
    SELECT ev.estado, ev.descripcion, ev.ocurrido_at
    FROM encomienda_eventos ev
    WHERE ev.encomienda_id = e.id AND ev.visible_cliente
    ORDER BY ev.ocurrido_at DESC, ev.id DESC
    LIMIT 1
) ue ON true
"""

V_OFICINAS_CON_HORARIO_SQL = f"""
CREATE OR REPLACE VIEW v_oficinas_con_horario AS
WITH grupos AS (
    SELECT oficina_id, hora_apertura, hora_cierre,
           array_agg(dia_semana ORDER BY dia_semana) AS dias,
           min(dia_semana) AS dmin, max(dia_semana) AS dmax, count(*) AS n
    FROM horarios_oficina
    GROUP BY oficina_id, hora_apertura, hora_cierre
),
tramos AS (
    SELECT oficina_id, dmin, hora_apertura,
        CASE WHEN n > 1 AND n = dmax - dmin + 1
             THEN ({_DIAS})[dmin] || '–' || ({_DIAS})[dmax]
             ELSE (SELECT string_agg(({_DIAS})[d], ', ') FROM unnest(dias) AS d)
        END || ' ' || left(hora_apertura::text, 5) || '–' || left(hora_cierre::text, 5) AS tramo
    FROM grupos
)
SELECT
    o.id AS oficina_id,
    o.codigo,
    o.nombre,
    o.tipo,
    c.id AS ciudad_id,
    c.nombre AS ciudad,
    o.direccion,
    o.referencia,
    o.telefono_e164,
    o.whatsapp_e164,
    o.url_mapa,
    (SELECT string_agg(t.tramo, '; ' ORDER BY t.dmin, t.hora_apertura)
     FROM tramos t WHERE t.oficina_id = o.id) AS horario_texto
FROM oficinas o
JOIN ciudades c ON c.id = o.ciudad_id
WHERE o.activo
"""

VIEWS_SQL = [V_SALIDAS_DISPONIBLES_SQL, V_ENCOMIENDA_RASTREO_SQL, V_OFICINAS_CON_HORARIO_SQL]
VIEW_NAMES = ["v_salidas_disponibles", "v_encomienda_rastreo", "v_oficinas_con_horario"]

SEQUENCES = {
    "seq_numero_boleto": 26001000,
    "seq_numero_guia": 26001000,
    "seq_numero_factura": 1000,
    "seq_solicitud_puerta": 1000,
}

SET_UPDATED_AT_FN = """
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
"""

# --- Tablas de solo lectura sobre las vistas --------------------------------------------------

vistas_metadata = MetaData()

v_salidas_disponibles = Table(
    "v_salidas_disponibles",
    vistas_metadata,
    Column("salida_id", Uuid, primary_key=True),
    Column("codigo", String),
    Column("estado", String),
    Column("fecha_hora_salida", DateTime(timezone=True)),
    Column("fecha_hora_llegada_estimada", DateTime(timezone=True)),
    Column("minutos_demora", SmallInteger),
    Column("anden", String),
    Column("ruta_id", Integer),
    Column("ruta_codigo", String),
    Column("origen", String),
    Column("destino", String),
    Column("bus_id", Integer),
    Column("bus_numero_interno", String),
    Column("tipo_asiento_id", SmallInteger, primary_key=True),
    Column("tipo_asiento_codigo", String),
    Column("tipo_asiento", String),
    Column("precio_bs", Numeric(10, 2)),
    Column("precio_maximo_referencial_bs", Numeric(10, 2)),
    Column("asientos_total", Integer),
    Column("asientos_ocupados", Integer),
    Column("asientos_libres", Integer),
)

v_encomienda_rastreo = Table(
    "v_encomienda_rastreo",
    vistas_metadata,
    Column("encomienda_id", Uuid, primary_key=True),
    Column("numero_guia", String),
    Column("tipo_envio", String),
    Column("estado", String),
    Column("modalidad_entrega", String),
    Column("pago_en", String),
    Column("estado_pago", String),
    Column("peso_kg", Numeric(7, 2)),
    Column("cantidad_bultos", SmallInteger),
    Column("fecha_registro", DateTime(timezone=True)),
    Column("fecha_estimada_entrega", DateTime(timezone=True)),
    Column("fecha_entrega", DateTime(timezone=True)),
    Column("ciudad_origen", String),
    Column("oficina_origen", String),
    Column("ciudad_destino", String),
    Column("oficina_destino_id", Integer),
    Column("oficina_destino", String),
    Column("oficina_destino_direccion", String),
    Column("oficina_destino_telefono_e164", String),
    Column("ultimo_evento_estado", String),
    Column("ultimo_evento_descripcion", String),
    Column("ultimo_evento_at", DateTime(timezone=True)),
)

v_oficinas_con_horario = Table(
    "v_oficinas_con_horario",
    vistas_metadata,
    Column("oficina_id", Integer, primary_key=True),
    Column("codigo", String),
    Column("nombre", String),
    Column("tipo", String),
    Column("ciudad_id", SmallInteger),
    Column("ciudad", String),
    Column("direccion", String),
    Column("referencia", String),
    Column("telefono_e164", String),
    Column("whatsapp_e164", String),
    Column("url_mapa", String),
    Column("horario_texto", Text),
)

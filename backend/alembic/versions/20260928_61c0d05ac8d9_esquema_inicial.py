"""esquema inicial

Revision ID: 61c0d05ac8d9
Revises: 
Create Date: 2026-09-28 20:06:45.636131

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '61c0d05ac8d9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# SQL copiado aquí a propósito: la migración no debe cambiar si cambia el código de la app.
SET_UPDATED_AT_FN = '''
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
'''

SEQUENCES = {'seq_numero_boleto': 26001000, 'seq_numero_guia': 26001000, 'seq_numero_factura': 1000, 'seq_solicitud_puerta': 1000}

VIEW_NAMES = ['v_salidas_disponibles', 'v_encomienda_rastreo', 'v_oficinas_con_horario']

VIEWS_SQL = [
    '''
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
    ON bo.salida_id = s.id AND bo.numero_asiento = a.numero AND bo.estado IN ('reservado', 'emitido', 'abordado')
LEFT JOIN precios_salida ps ON ps.salida_id = s.id AND ps.tipo_asiento_id = ta.id
LEFT JOIN LATERAL (
    SELECT tp.precio_bs, tp.precio_maximo_referencial_bs
    FROM tarifas_pasaje tp
    WHERE tp.ruta_id = r.id
      AND tp.tipo_asiento_id = ta.id
      AND tp.vigente_desde <= (s.fecha_hora_salida AT TIME ZONE 'America/La_Paz')::date
      AND (tp.vigente_hasta IS NULL OR tp.vigente_hasta >= (s.fecha_hora_salida AT TIME ZONE 'America/La_Paz')::date)
    ORDER BY tp.vigente_desde DESC
    LIMIT 1
) t ON true
GROUP BY s.id, r.id, co.nombre, cd.nombre, b.id, ta.id, ps.precio_bs, t.precio_bs, t.precio_maximo_referencial_bs
''',
    '''
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
''',
    '''
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
             THEN (ARRAY['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'])[dmin] || '–' || (ARRAY['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'])[dmax]
             ELSE (SELECT string_agg((ARRAY['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'])[d], ', ') FROM unnest(dias) AS d)
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
''',
]

CANAL_VENTA_ENUM = postgresql.ENUM('web', 'app_movil', 'boleteria', 'whatsapp_chat', 'whatsapp_llamada', 'telefono', name='canal_venta', create_type=False)
ESTADO_BOLETO_ENUM = postgresql.ENUM('reservado', 'emitido', 'abordado', 'cancelado', 'reembolsado', 'cambiado', 'no_show', name='estado_boleto', create_type=False)
ESTADO_BUS_ENUM = postgresql.ENUM('operativo', 'mantenimiento', 'fuera_de_servicio', name='estado_bus', create_type=False)
ESTADO_ENCOMIENDA_ENUM = postgresql.ENUM('registrada', 'recibida_en_origen', 'en_transito', 'llegada_a_destino', 'lista_para_retiro', 'en_reparto', 'entregada', 'intento_fallido', 'devuelta', 'cancelada', name='estado_encomienda', create_type=False)
ESTADO_FACTURA_ENUM = postgresql.ENUM('valida', 'anulada', name='estado_factura', create_type=False)
ESTADO_PAGO_ENUM = postgresql.ENUM('pendiente', 'aprobado', 'rechazado', 'reembolsado', 'anulado', name='estado_pago', create_type=False)
ESTADO_REEMBOLSO_ENUM = postgresql.ENUM('solicitado', 'aprobado', 'rechazado', 'pagado', name='estado_reembolso', create_type=False)
ESTADO_SALIDA_ENUM = postgresql.ENUM('programada', 'abordando', 'en_ruta', 'demorada', 'llegada', 'cancelada', name='estado_salida', create_type=False)
ESTADO_SOLICITUD_PUERTA_ENUM = postgresql.ENUM('solicitada', 'confirmada', 'en_camino', 'completada', 'cancelada', 'fallida', name='estado_solicitud_puerta', create_type=False)
ESTADO_VENTA_ENUM = postgresql.ENUM('pendiente_pago', 'pagada', 'cancelada', 'expirada', 'reembolsada_parcial', 'reembolsada', name='estado_venta', create_type=False)
FRANJA_HORARIA_ENUM = postgresql.ENUM('manana_08_12', 'tarde_14_17', name='franja_horaria', create_type=False)
METODO_PAGO_ENUM = postgresql.ENUM('qr', 'tarjeta_debito', 'tarjeta_credito', 'tigo_money', 'efectivo', 'credito_corporativo', name='metodo_pago', create_type=False)
MODALIDAD_ENTREGA_ENUM = postgresql.ENUM('retiro_en_oficina', 'puerta_a_puerta', name='modalidad_entrega', create_type=False)
ORIGEN_REEMBOLSO_ENUM = postgresql.ENUM('solicitud_cliente', 'cancelacion_empresa', name='origen_reembolso', create_type=False)
PAGO_EN_ENUM = postgresql.ENUM('origen', 'destino', 'credito_corporativo', name='pago_en', create_type=False)
PLANTA_BUS_ENUM = postgresql.ENUM('alta', 'baja', name='planta_bus', create_type=False)
POSICION_ASIENTO_ENUM = postgresql.ENUM('ventana', 'pasillo', 'centro', name='posicion_asiento', create_type=False)
ROL_TRIPULACION_ENUM = postgresql.ENUM('conductor', 'conductor_relevo', 'ayudante', name='rol_tripulacion', create_type=False)
ROL_USUARIO_ENUM = postgresql.ENUM('admin', 'supervisor', 'boletero', 'encargado_bodega', 'repartidor', 'conductor', 'soporte', name='rol_usuario', create_type=False)
SERVICIO_OFICINA_ENUM = postgresql.ENUM('boleteria', 'carga', 'general', name='servicio_oficina', create_type=False)
TIPO_DOCUMENTO_ENUM = postgresql.ENUM('ci', 'pasaporte', 'nit', 'carnet_extranjero', 'otro', name='tipo_documento', create_type=False)
TIPO_ENVIO_ENUM = postgresql.ENUM('sobre', 'paquete', 'carga', name='tipo_envio', create_type=False)
TIPO_EQUIPAJE_ENUM = postgresql.ENUM('bodega', 'mano', name='tipo_equipaje', create_type=False)
TIPO_OFICINA_ENUM = postgresql.ENUM('boleteria', 'bodega_carga', 'mixta', name='tipo_oficina', create_type=False)
TIPO_PASAJERO_ENUM = postgresql.ENUM('adulto', 'menor', 'adulto_mayor', 'persona_con_discapacidad', 'embarazada', name='tipo_pasajero', create_type=False)
TIPO_SOLICITUD_PUERTA_ENUM = postgresql.ENUM('recojo', 'entrega', name='tipo_solicitud_puerta', create_type=False)
TIPO_VEHICULO_CARGA_ENUM = postgresql.ENUM('furgon', 'camion', 'furgoneta_reparto', name='tipo_vehiculo_carga', create_type=False)

ENUMS = [CANAL_VENTA_ENUM, ESTADO_BOLETO_ENUM, ESTADO_BUS_ENUM, ESTADO_ENCOMIENDA_ENUM, ESTADO_FACTURA_ENUM, ESTADO_PAGO_ENUM, ESTADO_REEMBOLSO_ENUM, ESTADO_SALIDA_ENUM, ESTADO_SOLICITUD_PUERTA_ENUM, ESTADO_VENTA_ENUM, FRANJA_HORARIA_ENUM, METODO_PAGO_ENUM, MODALIDAD_ENTREGA_ENUM, ORIGEN_REEMBOLSO_ENUM, PAGO_EN_ENUM, PLANTA_BUS_ENUM, POSICION_ASIENTO_ENUM, ROL_TRIPULACION_ENUM, ROL_USUARIO_ENUM, SERVICIO_OFICINA_ENUM, TIPO_DOCUMENTO_ENUM, TIPO_ENVIO_ENUM, TIPO_EQUIPAJE_ENUM, TIPO_OFICINA_ENUM, TIPO_PASAJERO_ENUM, TIPO_SOLICITUD_PUERTA_ENUM, TIPO_VEHICULO_CARGA_ENUM]

TABLAS_CON_UPDATED_AT = ['buses', 'ciudades', 'comodidades', 'cuentas_corporativas', 'empresa', 'faq_categorias', 'feriados', 'paginas_contenido', 'parametros_negocio', 'politicas_tipo_pasajero', 'tipos_asiento', 'asientos', 'clientes', 'faqs', 'oficinas', 'rutas', 'tarifas_carga', 'vehiculos_carga', 'horarios_oficina', 'plantillas_horario', 'ruta_paradas', 'tarifas_pasaje', 'usuarios', 'salidas', 'ventas_pasaje', 'boletos', 'encomiendas', 'precios_salida', 'salida_tripulacion', 'equipajes', 'solicitudes_puerta_a_puerta', 'pagos', 'facturas', 'reembolsos']


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for enum in ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table('buses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('numero_interno', sa.String(length=10), nullable=False),
    sa.Column('placa', sa.String(length=10), nullable=False),
    sa.Column('marca', sa.String(length=40), nullable=True),
    sa.Column('modelo', sa.String(length=60), nullable=True),
    sa.Column('anio', sa.SmallInteger(), nullable=True),
    sa.Column('pisos', sa.SmallInteger(), server_default='2', nullable=False),
    sa.Column('capacidad_total', sa.SmallInteger(), nullable=False),
    sa.Column('estado', ESTADO_BUS_ENUM, server_default='operativo', nullable=False),
    sa.Column('gps_dispositivo_id', sa.String(length=50), nullable=True),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('anio BETWEEN 1990 AND 2100', name=op.f('ck_buses_anio_valido')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_buses')),
    sa.UniqueConstraint('numero_interno', name=op.f('uq_buses_numero_interno')),
    sa.UniqueConstraint('placa', name=op.f('uq_buses_placa'))
    )
    op.create_table('ciudades',
    sa.Column('id', sa.SmallInteger(), autoincrement=True, nullable=False),
    sa.Column('codigo', sa.String(length=3), nullable=False),
    sa.Column('nombre', sa.String(length=60), nullable=False),
    sa.Column('departamento', sa.String(length=40), nullable=False),
    sa.Column('es_destino_pasajeros', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('es_destino_carga', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('tiene_puerta_a_puerta', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('whatsapp_puerta_a_puerta_e164', sa.String(length=15), nullable=True),
    sa.Column('alias_busqueda', postgresql.ARRAY(sa.Text()), nullable=True),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ciudades')),
    sa.UniqueConstraint('codigo', name=op.f('uq_ciudades_codigo')),
    sa.UniqueConstraint('nombre', name=op.f('uq_ciudades_nombre'))
    )
    op.create_table('comodidades',
    sa.Column('id', sa.SmallInteger(), autoincrement=True, nullable=False),
    sa.Column('codigo', sa.String(length=30), nullable=False),
    sa.Column('nombre', sa.String(length=60), nullable=False),
    sa.Column('icono', sa.String(length=40), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_comodidades')),
    sa.UniqueConstraint('codigo', name=op.f('uq_comodidades_codigo'))
    )
    op.create_table('cuentas_corporativas',
    sa.Column('codigo', sa.String(length=10), nullable=False),
    sa.Column('razon_social', sa.String(length=150), nullable=False),
    sa.Column('nit', sa.String(length=20), nullable=False),
    sa.Column('contacto_nombre', sa.String(length=100), nullable=True),
    sa.Column('contacto_telefono_e164', sa.String(length=15), nullable=True),
    sa.Column('contacto_email', sa.String(length=150), nullable=True),
    sa.Column('limite_credito_bs', sa.Numeric(precision=12, scale=2), server_default='0', nullable=False),
    sa.Column('saldo_pendiente_bs', sa.Numeric(precision=12, scale=2), server_default='0', nullable=False),
    sa.Column('dias_credito', sa.SmallInteger(), server_default='30', nullable=False),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cuentas_corporativas')),
    sa.UniqueConstraint('codigo', name=op.f('uq_cuentas_corporativas_codigo')),
    sa.UniqueConstraint('nit', name=op.f('uq_cuentas_corporativas_nit'))
    )
    op.create_table('empresa',
    sa.Column('id', sa.SmallInteger(), nullable=False),
    sa.Column('razon_social', sa.String(length=150), nullable=False),
    sa.Column('nombre_comercial', sa.String(length=100), nullable=False),
    sa.Column('nit', sa.String(length=20), nullable=True),
    sa.Column('ente_regulador', sa.String(length=200), nullable=True),
    sa.Column('sitio_web', sa.String(length=200), nullable=True),
    sa.Column('url_compra_pasajes', sa.String(length=300), nullable=True),
    sa.Column('url_rastreo_carga', sa.String(length=300), nullable=True),
    sa.Column('facebook_url', sa.String(length=300), nullable=True),
    sa.Column('email_contacto', sa.String(length=150), nullable=True),
    sa.Column('telefono_central_e164', sa.String(length=15), nullable=True),
    sa.Column('telefono_atencion_cliente_e164', sa.String(length=15), nullable=True),
    sa.Column('whatsapp_central_e164', sa.String(length=15), nullable=True),
    sa.Column('color_marca', sa.String(length=7), nullable=True),
    sa.Column('eslogan', sa.String(length=200), nullable=True),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('terminos_condiciones', sa.Text(), nullable=True),
    sa.Column('moneda', sa.String(length=3), server_default='BOB', nullable=False),
    sa.Column('zona_horaria', sa.String(length=40), server_default='America/La_Paz', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('id = 1', name=op.f('ck_empresa_fila_unica')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_empresa'))
    )
    op.create_table('faq_categorias',
    sa.Column('id', sa.SmallInteger(), autoincrement=True, nullable=False),
    sa.Column('codigo', sa.String(length=30), nullable=False),
    sa.Column('nombre', sa.String(length=60), nullable=False),
    sa.Column('orden', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_faq_categorias')),
    sa.UniqueConstraint('codigo', name=op.f('uq_faq_categorias_codigo'))
    )
    op.create_table('feriados',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.Date(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('departamento', sa.String(length=40), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_feriados')),
    sa.UniqueConstraint('fecha', 'departamento', name=op.f('uq_feriados_fecha_departamento'), postgresql_nulls_not_distinct=True)
    )
    op.create_table('paginas_contenido',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=60), nullable=False),
    sa.Column('titulo', sa.String(length=150), nullable=False),
    sa.Column('meta_descripcion', sa.String(length=300), nullable=True),
    sa.Column('contenido_md', sa.Text(), nullable=False),
    sa.Column('url_original', sa.String(length=300), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_paginas_contenido')),
    sa.UniqueConstraint('slug', name=op.f('uq_paginas_contenido_slug'))
    )
    op.create_table('parametros_negocio',
    sa.Column('clave', sa.String(length=60), nullable=False),
    sa.Column('valor', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('descripcion', sa.String(length=250), nullable=True),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('clave', name=op.f('pk_parametros_negocio'))
    )
    op.create_table('politicas_tipo_pasajero',
    sa.Column('tipo_pasajero', TIPO_PASAJERO_ENUM, nullable=False),
    sa.Column('nombre', sa.String(length=60), nullable=False),
    sa.Column('descuento_porcentaje', sa.Numeric(precision=5, scale=2), server_default='0', nullable=False),
    sa.Column('solo_boleteria', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('edad_min', sa.SmallInteger(), nullable=True),
    sa.Column('edad_max', sa.SmallInteger(), nullable=True),
    sa.Column('requisito', sa.String(length=250), nullable=True),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('descuento_porcentaje BETWEEN 0 AND 100', name=op.f('ck_politicas_tipo_pasajero_descuento_valido')),
    sa.PrimaryKeyConstraint('tipo_pasajero', name=op.f('pk_politicas_tipo_pasajero'))
    )
    op.create_table('tipos_asiento',
    sa.Column('id', sa.SmallInteger(), autoincrement=True, nullable=False),
    sa.Column('codigo', sa.String(length=20), nullable=False),
    sa.Column('nombre', sa.String(length=50), nullable=False),
    sa.Column('planta', PLANTA_BUS_ENUM, nullable=False),
    sa.Column('inclinacion_grados', sa.SmallInteger(), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('orden', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tipos_asiento')),
    sa.UniqueConstraint('codigo', name=op.f('uq_tipos_asiento_codigo'))
    )
    op.create_table('asientos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('bus_id', sa.Integer(), nullable=False),
    sa.Column('numero', sa.SmallInteger(), nullable=False),
    sa.Column('tipo_asiento_id', sa.SmallInteger(), nullable=False),
    sa.Column('planta', PLANTA_BUS_ENUM, nullable=False),
    sa.Column('fila', sa.SmallInteger(), nullable=False),
    sa.Column('columna', sa.SmallInteger(), nullable=False),
    sa.Column('posicion', POSICION_ASIENTO_ENUM, nullable=False),
    sa.Column('habilitado', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['bus_id'], ['buses.id'], name=op.f('fk_asientos_bus_id_buses'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tipo_asiento_id'], ['tipos_asiento.id'], name=op.f('fk_asientos_tipo_asiento_id_tipos_asiento')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_asientos')),
    sa.UniqueConstraint('bus_id', 'numero', name=op.f('uq_asientos_bus_id_numero'))
    )
    op.create_table('clientes',
    sa.Column('tipo_documento', TIPO_DOCUMENTO_ENUM, server_default='ci', nullable=False),
    sa.Column('numero_documento', sa.String(length=20), nullable=False),
    sa.Column('complemento', sa.String(length=5), nullable=True),
    sa.Column('extension', sa.String(length=3), nullable=True),
    sa.Column('nombres', sa.String(length=80), nullable=False),
    sa.Column('apellidos', sa.String(length=80), nullable=False),
    sa.Column('fecha_nacimiento', sa.Date(), nullable=True),
    sa.Column('telefono_e164', sa.String(length=15), nullable=True),
    sa.Column('email', sa.String(length=150), nullable=True),
    sa.Column('nit_facturacion', sa.String(length=20), nullable=True),
    sa.Column('razon_social_facturacion', sa.String(length=150), nullable=True),
    sa.Column('cuenta_corporativa_id', sa.Uuid(), nullable=True),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['cuenta_corporativa_id'], ['cuentas_corporativas.id'], name=op.f('fk_clientes_cuenta_corporativa_id_cuentas_corporativas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clientes')),
    sa.UniqueConstraint('tipo_documento', 'numero_documento', 'complemento', name=op.f('uq_clientes_tipo_documento_numero_documento_complemento'), postgresql_nulls_not_distinct=True)
    )
    op.create_index(op.f('ix_clientes_telefono_e164'), 'clientes', ['telefono_e164'], unique=False)
    op.create_table('faqs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('categoria_id', sa.SmallInteger(), nullable=False),
    sa.Column('slug', sa.String(length=60), nullable=False),
    sa.Column('pregunta', sa.String(length=200), nullable=False),
    sa.Column('respuesta', sa.Text(), nullable=False),
    sa.Column('respuesta_corta_voz', sa.String(length=400), nullable=True),
    sa.Column('palabras_clave', postgresql.ARRAY(sa.Text()), nullable=True),
    sa.Column('orden', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['categoria_id'], ['faq_categorias.id'], name=op.f('fk_faqs_categoria_id_faq_categorias')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_faqs')),
    sa.UniqueConstraint('slug', name=op.f('uq_faqs_slug'))
    )
    op.create_index('ix_faqs_fts', 'faqs', [sa.literal_column("to_tsvector('spanish', pregunta || ' ' || respuesta)")], unique=False, postgresql_using='gin')
    op.create_table('oficinas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ciudad_id', sa.SmallInteger(), nullable=False),
    sa.Column('codigo', sa.String(length=10), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('tipo', TIPO_OFICINA_ENUM, nullable=False),
    sa.Column('direccion', sa.String(length=250), nullable=False),
    sa.Column('referencia', sa.String(length=250), nullable=True),
    sa.Column('telefono_e164', sa.String(length=15), nullable=True),
    sa.Column('whatsapp_e164', sa.String(length=15), nullable=True),
    sa.Column('email', sa.String(length=150), nullable=True),
    sa.Column('latitud', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('longitud', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('url_mapa', sa.String(length=300), nullable=True),
    sa.Column('es_principal', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['ciudad_id'], ['ciudades.id'], name=op.f('fk_oficinas_ciudad_id_ciudades')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_oficinas')),
    sa.UniqueConstraint('codigo', name=op.f('uq_oficinas_codigo'))
    )
    op.create_index(op.f('ix_oficinas_ciudad_id'), 'oficinas', ['ciudad_id'], unique=False)
    op.create_index(op.f('ix_oficinas_tipo'), 'oficinas', ['tipo'], unique=False)
    op.create_table('rutas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(length=10), nullable=False),
    sa.Column('origen_ciudad_id', sa.SmallInteger(), nullable=False),
    sa.Column('destino_ciudad_id', sa.SmallInteger(), nullable=False),
    sa.Column('distancia_km', sa.SmallInteger(), nullable=False),
    sa.Column('duracion_estimada_min', sa.SmallInteger(), nullable=False),
    sa.Column('cargo_exceso_equipaje_kg_bs', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
    sa.Column('descripcion', sa.String(length=250), nullable=True),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('origen_ciudad_id <> destino_ciudad_id', name=op.f('ck_rutas_origen_distinto_destino')),
    sa.ForeignKeyConstraint(['destino_ciudad_id'], ['ciudades.id'], name=op.f('fk_rutas_destino_ciudad_id_ciudades')),
    sa.ForeignKeyConstraint(['origen_ciudad_id'], ['ciudades.id'], name=op.f('fk_rutas_origen_ciudad_id_ciudades')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rutas')),
    sa.UniqueConstraint('codigo', name=op.f('uq_rutas_codigo')),
    sa.UniqueConstraint('origen_ciudad_id', 'destino_ciudad_id', name=op.f('uq_rutas_origen_ciudad_id_destino_ciudad_id'))
    )
    op.create_table('tarifas_carga',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('origen_ciudad_id', sa.SmallInteger(), nullable=False),
    sa.Column('destino_ciudad_id', sa.SmallInteger(), nullable=False),
    sa.Column('tipo_envio', TIPO_ENVIO_ENUM, nullable=False),
    sa.Column('peso_min_kg', sa.Numeric(precision=7, scale=2), nullable=False),
    sa.Column('peso_max_kg', sa.Numeric(precision=7, scale=2), nullable=True),
    sa.Column('precio_base_bs', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('precio_kg_adicional_bs', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
    sa.Column('recargo_puerta_a_puerta_bs', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
    sa.Column('vigente_desde', sa.Date(), nullable=False),
    sa.Column('vigente_hasta', sa.Date(), nullable=True),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('peso_max_kg IS NULL OR peso_max_kg >= peso_min_kg', name=op.f('ck_tarifas_carga_rango_peso')),
    sa.ForeignKeyConstraint(['destino_ciudad_id'], ['ciudades.id'], name=op.f('fk_tarifas_carga_destino_ciudad_id_ciudades')),
    sa.ForeignKeyConstraint(['origen_ciudad_id'], ['ciudades.id'], name=op.f('fk_tarifas_carga_origen_ciudad_id_ciudades')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tarifas_carga')),
    sa.UniqueConstraint('origen_ciudad_id', 'destino_ciudad_id', 'tipo_envio', 'peso_min_kg', 'vigente_desde', name=op.f('uq_tarifas_carga_origen_ciudad_id_destino_ciudad_id_tipo_envio_peso_min_kg_vigente_desde'))
    )
    op.create_table('tipo_asiento_comodidades',
    sa.Column('tipo_asiento_id', sa.SmallInteger(), nullable=False),
    sa.Column('comodidad_id', sa.SmallInteger(), nullable=False),
    sa.ForeignKeyConstraint(['comodidad_id'], ['comodidades.id'], name=op.f('fk_tipo_asiento_comodidades_comodidad_id_comodidades'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tipo_asiento_id'], ['tipos_asiento.id'], name=op.f('fk_tipo_asiento_comodidades_tipo_asiento_id_tipos_asiento'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('tipo_asiento_id', 'comodidad_id', name=op.f('pk_tipo_asiento_comodidades'))
    )
    op.create_table('vehiculos_carga',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('placa', sa.String(length=10), nullable=False),
    sa.Column('tipo', TIPO_VEHICULO_CARGA_ENUM, nullable=False),
    sa.Column('capacidad_kg', sa.Integer(), nullable=False),
    sa.Column('ciudad_base_id', sa.SmallInteger(), nullable=True),
    sa.Column('gps_dispositivo_id', sa.String(length=50), nullable=True),
    sa.Column('ultima_latitud', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('ultima_longitud', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('ultima_posicion_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['ciudad_base_id'], ['ciudades.id'], name=op.f('fk_vehiculos_carga_ciudad_base_id_ciudades')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_vehiculos_carga')),
    sa.UniqueConstraint('placa', name=op.f('uq_vehiculos_carga_placa'))
    )
    op.create_table('horarios_oficina',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('oficina_id', sa.Integer(), nullable=False),
    sa.Column('servicio', SERVICIO_OFICINA_ENUM, server_default='general', nullable=False),
    sa.Column('dia_semana', sa.SmallInteger(), nullable=False),
    sa.Column('hora_apertura', sa.Time(), nullable=False),
    sa.Column('hora_cierre', sa.Time(), nullable=False),
    sa.Column('observacion', sa.String(length=150), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('dia_semana BETWEEN 1 AND 7', name=op.f('ck_horarios_oficina_dia_semana_valido')),
    sa.CheckConstraint('hora_cierre > hora_apertura', name=op.f('ck_horarios_oficina_rango_horas')),
    sa.ForeignKeyConstraint(['oficina_id'], ['oficinas.id'], name=op.f('fk_horarios_oficina_oficina_id_oficinas'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_horarios_oficina')),
    sa.UniqueConstraint('oficina_id', 'servicio', 'dia_semana', 'hora_apertura', name=op.f('uq_horarios_oficina_oficina_id_servicio_dia_semana_hora_apertura'))
    )
    op.create_table('plantillas_horario',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ruta_id', sa.Integer(), nullable=False),
    sa.Column('hora_salida', sa.Time(), nullable=False),
    sa.Column('dias_semana', postgresql.ARRAY(sa.SmallInteger()), server_default=sa.text("'{1,2,3,4,5,6,7}'"), nullable=False),
    sa.Column('oficina_salida_id', sa.Integer(), nullable=True),
    sa.Column('vigente_desde', sa.Date(), nullable=False),
    sa.Column('vigente_hasta', sa.Date(), nullable=True),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['oficina_salida_id'], ['oficinas.id'], name=op.f('fk_plantillas_horario_oficina_salida_id_oficinas')),
    sa.ForeignKeyConstraint(['ruta_id'], ['rutas.id'], name=op.f('fk_plantillas_horario_ruta_id_rutas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_plantillas_horario')),
    sa.UniqueConstraint('ruta_id', 'hora_salida', 'vigente_desde', name=op.f('uq_plantillas_horario_ruta_id_hora_salida_vigente_desde'))
    )
    op.create_table('ruta_paradas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ruta_id', sa.Integer(), nullable=False),
    sa.Column('ciudad_id', sa.SmallInteger(), nullable=False),
    sa.Column('orden', sa.SmallInteger(), nullable=False),
    sa.Column('km_desde_origen', sa.SmallInteger(), nullable=False),
    sa.Column('minutos_desde_origen', sa.SmallInteger(), nullable=False),
    sa.Column('permite_carga', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('permite_pasajeros', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['ciudad_id'], ['ciudades.id'], name=op.f('fk_ruta_paradas_ciudad_id_ciudades')),
    sa.ForeignKeyConstraint(['ruta_id'], ['rutas.id'], name=op.f('fk_ruta_paradas_ruta_id_rutas'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ruta_paradas')),
    sa.UniqueConstraint('ruta_id', 'ciudad_id', name=op.f('uq_ruta_paradas_ruta_id_ciudad_id')),
    sa.UniqueConstraint('ruta_id', 'orden', name=op.f('uq_ruta_paradas_ruta_id_orden'))
    )
    op.create_table('tarifas_pasaje',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ruta_id', sa.Integer(), nullable=False),
    sa.Column('tipo_asiento_id', sa.SmallInteger(), nullable=False),
    sa.Column('precio_bs', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('precio_maximo_referencial_bs', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('vigente_desde', sa.Date(), nullable=False),
    sa.Column('vigente_hasta', sa.Date(), nullable=True),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('precio_bs > 0 AND precio_bs <= precio_maximo_referencial_bs', name=op.f('ck_tarifas_pasaje_precio_valido')),
    sa.CheckConstraint('vigente_hasta IS NULL OR vigente_hasta >= vigente_desde', name=op.f('ck_tarifas_pasaje_vigencia_valida')),
    sa.ForeignKeyConstraint(['ruta_id'], ['rutas.id'], name=op.f('fk_tarifas_pasaje_ruta_id_rutas')),
    sa.ForeignKeyConstraint(['tipo_asiento_id'], ['tipos_asiento.id'], name=op.f('fk_tarifas_pasaje_tipo_asiento_id_tipos_asiento')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tarifas_pasaje')),
    sa.UniqueConstraint('ruta_id', 'tipo_asiento_id', 'vigente_desde', name=op.f('uq_tarifas_pasaje_ruta_id_tipo_asiento_id_vigente_desde'))
    )
    op.create_table('usuarios',
    sa.Column('email', sa.String(length=150), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('nombres', sa.String(length=80), nullable=False),
    sa.Column('apellidos', sa.String(length=80), nullable=False),
    sa.Column('telefono_e164', sa.String(length=15), nullable=True),
    sa.Column('rol', ROL_USUARIO_ENUM, nullable=False),
    sa.Column('oficina_id', sa.Integer(), nullable=True),
    sa.Column('licencia_conducir', sa.String(length=20), nullable=True),
    sa.Column('ultimo_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['oficina_id'], ['oficinas.id'], name=op.f('fk_usuarios_oficina_id_oficinas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_usuarios')),
    sa.UniqueConstraint('email', name=op.f('uq_usuarios_email'))
    )
    op.create_index(op.f('ix_usuarios_rol'), 'usuarios', ['rol'], unique=False)
    op.create_table('auditoria',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=True),
    sa.Column('accion', sa.String(length=60), nullable=False),
    sa.Column('tabla', sa.String(length=60), nullable=False),
    sa.Column('registro_id', sa.String(length=40), nullable=False),
    sa.Column('cambios', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_auditoria_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_auditoria'))
    )
    op.create_index('ix_auditoria_created_at', 'auditoria', [sa.literal_column('created_at DESC')], unique=False)
    op.create_index('ix_auditoria_tabla_registro', 'auditoria', ['tabla', 'registro_id'], unique=False)
    op.create_table('salidas',
    sa.Column('codigo', sa.String(length=20), nullable=False),
    sa.Column('ruta_id', sa.Integer(), nullable=False),
    sa.Column('plantilla_id', sa.Integer(), nullable=True),
    sa.Column('bus_id', sa.Integer(), nullable=True),
    sa.Column('oficina_salida_id', sa.Integer(), nullable=True),
    sa.Column('fecha_hora_salida', sa.DateTime(timezone=True), nullable=False),
    sa.Column('fecha_hora_llegada_estimada', sa.DateTime(timezone=True), nullable=False),
    sa.Column('anden', sa.String(length=10), nullable=True),
    sa.Column('estado', ESTADO_SALIDA_ENUM, server_default='programada', nullable=False),
    sa.Column('minutos_demora', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('motivo_estado', sa.String(length=250), nullable=True),
    sa.Column('salida_real_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('llegada_real_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('fecha_hora_llegada_estimada > fecha_hora_salida', name=op.f('ck_salidas_llegada_despues_de_salida')),
    sa.CheckConstraint('minutos_demora >= 0', name=op.f('ck_salidas_demora_no_negativa')),
    sa.ForeignKeyConstraint(['bus_id'], ['buses.id'], name=op.f('fk_salidas_bus_id_buses')),
    sa.ForeignKeyConstraint(['oficina_salida_id'], ['oficinas.id'], name=op.f('fk_salidas_oficina_salida_id_oficinas')),
    sa.ForeignKeyConstraint(['plantilla_id'], ['plantillas_horario.id'], name=op.f('fk_salidas_plantilla_id_plantillas_horario')),
    sa.ForeignKeyConstraint(['ruta_id'], ['rutas.id'], name=op.f('fk_salidas_ruta_id_rutas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_salidas')),
    sa.UniqueConstraint('codigo', name=op.f('uq_salidas_codigo'))
    )
    op.create_index('ix_salidas_bus_id_fecha_hora_salida', 'salidas', ['bus_id', 'fecha_hora_salida'], unique=False)
    op.create_index(op.f('ix_salidas_estado'), 'salidas', ['estado'], unique=False)
    op.create_index('ix_salidas_ruta_id_fecha_hora_salida', 'salidas', ['ruta_id', 'fecha_hora_salida'], unique=False)
    op.create_table('ventas_pasaje',
    sa.Column('codigo_reserva', sa.String(length=8), nullable=False),
    sa.Column('comprador_cliente_id', sa.Uuid(), nullable=False),
    sa.Column('canal', CANAL_VENTA_ENUM, server_default='web', nullable=False),
    sa.Column('estado', ESTADO_VENTA_ENUM, server_default='pendiente_pago', nullable=False),
    sa.Column('subtotal_bs', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
    sa.Column('descuento_bs', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
    sa.Column('total_bs', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
    sa.Column('expira_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('pagada_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('vendida_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('oficina_venta_id', sa.Integer(), nullable=True),
    sa.Column('observaciones', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('total_bs = subtotal_bs - descuento_bs', name=op.f('ck_ventas_pasaje_total_cuadra')),
    sa.ForeignKeyConstraint(['comprador_cliente_id'], ['clientes.id'], name=op.f('fk_ventas_pasaje_comprador_cliente_id_clientes')),
    sa.ForeignKeyConstraint(['oficina_venta_id'], ['oficinas.id'], name=op.f('fk_ventas_pasaje_oficina_venta_id_oficinas')),
    sa.ForeignKeyConstraint(['vendida_por_usuario_id'], ['usuarios.id'], name=op.f('fk_ventas_pasaje_vendida_por_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ventas_pasaje')),
    sa.UniqueConstraint('codigo_reserva', name=op.f('uq_ventas_pasaje_codigo_reserva'))
    )
    op.create_index(op.f('ix_ventas_pasaje_comprador_cliente_id'), 'ventas_pasaje', ['comprador_cliente_id'], unique=False)
    op.create_index('ix_ventas_pasaje_estado_expira_at', 'ventas_pasaje', ['estado', 'expira_at'], unique=False)
    op.create_table('boletos',
    sa.Column('numero_boleto', sa.String(length=12), nullable=False),
    sa.Column('venta_id', sa.Uuid(), nullable=False),
    sa.Column('salida_id', sa.Uuid(), nullable=False),
    sa.Column('asiento_id', sa.Integer(), nullable=False),
    sa.Column('numero_asiento', sa.SmallInteger(), nullable=False),
    sa.Column('tipo_asiento_id', sa.SmallInteger(), nullable=False),
    sa.Column('pasajero_cliente_id', sa.Uuid(), nullable=False),
    sa.Column('tipo_pasajero', TIPO_PASAJERO_ENUM, server_default='adulto', nullable=False),
    sa.Column('precio_bs', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('descuento_bs', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
    sa.Column('estado', ESTADO_BOLETO_ENUM, server_default='reservado', nullable=False),
    sa.Column('es_electronico', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('codigo_qr', sa.String(length=100), nullable=True),
    sa.Column('viaja_con_perro_guia', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('semanas_gestacion', sa.SmallInteger(), nullable=True),
    sa.Column('permiso_viaje_numero', sa.String(length=40), nullable=True),
    sa.Column('menor_acompanado_por_id', sa.Uuid(), nullable=True),
    sa.Column('boleto_origen_id', sa.Uuid(), nullable=True),
    sa.Column('abordado_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('descuento_bs >= 0 AND descuento_bs <= precio_bs', name=op.f('ck_boletos_descuento_valido')),
    sa.CheckConstraint('semanas_gestacion IS NULL OR semanas_gestacion BETWEEN 1 AND 30', name=op.f('ck_boletos_semanas_gestacion_valida')),
    sa.ForeignKeyConstraint(['asiento_id'], ['asientos.id'], name=op.f('fk_boletos_asiento_id_asientos')),
    sa.ForeignKeyConstraint(['boleto_origen_id'], ['boletos.id'], name=op.f('fk_boletos_boleto_origen_id_boletos')),
    sa.ForeignKeyConstraint(['menor_acompanado_por_id'], ['clientes.id'], name=op.f('fk_boletos_menor_acompanado_por_id_clientes')),
    sa.ForeignKeyConstraint(['pasajero_cliente_id'], ['clientes.id'], name=op.f('fk_boletos_pasajero_cliente_id_clientes')),
    sa.ForeignKeyConstraint(['salida_id'], ['salidas.id'], name=op.f('fk_boletos_salida_id_salidas')),
    sa.ForeignKeyConstraint(['tipo_asiento_id'], ['tipos_asiento.id'], name=op.f('fk_boletos_tipo_asiento_id_tipos_asiento')),
    sa.ForeignKeyConstraint(['venta_id'], ['ventas_pasaje.id'], name=op.f('fk_boletos_venta_id_ventas_pasaje')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_boletos')),
    sa.UniqueConstraint('numero_boleto', name=op.f('uq_boletos_numero_boleto'))
    )
    op.create_index(op.f('ix_boletos_pasajero_cliente_id'), 'boletos', ['pasajero_cliente_id'], unique=False)
    op.create_index(op.f('ix_boletos_salida_id'), 'boletos', ['salida_id'], unique=False)
    op.create_index(op.f('ix_boletos_venta_id'), 'boletos', ['venta_id'], unique=False)
    op.create_index('uq_boletos_asiento_activo', 'boletos', ['salida_id', 'numero_asiento'], unique=True, postgresql_where=sa.text("estado IN ('reservado', 'emitido', 'abordado')"))
    op.create_table('encomiendas',
    sa.Column('numero_guia', sa.String(length=10), nullable=False),
    sa.Column('tipo_envio', TIPO_ENVIO_ENUM, nullable=False),
    sa.Column('remitente_cliente_id', sa.Uuid(), nullable=False),
    sa.Column('cuenta_corporativa_id', sa.Uuid(), nullable=True),
    sa.Column('destinatario_nombre', sa.String(length=160), nullable=False),
    sa.Column('destinatario_tipo_documento', TIPO_DOCUMENTO_ENUM, nullable=True),
    sa.Column('destinatario_numero_documento', sa.String(length=20), nullable=True),
    sa.Column('destinatario_telefono_e164', sa.String(length=15), nullable=False),
    sa.Column('oficina_origen_id', sa.Integer(), nullable=False),
    sa.Column('oficina_destino_id', sa.Integer(), nullable=False),
    sa.Column('modalidad_entrega', MODALIDAD_ENTREGA_ENUM, server_default='retiro_en_oficina', nullable=False),
    sa.Column('direccion_entrega', sa.String(length=250), nullable=True),
    sa.Column('referencia_entrega', sa.String(length=250), nullable=True),
    sa.Column('descripcion_contenido', sa.String(length=250), nullable=False),
    sa.Column('cantidad_bultos', sa.SmallInteger(), server_default='1', nullable=False),
    sa.Column('peso_kg', sa.Numeric(precision=7, scale=2), nullable=False),
    sa.Column('largo_cm', sa.Numeric(precision=6, scale=1), nullable=True),
    sa.Column('ancho_cm', sa.Numeric(precision=6, scale=1), nullable=True),
    sa.Column('alto_cm', sa.Numeric(precision=6, scale=1), nullable=True),
    sa.Column('valor_declarado_bs', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('es_fragil', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('es_mudanza', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('precio_bs', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('pago_en', PAGO_EN_ENUM, server_default='origen', nullable=False),
    sa.Column('estado_pago', ESTADO_PAGO_ENUM, server_default='pendiente', nullable=False),
    sa.Column('estado', ESTADO_ENCOMIENDA_ENUM, server_default='registrada', nullable=False),
    sa.Column('salida_id', sa.Uuid(), nullable=True),
    sa.Column('vehiculo_carga_id', sa.Integer(), nullable=True),
    sa.Column('codigo_retiro', sa.String(length=4), nullable=True),
    sa.Column('fecha_registro', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('fecha_estimada_entrega', sa.DateTime(timezone=True), nullable=True),
    sa.Column('fecha_entrega', sa.DateTime(timezone=True), nullable=True),
    sa.Column('entregado_a_nombre', sa.String(length=160), nullable=True),
    sa.Column('entregado_a_documento', sa.String(length=20), nullable=True),
    sa.Column('registrada_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('observaciones', sa.Text(), nullable=True),
    sa.Column('es_dato_demo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(tipo_envio IN ('sobre', 'paquete') AND peso_kg <= 30) OR (tipo_envio = 'carga' AND peso_kg > 30)", name=op.f('ck_encomiendas_peso_segun_tipo')),
    sa.CheckConstraint("modalidad_entrega = 'retiro_en_oficina' OR direccion_entrega IS NOT NULL", name=op.f('ck_encomiendas_direccion_si_puerta_a_puerta')),
    sa.CheckConstraint('cantidad_bultos >= 1', name=op.f('ck_encomiendas_bultos_positivos')),
    sa.CheckConstraint('oficina_origen_id <> oficina_destino_id', name=op.f('ck_encomiendas_oficinas_distintas')),
    sa.CheckConstraint('peso_kg > 0', name=op.f('ck_encomiendas_peso_positivo')),
    sa.ForeignKeyConstraint(['cuenta_corporativa_id'], ['cuentas_corporativas.id'], name=op.f('fk_encomiendas_cuenta_corporativa_id_cuentas_corporativas')),
    sa.ForeignKeyConstraint(['oficina_destino_id'], ['oficinas.id'], name=op.f('fk_encomiendas_oficina_destino_id_oficinas')),
    sa.ForeignKeyConstraint(['oficina_origen_id'], ['oficinas.id'], name=op.f('fk_encomiendas_oficina_origen_id_oficinas')),
    sa.ForeignKeyConstraint(['registrada_por_usuario_id'], ['usuarios.id'], name=op.f('fk_encomiendas_registrada_por_usuario_id_usuarios')),
    sa.ForeignKeyConstraint(['remitente_cliente_id'], ['clientes.id'], name=op.f('fk_encomiendas_remitente_cliente_id_clientes')),
    sa.ForeignKeyConstraint(['salida_id'], ['salidas.id'], name=op.f('fk_encomiendas_salida_id_salidas')),
    sa.ForeignKeyConstraint(['vehiculo_carga_id'], ['vehiculos_carga.id'], name=op.f('fk_encomiendas_vehiculo_carga_id_vehiculos_carga')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_encomiendas')),
    sa.UniqueConstraint('numero_guia', name=op.f('uq_encomiendas_numero_guia'))
    )
    op.create_index(op.f('ix_encomiendas_destinatario_telefono_e164'), 'encomiendas', ['destinatario_telefono_e164'], unique=False)
    op.create_index(op.f('ix_encomiendas_estado'), 'encomiendas', ['estado'], unique=False)
    op.create_index(op.f('ix_encomiendas_remitente_cliente_id'), 'encomiendas', ['remitente_cliente_id'], unique=False)
    op.create_index(op.f('ix_encomiendas_salida_id'), 'encomiendas', ['salida_id'], unique=False)
    op.create_table('precios_salida',
    sa.Column('salida_id', sa.Uuid(), nullable=False),
    sa.Column('tipo_asiento_id', sa.SmallInteger(), nullable=False),
    sa.Column('precio_bs', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('precio_bs > 0', name=op.f('ck_precios_salida_precio_positivo')),
    sa.ForeignKeyConstraint(['salida_id'], ['salidas.id'], name=op.f('fk_precios_salida_salida_id_salidas'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tipo_asiento_id'], ['tipos_asiento.id'], name=op.f('fk_precios_salida_tipo_asiento_id_tipos_asiento')),
    sa.PrimaryKeyConstraint('salida_id', 'tipo_asiento_id', name=op.f('pk_precios_salida'))
    )
    op.create_table('salida_tripulacion',
    sa.Column('salida_id', sa.Uuid(), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('rol', ROL_TRIPULACION_ENUM, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['salida_id'], ['salidas.id'], name=op.f('fk_salida_tripulacion_salida_id_salidas'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_salida_tripulacion_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('salida_id', 'usuario_id', name=op.f('pk_salida_tripulacion'))
    )
    op.create_table('encomienda_eventos',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('encomienda_id', sa.Uuid(), nullable=False),
    sa.Column('estado', ESTADO_ENCOMIENDA_ENUM, nullable=False),
    sa.Column('oficina_id', sa.Integer(), nullable=True),
    sa.Column('ciudad_id', sa.SmallInteger(), nullable=True),
    sa.Column('descripcion', sa.String(length=250), nullable=False),
    sa.Column('latitud', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('longitud', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('ocurrido_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('registrado_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('visible_cliente', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['ciudad_id'], ['ciudades.id'], name=op.f('fk_encomienda_eventos_ciudad_id_ciudades')),
    sa.ForeignKeyConstraint(['encomienda_id'], ['encomiendas.id'], name=op.f('fk_encomienda_eventos_encomienda_id_encomiendas'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['oficina_id'], ['oficinas.id'], name=op.f('fk_encomienda_eventos_oficina_id_oficinas')),
    sa.ForeignKeyConstraint(['registrado_por_usuario_id'], ['usuarios.id'], name=op.f('fk_encomienda_eventos_registrado_por_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_encomienda_eventos'))
    )
    op.create_index('ix_encomienda_eventos_encomienda_ocurrido', 'encomienda_eventos', ['encomienda_id', sa.literal_column('ocurrido_at DESC')], unique=False)
    op.create_table('equipajes',
    sa.Column('boleto_id', sa.Uuid(), nullable=False),
    sa.Column('etiqueta', sa.String(length=15), nullable=False),
    sa.Column('tipo', TIPO_EQUIPAJE_ENUM, server_default='bodega', nullable=False),
    sa.Column('piezas', sa.SmallInteger(), server_default='1', nullable=False),
    sa.Column('peso_kg', sa.Numeric(precision=6, scale=2), nullable=False),
    sa.Column('peso_permitido_kg', sa.Numeric(precision=6, scale=2), server_default='20', nullable=False),
    sa.Column('exceso_kg', sa.Numeric(precision=6, scale=2), server_default='0', nullable=False),
    sa.Column('cargo_exceso_bs', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
    sa.Column('descripcion', sa.String(length=150), nullable=True),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('peso_kg > 0', name=op.f('ck_equipajes_peso_positivo')),
    sa.ForeignKeyConstraint(['boleto_id'], ['boletos.id'], name=op.f('fk_equipajes_boleto_id_boletos')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_equipajes')),
    sa.UniqueConstraint('etiqueta', name=op.f('uq_equipajes_etiqueta'))
    )
    op.create_index(op.f('ix_equipajes_boleto_id'), 'equipajes', ['boleto_id'], unique=False)
    op.create_table('solicitudes_puerta_a_puerta',
    sa.Column('codigo', sa.String(length=10), nullable=False),
    sa.Column('tipo', TIPO_SOLICITUD_PUERTA_ENUM, nullable=False),
    sa.Column('ciudad_id', sa.SmallInteger(), nullable=False),
    sa.Column('cliente_id', sa.Uuid(), nullable=False),
    sa.Column('contacto_telefono_e164', sa.String(length=15), nullable=False),
    sa.Column('direccion', sa.String(length=250), nullable=False),
    sa.Column('referencia', sa.String(length=250), nullable=True),
    sa.Column('latitud', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('longitud', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('fecha_programada', sa.Date(), nullable=False),
    sa.Column('franja', FRANJA_HORARIA_ENUM, nullable=False),
    sa.Column('peso_estimado_kg', sa.Numeric(precision=7, scale=2), nullable=True),
    sa.Column('descripcion', sa.String(length=250), nullable=True),
    sa.Column('encomienda_id', sa.Uuid(), nullable=True),
    sa.Column('vehiculo_carga_id', sa.Integer(), nullable=True),
    sa.Column('repartidor_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('estado', ESTADO_SOLICITUD_PUERTA_ENUM, server_default='solicitada', nullable=False),
    sa.Column('canal', CANAL_VENTA_ENUM, server_default='whatsapp_chat', nullable=False),
    sa.Column('costo_bs', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(tipo = 'recojo' AND franja = 'tarde_14_17') OR (tipo = 'entrega' AND franja = 'manana_08_12')", name=op.f('ck_solicitudes_puerta_a_puerta_franja_segun_tipo')),
    sa.CheckConstraint('EXTRACT(ISODOW FROM fecha_programada) BETWEEN 1 AND 5', name=op.f('ck_solicitudes_puerta_a_puerta_dia_habil')),
    sa.CheckConstraint('peso_estimado_kg IS NULL OR peso_estimado_kg >= 1', name=op.f('ck_solicitudes_puerta_a_puerta_peso_minimo')),
    sa.ForeignKeyConstraint(['ciudad_id'], ['ciudades.id'], name=op.f('fk_solicitudes_puerta_a_puerta_ciudad_id_ciudades')),
    sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], name=op.f('fk_solicitudes_puerta_a_puerta_cliente_id_clientes')),
    sa.ForeignKeyConstraint(['encomienda_id'], ['encomiendas.id'], name=op.f('fk_solicitudes_puerta_a_puerta_encomienda_id_encomiendas')),
    sa.ForeignKeyConstraint(['repartidor_usuario_id'], ['usuarios.id'], name=op.f('fk_solicitudes_puerta_a_puerta_repartidor_usuario_id_usuarios')),
    sa.ForeignKeyConstraint(['vehiculo_carga_id'], ['vehiculos_carga.id'], name=op.f('fk_solicitudes_puerta_a_puerta_vehiculo_carga_id_vehiculos_carga')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_solicitudes_puerta_a_puerta')),
    sa.UniqueConstraint('codigo', name=op.f('uq_solicitudes_puerta_a_puerta_codigo'))
    )
    op.create_index(op.f('ix_solicitudes_puerta_a_puerta_cliente_id'), 'solicitudes_puerta_a_puerta', ['cliente_id'], unique=False)
    op.create_index('ix_solicitudes_puerta_ciudad_fecha', 'solicitudes_puerta_a_puerta', ['ciudad_id', 'fecha_programada'], unique=False)
    op.create_table('pagos',
    sa.Column('venta_pasaje_id', sa.Uuid(), nullable=True),
    sa.Column('encomienda_id', sa.Uuid(), nullable=True),
    sa.Column('solicitud_puerta_id', sa.Uuid(), nullable=True),
    sa.Column('metodo', METODO_PAGO_ENUM, nullable=False),
    sa.Column('monto_bs', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('estado', ESTADO_PAGO_ENUM, server_default='pendiente', nullable=False),
    sa.Column('proveedor', sa.String(length=40), nullable=True),
    sa.Column('transaccion_externa_id', sa.String(length=80), nullable=True),
    sa.Column('qr_payload', sa.Text(), nullable=True),
    sa.Column('ultimos4_tarjeta', sa.String(length=4), nullable=True),
    sa.Column('pagado_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cobrado_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('monto_bs > 0', name=op.f('ck_pagos_monto_positivo')),
    sa.CheckConstraint('num_nonnulls(venta_pasaje_id, encomienda_id, solicitud_puerta_id) = 1', name=op.f('ck_pagos_un_solo_concepto')),
    sa.ForeignKeyConstraint(['cobrado_por_usuario_id'], ['usuarios.id'], name=op.f('fk_pagos_cobrado_por_usuario_id_usuarios')),
    sa.ForeignKeyConstraint(['encomienda_id'], ['encomiendas.id'], name=op.f('fk_pagos_encomienda_id_encomiendas')),
    sa.ForeignKeyConstraint(['solicitud_puerta_id'], ['solicitudes_puerta_a_puerta.id'], name=op.f('fk_pagos_solicitud_puerta_id_solicitudes_puerta_a_puerta')),
    sa.ForeignKeyConstraint(['venta_pasaje_id'], ['ventas_pasaje.id'], name=op.f('fk_pagos_venta_pasaje_id_ventas_pasaje')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pagos'))
    )
    op.create_index(op.f('ix_pagos_encomienda_id'), 'pagos', ['encomienda_id'], unique=False)
    op.create_index(op.f('ix_pagos_solicitud_puerta_id'), 'pagos', ['solicitud_puerta_id'], unique=False)
    op.create_index(op.f('ix_pagos_venta_pasaje_id'), 'pagos', ['venta_pasaje_id'], unique=False)
    op.create_table('facturas',
    sa.Column('pago_id', sa.Uuid(), nullable=False),
    sa.Column('numero_factura', sa.BigInteger(), nullable=False),
    sa.Column('cuf', sa.String(length=100), nullable=True),
    sa.Column('nit_ci_cliente', sa.String(length=20), nullable=False),
    sa.Column('razon_social_cliente', sa.String(length=150), nullable=False),
    sa.Column('monto_total_bs', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('fecha_emision', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('estado', ESTADO_FACTURA_ENUM, server_default='valida', nullable=False),
    sa.Column('url_pdf', sa.String(length=300), nullable=True),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['pago_id'], ['pagos.id'], name=op.f('fk_facturas_pago_id_pagos')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_facturas')),
    sa.UniqueConstraint('numero_factura', name=op.f('uq_facturas_numero_factura')),
    sa.UniqueConstraint('pago_id', name=op.f('uq_facturas_pago_id'))
    )
    op.create_table('reembolsos',
    sa.Column('pago_id', sa.Uuid(), nullable=False),
    sa.Column('boleto_id', sa.Uuid(), nullable=True),
    sa.Column('origen', ORIGEN_REEMBOLSO_ENUM, server_default='solicitud_cliente', nullable=False),
    sa.Column('monto_original_bs', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('porcentaje_retencion', sa.Numeric(precision=5, scale=2), server_default='0', nullable=False),
    sa.Column('monto_bs', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('motivo', sa.String(length=250), nullable=False),
    sa.Column('estado', ESTADO_REEMBOLSO_ENUM, server_default='solicitado', nullable=False),
    sa.Column('solicitado_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('fecha_limite_pago', sa.Date(), nullable=True),
    sa.Column('resuelto_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resuelto_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('monto_bs >= 0 AND monto_bs <= monto_original_bs', name=op.f('ck_reembolsos_monto_valido')),
    sa.CheckConstraint('porcentaje_retencion BETWEEN 0 AND 100', name=op.f('ck_reembolsos_retencion_valida')),
    sa.ForeignKeyConstraint(['boleto_id'], ['boletos.id'], name=op.f('fk_reembolsos_boleto_id_boletos')),
    sa.ForeignKeyConstraint(['pago_id'], ['pagos.id'], name=op.f('fk_reembolsos_pago_id_pagos')),
    sa.ForeignKeyConstraint(['resuelto_por_usuario_id'], ['usuarios.id'], name=op.f('fk_reembolsos_resuelto_por_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reembolsos'))
    )
    op.create_index(op.f('ix_reembolsos_boleto_id'), 'reembolsos', ['boleto_id'], unique=False)
    op.create_index(op.f('ix_reembolsos_estado'), 'reembolsos', ['estado'], unique=False)
    op.create_index(op.f('ix_reembolsos_pago_id'), 'reembolsos', ['pago_id'], unique=False)

    # Correlativos (boletos, guías, facturas, solicitudes puerta a puerta)
    for nombre, inicio in SEQUENCES.items():
        op.execute(f"CREATE SEQUENCE IF NOT EXISTS {nombre} START WITH {inicio}")

    # updated_at mantenido por trigger
    op.execute(SET_UPDATED_AT_FN)
    for tabla in TABLAS_CON_UPDATED_AT:
        op.execute(
            f"CREATE TRIGGER trg_{tabla}_updated_at BEFORE UPDATE ON {tabla} "
            f"FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )

    for sql in VIEWS_SQL:
        op.execute(sql)


def downgrade() -> None:
    """Downgrade schema."""
    for nombre in reversed(VIEW_NAMES):
        op.execute(f"DROP VIEW IF EXISTS {nombre}")
    for nombre in SEQUENCES:
        op.execute(f"DROP SEQUENCE IF EXISTS {nombre}")

    op.drop_index(op.f('ix_reembolsos_pago_id'), table_name='reembolsos')
    op.drop_index(op.f('ix_reembolsos_estado'), table_name='reembolsos')
    op.drop_index(op.f('ix_reembolsos_boleto_id'), table_name='reembolsos')
    op.drop_table('reembolsos')
    op.drop_table('facturas')
    op.drop_index(op.f('ix_pagos_venta_pasaje_id'), table_name='pagos')
    op.drop_index(op.f('ix_pagos_solicitud_puerta_id'), table_name='pagos')
    op.drop_index(op.f('ix_pagos_encomienda_id'), table_name='pagos')
    op.drop_table('pagos')
    op.drop_index('ix_solicitudes_puerta_ciudad_fecha', table_name='solicitudes_puerta_a_puerta')
    op.drop_index(op.f('ix_solicitudes_puerta_a_puerta_cliente_id'), table_name='solicitudes_puerta_a_puerta')
    op.drop_table('solicitudes_puerta_a_puerta')
    op.drop_index(op.f('ix_equipajes_boleto_id'), table_name='equipajes')
    op.drop_table('equipajes')
    op.drop_index('ix_encomienda_eventos_encomienda_ocurrido', table_name='encomienda_eventos')
    op.drop_table('encomienda_eventos')
    op.drop_table('salida_tripulacion')
    op.drop_table('precios_salida')
    op.drop_index(op.f('ix_encomiendas_salida_id'), table_name='encomiendas')
    op.drop_index(op.f('ix_encomiendas_remitente_cliente_id'), table_name='encomiendas')
    op.drop_index(op.f('ix_encomiendas_estado'), table_name='encomiendas')
    op.drop_index(op.f('ix_encomiendas_destinatario_telefono_e164'), table_name='encomiendas')
    op.drop_table('encomiendas')
    op.drop_index('uq_boletos_asiento_activo', table_name='boletos', postgresql_where=sa.text("estado IN ('reservado', 'emitido', 'abordado')"))
    op.drop_index(op.f('ix_boletos_venta_id'), table_name='boletos')
    op.drop_index(op.f('ix_boletos_salida_id'), table_name='boletos')
    op.drop_index(op.f('ix_boletos_pasajero_cliente_id'), table_name='boletos')
    op.drop_table('boletos')
    op.drop_index('ix_ventas_pasaje_estado_expira_at', table_name='ventas_pasaje')
    op.drop_index(op.f('ix_ventas_pasaje_comprador_cliente_id'), table_name='ventas_pasaje')
    op.drop_table('ventas_pasaje')
    op.drop_index('ix_salidas_ruta_id_fecha_hora_salida', table_name='salidas')
    op.drop_index(op.f('ix_salidas_estado'), table_name='salidas')
    op.drop_index('ix_salidas_bus_id_fecha_hora_salida', table_name='salidas')
    op.drop_table('salidas')
    op.drop_index('ix_auditoria_tabla_registro', table_name='auditoria')
    op.drop_index('ix_auditoria_created_at', table_name='auditoria')
    op.drop_table('auditoria')
    op.drop_index(op.f('ix_usuarios_rol'), table_name='usuarios')
    op.drop_table('usuarios')
    op.drop_table('tarifas_pasaje')
    op.drop_table('ruta_paradas')
    op.drop_table('plantillas_horario')
    op.drop_table('horarios_oficina')
    op.drop_table('vehiculos_carga')
    op.drop_table('tipo_asiento_comodidades')
    op.drop_table('tarifas_carga')
    op.drop_table('rutas')
    op.drop_index(op.f('ix_oficinas_tipo'), table_name='oficinas')
    op.drop_index(op.f('ix_oficinas_ciudad_id'), table_name='oficinas')
    op.drop_table('oficinas')
    op.drop_index('ix_faqs_fts', table_name='faqs', postgresql_using='gin')
    op.drop_table('faqs')
    op.drop_index(op.f('ix_clientes_telefono_e164'), table_name='clientes')
    op.drop_table('clientes')
    op.drop_table('asientos')
    op.drop_table('tipos_asiento')
    op.drop_table('politicas_tipo_pasajero')
    op.drop_table('parametros_negocio')
    op.drop_table('paginas_contenido')
    op.drop_table('feriados')
    op.drop_table('faq_categorias')
    op.drop_table('empresa')
    op.drop_table('cuentas_corporativas')
    op.drop_table('comodidades')
    op.drop_table('ciudades')
    op.drop_table('buses')
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
    bind = op.get_bind()
    for enum in reversed(ENUMS):
        enum.drop(bind, checkfirst=True)

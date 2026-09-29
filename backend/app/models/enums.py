"""Enums de dominio. Cada uno se mapea a un tipo ENUM de PostgreSQL con su nombre en snake_case."""

from enum import StrEnum


class TipoOficina(StrEnum):
    boleteria = "boleteria"
    bodega_carga = "bodega_carga"
    mixta = "mixta"


class ServicioOficina(StrEnum):
    boleteria = "boleteria"
    carga = "carga"
    general = "general"


class PlantaBus(StrEnum):
    alta = "alta"
    baja = "baja"


class PosicionAsiento(StrEnum):
    ventana = "ventana"
    pasillo = "pasillo"
    centro = "centro"


class EstadoBus(StrEnum):
    operativo = "operativo"
    mantenimiento = "mantenimiento"
    fuera_de_servicio = "fuera_de_servicio"


class EstadoSalida(StrEnum):
    programada = "programada"
    abordando = "abordando"
    en_ruta = "en_ruta"
    demorada = "demorada"
    llegada = "llegada"
    cancelada = "cancelada"


class RolTripulacion(StrEnum):
    conductor = "conductor"
    conductor_relevo = "conductor_relevo"
    ayudante = "ayudante"


class TipoDocumento(StrEnum):
    ci = "ci"
    pasaporte = "pasaporte"
    nit = "nit"
    carnet_extranjero = "carnet_extranjero"
    otro = "otro"


class TipoPasajero(StrEnum):
    adulto = "adulto"
    menor = "menor"
    adulto_mayor = "adulto_mayor"
    persona_con_discapacidad = "persona_con_discapacidad"
    embarazada = "embarazada"


class CanalVenta(StrEnum):
    web = "web"
    app_movil = "app_movil"
    boleteria = "boleteria"
    whatsapp_chat = "whatsapp_chat"
    whatsapp_llamada = "whatsapp_llamada"
    telefono = "telefono"


class EstadoVenta(StrEnum):
    pendiente_pago = "pendiente_pago"
    pagada = "pagada"
    cancelada = "cancelada"
    expirada = "expirada"
    reembolsada_parcial = "reembolsada_parcial"
    reembolsada = "reembolsada"


class EstadoBoleto(StrEnum):
    reservado = "reservado"
    emitido = "emitido"
    abordado = "abordado"
    cancelado = "cancelado"
    reembolsado = "reembolsado"
    cambiado = "cambiado"
    no_show = "no_show"


BOLETO_ACTIVO = (EstadoBoleto.reservado, EstadoBoleto.emitido, EstadoBoleto.abordado)


class TipoEquipaje(StrEnum):
    bodega = "bodega"
    mano = "mano"


class MetodoPago(StrEnum):
    qr = "qr"
    tarjeta_debito = "tarjeta_debito"
    tarjeta_credito = "tarjeta_credito"
    tigo_money = "tigo_money"
    efectivo = "efectivo"
    credito_corporativo = "credito_corporativo"


class EstadoPago(StrEnum):
    pendiente = "pendiente"
    aprobado = "aprobado"
    rechazado = "rechazado"
    reembolsado = "reembolsado"
    anulado = "anulado"


class EstadoFactura(StrEnum):
    valida = "valida"
    anulada = "anulada"


class EstadoReembolso(StrEnum):
    solicitado = "solicitado"
    aprobado = "aprobado"
    rechazado = "rechazado"
    pagado = "pagado"


class OrigenReembolso(StrEnum):
    solicitud_cliente = "solicitud_cliente"
    cancelacion_empresa = "cancelacion_empresa"


class TipoEnvio(StrEnum):
    sobre = "sobre"
    paquete = "paquete"
    carga = "carga"


class ModalidadEntrega(StrEnum):
    retiro_en_oficina = "retiro_en_oficina"
    puerta_a_puerta = "puerta_a_puerta"


class PagoEn(StrEnum):
    origen = "origen"
    destino = "destino"
    credito_corporativo = "credito_corporativo"


class EstadoEncomienda(StrEnum):
    registrada = "registrada"
    recibida_en_origen = "recibida_en_origen"
    en_transito = "en_transito"
    llegada_a_destino = "llegada_a_destino"
    lista_para_retiro = "lista_para_retiro"
    en_reparto = "en_reparto"
    entregada = "entregada"
    intento_fallido = "intento_fallido"
    devuelta = "devuelta"
    cancelada = "cancelada"


class TipoSolicitudPuerta(StrEnum):
    recojo = "recojo"
    entrega = "entrega"


class EstadoSolicitudPuerta(StrEnum):
    solicitada = "solicitada"
    confirmada = "confirmada"
    en_camino = "en_camino"
    completada = "completada"
    cancelada = "cancelada"
    fallida = "fallida"


class FranjaHoraria(StrEnum):
    manana_08_12 = "manana_08_12"
    tarde_14_17 = "tarde_14_17"


class TipoVehiculoCarga(StrEnum):
    furgon = "furgon"
    camion = "camion"
    furgoneta_reparto = "furgoneta_reparto"


class RolUsuario(StrEnum):
    admin = "admin"
    supervisor = "supervisor"
    boletero = "boletero"
    encargado_bodega = "encargado_bodega"
    repartidor = "repartidor"
    conductor = "conductor"
    soporte = "soporte"

/** Etiquetas en español y tono visual de cada estado del dominio. */

export type Tono = 'exito' | 'info' | 'aviso' | 'peligro' | 'neutro' | 'turquesa' | 'noche' | 'carmin'

interface Etiqueta {
  label: string
  tono: Tono
}

export const ESTADO_SALIDA: Record<string, Etiqueta> = {
  programada: { label: 'Programada', tono: 'exito' },
  abordando: { label: 'Abordando', tono: 'info' },
  demorada: { label: 'Demorada', tono: 'aviso' },
  en_ruta: { label: 'En ruta', tono: 'noche' },
  llegada: { label: 'Llegó', tono: 'neutro' },
  cancelada: { label: 'Cancelada', tono: 'peligro' },
}

export const ESTADO_ENCOMIENDA: Record<string, Etiqueta> = {
  registrada: { label: 'Registrada', tono: 'neutro' },
  recibida_en_origen: { label: 'Recibida en origen', tono: 'neutro' },
  en_transito: { label: 'En tránsito', tono: 'info' },
  llegada_a_destino: { label: 'Llegó a destino', tono: 'info' },
  lista_para_retiro: { label: 'Lista para recoger', tono: 'turquesa' },
  en_reparto: { label: 'En reparto', tono: 'noche' },
  entregada: { label: 'Entregada', tono: 'exito' },
  intento_fallido: { label: 'Intento fallido', tono: 'aviso' },
  devuelta: { label: 'Devuelta', tono: 'peligro' },
  cancelada: { label: 'Cancelada', tono: 'peligro' },
}

/** Transiciones válidas (espejo de las del backend, para ofrecer solo acciones posibles). */
export const TRANSICIONES_ENCOMIENDA: Record<string, string[]> = {
  registrada: ['recibida_en_origen', 'cancelada'],
  recibida_en_origen: ['en_transito', 'cancelada'],
  en_transito: ['llegada_a_destino'],
  llegada_a_destino: ['lista_para_retiro', 'en_reparto'],
  lista_para_retiro: ['en_reparto', 'devuelta'],
  en_reparto: ['intento_fallido'],
  intento_fallido: ['en_reparto', 'lista_para_retiro', 'devuelta'],
}

export const TRANSICIONES_SALIDA: Record<string, string[]> = {
  programada: ['abordando', 'demorada', 'en_ruta', 'cancelada'],
  demorada: ['demorada', 'abordando', 'en_ruta', 'cancelada'],
  abordando: ['en_ruta', 'demorada', 'cancelada'],
  en_ruta: ['llegada'],
  llegada: [],
  cancelada: [],
}

export const ESTADO_VENTA: Record<string, Etiqueta> = {
  pendiente_pago: { label: 'Pendiente de pago', tono: 'aviso' },
  pagada: { label: 'Pagada', tono: 'exito' },
  cancelada: { label: 'Cancelada', tono: 'neutro' },
  expirada: { label: 'Expirada', tono: 'neutro' },
  reembolsada_parcial: { label: 'Reembolso parcial', tono: 'info' },
  reembolsada: { label: 'Reembolsada', tono: 'info' },
}

export const ESTADO_BOLETO: Record<string, Etiqueta> = {
  reservado: { label: 'Reservado', tono: 'aviso' },
  emitido: { label: 'Emitido', tono: 'exito' },
  abordado: { label: 'Abordó', tono: 'noche' },
  cancelado: { label: 'Cancelado', tono: 'neutro' },
  reembolsado: { label: 'Reembolsado', tono: 'info' },
  cambiado: { label: 'Cambiado', tono: 'neutro' },
  no_show: { label: 'No se presentó', tono: 'peligro' },
}

export const ESTADO_REEMBOLSO: Record<string, Etiqueta> = {
  solicitado: { label: 'Solicitado', tono: 'aviso' },
  aprobado: { label: 'Aprobado', tono: 'info' },
  rechazado: { label: 'Rechazado', tono: 'peligro' },
  pagado: { label: 'Pagado', tono: 'exito' },
}

export const ESTADO_PUERTA: Record<string, Etiqueta> = {
  solicitada: { label: 'Solicitada', tono: 'aviso' },
  confirmada: { label: 'Confirmada', tono: 'info' },
  en_camino: { label: 'En camino', tono: 'noche' },
  completada: { label: 'Completada', tono: 'exito' },
  fallida: { label: 'Fallida', tono: 'peligro' },
  cancelada: { label: 'Cancelada', tono: 'neutro' },
}

export const TRANSICIONES_PUERTA: Record<string, string[]> = {
  solicitada: ['confirmada', 'cancelada'],
  confirmada: ['en_camino', 'cancelada'],
  en_camino: ['completada', 'fallida'],
  fallida: ['confirmada', 'cancelada'],
  completada: [],
  cancelada: [],
}

export const ESTADO_PAGO: Record<string, Etiqueta> = {
  pendiente: { label: 'Pendiente', tono: 'aviso' },
  aprobado: { label: 'Pagado', tono: 'exito' },
  rechazado: { label: 'Rechazado', tono: 'peligro' },
  reembolsado: { label: 'Reembolsado', tono: 'info' },
  anulado: { label: 'Anulado', tono: 'neutro' },
}

export const TIPO_PASAJERO: Record<string, string> = {
  adulto: 'Adulto',
  menor: 'Menor (3 a 11 años)',
  adulto_mayor: 'Adulto mayor',
  persona_con_discapacidad: 'Persona con discapacidad',
  embarazada: 'Embarazada',
}

export const METODO_PAGO: Record<string, string> = {
  qr: 'QR',
  tarjeta_debito: 'Tarjeta de débito',
  tarjeta_credito: 'Tarjeta de crédito',
  tigo_money: 'Tigo Money',
  efectivo: 'Efectivo',
  credito_corporativo: 'Crédito corporativo',
}

export const CANAL: Record<string, string> = {
  web: 'Web',
  app_movil: 'App',
  boleteria: 'Boletería',
  whatsapp_chat: 'WhatsApp',
  whatsapp_llamada: 'Llamada WhatsApp',
  telefono: 'Teléfono',
}

export const TIPO_ENVIO: Record<string, string> = { sobre: 'Sobre', paquete: 'Paquete', carga: 'Carga' }

export const ROL: Record<string, string> = {
  admin: 'Administrador',
  supervisor: 'Supervisor',
  boletero: 'Boletería',
  encargado_bodega: 'Bodega',
  repartidor: 'Repartidor',
  conductor: 'Conductor',
  soporte: 'Soporte',
}

export const TIPO_OFICINA: Record<string, string> = {
  boleteria: 'Boletería',
  bodega_carga: 'Bodega',
  mixta: 'Boletería y bodega',
}

export const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

export function etiqueta(mapa: Record<string, Etiqueta>, clave: string | null | undefined): Etiqueta {
  return (clave && mapa[clave]) || { label: clave ?? '—', tono: 'neutro' }
}

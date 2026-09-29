/** Tipos de los reportes del panel (el backend los devuelve como objetos libres). */

import type { Schemas } from './client'

export type EstadoSalida = Schemas['EstadoSalida']

export interface SalidaDelDia {
  salida_id: string
  salida: string
  ruta: string
  origen: string
  destino: string
  fecha_hora_salida: string
  estado: EstadoSalida
  minutos_demora: number
  bus: string | null
  asientos_total: number
  asientos_ocupados: number
  ocupacion_pct: number
}

export interface Resumen {
  fecha: string
  ventas_hoy_bs: number
  ventas_hoy: number
  boletos_hoy: number
  por_canal_hoy: { canal: string; ventas: number; total_bs: number }[]
  ocupacion_hoy_pct: number
  salidas_hoy: SalidaDelDia[]
  ventas_7_dias: { fecha: string; ventas: number; total_bs: number }[]
  reembolsos_pendientes: number
  reembolsos_pendientes_bs: number
  encomiendas_por_estado: Record<string, number>
  pendiente_de_cobro_bs: number
  novedades: {
    salida_id: string
    codigo: string
    ruta: string
    fecha_hora_salida: string
    estado: EstadoSalida
    minutos_demora: number
    motivo: string | null
  }[]
}

export interface ReporteVentas {
  desde: string
  hasta: string
  total_bs: number
  ventas: number
  por_dia: { fecha: string; ventas: number; total_bs: number }[]
  por_canal: { canal: string; ventas: number; total_bs: number }[]
  por_metodo_pago: { metodo: string; pagos: number; total_bs: number }[]
}

export interface ReporteEncomiendas {
  por_estado: Record<string, number>
  por_oficina_destino: { oficina: string; encomiendas: number; total_bs: number }[]
  pendiente_de_cobro_bs: number
}

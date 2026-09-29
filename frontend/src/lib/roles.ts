import type { Rol } from '@/stores/auth'

/** Quién ve cada sección del panel (el backend aplica los mismos permisos). */
export const ACCESO = {
  tablero: [] as Rol[],
  salidas: ['supervisor', 'boletero', 'conductor', 'encargado_bodega'] as Rol[],
  salidasOperar: ['supervisor'] as Rol[],
  boleteria: ['supervisor', 'boletero'] as Rol[],
  abordaje: ['supervisor', 'boletero', 'conductor'] as Rol[],
  ventas: ['supervisor', 'boletero'] as Rol[],
  reembolsos: ['supervisor', 'soporte'] as Rol[],
  reembolsosResolver: ['supervisor'] as Rol[],
  encomiendas: ['supervisor', 'encargado_bodega', 'repartidor'] as Rol[],
  encomiendasRegistrar: ['supervisor', 'encargado_bodega'] as Rol[],
  puerta: ['supervisor', 'encargado_bodega', 'repartidor', 'soporte'] as Rol[],
  catalogos: ['supervisor', 'soporte'] as Rol[],
  personal: ['supervisor'] as Rol[],
  personalEditar: ['admin'] as Rol[],
  parametros: ['admin'] as Rol[],
  clientes: ['supervisor', 'boletero', 'encargado_bodega', 'soporte'] as Rol[],
  reportes: ['supervisor'] as Rol[],
  auditoria: ['supervisor'] as Rol[],
} satisfies Record<string, Rol[]>

export const SOLO_ADMIN: Rol[] = ['admin']

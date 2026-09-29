/**
 * Acceso genérico a los catálogos CRUD del panel (/api/v1/admin/<recurso>).
 * Los catálogos comparten forma (lista paginada, GET/POST/PATCH por id), así que
 * el panel los maneja con un solo componente sin perder el manejo de errores del cliente.
 */
import { api, unwrap } from './client'

/** Fila de un catálogo: su forma depende del recurso. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Fila = Record<string, any>

export interface Pagina<T> {
  total: number
  limit: number
  offset: number
  items: T[]
}

type Metodo = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
type Opciones = { params?: { query?: Record<string, unknown> }; body?: unknown }
type ClienteSuelto = Record<Metodo, (ruta: string, opciones?: Opciones) => Promise<{ data?: unknown; error?: unknown; response: Response }>>

const suelto = api as unknown as ClienteSuelto

export function pedir<T>(metodo: Metodo, ruta: string, opciones?: Opciones): Promise<T> {
  return unwrap(suelto[metodo](ruta, opciones)) as Promise<T>
}

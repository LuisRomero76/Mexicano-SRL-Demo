import createClient, { type Middleware } from 'openapi-fetch'
import type { components, paths } from './schema'

export type Schemas = components['schemas']

/** Vacío = mismo origen (en desarrollo, Vite reenvía /api al backend). */
export const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly detalle: unknown

  constructor(status: number, code: string, message: string, detalle?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.detalle = detalle
  }

  /** Errores de validación del backend: { campo: mensaje }. */
  get camposInvalidos(): Record<string, string> {
    if (this.code !== 'datos_invalidos' || !Array.isArray(this.detalle)) return {}
    const campos: Record<string, string> = {}
    for (const e of this.detalle as { campo?: string; mensaje?: string }[]) {
      if (e.campo) campos[e.campo] = e.mensaje ?? 'Valor inválido'
    }
    return campos
  }
}

type CuerpoError = { error?: string; mensaje?: string; detalle?: unknown }

export function aApiError(status: number, cuerpo: unknown): ApiError {
  const c = (cuerpo ?? {}) as CuerpoError
  const porDefecto: Record<number, string> = {
    401: 'Tu sesión expiró. Vuelve a iniciar sesión.',
    403: 'No tienes permiso para esta acción.',
    404: 'No encontramos lo que buscas.',
    429: 'Demasiados intentos. Espera un momento.',
  }
  const mensaje = c.mensaje ?? porDefecto[status] ?? 'Ocurrió un error inesperado. Intenta de nuevo.'
  return new ApiError(status, c.error ?? `http_${status}`, mensaje, c.detalle)
}

type Oyente = () => void
const alExpirarSesion = new Set<Oyente>()
export function onSesionExpirada(fn: Oyente): () => void {
  alExpirarSesion.add(fn)
  return () => alExpirarSesion.delete(fn)
}

const middleware: Middleware = {
  async onResponse({ request, response }) {
    const esAdmin = new URL(request.url, window.location.origin).pathname.startsWith('/api/v1/admin')
    if (response.status === 401 && esAdmin) alExpirarSesion.forEach((fn) => fn())
    return response
  },
}

export const api = createClient<paths>({
  baseUrl: API_BASE,
  credentials: 'include',
  // Defensa CSRF: el backend exige esta cabecera en escrituras autenticadas por cookie.
  headers: { 'X-Requested-With': 'XMLHttpRequest' },
})
api.use(middleware)

type Resultado<T> = { data?: T; error?: unknown; response: Response }

/** Devuelve `data` o lanza `ApiError` con el mensaje del backend. */
export async function unwrap<T>(peticion: Promise<Resultado<T>>): Promise<T> {
  let r: Resultado<T>
  try {
    r = await peticion
  } catch (e) {
    if (e instanceof ApiError) throw e
    throw new ApiError(0, 'sin_conexion', 'No pudimos conectar con el servidor. Revisa tu conexión.')
  }
  if (!r.response.ok) throw aApiError(r.response.status, r.error)
  return r.data as T
}

/** Login con formulario OAuth2 (application/x-www-form-urlencoded). */
export async function loginConFormulario(email: string, password: string): Promise<void> {
  let respuesta: Response
  try {
    respuesta = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
      body: new URLSearchParams({ username: email, password }),
    })
  } catch {
    throw new ApiError(0, 'sin_conexion', 'No pudimos conectar con el servidor. Revisa tu conexión.')
  }
  if (!respuesta.ok) throw aApiError(respuesta.status, await respuesta.json().catch(() => null))
}

export function mensajeDeError(e: unknown): string {
  if (e instanceof ApiError) return e.message
  return 'Ocurrió un error inesperado. Intenta de nuevo.'
}

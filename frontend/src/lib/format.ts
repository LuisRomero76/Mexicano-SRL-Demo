/** Formatos en español de Bolivia y zona horaria America/La_Paz (UTC-4, sin horario de verano). */

export const ZONA = 'America/La_Paz'

const moneda = new Intl.NumberFormat('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const monedaEntera = new Intl.NumberFormat('es-BO', { maximumFractionDigits: 0 })
const numero = new Intl.NumberFormat('es-BO')

/** 180 → "Bs 180" ; 1234.5 → "Bs 1.234,50" ; con `entero` siempre redondea. */
export function bs(valor: number | string | null | undefined, entero = false): string {
  if (valor === null || valor === undefined || valor === '') return '—'
  const n = typeof valor === 'string' ? Number(valor) : valor
  return `Bs ${(entero || Number.isInteger(n) ? monedaEntera : moneda).format(n)}`
}

export function bsExacto(valor: number | string | null | undefined): string {
  if (valor === null || valor === undefined || valor === '') return '—'
  return `Bs ${moneda.format(typeof valor === 'string' ? Number(valor) : valor)}`
}

export function num(valor: number | null | undefined): string {
  return valor === null || valor === undefined ? '—' : numero.format(valor)
}

function partes(fecha: Date, opciones: Intl.DateTimeFormatOptions): Record<string, string> {
  const salida: Record<string, string> = {}
  for (const p of new Intl.DateTimeFormat('es-BO', { timeZone: ZONA, ...opciones }).formatToParts(fecha)) {
    salida[p.type] = p.value
  }
  return salida
}

function aDate(valor: string | Date): Date {
  if (valor instanceof Date) return valor
  // Una fecha sola ("2026-09-29") se interpreta como mediodía en Bolivia para no cambiar de día.
  return /^\d{4}-\d{2}-\d{2}$/.test(valor) ? new Date(`${valor}T12:00:00-04:00`) : new Date(valor)
}

/** "18:30" */
export function hora(valor: string | Date | null | undefined): string {
  if (!valor) return '—'
  const p = partes(aDate(valor), { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
  return `${p.hour}:${p.minute}`
}

/** "mar 29 sep" */
export function fechaCorta(valor: string | Date | null | undefined): string {
  if (!valor) return '—'
  return new Intl.DateTimeFormat('es-BO', { timeZone: ZONA, weekday: 'short', day: 'numeric', month: 'short' })
    .format(aDate(valor))
    .replace(/\./g, '')
    .replace(',', '')
}

/** "martes 29 de septiembre" */
export function fechaLarga(valor: string | Date | null | undefined): string {
  if (!valor) return '—'
  return new Intl.DateTimeFormat('es-BO', { timeZone: ZONA, weekday: 'long', day: 'numeric', month: 'long' }).format(
    aDate(valor),
  )
}

/** "29/09/2026 18:30" */
export function fechaHora(valor: string | Date | null | undefined): string {
  if (!valor) return '—'
  const p = partes(aDate(valor), {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  })
  return `${p.day}/${p.month}/${p.year} ${p.hour}:${p.minute}`
}

/** Fecha de hoy en Bolivia en formato ISO "2026-09-29". */
export function hoyISO(): string {
  const p = partes(new Date(), { year: 'numeric', month: '2-digit', day: '2-digit' })
  return `${p.year}-${p.month}-${p.day}`
}

/** Suma días a una fecha ISO sin problemas de zona horaria. */
export function sumarDias(iso: string, dias: number): string {
  const [a, m, d] = iso.split('-').map(Number)
  const f = new Date(Date.UTC(a, m - 1, d + dias))
  return f.toISOString().slice(0, 10)
}

/** 1 = lunes … 7 = domingo para una fecha ISO. */
export function diaSemanaISO(iso: string): number {
  const [a, m, d] = iso.split('-').map(Number)
  const dia = new Date(Date.UTC(a, m - 1, d)).getUTCDay()
  return dia === 0 ? 7 : dia
}

/** 840 → "14 h" ; 90 → "1 h 30 min" */
export function duracion(minutos: number): string {
  const h = Math.floor(minutos / 60)
  const m = minutos % 60
  return m ? `${h} h ${m} min` : `${h} h`
}

/** "59171420823" → "+591 71420823" */
export function telefono(e164: string | null | undefined): string {
  if (!e164) return '—'
  return e164.startsWith('591') ? `+591 ${e164.slice(3)}` : `+${e164}`
}

export function whatsappUrl(e164: string | null | undefined, texto?: string): string | undefined {
  if (!e164) return undefined
  return `https://wa.me/${e164.replace(/\D/g, '')}${texto ? `?text=${encodeURIComponent(texto)}` : ''}`
}

/** true si el ISO de fecha-hora es de otro día que `referencia` (para "+1"). */
export function esDiaSiguiente(salida: string, llegada: string): boolean {
  const a = partes(aDate(salida), { day: '2-digit', month: '2-digit' })
  const b = partes(aDate(llegada), { day: '2-digit', month: '2-digit' })
  return a.day !== b.day || a.month !== b.month
}

export function iniciales(nombre: string): string {
  return nombre
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('')
}
